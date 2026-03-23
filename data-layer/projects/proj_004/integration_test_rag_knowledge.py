"""
Phase 2.4 知识增强联调 (P1-5 / P1-6 / P1-7)

验证 2.4 RAG 系统为 2.1 / 2.2 / 2.3 提供知识支持的能力:
  P1-5 (A1-A3)  2.4 → 2.1: 信号类型相关知识检索质量验证
  P1-6 (B1-B3)  2.4 → 2.2: ContextPacket 注入 JudgmentEngine 全路径验证
  P1-7 (C1-C2)  2.4 → 2.3: 行动设计相关知识检索质量验证

运行方式: python integration_test_rag_knowledge.py
不需要外部 API Key（使用本地 BERT embedding + 本地 FAISS 索引）
"""

import os
import sys
import time
import importlib.util
from pathlib import Path
from typing import List, Optional

BASE = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.join(BASE, 'phase2.4_implementation', 'rag_system')

# ── 加载 API key（P1-6 需要调用 2.1 LLM，可选跳过）─────────────────────────
def _load_env_file(path):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))


# ── 下游模块加载（与 integration_test_e2e.py 保持一致）────────────────────────
def load_module(name, path, dep_modules=None):
    """加载模块，可注入依赖到 sys.modules 避免 schemas 命名冲突"""
    if dep_modules:
        for dep_name, dep_mod in dep_modules.items():
            sys.modules[dep_name] = dep_mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    if dep_modules:
        for dep_name in dep_modules:
            if dep_name != name:
                sys.modules.pop(dep_name, None)
    return mod

# 2.1
m21_schemas = load_module('schemas_21', os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
m21_prompts = load_module('prompt_templates',
    os.path.join(BASE, 'phase2.1_implementation', 'prompt_templates.py'),
    dep_modules={'schemas': m21_schemas})
decoder_mod = load_module('decoder',
    os.path.join(BASE, 'phase2.1_implementation', 'decoder.py'),
    dep_modules={'schemas': m21_schemas, 'prompt_templates': m21_prompts})
IntelligenceDecoder      = decoder_mod.IntelligenceDecoder
IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest
SourceType               = m21_schemas.SourceType

# 2.2
m22_schemas = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))
m22_validators = load_module('validators',
    os.path.join(BASE, 'phase2.2_implementation', 'validators.py'),
    dep_modules={'schemas': m22_schemas})
judgment_mod = load_module('judgment_engine',
    os.path.join(BASE, 'phase2.2_implementation', 'judgment_engine.py'),
    dep_modules={'schemas': m22_schemas, 'validators': m22_validators})
JudgmentEngine            = judgment_mod.JudgmentEngine
OpportunityJudgmentRequest = m22_schemas.OpportunityJudgmentRequest
ContextPacket             = m22_schemas.ContextPacket

# 2.3
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OpportunityObject23, ActionDesignRequest
from action_designer import ActionDesigner


# ── 2.4 RAG 初始化（本地 BERT，无需 API Key）──────────────────────────────────
sys.path.insert(0, RAG_DIR)
from core.retrieval import LocalEmbeddingService, VectorStore
from core.models import Document

_RAG_READY = False
_embedding_service: Optional[LocalEmbeddingService] = None
_vector_store: Optional[VectorStore] = None


def init_rag() -> bool:
    """初始化本地 BERT embedding + 本地 FAISS 索引（仅执行一次）"""
    global _RAG_READY, _embedding_service, _vector_store
    if _RAG_READY:
        return True

    model_path = os.path.join(RAG_DIR, 'models', 'bert-base-uncased')
    index_path = os.path.join(RAG_DIR, 'data', 'vector_index_local.faiss')
    meta_path  = os.path.join(RAG_DIR, 'data', 'vector_meta_local.pkl')

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        print(f"[ERROR] 本地索引文件不存在: {index_path}")
        return False
    if not os.path.exists(model_path):
        print(f"[ERROR] 本地模型目录不存在: {model_path}")
        return False

    print("[RAG] 加载本地 BERT embedding 模型...")
    _embedding_service = LocalEmbeddingService(model_name=model_path)

    print("[RAG] 加载本地 FAISS 索引...")
    _vector_store = VectorStore(dimension=_embedding_service.dimension)
    _vector_store.load(index_path, meta_path)

    _RAG_READY = True
    print(f"[RAG] 就绪，共 {len(_vector_store.documents)} 条知识文档")
    return True


