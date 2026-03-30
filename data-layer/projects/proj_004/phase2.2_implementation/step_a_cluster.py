"""
Phase 2.2 Step A — 批内聚类 + 信号角色标注

职责：
1. 对当次批次内的所有信号做一次 LLM 调用
2. 输出：哪些信号可以在批内直接组合（signal_groups）
3. 输出：每条信号的角色标注（roles / needs / domains / waiting_for_text）

设计原则：
- 分组依据是"逻辑互补"，不是"语义相似"
- 整批次只调用 1 次 LLM（haiku 级别）
- LLM 失败时 Fallback：所有信号视为孤立，角色标注使用规则推断
"""

import json
import os
import importlib.util
from datetime import date
from typing import List, Dict, Tuple, Optional

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
    "negative_validator":  [],  # 反向信号不需要伙伴
}


class StepAResult:
    def __init__(
        self,
        signal_groups: List[List[dict]],    # 可批内组合的信号组
        isolated_signals: List[dict],       # 孤立信号（含角色标注）
        role_annotations: Dict[str, dict],  # signal_id → {roles, needs, domains, waiting_for_text}
        fallback_used: bool = False,
    ):
        self.signal_groups = signal_groups
        self.isolated_signals = isolated_signals
        self.role_annotations = role_annotations
        self.fallback_used = fallback_used


def run_step_a(
    enriched_signals: List[dict],
    llm_client=None,
    model: str = "claude-haiku-4-5",
    api_key: str = None,
    base_url: str = None,
) -> StepAResult:
    """
    执行 Step A：批内聚类 + 角色标注。

    Args:
        enriched_signals: _extract_enriched_signals 输出的信号列表
        llm_client: 可选，传入复用 JudgmentEngine 的 LLM 客户端
        model / api_key / base_url: LLM 参数，llm_client 不传时使用

    Returns:
        StepAResult
    """
    if not enriched_signals:
        return StepAResult([], [], {})

    # 尝试 LLM 标注
    try:
        client = llm_client or _load_llm_client(api_key, base_url)
        if client:
            return _llm_cluster_and_annotate(enriched_signals, client, model)
    except Exception as e:
        print(f"[Step A] LLM 调用失败，使用规则 fallback: {e}")

    # Fallback：规则推断
    return _rule_fallback(enriched_signals)


# ──────────────────────────────────────────────
# LLM 路径
# ──────────────────────────────────────────────

def _llm_cluster_and_annotate(
    signals: List[dict],
    client,
    model: str,
) -> StepAResult:
    """单次 LLM 调用，完成批内聚类 + 角色标注"""

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

## 任务1：批内逻辑组合识别

识别哪些信号可以组合成一个完整的机会论点。注意：
- 组合依据是"逻辑互补"，不是"语义相似"
- 典型组合：外部压力信号（催化剂）+ 需求侧变化信号 + 资源到位信号
- 可以有多个组合，也可以没有（返回空列表）
- 一条信号最多出现在一个组合中

## 任务2：每条信号角色标注

对每条信号标注：
- roles：该信号在机会论点中扮演的角色（1-2个），从以下选择：
  catalyst / demand_evidence / resource_validation / competitive_gap / execution_risk / timing_signal / negative_validator
- needs：构成完整机会论点，还需要什么角色的信号（0-3个），从上述角色选择
- domains：信号所属领域（1-3个），从以下选择：
  gaming / ai / mobile / regulation / capital / geopolitics
- waiting_for_text：一句话（15字以内），描述"这条信号在等待什么样的伙伴信号才能构成机会"

## 输出格式（严格JSON，不要有任何额外文字）

```json
{{
  "signal_groups": [
    {{
      "group_id": "g1",
      "signal_ids": ["信号ID1", "信号ID2"],
      "opportunity_direction": "一句话描述这组信号指向的机会方向"
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

重要：signal_groups 中的信号不会出现在孤立信号列表中。没有可组合的信号时，signal_groups 返回空列表 []。
"""


def _parse_step_a_response(raw: str, signals: List[dict]) -> StepAResult:
    """解析 LLM 输出，构建 StepAResult"""
    # 提取 JSON
    try:
        # 去掉可能的 markdown 代码块
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

    # 识别已分组的信号 ID
    grouped_ids = set()
    signal_groups = []
    for g in data.get("signal_groups", []):
        sids = g.get("signal_ids", [])
        if len(sids) >= 2:
            group_signals = [s for s in signals if _get_signal_id(s) in sids]
            if len(group_signals) >= 2:
                signal_groups.append(group_signals)
                grouped_ids.update(sids)

    # 孤立信号 = 未被分组的信号，补全角色标注
    isolated = []
    for s in signals:
        sid = _get_signal_id(s)
        if sid not in grouped_ids:
            s_copy = dict(s)
            if sid not in role_annotations:
                # LLM 没有标注这条，用规则兜底
                ann = _infer_roles_by_rule(s)
                role_annotations[sid] = ann
            s_copy["_role_annotation"] = role_annotations[sid]
            isolated.append(s_copy)

    return StepAResult(
        signal_groups=signal_groups,
        isolated_signals=isolated,
        role_annotations=role_annotations,
        fallback_used=False,
    )


# ──────────────────────────────────────────────
# 规则 Fallback
# ──────────────────────────────────────────────

def _rule_fallback(signals: List[dict]) -> StepAResult:
    """所有信号视为孤立，角色标注用规则推断"""
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
        signal_groups=[],
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
    label = signal.get("signal_label") or signal.get("label", "")
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


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _get_signal_id(signal: dict) -> str:
    return signal.get("signal_id") or signal.get("id") or str(id(signal))


def _load_llm_client(api_key: str, base_url: str):
    try:
        proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(proj_root, "llm_client.py")
        if not os.path.exists(path):
            return None
        spec = importlib.util.spec_from_file_location("llm_client", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.LLMClient(api_key=api_key or "", base_url=base_url or "")
    except Exception:
        return None
