"""
Phase 2.2 Signal Store — 存储与检索层

职责：
- 信号写入（含角色标注、waiting_for_text、缺口清单）
- 按 tag 查询候选信号（L1 粗筛）
- 信号状态更新（pending / matched / archived / converted）
- 过期信号归档

存储格式：独立 pickle 文件，不与 2.4 RAG 知识库混存。
"""

import os
import pickle
import math
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# ──────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────

SIGNAL_STORE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "phase2.4_implementation", "rag_system", "data", "signal_store.pkl"
)

VALID_ROLES = {
    "catalyst",           # 触发机会的外部事件/压力
    "demand_evidence",    # 证明需求侧存在
    "resource_validation",# 证明资源/能力/资金到位
    "competitive_gap",    # 竞品退出/收缩/受限
    "execution_risk",     # 执行层面的障碍或风险
    "timing_signal",      # 时间窗口/紧迫性证据
    "negative_validator", # 证伪/削弱机会论点的反向信号
}

VALID_DOMAINS = {
    "gaming", "ai", "mobile", "regulation", "capital", "geopolitics"
}

# signal_type → 衰减系数 λ（半衰期 = ln2/λ 天）
DECAY_LAMBDA = {
    "regulatory": 0.008,   # 半衰期 ~87 天
    "capital":    0.012,   # 半衰期 ~58 天
    "technical":  0.015,   # 半衰期 ~46 天
    "team":       0.020,   # 半衰期 ~35 天
    "market":     0.023,   # 半衰期 ~30 天
}

DEFAULT_TTL_DAYS = 90


# ──────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────

class SignalEntry:
    """Signal Store 中的一条记录"""

    def __init__(
        self,
        signal_id: str,
        source_id: str,
        signal_label: str,
        signal_type: str,           # regulatory / capital / market / technical / team
        description: str,
        evidence_text: str,
        intensity_score: int,       # 1-10
        confidence_score: int,      # 1-10
        roles: List[str],           # 来自 VALID_ROLES
        needs: List[str],           # 构成机会还需要的角色，来自 VALID_ROLES
        domains: List[str],         # 来自 VALID_DOMAINS
        waiting_for_text: str,      # 一句话：我在等待什么样的伙伴
        batch_date: str,            # ISO date，如 "2026-03-31"
        timeliness_score: int = 5,
        original_signal_id: Optional[str] = None,
    ):
        self.signal_id = signal_id
        self.source_id = source_id
        self.signal_label = signal_label
        self.signal_type = signal_type
        self.description = description
        self.evidence_text = evidence_text
        self.intensity_score = intensity_score
        self.confidence_score = confidence_score
        self.roles = roles
        self.needs = needs
        self.domains = domains
        self.waiting_for_text = waiting_for_text
        self.batch_date = batch_date
        self.timeliness_score = timeliness_score
        self.original_signal_id = original_signal_id or signal_id

        self.status = "pending"              # pending / matched / archived / converted / contributed
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.attempt_log: List[str] = []     # 已尝试过的组合 signal_id，避免重复
        self.matched_opportunity_id: Optional[str] = None
        self.last_activated_at: Optional[str] = None
        self.activation_count: int = 0
        self.linked_scenario_ids: List[str] = []
        self.linked_edge_ids: List[str] = []

    def effective_intensity(self) -> float:
        """按信号类型衰减系数计算当前有效强度"""
        lam = DECAY_LAMBDA.get(self.signal_type, 0.015)
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(self.created_at)).days
        days = max(days, 0)
        return self.intensity_score * math.exp(-lam * days)

    def is_expired(self, ttl_days: int = DEFAULT_TTL_DAYS) -> bool:
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(self.created_at)).days
        return days > ttl_days

    def mark_activated(self, scenario_id: str = None, edge_id: str = None):
        self.activation_count += 1
        self.last_activated_at = datetime.now(timezone.utc).isoformat()
        if scenario_id and scenario_id not in self.linked_scenario_ids:
            self.linked_scenario_ids.append(scenario_id)
        if edge_id and edge_id not in self.linked_edge_ids:
            self.linked_edge_ids.append(edge_id)

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "source_id": self.source_id,
            "signal_label": self.signal_label,
            "signal_type": self.signal_type,
            "description": self.description,
            "evidence_text": self.evidence_text,
            "intensity_score": self.intensity_score,
            "confidence_score": self.confidence_score,
            "roles": self.roles,
            "needs": self.needs,
            "domains": self.domains,
            "waiting_for_text": self.waiting_for_text,
            "batch_date": self.batch_date,
            "timeliness_score": self.timeliness_score,
            "original_signal_id": self.original_signal_id,
            "status": self.status,
            "created_at": self.created_at,
            "attempt_log": self.attempt_log,
            "matched_opportunity_id": self.matched_opportunity_id,
            "last_activated_at": self.last_activated_at,
            "activation_count": self.activation_count,
            "linked_scenario_ids": self.linked_scenario_ids,
            "linked_edge_ids": self.linked_edge_ids,
            "effective_intensity": self.effective_intensity(),
        }