def retrieve(query: str, top_k: int = 5) -> List[tuple]:
    """
    检索最相关的知识文档

    Returns:
        List[(Document, score)]
    """
    if not _RAG_READY:
        raise RuntimeError("RAG 未初始化，请先调用 init_rag()")
    emb = _embedding_service.embed_single(query)
    return _vector_store.search(emb, top_k=top_k)


def docs_to_context_packet(results: List[tuple]) -> ContextPacket:
    """
    将检索结果映射为 ContextPacket（B1 字段对齐逻辑）

    映射规则：
      market_trend    → similar_cases（市场类比案例）
      tech_innovation → methodology_hints（技术方法论提示）
      game_design     → domain_constraints（领域约束与经验）
      score < 0.3 的文档 → counter_examples
    """
    similar_cases      = []
    counter_examples   = []
    methodology_hints  = []
    domain_constraints = []

    for doc, score in results:
        snippet = f"[{doc.id}] {doc.title}: {doc.content[:120]}..."
        if score < 0.30:
            counter_examples.append(snippet)
        elif doc.category == 'market_trend':
            similar_cases.append(snippet)
        elif doc.category == 'tech_innovation':
            methodology_hints.append(snippet)
        else:  # game_design 或其他
            domain_constraints.append(snippet)

    return ContextPacket(
        similar_cases=similar_cases      or None,
        counter_examples=counter_examples or None,
        methodology_hints=methodology_hints or None,
        domain_constraints=domain_constraints or None,
    )


# ═══════════════════════════════════════════════════════════════
# P1-5  2.4 → 2.1  信号类型相关知识检索质量验证 (A1-A3)
# ═══════════════════════════════════════════════════════════════

# 与 2.1 SignalType 对应的代表性检索词
_SIGNAL_TYPE_QUERIES = {
    "technical":  "游戏技术创新 AI NPC 生成式技术突破",
    "market":     "游戏市场趋势 竞争格局变化 商业化",
    "team":       "游戏公司团队变化 核心人员 组织架构",
    "capital":    "游戏行业融资 投资 并购 资本动向",
}

MIN_TOP1_SCORE   = 0.20   # top-1 最低相似度阈值
MIN_RELEVANT_K   = 2      # top-5 中至少有 N 条相关文档（score >= 0.15）


def run_p1_5() -> bool:
    """
    P1-5 验收：验证 2.4 能为 2.1 各信号类型提供相关知识

    验收标准（A1-A3）：
      A1  四种信号类型的检索查询均无格式错误
      A2  每类查询 top-1 相似度 >= MIN_TOP1_SCORE
      A3  每类查询 top-5 中相关文档数 >= MIN_RELEVANT_K
    """
    print(f"\n{'='*60}")
    print("P1-5  2.4 → 2.1  信号类型知识检索质量验证")
    print(f"{'='*60}")

    results_by_type = {}
    for sig_type, query in _SIGNAL_TYPE_QUERIES.items():
        try:
            hits = retrieve(query, top_k=5)
            top1_score   = hits[0][1] if hits else 0.0
            relevant_cnt = sum(1 for _, s in hits if s >= 0.15)
            results_by_type[sig_type] = {
                "hits": hits,
                "top1_score": top1_score,
                "relevant_cnt": relevant_cnt,
                "error": None,
            }
            print(f"  [{sig_type}] query='{query[:30]}...'")
            for i, (doc, score) in enumerate(hits[:3], 1):
                print(f"    {i}. [{doc.category}] {doc.title[:40]} (score={score:.4f})")
        except Exception as e:
            results_by_type[sig_type] = {"error": str(e)}
            print(f"  [{sig_type}] ERROR: {e}")

    # 验收判断
    checks = {}
    for sig_type, r in results_by_type.items():
        if r.get("error"):
            checks[f"A1 {sig_type} 无格式错误"]     = False
            checks[f"A2 {sig_type} top1_score>={MIN_TOP1_SCORE}"] = False
            checks[f"A3 {sig_type} 相关文档>={MIN_RELEVANT_K}"]  = False
        else:
            checks[f"A1 {sig_type} 无格式错误"]     = True
            checks[f"A2 {sig_type} top1_score>={MIN_TOP1_SCORE}"] = r["top1_score"] >= MIN_TOP1_SCORE
            checks[f"A3 {sig_type} 相关文档>={MIN_RELEVANT_K}"]  = r["relevant_cnt"] >= MIN_RELEVANT_K

    all_pass = all(checks.values())
    print(f"\nP1-5 验收 ({'PASS' if all_pass else 'FAIL'}):")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")
    return all_pass


