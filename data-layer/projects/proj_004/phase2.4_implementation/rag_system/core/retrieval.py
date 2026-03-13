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

        print(f"✅ 向量索引构建完成：{len(documents)} 条文档")

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
            print(f"❌ Embedding失败: {e}")
            raise

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
        print(f"✅ 向量索引加载完成：{len(vector_store.documents)} 条文档")
    else:
        print(f"⚠️ 索引文件不存在，需要先构建索引")

    _retriever_instance = Retriever(embedding_service, vector_store)
    return _retriever_instance
