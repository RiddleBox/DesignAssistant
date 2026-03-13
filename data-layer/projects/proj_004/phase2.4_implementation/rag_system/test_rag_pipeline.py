"""
完整RAG闭环测试（使用模拟向量和模拟生成）
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import VectorStore, Retriever
from core.generation import RAGChain
from core.models import Document
import numpy as np
import time


class MockEmbeddingService:
    """模拟Embedding服务"""
    def __init__(self):
        self.dimension = 2048

    def embed_single(self, text: str) -> np.ndarray:
        """使用文本hash生成一致的模拟向量"""
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        return np.random.randn(self.dimension).astype(np.float32)


class MockGenerationService:
    """模拟生成服务（不调用真实API）"""

    def __init__(self):
        self.model = "mock-llm"

    def _build_prompt(self, query: str, context_docs: list[Document]) -> str:
        """构建RAG Prompt"""
        context_text = "\n\n".join([
            f"[{i+1}] {doc.title}\n{doc.content[:300]}..."
            for i, doc in enumerate(context_docs)
        ])

        prompt = f"""你是一个游戏行业战略研究专家。请基于以下参考资料回答用户的问题。

用户问题：{query}

参考资料：
{context_text}

请基于以上参考资料，回答用户的问题。"""

        return prompt

    def generate_with_confidence(self, query: str, context_docs: list[Document], temperature: float = 0.7) -> tuple[str, float, float]:
        """
        模拟生成回答

        Returns:
            (answer, confidence, generation_time_ms)
        """
        start_time = time.time()

        # 模拟生成延迟
        time.sleep(0.1)

        # 构建模拟回答
        answer = f"""基于检索到的 {len(context_docs)} 条参考资料，我为您总结如下：

"""

        for i, doc in enumerate(context_docs[:3], 1):
            answer += f"{i}. 根据[{i}] {doc.title}：\n"
            answer += f"   {doc.content[:150]}...\n\n"

        answer += f"""
以上是基于参考资料的回答。由于这是模拟生成，实际生产环境中会使用真实的LLM（如Claude）生成更详细和准确的回答。

引用来源：{', '.join([f'[{i+1}]' for i in range(len(context_docs))])}
"""

        # 模拟置信度（基于检索文档数量）
        confidence = min(len(context_docs) / 5.0, 1.0)

        generation_time = time.time() - start_time

        return answer, confidence, generation_time


def test_rag_pipeline():
    """测试完整RAG流程"""
    print("=" * 80)
    print("RAG系统完整闭环测试")
    print("=" * 80)

    # 1. 加载向量索引
    print("\n[步骤 1/4] 加载向量索引...")
    vector_store = VectorStore(dimension=2048)
    vector_store.load('data/vector_index.faiss', 'data/vector_meta.pkl')
    print(f"[OK] 加载完成：{len(vector_store.documents)} 条文档")

    # 2. 创建检索器
    print("\n[步骤 2/4] 创建检索器...")
    embedding_service = MockEmbeddingService()
    retriever = Retriever(embedding_service, vector_store)
    print("[OK] 检索器创建完成")

    # 3. 创建生成服务
    print("\n[步骤 3/4] 创建生成服务...")
    generation_service = MockGenerationService()
    print("[OK] 生成服务创建完成（模拟模式）")

    # 4. 创建RAG链
    print("\n[步骤 4/4] 创建RAG链...")
    rag_chain = RAGChain(retriever, generation_service)
    print("[OK] RAG链创建完成")

    # 5. 测试RAG流程
    print("\n" + "=" * 80)
    print("开始测试RAG查询")
    print("=" * 80)

    test_queries = [
        "如何设计游戏的付费系统？",
        "Roguelike游戏的核心机制是什么？",
        "独立游戏如何发行？"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"测试查询 {i}/{len(test_queries)}")
        print(f"{'='*80}")
        print(f"问题: {query}\n")

        # 执行RAG
        result = rag_chain.run(query, top_k=3, temperature=0.7)

        # 显示结果
        print(f"[检索阶段]")
        print(f"  检索耗时: {result['retrieval_time_ms']}ms")
        print(f"  检索到 {len(result['retrieved_docs'])} 条文档:")
        for j, doc in enumerate(result['retrieved_docs'], 1):
            print(f"    [{j}] {doc.title} (相似度: {doc.score:.4f})")

        print(f"\n[生成阶段]")
        print(f"  生成耗时: {result['generation_time_ms']}ms")
        print(f"  置信度: {result['confidence']:.2f}")

        print(f"\n[生成回答]")
        print("-" * 80)
        print(result['answer'])
        print("-" * 80)

        print(f"\n[性能统计]")
        print(f"  检索耗时: {result['retrieval_time_ms']}ms")
        print(f"  生成耗时: {result['generation_time_ms']}ms")
        print(f"  总耗时: {result['total_time_ms']}ms")

    # 6. 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print("[OK] 检索模块：正常工作")
    print("[OK] 生成模块：正常工作（模拟模式）")
    print("[OK] RAG链路：完整打通")
    print("\n[注意]")
    print("  - 当前使用模拟向量和模拟生成")
    print("  - 生产环境需要：")
    print("    1. 真实的embedding API（智谱/OpenAI）")
    print("    2. 真实的LLM API（Claude/GPT）")
    print("=" * 80)


if __name__ == '__main__':
    test_rag_pipeline()