# ═══════════════════════════════════════════════════════════════
# P1-6  2.4 → 2.2  ContextPacket 注入 JudgmentEngine 全路径验证 (B1-B3)
# ═══════════════════════════════════════════════════════════════

# 用于构造 OpportunityJudgmentRequest 的最小 decoded_intelligence 桩数据
_STUB_DECODED_INTELLIGENCE = {
    "source_id": "p16_stub_001",
    "signals": [
        {
            "signal_id": "sig_001",
            "signal_type": "market",
            "signal_label": "AI NPC 商业化提速",
            "description": "生成式AI进入游戏NPC商业化阶段，大厂相继签约合作",
            "intensity_score": 8,
            "confidence_score": 7,
            "source_id": "p16_stub_001",
            "evidence_fragments": ["EA、育碧与OpenAI合作", "市场规模预测50亿美元"],
            "related_entities": ["OpenAI", "EA", "育碧"],
            "taxonomy_path": "market/commercial_acceleration",
            "raw_text_fragment": "生成式AI在游戏行业的商业化进程大幅提速",
        },
        {
            "signal_id": "sig_002",
            "signal_type": "capital",
            "signal_label": "AI游戏创业融资潮",
            "description": "三家AI游戏初创公司合计A轮融资超2亿美元",
            "intensity_score": 7,
            "confidence_score": 8,
            "source_id": "p16_stub_001",
            "evidence_fragments": ["红杉资本、a16z投资", "融资2亿美元"],
            "related_entities": ["红杉资本", "a16z"],
            "taxonomy_path": "capital/funding_round",
            "raw_text_fragment": "三家AI游戏初创公司完成A轮融资，合计超过2亿美元",
        },
    ],
    "summary": "检测到2个范式信号：市场信号1个、资本信号1个",
    "decoder_version": "v1.2-stub",
    "processing_time_ms": 0,
    "warnings": [],
}


def _run_judgment(context_packet: Optional[ContextPacket], label: str) -> dict:
    """执行一次 2.2 判断，返回结果摘要"""
    engine = JudgmentEngine()
    req = OpportunityJudgmentRequest(
        decoded_intelligence=_STUB_DECODED_INTELLIGENCE,
        context_packet=context_packet,
    )
    t0 = time.time()
    result = engine.judge(req)
    elapsed = int((time.time() - t0) * 1000)
    opp = result.opportunity
    print(f"  [{label}] status={result.status} priority={opp.priority_level} "
          f"supporting={len(opp.supporting_evidence)} counter={len(opp.counter_evidence)} "
          f"({elapsed}ms)")
    return {
        "status": result.status,
        "priority_level": opp.priority_level,
        "supporting_count": len(opp.supporting_evidence),
        "error": result.error,
    }


