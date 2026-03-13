"""
测试检索功能（使用模拟向量）
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import VectorStore, EmbeddingService, Retriever
import numpy as np


def test_retrieval():
    """测试检索功能"""
    print("=" * 60)
    print("RAG系统检索功能测试")
    print("=" * 60)

    # 1. 加载向量索引
    print("\n[1] 加载向量索引...")
    vector_store = VectorStore(dimension=2048)
    vector_store.load('data/vector_index.faiss', 'data/vector_meta.pkl')
    print(f"[OK] 加载完成：{len(vector_store.documents)} 条文档")

    # 2. 创建模拟的Embedding服务（用于查询向量化）
    print("\n[2] 创建模拟Embedding服务...")

    class MockEmbeddingService:
        """模拟Embedding服务"""
        def __init__(self):
            self.dimension = 2048

        def embed_single(self, text: str) -> np.ndarray:
            """使用文本hash生成一致的模拟向量"""
            seed = hash(text) % (2**32)
            np.random.seed(seed)
            return np.random.randn(self.dimension).astype(np.float32)

    embedding_service = MockEmbeddingService()
    print("[OK] 模拟Embedding服务创建完成")

    # 3. 创建检索器
    print("\n[3] 创建检索器...")
    retriever = Retriever(embedding_service, vector_store)
    print("[OK] 检索器创建完成")

    # 4. 测试检索
    print("\n[4] 测试检索功能...")
    print("-" * 60)

    test_queries = [
        "如何设计游戏的付费系统？",
        "Roguelike游戏的核心机制是什么？",
        "游戏性能优化有哪些方法？",
        "独立游戏如何发行？",
        "VR游戏设计要注意什么？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        documents, query_time = retriever.retrieve(query, top_k=3)

        print(f"检索耗时: {query_time}ms")
        print(f"返回文档数: {len(documents)}")

        for j, doc in enumerate(documents, 1):
            print(f"\n  [{j}] {doc.title} (ID: {doc.id}, 相似度: {doc.score:.4f})")
            print(f"      分类: {doc.category}")
            print(f"      标签: {', '.join(doc.tags)}")
            print(f"      内容预览: {doc.content[:100]}...")

        print("-" * 60)

    # 5. 统计信息
    print("\n[5] 统计信息")
    print(f"索引文档总数: {len(vector_store.documents)}")
    print(f"向量维度: {vector_store.dimension}")
    print(f"索引类型: FAISS IndexFlatIP")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    test_retrieval()
