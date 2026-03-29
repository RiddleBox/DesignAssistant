"""
检索核心模块
实现基于向量的文档检索
"""

import time
import numpy as np
from typing import List, Optional
import faiss
import pickle
import os

from .models import Document, DocumentMetadata


class VectorStore:
    """向量存储 - 使用FAISS"""

    def __init__(self, dimension: int = 2048):
        self.dimension = dimension
        self.index = None
        self.documents: dict[str, Document] = {}  # id -> Document
        self.id_to_index: dict[str, int] = {}     # id -> vector index
        self.index_to_id: dict[int, str] = {}     # vector index -> id

    def build_index(self, documents: List[Document], embeddings: np.ndarray):
        """构建FAISS索引"""
        # 归一化向量（使用余弦相似度）
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # 创建索引
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product = Cosine Similarity (归一化后)
        self.index.add(embeddings.astype(np.float32))

        # 建立ID映射
        for i, doc in enumerate(documents):
            self.documents[doc.id] = doc
            self.id_to_index[doc.id] = i
            self.index_to_id[i] = doc.id

        print(f"[OK] Vector index built: {len(documents)} documents")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[tuple[Document, float]]:
        """
        向量检索

        Returns:
            List[(Document, score)] - 按相似度排序的文档和分数
        """
        if self.index is None:
            raise ValueError("索引未构建，请先调用build_index()")

        # 归一化查询向量
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # 检索
        scores, indices = self.index.search(
            query_embedding.reshape(1, -1).astype(np.float32),
            min(top_k, len(self.documents))
        )

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS返回-1表示无结果
                continue
            doc_id = self.index_to_id[idx]
            doc = self.documents[doc_id]
            doc.score = float(score)
            results.append((doc, float(score)))

        return results

    def save(self, index_path: str, meta_path: str):
        """保存索引和元数据"""
        # 保存FAISS索引
        faiss.write_index(self.index, index_path)

        # 保存文档元数据
        with open(meta_path, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id
            }, f)

    def load(self, index_path: str, meta_path: str):
        """加载索引和元数据"""
        self.index = faiss.read_index(index_path)

        with open(meta_path, 'rb') as f:
            meta = pickle.load(f)
            self.documents = meta['documents']
            self.id_to_index = meta['id_to_index']
            self.index_to_id = meta['index_to_id']


class EmbeddingService:
    """Embedding服务 - 支持OpenAI和智谱API"""

    def __init__(self, api_key: str, model: str = "embedding-3", provider: str = "zhipu"):
        self.api_key = api_key
        self.model = model
        self.provider = provider

        # 智谱 embedding-3 维度是 2048，OpenAI text-embedding-3-large 是 1536
        if provider == "zhipu":
            self.dimension = 2048
            self.base_url = "https://open.bigmodel.cn/api/paas/v4/"
        else:
            self.dimension = 1536
            self.base_url = None

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        批量向量化文本

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        try:
            from openai import OpenAI

            # 创建客户端
            if self.provider == "zhipu":
                client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            else:
                client = OpenAI(api_key=self.api_key)

            response = client.embeddings.create(
                model=self.model,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings)

        except Exception as e:
            print(f"[ERROR] Embedding failed: {e}")
            raise

    def embed_single(self, text: str) -> np.ndarray:
        """向量化单条文本"""
        return self.embed([text])[0]


class LocalEmbeddingService:
    """本地Embedding服务 - 使用 sentence-transformers"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        初始化本地embedding服务

        Args:
            model_name: 模型名称或路径，默认使用 all-MiniLM-L6-v2（轻量，384维）
                        支持 HuggingFace Hub ID（自动缓存到 ~/.cache/huggingface）
                        或本地路径（需包含完整权重文件）
        """
        print(f"[INFO] Loading local embedding model: {model_name}")

        # 如果传入本地路径但目录不含权重，自动 fallback 到在线模型
        import os
        _FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
        if os.path.isabs(model_name) or model_name.startswith('.'):
            # 本地路径模式：检查是否有 config.json
            if not os.path.exists(os.path.join(model_name, "config.json")):
                print(f"[WARN] 本地模型路径 {model_name} 不含权重，自动切换到在线模型 {_FALLBACK_MODEL}")
                model_name = _FALLBACK_MODEL

        from sentence_transformers import SentenceTransformer
        self._st_model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = self._st_model.get_sentence_embedding_dimension()
        print(f"[OK] Model loaded successfully, dimension: {self.dimension}")

    def _mean_pooling(self, model_output, attention_mask):
        """兼容旧接口，sentence-transformers 已内部处理"""
        pass

    def embed(self, texts: List[str]) -> np.ndarray:
        """批量向量化"""
        embeddings = self._st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """向量化单条文本"""
        return self.embed([text])[0]