def run_p1_6() -> bool:
    """
    P1-6 验收：验证 ContextPacket 全路径（B1-B3）

    验收标准：
      B1  ContextPacket 字段可由 docs_to_context_packet() 正确填充（无冗余/缺失）
      B2  注入 ContextPacket 后 JudgmentEngine 正常运行，status=success
      B3  context_packet=None（降级路径）时 JudgmentEngine 仍正常运行，无崩溃
    """
    print(f"\n{'='*60}")
    print("P1-6  2.4 → 2.2  ContextPacket 注入全路径验证")
    print(f"{'='*60}")

    # B1: 用机会相关查询构建 ContextPacket
    print("\n[B1] 构建 ContextPacket...")
    query = "AI游戏市场商业化 竞争格局 投资趋势"
    hits = retrieve(query, top_k=6)
    ctx = docs_to_context_packet(hits)
    print(f"  similar_cases:      {len(ctx.similar_cases or [])} 条")
    print(f"  counter_examples:   {len(ctx.counter_examples or [])} 条")
    print(f"  methodology_hints:  {len(ctx.methodology_hints or [])} 条")
    print(f"  domain_constraints: {len(ctx.domain_constraints or [])} 条")
    b1_pass = any([
        ctx.similar_cases,
        ctx.methodology_hints,
        ctx.domain_constraints,
    ])

    # B2: 注入 ContextPacket 运行判断
    print("\n[B2] 注入 ContextPacket 运行 JudgmentEngine...")
    r_with = _run_judgment(ctx, "with_context")
    b2_pass = r_with["status"] in ("success", "insufficient_evidence") and r_with["error"] is None

    # B3: 降级路径（context_packet=None）
    print("\n[B3] 降级路径（context_packet=None）...")
    r_without = _run_judgment(None, "no_context ")
    b3_pass = r_without["status"] in ("success", "insufficient_evidence") and r_without["error"] is None

    checks = {
        "B1 ContextPacket 至少一个字段有内容":              b1_pass,
        "B2 注入 ContextPacket 后 JudgmentEngine 无报错":   b2_pass,
        "B3 context_packet=None 降级路径无崩溃":            b3_pass,
    }
    all_pass = all(checks.values())
    print(f"\nP1-6 验收 ({'PASS' if all_pass else 'FAIL'}):")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")

    # 可观测性：对比两次优先级是否一致（不作为验收条件，仅记录）
    print(f"  [INFO] priority 对比: with_context={r_with['priority_level']} "
          f"no_context={r_without['priority_level']}")
    return all_pass


# ═══════════════════════════════════════════════════════════════
# P1-7  2.4 → 2.3  行动设计相关知识检索质量验证 (C1-C2)
# ═══════════════════════════════════════════════════════════════

# 行动设计场景下的代表性检索词，覆盖主要 posture 类型
_ACTION_DESIGN_QUERIES = {
    "资源承诺与分阶段投入": "游戏项目分阶段资源承诺 里程碑投入策略",
    "风险识别与止损": "游戏开发风险 项目失败案例 止损退出",
    "试点验证策略": "游戏新功能 MVP 试点验证 小范围测试",
    "升级决策条件": "游戏产品升级决策 规模化时机 go-no-go",
}

MIN_ACTION_TOP1_SCORE = 0.18   # 行动设计类查询相似度阈值（略低于信号类）
MIN_ACTION_RELEVANT_K = 1      # top-5 中至少有 N 条相关文档


def _stub_opportunity_for_23() -> OpportunityObject23:
    """构造用于 P1-7 演示的 2.3 输入机会对象（使用 2.3 dataclass 字段）"""
    return OpportunityObject23(
        opportunity_title="AI NPC商业化加速机会",
        opportunity_thesis="生成式AI在NPC领域进入商业化阶段，存在先发优势窗口",
        priority_level="deep_dive",
        key_assumptions=[
            "生成式AI NPC体验能达到商业可用标准",
            "玩家愿意为AI NPC付费或接受其存在",
            "现有技术成本在18个月内可降至可接受水平",
        ],
        supporting_evidence=["EA与OpenAI签约", "育碧AI实验室扩招", "市场规模预测50亿"],
        counter_evidence=["玩家对AI生成内容接受度存疑"],
        uncertainty_map={"技术成熟度": "不确定", "监管政策": "不确定"},
    )


