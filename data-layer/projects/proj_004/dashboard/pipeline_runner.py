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

# 路径：dashboard/ → proj_004/ → projects/ → data-layer/ → DesignAssistant/
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # proj_004/
DA_ROOT = os.path.normpath(os.path.join(PROJ_DIR, "..", "..", ".."))    # DesignAssistant/

INCOMING_DIR = os.path.normpath(os.path.join(DA_ROOT, "background", "real_intel_samples", "incoming"))

sys.path.insert(0, PROJ_DIR)
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.1_implementation"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.2_implementation"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.3_implementation", "src"))
sys.path.insert(0, os.path.join(PROJ_DIR, "phase2.5_implementation"))


def _event(type_, step, message, data=None):
    return {"type": type_, "step": step, "message": message, "data": data or {}}


def _compute_phase21_diagnostics(samples_data: list, elapsed_ms: int) -> dict:
    processing_values = sorted(
        int(sample.get("processing_time_ms", 0) or 0)
        for sample in samples_data
    )

    def _percentile(sorted_values: list[int], ratio: float) -> int:
        if not sorted_values:
            return 0
        index = max(0, min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * ratio))))
        return int(sorted_values[index])

    def _sample_digest(sample: dict) -> dict:
        return {
            "source_id": sample.get("source_id", ""),
            "raw_title": sample.get("raw_title", ""),
            "raw_source_name": sample.get("raw_source_name", ""),
            "decode_status": sample.get("decode_status", "unknown"),
            "processing_time_ms": int(sample.get("processing_time_ms", 0) or 0),
            "signal_count": int(sample.get("signal_count", 0) or 0),
            "warning_count": int(sample.get("warning_count", 0) or 0),
            "error_type": sample.get("error_type", ""),
            "error_message": sample.get("error_message", ""),
        }

    sorted_by_slow = sorted(
        samples_data,
        key=lambda sample: int(sample.get("processing_time_ms", 0) or 0),
        reverse=True,
    )
    sorted_by_warning = sorted(
        [sample for sample in samples_data if int(sample.get("warning_count", 0) or 0) > 0],
        key=lambda sample: (
            int(sample.get("warning_count", 0) or 0),
            int(sample.get("processing_time_ms", 0) or 0),
        ),
        reverse=True,
    )
    failed_samples = [sample for sample in samples_data if sample.get("decode_status") == "failed"]

    p50_ms = _percentile(processing_values, 0.50)
    p90_ms = _percentile(processing_values, 0.90)
    p95_ms = _percentile(processing_values, 0.95)
    slow_sample_threshold_ms = p90_ms if p90_ms > 0 else 0
    slow_sample_count = sum(
        1 for sample in samples_data
        if int(sample.get("processing_time_ms", 0) or 0) >= slow_sample_threshold_ms and slow_sample_threshold_ms > 0
    )

    return {
        "elapsed_ms": int(elapsed_ms or 0),
        "p50_processing_time_ms": p50_ms,
        "p90_processing_time_ms": p90_ms,
        "p95_processing_time_ms": p95_ms,
        "slow_sample_threshold_ms": slow_sample_threshold_ms,
        "slow_sample_count": slow_sample_count,
        "top_slowest_samples": [_sample_digest(sample) for sample in sorted_by_slow[:10]],
        "top_warning_samples": [_sample_digest(sample) for sample in sorted_by_warning[:10]],
        "failed_samples": [_sample_digest(sample) for sample in failed_samples[:10]],
    }