class Retriever:
    """
    检索器 - 对外提供检索服务
    """

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> tuple[List[Document], int]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回文档数量

        Returns:
            (documents, query_time_ms)
        """
        start_time = time.time()

        # 向量化查询
        query_embedding = self.embedding_service.embed_single(query)

        # 向量检索
        results = self.vector_store.search(query_embedding, top_k=top_k)

        documents = [doc for doc, _ in results]
        query_time = int((time.time() - start_time) * 1000)

        return documents, query_time

    def batch_retrieve(self, queries: List[str], top_k: int = 5) -> List[tuple[List[Document], int]]:
        """批量检索"""
        results = []
        for query in queries:
            docs, time_ms = self.retrieve(query, top_k)
            results.append((docs, time_ms))
        return results

    def retrieve_context(self, request) -> "ContextResponse":
        """
        分桶召回 —— 证据包级检索，对应 /api/v1/context 接口

        设计要点（来自 PHASE2_4_CONTEXT_PACKET_PROTOCOL.md）：
        1. 先过滤再检索：按 content_type 筛选候选文档，在候选集内做向量检索
           （不是全库混排后筛，避免低频类型被高频类型淹没）
        2. 分桶配额：每种 content_type 独立配额，保证类型多样性
        3. trust_level 过滤：基于 metadata.confidence 评定
        4. reason_for_match：MVP 阶段用模板生成，保证稳定性

        Args:
            request: ContextRequest 对象

        Returns:
            ContextResponse
        """
        import time as _time
        import sys as _sys
        # 兼容两种加载方式：
        # 1. 正常包导入：from .models import ...
        # 2. load_module 动态加载（run_batch_real.py）：relative import 无法解析，改从 sys.modules 取
        _m = _sys.modules.get('rag_core.models') or _sys.modules.get('core.models')
        if _m:
            ContextPacket = _m.ContextPacket
            ContextResponse = _m.ContextResponse
            CONTENT_TYPE_VALUES = _m.CONTENT_TYPE_VALUES
            TRUST_LEVEL_VALUES = _m.TRUST_LEVEL_VALUES
        else:
            from .models import ContextPacket, ContextResponse, CONTENT_TYPE_VALUES, TRUST_LEVEL_VALUES

        t0 = _time.time()
        notes = []
        all_packets = []

        # 确定需要召回的类型列表
        needed_types = request.needed_content_types
        if not needed_types:
            needed_types = list(CONTENT_TYPE_VALUES)

        # 每桶配额
        import math
        per_bucket = max(1, math.ceil(request.top_k / len(needed_types)))

        # metadata_filter 解包
        mf = getattr(request, 'metadata_filter', None)
        industry_filter = getattr(mf, 'industry', []) if mf else []
        category_filter = getattr(mf, 'category', []) if mf else []
        min_trust_level = getattr(mf, 'min_trust_level', 'low') if mf else 'low'

        # trust_level → confidence 阈值映射
        trust_threshold = {"high": 0.8, "medium": 0.5, "low": 0.0}
        min_conf = trust_threshold.get(min_trust_level, 0.0)

        # 向量化 query（只做一次）
        query_embedding = self.embedding_service.embed_single(request.query)

        for ct in needed_types:
            # Step 1：按 content_type + metadata_filter 过滤候选文档
            candidates = [
                doc for doc in self.vector_store.documents.values()
                if getattr(doc, "content_type", None) == ct
                and (not industry_filter or getattr(doc, 'industry', 'gaming') in industry_filter)
                and (not category_filter or doc.category in category_filter)
                and doc.metadata.confidence >= min_conf
            ]

            if not candidates:
                notes.append(f"content_type='{ct}' 无候选文档（知识库未覆盖或未标注）")
                continue

            # Step 2：在候选集内做向量检索
            # 构建临时候选 id 集合，从 vector_store 里取对应向量
            candidate_ids = {doc.id for doc in candidates}
            scored = []
            for doc in candidates:
                idx = self.vector_store.id_to_index.get(doc.id)
                if idx is None:
                    continue
                import numpy as np
                vec = self.vector_store.index.reconstruct(idx)
                vec = vec / (np.linalg.norm(vec) + 1e-9)
                q = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
                score = float(np.dot(q, vec))
                scored.append((doc, score))

            # 按相似度排序，取 per_bucket 条
            scored.sort(key=lambda x: x[1], reverse=True)
            top_docs = scored[:per_bucket]

            # Step 3：组装 ContextPacket
            for doc, score in top_docs:
                # 生成 excerpt（MVP：取 content 前500字符；后续可升级为段落级定位）
                excerpt = doc.content[:500] if len(doc.content) > 500 else doc.content

                # 生成 reason_for_match（MVP：模板化，保证稳定性；后续可接 LLM）
                reason = _build_reason_for_match(request.query, ct, doc.title)

                # 评定 trust_level
                trust = _calc_trust_level(doc.metadata.confidence, doc.metadata.source)

                packet = ContextPacket(
                    packet_id=ContextPacket.new_id(),
                    source_id=doc.id,
                    source_title=doc.title,
                    content_type=ct,
                    excerpt=excerpt,
                    reason_for_match=reason,
                    trust_level=trust,
                    score=round(score, 4),
                    metadata=doc.metadata,
                    tags=doc.tags,
                    category=doc.category,
                )
                all_packets.append(packet)

        # 汇总摘要
        type_hits = {}
        for p in all_packets:
            type_hits[p.content_type] = type_hits.get(p.content_type, 0) + 1
        summary_parts = [f"{ct}×{n}" for ct, n in type_hits.items()]
        summary = f"命中 {len(all_packets)} 条：{', '.join(summary_parts) if summary_parts else '无'}"

        elapsed_ms = int((_time.time() - t0) * 1000)

        return ContextResponse(
            request_id=request.request_id,
            context_packets=all_packets,
            retrieval_time_ms=elapsed_ms,
            retrieval_summary=summary,
            retrieval_notes=notes,
        )


# 全局检索器实例（单例模式）
_retriever_instance: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """获取检索器实例"""
    global _retriever_instance
    if _retriever_instance is None:
        raise ValueError("检索器未初始化，请先调用init_retriever()")
    return _retriever_instance


def init_retriever(api_key: str, index_path: str, meta_path: str, provider: str = "zhipu") -> Retriever:
    """初始化检索器"""
    global _retriever_instance

    # 创建Embedding服务
    embedding_service = EmbeddingService(api_key=api_key, provider=provider)

    # 加载向量存储
    vector_store = VectorStore(dimension=embedding_service.dimension)
    if os.path.exists(index_path) and os.path.exists(meta_path):
        vector_store.load(index_path, meta_path)
        print(f"[OK] Vector index loaded: {len(vector_store.documents)} documents")
    else:
        print(f"[WARNING] Index file not found, need to build index first")

    _retriever_instance = Retriever(embedding_service, vector_store)
    return _retriever_instance


# ─────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def _build_reason_for_match(query: str, content_type: str, doc_title: str) -> str:
    """
    生成 reason_for_match —— MVP 阶段模板化实现，保证稳定性。
    后续可升级为 LLM 生成，但不在当前阶段做。

    模板策略：说明"为什么这条内容和当前 query 有关"，
    区分不同 content_type 的消费价值。
    """
    type_desc = {
        "glossary":         "提供术语定义，可帮助消歧和字段判断",
        "few_shot_example": "提供高质量样例，可作为格式参考和判断依据",
        "constraint_rule":  "提供判定规则或边界约束，可限定分类范围",
        "case_record":      "提供真实行业事件（含结果），可用于查证假设或引用论据",
        "market_data":      "提供可引用的行业数据或基准数字，可支撑或反驳判断",
        "background":       "提供背景知识，有助于理解上下文，非核心判断依据",
    }
    desc = type_desc.get(content_type, "提供相关知识")
    # 截断 query 到 50 字符避免过长
    q_brief = query[:50] + "…" if len(query) > 50 else query
    return f"查询「{q_brief}」与《{doc_title}》语义相关；该文档为 {content_type} 类型，{desc}。"


def _calc_trust_level(confidence: float, source: str) -> str:
    """
    评定 trust_level —— 基于 metadata.confidence 和来源评定。

    high：confidence >= 0.8（权威来源）
    medium：confidence 0.5–0.8
    low：confidence < 0.5 或来源不明
    """
    if not source or source.strip() == "":
        return "low"
    if confidence >= 0.8:
        return "high"
    elif confidence >= 0.5:
        return "medium"
    else:
        return "low"
