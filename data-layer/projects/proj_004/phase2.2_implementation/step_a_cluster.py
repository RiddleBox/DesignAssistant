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
import queue
import threading
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


class RelationEdge:
    """批内两条信号之间的关系边（内部对象）"""
    def __init__(
        self,
        edge_id: str,
        left_signal_id: str,
        right_signal_id: str,
        edge_type: str,
        strength_band: str,
        gate_passed: bool,
        bucket_scores: Dict[str, float],
        synergy_bonus: float,
        concentration_penalty: float,
        final_score: float,
        reasoning: str,
        shared_affects: Optional[List[str]] = None,
    ):
        self.edge_id = edge_id
        self.left_signal_id = left_signal_id
        self.right_signal_id = right_signal_id
        self.edge_type = edge_type
        self.strength_band = strength_band
        self.gate_passed = gate_passed
        self.bucket_scores = bucket_scores
        self.synergy_bonus = synergy_bonus
        self.concentration_penalty = concentration_penalty
        self.final_score = final_score
        self.reasoning = reasoning
        self.shared_affects = shared_affects or []

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "left_signal_id": self.left_signal_id,
            "right_signal_id": self.right_signal_id,
            "edge_type": self.edge_type,
            "strength_band": self.strength_band,
            "gate_passed": self.gate_passed,
            "bucket_scores": self.bucket_scores,
            "synergy_bonus": self.synergy_bonus,
            "concentration_penalty": self.concentration_penalty,
            "final_score": self.final_score,
            "reasoning": self.reasoning,
            "shared_affects": self.shared_affects,
        }


class ScenarioCandidate:
    """由多条相关边组装出的候选场景（内部对象）"""
    def __init__(
        self,
        candidate_id: str,
        anchor_signal_ids: List[str],
        member_signal_ids: List[str],
        covered_roles: List[str],
        missing_slots: List[str],
        shared_affects: List[str],
        state: str,
        promotion_score: float,
        option_value_score: float,
        novelty_score: float,
        gap_fill_value: float,
        cross_domain_bonus: float,
        reasoning_path: str,
        activated_by: Optional[str] = None,
        last_activated_at: Optional[str] = None,
    ):
        self.candidate_id = candidate_id
        self.anchor_signal_ids = anchor_signal_ids
        self.member_signal_ids = member_signal_ids
        self.covered_roles = covered_roles
        self.missing_slots = missing_slots
        self.shared_affects = shared_affects
        self.state = state
        self.promotion_score = promotion_score
        self.option_value_score = option_value_score
        self.novelty_score = novelty_score
        self.gap_fill_value = gap_fill_value
        self.cross_domain_bonus = cross_domain_bonus
        self.reasoning_path = reasoning_path
        self.activated_by = activated_by
        self.last_activated_at = last_activated_at

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "anchor_signal_ids": self.anchor_signal_ids,
            "member_signal_ids": self.member_signal_ids,
            "covered_roles": self.covered_roles,
            "missing_slots": self.missing_slots,
            "shared_affects": self.shared_affects,
            "state": self.state,
            "promotion_score": self.promotion_score,
            "option_value_score": self.option_value_score,
            "novelty_score": self.novelty_score,
            "gap_fill_value": self.gap_fill_value,
            "cross_domain_bonus": self.cross_domain_bonus,
            "reasoning_path": self.reasoning_path,
            "activated_by": self.activated_by,
            "last_activated_at": self.last_activated_at,
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
        reasoning_path: Optional[str] = None,
        missing_slots: Optional[List[str]] = None,
        scenario_score: Optional[float] = None,
        lane: Optional[str] = None,
    ):
        self.scenario_id = scenario_id
        self.primary_signal_ids = primary_signal_ids
        self.context_signal_ids = context_signal_ids
        self.reasoning = reasoning
        self.opportunity_direction = opportunity_direction
        self.reasoning_path = reasoning_path
        self.missing_slots = missing_slots or []
        self.scenario_score = scenario_score
        self.lane = lane or "primary"

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "primary_signal_ids": self.primary_signal_ids,
            "context_signal_ids": self.context_signal_ids,
            "reasoning": self.reasoning,
            "opportunity_direction": self.opportunity_direction,
            "reasoning_path": self.reasoning_path,
            "missing_slots": self.missing_slots,
            "scenario_score": self.scenario_score,
            "lane": self.lane,
        }


