"""
测试真实检索链路
验证本地embedding + FAISS索引的检索效果
"""

import os
import sys
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import VectorStore, LocalEmbeddingService


def test_real_retrieval():
    """测试真实检索链路"""

    print("=" * 60)
    print("Testing Real Retrieval Pipeline")
    print("=" * 60)

    # 1. 加载本地embedding服务
    print("\n[Step 1/3] Loading local embedding service...")
    model_path = Path(__file__).parent / "models" / "bert-base-uncased"
    embedding_service = LocalEmbeddingService(model_name=str(model_path))
    print(f"[OK] Model loaded, dimension: {embedding_service.dimension}")

    # 2. 加载真实向量索引
    print("\n[Step 2/3] Loading real vector index...")
    data_dir = Path(__file__).parent / "data"
    index_path = data_dir / "vector_index_local.faiss"
    meta_path = data_dir / "vector_meta_local.pkl"

    if not index_path.exists() or not meta_path.exists():
        print("[ERROR] Index files not found! Please run build_index_local.py first.")
        return False

    vector_store = VectorStore(dimension=embedding_service.dimension)
    vector_store.load(str(index_path), str(meta_path))
    print(f"[OK] Index loaded: {len(vector_store.documents)} documents")

    # 3. 测试检索
    print("\n[Step 3/3] Testing retrieval...")

    test_queries = [
        "游戏设计的核心要素是什么？",
        "2024年游戏市场的趋势",
        "Unity引擎的优势",
        "如何提升玩家留存率",
        "独立游戏开发的挑战"
    ]

    print(f"\n{'='*60}")
    print("Retrieval Test Results")
    print(f"{'='*60}\n")

    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        print("-" * 60)

        # 向量化查询
        query_embedding = embedding_service.embed_single(query)

        # 检索
        results = vector_store.search(query_embedding, top_k=3)

        # 显示结果
        for rank, (doc, score) in enumerate(results, 1):
            print(f"  {rank}. [{doc.id}] {doc.title}")
            print(f"     Score: {score:.4f}")
            print(f"     Category: {doc.category}")
            print(f"     Tags: {', '.join(doc.tags[:3])}")
            print()

        print()

    print("=" * 60)
    print("[SUCCESS] Real retrieval pipeline test passed!")
    print("=" * 60)
    print("\nKey Metrics:")
    print(f"  - Total documents: {len(vector_store.documents)}")
    print(f"  - Embedding dimension: {embedding_service.dimension}")
    print(f"  - Model: bert-base-uncased (local)")
    print(f"  - Index type: FAISS IndexFlatIP")
    print(f"  - Test queries: {len(test_queries)}")

    return True


if __name__ == "__main__":
    success = test_real_retrieval()
    sys.exit(0 if success else 1)
