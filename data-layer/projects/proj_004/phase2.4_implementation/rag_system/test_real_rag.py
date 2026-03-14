"""
测试真实RAG完整链路
验证：本地embedding + FAISS检索 + Claude API生成
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import VectorStore, LocalEmbeddingService, Retriever
from core.generation import GenerationService, RAGChain


def test_real_rag():
    """测试真实RAG完整链路"""

    print("=" * 60)
    print("Testing Real RAG Pipeline (Retrieval + Generation)")
    print("=" * 60)

    # 1. 加载本地embedding服务
    print("\n[Step 1/4] Loading local embedding service...")
    model_path = Path(__file__).parent / "models" / "bert-base-uncased"
    embedding_service = LocalEmbeddingService(model_name=str(model_path))
    print(f"[OK] Model loaded, dimension: {embedding_service.dimension}")

    # 2. 加载真实向量索引
    print("\n[Step 2/4] Loading real vector index...")
    data_dir = Path(__file__).parent / "data"
    index_path = data_dir / "vector_index_local.faiss"
    meta_path = data_dir / "vector_meta_local.pkl"

    if not index_path.exists() or not meta_path.exists():
        print("[ERROR] Index files not found! Please run build_index_local.py first.")
        return False

    vector_store = VectorStore(dimension=embedding_service.dimension)
    vector_store.load(str(index_path), str(meta_path))
    print(f"[OK] Index loaded: {len(vector_store.documents)} documents")

    # 创建检索器
    retriever = Retriever(embedding_service, vector_store)

    # 3. 初始化Claude生成服务
    print("\n[Step 3/4] Initializing Claude API generation service...")

    # 使用你提供的API配置
    api_key = "sk-zaTElcRPkLs7ei5P0Loek8abGi8vFrH0ozBRltt7rL4djhMx"
    base_url = "https://api123.icu"

    generation_service = GenerationService(
        api_key=api_key,
        model="claude-opus-4-5",
        base_url=base_url
    )
    print(f"[OK] Generation service initialized (model: claude-opus-4-5)")

    # 4. 创建RAG链路
    print("\n[Step 4/4] Testing end-to-end RAG pipeline...")
    rag_chain = RAGChain(retriever, generation_service)

    # 测试查询
    test_queries = [
        "游戏设计中如何提升玩家留存率？",
        "Battle Royale游戏的核心设计要素有哪些？",
        "独立游戏开发面临的主要挑战是什么？"
    ]

    # 保存测试结果
    results = []

    print(f"\n{'='*60}")
    print("RAG Pipeline Test Results")
    print(f"{'='*60}\n")

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}/{len(test_queries)}")
        print(f"{'='*60}")
        print(f"Query: {query}\n")

        try:
            # 执行RAG
            result = rag_chain.run(query, top_k=3, temperature=0.7)

            # 显示检索结果
            print("Retrieved Documents:")
            print("-" * 60)
            for j, doc in enumerate(result['retrieved_docs'], 1):
                print(f"  {j}. [{doc.id}] {doc.title}")
                print(f"     Score: {doc.score:.4f}")
                print(f"     Category: {doc.category}")

            # 显示生成结果
            print(f"\nGenerated Answer:")
            print("-" * 60)
            print(result['answer'])

            # 显示性能指标
            print(f"\nPerformance Metrics:")
            print("-" * 60)
            print(f"  Retrieval time: {result['retrieval_time_ms']}ms")
            print(f"  Generation time: {result['generation_time_ms']}ms")
            print(f"  Total time: {result['total_time_ms']}ms")
            print(f"  Confidence: {result['confidence']:.2f}")

            # 保存结果
            results.append({
                "query": query,
                "answer": result['answer'],
                "sources": [{"id": doc.id, "title": doc.title, "score": doc.score} for doc in result['retrieved_docs']],
                "metrics": {
                    "retrieval_time_ms": result['retrieval_time_ms'],
                    "generation_time_ms": result['generation_time_ms'],
                    "total_time_ms": result['total_time_ms'],
                    "confidence": result['confidence']
                },
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"[ERROR] Test case {i} failed: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 保存测试日志
    log_dir = Path(__file__).parent / "docs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "real_rag_test_log.json"

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "config": {
                "embedding_model": "bert-base-uncased (local)",
                "embedding_dimension": embedding_service.dimension,
                "llm_model": "claude-opus-4-5",
                "index_type": "FAISS IndexFlatIP",
                "total_documents": len(vector_store.documents)
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("[SUCCESS] Real RAG pipeline test completed!")
    print(f"{'='*60}")
    print(f"\nTest Summary:")
    print(f"  - Total test cases: {len(test_queries)}")
    print(f"  - Successful: {len(results)}")
    print(f"  - Failed: {len(test_queries) - len(results)}")
    print(f"  - Test log saved to: {log_file}")

    return len(results) == len(test_queries)


if __name__ == "__main__":
    success = test_real_rag()
    sys.exit(0 if success else 1)
