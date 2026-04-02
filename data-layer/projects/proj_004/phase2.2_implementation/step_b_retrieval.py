"""
Phase 2.2 Step B — 历史关系唤醒（分层漏斗）

四层漏斗：
  L1: Tag 粗筛  — 优先查等待补槽的 scenario memories，再查 emerging links，最后查历史 pending 信号
  L2: 规则硬过滤 — domain/shared_affects + 时间窗口 + 有效强度 + 排除已尝试组合
  L3: 暂缓（MVP 阶段不实现 embedding 精排，待 L1+L2 效果验证后决定）
  L4: LLM 轻量确认 — 有没有已经成形、值得进入 Step C 的机会逻辑

设计原则：
- `signal_entry / emerging_link / scenario_memory` 都是机会前状态，不是机会本身
- 只有已经形成“最小可解释机会逻辑”的候选，才进入 Step C
- 仍未形成机会但有补槽/关系价值的候选，只保留为 store-for-later，不上送 Step C
- L1+L2 纯规则，零 LLM 调用
- L4 只在已有 Step C-ready 候选组时触发，每条孤立信号最多 1 次 haiku 调用
- 返回 Step C-ready 候选组合；若只有 latent 候选，则当前信号继续写入 Signal Store
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Optional

from signal_store import SignalStore, SignalEntry, EmergingLink, ScenarioMemory

CORE_ROLES = ["catalyst", "demand_evidence", "resource_validation"]

# L2 / 分流参数（可配置）
L2_TIME_WINDOW_DAYS = 90
L2_MIN_EFFECTIVE_INTENSITY = 4
L2_MAX_GROUPS = 8
L2_MAX_CANDIDATES = 20
STEP_C_READY_LIMIT = 4
STORE_FOR_LATER_LIMIT = 3
EXPLORATION_MIN_SCORE = 0.52
DORMANT_REACTIVATION_DAYS = 21
L4_SKIP_THRESHOLD = 0

ROUTE_STEP_C_READY = "step_c_ready"
ROUTE_STORE_FOR_LATER = "store_for_later"
ROUTE_DISCARD = "discard"


class CandidateGroupInfo:
    def __init__(
        self,
        group_id: str,
        entries: List[SignalEntry],
        source_kind: str,
        rank_score: float,
        route: str,
        route_reason: str,
        slot_fill_count: int = 0,
        core_role_coverage: int = 0,
        domain_overlap_count: int = 0,
        dormant_reactivation: bool = False,
        scenario: Optional[ScenarioMemory] = None,
        link: Optional[EmergingLink] = None,
    ):
        self.group_id = group_id
        self.entries = entries
        self.source_kind = source_kind
        self.rank_score = round(rank_score, 3)
        self.route = route
        self.route_reason = route_reason
        self.slot_fill_count = slot_fill_count
        self.core_role_coverage = core_role_coverage
        self.domain_overlap_count = domain_overlap_count
        self.dormant_reactivation = dormant_reactivation
        self.scenario = scenario
        self.link = link

    def group_key(self) -> tuple:
        return tuple(sorted(entry.signal_id for entry in self.entries))

    def original_group_key(self) -> tuple:
        return tuple(sorted(getattr(entry, "original_signal_id", entry.signal_id) for entry in self.entries))


class StepBResult:
    def __init__(
        self,
        candidate_groups: List[List[SignalEntry]],
        current_signal_id: str,
        matched: bool,
        matched_links: Optional[List[EmergingLink]] = None,
        matched_scenarios: Optional[List[ScenarioMemory]] = None,
        fallback_used: bool = False,
        candidate_group_infos: Optional[List[CandidateGroupInfo]] = None,
        latent_candidate_group_infos: Optional[List[CandidateGroupInfo]] = None,
    ):
        self.candidate_groups = candidate_groups
        self.current_signal_id = current_signal_id
        self.matched = matched
        self.matched_links = matched_links or []
        self.matched_scenarios = matched_scenarios or []
        self.fallback_used = fallback_used
        self.candidate_group_infos = candidate_group_infos or []
        self.latent_candidate_group_infos = latent_candidate_group_infos or []
        self.ready_candidate_groups = [info.entries for info in self.candidate_group_infos if info.route == ROUTE_STEP_C_READY]
        self.store_candidate_groups = [info.entries for info in self.latent_candidate_group_infos if info.route == ROUTE_STORE_FOR_LATER]


def run_step_b(
    isolated_signal: dict,
    signal_store: SignalStore,
    llm_client=None,
    model: str = "claude-haiku-4-5",
) -> StepBResult:
    sid = _get_signal_id(isolated_signal)
    annotation = isolated_signal.get("_role_annotation", {})
    roles = annotation.get("roles", [])
    domains = annotation.get("domains", [])

    scenario_hits = _retrieve_scenario_memory_candidates(
        isolated_signal=isolated_signal,
        signal_store=signal_store,
        roles=roles,
        domains=domains,
    )
    link_hits = _retrieve_emerging_link_candidates(
        isolated_signal=isolated_signal,
        signal_store=signal_store,
        roles=roles,
        domains=domains,
    )
    signal_hits = _retrieve_pending_signal_candidates(
        isolated_signal=isolated_signal,
        signal_store=signal_store,
        roles=roles,
        domains=domains,
    )

    ranked_infos = _merge_and_rank_candidates(
        isolated_signal=isolated_signal,
        signal_store=signal_store,
        scenario_hits=scenario_hits,
        link_hits=link_hits,
        signal_hits=signal_hits,
    )
    ready_infos, latent_infos = _select_candidate_infos_for_step_c(ranked_infos)

    if not ready_infos:
        if latent_infos:
            _log_group_attempts(signal_store, isolated_signal, latent_infos)
            return _build_step_b_result(
                current_signal_id=sid,
                candidate_infos=[],
                latent_candidate_infos=latent_infos,
                fallback_used=False,
            )
        return StepBResult([], sid, matched=False)

    if llm_client and len(ready_infos) > L4_SKIP_THRESHOLD:
        try:
            llm_result = _l4_llm_confirm(
                current=isolated_signal,
                candidate_infos=ready_infos,
                client=llm_client,
                model=model,
            )
            confirmed_infos = _normalize_l4_result(llm_result, ready_infos)
            if confirmed_infos:
                _log_group_attempts(signal_store, isolated_signal, confirmed_infos)
                return _build_step_b_result(
                    current_signal_id=sid,
                    candidate_infos=confirmed_infos,
                    latent_candidate_infos=latent_infos,
                    fallback_used=False,
                )
        except Exception as ex:
            print(f"[Step B] L4 LLM 确认失败: {ex}，退化为规则候选")

    _log_group_attempts(signal_store, isolated_signal, ready_infos)
    return _build_step_b_result(
        current_signal_id=sid,
        candidate_infos=ready_infos,
        latent_candidate_infos=latent_infos,
        fallback_used=True,
    )


# ──────────────────────────────────────────────
# L1: 三层召回
# ──────────────────────────────────────────────

def _retrieve_pending_signal_candidates(
    isolated_signal: dict,
    signal_store: SignalStore,
    roles: List[str],
    domains: List[str],
) -> List[SignalEntry]:
    sid = _get_signal_id(isolated_signal)
    l1_candidates: List[SignalEntry] = []
    for role in roles:
        hits = signal_store.query_by_role(role=role, exclude_ids=[sid])
        l1_candidates.extend(hits)

    seen = set()
    unique = []
    for entry in l1_candidates:
        if entry.signal_id in seen:
            continue
        seen.add(entry.signal_id)
        unique.append(entry)
    return _l2_filter_signals(isolated_signal, unique, domains)


def _retrieve_emerging_link_candidates(
    isolated_signal: dict,
    signal_store: SignalStore,
    roles: List[str],
    domains: List[str],
) -> List[EmergingLink]:
    exclude_ids = [_get_signal_id(isolated_signal)]
    hits = signal_store.query_matching_links(
        roles=roles,
        domains=domains,
        exclude_signal_ids=exclude_ids,
        active_only=True,
    )
    return _l2_filter_links(hits)


def _retrieve_scenario_memory_candidates(
    isolated_signal: dict,
    signal_store: SignalStore,
    roles: List[str],
    domains: List[str],
) -> List[ScenarioMemory]:
    exclude_ids = [_get_signal_id(isolated_signal)]
    hits = signal_store.query_matching_scenarios(
        roles=roles,
        domains=domains,
        exclude_signal_ids=exclude_ids,
        active_only=True,
    )
    return _l2_filter_scenarios(hits)


# ──────────────────────────────────────────────
# L2: 规则过滤
# ──────────────────────────────────────────────

def _l2_filter_signals(
    current: dict,
    candidates: List[SignalEntry],
    current_domains: List[str],
) -> List[SignalEntry]:
    current_domain_set = set(current_domains or [])
    current_sid = _get_signal_id(current)
    current_time = datetime.now(timezone.utc)
    current_signal_type = current.get("signal_type", "")

    results = []
    for entry in candidates:
        domain_overlap = bool(current_domain_set.intersection(set(entry.domains)))
        type_complement = bool(current_signal_type) and current_signal_type != entry.signal_type
        if not domain_overlap and not type_complement:
            continue
        if not _within_time_window(entry.created_at, current_time):
            continue
        if entry.effective_intensity() < L2_MIN_EFFECTIVE_INTENSITY:
            continue
        if current_sid in entry.attempt_log or entry.signal_id in current.get("_attempt_log", []):
            continue
        results.append(entry)

    results.sort(key=lambda item: item.effective_intensity(), reverse=True)
    return results[:L2_MAX_CANDIDATES]


def _l2_filter_links(candidates: List[EmergingLink]) -> List[EmergingLink]:
    results = []
    current_time = datetime.now(timezone.utc)
    for link in candidates:
        if link.status != "active":
            continue
        if link.final_score < 0.45:
            continue
        if not _within_time_window(link.created_at, current_time):
            continue
        results.append(link)
    results.sort(key=lambda item: (item.final_score, item.activation_count), reverse=True)
    return results[:L2_MAX_GROUPS]


def _l2_filter_scenarios(candidates: List[ScenarioMemory]) -> List[ScenarioMemory]:
    results = []
    current_time = datetime.now(timezone.utc)
    for memory in candidates:
        if memory.status != "active":
            continue
        if max(memory.option_value_score, memory.promotion_score) < 0.5:
            continue
        if not _within_time_window(memory.created_at, current_time):
            continue
        results.append(memory)
    results.sort(key=lambda item: (item.gap_fill_value, item.promotion_score, item.option_value_score), reverse=True)
    return results[:L2_MAX_GROUPS]


# ──────────────────────────────────────────────
# 候选合并、统一排序与分流
# ──────────────────────────────────────────────

def _merge_and_rank_candidates(
    isolated_signal: dict,
    signal_store: SignalStore,
    scenario_hits: List[ScenarioMemory],
    link_hits: List[EmergingLink],
    signal_hits: List[SignalEntry],
) -> List[CandidateGroupInfo]:
    ranked_infos: List[CandidateGroupInfo] = []
    current_id = _get_signal_id(isolated_signal)

    for memory in scenario_hits:
        group = signal_store.get_entries_by_original_signal_ids(memory.member_signal_ids)
        group = [entry for entry in group if getattr(entry, "original_signal_id", None) != current_id]
        if not group:
            continue
        metrics = _build_group_metrics(isolated_signal, group, slot_targets=memory.missing_slots)
        route, reason = _route_scenario_candidate(memory, metrics)
        rank_score = _score_scenario_candidate(memory, metrics, route)
        ranked_infos.append(CandidateGroupInfo(
            group_id=f"scenario::{memory.scenario_id}",
            entries=group,
            source_kind="scenario_memory",
            rank_score=rank_score,
            route=route,
            route_reason=reason,
            slot_fill_count=metrics["slot_fill_count"],
            core_role_coverage=metrics["core_role_coverage"],
            domain_overlap_count=metrics["domain_overlap_count"],
            dormant_reactivation=metrics["dormant_reactivation"],
            scenario=memory,
        ))

    for link in link_hits:
        group = signal_store.get_entries_by_original_signal_ids(link.signal_ids)
        group = [entry for entry in group if getattr(entry, "original_signal_id", None) != current_id]
        if not group:
            continue
        metrics = _build_group_metrics(isolated_signal, group)
        route, reason = _route_link_candidate(link, metrics)
        rank_score = _score_link_candidate(link, metrics, route)
        ranked_infos.append(CandidateGroupInfo(
            group_id=f"link::{link.link_id}",
            entries=group,
            source_kind="emerging_link",
            rank_score=rank_score,
            route=route,
            route_reason=reason,
            slot_fill_count=metrics["slot_fill_count"],
            core_role_coverage=metrics["core_role_coverage"],
            domain_overlap_count=metrics["domain_overlap_count"],
            dormant_reactivation=metrics["dormant_reactivation"],
            link=link,
        ))

    for entry in signal_hits:
        metrics = _build_group_metrics(isolated_signal, [entry], slot_targets=entry.needs)
        route, reason = _route_signal_candidate(entry, metrics)
        rank_score = _score_signal_candidate(entry, metrics, route)
        ranked_infos.append(CandidateGroupInfo(
            group_id=f"signal::{entry.signal_id}",
            entries=[entry],
            source_kind="signal_entry",
            rank_score=rank_score,
            route=route,
            route_reason=reason,
            slot_fill_count=metrics["slot_fill_count"],
            core_role_coverage=metrics["core_role_coverage"],
            domain_overlap_count=metrics["domain_overlap_count"],
            dormant_reactivation=metrics["dormant_reactivation"],
        ))

    ranked_infos.sort(
        key=lambda info: (
            _route_priority(info.route),
            _source_kind_priority(info.source_kind),
            info.slot_fill_count,
            info.core_role_coverage,
            info.rank_score,
            info.domain_overlap_count,
        ),
        reverse=True,
    )
    return _dedupe_candidate_infos(ranked_infos)


def _select_candidate_infos_for_step_c(candidate_infos: List[CandidateGroupInfo]):
    ready_infos = [info for info in candidate_infos if info.route == ROUTE_STEP_C_READY][:STEP_C_READY_LIMIT]
    latent_infos = [info for info in candidate_infos if info.route == ROUTE_STORE_FOR_LATER][:STORE_FOR_LATER_LIMIT]
    return ready_infos[:L2_MAX_GROUPS], latent_infos[:L2_MAX_GROUPS]


def _dedupe_candidate_infos(candidate_infos: List[CandidateGroupInfo]) -> List[CandidateGroupInfo]:
    results = []
    seen = set()
    for info in candidate_infos:
        key = info.group_key()
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(info)
    return results


# ──────────────────────────────────────────────
# L4: LLM 轻量确认
# ──────────────────────────────────────────────

def _l4_llm_confirm(
    current: dict,
    candidate_infos: List[CandidateGroupInfo],
    client,
    model: str,
):
    prompt = _build_l4_prompt(current, candidate_infos)
    raw = client.call(
        prompt=prompt,
        model=model,
        max_tokens=1200,
        temperature=0.1,
    )
    return _parse_l4_response(raw, candidate_infos)


def _build_l4_prompt(
    current: dict,
    candidate_infos: List[CandidateGroupInfo],
) -> str:
    annotation = current.get("_role_annotation", {})
    current_desc = (
        f"当前信号：{current.get('signal_label') or current.get('label', '')}\n"
        f"类型：{current.get('signal_type', '')}\n"
        f"描述：{current.get('description', '')[:150]}\n"
        f"角色：{annotation.get('roles', [])}\n"
        f"在等待：{annotation.get('waiting_for_text', '')}"
    )

    group_desc = []
    for index, info in enumerate(candidate_infos, start=1):
        group_id = f"G{index}"
        member_desc = "; ".join(
            f"{entry.signal_label}(roles={entry.roles}, type={entry.signal_type})"
            for entry in info.entries
        )
        meta_parts = [
            f"source={info.source_kind}",
            f"route={info.route}",
            f"score={info.rank_score}",
            f"slot_fill={info.slot_fill_count}",
            f"core_roles={info.core_role_coverage}",
            f"reason={info.route_reason}",
        ]
        if info.scenario:
            meta_parts.append(f"scenario={info.scenario.scenario_id}")
            meta_parts.append(f"missing_slots={info.scenario.missing_slots}")
        if info.link:
            meta_parts.append(f"link={info.link.link_id}")
            meta_parts.append(f"edge_type={info.link.edge_type}")
        group_desc.append(f"[{group_id}] {member_desc} | {' | '.join(meta_parts)}")

    return f"""你是战略机会分析助手。判断以下历史关系候选中，有没有已经能与当前信号构成“最小可解释机会逻辑”的组合。 