class EmergingLink:
    """跨批次可继续生长的关系痕迹"""

    def __init__(
        self,
        link_id: str,
        signal_ids: List[str],
        edge_type: str,
        strength_band: str,
        gate_passed: bool,
        final_score: float,
        reasoning: str,
        shared_affects: List[str],
        batch_date: str,
    ):
        self.link_id = link_id
        self.signal_ids = signal_ids
        self.edge_type = edge_type
        self.strength_band = strength_band
        self.gate_passed = gate_passed
        self.final_score = final_score
        self.reasoning = reasoning
        self.shared_affects = shared_affects
        self.batch_date = batch_date
        self.status = "active"                      # active / promoted / archived
        self.promoted_to_scenario_id: Optional[str] = None
        self.last_activated_at: Optional[str] = None
        self.activation_count: int = 0
        self.created_at = datetime.now(timezone.utc).isoformat()

    def mark_promoted(self, scenario_id: str = None):
        self.status = "promoted"
        self.promoted_to_scenario_id = scenario_id
        self.activation_count += 1
        self.last_activated_at = datetime.now(timezone.utc).isoformat()

    def mark_activated(self):
        self.activation_count += 1
        self.last_activated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "signal_ids": self.signal_ids,
            "edge_type": self.edge_type,
            "strength_band": self.strength_band,
            "gate_passed": self.gate_passed,
            "final_score": self.final_score,
            "reasoning": self.reasoning,
            "shared_affects": self.shared_affects,
            "batch_date": self.batch_date,
            "status": self.status,
            "promoted_to_scenario_id": self.promoted_to_scenario_id,
            "last_activated_at": self.last_activated_at,
            "activation_count": self.activation_count,
            "created_at": self.created_at,
        }


class ScenarioMemory:
    """可跨批次等待补槽的半成品场景"""

    def __init__(
        self,
        scenario_id: str,
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
        batch_date: str,
        linked_edge_ids: List[str] = None,
    ):
        self.scenario_id = scenario_id
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
        self.batch_date = batch_date
        self.linked_edge_ids = linked_edge_ids or []
        self.status = "active"                      # active / promoted / archived / matched
        self.last_activated_at: Optional[str] = None
        self.activation_count: int = 0
        self.matched_opportunity_id: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()

    def mark_activated(self):
        self.activation_count += 1
        self.last_activated_at = datetime.now(timezone.utc).isoformat()

    def update_state(self, state: str, opportunity_id: str = None):
        self.state = state
        if state in ("promoted", "matched"):
            self.status = state
        if opportunity_id:
            self.matched_opportunity_id = opportunity_id
        self.mark_activated()

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
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
            "batch_date": self.batch_date,
            "linked_edge_ids": self.linked_edge_ids,
            "status": self.status,
            "last_activated_at": self.last_activated_at,
            "activation_count": self.activation_count,
            "matched_opportunity_id": self.matched_opportunity_id,
            "created_at": self.created_at,
        }


# ──────────────────────────────────────────────
# SignalStore 主类
# ──────────────────────────────────────────────

