"""
使用本地开源模型构建真实向量索引
方案B：sentence-transformers + 本地embedding
"""

import os
import sys
import yaml
import numpy as np
from pathlib import Path
from tqdm import tqdm

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.models import Document, DocumentMetadata
from core.retrieval import VectorStore, LocalEmbeddingService


def load_documents(data_dir: str) -> list[Document]:
    """加载所有YAML文档"""
    documents = []
    data_path = Path(data_dir)

    yaml_files = sorted(data_path.glob("kb_*.yaml"))

    print(f"\n[INFO] Found {len(yaml_files)} document files")

    for yaml_file in yaml_files:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

            # 创建Document对象
            doc = Document(
                id=data['id'],
                title=data['title'],
                content=data['content'],
                category=data['category'],
                tags=data['tags'],
                metadata=DocumentMetadata(**data['metadata'])
            )
            documents.append(doc)

    print(f"[OK] Loaded {len(documents)} documents")
    return documents


def build_real_index():
    """构建真实向量索引"""

    print("=" * 60)
    print("Building Real Vector Index with Local Embedding Model")
    print("=" * 60)

    # 1. 加载文档
    print("\n[Step 1/4] Loading documents...")
    data_dir = Path(__file__).parent / "data" / "documents"
    documents = load_documents(str(data_dir))

    if len(documents) == 0:
        print("[ERROR] No documents found!")
        return False

    # 2. 初始化本地embedding服务
    print("\n[Step 2/4] Initializing local embedding service...")
    # 使用本地下载的BERT模型
    model_path = Path(__file__).parent / "models" / "bert-base-uncased"
    embedding_service = LocalEmbeddingService(
        model_name=str(model_path)
    )
    print(f"[OK] Model dimension: {embedding_service.dimension}")

    # 3. 向量化所有文档
    print("\n[Step 3/4] Embedding documents...")
    texts = [doc.content for doc in documents]

    print(f"[INFO] Embedding {len(texts)} documents...")
    embeddings = embedding_service.embed(texts)
    print(f"[OK] Embeddings shape: {embeddings.shape}")

    # 4. 构建FAISS索引
    print("\n[Step 4/4] Building FAISS index...")
    vector_store = VectorStore(dimension=embedding_service.dimension)
    vector_store.build_index(documents, embeddings)

    # 5. 保存索引
    output_dir = Path(__file__).parent / "data"
    index_path = output_dir / "vector_index_local.faiss"
    meta_path = output_dir / "vector_meta_local.pkl"

    vector_store.save(str(index_path), str(meta_path))
    print(f"\n[OK] Index saved to:")
    print(f"  - {index_path}")
    print(f"  - {meta_path}")

    # 6. 验证索引
    print("\n[Validation] Testing index...")
    test_query = "游戏设计的核心要素"
    query_embedding = embedding_service.embed_single(test_query)
    results = vector_store.search(query_embedding, top_k=3)

    print(f"\nTest query: '{test_query}'")
    print(f"Top 3 results:")
    for i, (doc, score) in enumerate(results, 1):
        print(f"  {i}. [{doc.id}] {doc.title} (score: {score:.4f})")

    print("\n" + "=" * 60)
    print("[SUCCESS] Real vector index built successfully!")
    print("=" * 60)
    print(f"\nIndex stats:")
    print(f"  - Documents: {len(documents)}")
    print(f"  - Dimension: {embedding_service.dimension}")
    print(f"  - Model: {embedding_service.model_name}")
    print(f"  - Index type: FAISS IndexFlatIP")

    return True


if __name__ == "__main__":
    success = build_real_index()
    sys.exit(0 if success else 1)