def run_pipeline(api_key: str, base_url: str) -> Generator[dict, None, None]:
    """
    主 generator：按顺序执行各 step，每步完成后 yield 事件。
    模型配置从 llm_config.yaml 按 phase 读取，不再接受单一 model 参数。

    api_key / base_url 参数作为全局兜底（来自 dashboard 全局配置区），
    优先级低于 llm_config.yaml 中各 phase 的独立配置。
    """
    # ── 设置全局兜底环境变量（各模块从 os.environ 读取）
    # 只在环境变量未设置时写入，避免覆盖 yaml phase 级配置
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    if base_url:
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
            load_llm_config,
        )
        import glob, json as _json

        incoming_files = sorted(glob.glob(os.path.join(INCOMING_DIR, "*.json")))
        if not incoming_files:
            yield _event("error", None, "incoming/ 目录为空，请先放入样本文件", {})
            return

        yield _event("log", None, f"发现 {len(incoming_files)} 个样本文件")
        samples = load_samples(incoming_files)
        llm_config_21 = load_llm_config("2.1")
    except Exception as e:
        yield _event("error", None, f"初始化失败：{e}", {"traceback": traceback.format_exc()})
        return

    # ── Step 1：2.1 情报解码
    yield _event("step_start", "2.1", "2.1 情报解码 开始…")
    t1 = time.time()
    try:
        all_signals, decode_results, per_sample_stats = run_step1_decode(samples, llm_config_21)

        # 组装展示数据
        # decode_results 是 IntelligenceDecodeResult 对象列表（非 dict）
        dr_map = {r.source_id: r for r in decode_results}
        # 原始样本 payload 映射（source_id → payload dict）
        raw_payload_map = {
            s["payload"].get("source_id", s["file_name"]): s["payload"]
            for s in samples
        }
        samples_data = []
        for stat in per_sample_stats:
            sid = stat.get("source_id", "?")
            sig_count = stat.get("signal_count", 0)
            dr = dr_map.get(sid)
            # 把 Signal 对象序列化为 dict，取常用展示字段
            signals_detail = []
            if dr and dr.signals:
                for s in dr.signals:
                    signals_detail.append({
                        "signal_type": s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
                        "signal_label": s.signal_label,
                        "description": s.description,
                        "intensity_score": s.intensity_score,
                        "confidence_score": s.confidence_score,
                        "evidence_text": s.evidence_text,
                        "timeliness_score": s.timeliness_score,
                    })
            # 原始样本字段（用于 dashboard 原文展示）
            raw = raw_payload_map.get(sid, {})
            samples_data.append({
                "source_id": sid,
                "file_name": stat.get("file_name", sid),
                "signal_count": sig_count,
                "signals": signals_detail,
                "is_noise": sig_count == 0,
                "processing_time_ms": stat.get("processing_time_ms", 0),
                "warning_count": stat.get("warning_count", 0),
                "warnings": stat.get("warnings", []),
                "error_message": stat.get("error", ""),
                "error_type": stat.get("error_type", ""),
                "decode_status": "failed" if stat.get("error") else ("noise" if sig_count == 0 else "signal"),
                "started_at": stat.get("started_at", ""),
                "finished_at": stat.get("finished_at", ""),
                # 原文字段
                "raw_title":       raw.get("title", ""),
                "raw_content":     raw.get("content", ""),
                "raw_source_url":  raw.get("source_url", ""),
                "raw_source_name": raw.get("source_name", ""),
                "raw_published_at":raw.get("published_at", ""),
            })

        elapsed = int((time.time() - t1) * 1000)
        decode_error_count = sum(1 for s in per_sample_stats if s.get("error"))
        decode_success_count = len(samples_data) - decode_error_count
        avg_processing_time_ms = int(sum(s.get("processing_time_ms", 0) for s in per_sample_stats) / len(per_sample_stats)) if per_sample_stats else 0
        warning_sample_count = sum(1 for s in per_sample_stats if s.get("warning_count", 0) > 0)
        max_processing_time_ms = max((s.get("processing_time_ms", 0) for s in per_sample_stats), default=0)
        yield _event("step_done", "2.1", f"2.1 完成：{len(all_signals)} 个信号，耗时 {elapsed}ms", {
            "samples": samples_data,
            "signal_total": len(all_signals),
            "noise_count": sum(1 for s in samples_data if s["is_noise"]),
            "decode_error_count": decode_error_count,
            "decode_success_count": decode_success_count,
            "avg_processing_time_ms": avg_processing_time_ms,
            "warning_sample_count": warning_sample_count,
            "max_processing_time_ms": max_processing_time_ms,
            "max_parallel_samples": llm_config_21.get("max_parallel_samples", 1),
            "request_spacing_ms": llm_config_21.get("request_spacing_ms", 0),
            "diagnostics": _compute_phase21_diagnostics(samples_data, elapsed),
            "elapsed_ms": elapsed,
        })
    except Exception as e:
        yield _event("error", "2.1", f"2.1 失败：{e}", {"traceback": traceback.format_exc()})
        return

    # 冷却
    cooldown = llm_config_21.get("step1_cooldown_seconds")
    if cooldown is None or cooldown == "":
        cooldown = 15 * len(samples)
    cooldown = max(0, int(cooldown))
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

        # ── pending_signals / insufficient_evidence：无机会产出，生成轻量 summary
        if not judgment_result.opportunities:
            status = getattr(judgment_result, "status", "unknown")
            sig_count_22 = judgment_result.diagnostics.signal_count if judgment_result.diagnostics else len(all_signals)

            # Signal Store 当前 pending 数量
            try:
                from signal_store import SignalStore
                _ss = SignalStore()
                _ss_stats = _ss.stats()
                pending_in_store = _ss_stats.get("by_status", {}).get("pending", 0)
            except Exception:
                pending_in_store = 0

            no_opp_data = {
                "status": status,
                "signal_count": sig_count_22,
                "sample_count": len(samples),
                "pending_in_store": pending_in_store,
                "elapsed_ms": elapsed2,
            }

            # 生成轻量报告文件
            report_path_no_opp = None
            try:
                from report_writer import generate_no_opportunity_report
                report_path_no_opp = generate_no_opportunity_report(
                    status=status,
                    signal_count=sig_count_22,
                    sample_count=len(samples),
                    pending_in_store=pending_in_store,
                    total_ms=int((time.time() - t_total) * 1000),
                )
                no_opp_data["report_path"] = report_path_no_opp
            except Exception as e:
                yield _event("log", None, f"轻量报告生成失败（不影响主流程）：{e}")

            move_to_processed(samples)
            total_ms = int((time.time() - t_total) * 1000)
            yield _event(
                "pipeline_no_opportunity", None,
                f"本批次未发现可操作机会（{status}），{sig_count_22} 条信号已处理",
                {**no_opp_data, "total_ms": total_ms},
            )
            return

        opp = judgment_result.opportunities[0] if judgment_result.opportunities else None
        opp_data = {}
        if opp:
            # 判断是否走了 LLM 路径（有 warnings 且含 [fallback] 表示 fallback）
            fallback_flags = [str(w) for w in (getattr(opp, "warnings", []) or []) if "[fallback]" in str(w)]
            llm_used = len(fallback_flags) == 0
            opp_data = {
                "title": getattr(opp, "opportunity_title", ""),
                "thesis": getattr(opp, "opportunity_thesis", ""),   # 实际字段名 opportunity_thesis
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

        # 2.4 证据包：2.2 阶段不单独存 rag_context，
        # RAG 在 step4 才查。此处占位，dashboard 展示时从 step4 结果回填。
        rag_packets = []

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
        action_result = run_step3_action(judgment_result)
        elapsed3 = int((time.time() - t3) * 1000)

        act = getattr(action_result, "action_decision", None)
        act_data = {}
        if act:
            debate = getattr(act, "debate_summary", None)
            llm_used = debate is not None
            display = getattr(act, "display", None)
            act_data = {
                "posture": str(getattr(act, "decision_posture", "")),
                "commitment_mode": str(getattr(act, "commitment_mode", "")),
                "display_judgment_label": getattr(display, "display_judgment_label", "") if display else "",
                "display_badge": getattr(display, "display_badge", "") if display else str(getattr(act, "decision_posture", "")),
                "display_title_mode": getattr(display, "display_title_mode", "") if display else "",
                "stage_1_objective": getattr(act, "stage_1_objective", ""),
                "key_gates": _serialize_list(getattr(act, "key_gates", [])),
                "why": getattr(act, "why_this_posture", ""),
                "llm_used": llm_used,
                "debate_summary": _serialize_debate(debate),
                "phases": _serialize_list(getattr(act, "phased_plan", [])),
                "top_risks": _serialize_list(getattr(act, "top_risks", [])),
                "exit_conditions": _serialize_list(getattr(act, "exit_conditions", [])),
                "open_disagreements": _serialize_list(getattr(act, "open_disagreements", [])),
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

        # 把 step4 内部查到的 RAG 证据包也透传出来（供 dashboard 2.4 区块展示）
        rag_packets_from_retro = []
        if hasattr(retro_result, "upstream_outputs"):
            p24 = (retro_result.upstream_outputs or {}).get("phase2_4", {})
            rag_packets_from_retro = p24.get("context_packets", [])

        yield _event("step_done", "2.5", f"2.5 完成：findings={len(retro_data['critical_findings'])}，耗时 {elapsed5}ms", {
            "retrospective": retro_data,
            "elapsed_ms": elapsed5,
            "rag_packets": rag_packets_from_retro,   # 供 dashboard 回填到 2.4 展示区
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
        source_ids = [str(sample.get("payload", {}).get("source_id", sample.get("file_name", ""))) for sample in samples]
        report_path = generate_report(
            opportunity=opp_obj,
            action=act_obj,
            retrospective=retro_result.retrospective,
            decode_results=decode_results,
            sample_count=len(samples),
            signal_count=len(all_signals),
            run_id=f"dashboard_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            source_ids=source_ids,
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
        # severity / layer 是枚举对象，需要 .value 取字符串
        sev = getattr(f, "severity", None)
        sev_str = sev.value if hasattr(sev, "value") else str(sev)
        layer = getattr(f, "layer", None)
        layer_str = layer.value if hasattr(layer, "value") else str(layer)
        result.append({
            "summary": getattr(f, "summary", str(f)),
            "severity": sev_str,
            "layer": layer_str,
            "evidence": getattr(f, "evidence", ""),
            "impact": getattr(f, "impact", ""),
        })
    return result


def _serialize_debate(debate) -> dict:
    if debate is None:
        return {}
    hawk_stance = getattr(debate, "hawk_stance", "")
    dove_stance = getattr(debate, "dove_stance", "")
    executor_stance = getattr(debate, "executor_stance", "")
    dove_rebuttal = getattr(debate, "dove_rebuttal", "")
    executor_rebuttal = getattr(debate, "executor_rebuttal", "")
    resolution = getattr(debate, "resolution", "")
    return {
        "hawk_stance": hawk_stance,
        "dove_stance": dove_stance,
        "executor_stance": executor_stance,
        "dove_rebuttal": dove_rebuttal,
        "executor_rebuttal": executor_rebuttal,
        "resolution": resolution,
        "hawk_position": hawk_stance,
        "dove_position": dove_stance,
        "arbitrator_verdict": resolution,
        "consensus_level": "multi-agent-converged" if resolution else "",
    }


def _serialize_rag_packets(rag_context) -> list:
    """从 ContextResponse 提取展示数据。字段名：context_packets（非 packets）"""
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
            "trust_level": str(getattr(p, "trust_level", "")),
            "score": float(getattr(p, "score", 0.0)),
        })
    return packets