class SignalStore:
    """
    Signal Store 读写接口。

    内部存储包含：
    - Dict[signal_id, SignalEntry]
    - Dict[link_id, EmergingLink]
    - Dict[scenario_id, ScenarioMemory]

    持久化到独立 pkl 文件。
    不与 2.4 RAG 知识库混存，不共享检索接口。
    """

    def __init__(self, store_path: str = None):
        self.store_path = store_path or SIGNAL_STORE_PATH
        self._store: Dict[str, SignalEntry] = {}
        self._emerging_links: Dict[str, EmergingLink] = {}
        self._scenario_memories: Dict[str, ScenarioMemory] = {}
        self._load()

    # ── 持久化 ──────────────────────────────────

    def _load(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "rb") as f:
                    loaded = pickle.load(f)
                if isinstance(loaded, dict) and any(
                    key in loaded for key in ("signals", "emerging_links", "scenario_memories")
                ):
                    self._store = loaded.get("signals", {}) or {}
                    self._emerging_links = loaded.get("emerging_links", {}) or {}
                    self._scenario_memories = loaded.get("scenario_memories", {}) or {}
                elif isinstance(loaded, dict):
                    self._store = loaded
                    self._emerging_links = {}
                    self._scenario_memories = {}
                else:
                    self._store = {}
                    self._emerging_links = {}
                    self._scenario_memories = {}
                self._ensure_backward_compatible_fields()
            except Exception:
                self._store = {}
                self._emerging_links = {}
                self._scenario_memories = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        payload = {
            "signals": self._store,
            "emerging_links": self._emerging_links,
            "scenario_memories": self._scenario_memories,
        }
        with open(self.store_path, "wb") as f:
            pickle.dump(payload, f)

    def _ensure_backward_compatible_fields(self):
        for entry in self._store.values():
            if not hasattr(entry, "original_signal_id"):
                entry.original_signal_id = getattr(entry, "signal_id", None)
            if not hasattr(entry, "last_activated_at"):
                entry.last_activated_at = None
            if not hasattr(entry, "activation_count"):
                entry.activation_count = 0
            if not hasattr(entry, "linked_scenario_ids"):
                entry.linked_scenario_ids = []
            if not hasattr(entry, "linked_edge_ids"):
                entry.linked_edge_ids = []
        for link in self._emerging_links.values():
            if not hasattr(link, "status"):
                link.status = "active"
            if not hasattr(link, "promoted_to_scenario_id"):
                link.promoted_to_scenario_id = None
            if not hasattr(link, "last_activated_at"):
                link.last_activated_at = None
            if not hasattr(link, "activation_count"):
                link.activation_count = 0
            if not hasattr(link, "created_at"):
                link.created_at = datetime.now(timezone.utc).isoformat()
        for memory in self._scenario_memories.values():
            if not hasattr(memory, "status"):
                memory.status = "active"
            if not hasattr(memory, "last_activated_at"):
                memory.last_activated_at = None
            if not hasattr(memory, "activation_count"):
                memory.activation_count = 0
            if not hasattr(memory, "matched_opportunity_id"):
                memory.matched_opportunity_id = None
            if not hasattr(memory, "created_at"):
                memory.created_at = datetime.now(timezone.utc).isoformat()
            if not hasattr(memory, "linked_edge_ids"):
                memory.linked_edge_ids = []

    # ── 写入 ────────────────────────────────────

    def add(self, entry: SignalEntry) -> str:
        """写入一条信号，返回 signal_id"""
        self._store[entry.signal_id] = entry
        self._save()
        return entry.signal_id

    def add_batch(self, entries: List[SignalEntry]) -> List[str]:
        """批量写入，减少 IO"""
        ids = []
        for e in entries:
            self._store[e.signal_id] = e
            ids.append(e.signal_id)
        self._save()
        return ids

    def save_emerging_links(self, links: List[Dict[str, Any]], batch_date: str) -> List[str]:
        ids = []
        for raw in links or []:
            signal_ids = sorted(list({
                raw.get("left_signal_id", ""),
                raw.get("right_signal_id", ""),
                *(raw.get("signal_ids", []) or []),
            } - {""}))
            if len(signal_ids) < 2:
                continue
            link_id = raw.get("link_id") or raw.get("edge_id") or f"link_{'_'.join(signal_ids)}"
            existing = self._emerging_links.get(link_id)
            if existing:
                existing.signal_ids = signal_ids
                existing.edge_type = raw.get("edge_type", existing.edge_type)
                existing.strength_band = raw.get("strength_band", existing.strength_band)
                existing.gate_passed = raw.get("gate_passed", existing.gate_passed)
                existing.final_score = raw.get("final_score", existing.final_score)
                existing.reasoning = raw.get("reasoning", existing.reasoning)
                existing.shared_affects = raw.get("shared_affects", existing.shared_affects)
                existing.batch_date = batch_date
                link = existing
            else:
                link = EmergingLink(
                    link_id=link_id,
                    signal_ids=signal_ids,
                    edge_type=raw.get("edge_type", "complementary"),
                    strength_band=raw.get("strength_band", "emerging"),
                    gate_passed=bool(raw.get("gate_passed", True)),
                    final_score=float(raw.get("final_score", 0.0)),
                    reasoning=raw.get("reasoning", ""),
                    shared_affects=list(raw.get("shared_affects", []) or []),
                    batch_date=batch_date,
                )
                self._emerging_links[link_id] = link
            ids.append(link.link_id)
            self._mark_signals_activated(signal_ids, edge_id=link.link_id)
        if ids:
            self._save()
        return ids

    def save_scenario_memories(self, scenarios: List[Dict[str, Any]], batch_date: str) -> List[str]:
        ids = []
        for raw in scenarios or []:
            scenario_id = raw.get("scenario_id") or raw.get("candidate_id")
            if not scenario_id:
                continue
            member_signal_ids = sorted(list(raw.get("member_signal_ids", []) or raw.get("primary_signal_ids", []) or []))
            if len(member_signal_ids) < 2:
                continue
            linked_edge_ids = list(raw.get("linked_edge_ids", []) or raw.get("linked_links", []) or [])
            existing = self._scenario_memories.get(scenario_id)
            if existing:
                existing.anchor_signal_ids = list(raw.get("anchor_signal_ids", existing.anchor_signal_ids))
                existing.member_signal_ids = member_signal_ids
                existing.covered_roles = list(raw.get("covered_roles", existing.covered_roles))
                existing.missing_slots = list(raw.get("missing_slots", existing.missing_slots))
                existing.shared_affects = list(raw.get("shared_affects", existing.shared_affects))
                existing.state = raw.get("state", existing.state)
                existing.promotion_score = float(raw.get("promotion_score", existing.promotion_score))
                existing.option_value_score = float(raw.get("option_value_score", existing.option_value_score))
                existing.novelty_score = float(raw.get("novelty_score", existing.novelty_score))
                existing.gap_fill_value = float(raw.get("gap_fill_value", existing.gap_fill_value))
                existing.cross_domain_bonus = float(raw.get("cross_domain_bonus", existing.cross_domain_bonus))
                existing.reasoning_path = raw.get("reasoning_path", existing.reasoning_path)
                existing.batch_date = batch_date
                existing.linked_edge_ids = linked_edge_ids or existing.linked_edge_ids
                memory = existing
            else:
                memory = ScenarioMemory(
                    scenario_id=scenario_id,
                    anchor_signal_ids=list(raw.get("anchor_signal_ids", []) or []),
                    member_signal_ids=member_signal_ids,
                    covered_roles=list(raw.get("covered_roles", []) or []),
                    missing_slots=list(raw.get("missing_slots", []) or []),
                    shared_affects=list(raw.get("shared_affects", []) or []),
                    state=raw.get("state", "developing"),
                    promotion_score=float(raw.get("promotion_score", 0.0)),
                    option_value_score=float(raw.get("option_value_score", 0.0)),
                    novelty_score=float(raw.get("novelty_score", 0.0)),
                    gap_fill_value=float(raw.get("gap_fill_value", 0.0)),
                    cross_domain_bonus=float(raw.get("cross_domain_bonus", 0.0)),
                    reasoning_path=raw.get("reasoning_path", ""),
                    batch_date=batch_date,
                    linked_edge_ids=linked_edge_ids,
                )
                self._scenario_memories[scenario_id] = memory
            ids.append(memory.scenario_id)
            self._mark_signals_activated(member_signal_ids, scenario_id=memory.scenario_id)
        if ids:
            self._save()
        return ids

    # ── 查询 ────────────────────────────────────

    def get(self, signal_id: str) -> Optional[SignalEntry]:
        return self._store.get(signal_id)

    def get_by_original_signal_id(self, original_signal_id: str) -> Optional[SignalEntry]:
        for entry in self._store.values():
            if getattr(entry, "original_signal_id", None) == original_signal_id:
                return entry
        return None

    def get_entries_by_original_signal_ids(self, original_signal_ids: List[str]) -> List[SignalEntry]:
        results = []
        seen = set()
        for original_signal_id in original_signal_ids or []:
            entry = self.get_by_original_signal_id(original_signal_id)
            if entry and entry.signal_id not in seen:
                seen.add(entry.signal_id)
                results.append(entry)
        return results

    def _has_domain_overlap_by_original_ids(self, original_signal_ids: List[str], domains: List[str]) -> bool:
        domain_set = set(domains or [])
        if not domain_set:
            return True
        entries = self.get_entries_by_original_signal_ids(original_signal_ids)
        if not entries:
            return False
        for entry in entries:
            if domain_set.intersection(set(entry.domains or [])):
                return True
        return False

    def get_link(self, link_id: str) -> Optional[EmergingLink]:
        return self._emerging_links.get(link_id)

    def get_scenario_memory(self, scenario_id: str) -> Optional[ScenarioMemory]:
        return self._scenario_memories.get(scenario_id)

    def query_by_role(
        self,
        role: str,
        exclude_ids: List[str] = None,
    ) -> List[SignalEntry]:
        """
        L1 粗筛：找出 needs 中包含指定角色的信号。
        即"我需要一个 {role} 角色的信号来配对"。

        同时返回 pending 和 matched 状态的信号：
        - pending：尚未参与任何机会
        - matched：已参与过某机会，但同一信号可跨机会复用
        去重逻辑在 Step C 组合时按 source_id 处理，此处不过滤。
        """
        exclude = set(exclude_ids or [])
        results = []
        for entry in self._store.values():
            if entry.status not in ("pending", "matched"):
                continue
            if entry.signal_id in exclude:
                continue
            if role in entry.needs:
                results.append(entry)
        return results

    def query_pending(self) -> List[SignalEntry]:
        """返回所有 pending 状态的信号"""
        return [e for e in self._store.values() if e.status == "pending"]

    def query_negative_validators(self, domains: List[str]) -> List[SignalEntry]:
        """检索 negative_validator 角色 + domain 匹配的反向信号"""
        results = []
        for entry in self._store.values():
            if entry.status not in ("pending", "matched"):
                continue
            if "negative_validator" not in entry.roles:
                continue
            if any(d in entry.domains for d in domains):
                results.append(entry)
        return results

    def query_matching_links(
        self,
        roles: List[str],
        domains: List[str] = None,
        exclude_signal_ids: List[str] = None,
        active_only: bool = True,
    ) -> List[EmergingLink]:
        results = []
        excluded = set(exclude_signal_ids or [])
        role_set = set(roles or [])
        for link in self._emerging_links.values():
            if active_only and link.status != "active":
                continue
            if excluded.intersection(link.signal_ids):
                continue
            if domains and not self._has_domain_overlap_by_original_ids(link.signal_ids, domains):
                continue
            if role_set and link.edge_type == "contradictory":
                continue
            results.append(link)
        results.sort(key=lambda item: (item.final_score, item.activation_count), reverse=True)
        return results

    def query_matching_scenarios(
        self,
        roles: List[str],
        domains: List[str] = None,
        exclude_signal_ids: List[str] = None,
        active_only: bool = True,
    ) -> List[ScenarioMemory]:
        results = []
        excluded = set(exclude_signal_ids or [])
        role_set = set(roles or [])
        for memory in self._scenario_memories.values():
            if active_only and memory.status not in ("active",):
                continue
            if excluded.intersection(memory.member_signal_ids):
                continue
            if role_set and not role_set.intersection(set(memory.missing_slots)):
                continue
            if domains and not self._has_domain_overlap_by_original_ids(memory.member_signal_ids, domains):
                continue
            results.append(memory)
        results.sort(key=lambda item: (item.option_value_score, item.promotion_score), reverse=True)
        return results

    # ── 状态更新 ────────────────────────────────

    def update_status(self, signal_id: str, status: str, opportunity_id: str = None):
        """更新信号状态"""
        entry = self._store.get(signal_id)
        if entry:
            entry.status = status
            if opportunity_id:
                entry.matched_opportunity_id = opportunity_id
            self._save()

    def update_scenario_state(self, scenario_id: str, state: str, opportunity_id: str = None):
        memory = self._scenario_memories.get(scenario_id)
        if memory:
            memory.update_state(state, opportunity_id)
            self._save()

    def activate_scenario_memory(self, scenario_id: str):
        memory = self._scenario_memories.get(scenario_id)
        if memory:
            memory.mark_activated()
            self._save()

    def mark_link_promoted(self, link_id: str, scenario_id: str = None):
        link = self._emerging_links.get(link_id)
        if link:
            link.mark_promoted(scenario_id)
            self._save()

    def activate_link(self, link_id: str):
        link = self._emerging_links.get(link_id)
        if link:
            link.mark_activated()
            self._save()

    def log_attempt(self, signal_id: str, attempted_signal_id: str):
        """记录已尝试过的组合，避免重复"""
        entry = self._store.get(signal_id)
        if entry and attempted_signal_id not in entry.attempt_log:
            entry.attempt_log.append(attempted_signal_id)
            self._save()

    def archive_expired(self, ttl_days: int = DEFAULT_TTL_DAYS) -> int:
        """将超过 TTL 的 pending 信号归档，返回归档数量"""
        count = 0
        for entry in self._store.values():
            if entry.status == "pending" and entry.is_expired(ttl_days):
                entry.status = "archived"
                count += 1
        if count:
            self._save()
        return count

    # ── 统计 ────────────────────────────────────

    def stats(self) -> dict:
        """返回 Signal Store 统计信息"""
        total = len(self._store)
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for e in self._store.values():
            by_status[e.status] = by_status.get(e.status, 0) + 1
            by_type[e.signal_type] = by_type.get(e.signal_type, 0) + 1

        link_status: Dict[str, int] = {}
        for link in self._emerging_links.values():
            link_status[link.status] = link_status.get(link.status, 0) + 1

        scenario_status: Dict[str, int] = {}
        for memory in self._scenario_memories.values():
            scenario_status[memory.status] = scenario_status.get(memory.status, 0) + 1

        return {
            "total": total,
            "by_status": by_status,
            "by_signal_type": by_type,
            "emerging_links_total": len(self._emerging_links),
            "emerging_links_by_status": link_status,
            "scenario_memories_total": len(self._scenario_memories),
            "scenario_memories_by_status": scenario_status,
        }

    def _mark_signals_activated(
        self,
        signal_ids: List[str],
        scenario_id: str = None,
        edge_id: str = None,
    ):
        if not signal_ids:
            return
        signal_id_set = set(signal_ids)
        for entry in self._store.values():
            if entry.signal_id in signal_id_set or getattr(entry, "original_signal_id", None) in signal_id_set:
                entry.mark_activated(scenario_id=scenario_id, edge_id=edge_id)


