"""
Phase 2.3 决策简报生成器

接收 ActionDesignResult（必须）+ OpportunityObject（可选），
输出 Markdown 格式的决策简报（方向A：1-2页决策简报）。

不调用 LLM，直接从结构化数据生成。
"""

from typing import Optional
from models import ActionDesignResult, OpportunityObject

# 行动姿态中文映射
POSTURE_ZH = {
    "watch":    "持续观察",
    "validate": "验证假设",
    "pilot":    "小规模试点",
    "escalate": "全面推进",
    "hold":     "暂缓",
    "stop":     "终止",
}

POSTURE_EMOJI = {
    "watch":    "👀",
    "validate": "🔍",
    "pilot":    "🚀",
    "escalate": "⚡",
    "hold":     "⏸️",
    "stop":     "🛑",
}


def generate_brief(
    result: ActionDesignResult,
    opp: Optional[OpportunityObject] = None,
) -> str:
    """
    生成决策简报（Markdown）。

    Args:
        result: ActionDesignResult（2.3 输出）
        opp:    OpportunityObject（2.2 输出，可选，用于补充机会背景）

    Returns:
        Markdown 格式字符串
    """
    d = result.action_decision
    posture = d.decision_posture
    posture_label = f"{POSTURE_EMOJI.get(posture,'')}{POSTURE_ZH.get(posture, posture)}"

    lines = []

    # ── 标题 ────────────────────────────────────────────────────────
    lines.append(f"# 决策简报：{d.opportunity_title}")
    lines.append("")
    lines.append(f"> **建议行动**：{posture_label}　｜　**生成版本**：{result.designer_version}")
    lines.append("")

    # ── 一句话结论 ────────────────────────────────────────────────────
    lines.append("## 结论")
    lines.append("")
    lines.append(f"{d.why_this_posture}")
    lines.append("")

    # ── 时机判断（如有） ───────────────────────────────────────────────
    if opp and opp.why_now:
        lines.append("## 为什么是现在")
        lines.append("")
        lines.append(opp.why_now)
        lines.append("")

    # ── 风险摘要 ─────────────────────────────────────────────────────
    if d.top_risks:
        lines.append("## 主要风险")
        lines.append("")
        for r in d.top_risks:
            stage_note = f"（影响阶段：{r.blocks_stage}）" if r.blocks_stage else "（全局影响）"
            lines.append(f"- **{r.risk}** {stage_note}")
            lines.append(f"  - 影响：{r.impact_on_plan}")
            lines.append(f"  - 应对：{r.mitigation}")
        lines.append("")

    # ── 分阶段计划 ────────────────────────────────────────────────────
    if d.phased_plan:
        lines.append("## 行动计划")
        lines.append("")
        for i, stage in enumerate(d.phased_plan, 1):
            r = stage.resources
            lines.append(f"### 第{i}阶段：{stage.stage}")
            lines.append("")
            lines.append(f"**目标**：{stage.objective}")
            lines.append("")

            # 资源
            lines.append(f"**资源投入**：{r.people} · {r.budget} · {r.time}")
            if r.resource_rationale:
                lines.append(f"> {r.resource_rationale}")
            lines.append("")

            # 验证假设
            if stage.key_assumptions_to_test:
                lines.append("**需验证的假设**：")
                for a in stage.key_assumptions_to_test:
                    lines.append(f"- {a}")
                lines.append("")

            # 具体行动
            if stage.actions:
                lines.append("**具体行动**：")
                for a in stage.actions:
                    lines.append(f"- {a}")
                lines.append("")

            # 升级条件（Go 标准）
            if stage.go_no_go_criteria:
                lines.append("**升级条件（达到则进入下一阶段）**：")
                for c in stage.go_no_go_criteria:
                    lines.append(f"- ✅ {c}")
                lines.append("")

            # 降级/退出条件
            if stage.exit_conditions:
                lines.append("**降级/退出条件**：")
                for c in stage.exit_conditions:
                    lines.append(f"- 🔴 {c}")
                lines.append("")

            # 里程碑
            if stage.milestones:
                lines.append("**里程碑**：")
                for m in stage.milestones:
                    lines.append(f"- {m}")
                lines.append("")

    # ── 资源承诺逻辑 ─────────────────────────────────────────────────
    if d.resource_commitment_logic:
        lines.append("## 资源承诺逻辑")
        lines.append("")
        lines.append(d.resource_commitment_logic)
        lines.append("")

    # ── 备选路径（降级方案） ────────────────────────────────────────────
    if d.fallback_path:
        lines.append("## 备选路径（如方案不成立）")
        lines.append("")
        lines.append(d.fallback_path)
        lines.append("")

    # ── 三方辩论摘要（推理链透明化） ────────────────────────────────────
    if d.debate_summary:
        ds = d.debate_summary
        lines.append("## 评估过程（三方辩论摘要）")
        lines.append("")
        if ds.hawk_stance:
            lines.append(f"**激进派**：{ds.hawk_stance}")
        if ds.dove_stance:
            lines.append(f"**保守派**：{ds.dove_stance}")
        if ds.executor_stance:
            lines.append(f"**执行者**：{ds.executor_stance}")
        if ds.dove_rebuttal:
            lines.append(f"**保守派反驳**：{ds.dove_rebuttal}")
        if ds.executor_rebuttal:
            lines.append(f"**执行者回应**：{ds.executor_rebuttal}")
        if ds.resolution:
            lines.append(f"**仲裁理由**：{ds.resolution}")
        lines.append("")

    # ── 待回答的关键问题 ─────────────────────────────────────────────
    if d.open_questions:
        lines.append("## 待回答的关键问题")
        lines.append("")
        for q in d.open_questions:
            lines.append(f"- ❓ {q}")
        lines.append("")

    # ── 警示（如有 2.2 的 warnings） ─────────────────────────────────
    if opp and opp.warnings:
        lines.append("## ⚠️ 注意事项")
        lines.append("")
        for w in opp.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    """快速测试：用规则引擎生成一个示例简报"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from models import (
        OpportunityObject, ActionDesignRequest,
        ActionDecisionObject, ActionDesignResult,
        PhasedPlanStage, PhaseResources, TopRisk, DebateSummary
    )
    from action_designer import ActionDesigner

    opp = OpportunityObject(
        opportunity_title="生成式AI驱动游戏NPC赛道商业化",
        opportunity_thesis="GPT-4集成已达商用门槛，头部厂商立项+资本跟进，赛道进入快速商业化期",
        supporting_evidence=["GPT-4已集成主流NPC系统", "三家初创A轮融资2亿美元"],
        counter_evidence=["推理成本尚未下降到可接受水平", "玩家接受度未验证"],
        key_assumptions=["团队具备UE5/Unity插件交付能力", "推理成本6个月内可降至商用水平"],
        uncertainty_map={"推理成本": "关键不确定性", "玩家接受度": "中等不确定性"},
        priority_level="escalate",
        why_now="头部厂商采购窗口期约3个月，GPU新系列刚发布，竞争方尚未产品化",
        warnings=["信号来源均为新闻报道，非官方公告，存在解读偏差风险"],
    )

    designer = ActionDesigner(api_key='')
    result = designer.design_action(ActionDesignRequest("test_001", opp))

    brief = generate_brief(result, opp)
    print(brief)
    print("\n---\nglobal_summary:", result.global_summary)
