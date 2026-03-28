"""
给已加载的索引补 content_type 字段
原理：pkl 里的 Document 对象没有 content_type（旧版），
从 yaml 文件重新读取该字段并 patch 到内存中的对象。

用法：
  from patch_content_type import patch_vector_store
  patch_vector_store(vector_store, docs_dir)
"""

import yaml
import os


def patch_vector_store(vector_store, docs_dir: str):
    """
    给 VectorStore 里已加载的 Document 对象补 content_type 字段

    Args:
        vector_store: 已加载的 VectorStore 实例
        docs_dir: yaml 文档目录路径
    """
    patched = 0
    missing = 0

    for doc_id, doc in vector_store.documents.items():
        yaml_path = os.path.join(docs_dir, f"{doc_id}.yaml")
        if not os.path.exists(yaml_path):
            missing += 1
            continue

        with open(yaml_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        ct = data.get('content_type', None)
        doc.content_type = ct
        if ct:
            patched += 1

    print(f"[patch] content_type 补标：{patched} 条有值，{missing} 条 yaml 不存在")
    return patched