class StepAResult:
    def __init__(
        self,
        logical_scenarios: List[LogicalScenario],  # 主通道场景建议
        isolated_signals: List[dict],              # 含角色标注的全量信号
        role_annotations: Dict[str, dict],         # signal_id → {roles, needs, domains, waiting_for_text}
        exploration_scenarios: Optional[List[LogicalScenario]] = None,
        emerging_links: Optional[List[dict]] = None,
        scenario_candidates: Optional[List[dict]] = None,
        fallback_used: bool = False,
        # 向后兼容：保留 signal_groups 属性，值始终为空列表
        # judgment_engine 迁移完成后可移除
    ):
        self.logical_scenarios = logical_scenarios
        self.isolated_signals = isolated_signals
        self.role_annotations = role_annotations
        self.exploration_scenarios = exploration_scenarios or []
        self.emerging_links = emerging_links or []
        self.scenario_candidates = scenario_candidates or []
        self.fallback_used = fallback_used
        # 兼容旧代码访问 signal_groups
        self.signal_groups: List[List[dict]] = []


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _step_a_debug_log(message: str) -> None:
    if _env_flag("STEP_A_DEBUG", False) or _env_flag("LLM_DEBUG", False):
        print(f"[Step A] {message}", flush=True)


def _run_with_timeout(func, timeout_seconds: int, *args, **kwargs):
    result_queue = queue.Queue(maxsize=1)

    def _target():
        try:
            result_queue.put(("ok", func(*args, **kwargs)))
        except Exception as exc:
            result_queue.put(("error", exc))

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    try:
        status, value = result_queue.get(timeout=timeout_seconds)
    except queue.Empty as exc:
        raise TimeoutError(f"operation timed out after {timeout_seconds}s") from exc

    if status == "error":
        raise value
    return value



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
        step_a_timeout_seconds = max(1, _env_int("STEP_A_LLM_TIMEOUT_SECONDS", 45))
        try:
            _step_a_debug_log(
                f"llm_path_start signals={len(enriched_signals)} model={model} timeout={step_a_timeout_seconds}s"
            )
            result = _run_with_timeout(
                _llm_annotate_and_identify_scenarios,
                step_a_timeout_seconds,
                enriched_signals,
                llm_client,
                model,
            )
            _step_a_debug_log(
                f"llm_path_success logical_scenarios={len(result.logical_scenarios)} exploration={len(result.exploration_scenarios)}"
            )
            return result
        except TimeoutError:
            _step_a_debug_log(f"llm_path_timeout after {step_a_timeout_seconds}s; fallback to rules")
            print(f"[Step A] LLM 调用超时（>{step_a_timeout_seconds}s），使用规则 fallback")
        except Exception as e:
            _step_a_debug_log(f"llm_path_error error={e}")
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

    _step_a_debug_log(
        f"llm_request_prepared signal_lines={len(signals)} prompt_chars={len(prompt)} model={model}"
    )
    raw = client.call(
        prompt=prompt,
        model=model,
        max_tokens=2048,
        temperature=0.2,
    )
    _step_a_debug_log(f"llm_response_received chars={len(raw)}")
    return _parse_step_a_response(raw, signals)


def _build_signals_summary(signals: List[dict]) -> str:
    lines = []
    for i, s in enumerate(signals):
        sid = s.get("signal_id") or s.get("id") or f"s{i}"
        stype = s.get("signal_type", "unknown")
        label = s.get("signal_label") or s.get("label", "")
        desc = s.get("description", "")[:100]
        intensity = s.get("intensity_score") or s.get("intensity", 5)
        logic_frame = s.get("logic_frame") or {}
        what_changed = logic_frame.get("what_changed", "")
        change_direction = logic_frame.get("change_direction", "")
        affects = logic_frame.get("affects", []) or []

        logic_bits = []
        if what_changed:
            logic_bits.append(f"what_changed={what_changed}")
        if change_direction:
            logic_bits.append(f"direction={change_direction}")
        if affects:
            logic_bits.append(f"affects={','.join(affects[:3])}")

        logic_text = f" | logic[{'; '.join(logic_bits)}]" if logic_bits else ""
        lines.append(f"[{sid}] type={stype} intensity={intensity} | {label} | {desc}{logic_text}")
    return "\n".join(lines)