## 当前信号
{current_desc}

## 历史候选组
{chr(10).join(group_desc)}

## 判断原则
- 只有已经形成机会逻辑的组合，才保留为 Step C 候选
- 形成关系、补到部分 scenario、或在本类别里分数较高，都不足以直接进入 Step C
- 若已命中 scenario memory，关注它是否被当前信号补成了可解释的机会闭环
- 若已命中 emerging link，关注它是否从“有关系”升级为“有机会语义”
- 若只是强 signal pair，只有在它已经明显构成最小机会逻辑时才保留

## 输出格式（严格 JSON）
```json
{{
  "has_combination": true,
  "combinations": [
    {{
      "group_ids": ["G1"],
      "logic_chain": "一句话说明为何该组已形成最小机会逻辑"
    }}
  ]
}}
```

如果没有可行组合，has_combination=false，combinations=[]。
"""


def _parse_l4_response(raw: str, candidate_infos: List[CandidateGroupInfo]) -> List[CandidateGroupInfo]:
    try:
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
    except Exception:
        return []

    if not data.get("has_combination"):
        return []

    info_map = {f"G{i+1}": info for i, info in enumerate(candidate_infos)}
    selected = []
    seen = set()
    for combo in data.get("combinations", []):
        for group_id in combo.get("group_ids", []):
            info = info_map.get(group_id)
            if not info:
                continue
            key = info.group_key()
            if key in seen:
                continue
            seen.add(key)
            selected.append(info)
    return selected


# ──────────────────────────────────────────────
# 统一度量、路由与打分
# ──────────────────────────────────────────────

def _build_group_metrics(
    current: dict,
    group: List[SignalEntry],
    slot_targets: List[str] = None,
) -> Dict[str, float]:
    current_roles = set(current.get("_role_annotation", {}).get("roles", []))
    current_domains = set(current.get("_role_annotation", {}).get("domains", []))
    group_roles = {role for entry in group for role in (entry.roles or [])}
    group_domains = {domain for entry in group for domain in (entry.domains or [])}
    all_roles = current_roles.union(group_roles)

    slot_fill_count = len(current_roles.intersection(set(slot_targets or [])))
    core_role_coverage = len([role for role in CORE_ROLES if role in all_roles])
    domain_overlap_count = len(current_domains.intersection(group_domains))
    type_complement = any(entry.signal_type != current.get("signal_type", "") for entry in group if current.get("signal_type", ""))
    max_effective_intensity = max((entry.effective_intensity() for entry in group), default=0.0)
    freshness_score = max((_freshness_score(entry.created_at) for entry in group), default=0.0)
    dormant_reactivation = any(_is_dormant(entry.last_activated_at or entry.created_at) for entry in group)

    return {
        "slot_fill_count": slot_fill_count,
        "core_role_coverage": core_role_coverage,
        "domain_overlap_count": domain_overlap_count,
        "type_complement": 1.0 if type_complement else 0.0,
        "max_effective_intensity": max_effective_intensity,
        "freshness_score": freshness_score,
        "dormant_reactivation": 1.0 if dormant_reactivation else 0.0,
    }


def _route_scenario_candidate(memory: ScenarioMemory, metrics: Dict[str, float]):
    closes_core_loop = metrics["slot_fill_count"] > 0 and metrics["core_role_coverage"] >= len(CORE_ROLES)
    closes_high_confidence_min_loop = (
        metrics["slot_fill_count"] > 0
        and metrics["core_role_coverage"] >= 2
        and memory.gap_fill_value >= 0.72
        and memory.promotion_score >= 0.75
    )
    if closes_core_loop or closes_high_confidence_min_loop:
        return ROUTE_STEP_C_READY, "scenario now forms a minimum opportunity logic"
    if metrics["slot_fill_count"] > 0:
        return ROUTE_STORE_FOR_LATER, "scenario receives a useful slot fill but is still not an opportunity"
    if metrics["dormant_reactivation"] and memory.option_value_score >= 0.6:
        return ROUTE_STORE_FOR_LATER, "reactivates dormant scenario for later observation"
    if max(memory.option_value_score, memory.promotion_score) >= EXPLORATION_MIN_SCORE:
        return ROUTE_STORE_FOR_LATER, "retain scenario as pre-opportunity structure"
    return ROUTE_DISCARD, "insufficient scenario value"


def _route_link_candidate(link: EmergingLink, metrics: Dict[str, float]):
    if metrics["slot_fill_count"] > 0 and metrics["core_role_coverage"] >= len(CORE_ROLES) and link.final_score >= 0.62:
        return ROUTE_STEP_C_READY, "link now forms a minimum opportunity logic"
    if metrics["slot_fill_count"] > 0:
        return ROUTE_STORE_FOR_LATER, "link receives a useful fill but remains pre-opportunity"
    if link.final_score >= EXPLORATION_MIN_SCORE or metrics["dormant_reactivation"]:
        return ROUTE_STORE_FOR_LATER, "retain promising emerging relation for later growth"
    return ROUTE_DISCARD, "weak emerging relation"


def _route_signal_candidate(entry: SignalEntry, metrics: Dict[str, float]):
    intensity_norm = min(1.0, metrics["max_effective_intensity"] / 10.0)
    if (
        metrics["slot_fill_count"] > 0
        and metrics["core_role_coverage"] >= len(CORE_ROLES)
        and metrics["domain_overlap_count"] > 0
        and intensity_norm >= 0.82
    ):
        return ROUTE_STEP_C_READY, "strong direct signal pair closes a full core opportunity loop"
    if metrics["slot_fill_count"] > 0:
        return ROUTE_STORE_FOR_LATER, "historical signal fills a gap but still needs more structure"
    if intensity_norm >= EXPLORATION_MIN_SCORE or metrics["type_complement"] > 0:
        return ROUTE_STORE_FOR_LATER, "retain complementary historical signal for later pairing"
    return ROUTE_DISCARD, "weak standalone signal match"


def _score_scenario_candidate(memory: ScenarioMemory, metrics: Dict[str, float], route: str) -> float:
    score = (
        min(1.0, metrics["slot_fill_count"]) * 0.24
        + min(1.0, metrics["core_role_coverage"] / 3.0) * 0.22
        + memory.gap_fill_value * 0.16
        + memory.promotion_score * 0.12
        + memory.option_value_score * 0.08
        + min(1.0, metrics["domain_overlap_count"] / 2.0) * 0.08
        + metrics["freshness_score"] * 0.05
        + metrics["dormant_reactivation"] * 0.05
    )
    if route == ROUTE_STEP_C_READY:
        score += 0.08
    elif route == ROUTE_STORE_FOR_LATER:
        score += 0.03
    return min(1.0, score)


def _score_link_candidate(link: EmergingLink, metrics: Dict[str, float], route: str) -> float:
    score = (
        min(1.0, metrics["slot_fill_count"]) * 0.28
        + min(1.0, metrics["core_role_coverage"] / 3.0) * 0.25
        + link.final_score * 0.2
        + min(1.0, metrics["domain_overlap_count"] / 2.0) * 0.1
        + metrics["freshness_score"] * 0.07
        + metrics["type_complement"] * 0.05
        + metrics["dormant_reactivation"] * 0.05
    )
    if route == ROUTE_STEP_C_READY:
        score += 0.08
    elif route == ROUTE_STORE_FOR_LATER:
        score += 0.03
    return min(1.0, score)


def _score_signal_candidate(entry: SignalEntry, metrics: Dict[str, float], route: str) -> float:
    intensity_norm = min(1.0, metrics["max_effective_intensity"] / 10.0)
    score = (
        min(1.0, metrics["slot_fill_count"]) * 0.3
        + min(1.0, metrics["core_role_coverage"] / 3.0) * 0.25
        + intensity_norm * 0.2
        + min(1.0, metrics["domain_overlap_count"] / 2.0) * 0.12
        + metrics["type_complement"] * 0.08
        + metrics["freshness_score"] * 0.05
    )
    if route == ROUTE_STEP_C_READY:
        score += 0.08
    elif route == ROUTE_STORE_FOR_LATER:
        score += 0.03
    return min(1.0, score)


def _route_priority(route: str) -> int:
    return {
        ROUTE_STEP_C_READY: 3,
        ROUTE_STORE_FOR_LATER: 2,
        ROUTE_DISCARD: 1,
    }.get(route, 0)


def _source_kind_priority(source_kind: str) -> int:
    return {
        "scenario_memory": 3,
        "emerging_link": 2,
        "signal_entry": 1,
    }.get(source_kind, 0)


def _is_dormant(timestamp: str) -> bool:
    try:
        ts = datetime.fromisoformat(timestamp)
        return (datetime.now(timezone.utc) - ts).days >= DORMANT_REACTIVATION_DAYS
    except Exception:
        return False


def _freshness_score(created_at: str) -> float:
    try:
        created_time = datetime.fromisoformat(created_at)
        days = max((datetime.now(timezone.utc) - created_time).days, 0)
        return max(0.0, 1 - (days / L2_TIME_WINDOW_DAYS))
    except Exception:
        return 0.5


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _normalize_l4_result(llm_result, candidate_infos: List[CandidateGroupInfo]) -> List[CandidateGroupInfo]:
    if not llm_result:
        return []

    if isinstance(llm_result, tuple):
        llm_result = llm_result[0] if llm_result else []

    if llm_result and all(isinstance(item, CandidateGroupInfo) for item in llm_result):
        return list(llm_result)

    if llm_result and all(isinstance(item, list) for item in llm_result):
        group_map = {info.group_key(): info for info in candidate_infos}
        selected = []
        seen = set()
        for group in llm_result:
            key = tuple(sorted(entry.signal_id for entry in group))
            info = group_map.get(key)
            if info and key not in seen:
                seen.add(key)
                selected.append(info)
        return selected

    return []


def _build_step_b_result(
    current_signal_id: str,
    candidate_infos: List[CandidateGroupInfo],
    latent_candidate_infos: List[CandidateGroupInfo],
    fallback_used: bool,
) -> StepBResult:
    matched_scenarios = []
    matched_links = []
    for info in candidate_infos + latent_candidate_infos:
        if info.scenario and all(item.scenario_id != info.scenario.scenario_id for item in matched_scenarios):
            matched_scenarios.append(info.scenario)
        if info.link and all(item.link_id != info.link.link_id for item in matched_links):
            matched_links.append(info.link)

    return StepBResult(
        candidate_groups=[info.entries for info in candidate_infos],
        current_signal_id=current_signal_id,
        matched=bool(candidate_infos),
        matched_links=matched_links,
        matched_scenarios=matched_scenarios,
        fallback_used=fallback_used,
        candidate_group_infos=candidate_infos,
        latent_candidate_group_infos=latent_candidate_infos,
    )


def _log_group_attempts(
    signal_store: SignalStore,
    isolated_signal: dict,
    candidate_infos: List[CandidateGroupInfo],
):
    current_id = _get_signal_id(isolated_signal)
    for info in candidate_infos:
        for entry in info.entries:
            signal_store.log_attempt(current_id, entry.signal_id)
            signal_store.log_attempt(entry.signal_id, current_id)


def _within_time_window(created_at: str, now: datetime) -> bool:
    try:
        created_time = datetime.fromisoformat(created_at)
        days_diff = abs((now - created_time).days)
        return days_diff <= L2_TIME_WINDOW_DAYS
    except Exception:
        return True


def _get_signal_id(signal: dict) -> str:
    return signal.get("signal_id") or signal.get("id") or str(id(signal))
