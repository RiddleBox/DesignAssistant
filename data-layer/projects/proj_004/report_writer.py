"""
报告输出层 - 把每次批量运行的结果写成结构化 Markdown 报告

输出路径：data-layer/projects/proj_004/reports/YYYY-MM-DD_HHmm_<posture>_<slug>.md
"""

import os
import re
from datetime import datetime
from typing import Optional


REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def _slug(text: str, max_len: int = 30) -> str:
    """把标题压缩成文件名安全的 slug"""
    # 只保留中文、英文、数字、空格
    text = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)
    text = text.strip()[:max_len]
    text = re.sub(r"\s+", "_", text)
    return text


def _pct(val) -> str:
    if val is None:
        return "—"
    return f"{val:.0%}" if isinstance(val, float) and val <= 1.0 else str(val)


def _list_items(items, indent="  ") -> str:
    if not items:
        return f"{indent}（无）\n"
    return "".join(f"{indent}- {item}\n" for item in items)


def generate_report(
    judgment_result,
    action_result,
    retro_result,
    decode_results: list,
    sample_count: int,
    signal_count: int,
    total_ms: int,
    run_timestamp: Optional[datetime] = None,
) -> str:
    """生成完整 Markdown 报告，返回文件路径"""
    os.makedirs(REPORTS_DIR, exist_ok=True)

    ts = run_timestamp or datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M")
    ts_file = ts.strftime("%Y-%m-%d_%H%M")

    opp = judgment_result.opportunities[0]
    act = action_result.action_decision
    retro = retro_result.retrospective

    posture = str(act.decision_posture.value if hasattr(act.decision_posture, "value") else act.decision_posture)
    title = opp.opportunity_title or "未命名机会"
    priority = str(opp.priority_level.value if hasattr(opp.priority_level, "value") else opp.priority_level)

    # 文件名
    fname = f"{ts_file}_{posture}_{_slug(title)}.md"
    fpath = os.path.join(REPORTS_DIR, fname)

    lines = []
    lines.append(f"# 机会判断报告\n")
    lines.append(f"> 生成时间：{ts_str}　｜　样本数：{sample_count}　｜　信号池：{signal_count}　｜　耗时：{total_ms/1000:.1f}s\n")
    lines.append("\n---\n")

    # ── 一、机会概览 ─────────────────────────────────────────
    lines.append("## 一、机会概览\n\n")
    lines.append(f"**标题**：{title}\n\n")
    lines.append(f"**优先级**：`{priority}`　　**行动姿态**：`{posture}`\n\n")

    thesis = getattr(opp, "opportunity_thesis", None) or getattr(opp, "thesis", None)
    if thesis:
        lines.append(f"**论点**：{thesis}\n\n")

    # ── 二、信号来源 ─────────────────────────────────────────
    lines.append("## 二、信号来源（本批次）\n\n")
    lines.append(f"共处理 **{sample_count}** 条样本，提取 **{signal_count}** 个信号。\n\n")

    if decode_results:
        lines.append("| 样本 | 信号数 | 类型 | 核心标签 |\n")
        lines.append("|------|--------|------|----------|\n")
        for dr in decode_results:
            sid = getattr(dr, "source_id", "—")
            sigs = getattr(dr, "signals", [])
            if sigs:
                for s in sigs:
                    stype = getattr(s, "signal_type", "—")
                    stype = stype.value if hasattr(stype, "value") else str(stype)
                    label = getattr(s, "signal_label", "") or getattr(s, "label", "—")
                    lines.append(f"| {sid} | {len(sigs)} | {stype} | {label} |\n")
            else:
                lines.append(f"| {sid} | 0 | — | （无信号） |\n")
        lines.append("\n")

    # ── 三、机会判断（2.2） ───────────────────────────────────
    # 判断来源标注：opp.warnings 含 [fallback] 说明规则引擎生成
    opp_warnings = getattr(opp, "warnings", []) or []
    is_opp_fallback = any("[fallback]" in str(w) for w in opp_warnings)
    opp_source_tag = " ⚠️ `规则引擎生成，LLM 未跑通`" if is_opp_fallback else " ✅ `LLM生成`"
    lines.append(f"## 三、机会判断（Phase 2.2）{opp_source_tag}\n\n")

    supporting = getattr(opp, "supporting_evidence", []) or []
    counter = getattr(opp, "counter_evidence", []) or []
    assumptions = getattr(opp, "key_assumptions", []) or []
    uncertainty = getattr(opp, "uncertainty_map", {}) or {}
    next_q = getattr(opp, "next_validation_questions", []) or []

    lines.append("### 支持证据\n\n")
    lines.append(_list_items(supporting))

    lines.append("\n### 反对证据\n\n")
    lines.append(_list_items(counter))

    lines.append("\n### 关键假设\n\n")
    lines.append(_list_items(assumptions))

    if uncertainty:
        lines.append("\n### 不确定性地图\n\n")
        if isinstance(uncertainty, dict):
            for k, v in uncertainty.items():
                lines.append(f"  - **{k}**：{v}\n")
        elif isinstance(uncertainty, list):
            lines.append(_list_items(uncertainty))
        lines.append("\n")

    if next_q:
        lines.append("\n### 下一步验证问题\n\n")
        lines.append(_list_items(next_q))

    why_now = getattr(opp, "why_now", None)
    if why_now:
        lines.append("\n### 为什么是现在\n\n")
        lines.append(f"  {why_now}\n")

    # ── 四、行动设计（2.3） ───────────────────────────────────
    # 判断来源标注：debate_summary 存在说明 LLM 跑通，否则是规则引擎
    debate = getattr(act, "debate_summary", None)
    is_act_fallback = debate is None
    act_source_tag = " ⚠️ `规则引擎生成，LLM 未跑通`" if is_act_fallback else " ✅ `LLM生成`"
    lines.append(f"\n## 四、行动设计（Phase 2.3）{act_source_tag}\n\n")
    lines.append(f"**行动姿态**：`{posture}`\n\n")

    why = getattr(act, "why_this_posture", None)
    if why:
        lines.append(f"**选择理由**：{why}\n\n")

    # debate_summary — dataclass 或 dict 均兼容
    debate = getattr(act, "debate_summary", None)
    if debate:
        # 支持 DebateSummary dataclass 和旧版 dict 两种形式
        hawk  = getattr(debate, "hawk_stance",  None) or (debate.get("hawk_stance")  if isinstance(debate, dict) else None)
        dove  = getattr(debate, "dove_stance",  None) or (debate.get("dove_stance")  if isinstance(debate, dict) else None)
        resol = getattr(debate, "resolution",   None) or (debate.get("resolution")   if isinstance(debate, dict) else None)
        if hawk or dove or resol:
            lines.append("### 辩论摘要\n\n")
            if hawk:
                lines.append(f"- 🦅 **鹰派**：{hawk}\n")
            if dove:
                lines.append(f"- 🕊️ **鸽派**：{dove}\n")
            if resol:
                lines.append(f"- ⚖️ **仲裁**：{resol}\n")
            lines.append("\n")

    # 分阶段计划
    phased = getattr(act, "phased_plan", []) or []
    if phased:
        lines.append("### 分阶段计划\n\n")
        for i, stage in enumerate(phased, 1):
            stage_name = getattr(stage, "stage", f"阶段{i}")
            obj = getattr(stage, "objective", "")
            actions = getattr(stage, "actions", []) or []
            assumptions_to_test = getattr(stage, "key_assumptions_to_test", []) or []
            go_no_go = getattr(stage, "go_no_go_criteria", []) or []
            exit_cond = getattr(stage, "exit_conditions", []) or []
            resources = getattr(stage, "resources", None)
            milestones = getattr(stage, "milestones", []) or []

            lines.append(f"#### {stage_name}\n\n")
            if obj:
                lines.append(f"**目标**：{obj}\n\n")
            if assumptions_to_test:
                lines.append("**待验证假设**：\n")
                lines.append(_list_items(assumptions_to_test))
                lines.append("\n")
            if actions:
                lines.append("**行动**：\n")
                lines.append(_list_items(actions))
                lines.append("\n")
            if resources:
                people    = getattr(resources, "people",    "") or (resources.get("people",    "") if isinstance(resources, dict) else "")
                budget    = getattr(resources, "budget",    "") or (resources.get("budget",    "") if isinstance(resources, dict) else "")
                time_r    = getattr(resources, "time",      "") or (resources.get("time",      "") if isinstance(resources, dict) else "")
                rationale = getattr(resources, "resource_rationale", "") or (resources.get("resource_rationale", "") if isinstance(resources, dict) else "")
                if any([people, budget, time_r]):
                    lines.append(f"**资源**：人力={people}，预算={budget}，时间={time_r}\n\n")
                if rationale:
                    lines.append(f"**资源承诺依据**：{rationale}\n\n")
            if milestones:
                lines.append("**里程碑**：\n")
                lines.append(_list_items(milestones))
                lines.append("\n")
            if go_no_go:
                lines.append("**Go/No-Go 标准**：\n")
                lines.append(_list_items(go_no_go))
                lines.append("\n")
            if exit_cond:
                lines.append("**退出条件**：\n")
                lines.append(_list_items(exit_cond))
                lines.append("\n")

    # 风险
    risks = getattr(act, "top_risks", []) or []
    if risks:
        lines.append("### 主要风险\n\n")
        for r in risks:
            if isinstance(r, dict):
                risk_text   = r.get("risk", "")
                impact      = r.get("impact_on_plan", "")
                mitigation  = r.get("mitigation", "")
                blocks      = r.get("blocks_stage", "")
            else:
                risk_text   = getattr(r, "risk", str(r))
                impact      = getattr(r, "impact_on_plan", "")
                mitigation  = getattr(r, "mitigation", "")
                blocks      = getattr(r, "blocks_stage", "")
            lines.append(f"- **{risk_text}**\n")
            if blocks:
                lines.append(f"  - 影响阶段：`{blocks}`\n")
            if impact:
                lines.append(f"  - 计划影响：{impact}\n")
            if mitigation:
                lines.append(f"  - 应对策略：{mitigation}\n")
        lines.append("\n")

    # 资源承诺逻辑
    rcl = getattr(act, "resource_commitment_logic", None)
    if rcl:
        lines.append("### 资源承诺逻辑\n\n")
        lines.append(f"{rcl}\n\n")

    # fallback
    fallback = getattr(act, "fallback_path", None)
    if fallback:
        lines.append("### 备选路径\n\n")
        lines.append(f"{fallback}\n\n")

    # 开放问题
    open_q = getattr(act, "open_questions", []) or []
    if open_q:
        lines.append("### 开放问题\n\n")
        lines.append(_list_items(open_q))
        lines.append("\n")

    # ── 五、复盘摘要（2.5） ───────────────────────────────────
    lines.append("## 五、复盘摘要（Phase 2.5）\n\n")

    output_checks   = getattr(retro, "output_checks", []) or []
    findings        = getattr(retro, "critical_findings", []) or []
    root_causes     = getattr(retro, "suspected_root_causes", []) or []
    priorities      = getattr(retro, "phase3_priorities", []) or []
    summary         = getattr(retro, "workflow_summary", None)

    if summary:
        lines.append(f"**工作流摘要**：{summary}\n\n")

    # ── 5.1 输出质量检查结果（规则层 + LLM 语义层） ──────────
    if output_checks:
        lines.append("### 输出质量检查\n\n")
        for ck in output_checks:
            if isinstance(ck, dict):
                ctype   = ck.get("check_type", "")
                status  = ck.get("status", "")
                details = ck.get("details", "")
            else:
                ctype   = str(getattr(ck, "check_type",  "")).replace("CheckType.", "")
                status  = str(getattr(ck, "status",       "")).replace("CheckStatus.", "")
                details = getattr(ck, "details", "")
            icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(status.lower(), "—")
            lines.append(f"  - {icon} **{ctype}**：{details}\n")
        lines.append("\n")

    # ── 5.2 关键发现（LLM 语义归因层）── 只展示真正的 findings ─
    # 过滤掉来自 OutputChecker 的规则检测描述（以 "[规则检测]" 开头）
    real_findings = []
    for f in findings:
        text = f.get("summary", str(f)) if isinstance(f, dict) else getattr(f, "summary", str(f))
        if text.startswith("[规则检测]"):
            continue
        real_findings.append(f)

    if real_findings:
        lines.append("### 关键发现\n\n")
        for f in real_findings:
            if isinstance(f, dict):
                text     = f.get("summary", "")
                severity = f.get("severity", "")
                layer    = f.get("layer", "")
            else:
                text     = getattr(f, "summary", str(f))
                severity = str(getattr(f, "severity", "")).replace("SeverityLevel.", "")
                layer    = str(getattr(f, "layer",    "")).replace("AttributionLayer.", "")
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(severity.lower(), "—")
            tag = f" `[{layer}]`" if layer else ""
            lines.append(f"  - {sev_icon}{tag} {text}\n")
        lines.append("\n")

    # ── 5.3 初步归因 ─────────────────────────────────────────
    if root_causes:
        lines.append("### 初步归因\n\n")
        for rc in root_causes:
            if isinstance(rc, dict):
                text       = rc.get("suspected_root_cause", rc.get("description", str(rc)))
                confidence = rc.get("confidence", "")
                reasoning  = rc.get("reasoning", "")
            else:
                text       = getattr(rc, "suspected_root_cause", getattr(rc, "description", str(rc)))
                confidence = str(getattr(rc, "confidence", "")).replace("ConfidenceLevel.", "")
                reasoning  = getattr(rc, "reasoning", "")
            conf_tag = f" `[{confidence}]`" if confidence else ""
            lines.append(f"  - {text}{conf_tag}\n")
            if reasoning:
                lines.append(f"    > {reasoning}\n")
        lines.append("\n")

    # ── 5.4 Phase 3 优先项 ────────────────────────────────────
    if priorities:
        lines.append("### Phase 3 优先项\n\n")
        for p in priorities:
            if isinstance(p, dict):
                text   = p.get("title", str(p))
                reason = p.get("reason", "")
                scope  = p.get("scope", "")
            else:
                text   = getattr(p, "title",  str(p))
                reason = getattr(p, "reason", "")
                scope  = str(getattr(p, "scope", "")).replace("PriorityScope.", "")
            scope_tag = f" `[{scope}]`" if scope else ""
            lines.append(f"  - **{text}**{scope_tag}")
            if reason:
                lines.append(f"：{reason}")
            lines.append("\n")
        lines.append("\n")

    lines.append("\n---\n")
    lines.append(f"*本报告由 proj_004 workflow 自动生成 · {ts_str}*\n")

    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return fpath