def _build_step_a_prompt(signals_summary: str) -> str:
    return f"""你是一个战略机会分析助手。以下是一批从外部情报中提取的信号，请完成两项任务。

## 当前批次信号

{signals_summary}

## 任务1：逻辑场景识别（软建议，非硬性分组）

识别哪些信号已经可以被组合成一个可上送 `2.3` 的机会假设对象，形成"逻辑场景"建议。注意：
- **Step A 做的是“能否组合成机会”的判断，不做“机会成熟度 / 优先级”判断**：只要信号之间已经形成清晰的逻辑互补结构，就可以上升为场景；不要替 `2.3` 判断这个机会值不值得做、优先级高不高
- **这是建议，不是分组**：你识别出的场景只是给后续分析的参考，分析师可以自由突破场景边界
- 组合依据是"逻辑互补"，不是"语义相似"（见下方典型案例）
- 一个场景需要2条以上信号，核心信号2-4条，上下文信号0-3条
- 可以有多个场景，也可以没有（返回空列表）
- 一条信号可以出现在多个场景中（软建议不需要互斥）
- **优先使用结构化 logic_frame 做判断**：如果信号里带有 `what_changed / direction / affects`，优先依据这些字段判断逻辑互补关系
- **当 logic_frame 缺失时再回退**：回退使用 `signal_type + signal_label + description` 做轻量推理，不要因为缺失 logic_frame 就忽略该信号
- **如果两个信号只是主题相近，但 what_changed 不同且不存在清晰互补链路，不应成场景**
- **如果两个信号 what_changed 相近，但一个是 tighten / decrease，另一个是 loosen / increase，要判断它们是互补、对冲还是彼此否定，不要机械归为同类**
- **同一篇原文里若已经被 2.1 拆成多条 Signal，视为多个独立变化单元进行组合，不要再强行合并回一个模糊大主题**
- **只有在存在明确的逻辑链路时才能成场景**：例如因果链、供需互补、资源响应外部催化、时机信号与需求/资源形成闭环
- **一旦已经形成可解释的机会骨架，就应上升为场景交给 `2.3`**：不要因为信息还不完美，就在 Step A 里提前做价值判断或优先级淘汰
- **仅仅共享行业、主题、新闻类型、公司属性，不足以构成场景**：例如"都是游戏发布""都是融资新闻""都属于AI/游戏赛道"都不成立
- **如果你拿不出清晰的逻辑链，而只能说它们像同一类新闻或同一行业趋势，请返回空列表 []**
- **不确定时宁可少报或不报，也不要为了凑场景而分组**
- **如果一个完整逻辑链依赖3条核心信号（如 catalyst + resource_validation + demand_evidence），这3条都应放在 primary_signal_ids 中；context_signal_ids 只放辅助理解、但不是论点骨架的信号**

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

反例 - 同类资本新闻但互不支撑：
- 信号A：VR 硬件创业公司融资
- 信号B：移动广告测量创业公司融资
- 信号C：云基础设施公司融资
❌ 它们只是都属于融资新闻，彼此不构成一个机会论点，应返回空列表

## 任务2：每条信号角色标注

对每条信号标注：
- roles：该信号在机会论点中扮演的角色（1-2个），从以下选择：
  catalyst / demand_evidence / resource_validation / competitive_gap / execution_risk / timing_signal / negative_validator
- needs：构成完整机会论点，还需要什么角色的信号（0-3个）
- domains：信号所属领域（1-3个），从以下选择：
  gaming / ai / mobile / regulation / capital / geopolitics
- waiting_for_text：一句话（15字以内），描述"这条信号在等待什么样的伙伴信号才能构成机会"
- **每条信号都必须输出非空的 roles 和 domains**
- **如果某条信号与当前任何机会方向都无关，不要留空 roles；请显式标为 negative_validator，并保留至少一个最贴近的 domain**

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

    signal_map = {_get_signal_id(s): s for s in signals}

    role_annotations: Dict[str, dict] = {}
    for ann in data.get("annotations", []):
        sid = ann.get("signal_id", "")
        if sid:
            signal = signal_map.get(sid, {})
            rule_ann = _infer_roles_by_rule(signal) if signal else {
                "roles": ["catalyst"],
                "needs": [],
                "domains": ["gaming"],
                "waiting_for_text": "等待更多证据",
            }
            waiting_for_text = ann.get("waiting_for_text", "")
            if ann.get("roles"):
                roles = ann.get("roles")
            elif _looks_irrelevant_annotation(waiting_for_text):
                roles = ["negative_validator"]
            else:
                roles = rule_ann["roles"]

            domains = ann.get("domains") or rule_ann["domains"]
            if roles == ["negative_validator"]:
                needs = []
            else:
                needs = ann.get("needs") or rule_ann["needs"]

            role_annotations[sid] = {
                "roles": roles,
                "needs": needs,
                "domains": domains,
                "waiting_for_text": waiting_for_text or rule_ann["waiting_for_text"],
            }

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

    return _finalize_step_a_result(
        signals=signals,
        role_annotations=role_annotations,
        base_logical_scenarios=logical_scenarios,
        fallback_used=False,
    )


# ──────────────────────────────────────────────
# Relation Graph v1（批内最小可运行版）
# ──────────────────────────────────────────────

def _finalize_step_a_result(
    signals: List[dict],
    role_annotations: Dict[str, dict],
    base_logical_scenarios: List[LogicalScenario],
    fallback_used: bool,
) -> StepAResult:
    isolated = []
    normalized_annotations: Dict[str, dict] = {}
    for s in signals:
        sid = _get_signal_id(s)
        ann = role_annotations.get(sid) or _infer_roles_by_rule(s)
        normalized_annotations[sid] = ann
        s_copy = dict(s)
        s_copy["_role_annotation"] = ann
        isolated.append(s_copy)

    edges = _build_candidate_edges(isolated)
    candidates = _assemble_scenario_candidates(edges, isolated)
    logical_scenarios = _merge_primary_scenarios(base_logical_scenarios, candidates, isolated)
    exploration_scenarios = _select_exploration_scenarios(
        candidates,
        logical_scenarios,
        isolated,
    )
    emerging_links = _extract_emerging_links(edges)

    return StepAResult(
        logical_scenarios=logical_scenarios,
        isolated_signals=isolated,
        role_annotations=normalized_annotations,
        exploration_scenarios=exploration_scenarios,
        emerging_links=emerging_links,
        scenario_candidates=[c.to_dict() for c in candidates],
        fallback_used=fallback_used,
    )


def _build_candidate_edges(signals: List[dict]) -> List[RelationEdge]:
    edges: List[RelationEdge] = []
    for i in range(len(signals)):
        for j in range(i + 1, len(signals)):
            left = signals[i]
            right = signals[j]
            bucket_scores = _score_edge_buckets(left, right)
            synergy_bonus = _compute_synergy_bonus(left, right)
            concentration_penalty = _compute_concentration_penalty(left, right)
            edge_type = _infer_edge_type(left, right)
            contradiction_penalty = 0.45 if edge_type == "contradictory" else 0.0
            final_score = round(
                bucket_scores["structural"]
                + bucket_scores["role_fit"]
                + bucket_scores["domain_fit"]
                + bucket_scores["signal_strength"]
                + synergy_bonus
                - concentration_penalty
                - contradiction_penalty,
                3,
            )
            gate_passed = edge_type != "contradictory" and final_score >= 0.55
            strength_band = _classify_edge_strength(final_score, gate_passed)
            shared_affects = _shared_affects(left, right)
            reasoning = _build_edge_reasoning(left, right, edge_type, shared_affects)
            edges.append(RelationEdge(
                edge_id=f"edge_{_get_signal_id(left)}_{_get_signal_id(right)}",
                left_signal_id=_get_signal_id(left),
                right_signal_id=_get_signal_id(right),
                edge_type=edge_type,
                strength_band=strength_band,
                gate_passed=gate_passed,
                bucket_scores=bucket_scores,
                synergy_bonus=round(synergy_bonus, 3),
                concentration_penalty=round(concentration_penalty, 3),
                final_score=final_score,
                reasoning=reasoning,
                shared_affects=shared_affects,
            ))
    return edges


def _score_edge_buckets(left: dict, right: dict) -> Dict[str, float]:
    left_roles = set(_get_roles(left))
    right_roles = set(_get_roles(right))
    left_needs = set(_get_needs(left))
    right_needs = set(_get_needs(right))
    left_domains = set(_get_domains(left))
    right_domains = set(_get_domains(right))

    shared_affects = _shared_affects(left, right)
    same_change = _same_what_changed(left, right)

    structural = 0.0
    if shared_affects:
        structural += min(0.4, 0.2 * len(shared_affects))
    if same_change:
        structural += 0.15

    role_fit = 0.0
    if left_roles.intersection(right_needs) or right_roles.intersection(left_needs):
        role_fit += 0.35
    elif left_roles.intersection(right_roles):
        role_fit += 0.15

    domain_fit = 0.0
    if left_domains.intersection(right_domains):
        domain_fit += 0.15
    if left.get("signal_type") != right.get("signal_type"):
        domain_fit += 0.1

    avg_intensity = (
        int(left.get("intensity_score") or left.get("intensity") or 5)
        + int(right.get("intensity_score") or right.get("intensity") or 5)
    ) / 2
    signal_strength = min(0.15, avg_intensity / 50)

    return {
        "structural": round(structural, 3),
        "role_fit": round(role_fit, 3),
        "domain_fit": round(domain_fit, 3),
        "signal_strength": round(signal_strength, 3),
    }


def _infer_edge_type(left: dict, right: dict) -> str:
    left_roles = set(_get_roles(left))
    right_roles = set(_get_roles(right))

    if _has_direction_conflict(left, right) and (_same_what_changed(left, right) or _shared_affects(left, right)):
        return "contradictory"
    if {"catalyst", "resource_validation"}.issubset(left_roles.union(right_roles)):
        return "resource_enablement"
    if {"catalyst", "demand_evidence"}.issubset(left_roles.union(right_roles)):
        return "demand_validation"
    if _is_constraint_release_pair(left, right):
        return "constraint_release"
    if _shared_affects(left, right) or _same_what_changed(left, right):
        return "reinforcing"
    return "complementary"


def _classify_edge_strength(final_score: float, gate_passed: bool) -> str:
    if not gate_passed:
        return "weak"
    if final_score >= 0.8:
        return "strong"
    if final_score >= 0.55:
        return "emerging"
    return "weak"


def _assemble_scenario_candidates(edges: List[RelationEdge], signals: List[dict]) -> List[ScenarioCandidate]:
    signal_map = {_get_signal_id(s): s for s in signals}
    adjacency: Dict[str, set] = {}
    edge_map: Dict[frozenset, RelationEdge] = {}

    for edge in edges:
        if not edge.gate_passed:
            continue
        pair_key = frozenset({edge.left_signal_id, edge.right_signal_id})
        edge_map[pair_key] = edge
        adjacency.setdefault(edge.left_signal_id, set()).add(edge.right_signal_id)
        adjacency.setdefault(edge.right_signal_id, set()).add(edge.left_signal_id)

    visited = set()
    candidates: List[ScenarioCandidate] = []
    for sid in adjacency:
        if sid in visited:
            continue
        stack = [sid]
        component = []
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            stack.extend(list(adjacency.get(node, set()) - visited))

        if len(component) < 2:
            continue

        component_signals = [signal_map[cid] for cid in component if cid in signal_map]
        component_edges = []
        for i in range(len(component)):
            for j in range(i + 1, len(component)):
                edge = edge_map.get(frozenset({component[i], component[j]}))
                if edge:
                    component_edges.append(edge)

        covered_roles = sorted({
            role
            for signal in component_signals
            for role in _get_roles(signal)
            if role != "negative_validator"
        })
        missing_slots = [
            role for role in ["catalyst", "demand_evidence", "resource_validation"]
            if role not in covered_roles
        ]
        shared_affects = _collect_component_affects(component_signals)
        promotion_score = _compute_promotion_score(component_edges, covered_roles, component_signals)
        option_value_score = _compute_option_value_score(component_signals, shared_affects, missing_slots)
        novelty_score = _compute_novelty_score(component_signals)
        gap_fill_value = round(1 - (len(missing_slots) / 3), 3)
        cross_domain_bonus = _compute_cross_domain_bonus(component_signals)
        state = _derive_candidate_state(promotion_score, option_value_score, covered_roles)
        anchors = _select_anchor_signal_ids(component_signals)
        reasoning_path = _build_candidate_reasoning_path(component_signals, covered_roles, shared_affects, missing_slots)

        candidates.append(ScenarioCandidate(
            candidate_id=f"candidate_{len(candidates)+1}",
            anchor_signal_ids=anchors,
            member_signal_ids=sorted(component),
            covered_roles=covered_roles,
            missing_slots=missing_slots,
            shared_affects=shared_affects,
            state=state,
            promotion_score=promotion_score,
            option_value_score=option_value_score,
            novelty_score=novelty_score,
            gap_fill_value=gap_fill_value,
            cross_domain_bonus=cross_domain_bonus,
            reasoning_path=reasoning_path,
        ))

    candidates.sort(key=lambda c: (c.promotion_score, c.option_value_score), reverse=True)
    return candidates


def _compute_promotion_score(edges: List[RelationEdge], covered_roles: List[str], signals: List[dict]) -> float:
    if edges:
        avg_edge_score = sum(e.final_score for e in edges) / len(edges)
    else:
        avg_edge_score = 0.0
    role_coverage = len([r for r in ["catalyst", "demand_evidence", "resource_validation"] if r in covered_roles]) / 3
    cross_domain_bonus = _compute_cross_domain_bonus(signals)
    return round(min(1.0, avg_edge_score * 0.6 + role_coverage * 0.25 + cross_domain_bonus * 0.5), 3)


def _compute_option_value_score(signals: List[dict], shared_affects: List[str], missing_slots: List[str]) -> float:
    if not signals:
        return 0.0
    max_intensity = max(int(s.get("intensity_score") or s.get("intensity") or 5) for s in signals) / 10
    affect_bonus = 0.2 if shared_affects else 0.0
    incompleteness_bonus = 0.2 if 0 < len(missing_slots) <= 2 else 0.05
    return round(min(1.0, max_intensity * 0.55 + affect_bonus + incompleteness_bonus), 3)


def _compute_novelty_score(signals: List[dict]) -> float:
    unique_domains = sorted({d for s in signals for d in _get_domains(s)})
    return round(min(1.0, len(unique_domains) / 4), 3)


def _compute_cross_domain_bonus(signals: List[dict]) -> float:
    unique_domains = sorted({d for s in signals for d in _get_domains(s)})
    if len(unique_domains) <= 1:
        return 0.0
    return round(min(0.2, (len(unique_domains) - 1) * 0.1), 3)


def _select_primary_scenarios(candidates: List[ScenarioCandidate], signals: List[dict]) -> List[LogicalScenario]:
    signal_map = {_get_signal_id(s): s for s in signals}
    scenarios: List[LogicalScenario] = []
    for candidate in candidates:
        if candidate.state not in {"opportunity_assembled", "opportunity_partial"}:
            continue
        member_ids = [sid for sid in candidate.member_signal_ids if sid in signal_map]
        if len(member_ids) < 2:
            continue
        primary_ids = member_ids[:3]
        context_ids = member_ids[3:6]
        scenarios.append(LogicalScenario(
            scenario_id=candidate.candidate_id,
            primary_signal_ids=primary_ids,
            context_signal_ids=context_ids,
            reasoning=candidate.reasoning_path,
            opportunity_direction=_infer_opportunity_direction(candidate, signal_map),
            reasoning_path=candidate.reasoning_path,
            missing_slots=candidate.missing_slots,
            scenario_score=candidate.promotion_score,
            lane="primary",
        ))
    return scenarios


def _select_exploration_scenarios(
    candidates: List[ScenarioCandidate],
    primary_scenarios: List[LogicalScenario],
    signals: List[dict],
) -> List[LogicalScenario]:
    signal_map = {_get_signal_id(s): s for s in signals}
    primary_keys = {_scenario_member_key(scenario) for scenario in primary_scenarios}
    exploration: List[LogicalScenario] = []
    for candidate in candidates:
        if candidate.state != "link_emerging":
            continue
        if candidate.option_value_score < 0.55:
            continue
        member_ids = [sid for sid in candidate.member_signal_ids if sid in signal_map]
        if len(member_ids) < 2:
            continue
        scenario = LogicalScenario(
            scenario_id=f"exp_{candidate.candidate_id}",
            primary_signal_ids=member_ids[:2],
            context_signal_ids=member_ids[2:5],
            reasoning=f"探索通道：{candidate.reasoning_path}",
            opportunity_direction=_infer_opportunity_direction(candidate, signal_map),
            reasoning_path=candidate.reasoning_path,
            missing_slots=candidate.missing_slots,
            scenario_score=candidate.option_value_score,
            lane="exploration",
        )
        key = _scenario_member_key(scenario)
        if key in primary_keys:
            continue
        primary_keys.add(key)
        exploration.append(scenario)
    return exploration


def _extract_emerging_links(edges: List[RelationEdge]) -> List[dict]:
    return [
        edge.to_dict()
        for edge in edges
        if edge.gate_passed and edge.strength_band == "emerging"
    ]


def _merge_primary_scenarios(
    base_logical_scenarios: List[LogicalScenario],
    candidates: List[ScenarioCandidate],
    signals: List[dict],
) -> List[LogicalScenario]:
    merged: List[LogicalScenario] = []
    seen = set()

    for scenario in base_logical_scenarios:
        if not scenario.reasoning_path:
            scenario.reasoning_path = scenario.reasoning
        if scenario.scenario_score is None:
            scenario.scenario_score = 0.8
        scenario.lane = scenario.lane or "primary"
        key = _scenario_member_key(scenario)
        if key in seen:
            continue
        seen.add(key)
        merged.append(scenario)

    for scenario in _select_primary_scenarios(candidates, signals):
        key = _scenario_member_key(scenario)
        if key in seen:
            continue
        seen.add(key)
        merged.append(scenario)

    return merged


def _compute_synergy_bonus(left: dict, right: dict) -> float:
    roles = set(_get_roles(left)).union(_get_roles(right))
    bonus = 0.0
    if "catalyst" in roles and "resource_validation" in roles:
        bonus += 0.08
    if "catalyst" in roles and "demand_evidence" in roles:
        bonus += 0.08
    if len(_shared_affects(left, right)) >= 2:
        bonus += 0.05
    return min(0.2, bonus)


def _compute_concentration_penalty(left: dict, right: dict) -> float:
    penalty = 0.0
    if left.get("signal_type") == right.get("signal_type"):
        penalty += 0.06
    if len(set(_get_domains(left)).union(_get_domains(right))) <= 1:
        penalty += 0.04
    return min(0.12, penalty)


def _has_direction_conflict(left: dict, right: dict) -> bool:
    left_direction = _normalize_text((_get_logic_frame(left).get("change_direction") or ""))
    right_direction = _normalize_text((_get_logic_frame(right).get("change_direction") or ""))
    if not left_direction or not right_direction:
        return False
    opposite_pairs = {
        ("increase", "decrease"),
        ("decrease", "increase"),
        ("tighten", "loosen"),
        ("loosen", "tighten"),
        ("up", "down"),
        ("down", "up"),
    }
    return (left_direction, right_direction) in opposite_pairs


def _is_constraint_release_pair(left: dict, right: dict) -> bool:
    directions = {
        _normalize_text((_get_logic_frame(left).get("change_direction") or "")),
        _normalize_text((_get_logic_frame(right).get("change_direction") or "")),
    }
    roles = set(_get_roles(left)).union(_get_roles(right))
    return bool(directions.intersection({"loosen", "decrease"})) and "resource_validation" in roles


def _build_edge_reasoning(left: dict, right: dict, edge_type: str, shared_affects: List[str]) -> str:
    left_label = left.get("signal_label") or left.get("label") or _get_signal_id(left)
    right_label = right.get("signal_label") or right.get("label") or _get_signal_id(right)
    affect_text = f"，共同指向 {', '.join(shared_affects[:2])}" if shared_affects else ""
    return f"{left_label} 与 {right_label} 形成 {edge_type} 关系{affect_text}"


def _collect_component_affects(signals: List[dict]) -> List[str]:
    counter: Dict[str, int] = {}
    for signal in signals:
        for affect in _get_affects(signal):
            counter[affect] = counter.get(affect, 0) + 1
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, count in ranked if count >= 2][:3] or [name for name, _ in ranked[:2]]


def _derive_candidate_state(promotion_score: float, option_value_score: float, covered_roles: List[str]) -> str:
    essential_count = len([r for r in ["catalyst", "demand_evidence", "resource_validation"] if r in covered_roles])
    if promotion_score >= 0.72 and essential_count >= 2:
        return "opportunity_assembled"
    if promotion_score >= 0.58 or option_value_score >= 0.65:
        return "opportunity_partial"
    if option_value_score >= 0.5:
        return "link_emerging"
    return "link_seed"


def _select_anchor_signal_ids(signals: List[dict]) -> List[str]:
    ranked = sorted(
        signals,
        key=lambda s: int(s.get("intensity_score") or s.get("intensity") or 5),
        reverse=True,
    )
    return [_get_signal_id(s) for s in ranked[:2]]


def _build_candidate_reasoning_path(
    signals: List[dict],
    covered_roles: List[str],
    shared_affects: List[str],
    missing_slots: List[str],
) -> str:
    labels = [s.get("signal_label") or s.get("label") or _get_signal_id(s) for s in signals[:3]]
    affect_text = f"，共同影响 {', '.join(shared_affects[:2])}" if shared_affects else ""
    missing_text = f"，仍缺 {_roles_to_text(missing_slots)}" if missing_slots else ""
    return f"{' + '.join(labels)} 形成 {', '.join(covered_roles[:3])} 的互补结构{affect_text}{missing_text}"


def _infer_opportunity_direction(candidate: ScenarioCandidate, signal_map: Dict[str, dict]) -> str:
    if candidate.shared_affects:
        return f"围绕 {candidate.shared_affects[0]} 的机会窗口"
    domains = sorted({d for sid in candidate.member_signal_ids for d in _get_domains(signal_map.get(sid, {}))})
    if domains:
        return f"{domains[0]} 相关机会方向"
    return "潜在机会方向待验证"


def _scenario_member_key(scenario: LogicalScenario) -> str:
    return "|".join(sorted(set(scenario.primary_signal_ids + scenario.context_signal_ids)))


def _get_logic_frame(signal: dict) -> dict:
    return signal.get("logic_frame") or {}


def _get_roles(signal: dict) -> List[str]:
    return list((signal.get("_role_annotation") or {}).get("roles", []))


def _get_needs(signal: dict) -> List[str]:
    return list((signal.get("_role_annotation") or {}).get("needs", []))


def _get_domains(signal: dict) -> List[str]:
    domains = list((signal.get("_role_annotation") or {}).get("domains", []))
    return domains or ["gaming"]


def _get_affects(signal: dict) -> List[str]:
    affects = (_get_logic_frame(signal).get("affects") or [])
    if isinstance(affects, str):
        affects = [affects]
    return [_normalize_text(v) for v in affects if _normalize_text(v)]


def _shared_affects(left: dict, right: dict) -> List[str]:
    return sorted(set(_get_affects(left)).intersection(_get_affects(right)))


def _same_what_changed(left: dict, right: dict) -> bool:
    left_value = _normalize_text((_get_logic_frame(left).get("what_changed") or ""))
    right_value = _normalize_text((_get_logic_frame(right).get("what_changed") or ""))
    return bool(left_value and left_value == right_value)


def _normalize_text(value: str) -> str:
    return str(value or "").strip().lower()


def _roles_to_text(roles: List[str]) -> str:
    if not roles:
        return "无"
    return ", ".join(_role_cn(role) for role in roles)


# ──────────────────────────────────────────────
# 规则 Fallback
# ──────────────────────────────────────────────

def _rule_fallback(signals: List[dict]) -> StepAResult:
    """LLM 失败时：无 logical_scenarios，所有信号视为孤立，角色标注用规则推断"""
    role_annotations = {}
    for s in signals:
        sid = _get_signal_id(s)
        role_annotations[sid] = _infer_roles_by_rule(s)
    return _finalize_step_a_result(
        signals=signals,
        role_annotations=role_annotations,
        base_logical_scenarios=[],
        fallback_used=True,
    )


def _looks_irrelevant_annotation(waiting_for_text: str) -> bool:
    text = (waiting_for_text or "").lower()
    markers = ["无关", "不相关", "irrelevant", "unrelated", "noise"]
    return any(marker in text for marker in markers)


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
