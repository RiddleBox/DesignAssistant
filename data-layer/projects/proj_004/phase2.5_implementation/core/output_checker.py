"""
Phase 2.5 Output Checker

输出检查器：规则层（字段存在性 + 枚举比对）+ LLM 语义层（可选增强）。

规则层：快速、零 token 消耗，catch 结构性问题（字段缺失、枚举不合理）
LLM 语义层：检查论证自洽性（如 supporting_evidence 是否真正支撑 priority_level）

设计原则：LLM 语义检查是增强项，规则检查结果始终返回，不依赖 LLM。
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import OutputCheck, CheckType, CheckStatus

# 加载公共 llm_client
_PROJ_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_PROJ_ROOT))
try:
    from llm_client import LLMClient as _LLMClient
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

try:
    from dotenv import load_dotenv
    _env = _PROJ_ROOT / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass


class OutputChecker:
    """
    输出检查器

    规则层（始终运行）：
    - 完整性检查：必需字段是否存在
    - 一致性检查：结论与证据、上下游模块间是否一致
    - 可理解性检查：关键论述是否有足够内容

    LLM 语义层（可选，需 ANTHROPIC_API_KEY）：
    - 论证自洽性：supporting_evidence 是否真正支撑 priority_level 的结论
    返回一条额外的 semantic_quality 检查结果（check_type 用 CONSISTENCY 表达）
    """

    SEMANTIC_CHECK_SYSTEM = """\
你是一个 AI 输出质量检查专家。
请检查以下情报分析链路的输出质量，重点检查：
1. 2.2 机会判断的论证是否自洽（supporting_evidence 是否真正支撑 priority_level 结论，counter_evidence 是否被合理权衡）
2. 2.2 → 2.3 的跳转是否合理（priority_level 与 decision_posture 在语义上是否一致）
3. 整体输出质量是否满足"可供组织决策参考"的基本标准

