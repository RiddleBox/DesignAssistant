"""
Phase 2.2 Step A — 批内信号软标注 + 逻辑场景识别

职责：
1. 对当次批次内的所有信号做一次 LLM 调用
2. 输出：logical_scenarios（软性场景建议，供 Step C 参考）
3. 输出：每条信号的角色标注（roles / needs / domains / waiting_for_text）

设计原则：
- Step A 是"软标注器"，不是"硬分组器"
- logical_scenarios 是建议，Step C 全量接收信号后可自由突破场景边界
- 分组依据是"逻辑互补"，不是"语义相似"
- 整批次只调用 1 次 LLM（haiku 级别）
- LLM 失败时 Fallback：所有信号视为孤立，logical_scenarios 为空

变更历史：
- v1.0（2026-03-30）：初始实现，输出 signal_groups（硬分组）
- v2.0（2026-04-01）：重构输出为 logical_scenarios（软场景建议），
  消除硬分组对 Step C 判断前提的污染，保留跨域信号的组合可能
"""

import json
import os
import importlib.util
from datetime import date
from typing import List, Dict, Optional


ROLE_BY_SIGNAL_TYPE = {
    "regulatory": ["catalyst", "timing_signal"],
    "capital":    ["resource_validation"],
    "market":     ["demand_evidence", "competitive_gap"],
    "technical":  ["resource_validation", "execution_risk"],
    "team":       ["resource_validation", "execution_risk"],
}

DOMAIN_BY_SIGNAL_TYPE = {
    "regulatory": ["regulation"],
    "capital":    ["capital"],
    "market":     ["gaming", "mobile"],
    "technical":  ["ai", "gaming"],
    "team":       ["gaming"],
}

ROLE_COMPLEMENTS = {
    "catalyst":            ["demand_evidence", "resource_validation", "competitive_gap"],
    "demand_evidence":     ["catalyst", "resource_validation"],
    "resource_validation": ["catalyst", "demand_evidence"],
    "competitive_gap":     ["catalyst", "resource_validation"],
    "execution_risk":      ["catalyst", "demand_evidence"],
    "timing_signal":       ["catalyst", "demand_evidence", "resource_validation"],
    "negative_validator":  [],
}


class LogicalScenario:
    """
    Step A 的软性场景建议。

    与旧版 signal_groups 的关键区别：
    - signal_groups：硬分组，Step C 只能看到组内信号
    - LogicalScenario：软建议，Step C 看全量信号，场景只是"建议重点关注"
    """
    def __init__(
        self,
        scenario_id: str,
        primary_signal_ids: List[str],    # 核心相关信号（2-4条）
        context_signal_ids: List[str],    # 建议关注但非核心的信号（0-3条）
        reasoning: str,                   # 为什么认为这些信号有逻辑关联
        opportunity_direction: str,       # 可能指向的机会方向
    ):
        self.scenario_id = scenario_id
        self.primary_signal_ids = primary_signal_ids
        self.context_signal_ids = context_signal_ids
        self.reasoning = reasoning
        self.opportunity_direction = opportunity_direction

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "primary_signal_ids": self.primary_signal_ids,
            "context_signal_ids": self.context_signal_ids,
            "reasoning": self.reasoning,
            "opportunity_direction": self.opportunity_direction,
        }


class StepAResult:
    def __init__(
        self,
        logical_scenarios: List[LogicalScenario],  # 软性场景建议（替代原 signal_groups）
        isolated_signals: List[dict],               # 孤立信号（含角色标注）
        role_annotations: Dict[str, dict],          # signal_id → {roles, needs, domains, waiting_for_text}
        fallback_used: bool = False,
        # 向后兼容：保留 signal_groups 属性，值始终为空列表
        # judgment_engine 迁移完成后可移除
    ):
        self.logical_scenarios = logical_scenarios
        self.isolated_signals = isolated_signals
        self.role_annotations = role_annotations
        self.fallback_used = fallback_used
        # 兼容旧代码访问 signal_groups
        self.signal_groups: List[List[dict]] = []


