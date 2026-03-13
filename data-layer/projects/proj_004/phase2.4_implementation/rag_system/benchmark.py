"""
RAG系统 Benchmark 基准测试
测试检索和生成的延迟与质量指标
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import VectorStore, Retriever
from core.generation import RAGChain
from core.models import Document
import numpy as np


class MockEmbeddingService:
    """模拟Embedding服务"""
    def __init__(self):
        self.dimension = 2048

    def embed_single(self, text: str) -> np.ndarray:
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(self.dimension).astype(np.float32)


class MockGenerationService:
    """模拟生成服务"""
    def __init__(self):
        self.model = "mock-llm"

    def generate_with_confidence(self, query: str, context_docs: List[Document], temperature: float = 0.7):
        start_time = time.time()
        time.sleep(0.1)  # 模拟生成延迟

        answer = f"基于 {len(context_docs)} 条参考资料的回答..."
        confidence = min(len(context_docs) / 5.0, 1.0)
        generation_time = time.time() - start_time

        return answer, confidence, generation_time


def run_benchmark():
    """运行基准测试"""
    print("=" * 80)
    print("RAG系统 Benchmark 基准测试")
    print("=" * 80)

    # 1. 初始化系统
    print("\n[初始化] 加载系统组件...")
    vector_store = VectorStore(dimension=2048)
    vector_store.load('data/vector_index.faiss', 'data/vector_meta.pkl')

    embedding_service = MockEmbeddingService()
    retriever = Retriever(embedding_service, vector_store)

    generation_service = MockGenerationService()
    rag_chain = RAGChain(retriever, generation_service)

    print(f"[OK] 系统初始化完成，文档数：{len(vector_store.documents)}")

    # 2. 定义测试查询
    test_queries = [
        "如何设计游戏的付费系统？",
        "Roguelike游戏的核心机制是什么？",
        "游戏性能优化有哪些方法？",
        "独立游戏如何发行？",
        "VR游戏设计要注意什么？",
        "MMORPG副本如何设计？",
        "游戏新手引导的最佳实践？",
        "二次元手游市场趋势？",
        "游戏数据分析的关键指标？",
        "游戏本地化策略？"
    ]

    # 3. 检索性能测试
    print("\n" + "=" * 80)
    print("[测试 1/3] 检索性能测试")
    print("=" * 80)

    retrieval_times = []
    retrieval_results = []

    for i, query in enumerate(test_queries, 1):
        docs, query_time = retriever.retrieve(query, top_k=5)
        retrieval_times.append(query_time)
        retrieval_results.append({
            "query": query,
            "num_docs": len(docs),
            "time_ms": query_time,
            "top_score": docs[0].score if docs else 0
        })
        print(f"  [{i:2d}] {query[:40]:40s} | {query_time:4d}ms | {len(docs)} docs")

    # 统计检索性能
    retrieval_stats = {
        "total_queries": len(test_queries),
        "avg_time_ms": np.mean(retrieval_times),
        "p50_time_ms": np.percentile(retrieval_times, 50),
        "p95_time_ms": np.percentile(retrieval_times, 95),
        "p99_time_ms": np.percentile(retrieval_times, 99),
        "min_time_ms": np.min(retrieval_times),
        "max_time_ms": np.max(retrieval_times)
    }

    print(f"\n[检索性能统计]")
    print(f"  总查询数: {retrieval_stats['total_queries']}")
    print(f"  平均延迟: {retrieval_stats['avg_time_ms']:.2f}ms")
    print(f"  P50延迟: {retrieval_stats['p50_time_ms']:.2f}ms")
    print(f"  P95延迟: {retrieval_stats['p95_time_ms']:.2f}ms")
    print(f"  P99延迟: {retrieval_stats['p99_time_ms']:.2f}ms")
    print(f"  最小延迟: {retrieval_stats['min_time_ms']:.2f}ms")
    print(f"  最大延迟: {retrieval_stats['max_time_ms']:.2f}ms")

    # 4. RAG完整流程测试
    print("\n" + "=" * 80)
    print("[测试 2/3] RAG完整流程测试")
    print("=" * 80)

    rag_times = []
    rag_results = []

    for i, query in enumerate(test_queries[:5], 1):  # 只测试前5个
        result = rag_chain.run(query, top_k=5, temperature=0.7)
        rag_times.append(result['total_time_ms'])
        rag_results.append({
            "query": query,
            "retrieval_time_ms": result['retrieval_time_ms'],
            "generation_time_ms": result['generation_time_ms'],
            "total_time_ms": result['total_time_ms'],
            "confidence": result['confidence']
        })
        print(f"  [{i}] {query[:40]:40s}")
        print(f"      检索: {result['retrieval_time_ms']:4d}ms | 生成: {result['generation_time_ms']:4d}ms | 总计: {result['total_time_ms']:4d}ms | 置信度: {result['confidence']:.2f}")

    # 统计RAG性能
    rag_stats = {
        "total_queries": len(rag_results),
        "avg_total_time_ms": np.mean(rag_times),
        "avg_retrieval_time_ms": np.mean([r['retrieval_time_ms'] for r in rag_results]),
        "avg_generation_time_ms": np.mean([r['generation_time_ms'] for r in rag_results]),
        "avg_confidence": np.mean([r['confidence'] for r in rag_results]),
        "p95_total_time_ms": np.percentile(rag_times, 95) if len(rag_times) > 1 else rag_times[0]
    }

    print(f"\n[RAG性能统计]")
    print(f"  总查询数: {rag_stats['total_queries']}")
    print(f"  平均总延迟: {rag_stats['avg_total_time_ms']:.2f}ms")
    print(f"  平均检索延迟: {rag_stats['avg_retrieval_time_ms']:.2f}ms")
    print(f"  平均生成延迟: {rag_stats['avg_generation_time_ms']:.2f}ms")
    print(f"  平均置信度: {rag_stats['avg_confidence']:.2f}")
    print(f"  P95总延迟: {rag_stats['p95_total_time_ms']:.2f}ms")

    # 5. 检索质量评估
    print("\n" + "=" * 80)
    print("[测试 3/3] 检索质量评估")
    print("=" * 80)

    quality_metrics = {
        "avg_top1_score": np.mean([r['top_score'] for r in retrieval_results]),
        "queries_with_results": sum(1 for r in retrieval_results if r['num_docs'] > 0),
        "avg_docs_per_query": np.mean([r['num_docs'] for r in retrieval_results])
    }

    print(f"  平均Top-1相似度: {quality_metrics['avg_top1_score']:.4f}")
    print(f"  有结果的查询数: {quality_metrics['queries_with_results']}/{len(test_queries)}")
    print(f"  平均返回文档数: {quality_metrics['avg_docs_per_query']:.2f}")

    # 6. 生成基准报告
    print("\n" + "=" * 80)
    print("[基准报告] 性能基线")
    print("=" * 80)

    baseline = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_config": {
            "num_documents": len(vector_store.documents),
            "vector_dimension": vector_store.dimension,
            "index_type": "FAISS IndexFlatIP",
            "mode": "mock"
        },
        "retrieval_baseline": {
            "target_p95_ms": 100,
            "actual_p95_ms": retrieval_stats['p95_time_ms'],
            "status": "PASS" if retrieval_stats['p95_time_ms'] < 100 else "FAIL"
        },
        "rag_baseline": {
            "target_p95_ms": 3500,
            "actual_p95_ms": rag_stats['p95_total_time_ms'],
            "status": "PASS" if rag_stats['p95_total_time_ms'] < 3500 else "FAIL"
        },
        "quality_baseline": {
            "target_avg_score": 0.03,
            "actual_avg_score": quality_metrics['avg_top1_score'],
            "status": "PASS" if quality_metrics['avg_top1_score'] > 0.03 else "FAIL"
        },
        "detailed_stats": {
            "retrieval": retrieval_stats,
            "rag": rag_stats,
            "quality": quality_metrics
        }
    }

    print(f"\n[性能基线]")
    print(f"  检索延迟 (P95): 目标 < 100ms, 实际 {baseline['retrieval_baseline']['actual_p95_ms']:.2f}ms [{baseline['retrieval_baseline']['status']}]")
    print(f"  RAG延迟 (P95): 目标 < 3500ms, 实际 {baseline['rag_baseline']['actual_p95_ms']:.2f}ms [{baseline['rag_baseline']['status']}]")
    print(f"  检索质量: 目标 > 0.03, 实际 {baseline['quality_baseline']['actual_avg_score']:.4f} [{baseline['quality_baseline']['status']}]")

    # 7. 保存报告
    report_path = 'docs/benchmark_report.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    # 转换numpy类型为Python原生类型
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        return obj

    baseline_serializable = convert_numpy_types(baseline)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(baseline_serializable, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] 基准报告已保存: {report_path}")

    # 8. 总结
    print("\n" + "=" * 80)
    print("[总结]")
    print("=" * 80)
    all_pass = all([
        baseline['retrieval_baseline']['status'] == 'PASS',
        baseline['rag_baseline']['status'] == 'PASS',
        baseline['quality_baseline']['status'] == 'PASS'
    ])

    if all_pass:
        print("✅ 所有基准测试通过！")
    else:
        print("⚠️ 部分基准测试未通过，请检查详细报告。")

    print("\n[注意]")
    print("  - 当前使用模拟向量和模拟生成")
    print("  - 生产环境性能可能有所不同")
    print("  - 建议使用真实API后重新建立基线")
    print("=" * 80)


if __name__ == '__main__':
    run_benchmark()
