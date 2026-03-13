"""
生成核心模块
实现基于检索上下文的回答生成
"""

import time
from typing import List

from .models import Document


class GenerationService:
    """生成服务 - 调用Claude API"""

    def __init__(self, api_key: str, model: str = "claude-opus-4-6"):
        self.api_key = api_key
        self.model = model

    def _build_prompt(self, query: str, context_docs: List[Document]) -> str:
        """构建RAG Prompt"""
        # 构建上下文
        context_text = "\n\n".join([
            f"[{i+1}] {doc.title}\n{doc.content[:500]}..."  # 限制每条内容长度
            for i, doc in enumerate(context_docs)
        ])

        prompt = f"""你是一个游戏行业战略研究专家。请基于以下参考资料回答用户的问题。

用户问题：{query}

参考资料：
{context_text}

请基于以上参考资料，回答用户的问题。回答时请注意：
1. 优先使用参考资料中的信息
2. 如果参考资料不足以回答，请明确说明
3. 保持客观、专业的语气
4. 如有引用，标注来源编号（如[1]、[2]）

回答："""

        return prompt

    def generate(self, query: str, context_docs: List[Document], temperature: float = 0.7) -> tuple[str, float]:
        """
        基于上下文生成回答

        Args:
            query: 用户问题
            context_docs: 上下文文档列表
            temperature: 生成随机性（0-1）

        Returns:
            (answer, generation_time_ms)
        """
        start_time = time.time()

        # 构建Prompt
        prompt = self._build_prompt(query, context_docs)

        # 调用Claude API
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            answer = response.content[0].text
            generation_time = time.time() - start_time

            return answer, generation_time

        except Exception as e:
            print(f"❌ 生成失败: {e}")
            raise

    def generate_with_confidence(self, query: str, context_docs: List[Document], temperature: float = 0.7) -> tuple[str, float, float]:
        """
        生成回答并计算置信度

        Returns:
            (answer, confidence, generation_time_ms)
        """
        import re

        start_time = time.time()

        # 生成回答
        answer, gen_time = self.generate(query, context_docs, temperature)

        # 简单置信度计算（基于引用数量）
        # 实际应用中可以使用更复杂的方法
        citations = len(re.findall(r'\[\d+\]', answer))
        confidence = min(citations / max(len(context_docs), 1), 1.0)

        total_time = time.time() - start_time

        return answer, confidence, total_time


class RAGChain:
    """
    RAG完整链路
    """

    def __init__(self, retriever, generation_service: GenerationService):
        self.retriever = retriever
        self.generation_service = generation_service

    def run(self, query: str, top_k: int = 5, temperature: float = 0.7) -> dict:
        """
        执行完整RAG流程

        Returns:
            {
                "query": 查询,
                "retrieved_docs": 检索到的文档,
                "answer": 生成的回答,
                "sources": 引用来源,
                "confidence": 置信度,
                "retrieval_time_ms": 检索耗时,
                "generation_time_ms": 生成耗时,
                "total_time_ms": 总耗时
            }
        """
        import time
        total_start = time.time()

        # 1. 检索
        retrieved_docs, retrieval_time = self.retriever.retrieve(query, top_k=top_k)

        # 2. 生成
        answer, confidence, generation_time = self.generation_service.generate_with_confidence(
            query, retrieved_docs, temperature
        )

        total_time = time.time() - total_start

        return {
            "query": query,
            "retrieved_docs": retrieved_docs,
            "answer": answer,
            "sources": retrieved_docs,
            "confidence": confidence,
            "retrieval_time_ms": retrieval_time,
            "generation_time_ms": int(generation_time * 1000),
            "total_time_ms": int(total_time * 1000)
        }


# 全局生成服务实例
_generation_service: GenerationService = None


def get_generation_service() -> GenerationService:
    """获取生成服务实例"""
    global _generation_service
    if _generation_service is None:
        raise ValueError("生成服务未初始化，请先调用init_generation_service()")
    return _generation_service


def init_generation_service(api_key: str, model: str = "claude-opus-4-6") -> GenerationService:
    """初始化生成服务"""
    global _generation_service
    _generation_service = GenerationService(api_key=api_key, model=model)
    return _generation_service