def run_step_a(
    enriched_signals: List[dict],
    llm_client=None,
    model: str = "deepseek-chat",
) -> StepAResult:
    """
    执行 Step A：批内信号软标注 + 逻辑场景识别。

    LLM 客户端必须由调用方（judgment_engine）统一创建并传入，
    不在此处自行构造，确保所有 LLM 调用追溯到 llm_config.yaml 的统一配置。

    Args:
        enriched_signals: _extract_enriched_signals 输出的信号列表
        llm_client: 由 JudgmentEngine 从 llm_config.yaml 创建的 LLMClient 实例
        model: 模型名称（由调用方从配置传入）

    Returns:
        StepAResult（包含 logical_scenarios 而非 signal_groups）
    """
    if not enriched_signals:
        return StepAResult([], [], {})

    if llm_client:
        try:
            return _llm_annotate_and_identify_scenarios(enriched_signals, llm_client, model)
        except Exception as e:
            print(f"[Step A] LLM 调用失败，使用规则 fallback: {e}")

    return _rule_fallback(enriched_signals)


# ──────────────────────────────────────────────
# LLM 路径
# ──────────────────────────────────────────────

def _llm_annotate_and_identify_scenarios(
    signals: List[dict],
    client,
    model: str,
) -> StepAResult:
    """单次 LLM 调用，完成信号角色标注 + 逻辑场景识别"""
    signals_summary = _build_signals_summary(signals)
    prompt = _build_step_a_prompt(signals_summary)

    raw = client.call(
        prompt=prompt,
        model=model,
        max_tokens=2048,
        temperature=0.2,
    )
    return _parse_step_a_response(raw, signals)


def _build_signals_summary(signals: List[dict]) -> str:
    lines = []
    for i, s in enumerate(signals):
        sid = s.get("signal_id") or s.get("id") or f"s{i}"
        stype = s.get("signal_type", "unknown")
        label = s.get("signal_label") or s.get("label", "")
        desc = s.get("description", "")[:100]
        intensity = s.get("intensity_score") or s.get("intensity", 5)
        lines.append(f"[{sid}] type={stype} intensity={intensity} | {label} | {desc}")
    return "\n".join(lines)


def _build_step_a_prompt(signals_summary: str) -> str:
    return f"""你是一个战略机会分析助手。以下是一批从外部情报中提取的信号，请完成两项任务。

## 当前批次信号

{signals_summary}

## 任务1：逻辑场景识别（软建议，非硬性分组）

识别哪些信号可能组合成一个完整的机会论点，形成"逻辑场景"建议。注意：
- **这是建议，不是分组**：你识别出的场景只是给后续分析的参考，分析师可以自由突破场景边界
- 组合依据是"逻辑互补"，不是"语义相似"（见下方典型案例）
- 一个场景需要2条以上信号，核心信号2-4条，上下文信号0-3条
- 可以有多个场景，也可以没有（返回空列表）
- 一条信号可以出现在多个场景中（软建议不需要互斥）

**逻辑互补案例参考**（理解什么是逻辑互补，而非语义相似）：

案例1 - 监管倒逼整合机会（跨域互补）：
- 催化剂：EU DMA 罚款苹果（监管域）→ 平台分发成本上升
- 资源验证：某大厂宣布 3 亿并购资金（资本域）→ 资源充足
- 市场确认：独立开发者出走 App Store 数量创新高（市场域）→ 需求出现
✅ 三条信号跨域但逻辑互补：外部压力 + 资源到位 + 市场需求

案例2 - AI 降低独立游戏门槛（跨域互补）：
- 技术信号：生成式 AI 代码工具成本骤降 80%（技术域）
- 市场信号：Steam 独立游戏月活创新高（市场域）
✅ 供给侧成本下降 + 需求侧市场验证

反例 - 语义相似但非逻辑互补：
- 信号A：腾讯游戏新作发布
- 信号B：网易游戏新作发布
❌ 语义相似（都是游戏新作）但不构成逻辑链，不应作为场景

## 任务2：每条信号角色标注

对每条信号标注：
- roles：该信号在机会论点中扮演的角色（1-2个），从以下选择：
  catalyst / demand_evidence / resource_validation / competitive_gap / execution_risk / timing_signal / negative_validator
- needs：构成完整机会论点，还需要什么角色的信号（0-3个）
- domains：信号所属领域（1-3个），从以下选择：
  gaming / ai / mobile / regulation / capital / geopolitics
- waiting_for_text：一句话（15字以内），描述"这条信号在等待什么样的伙伴信号才能构成机会"

## 输出格式（严格JSON，不要有任何额外文字）

```json
{{
  "logical_scenarios": [
    {{
      "scenario_id": "s1",
      "primary_signal_ids": ["信号ID1", "信号ID2"],
      "context_signal_ids": ["信号ID3"],
      "reasoning": "一句话：为什么认为这些信号在逻辑上有关联",
      "opportunity_direction": "一句话：可能指向什么机会方向"
    }}
  ],
  "annotations": [
    {{
      "signal_id": "信号ID",
      "roles": ["catalyst"],
      "needs": ["demand_evidence", "resource_validation"],
      "domains": ["gaming", "regulation"],
      "waiting_for_text": "等待市场侧需求变化证据"
    }}
  ]
}}
```

重要：logical_scenarios 是软建议，信号可以跨场景出现。没有发现逻辑关联时，返回空列表 []。
"""


