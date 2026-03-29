"""
pipeline_runner.py
将 run_batch_real.py 的各步骤包装为 generator，
每步完成后 yield 一个结构化事件供 dashboard 实时展示。

事件格式：
{
    "type": "step_start" | "step_done" | "log" | "error" | "pipeline_done",
    "step": "2.1" | "2.2" | "2.3" | "2.4" | "2.5" | None,
    "data": { ... }   # 步骤专属数据
    "message": str    # 人类可读摘要
}
"""

import sys
import os
import time
import traceback
from datetime import datetime
from typing import Generator

# 确保项目路径可访问
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ_DIR)
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.1_implementation"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.2_implementation"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.3_implementation", "src"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.5_implementation"))

INCOMING_DIR = os.path.join(
    os.path.dirname(PROJ_DIR), "..", "background", "real_intel_samples", "incoming"
)
INCOMING_DIR = os.path.normpath(
    os.path.join(PROJ_DIR, "..", "..", "background", "real_intel_samples", "incoming")
)


def _event(type_, step, message, data=None):
    return {"type": type_, "step": step, "message": message, "data": data or {}}


def run_pipeline(api_key: str, base_url: str, model: str) -> Generator[dict, None, None]:
    """
    主 generator：按顺序执行各 step，每步完成后 yield 事件。
    调用方用 for event in run_pipeline(...): 消费。
    """
    # ── 设置环境变量（各模块从 os.environ 读取）
    os.environ["ANTHROPIC_API_KEY"] = api_key
    os.environ["ANTHROPIC_BASE_URL"] = base_url.rstrip("/")

    t_total = time.time()

    # ── 扫描 incoming/
    yield _event("log", None, f"扫描 incoming/ 目录…")
    try:
        from run_batch_real import (
            load_samples,
            run_step1_decode,
            run_step2_judgment,
            run_step3_action,
            run_step4_retro,
            build_rag_retriever,
            move_to_processed,
        )
        import glob, json as _json

        incoming_files = sorted(glob.glob(os.path.join(INCOMING_DIR, "*.json")))
        if not incoming_files:
            yield _event("error", None, "incoming/ 目录为空，请先放入样本文件", {})
            return

        yield _event("log", None, f"发现 {len(incoming_files)} 个样本文件")
        samples = load_samples(incoming_files)
    except Exception as e:
        yield _event("error", None, f"初始化失败：{e}", {"traceback": traceback.format_exc()})
        return

    # ── Step 1：2.1 情报解码
    yield _event("step_start", "2.1", "2.1 情报解码 开始…")
    t1 = time.time()
    try:
        all_signals, decode_results, per_sample_stats = run_step1_decode(samples, api_key)

        # 组装展示数据
        samples_data = []
        for stat in per_sample_stats:
            sid = stat.get("source_id", "?")
            sigs = stat.get("signals", stat.get("signal_count", 0))
            sig_count = len(sigs) if isinstance(sigs, list) else sigs
            # 找对应 decode_result
            dr = next((d for d in decode_results if d.get("source_id") == sid), {})
            signals_detail = dr.get("signals", [])
            samples_data.append({
                "source_id": sid,
                "file_name": stat.get("file_name", sid),
                "signal_count": sig_count,
                "signals": signals_detail,
                "is_noise": sig_count == 0,
            })

        elapsed = int((time.time() - t1) * 1000)
        yield _event("step_done", "2.1", f"2.1 完成：{len(all_signals)} 个信号，耗时 {elapsed}ms", {
            "samples": samples_data,
            "signal_total": len(all_signals),
            "noise_count": sum(1 for s in samples_data if s["is_noise"]),
            "elapsed_ms": elapsed,
        })
    except Exception as e:
        yield _event("error", "2.1", f"2.1 失败：{e}", {"traceback": traceback.format_exc()})
        return

    # 冷却
    cooldown = 15 * len(samples)
    yield _event("log", None, f"限流冷却 {cooldown}s…")
    time.sleep(cooldown)

    # ── Step 1.5：2.4 RAG 初始化
    yield _event("step_start", "2.4", "2.4 RAG 检索器初始化…")
    t4 = time.time()
    rag_retriever = None
    try:
        rag_retriever = build_rag_retriever()
        elapsed4 = int((time.time() - t4) * 1000)
        doc_count = 0
        if rag_retriever and hasattr(rag_retriever, "vector_store"):
            doc_count = len(getattr(rag_retriever.vector_store, "documents", {}))
        yield _event("log", "2.4", f"RAG 就绪（{doc_count} 条文档，{elapsed4}ms）")
    except Exception as e:
        yield _event("log", "2.4", f"RAG 初始化失败，将 fallback：{e}")

    # ── Step 2：2.2 机会判断
    yield _event("step_start", "2.2", "2.2 机会判断 开始…")
    t2 = time.time()
    try:
        judgment_result = run_step2_judgment(all_signals, len(samples), rag_retriever, api_key)
        elapsed2 = int((time.time() - t2) * 1000)

        if judgment_result is None:
            yield _event("step_done", "2.2", "无有效信号，跳过后续步骤", {"no_signal": True})
            move_to_processed(samples)
            yield _event("pipeline_done", None, "运行完成（无信号样本已归档）", {"total_ms": int((time.time()-t_total)*1000)})
            return

        opp = judgment_result.opportunities[0] if judgment_result.opportunities else None
        opp_data = {}
        if opp:
            llm_used = not bool(getattr(opp, "warnings", None) and
                                any("[fallback]" in str(w) for w in (getattr(opp, "warnings", []) or [])))
            opp_data = {
                "title": getattr(opp, "opportunity_title", "") or getattr(opp, "title", ""),
                "thesis": getattr(opp, "opportunity_thesis", "") or getattr(opp, "thesis", ""),
                "priority_level": str(getattr(opp, "priority_level", "")),
                "llm_used": llm_used,
                "supporting_evidence": _serialize_list(getattr(opp, "supporting_evidence", [])),
                "counter_evidence": _serialize_list(getattr(opp, "counter_evidence", [])),
                "key_assumptions": _serialize_list(getattr(opp, "key_assumptions", [])),
                "why_now": getattr(opp, "why_now", ""),
                "uncertainty_map": _serialize_list(getattr(opp, "uncertainty_map", [])),
                "next_validation_questions": _serialize_list(getattr(opp, "next_validation_questions", [])),
                "warnings": [str(w) for w in (getattr(opp, "warnings", []) or [])],
            }

        # RAG 证据包（从 judgment_result 取）
        rag_packets = []
        if hasattr(judgment_result, "rag_context") and judgment_result.rag_context:
            rag_packets = _serialize_rag_packets(judgment_result.rag_context)

        yield _event("step_done", "2.2", f"2.2 完成：{opp_data.get('title','')}，耗时 {elapsed2}ms", {
            "opportunity": opp_data,
            "rag_packets": rag_packets,
            "elapsed_ms": elapsed2,
        })
    except Exception as e:
        yield _event("error", "2.2", f"2.2 失败：{e}", {"traceback": traceback.format_exc()})
        return

    # ── Step 3：2.3 行动设计
    yield _event("step_start", "2.3", "2.3 行动设计 开始…")
    t3 = time.time()
    try:
        action_result = run_step3_action(judgment_result, api_key=api_key)
        elapsed3 = int((time.time() - t3) * 1000)

        act = getattr(action_result, "action_decision", None)
        act_data = {}
        if act:
            debate = getattr(act, "debate_summary", None)
            llm_used = debate is not None
            act_data = {
                "posture": str(getattr(act, "decision_posture", "")),
                "why": getattr(act, "posture_rationale", ""),
                "llm_used": llm_used,
                "debate_summary": _serialize_debate(debate),
                "phases": _serialize_list(getattr(act, "phased_plan", [])),
                "top_risks": _serialize_list(getattr(act, "top_risks", [])),
                "exit_conditions": _serialize_list(getattr(act, "exit_conditions", [])),
                "go_no_go_criteria": _serialize_list(getattr(act, "go_no_go_criteria", [])),
            }

        yield _event("step_done", "2.3", f"2.3 完成：姿态={act_data.get('posture','')}，耗时 {elapsed3}ms", {
            "action": act_data,
            "elapsed_ms": elapsed3,
        })
    except Exception as e:
        yield _event("error", "2.3", f"2.3 失败：{e}", {"traceback": traceback.format_exc()})
        return

    # ── Step 4：2.5 复盘归因
    yield _event("step_start", "2.5", "2.5 复盘归因 开始…")
    t5 = time.time()
    try:
        retro_result = run_step4_retro(
            judgment_result, action_result, decode_results, per_sample_stats,
            rag_retriever=rag_retriever, t_start=t_total
        )
        elapsed5 = int((time.time() - t5) * 1000)

        retro = retro_result.retrospective
        retro_data = {
            "workflow_summary": getattr(retro, "workflow_summary", ""),
            "critical_findings": _serialize_findings(getattr(retro, "critical_findings", [])),
            "suspected_root_causes": _serialize_list(getattr(retro, "suspected_root_causes", [])),
            "phase3_priorities": _serialize_list(getattr(retro, "phase3_priorities", [])),
        }

        yield _event("step_done", "2.5", f"2.5 完成：findings={len(retro_data['critical_findings'])}，耗时 {elapsed5}ms", {
            "retrospective": retro_data,
            "elapsed_ms": elapsed5,
        })
    except Exception as e:
        yield _event("error", "2.5", f"2.5 失败：{e}", {"traceback": traceback.format_exc()})
        return

    # ── 生成报告 + 归档
    report_path = None
    try:
        from report_writer import generate_report
        opp_obj = judgment_result.opportunities[0] if judgment_result.opportunities else None
        act_obj = getattr(action_result, "action_decision", None)
        report_path = generate_report(
            opportunity=opp_obj,
            action=act_obj,
            retrospective=retro_result.retrospective,
            run_timestamp=datetime.now(),
            total_ms=int((time.time() - t_total) * 1000),
        )
    except Exception as e:
        yield _event("log", None, f"报告生成失败（不影响主流程）：{e}")

    move_to_processed(samples)
    total_ms = int((time.time() - t_total) * 1000)

    yield _event("pipeline_done", None, f"全链路完成，总耗时 {total_ms}ms", {
        "total_ms": total_ms,
        "report_path": report_path,
        "sample_count": len(samples),
    })


