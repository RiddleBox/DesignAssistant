"""
Iteration 3 批量真实样本运行脚本（RAG 集成版）

流程：
  incoming/*.json -> 2.1 解码 -> 2.2 机会判断（内部按需调用 2.4 RAG）-> 2.3 行动设计 -> 2.5 复盘
  处理完成后将样本移动到 processed/，避免重复处理

运行方式:
  python run_batch_real.py

依赖:
  在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 LLM 信息
"""

import os
import sys
import json
import time
import shutil
import importlib.util
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from datetime import datetime

# token 监控（可选，文件不存在时静默跳过）
try:
    _monitor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'token_monitor.py')
    _monitor_spec = importlib.util.spec_from_file_location('token_monitor', _monitor_path)
    _monitor_mod = importlib.util.module_from_spec(_monitor_spec)
    _monitor_spec.loader.exec_module(_monitor_mod)
    patch_decoder = _monitor_mod.patch_decoder
    show_token_summary = _monitor_mod.show_summary
except Exception:
    patch_decoder = lambda x: None
    show_token_summary = lambda: None

BASE = os.path.dirname(os.path.abspath(__file__))
LLM_CONFIG_PATH = os.path.join(BASE, "llm_config.py")
SAMPLES_ROOT = os.path.join(BASE, "..", "..", "..", "background", "real_intel_samples")
INCOMING_DIR = os.path.join(SAMPLES_ROOT, "incoming")
PROCESSED_DIR = os.path.join(SAMPLES_ROOT, "processed")
RUN_SUMMARY_PATH = os.path.join(BASE, "run_summary.json")
KEEP_INPUTS = os.environ.get("PHASE21_KEEP_INPUTS", "").strip().lower() in {"1", "true", "yes", "on"}
PHASE22_ONLY = os.environ.get("PHASE22_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
PHASE23_ONLY = os.environ.get("PHASE23_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}


def write_run_summary(summary: dict):
    payload = dict(summary or {})
    payload.setdefault("written_at", datetime.now().isoformat(timespec='seconds'))
    with open(RUN_SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_run_summary() -> dict:
    if not os.path.exists(RUN_SUMMARY_PATH):
        return {}
    try:
        with open(RUN_SUMMARY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def preserve_success_summary_on_no_input() -> bool:
    existing = read_run_summary()
    if existing.get("stage") == "done" and existing.get("status") == "success":
        existing["last_no_input_at"] = datetime.now().isoformat(timespec='seconds')
        existing["last_no_input_note"] = "incoming 目录为空，本次未执行；保留最近一次成功运行摘要"
        write_run_summary(existing)
        return True
    return False


def _load_env_file(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))


def load_module(name, path, dep_modules=None):
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


def load_llm_config(phase: str) -> dict:
    spec = importlib.util.spec_from_file_location("llm_config", LLM_CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["llm_config"] = mod
    spec.loader.exec_module(mod)
    return mod.get_llm_config(phase)


# 2.1
m21_schemas = load_module('schemas_21', os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
m21_prompts = load_module('prompt_templates',
    os.path.join(BASE, 'phase2.1_implementation', 'prompt_templates.py'),
    dep_modules={'schemas': m21_schemas})
decoder_mod = load_module('decoder',
    os.path.join(BASE, 'phase2.1_implementation', 'decoder.py'),
    dep_modules={'schemas': m21_schemas, 'prompt_templates': m21_prompts})
IntelligenceDecoder = decoder_mod.IntelligenceDecoder
IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest

# 2.2
m22_schemas = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))
m22_validators = load_module('validators',
    os.path.join(BASE, 'phase2.2_implementation', 'validators.py'),
    dep_modules={'schemas': m22_schemas})
judgment_mod = load_module('judgment_engine',
    os.path.join(BASE, 'phase2.2_implementation', 'judgment_engine.py'),
    dep_modules={'schemas': m22_schemas, 'validators': m22_validators})
JudgmentEngine = judgment_mod.JudgmentEngine
OpportunityJudgmentRequest = m22_schemas.OpportunityJudgmentRequest

# 2.3
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OppObj23, ActionDesignRequest
from action_designer import ActionDesigner


# 2.4 RAG (modules loaded lazily inside build_rag_retriever to avoid sys.path conflicts)
RAG_SYSTEM_DIR = os.path.join(BASE, 'phase2.4_implementation', 'rag_system')
_rag_available = None  # None = not yet checked
# 2.5
impl25_dir = os.path.join(BASE, 'phase2.5_implementation')
sys.path.insert(0, impl25_dir)
from schemas import SystemRetrospectiveRequest
from core import SystemRetrospectiveAnalyzer


def ensure_dirs():
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def list_incoming_json_files():
    files = []
    for name in os.listdir(INCOMING_DIR):
        if name.lower().endswith('.json'):
            files.append(os.path.join(INCOMING_DIR, name))
    files.sort()
    return files


def load_samples(file_paths):
    samples = []
    for fp in file_paths:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
        samples.append({
            'file_path': fp,
            'file_name': os.path.basename(fp),
            'payload': data,
        })
    return samples


def run_step1_decode(samples, llm_config_21):
    max_parallel_samples = max(1, int(llm_config_21.get("max_parallel_samples", 1) or 1))
    request_spacing_ms = max(0, int(llm_config_21.get("request_spacing_ms", 0) or 0))

    all_signals = []
    decode_results = []
    per_sample_stats = []

    print(f"\n{'='*60}")
    print("Step 1: 2.1 情报解码（批量真实样本）")
    print(f"  并发样本数: {max_parallel_samples}")
    if request_spacing_ms > 0:
        print(f"  提交错峰间隔: {request_spacing_ms}ms")
    print(f"{'='*60}")

    def _decode_single(item, order_index):
        p = item['payload']
        decoder = IntelligenceDecoder(
            api_key=llm_config_21.get("api_key", ""),
            model=llm_config_21.get("model", "claude-opus-4-6"),
            provider=llm_config_21.get("provider", "anthropic"),
            base_url=llm_config_21.get("base_url", ""),
            connect_timeout_seconds=llm_config_21.get("connect_timeout_seconds", 30),
            read_timeout_seconds=llm_config_21.get("read_timeout_seconds", 180),
            max_retries=llm_config_21.get("max_retries", 3),
            screen_provider=llm_config_21.get("screen_provider"),
            screen_model=llm_config_21.get("screen_model"),
            screen_api_key=llm_config_21.get("screen_api_key"),
            screen_base_url=llm_config_21.get("screen_base_url"),
        )
        patch_decoder(decoder)

        req = IntelligenceDecodeRequest(
            source_id=p['source_id'],
            source_type=p['source_type'],
            title=p.get('title'),
            content=p['content'],
            published_at=p.get('published_at'),
            source_name=p.get('source_name'),
            language=p.get('language', 'en'),
            mode=p.get('mode', 'prompt_first'),
        )

        started_at = time.time()
        print(f"\n  [{p['source_id']}] 解码中... ({item['file_name']})")
        try:
            result = decoder.decode(req)
            sig_count = len(result.signals)
            print(f"  [{p['source_id']}] 提取信号 {sig_count} 个，耗时 {result.processing_time_ms}ms")
            if result.warnings:
                for w in result.warnings:
                    print(f"    ! warning: {w}")
            for sig in result.signals:
                print(f"    - [{sig.signal_type.value}] {sig.signal_label} (强度={sig.intensity_score}, 置信={sig.confidence_score})")

            return {
                'order_index': order_index,
                'source_id': p['source_id'],
                'result': result,
                'signals_dump': [sig.model_dump() for sig in result.signals],
                'stat': {
                    'source_id': p['source_id'],
                    'file_name': item['file_name'],
                    'signal_count': sig_count,
                    'processing_time_ms': result.processing_time_ms,
                    'is_noise_like': sig_count == 0,
                    'warning_count': len(result.warnings or []),
                    'warnings': [str(w) for w in (result.warnings or [])],
                    'started_at': datetime.fromtimestamp(started_at).isoformat(timespec='seconds'),
                    'finished_at': datetime.now().isoformat(timespec='seconds'),
                },
            }
        except Exception as e:
            print(f"  [{p['source_id']}] ⚠️  解码失败，跳过：{e}")
            return {
                'order_index': order_index,
                'source_id': p['source_id'],
                'result': None,
                'signals_dump': [],
                'stat': {
                    'source_id': p['source_id'],
                    'file_name': item['file_name'],
                    'signal_count': 0,
                    'processing_time_ms': int((time.time() - started_at) * 1000),
                    'is_noise_like': True,
                    'warning_count': 0,
                    'warnings': [],
                    'error_type': type(e).__name__,
                    'error': str(e),
                    'started_at': datetime.fromtimestamp(started_at).isoformat(timespec='seconds'),
                    'finished_at': datetime.now().isoformat(timespec='seconds'),
                },
            }

    future_to_index = {}
    ordered_outputs = [None] * len(samples)
    with ThreadPoolExecutor(max_workers=max_parallel_samples) as executor:
        for idx, item in enumerate(samples):
            future = executor.submit(_decode_single, item, idx)
            future_to_index[future] = idx
            if request_spacing_ms > 0 and idx < len(samples) - 1:
                time.sleep(request_spacing_ms / 1000.0)

        for future in as_completed(future_to_index):
            output = future.result()
            ordered_outputs[output['order_index']] = output

    for output in ordered_outputs:
        if not output:
            continue
        if output['result'] is not None:
            decode_results.append(output['result'])
            all_signals.extend(output['signals_dump'])
        per_sample_stats.append(output['stat'])

    total = len(samples)
    with_signals = sum(1 for s in per_sample_stats if s['signal_count'] > 0)
    no_signals = total - with_signals
    error_count = sum(1 for s in per_sample_stats if s.get('error'))

    print(f"\n  >>> 样本总数: {total}")
    print(f"  >>> 有信号样本: {with_signals}")
    print(f"  >>> 无信号样本(噪音候选): {no_signals}")
    print(f"  >>> 解码失败样本: {error_count}")
    print(f"  >>> 信号池合计: {len(all_signals)}")

    return all_signals, decode_results, per_sample_stats



def build_rag_retriever():
    """构建 RAG 检索函数并返回。返回 (query: str) -> Optional[ContextPacket] 的可调用对象，
    供 JudgmentEngine 在 Step2 后按需调用。返回 None 表示 RAG 不可用。"""
    sep60 = "=" * 60
    print()
    print(sep60)
    print("Step 1.5: 2.4 RAG 检索器初始化")
    print(sep60)

    # Load RAG modules by file path to avoid 'core' namespace conflict with phase2.5
    try:
        _rag_core = os.path.join(RAG_SYSTEM_DIR, 'core')
        _models_mod = load_module('rag_core.models', os.path.join(_rag_core, 'models.py'))
        sys.modules['core.models'] = _models_mod
        _retrieval_mod = load_module('rag_core.retrieval', os.path.join(_rag_core, 'retrieval.py'),
                                     dep_modules={'rag_core.models': _models_mod})
        LocalEmbeddingService = _retrieval_mod.LocalEmbeddingService
        VectorStore = _retrieval_mod.VectorStore
        Retriever = _retrieval_mod.Retriever
    except Exception as _e:
        print(f"  [RAG] module load failed, skipping: {_e}")
        return None

    ContextPacket = m22_schemas.ContextPacket

    rag_data_dir = os.path.join(RAG_SYSTEM_DIR, "data")
    index_path = os.path.join(rag_data_dir, "vector_index_local.faiss")
    meta_path = os.path.join(rag_data_dir, "vector_meta_local.pkl")
    # index 为 384 维，使用 MiniLM（bert-base-uncased 路径不存在且维度不匹配）
    model_path = "sentence-transformers/all-MiniLM-L6-v2"

    if not os.path.exists(index_path):
        print("  [RAG] index file not found, skipping")
        return None

    try:
        emb_svc = LocalEmbeddingService(model_name=model_path)
        vs = VectorStore(dimension=emb_svc.dimension)
        vs.load(index_path, meta_path)
        retriever = Retriever(emb_svc, vs)
        print(f"  [RAG] 检索器就绪（{vs.index.ntotal} 条文档）")
    except Exception as _e:
        print(f"  [RAG] init exception, skipping: {_e}")
        return None

    def rag_retriever(query: str):
        """由 JudgmentEngine 在形成主题后按需调用。
        调用 retrieve_context() 获取结构化 ContextPacket（v1.0 协议），
        按 content_type 分桶召回，由 judgment_engine._extract_context_data() 消费。
        """
        try:
            print(f"  [RAG] 2.2 发起查询: {query[:80]}...")
            # 构造 ContextRequest（2.2 关心 case_record / market_data / few_shot_example）
            ContextRequest = _models_mod.ContextRequest
            req = ContextRequest(
                request_id=f"run_batch_{__import__('uuid').uuid4().hex[:8]}",
                caller="phase2.2",
                query=query,
                needed_content_types=["case_record", "market_data", "few_shot_example", "constraint_rule"],
                top_k=6,
            )
            ctx_response = retriever.retrieve_context(req)
            packets = ctx_response.context_packets if ctx_response else []
            if not packets:
                print("  [RAG] no context packets retrieved")
                return None
            print(f"  [RAG] 命中 {len(packets)} 条证据包（{ctx_response.retrieval_time_ms}ms）")
            for p in packets:
                print(f"    - [{p.content_type}][{p.trust_level}] {p.source_title}")
            if ctx_response.retrieval_notes:
                for note in ctx_response.retrieval_notes:
                    print(f"    [RAG note] {note}")
            # 将 2.4 ContextPacket 列表封装为 2.2 ContextPacket（packets 字段）
            m22_ContextPacketItem = m22_schemas.ContextPacketItem
            items = [
                m22_ContextPacketItem(
                    packet_id=p.packet_id,
                    source_id=p.source_id,
                    source_title=p.source_title,
                    content_type=p.content_type,
                    excerpt=p.excerpt,
                    reason_for_match=p.reason_for_match,
                    tags=list(p.tags) if p.tags else [],
                    trust_level=p.trust_level,
                    score=float(p.score),
                )
                for p in packets
            ]
            return ContextPacket(packets=items)
        except Exception as _e:
            print(f"  [RAG] query exception: {_e}")
            import traceback; traceback.print_exc()
            return None

    return rag_retriever


def run_step2_judgment(all_signals, sample_count, rag_retriever=None, api_key=None):
    print(f"\n{'='*60}")
    print("Step 2: 2.2 机会判断（聚合信号池）")
    # 2.2 的 api_key / provider / base_url 从 llm_config.yaml 读取，不依赖传入的 api_key
    # 传入的 api_key 是 Anthropic key（给 2.1 用的），2.2 可能配置了不同 provider
    print("  [2.2] LLM 判断模式已启用（配置见 llm_config.yaml phase 2.2）")
    if rag_retriever is not None:
        print("  [RAG] 检索器已就绪，将在形成判断主题后按需查询")
    print(f"{'='*60}")

    if len(all_signals) == 0:
        print("  无可用信号，跳过 2.2/2.3/2.5")
        return None

    merged_intelligence = {
        "source_id": f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "signals": all_signals,
        "summary": f"来自 {sample_count} 篇真实样本的信号聚合，共 {len(all_signals)} 个信号",
        "decoder_version": "v1.3",
        "processing_time_ms": 0,
        "warnings": [],
    }

    # api_key=None → JudgmentEngine 从 llm_config.yaml 读取 2.2 的 key/provider/base_url
    engine = JudgmentEngine(rag_retriever=rag_retriever, api_key=None)
    req = OpportunityJudgmentRequest(decoded_intelligences=[merged_intelligence])
    t0 = time.time()
    # Signal Store 编排入口（judge_with_signal_store 替代 judge）
    # 回退方法：将 try 块整体注释掉，改为 result = engine.judge(req)
    # 文档参考：phase2_plan/phase2.2_signal_store_设计方案_v2.md §3.3
    try:
        import sys as _sys, os as _os
        _impl_dir = _os.path.join(_os.path.dirname(__file__), "phase2.2_implementation")
        if _impl_dir not in _sys.path:
            _sys.path.insert(0, _impl_dir)
        from signal_store import SignalStore as _SignalStore
        _signal_store = _SignalStore()
        result = engine.judge_with_signal_store(req, signal_store=_signal_store)
    except Exception as _e:
        print(f"  [warn] judge_with_signal_store 失败，退化为 judge(): {_e}")
        result = engine.judge(req)

    if getattr(result, 'status', '') == 'error':
        print("  [warn] judge_with_signal_store 返回 error，退化为 judge()")
        result = engine.judge(req)

    if (not getattr(result, 'opportunities', None)) and sample_count <= 1:
        print("  [warn] 2.2 在单样本验证批次未形成机会，使用规则 fallback 继续验证下游链路")
        fallback_opportunities = engine._rule_engine_fallback(all_signals, context_packet=None)
        result = judgment_mod.OpportunityJudgmentResult(
            opportunities=fallback_opportunities,
            status="success" if fallback_opportunities else "insufficient_evidence",
            diagnostics=judgment_mod.Diagnostics(
                signal_count=len(all_signals),
                opportunity_count=len(fallback_opportunities),
                evidence_completeness=1.0 if fallback_opportunities else 0.0,
                boundary_warnings=["[fallback] run_batch_real_single_sample_rule_opportunity"],
            ),
        )
    elapsed = int((time.time() - t0) * 1000)

    # pending_signals：全为孤立信号，已写入 Signal Store，无机会产出
    if not result.opportunities:
        status = getattr(result, 'status', 'unknown')
        sig_count = result.diagnostics.signal_count if result.diagnostics else len(all_signals)
        print(f"  status:          {status}")
        print(f"  signal_count:    {sig_count} 条信号已写入 Signal Store，等待后续批次补全")
        print(f"  耗时:            {elapsed}ms")
        return result

    opp = result.opportunities[0]
    print(f"  status:          {result.status}")
    print(f"  priority_level:  {opp.priority_level}")
    print(f"  opportunity:     {opp.opportunity_title}")
    print(f"  thesis:          {opp.opportunity_thesis[:100]}...")
    print(f"  supporting:      {len(opp.supporting_evidence)} 条")
    print(f"  counter:         {len(opp.counter_evidence)} 条")
    print(f"  key_assumptions: {len(opp.key_assumptions)} 条")
    print(f"  耗时:            {elapsed}ms")

    return result


def run_step3_action(judgment_result, api_key=None):
    print(f"\n{'='*60}")
    print("Step 3: 2.3 行动设计")
    print(f"{'='*60}")

    opp22 = judgment_result.opportunities[0]
    opp23 = OppObj23(
        opportunity_title=opp22.opportunity_title,
        opportunity_thesis=opp22.opportunity_thesis,
        priority_level=opp22.priority_level,
        key_assumptions=opp22.key_assumptions,
        supporting_evidence=opp22.supporting_evidence,
        counter_evidence=opp22.counter_evidence,
        uncertainty_map={u: "不确定" for u in opp22.uncertainty_map},
        why_now=getattr(opp22, "why_now", None),
        warnings=getattr(opp22, "warnings", None),
        next_validation_questions=getattr(opp22, "next_validation_questions", None),
    )

    designer = ActionDesigner(api_key=api_key)
    req = ActionDesignRequest(request_id=f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}", opportunity_object=opp23)
    result = designer.design_action(req)
    ad = result.action_decision

    print(f"  posture:          {ad.decision_posture}")
    print(f"  why:              {ad.why_this_posture[:100]}...")
    print(f"  phases:           {len(ad.phased_plan)} 个阶段")
    for i, ph in enumerate(ad.phased_plan, 1):
        print(f"    阶段{i}: {ph.stage} — {ph.objective[:60]}")
    print(f"  top_risks:        {len(ad.top_risks)} 条")

    return result


def _collect_run_errors(judgment_result, action_result) -> list:
    """收集 2.2/2.3 fallback 信息作为 workflow 错误记录"""
    errors = []
    if judgment_result:
        opp = judgment_result.opportunities[0] if judgment_result.opportunities else None
        if opp:
            warnings = getattr(opp, "warnings", []) or []
            for w in warnings:
                if "[fallback]" in str(w):
                    errors.append({"module": "2.2", "type": "llm_fallback", "detail": str(w)})
    if action_result:
        act = getattr(action_result, "action_decision", None)
        why_this_posture = str(getattr(act, "why_this_posture", "") or "") if act else ""
        if act and (("[fallback]" in why_this_posture) or getattr(act, "debate_summary", None) is None):
            errors.append({"module": "2.3", "type": "llm_fallback", "detail": "[fallback] 2.3 LLM 未跑通，由规则引擎生成"})
    return errors


def build_run_summary(*, stage: str, status: str, sample_count: int, signal_count: int = 0,
                      judgment_result=None, action_result=None, retro_result=None,
                      moved_count: int = 0, total_ms: int = 0, report_path: str = None,
                      note: str = "", error: str = "", run_id: str = "", source_ids: list = None) -> dict:
    summary = {
        "stage": stage,
        "status": status,
        "sample_count": sample_count,
        "signal_count": signal_count,
        "moved_count": moved_count,
        "total_ms": total_ms,
        "report_path": report_path,
        "note": note,
        "error": error,
    }

    if run_id:
        summary["run_id"] = run_id
    if source_ids:
        summary["source_ids"] = list(source_ids)

    if judgment_result is not None:
        summary["judgment_status"] = getattr(judgment_result, "status", "unknown")
        diag = getattr(judgment_result, "diagnostics", None)
        if diag is not None:
            summary["judgment_signal_count"] = getattr(diag, "signal_count", signal_count)
            summary["judgment_opportunity_count"] = getattr(diag, "opportunity_count", 0)
        if getattr(judgment_result, "opportunities", None):
            opp = judgment_result.opportunities[0]
            warnings = [str(w) for w in (getattr(opp, "warnings", []) or [])]
            summary["opportunity"] = {
                "title": getattr(opp, "opportunity_title", ""),
                "priority_level": str(getattr(opp, "priority_level", "")),
                "warnings": warnings,
                "llm_used": not any("[fallback]" in w for w in warnings),
            }

    if action_result is not None:
        act = getattr(action_result, "action_decision", None)
        if act is not None:
            why_this_posture = str(getattr(act, "why_this_posture", "") or "")
            summary["action"] = {
                "posture": str(getattr(act, "decision_posture", "")),
                "llm_used": ("[fallback]" not in why_this_posture) and (getattr(act, "debate_summary", None) is not None),
            }

    if retro_result is not None and getattr(retro_result, "retrospective", None) is not None:
        retro = retro_result.retrospective
        summary["retrospective"] = {
            "critical_findings": len(getattr(retro, "critical_findings", []) or []),
            "phase3_priorities": len(getattr(retro, "phase3_priorities", []) or []),
        }

    return summary


def attach_per_sample_stats(summary: dict, per_sample_stats: list) -> dict:
    payload = dict(summary or {})
    payload["per_sample_stats"] = list(per_sample_stats or [])
    payload["keep_inputs"] = KEEP_INPUTS
    return payload


def run_step4_retro(judgment_result, action_result, decode_results, per_sample_stats, rag_retriever=None, t_start=None,
                   run_id: str = ""):
    print(f"\n{'='*60}")
    print("Step 4: 2.5 整合复盘（LLM 语义归因）")
    print(f"{'='*60}")

    opp = judgment_result.opportunities[0]
    ad = action_result.action_decision
    workflow_run_id = run_id or f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ── phase2_1：完整信号列表（decoded_intelligences 字段名对齐）
    all_signals_dump = []
    for r in decode_results:
        for s in r.signals:
            all_signals_dump.append(s.model_dump())

    phase2_1_payload = {
        "source_ids": [r.source_id for r in decode_results],
        "sample_stats": per_sample_stats,
        "total_signals": len(all_signals_dump),
        "decoded_intelligences": all_signals_dump,          # LLMAttributor 期望的字段名
        "signals": all_signals_dump,                        # 兼容旧代码
        "signals_sample": [r.signals[0].model_dump() for r in decode_results if r.signals],
    }

    # ── phase2_2：完整机会对象（直接 model_dump，保留所有字段）
    phase2_2_payload = opp.model_dump()

    # ── phase2_3：完整行动对象
    import dataclasses as _dc
    def _to_dict(obj):
        """dataclass / pydantic / dict 统一转 dict"""
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if _dc.is_dataclass(obj) and not isinstance(obj, type):
            return _dc.asdict(obj)
        if isinstance(obj, dict):
            return obj
        return str(obj)

    phase2_3_payload = {
        "decision_posture": ad.decision_posture,
        "posture_rationale": ad.why_this_posture or "",
        "why_this_posture": ad.why_this_posture or "",
        "phased_plan": [_to_dict(s) for s in ad.phased_plan] if ad.phased_plan else [],
        "go_no_go_criteria": {
            "go_conditions": [
                c for s in (ad.phased_plan or [])
                for c in (s.go_no_go_criteria or [])
            ]
        },
        "exit_conditions": ad.exit_conditions if hasattr(ad, "exit_conditions") else [],
        "resource_commitment": ad.resource_commitment_logic or "",
        "resource_commitment_logic": ad.resource_commitment_logic or "",
        "top_risks": [_to_dict(r) for r in (ad.top_risks or [])],
    }

    # ── phase2_4：RAG 检索结果（如有）
    phase2_4_payload = {}
    if rag_retriever is not None:
        try:
            import importlib, sys as _sys
            _rag_path = os.path.join(os.path.dirname(__file__), "phase2.4_implementation", "rag_system", "core")
            if _rag_path not in _sys.path:
                _sys.path.insert(0, _rag_path)
            _models = importlib.import_module("models")
            ContextRequest = _models.ContextRequest
            ctx_req = ContextRequest(
                request_id="retro_ctx",
                caller="phase2.5",
                query=opp.opportunity_title or "",
                needed_content_types=[],
                top_k=5,
            )
            ctx_resp = rag_retriever.retrieve_context(ctx_req)
            phase2_4_payload = {
                "context_packets": [p.model_dump() if hasattr(p, "model_dump") else p for p in (ctx_resp.packets or [])],
                "retrieval_notes": ctx_resp.retrieval_notes if hasattr(ctx_resp, "retrieval_notes") else "",
                "packets_count": len(ctx_resp.context_packets or []),
            }
        except Exception as e:
            phase2_4_payload = {"retrieval_notes": f"RAG fallback: {e}", "packets_count": 0}
    else:
        phase2_4_payload = {"retrieval_notes": "RAG retriever 未传入，跳过", "packets_count": 0}

    req = SystemRetrospectiveRequest(
        request_id=f"real_batch_retro_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        case_id="real_intel_batch",
        workflow_run_record={
            "run_id": workflow_run_id,
            "case_description": "真实样本批量运行（incoming -> 2.1 -> 2.2 -> 2.3）",
            "modules_executed": ["2.1", "2.2", "2.3"],
            "sample_count": len(per_sample_stats),
            "signal_count": len(all_signals_dump),
            "noise_like_count": sum(1 for s in per_sample_stats if s.get('signal_count', 0) == 0),
            "processing_time_ms": int((time.time() - t_start) * 1000) if t_start else 0,
            "errors": _collect_run_errors(judgment_result, action_result),
            "source_ids": [r.source_id for r in decode_results],
        },
        upstream_outputs={
            "phase2_1": phase2_1_payload,
            "phase2_2": phase2_2_payload,
            "phase2_3": phase2_3_payload,
            "phase2_4": phase2_4_payload,
        },
    )

    analyzer = SystemRetrospectiveAnalyzer()
    result = analyzer.analyze(req)
    retro = result.retrospective

    print(f"  workflow_summary:   {retro.workflow_summary[:100]}...")
    print(f"  critical_findings:  {len(retro.critical_findings)} 条")
    for f in retro.critical_findings[:3]:
        print(f"    [{f.severity.value.upper()}][{f.layer.value}] {f.summary[:80]}")
    print(f"  root_causes:        {len(retro.suspected_root_causes)} 条")
    print(f"  phase3_priorities:  {len(retro.phase3_priorities)} 条")

    return result


def move_to_processed(samples):
    if KEEP_INPUTS:
        print("  [debug] PHASE21_KEEP_INPUTS 已开启，保留 incoming/ 样本不搬运")
        return 0

    moved = 0
    skipped = 0
    for item in samples:
        src = item['file_path']
        dst = os.path.join(PROCESSED_DIR, item['file_name'])

        if os.path.exists(dst):
            os.remove(src)
            skipped += 1
        else:
            shutil.move(src, dst)
            moved += 1

    if skipped:
        print(f"  (跳过 {skipped} 个 processed/ 中已存在的文件)")
    return moved


def main():
    ensure_dirs()

    llm_config_21 = load_llm_config("2.1")
    if not llm_config_21.get("api_key"):
        print("ERROR: 未找到 phase 2.1 的 LLM API key")
        print("请在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 api_key")
        sys.exit(1)

    incoming_files = list_incoming_json_files()
    if not incoming_files:
        print(f"INFO: incoming 目录无待处理样本: {INCOMING_DIR}")
        print("      请将 openclaw 输出的 JSON 放入 incoming/ 后再运行。")
        if preserve_success_summary_on_no_input():
            print("      已保留最近一次成功运行摘要，未覆盖为 no_input。")
        else:
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="init",
                status="no_input",
                sample_count=0,
                note="incoming 目录为空，无待处理样本",
            ), per_sample_stats=[]))
        return

    print(f"2.1 provider: {llm_config_21.get('provider', 'anthropic')}")
    print(f"incoming 样本数: {len(incoming_files)}")

    t_total = time.time()
    samples = load_samples(incoming_files)
    current_run_id = f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    all_signals = []
    decode_results = []
    per_sample_stats = []
    judgment_result = None
    action_result = None
    retro_result = None
    report_path = None
    moved_count = 0
    source_ids = [str(s.get('payload', {}).get('source_id', s.get('file_name', ''))) for s in samples]

    try:
        all_signals, decode_results, per_sample_stats = run_step1_decode(samples, llm_config_21)

        # api123.icu 限流缓解：2.1 批量调用完后等待，避免 2.2/2.3 撞上限流窗口
        cooldown = llm_config_21.get("step1_cooldown_seconds")
        if cooldown is None or cooldown == "":
            cooldown = 15 * len(samples)
        cooldown = max(0, int(cooldown))
        print(f"\n[冷却] 等待 {cooldown}s 让中转代理限流窗口重置...")
        time.sleep(cooldown)

        rag_retriever = build_rag_retriever()
        judgment_result = run_step2_judgment(all_signals, len(samples), rag_retriever, llm_config_21.get("api_key"))
        if judgment_result is None:
            moved_count = move_to_processed(samples)
            print(f"\n全部样本无信号，已移动 {moved_count} 个文件到 processed/")
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="2.1",
                status="no_signals",
                sample_count=len(samples),
                signal_count=len(all_signals),
                moved_count=moved_count,
                total_ms=int((time.time() - t_total) * 1000),
                note="2.1 未产出可用信号，跳过 2.2/2.3/2.5",
                run_id=current_run_id,
                source_ids=source_ids,
            ), per_sample_stats))
            return

        if not judgment_result.opportunities:
            # pending_signals：信号存在但全为孤立信号，已写入 Signal Store 等待后续批次补全
            status = getattr(judgment_result, 'status', 'unknown')
            sig_count = judgment_result.diagnostics.signal_count if judgment_result.diagnostics else len(all_signals)
            print(f"\n[本批次] 状态: {status}")
            print(f"  {sig_count} 条信号已写入 Signal Store，等待后续批次补全组合条件")
            print(f"  跳过 2.3 行动设计 / 2.5 复盘")
            moved_count = move_to_processed(samples)
            print(f"  样本已移动: {moved_count} 个 -> processed/")
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="2.2",
                status=status,
                sample_count=len(samples),
                signal_count=len(all_signals),
                judgment_result=judgment_result,
                moved_count=moved_count,
                total_ms=int((time.time() - t_total) * 1000),
                note="2.2 未形成机会对象，已提前结束",
                run_id=current_run_id,
                source_ids=source_ids,
            ), per_sample_stats))
            return

        if PHASE22_ONLY:
            total_ms = int((time.time() - t_total) * 1000)
            print("\n[debug] PHASE22_ONLY 已开启，2.2 完成后提前结束")
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="2.2",
                status="success",
                sample_count=len(samples),
                signal_count=len(all_signals),
                judgment_result=judgment_result,
                moved_count=0,
                total_ms=total_ms,
                note="PHASE22_ONLY 调试模式：仅运行到 2.2",
                run_id=current_run_id,
                source_ids=source_ids,
            ), per_sample_stats))
            return

        action_result = run_step3_action(judgment_result)
        if PHASE23_ONLY:
            total_ms = int((time.time() - t_total) * 1000)
            print("\n[debug] PHASE23_ONLY 已开启，2.3 完成后提前结束")
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="2.3",
                status="success",
                sample_count=len(samples),
                signal_count=len(all_signals),
                judgment_result=judgment_result,
                action_result=action_result,
                moved_count=0,
                total_ms=total_ms,
                note="PHASE23_ONLY 调试模式：仅运行到 2.3",
                run_id=current_run_id,
                source_ids=source_ids,
            ), per_sample_stats))
            return
        retro_result = run_step4_retro(judgment_result, action_result, decode_results, per_sample_stats, rag_retriever=rag_retriever, t_start=t_total, run_id=current_run_id)

        moved_count = move_to_processed(samples)
        total_ms = int((time.time() - t_total) * 1000)

        # 生成 Markdown 报告
        try:
            from report_writer import generate_report
            report_path = generate_report(
                judgment_result=judgment_result,
                action_result=action_result,
                retro_result=retro_result,
                decode_results=decode_results,
                sample_count=len(samples),
                signal_count=len(all_signals),
                total_ms=total_ms,
                run_timestamp=datetime.now(),
                run_id=current_run_id,
                source_ids=source_ids,
            )
            print(f"  报告已生成:    {report_path}")
        except Exception as e:
            print(f"  报告生成失败:  {e}")
            write_run_summary(attach_per_sample_stats(build_run_summary(
                stage="report",
                status="report_failed",
                sample_count=len(samples),
                signal_count=len(all_signals),
                judgment_result=judgment_result,
                action_result=action_result,
                retro_result=retro_result,
                moved_count=moved_count,
                total_ms=total_ms,
                note="主流程成功，但报告生成失败",
                error=str(e),
                run_id=current_run_id,
                source_ids=source_ids,
            ), per_sample_stats))
            raise

        print(f"\n{'#'*60}")
        print(f"Iteration 1 批量运行完成，总耗时 {total_ms}ms")
        print(f"  样本数:        {len(samples)}")
        print(f"  信号池:        {len(all_signals)}")
        print(f"  机会判断:      {judgment_result.opportunities[0].priority_level} / {judgment_result.opportunities[0].opportunity_title}")
        print(f"  行动姿态:      {action_result.action_decision.decision_posture}")
        print(f"  复盘输出:      findings={len(retro_result.retrospective.critical_findings)}, priorities={len(retro_result.retrospective.phase3_priorities)}")
        print(f"  文件移动:      {moved_count} -> processed/")
        print(f"{'#'*60}")
        write_run_summary(attach_per_sample_stats(build_run_summary(
            stage="done",
            status="success",
            sample_count=len(samples),
            signal_count=len(all_signals),
            judgment_result=judgment_result,
            action_result=action_result,
            retro_result=retro_result,
            moved_count=moved_count,
            total_ms=total_ms,
            report_path=report_path,
            note="全链路运行完成",
            run_id=current_run_id,
            source_ids=source_ids,
        ), per_sample_stats))
        show_token_summary()
    except Exception as e:
        total_ms = int((time.time() - t_total) * 1000)
        write_run_summary(attach_per_sample_stats(build_run_summary(
            stage="exception",
            status="failed",
            sample_count=len(samples),
            signal_count=len(all_signals),
            judgment_result=judgment_result,
            action_result=action_result,
            retro_result=retro_result,
            moved_count=moved_count,
            total_ms=total_ms,
            report_path=report_path,
            note="运行过程中发生未捕获异常",
            error=f"{type(e).__name__}: {e}",
            run_id=current_run_id,
            source_ids=source_ids,
        ), per_sample_stats))
        raise


if __name__ == "__main__":
    main()