def _parse_step_a_response(raw: str, signals: List[dict]) -> StepAResult:
    """解析 LLM 输出，构建 StepAResult（含 logical_scenarios）"""
    try:
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
    except Exception as e:
        print(f"[Step A] JSON 解析失败: {e}，使用规则 fallback")
        return _rule_fallback(signals)

    # 构建角色标注索引
    role_annotations: Dict[str, dict] = {}
    for ann in data.get("annotations", []):
        sid = ann.get("signal_id", "")
        if sid:
            role_annotations[sid] = {
                "roles":            ann.get("roles", ["catalyst"]),
                "needs":            ann.get("needs", []),
                "domains":          ann.get("domains", ["gaming"]),
                "waiting_for_text": ann.get("waiting_for_text", ""),
            }

    # 解析 logical_scenarios
    logical_scenarios: List[LogicalScenario] = []
    for sc in data.get("logical_scenarios", []):
        primary_ids = sc.get("primary_signal_ids", [])
        if len(primary_ids) >= 2:
            logical_scenarios.append(LogicalScenario(
                scenario_id=sc.get("scenario_id", f"s{len(logical_scenarios)+1}"),
                primary_signal_ids=primary_ids,
                context_signal_ids=sc.get("context_signal_ids", []),
                reasoning=sc.get("reasoning", ""),
                opportunity_direction=sc.get("opportunity_direction", ""),
            ))

    # 所有信号补全角色标注（LLM 没有标注的用规则兜底）
    isolated = []
    for s in signals:
        sid = _get_signal_id(s)
        s_copy = dict(s)
        if sid not in role_annotations:
            ann = _infer_roles_by_rule(s)
            role_annotations[sid] = ann
        s_copy["_role_annotation"] = role_annotations[sid]
        isolated.append(s_copy)

    # isolated_signals = 所有信号（Step C 通过 logical_scenarios 软建议使用，非硬隔离）
    # 注意：这里返回全量信号作为 isolated_signals，是为了兼容 Step B 路径
    # judgment_engine 会根据 logical_scenarios 决定哪些信号送 Step C，哪些走 Step B
    return StepAResult(
        logical_scenarios=logical_scenarios,
        isolated_signals=isolated,
        role_annotations=role_annotations,
        fallback_used=False,
    )


# ──────────────────────────────────────────────
# 规则 Fallback
# ──────────────────────────────────────────────

def _rule_fallback(signals: List[dict]) -> StepAResult:
    """LLM 失败时：无 logical_scenarios，所有信号视为孤立，角色标注用规则推断"""
    role_annotations = {}
    isolated = []
    for s in signals:
        sid = _get_signal_id(s)
        ann = _infer_roles_by_rule(s)
        role_annotations[sid] = ann
        s_copy = dict(s)
        s_copy["_role_annotation"] = ann
        isolated.append(s_copy)
    return StepAResult(
        logical_scenarios=[],
        isolated_signals=isolated,
        role_annotations=role_annotations,
        fallback_used=True,
    )


def _infer_roles_by_rule(signal: dict) -> dict:
    """基于 signal_type 推断角色（规则层）"""
    stype = signal.get("signal_type", "market")
    roles = ROLE_BY_SIGNAL_TYPE.get(stype, ["catalyst"])
    primary_role = roles[0]
    needs = ROLE_COMPLEMENTS.get(primary_role, [])[:2]
    domains = DOMAIN_BY_SIGNAL_TYPE.get(stype, ["gaming"])
    waiting_for_text = f"等待{_role_cn(needs[0]) if needs else '更多'}证据"
    return {
        "roles":            roles,
        "needs":            needs,
        "domains":          domains,
        "waiting_for_text": waiting_for_text,
    }


def _role_cn(role: str) -> str:
    mapping = {
        "catalyst":            "外部催化",
        "demand_evidence":     "需求侧",
        "resource_validation": "资源验证",
        "competitive_gap":     "竞品收缩",
        "execution_risk":      "执行风险",
        "timing_signal":       "时机",
        "negative_validator":  "反向",
    }
    return mapping.get(role, role)


def _get_signal_id(signal: dict) -> str:
    return signal.get("signal_id") or signal.get("id") or str(id(signal))