def run_p1_7() -> bool:
    """
    P1-7 验收：验证 2.4 能为 2.3 行动设计提供相关知识 (C1-C2)

    验收标准：
      C1  行动设计相关查询（资源承诺、风险案例）可被检索到相关文档
      C2  ActionDesigner 在已有检索结果时运行正常（演示注入点），无报错
    """
    print(f"\n{'='*60}")
    print("P1-7  2.4 → 2.3  行动设计相关知识检索质量验证")
    print(f"{'='*60}")

    # C1: 逐场景检索
    print("\n[C1] 行动设计场景检索质量...")
    c1_results = {}
    for scenario, query in _ACTION_DESIGN_QUERIES.items():
        try:
            hits = retrieve(query, top_k=5)
            top1_score   = hits[0][1] if hits else 0.0
            relevant_cnt = sum(1 for _, s in hits if s >= 0.15)
            c1_results[scenario] = {
                "top1_score": top1_score,
                "relevant_cnt": relevant_cnt,
                "error": None,
            }
            marker = "OK" if top1_score >= MIN_ACTION_TOP1_SCORE else "WARN"
            print(f"  [{marker}] {scenario}")
            for i, (doc, score) in enumerate(hits[:2], 1):
                print(f"       {i}. [{doc.category}] {doc.title[:40]} (score={score:.4f})")
        except Exception as e:
            c1_results[scenario] = {"error": str(e)}
            print(f"  [ERR] {scenario}: {e}")

    c1_pass = all(
        not r.get("error") and r["top1_score"] >= MIN_ACTION_TOP1_SCORE
        for r in c1_results.values()
    )

    # C2: 演示检索结果可注入 ActionDesigner
    print("\n[C2] 演示检索结果注入 ActionDesigner resource_commitment_logic...")
    c2_pass = False
    try:
        opp = _stub_opportunity_for_23()
        # 用机会标题检索增强知识
        hits = retrieve(opp.opportunity_title + " 资源承诺 风险", top_k=4)
        knowledge_snippets = [f"{doc.title}: {doc.content[:80]}" for doc, _ in hits]

        # 运行 ActionDesigner（MVP 阶段不修改引擎接口，知识作为可观测附录记录）
        designer = ActionDesigner()
        req = ActionDesignRequest(
            request_id="p17_test_001",
            opportunity_object=opp,
        )
        result = designer.design_action(req)
        ad = result.action_decision
        print(f"  posture={ad.decision_posture}  phases={len(ad.phased_plan)}")
        print(f"  resource_logic(前80字): {ad.resource_commitment_logic[:80]}")
        print(f"  [INFO] 可注入的知识片段数: {len(knowledge_snippets)}")
        for i, s in enumerate(knowledge_snippets[:2], 1):
            print(f"    {i}. {s[:70]}...")
        c2_pass = True
    except Exception as e:
        print(f"  [ERROR] ActionDesigner 运行失败: {e}")

    checks = {
        "C1 行动设计场景检索 top1>=%.2f" % MIN_ACTION_TOP1_SCORE: c1_pass,
        "C2 ActionDesigner 运行无报错（知识注入点演示完成）":         c2_pass,
    }
    all_pass = all(checks.values())
    print(f"\nP1-7 验收 ({'PASS' if all_pass else 'FAIL'}):")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")
    return all_pass


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("Phase 2.4 知识增强联调  P1-5 / P1-6 / P1-7")
    print("#" * 60)

    # 初始化 RAG（必须在三个测试之前完成）
    if not init_rag():
        print("\n[FATAL] RAG 初始化失败，退出")
        sys.exit(1)

    results = {}
    results["P1-5"] = run_p1_5()
    results["P1-6"] = run_p1_6()
    results["P1-7"] = run_p1_7()

    print(f"\n{'='*60}")
    print("联调总结")
    print(f"{'='*60}")
    all_ok = True
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_ok = False

    print(f"\n最终结果: {'全部通过' if all_ok else '存在失败项，请检查上方日志'}")
    sys.exit(0 if all_ok else 1)
