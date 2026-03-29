"""
Phase 2.5 LLM Attributor

基于 LLM 的语义归因引擎。
接收链路运行全貌（upstream_outputs + output_checks + workflow_run_record），
输出层级化关键发现与有理有据的初步归因。

设计原则：
- 归因 > 字段检查：不只说"字段缺失"，要说"为什么"以及"哪层的问题"
- 证据优先：每条归因必须引用具体字段值或运行记录作为证据
- 不确定性显式表达：low/medium/high_confidence 必须说明理由
- 规则层降为 fallback：LLM 无响应或 JSON 解析失败时，由调用方降级到规则归因

调用方：problem_attributor.py
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# ── 加载公共 llm_client.py（项目级，位于 proj_004/ 根目录）
_PROJ_ROOT = Path(__file__).parent.parent.parent.parent  # data-layer/projects/proj_004
sys.path.insert(0, str(_PROJ_ROOT))
from llm_client import LLMClient

# ── 加载 .env
try:
    from dotenv import load_dotenv
    _env_path = _PROJ_ROOT / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


# ─────────────────────────────────────────────
# Prompt 模板
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一个 AI Native 工作流系统的质量审查专家。
你的任务是：对一次完整的情报分析链路运行结果进行语义层归因分析。

链路结构：
- 2.1 情报解码：将外部文本压缩为结构化信号（DecodedIntelligence）
- 2.2 机会判断：将多条信号聚合为机会对象（OpportunityObject），输出 priority_level 和完整论证
- 2.3 行动设计：将机会判断转化为分阶段行动方案（ActionDesignResult），输出 posture 和计划
- 2.4 知识库 RAG：为上述各环节提供历史案例/约束规则/市场数据等上下文支撑

你需要：
1. 基于提供的完整输出内容，识别系统级别的关键失真点（不是字段是否存在，而是内容是否合理、论证是否自洽、上下游是否一致）
2. 对每个关键发现给出层级化归因，说明最可能的根因及其所在层（signal/opportunity/action/context/orchestration/validation）
3. 为每条归因标注可信度（high_confidence/medium_confidence/low_confidence）并说明理由
4. 如果整体质量良好，直接输出空数组，不要为了输出而制造问题

【输出要求——严格遵守】
- 直接输出 JSON，第一个字符必须是 {，最后一个字符必须是 }
- 不要输出任何前缀说明、解释、注释或 markdown 代码块
- 每个字符串字段限制在 80 字以内，列表最多 3 条
- 总输出不超过 1500 字

输出格式：
{
  "critical_findings": [
    {
      "finding_id": "finding_001",
      "summary": "一句话（≤40字）",
      "severity": "high|medium|low",
      "layer": "signal|opportunity|action|context|orchestration|validation",
      "evidence": ["证据1（≤60字）"],
      "impact": "影响说明（≤60字）"
    }
  ],
  "suspected_root_causes": [
    {
      "cause_id": "cause_001",
      "suspected_root_cause": "初步归因（≤60字，用'可能是...'）",
      "confidence": "high_confidence|medium_confidence|low_confidence",
      "reasoning": "推理说明（≤80字）",
      "evidence": ["证据（≤60字）"],
      "limitations": ["局限性（≤40字）"],
      "related_findings": ["finding_001"]
    }
  ]
}
"""