# ──────────────────────────────────────────────
# 工厂函数：从 DecodedIntelligence 信号构建 SignalEntry
# ──────────────────────────────────────────────

def build_signal_entry(
    signal: dict,
    roles: List[str],
    needs: List[str],
    domains: List[str],
    waiting_for_text: str,
    batch_date: str,
) -> SignalEntry:
    """
    从 2.1 输出的信号字典构建 SignalEntry。

    Args:
        signal: 信号字典，含 signal_id/signal_label/signal_type/description/
                evidence_text/intensity_score/confidence_score/timeliness_score
        roles: Step A 标注的角色列表
        needs: Step A 标注的缺口列表
        domains: Step A 标注的领域列表
        waiting_for_text: Step A 生成的"我在等待什么"描述
        batch_date: 当前批次日期（ISO，如 "2026-03-31"）
    """
    # 生成唯一 signal_id（如原始信号无 ID）
    raw_id = signal.get("signal_id") or signal.get("id") or str(uuid.uuid4())[:8]

    # signal_type 可能是 2.1 解码器产出的枚举值（如 SignalType.REGULATORY），
    # 转为纯字符串（取 .value 或 str() 后截取最后一段），确保 pkl 可移植
    _raw_type = signal.get("signal_type", "market")
    if hasattr(_raw_type, "value"):
        signal_type_str = str(_raw_type.value)
    else:
        # 枚举 repr 形如 "SignalType.regulatory"，取最后一段
        signal_type_str = str(_raw_type).split(".")[-1].lower()

    signal_id = f"sig_{raw_id}_{signal_type_str}"

    return SignalEntry(
        signal_id=signal_id,
        source_id=(
            signal.get("source_id")
            or signal.get("_source_id")
            or signal.get("source_ref", "").split(":")[0]
        ),
        signal_label=signal.get("signal_label", signal.get("label", "")),
        signal_type=signal_type_str,
        description=signal.get("description", ""),
        evidence_text=signal.get("evidence_text", ""),
        intensity_score=int(signal.get("intensity_score", signal.get("intensity", 5))),
        confidence_score=int(signal.get("confidence_score", signal.get("confidence", 5))),
        timeliness_score=int(signal.get("timeliness_score", signal.get("timeliness", 5))),
        roles=roles,
        needs=needs,
        domains=domains,
        waiting_for_text=waiting_for_text,
        batch_date=batch_date,
        original_signal_id=str(signal.get("signal_id") or signal.get("id") or raw_id),
    )


