"""
端到端验证 /api/v1/context 核心逻辑
（不启动 Flask，直接测 Retriever.retrieve_context）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.retrieval import Retriever, LocalEmbeddingService, VectorStore
from core.models import ContextRequest
from core.patch_content_type import patch_vector_store

DOCS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'documents')
INDEX = os.path.join(os.path.dirname(__file__), 'data', 'vector_index_local.faiss')
META  = os.path.join(os.path.dirname(__file__), 'data', 'vector_meta_local.pkl')

print("=" * 60)
print("Step 1: 加载 embedding 模型")
emb = LocalEmbeddingService()

print("\nStep 2: 加载向量索引")
vs = VectorStore(dimension=emb.dimension)
vs.load(INDEX, META)
print(f"  loaded {len(vs.documents)} docs")

print("\nStep 3: patch content_type")
patch_vector_store(vs, DOCS_DIR)

# 验证 patch 结果
from collections import Counter
ct_dist = Counter(getattr(d, 'content_type', None) for d in vs.documents.values())
print("  分布:", dict(ct_dist))

retriever = Retriever(emb, vs)

print("\n" + "=" * 60)
print("Step 4: 测试 retrieve_context")

test_cases = [
    {
        "desc": "2.2 场景：查证「游戏AI商业化」假设",
        "req": ContextRequest(
            request_id="test_22_001",
            caller="phase2.2",
            query="AI NPC商业化推理成本是否已具备条件",
            needed_content_types=["market_data", "background"],
            top_k=4,
        )
    },
    {
        "desc": "2.1 场景：信号抽取辅助",
        "req": ContextRequest(
            request_id="test_21_001",
            caller="phase2.1",
            query="F2P游戏经济系统设计",
            needed_content_types=["constraint_rule", "background"],
            top_k=4,
        )
    },
    {
        "desc": "不限类型（needed_content_types 为空）",
        "req": ContextRequest(
            request_id="test_open_001",
            caller="phase2.3",
            query="独立游戏发行策略",
            needed_content_types=[],
            top_k=3,
        )
    },
]

for tc in test_cases:
    print(f"\n[{tc['desc']}]")
    resp = retriever.retrieve_context(tc['req'])
    print(f"  packets: {len(resp.context_packets)}  summary: {resp.retrieval_summary}")
    if resp.retrieval_notes:
        print(f"  notes: {resp.retrieval_notes}")
    for p in resp.context_packets:
        print(f"    [{p.content_type}] {p.source_id} score={p.score} trust={p.trust_level}")
        print(f"      reason: {p.reason_for_match[:90]}")

print("\n" + "=" * 60)
print("DONE")
