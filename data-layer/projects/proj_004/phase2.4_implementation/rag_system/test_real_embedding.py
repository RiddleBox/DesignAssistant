"""
测试真实 Embedding 服务
用于验证智谱 API 的 embedding-3 模型是否可用
"""
import os
import sys
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import EmbeddingService


def test_real_embedding():
    """测试真实 embedding 服务"""

    # 从环境变量获取 API Key
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        print("[ERROR] 未找到 ZHIPU_API_KEY 环境变量")
        print("请设置: export ZHIPU_API_KEY=your_api_key")
        return False

    print("=" * 60)
    print("测试真实 Embedding 服务")
    print("=" * 60)

    try:
        # 创建 embedding 服务
        print("\n1. 初始化 EmbeddingService...")
        embedding_service = EmbeddingService(
            api_key=api_key,
            model="embedding-3",
            provider="zhipu"
        )
        print(f"   [OK] 服务初始化成功")
        print(f"   - Provider: zhipu")
        print(f"   - Model: embedding-3")
        print(f"   - Dimension: {embedding_service.dimension}")

        # 测试单条文本
        print("\n2. 测试单条文本向量化...")
        test_text = "《黑神话：悟空》是一款基于中国神话的动作RPG游戏"
        embedding = embedding_service.embed_single(test_text)
        print(f"   ✅ 向量化成功")
        print(f"   - 输入文本: {test_text}")
        print(f"   - 向量维度: {embedding.shape}")
        print(f"   - 向量范数: {np.linalg.norm(embedding):.4f}")
        print(f"   - 前5维: {embedding[:5]}")

        # 测试批量文本
        print("\n3. 测试批量文本向量化...")
        test_texts = [
            "《黑神话：悟空》是一款基于中国神话的动作RPG游戏",
            "Unity引擎在移动游戏开发中占据主导地位",
            "2024年全球游戏市场规模预计达到2000亿美元"
        ]
        embeddings = embedding_service.embed(test_texts)
        print(f"   ✅ 批量向量化成功")
        print(f"   - 输入文本数: {len(test_texts)}")
        print(f"   - 输出向量形状: {embeddings.shape}")

        # 测试向量相似度
        print("\n4. 测试向量相似度...")
        similarity_01 = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        similarity_02 = np.dot(embeddings[0], embeddings[2]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[2])
        )
        print(f"   - 文本0 vs 文本1 相似度: {similarity_01:.4f}")
        print(f"   - 文本0 vs 文本2 相似度: {similarity_02:.4f}")

        print("\n" + "=" * 60)
        print("[SUCCESS] 真实 Embedding 服务测试通过")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_real_embedding()
    sys.exit(0 if success else 1)