# ──────────────────────────────────────────────
# 机会 ID 持久化（v1.1）
# ──────────────────────────────────────────────

OPPORTUNITY_STORE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "phase2.4_implementation", "rag_system", "data", "opportunity_store.pkl"
)


class OpportunitySnapshot:
    """持久化机会记录，用于跨批次 opportunity_id 复用"""

    def __init__(
        self,
        opportunity_id: str,
        opportunity_title: str,
        priority_level: str,
        source_signal_ids: set,
        signal_ids: List[str] = None,
    ):
        self.opportunity_id = opportunity_id
        self.opportunity_title = opportunity_title
        self.priority_level = priority_level
        self.source_signal_ids: set = set(source_signal_ids)   # 用于复用判断
        self.signal_ids: List[str] = signal_ids or []
        self.first_seen: str = datetime.now(timezone.utc).isoformat()
        self.last_updated: str = self.first_seen
        self.follow_up_signals: List[str] = []                 # 后续批次追加的 source_id

    def update(self, new_source_ids: set, new_signal_ids: List[str], priority_level: str):
        """追加新批次信号，更新优先级和时间"""
        added = new_source_ids - self.source_signal_ids
        self.source_signal_ids.update(new_source_ids)
        self.signal_ids.extend(new_signal_ids)
        self.follow_up_signals.extend(list(added))
        self.priority_level = priority_level
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity_title,
            "priority_level": self.priority_level,
            "source_signal_ids": list(self.source_signal_ids),
            "signal_ids": self.signal_ids,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "follow_up_signals": self.follow_up_signals,
        }


