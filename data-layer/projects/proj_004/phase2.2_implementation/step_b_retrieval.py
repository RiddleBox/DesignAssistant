"""
Phase 2.2 Step B — 历史信号检索（分层漏斗）

四层漏斗：
  L1: Tag 粗筛  — needs 中包含当前信号角色的历史 pending 信号
  L2: 规则硬过滤 — domain 重叠 + 时间窗口 + 有效强度 + 排除已尝试组合
  L3: 暂缓（MVP 阶段不实现 embedding 精排，待 L1+L2 效果验证后决定）
  L4: LLM 轻量确认 — 有没有能构成机会逻辑链的组合

设计原则：
- L1+L2 纯规则，零 LLM 调用
- L4 只在 L2 有候选时触发，每条孤立信号最多 1 次 haiku 调用
- 返回候选组合列表或空列表（空 = 当前信号写入 Signal Store）
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

from signal_store import SignalStore, SignalEntry

# L2 过滤参数（可配置）
L2_TIME_WINDOW_DAYS = 90        # 信号写入时间差上限
L2_MIN_EFFECTIVE_INTENSITY = 4  # 有效强度下限（衰减后）
L2_MAX_CANDIDATES = 20          # 进入 L4 前的候选上限
L4_SKIP_THRESHOLD = 0           # L2 候选数低于此值时跳过 L4（0=有候选就确认）


class StepBResult:
    def __init__(
        self,
        candidate_groups: List[List[SignalEntry]],  # 每组是可能组合的信号集合
        current_signal_id: str,
        matched: bool,
        fallback_used: bool = False,
    ):
        self.candidate_groups = candidate_groups
        self.current_signal_id = current_signal_id
        self.matched = matched          # True = 找到候选，进 Step C
        self.fallback_used = fallback_used


def run_step_b(
    isolated_signal: dict,
    signal_store: SignalStore,
    llm_client=None,
    model: str = "claude-haiku-4-5",
) -> StepBResult:
    """
    对一条孤立信号执行 Step B 检索。

    Args:
        isolated_signal: 含 _role_annotation 字段的信号字典（来自 Step A）
        signal_store: Signal Store 实例
        llm_client: 用于 L4 LLM 确认的客户端
        model: L4 使用的模型

    Returns:
        StepBResult
    """
    sid = _get_signal_id(isolated_signal)
    annotation = isolated_signal.get("_role_annotation", {})
    roles = annotation.get("roles", [])
    domains = annotation.get("domains", [])

    # L1: tag 粗筛 —— 找出 needs 中包含当前信号任意角色的历史 pending 信号
    l1_candidates: List[SignalEntry] = []
    for role in roles:
        hits = signal_store.query_by_role(role=role, exclude_ids=[sid])
        l1_candidates.extend(hits)
    # 去重
    seen = set()
    l1_unique = []
    for c in l1_candidates:
        if c.signal_id not in seen:
            seen.add(c.signal_id)
            l1_unique.append(c)

    if not l1_unique:
        return StepBResult([], sid, matched=False)

    # L2: 规则硬过滤
    l2_candidates = _l2_filter(isolated_signal, l1_unique, annotation)

    if not l2_candidates:
        return StepBResult([], sid, matched=False)

    # 按有效强度降序，取前 L2_MAX_CANDIDATES 条
    l2_candidates.sort(key=lambda e: e.effective_intensity(), reverse=True)
    l2_candidates = l2_candidates[:L2_MAX_CANDIDATES]

    # L4: LLM 轻量确认
    if llm_client and l2_candidates:
        try:
            groups = _l4_llm_confirm(isolated_signal, l2_candidates, llm_client, model)
            if groups:
                # 记录尝试过的组合
                for g in groups:
                    for e in g:
                        signal_store.log_attempt(sid, e.signal_id)
                        signal_store.log_attempt(e.signal_id, sid)
                return StepBResult(groups, sid, matched=True)
        except Exception as ex:
            print(f"[Step B] L4 LLM 确认失败: {ex}，退化为规则候选")

    # L4 失败或无 LLM：把 L2 候选作为单组返回（让 Step C 自行判断）
    return StepBResult([l2_candidates], sid, matched=bool(l2_candidates), fallback_used=True)


# ──────────────────────────────────────────────
# L2 规则硬过滤
# ──────────────────────────────────────────────

def _l2_filter(
    current: dict,
    candidates: List[SignalEntry],
    annotation: dict,
) -> List[SignalEntry]:
    """L2：domain 重叠 + 时间窗口 + 有效强度 + 排除已尝试"""
    current_domains = set(annotation.get("domains", []))
    current_intensity = int(
        current.get("intensity_score") or current.get("intensity") or 5
    )
    current_sid = _get_signal_id(current)
    current_time = datetime.now(timezone.utc)

    results = []
    for e in candidates:
        # domain 重叠（至少1个共同 domain）
        if not current_domains.intersection(set(e.domains)):
            continue

        # 时间窗口（写入时间差 ≤ L2_TIME_WINDOW_DAYS）
        try:
            e_time = datetime.fromisoformat(e.created_at)
            days_diff = abs((current_time - e_time).days)
            if days_diff > L2_TIME_WINDOW_DAYS:
                continue
        except Exception:
            pass

        # 有效强度下限
        if e.effective_intensity() < L2_MIN_EFFECTIVE_INTENSITY:
            continue

        # 排除当前信号已尝试过的组合
        if current_sid in e.attempt_log or e.signal_id in current.get("_attempt_log", []):
            continue

        results.append(e)

    return results


# ──────────────────────────────────────────────
# L4 LLM 轻量确认
# ──────────────────────────────────────────────

def _l4_llm_confirm(
    current: dict,
    candidates: List[SignalEntry],
    client,
    model: str,
) -> List[List[SignalEntry]]:
    """
    L4：用 haiku 判断 current + candidates 中有没有能构成机会逻辑链的组合。
    返回候选组合列表（每组是一个 List[SignalEntry]），无组合返回 []。
    """
    prompt = _build_l4_prompt(current, candidates)
    raw = client.call(
        prompt=prompt,
        model=model,
        max_tokens=1024,
        temperature=0.1,
    )
    return _parse_l4_response(raw, candidates)


def _build_l4_prompt(current: dict, candidates: List[SignalEntry]) -> str:
    annotation = current.get("_role_annotation", {})
    current_desc = (
        f"当前信号：{current.get('signal_label') or current.get('label', '')}\n"
        f"类型：{current.get('signal_type', '')}\n"
        f"描述：{current.get('description', '')[:150]}\n"
        f"角色：{annotation.get('roles', [])}\n"
        f"在等待：{annotation.get('waiting_for_text', '')}"
    )

    candidates_desc = []
    for i, e in enumerate(candidates):
        candidates_desc.append(
            f"[C{i+1}] id={e.signal_id} | {e.signal_label} | "
            f"type={e.signal_type} | roles={e.roles} | "
            f"描述：{e.description[:100]}"
        )

    return f"""你是战略机会分析助手。判断以下信号组合中，有没有能构成完整机会逻辑链的组合。

