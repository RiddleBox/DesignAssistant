"""
数据构建脚本
用于构建知识库和向量索引
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
from core.retrieval import EmbeddingService, VectorStore
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
            print(f"⚠️ 加载文档失败 {yaml_file}: {e}")

    print(f"✅ 加载 {len(documents)} 条文档")
    return documents


def build_index(documents: list[Document], openai_key: str, index_path: str, meta_path: str):
    """构建向量索引"""
    print("\n🔧 开始构建向量索引...")

    # 创建Embedding服务
    embedding_service = EmbeddingService(api_key=openai_key)

    # 准备文本
    texts = []
    for doc in documents:
        # 组合标题和内容用于向量化
        text = f"{doc.title}\n{doc.content}"
        texts.append(text)

    print(f"📝 准备向量化 {len(texts)} 条文本...")

    # 批量向量化
    embeddings = []
    batch_size = 100

    for i in tqdm(range(0, len(texts), batch_size), desc="向量化"):
        batch = texts[i:i+batch_size]
        batch_embeddings = embedding_service.embed(batch)
        embeddings.append(batch_embeddings)

    embeddings = np.vstack(embeddings)
    print(f"✅ 向量化完成：{embeddings.shape}")

    # 构建索引
    vector_store = VectorStore(dimension=1536)
    vector_store.build_index(documents, embeddings)

    # 保存索引
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    vector_store.save(index_path, meta_path)

    print(f"✅ 索引保存成功：{index_path}")
    print(f"✅ 元数据保存成功：{meta_path}")


def main():
    parser = argparse.ArgumentParser(description='构建RAG知识库')
    parser.add_argument('--data-dir', default='data/documents', help='文档目录')
    parser.add_argument('--index-path', default='data/vector_index.faiss', help='索引保存路径')
    parser.add_argument('--meta-path', default='data/vector_meta.pkl', help='元数据保存路径')
    parser.add_argument('--openai-key', default=os.getenv('OPENAI_API_KEY'), help='OpenAI API Key')

    args = parser.parse_args()

    if not args.openai_key:
        print("❌ 请提供OpenAI API Key（--openai-key或OPENAI_API_KEY环境变量）")
        return 1

    # 加载文档
    documents = load_documents(args.data_dir)

    if len(documents) == 0:
        print("❌ 没有加载到任何文档")
        return 1

    # 构建索引
    build_index(documents, args.openai_key, args.index_path, args.meta_path)

    print("\n🎉 知识库构建完成！")
    return 0


if __name__ == '__main__':
    exit(main())
