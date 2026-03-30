"""
Phase 2.2 黄金模板（Golden Pattern）写回逻辑

职责：
当 Step C 输出 priority_level=deep_dive/escalate 的机会时，
自动将信号组合模式抽象为 case_record 写入 2.4 RAG 知识库。

写入后：
- 未来 Step C 调用 RAG 时会自然命中这条记录（content_type=case_record）
- 形成"判断 → 沉淀 → 再判断"的学习闭环
- 不改变 2.4 RAG 的任何接口和现有文档
"""

import os
import sys
import uuid
import importlib.util
from datetime import date
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from signal_store import SignalEntry

# 只在 deep_dive / escalate 时写入，过滤探索性机会
GOLDEN_PATTERN_PRIORITY_THRESHOLD = {"deep_dive", "escalate"}


def maybe_write_golden_pattern(
    opportunity,                        # OpportunityObject
    source_signal_entries: List,        # List[SignalEntry]，参与组合的信号
    rag_store_add_fn=None,             # 可选：2.4 RAG 写入函数
) -> bool:
    """
    判断是否需要写入黄金模板，并执行写入。

    Args:
        opportunity: OpportunityObject
        source_signal_entries: 参与组合的 SignalEntry 列表
        rag_store_add_fn: 接受 Document-like dict 的写入函数；None 时尝试自动加载

    Returns:
        True = 写入成功，False = 跳过或失败
    """
    # 检查 priority_level 门槛
    priority = getattr(opportunity, "priority_level", None) or ""
    if priority.lower() not in GOLDEN_PATTERN_PRIORITY_THRESHOLD:
        return False

    # 检查 supporting_evidence（非空才有写入价值）
    evidence = getattr(opportunity, "supporting_evidence", None) or []
    if not evidence:
        return False

    try:
        doc = _build_golden_pattern_doc(opportunity, source_signal_entries)
        fn = rag_store_add_fn or _load_rag_add_fn()
        if fn is None:
            # 无法写入时，打印一条日志，不影响主流程
            print(f"[GoldenPattern] 跳过写入（无 RAG 写入函数）: {opportunity.opportunity_title}")
            return False
        fn(doc)
        print(f"[GoldenPattern] ✅ 写入成功: {doc['title']}")
        return True
    except Exception as e:
        print(f"[GoldenPattern] 写入失败（不影响主流程）: {e}")
        return False


def _build_golden_pattern_doc(opportunity, source_signal_entries: List) -> dict:
    """构建写入 2.4 RAG 的文档字典"""
    # 信号组合摘要
    signal_combo = _summarize_signal_combo(source_signal_entries)
    signal_types = list({e.signal_type for e in source_signal_entries if hasattr(e, "signal_type")})
    domains = list({d for e in source_signal_entries if hasattr(e, "domains") for d in e.domains})
    intensity_vals = [e.intensity_score for e in source_signal_entries if hasattr(e, "intensity_score")]

    # 假设与验证问题（取前3条）
    assumptions = getattr(opportunity, "key_assumptions", []) or []
    vqs = getattr(opportunity, "next_validation_questions", []) or []

    thesis = getattr(opportunity, "opportunity_thesis", "") or ""
    why_now = getattr(opportunity, "why_now", "") or ""
    priority = getattr(opportunity, "priority_level", "")

    content = f"""机会论点：{thesis}

时机说明：{why_now}

信号组合模式：{signal_combo}
信号类型组合：{' + '.join(signal_types)}
信号强度范围：{min(intensity_vals) if intensity_vals else 'N/A'} ~ {max(intensity_vals) if intensity_vals else 'N/A'}
信号数量：{len(source_signal_entries)} 条

关键假设（前3条）：
{chr(10).join(f'- {a}' for a in assumptions[:3])}

后续验证问题（前2条）：
{chr(10).join(f'- {q}' for q in vqs[:2])}
"""

    combo_tag = "+".join(sorted(signal_types)) if signal_types else "unknown"
    today = date.today().isoformat()

    return {
        "doc_id":       f"golden_{getattr(opportunity, 'opportunity_id', str(uuid.uuid4())[:8])}",
        "title":        f"[黄金模板] {getattr(opportunity, 'opportunity_title', '未知机会')}",
        "content":      content,
        "content_type": "case_record",
        "tags":         [
            "golden_pattern",
            f"combo:{combo_tag}",
            f"priority:{priority}",
            f"date:{today}",
        ] + [f"domain:{d}" for d in domains[:3]],
        "trust_level":  "high",
        "industry":     domains[0] if domains else "general",
        "category":     "opportunity_pattern",
        "source":       "auto_generated",
    }


def _summarize_signal_combo(entries: List) -> str:
    """生成信号组合的可读摘要"""
    parts = []
    for e in entries:
        if not hasattr(e, "signal_type"):
            continue
        roles = getattr(e, "roles", [])
        role_str = f"({roles[0]})" if roles else ""
        label = getattr(e, "signal_label", "")[:30]
        parts.append(f"{e.signal_type}{role_str}：{label}")
    return " | ".join(parts) if parts else "信号组合信息不可用"


def _load_rag_add_fn():
    """尝试自动加载 2.4 RAG 的文档写入函数"""
    try:
        rag_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__),
                         "..", "phase2.4_implementation", "rag_system")
        )
        core_path = os.path.join(rag_path, "core")
        if core_path not in sys.path:
            sys.path.insert(0, core_path)
        if rag_path not in sys.path:
            sys.path.insert(0, rag_path)

        # 尝试加载 VectorStore 的 add_document 方法
        store_path = os.path.join(rag_path, "core", "vector_store.py")
        if not os.path.exists(store_path):
            return None

        spec = importlib.util.spec_from_file_location("vector_store", store_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # 找到默认数据目录的 VectorStore
        data_dir = os.path.join(rag_path, "data")
        if hasattr(mod, "VectorStore"):
            vs = mod.VectorStore(data_dir=data_dir)
            return vs.add_document
        return None
    except Exception as e:
        print(f"[GoldenPattern] 自动加载 RAG 写入函数失败（忽略）: {e}")
        return None
