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

        self.status = "pending"              # pending / matched / archived / converted
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.attempt_log: List[str] = []     # 已尝试过的组合 signal_id，避免重复
        self.matched_opportunity_id: Optional[str] = None

    def effective_intensity(self) -> float:
        """按信号类型衰减系数计算当前有效强度"""
        lam = DECAY_LAMBDA.get(self.signal_type, 0.015)
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(self.created_at)).days
        days = max(days, 0)
        return self.intensity_score * math.exp(-lam * days)

    def is_expired(self, ttl_days: int = DEFAULT_TTL_DAYS) -> bool:
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(self.created_at)).days
        return days > ttl_days

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
            "status": self.status,
            "created_at": self.created_at,
            "attempt_log": self.attempt_log,
            "matched_opportunity_id": self.matched_opportunity_id,
            "effective_intensity": self.effective_intensity(),
        }


# ──────────────────────────────────────────────
# SignalStore 主类
# ──────────────────────────────────────────────

class SignalStore:
    """
    Signal Store 读写接口。

    内部存储为 Dict[signal_id, SignalEntry]，持久化到独立 pkl 文件。
    不与 2.4 RAG 知识库混存，不共享检索接口。
    """

    def __init__(self, store_path: str = None):
        self.store_path = store_path or SIGNAL_STORE_PATH
        self._store: Dict[str, SignalEntry] = {}
        self._load()

    # ── 持久化 ──────────────────────────────────

    def _load(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
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

    # ── 查询 ────────────────────────────────────

    def get(self, signal_id: str) -> Optional[SignalEntry]:
        return self._store.get(signal_id)

    def query_by_role(
        self,
        role: str,
        exclude_ids: List[str] = None,
        status: str = "pending",
    ) -> List[SignalEntry]:
        """
        L1 粗筛：找出 needs 中包含指定角色的信号。
        即"我需要一个 {role} 角色的信号来配对"。
        """
        exclude = set(exclude_ids or [])
        results = []
        for entry in self._store.values():
            if entry.status != status:
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

    # ── 状态更新 ────────────────────────────────

    def update_status(self, signal_id: str, status: str, opportunity_id: str = None):
        """更新信号状态"""
        entry = self._store.get(signal_id)
        if entry:
            entry.status = status
            if opportunity_id:
                entry.matched_opportunity_id = opportunity_id
            self._save()

    def log_attempt(self, signal_id: str, attempted_signal_id: str):
        """记录已尝试过的组合，避免重复"""
        entry = self._store.get(signal_id)
        if entry and attempted_signal_id not in entry.attempt_log:
            entry.attempt_log.append(attempted_signal_id)
            self._save()

    # ── 过期归档 ─────────────────────────────────

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
        return {
            "total": total,
            "by_status": by_status,
            "by_signal_type": by_type,
        }


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
    signal_id = f"sig_{raw_id}_{signal.get('signal_type', 'unknown')}"

    return SignalEntry(
        signal_id=signal_id,
        source_id=signal.get("source_id", ""),
        signal_label=signal.get("signal_label", signal.get("label", "")),
        signal_type=signal.get("signal_type", "market"),
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
    )