class OpportunityStore:
    """
    机会 ID 持久化存储。

    职责：
    - 跨批次复用 opportunity_id（基于 source_id 集合重叠判断）
    - 追踪机会演进（follow_up_signals）
    - 不改变 2.2→2.3 接口，opportunity_id 对下游透明
    """

    def __init__(self, store_path: str = None):
        self.store_path = store_path or OPPORTUNITY_STORE_PATH
        self._store: Dict[str, OpportunitySnapshot] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "rb") as f:
                    self._store = pickle.load(f)
            except Exception:
                self._store = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "wb") as f:
            pickle.dump(self._store, f)

    def resolve_opportunity_id(
        self,
        opportunity,          # OpportunityObject
        source_signal_ids: set,
        signal_ids: List[str],
    ) -> str:
        """
        核心方法：根据 source_id 重叠判断是否复用历史 opportunity_id。

        Returns:
            str: 最终使用的 opportunity_id（复用或新建）
        """
        # 找有 source_id 重叠的历史机会
        for snap in self._store.values():
            if snap.source_signal_ids.intersection(source_signal_ids):
                # 复用：追加新信号，更新优先级
                snap.update(
                    new_source_ids=source_signal_ids,
                    new_signal_ids=signal_ids,
                    priority_level=getattr(opportunity, "priority_level", snap.priority_level),
                )
                self._save()
                return snap.opportunity_id

        # 新建：写入 opportunity_store
        new_id = getattr(opportunity, "opportunity_id", None) or str(uuid.uuid4())
        snap = OpportunitySnapshot(
            opportunity_id=new_id,
            opportunity_title=getattr(opportunity, "opportunity_title", ""),
            priority_level=getattr(opportunity, "priority_level", "watch"),
            source_signal_ids=source_signal_ids,
            signal_ids=signal_ids,
        )
        self._store[new_id] = snap
        self._save()
        return new_id

    def get(self, opportunity_id: str) -> Optional[OpportunitySnapshot]:
        return self._store.get(opportunity_id)

    def stats(self) -> dict:
        by_priority = {}
        for snap in self._store.values():
            by_priority[snap.priority_level] = by_priority.get(snap.priority_level, 0) + 1
        return {
            "total": len(self._store),
            "by_priority": by_priority,
        }