输出格式（严格 JSON）：
{
  "status": "pass|warning|fail",
  "details": "一句话说明检查结论",
  "evidence": ["具体证据1", "具体证据2"]
}
"""

    def __init__(self):
        self._llm: Optional[_LLMClient] = None
        if _HAS_LLM:
            _key = os.environ.get("ANTHROPIC_API_KEY", "")
            _url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
            if _key:
                if not _url.rstrip("/").endswith("/v1"):
                    _url = _url.rstrip("/") + "/v1"
                self._llm = _LLMClient(api_key=_key, base_url=_url)

    def check_all(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> List[OutputCheck]:
        """执行所有检查，返回检查结果列表"""
        checks = []
        checks.append(self._check_completeness(workflow_run_record, upstream_outputs))
        checks.append(self._check_consistency(workflow_run_record, upstream_outputs))
        checks.append(self._check_understandability(workflow_run_record, upstream_outputs))

        # LLM 语义层（可选增强）
        semantic = self._check_semantic_quality(upstream_outputs)
        if semantic:
            checks.append(semantic)

        return checks

    def _check_completeness(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> OutputCheck:
        """
        完整性检查

        检查是否所有必需字段都已生成，是否存在明显的信息缺失。
        """
        evidence = []
        issues = []

        # 检查 2.1 信号输出（兼容 decoded_intelligences 和旧 signals 字段）
        if "phase2_1" in upstream_outputs:
            signal_output = upstream_outputs["phase2_1"]
            signals = signal_output.get("decoded_intelligences") or signal_output.get("signals")
            if not signals:
                issues.append("2.1 信号输出缺失")
                evidence.append("phase2_1 中 decoded_intelligences/signals 字段为空")
        else:
            issues.append("缺少 2.1 信号输出")
            evidence.append("upstream_outputs 中未找到 phase2_1")

        # 检查 2.2 机会判断输出
        if "phase2_2" in upstream_outputs:
            opportunity_output = upstream_outputs["phase2_2"]
            if not opportunity_output.get("opportunity_title"):
                issues.append("2.2 机会标题缺失")
                evidence.append("phase2_2.opportunity_title 字段为空")
        else:
            issues.append("缺少 2.2 机会判断输出")
            evidence.append("upstream_outputs 中未找到 phase2_2")

        # 检查 2.3 行动设计输出
        if "phase2_3" in upstream_outputs:
            action_output = upstream_outputs["phase2_3"]
            if not action_output.get("decision_posture"):
                issues.append("2.3 决策姿态缺失")
                evidence.append("phase2_3.decision_posture 字段为空")
        else:
            issues.append("缺少 2.3 行动设计输出")
            evidence.append("upstream_outputs 中未找到 phase2_3")

        # 判断状态
        if not issues:
            status = CheckStatus.PASS
            details = "所有必需字段已生成，输出完整"
        elif len(issues) <= 2:
            status = CheckStatus.WARNING
            details = f"发现 {len(issues)} 个完整性问题：{'; '.join(issues)}"
        else:
            status = CheckStatus.FAIL
            details = f"发现 {len(issues)} 个严重完整性问题：{'; '.join(issues)}"

        return OutputCheck(
            check_type=CheckType.COMPLETENESS,
            status=status,
            details=details,
            evidence=evidence
        )

    def _check_consistency(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> OutputCheck:
        """
        一致性检查：上下游字段一致性（规则层）

        使用真实枚举值（watch/research/deep_dive/escalate/validate/pilot/hold/stop）
        """
        evidence = []
        issues = []

        # 高冲突组合检测（基于真实枚举值）
        AGGRESSIVE_POSTURES = {"pilot", "escalate", "validate"}
        CONSERVATIVE_POSTURES = {"hold", "stop", "watch"}
        STRONG_PRIORITY = {"deep_dive", "escalate"}
        WEAK_PRIORITY = {"watch", "research"}

        if "phase2_2" in upstream_outputs and "phase2_3" in upstream_outputs:
            p22 = upstream_outputs["phase2_2"]
            p23 = upstream_outputs["phase2_3"]

            priority = (p22.get("priority_level") or "").lower().strip()
            posture = (p23.get("decision_posture") or "").lower().strip()

            if priority in STRONG_PRIORITY and posture in CONSERVATIVE_POSTURES:
                issues.append(f"高优先级信号（{priority}）但行动姿态保守（{posture}），存在落差")
                evidence.append(f"priority_level={priority}, decision_posture={posture}")

            if priority in WEAK_PRIORITY and posture in AGGRESSIVE_POSTURES - {"validate"}:
                issues.append(f"低优先级信号（{priority}）但行动姿态激进（{posture}），需关注")
                evidence.append(f"priority_level={priority}, decision_posture={posture}")

        # 2.2 证据数量比例检查
        if "phase2_2" in upstream_outputs:
            p22 = upstream_outputs["phase2_2"]
            sup = len(p22.get("supporting_evidence") or [])
            cnt = len(p22.get("counter_evidence") or [])
            if sup == 0 and cnt > 0:
                issues.append("2.2 无支撑证据但有反对证据，机会论断证据基础薄弱")
                evidence.append(f"supporting_evidence={sup}, counter_evidence={cnt}")
            elif cnt > sup * 2 and sup > 0:
                issues.append("反对证据数量远超支持证据，但机会判断仍成立，需关注论证逻辑")
                evidence.append(f"supporting_evidence={sup}, counter_evidence={cnt}")

        if not issues:
            status = CheckStatus.PASS
            details = "规则层一致性检查通过，结论与证据无明显结构矛盾"
        elif len(issues) == 1:
            status = CheckStatus.WARNING
            details = f"发现 1 个一致性问题：{issues[0]}"
        else:
            status = CheckStatus.FAIL
            details = f"发现 {len(issues)} 个一致性问题：{'; '.join(issues)}"

        return OutputCheck(
            check_type=CheckType.CONSISTENCY,
            status=status,
            details=details,
            evidence=evidence
        )

    def _check_understandability(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> OutputCheck:
        """
        可理解性检查：关键论述是否有足够内容
        """
        evidence = []
        issues = []

        if "phase2_2" in upstream_outputs:
            p22 = upstream_outputs["phase2_2"]
            thesis = p22.get("opportunity_thesis") or ""
            if not thesis or len(thesis) < 50:
                issues.append("2.2 机会论述过短或缺失")
                evidence.append(f"opportunity_thesis 长度: {len(thesis)}")
            if not (p22.get("supporting_evidence") or []):
                issues.append("2.2 缺少支撑证据")
                evidence.append("supporting_evidence 为空")

        if "phase2_3" in upstream_outputs:
            p23 = upstream_outputs["phase2_3"]
            if not (p23.get("phased_plan") or []):
                issues.append("2.3 缺少分阶段计划")
                evidence.append("phased_plan 为空")
            if not (p23.get("go_no_go_criteria") or {}):
                issues.append("2.3 缺少 Go/No-Go 条件")
                evidence.append("go_no_go_criteria 为空")

        if not issues:
            status = CheckStatus.PASS
            details = "输出可被人类理解，关键判断有足够内容"
        elif len(issues) <= 2:
            status = CheckStatus.WARNING
            details = f"发现 {len(issues)} 个可理解性问题：{'; '.join(issues)}"
        else:
            status = CheckStatus.FAIL
            details = f"发现 {len(issues)} 个严重可理解性问题：{'; '.join(issues)}"

        return OutputCheck(
            check_type=CheckType.UNDERSTANDABILITY,
            status=status,
            details=details,
            evidence=evidence
        )

    def _check_semantic_quality(self, upstream_outputs: Dict[str, Any]) -> Optional[OutputCheck]:
        """
        LLM 语义层检查（可选增强）：论证自洽性。
        LLM 不可用时返回 None，不影响规则层结果。
        """
        if not self._llm:
            return None

        p22 = upstream_outputs.get("phase2_2", {})
        p23 = upstream_outputs.get("phase2_3", {})

        snippet = {
            "priority_level": p22.get("priority_level"),
            "opportunity_thesis": (p22.get("opportunity_thesis") or "")[:200],
            "supporting_evidence": (p22.get("supporting_evidence") or [])[:4],
            "counter_evidence": (p22.get("counter_evidence") or [])[:2],
            "decision_posture": p23.get("decision_posture"),
            "posture_rationale": (p23.get("posture_rationale") or "")[:200],
        }

        try:
            raw = self._llm.call(
                prompt=f"请检查以下链路输出的论证自洽性：\n{json.dumps(snippet, ensure_ascii=False, indent=2)}",
                system=self.SEMANTIC_CHECK_SYSTEM,
                model="claude-sonnet-4-6",
                max_tokens=800,
                temperature=0.0,
            )
            text = raw.strip()
            # 去掉 ```json ``` 包裹，兼容 LLM 前缀说明文字
            if "```" in text:
                import re
                m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
                if m:
                    text = m.group(1).strip()
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]
            result = json.loads(text)

            status_map = {
                "pass": CheckStatus.PASS,
                "warning": CheckStatus.WARNING,
                "fail": CheckStatus.FAIL,
            }
            return OutputCheck(
                check_type=CheckType.CONSISTENCY,
                status=status_map.get(result.get("status", "warning"), CheckStatus.WARNING),
                details=f"[LLM语义检查] {result.get('details', '')}",
                evidence=result.get("evidence", []),
            )
        except Exception as e:
            print(f"[WARN] OutputChecker LLM 语义检查失败（跳过）：{e}")
            return None
