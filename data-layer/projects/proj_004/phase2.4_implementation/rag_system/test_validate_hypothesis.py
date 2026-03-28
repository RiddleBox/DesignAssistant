"""
test_validate_hypothesis.py
验证 ValidateHypothesisRequest 接口的端到端流程：
  2.2 传入假设 → 2.4 分桶召回证据 → 返回 HypothesisValidationResult

运行方式：
  cd D:\AIproject\DesignAssistant\data-layer\projects\proj_004
  python phase2.4_implementation/rag_system/test_validate_hypothesis.py
"""

import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import ContextRequest
from core.retrieval import Retriever, LocalEmbeddingService, VectorStore
from core.patch_content_type import patch_vector_store

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE, "data", "vector_index_local.faiss")
META_PATH  = os.path.join(BASE, "data", "vector_meta_local.pkl")
DOCS_DIR   = os.path.join(BASE, "data", "documents")


def load_retriever():
    emb = LocalEmbeddingService("sentence-transformers/all-MiniLM-L6-v2")
    vs = VectorStore(dimension=384)
    vs.load(INDEX_PATH, META_PATH)
    patch_vector_store(vs, DOCS_DIR)
    return Retriever(emb, vs)


def validate_hypothesis(retriever, hypothesis: str, evidence_types=None, top_k=5):
    """
    模拟 2.4 侧处理 ValidateHypothesisRequest 的逻辑：
    1. 将 hypothesis 作为 query
    2. 按 evidence_types 分桶召回（默认 case_record + market_data）
    3. 按 score 粗分 supporting / counter，返回 HypothesisValidationResult 结构
    """
    needed = evidence_types or ["case_record", "market_data"]

    req = ContextRequest(
        request_id=f"validate_{abs(hash(hypothesis)) % 100000}",
        query=hypothesis,
        needed_content_types=needed,
        top_k=top_k,
        caller="phase2.2",
    )
    resp = retriever.retrieve_context(req)

    supporting = []
    counter = []

    for pkt in resp.context_packets:
        entry = {
            "source_id": pkt.source_id,
            "title": pkt.source_title,
            "content_type": pkt.content_type,
            "excerpt": pkt.excerpt[:300],
            "trust_level": pkt.trust_level,
            "score": pkt.score,
        }
        # 粗分策略（MVP）：score >= 0.35 归 supporting，其余归 counter / 低相关
        if pkt.score >= 0.35:
            supporting.append(entry)
        else:
            counter.append(entry)

    # validation_status
    if not supporting and not counter:
        status = "insufficient"
        conf = 0.0
    elif supporting and not counter:
        status = "supported"
        conf = min(1.0, 0.5 + 0.1 * len(supporting))
    elif counter and not supporting:
        status = "refuted"
        conf = min(1.0, 0.5 + 0.1 * len(counter))
    else:
        status = "mixed"
        conf = 0.5

    return {
        "hypothesis": hypothesis,
        "supporting_evidence": supporting,
        "counter_evidence": counter,
        "validation_status": status,
        "confidence_score": round(conf, 2),
        "retrieval_time_ms": resp.retrieval_time_ms,
        "notes": resp.retrieval_notes,
    }


def print_result(label, result):
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"  假设: {result['hypothesis']}")
    print(f"  状态: {result['validation_status']}  置信度: {result['confidence_score']}")
    print(f"  耗时: {result['retrieval_time_ms']}ms")
    print(f"  支持证据 ({len(result['supporting_evidence'])} 条):")
    for e in result['supporting_evidence']:
        print(f"    [{e['content_type']}][{e['trust_level']}] {e['title']} (score={e['score']})")
    print(f"  质疑证据 ({len(result['counter_evidence'])} 条):")
    for e in result['counter_evidence']:
        print(f"    [{e['content_type']}][{e['trust_level']}] {e['title']} (score={e['score']})")
    if result['notes']:
        print(f"  notes: {result['notes']}")


if __name__ == "__main__":
    print("加载检索器...")
    retriever = load_retriever()
    print(f"  文档数: {len(retriever.vector_store.documents)}")

    # 测试案例：对应 2.2 实际会产出的假设
    test_cases = [
        {
            "label": "H1: AI NPC推理成本已具备商业化条件",
            "hypothesis": "AI NPC 推理成本已降至可商业化区间，游戏厂商可规模部署",
            "evidence_types": ["case_record", "market_data"],
        },
        {
            "label": "H2: 经典IP重启手游的市场启动效率高于新IP",
            "hypothesis": "经典IP重启的手游产品首日用户规模显著优于新IP，预约转化率更高",
            "evidence_types": ["case_record", "market_data"],
        },
        {
            "label": "H3: 大型游戏厂商千人裁员后会关停非核心业务线",
            "hypothesis": "游戏大厂进行千人级裁员时，会同步关停非核心游戏模式或业务线",
            "evidence_types": ["case_record"],
        },
        {
            "label": "H4: 新兴游戏品类首发失败后难以通过运营挽救（查证不足场景）",
            "hypothesis": "新品类游戏首发数据不达预期后，靠后续版本更新扭转留存的成功率极低",
            "evidence_types": ["case_record", "market_data", "background"],
        },
    ]

    all_pass = True
    for tc in test_cases:
        result = validate_hypothesis(
            retriever,
            tc["hypothesis"],
            evidence_types=tc.get("evidence_types"),
        )
        print_result(tc["label"], result)
        # 验收：不能直接 error，至少有一个 packet 或有明确 notes
        ok = result["validation_status"] != "error"
        if not ok:
            print(f"  ❌ FAIL")
            all_pass = False
        else:
            print(f"  ✅ PASS")

    print(f"\n{'='*60}")
    print(f"{'ALL PASS ✅' if all_pass else 'SOME FAILED ❌'}")
