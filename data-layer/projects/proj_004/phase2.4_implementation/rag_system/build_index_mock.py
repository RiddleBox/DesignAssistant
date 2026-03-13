"""
使用模拟向量构建索引（用于测试）
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from tqdm import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.models import Document, DocumentMetadata
from core.retrieval import VectorStore
import numpy as np


def load_documents(data_dir: str) -> list[Document]:
    """从YAML文件加载文档"""
    documents = []
    data_path = Path(data_dir)

    for yaml_file in sorted(data_path.glob('*.yaml')):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                doc = Document.from_dict(data)
                documents.append(doc)
        except Exception as e:
            print(f"[WARNING] 加载文档失败 {yaml_file}: {e}")

    print(f"[OK] 加载 {len(documents)} 条文档")
    return documents


def build_mock_index(documents: list[Document], index_path: str, meta_path: str, dimension: int = 2048):
    """使用模拟向量构建索引"""
    print("\n[INFO] 开始构建模拟向量索引...")
    print(f"[INFO] 向量维度：{dimension}")

    # 生成模拟向量（使用随机向量 + 文档内容的简单hash来保证一致性）
    print(f"[INFO] 生成 {len(documents)} 条模拟向量...")

    embeddings = []
    for doc in tqdm(documents, desc="生成向量"):
        # 使用文档ID的hash作为随机种子，保证相同文档生成相同向量
        seed = hash(doc.id) % (2**32)
        np.random.seed(seed)

        # 生成随机向量
        vec = np.random.randn(dimension).astype(np.float32)
        embeddings.append(vec)

    embeddings = np.array(embeddings)
    print(f"[OK] 向量生成完成：{embeddings.shape}")

    # 构建索引
    vector_store = VectorStore(dimension=dimension)
    vector_store.build_index(documents, embeddings)

    # 保存索引
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    vector_store.save(index_path, meta_path)

    print(f"[OK] 索引保存成功：{index_path}")
    print(f"[OK] 元数据保存成功：{meta_path}")


def main():
    parser = argparse.ArgumentParser(description='构建RAG知识库（模拟向量版本）')
    parser.add_argument('--data-dir', default='data/documents', help='文档目录')
    parser.add_argument('--index-path', default='data/vector_index.faiss', help='索引保存路径')
    parser.add_argument('--meta-path', default='data/vector_meta.pkl', help='元数据保存路径')
    parser.add_argument('--dimension', type=int, default=2048, help='向量维度')

    args = parser.parse_args()

    # 加载文档
    documents = load_documents(args.data_dir)

    if len(documents) == 0:
        print("[ERROR] 没有加载到任何文档")
        return 1

    # 构建索引
    build_mock_index(documents, args.index_path, args.meta_path, args.dimension)

    print("\n[SUCCESS] 知识库构建完成！")
    print("\n[NOTE] 这是使用模拟向量构建的索引，仅用于测试流程。")
    print("[NOTE] 生产环境请使用真实的 embedding API。")
    return 0


if __name__ == '__main__':
    exit(main())