def _build_user_prompt(
    upstream_outputs: Dict[str, Any],
    output_checks_summary: List[str],
    workflow_run_record: Dict[str, Any],
) -> str:
    """构造用户 prompt，把链路输出内容精简后送入 LLM"""

    # 精简 upstream_outputs，避免超长
    p21 = upstream_outputs.get("phase2_1", {})
    p22 = upstream_outputs.get("phase2_2", {})
    p23 = upstream_outputs.get("phase2_3", {})
    p24 = upstream_outputs.get("phase2_4", {})

    # 2.1：只取信号摘要（字段名对齐真实 Signal schema）
    signals_summary = []
    for sig in (p21.get("decoded_intelligences") or p21.get("signals") or []):
        if isinstance(sig, dict):
            signals_summary.append({
                "signal_type": sig.get("signal_type") or sig.get("type"),
                "description": (
                    sig.get("description") or sig.get("signal_label")
                    or sig.get("summary") or sig.get("content") or ""
                )[:150],
                "intensity_score": sig.get("intensity_score") or sig.get("intensity"),
                "confidence_score": sig.get("confidence_score") or sig.get("confidence"),
            })

    # 2.2：取关键字段，evidence 只保留标题/首句，不传全文
    def _trim_evidence(items, max_items=4, max_chars=80):
        result = []
        for it in (items or [])[:max_items]:
            if isinstance(it, str):
                result.append(it[:max_chars])
            elif isinstance(it, dict):
                text = it.get("title") or it.get("summary") or it.get("content") or str(it)
                result.append(str(text)[:max_chars])
        return result

    opp_summary = {
        "opportunity_title": p22.get("opportunity_title"),
        "opportunity_thesis": (p22.get("opportunity_thesis") or "")[:300],
        "priority_level": p22.get("priority_level"),
        "supporting_evidence_titles": _trim_evidence(p22.get("supporting_evidence"), 5, 80),
        "counter_evidence_titles": _trim_evidence(p22.get("counter_evidence"), 3, 80),
        "key_assumptions": (p22.get("key_assumptions") or [])[:3],
        "uncertainty_factors": str(p22.get("uncertainty_factors") or p22.get("uncertainty_map") or "")[:200],
        "why_now": (p22.get("why_now") or "")[:150],
        "next_validation_question": p22.get("next_validation_question"),
    }

    # 2.3：取行动姿态和计划摘要
    action_summary = {
        "decision_posture": p23.get("decision_posture"),
        "posture_rationale": (p23.get("posture_rationale") or p23.get("why_this_posture") or "")[:200],
        "phase_count": len(p23.get("phased_plan") or []),
        "go_conditions_count": len((p23.get("go_no_go_criteria") or {}).get("go_conditions") or []),
        "exit_conditions_count": len(p23.get("exit_conditions") or []),
        "resource_commitment": (p23.get("resource_commitment") or "")[:100],
    }

    # 2.4：只取摘要，不传全文
    rag_summary = {
        "packets_count": len(p24.get("context_packets") or p24.get("retrieval_results") or []),
        "retrieval_notes": (p24.get("retrieval_notes") or p24.get("source_trace") or "")[:100],
    }

    # 规则检查结果（来自 OutputChecker）
    checks_text = "\n".join(f"  - {s}" for s in output_checks_summary) if output_checks_summary else "  （无规则检查问题）"

    # 运行记录
    run_errors = workflow_run_record.get("errors", [])
    run_time_ms = workflow_run_record.get("processing_time_ms", 0)

    prompt = f"""以下是一次完整链路运行的输出内容，请进行语义层归因分析。

## 2.1 信号提取结果
信号数量：{len(signals_summary)}
信号摘要：
{json.dumps(signals_summary, ensure_ascii=False, indent=2)}

## 2.2 机会判断结果
{json.dumps(opp_summary, ensure_ascii=False, indent=2)}

## 2.3 行动设计结果
{json.dumps(action_summary, ensure_ascii=False, indent=2)}

## 2.4 RAG 知识检索
{json.dumps(rag_summary, ensure_ascii=False, indent=2)}

## 规则检查发现（来自 OutputChecker）
{checks_text}

## 运行元数据
- 运行时错误数：{len(run_errors)}
- 总耗时：{run_time_ms}ms
{f'- 错误摘要：{run_errors[:2]}' if run_errors else ''}

请基于以上内容，识别关键失真点并给出层级化归因。重点关注：
1. 2.2 的论证是否自洽（证据支撑 priority_level 的结论）
2. 2.2 → 2.3 的 priority → posture 跳转是否合理
3. 信号质量是否能支撑机会判断的信心水平
4. 2.4 知识检索是否真正增强了下游判断（还是 fallback 跳过）
5. 是否存在跨模块的信息损耗或语义不一致
"""
    return prompt


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

class LLMAttributor:
    """
    LLM 驱动的语义归因引擎

    职责：接收完整链路运行快照，返回结构化关键发现与归因结果（原始 dict 列表）。
    调用方（ProblemAttributor）负责将 dict 转换为 pydantic 对象。
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        _key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        _url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        # llm_client.py 的 base_url 需要带 /v1
        if _url and not _url.rstrip("/").endswith("/v1"):
            _url = _url.rstrip("/") + "/v1"
        self.client = LLMClient(api_key=_key, base_url=_url)
        self._available = bool(_key)

    @property
    def available(self) -> bool:
        return self._available

    def attribute(
        self,
        upstream_outputs: Dict[str, Any],
        output_checks_summary: List[str],
        workflow_run_record: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        执行 LLM 归因。

        Returns:
            dict with keys: critical_findings (list), suspected_root_causes (list)
            Returns None if LLM call fails (caller should fallback to rule-based).
        """
        if not self._available:
            return None

        user_prompt = _build_user_prompt(
            upstream_outputs=upstream_outputs,
            output_checks_summary=output_checks_summary,
            workflow_run_record=workflow_run_record,
        )

        try:
            raw = self.client.call(
                prompt=user_prompt,
                system=SYSTEM_PROMPT,
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0.0,
            )
        except Exception as e:
            print(f"[WARN] LLMAttributor: LLM 调用失败，将 fallback 到规则归因。原因：{e}")
            return None

        # 解析 JSON：提取第一个 { 到最后一个 } 之间的内容，兼容 LLM 前缀说明文字
        try:
            text = raw.strip()
            # 去掉 ```json ``` 包裹
            if "```" in text:
                import re
                m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
                if m:
                    text = m.group(1).strip()
            # 兜底：取第一个 { 到最后一个 } 之间的内容
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
            result = json.loads(text)
            if "critical_findings" not in result or "suspected_root_causes" not in result:
                raise ValueError("缺少必要字段")
            return result
        except Exception as e:
            print(f"[WARN] LLMAttributor: JSON 解析失败，将 fallback 到规则归因。原因：{e}\nRaw: {raw[:200]}")
            return None