# ── 序列化辅助函数 ──────────────────────────────────────────────

def _serialize_list(items) -> list:
    """把任意列表序列化为可 JSON 化的形式"""
    if not items:
        return []
    result = []
    for item in items:
        if hasattr(item, "__dict__"):
            result.append({k: str(v) for k, v in item.__dict__.items()})
        elif hasattr(item, "model_dump"):
            result.append(item.model_dump())
        else:
            result.append(str(item))
    return result


def _serialize_findings(findings) -> list:
    result = []
    for f in findings:
        result.append({
            "summary": getattr(f, "summary", str(f)),
            "severity": str(getattr(f, "severity", "")),
            "layer": str(getattr(f, "layer", "")),
            "evidence": getattr(f, "evidence", ""),
            "impact": getattr(f, "impact", ""),
        })
    return result


def _serialize_debate(debate) -> dict:
    if debate is None:
        return {}
    return {
        "hawk_position": getattr(debate, "hawk_position", ""),
        "dove_position": getattr(debate, "dove_position", ""),
        "arbitrator_verdict": getattr(debate, "arbitrator_verdict", ""),
        "consensus_level": str(getattr(debate, "consensus_level", "")),
    }


def _serialize_rag_packets(rag_context) -> list:
    """从 ContextResponse 或 packets 列表提取展示数据"""
    packets = []
    if hasattr(rag_context, "context_packets"):
        raw = rag_context.context_packets
    elif isinstance(rag_context, list):
        raw = rag_context
    else:
        return []
    for p in raw:
        packets.append({
            "packet_id": getattr(p, "packet_id", ""),
            "source_id": getattr(p, "source_id", ""),
            "source_title": getattr(p, "source_title", ""),
            "content_type": getattr(p, "content_type", ""),
            "excerpt": getattr(p, "excerpt", ""),
            "reason_for_match": getattr(p, "reason_for_match", ""),
            "trust_level": getattr(p, "trust_level", ""),
            "score": getattr(p, "score", 0.0),
        })
    return packets