## 当前信号
{current_desc}

## 历史候选信号
{chr(10).join(candidates_desc)}

## 任务
找出与当前信号能构成完整机会论点的历史信号组合。
- 完整论点需要：外部压力/催化剂 + 需求侧证据 + 资源/能力验证（三者不必全有，但逻辑要能自洽）
- 可以是当前信号 + 1-3条历史信号的组合

## 输出格式（严格JSON）
```json
{{
  "has_combination": true或false,
  "combinations": [
    {{
      "candidate_ids": ["C1", "C2"],
      "logic_chain": "一句话说明这组信号如何构成机会论点"
    }}
  ]
}}
```

如果没有可行组合，has_combination=false，combinations=[]。
"""


def _parse_l4_response(raw: str, candidates: List[SignalEntry]) -> List[List[SignalEntry]]:
    """解析 L4 LLM 输出，返回候选组合"""
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

    # 建立 C{i+1} → SignalEntry 映射
    idx_map = {f"C{i+1}": e for i, e in enumerate(candidates)}

    groups = []
    for combo in data.get("combinations", []):
        cids = combo.get("candidate_ids", [])
        group = [idx_map[cid] for cid in cids if cid in idx_map]
        if group:
            groups.append(group)

    return groups


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def _get_signal_id(signal: dict) -> str:
    return signal.get("signal_id") or signal.get("id") or str(id(signal))
