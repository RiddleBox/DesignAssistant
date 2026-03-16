"""
Phase 2.5 Output Checker

实现输出检查逻辑：完整性、一致性、可理解性检查。
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

# 添加父目录到路径以支持导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import OutputCheck, CheckType, CheckStatus


class OutputChecker:
    """
    输出检查器

    负责对系统输出进行结构化检查，包括：
    - 完整性检查：是否所有必需字段都已生成
    - 一致性检查：结论与证据是否一致
    - 可理解性检查：输出是否可被人类理解
    """

    def check_all(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> List[OutputCheck]:
        """
        执行所有检查

        Args:
            workflow_run_record: 真实链路运行记录
            upstream_outputs: 上游输出（2.1~2.4）

        Returns:
            检查结果列表
        """
        checks = []

        # 完整性检查
        checks.append(self._check_completeness(workflow_run_record, upstream_outputs))

        # 一致性检查
        checks.append(self._check_consistency(workflow_run_record, upstream_outputs))

        # 可理解性检查
        checks.append(self._check_understandability(workflow_run_record, upstream_outputs))

        return checks

    def _check_completeness(self, workflow_run_record: Dict[str, Any], upstream_outputs: Dict[str, Any]) -> OutputCheck:
        """
        完整性检查

        检查是否所有必需字段都已生成，是否存在明显的信息缺失。
        """
        evidence = []
        issues = []

        # 检查 2.1 信号输出
        if "phase2_1" in upstream_outputs:
            signal_output = upstream_outputs["phase2_1"]
            if not signal_output.get("signals"):
                issues.append("2.1 信号输出缺失")
                evidence.append("phase2_1.signals 字段为空")
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
        一致性检查

        检查结论与证据是否一致，不同模块输出之间是否存在矛盾。
        """
        evidence = []
        issues = []

        # 检查 2.2 机会判断与 2.3 行动设计的一致性
        if "phase2_2" in upstream_outputs and "phase2_3" in upstream_outputs:
            opportunity_output = upstream_outputs["phase2_2"]
            action_output = upstream_outputs["phase2_3"]

            # 检查优先级与决策姿态的一致性
            priority_level = opportunity_output.get("priority_level", "").lower()
            decision_posture = action_output.get("decision_posture", "").lower()

            if priority_level == "high" and decision_posture in ["hold", "stop"]:
                issues.append("高优先级机会却采取 hold/stop 姿态")
                evidence.append(f"priority_level={priority_level}, decision_posture={decision_posture}")

            if priority_level == "low" and decision_posture in ["escalate", "pilot"]:
                issues.append("低优先级机会却采取 escalate/pilot 姿态")
                evidence.append(f"priority_level={priority_level}, decision_posture={decision_posture}")

        # 检查 2.2 证据与结论的一致性
        if "phase2_2" in upstream_outputs:
            opportunity_output = upstream_outputs["phase2_2"]
            supporting_evidence = opportunity_output.get("supporting_evidence", [])
            counter_evidence = opportunity_output.get("counter_evidence", [])

            if len(counter_evidence) > len(supporting_evidence) * 2:
                issues.append("反对证据远多于支持证据，但仍形成机会判断")
                evidence.append(f"supporting_evidence={len(supporting_evidence)}, counter_evidence={len(counter_evidence)}")

        # 判断状态
        if not issues:
            status = CheckStatus.PASS
            details = "结论与证据一致，模块输出无明显矛盾"
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
        可理解性检查

        检查输出是否可被人类理解，关键判断是否有足够解释。
        """
        evidence = []
        issues = []

        # 检查 2.2 机会判断的可理解性
        if "phase2_2" in upstream_outputs:
            opportunity_output = upstream_outputs["phase2_2"]

            # 检查机会论述是否存在
            opportunity_thesis = opportunity_output.get("opportunity_thesis", "")
            if not opportunity_thesis or len(opportunity_thesis) < 50:
                issues.append("2.2 机会论述过短或缺失")
                evidence.append(f"opportunity_thesis 长度: {len(opportunity_thesis)}")

            # 检查是否有支撑证据
            supporting_evidence = opportunity_output.get("supporting_evidence", [])
            if not supporting_evidence:
                issues.append("2.2 缺少支撑证据")
                evidence.append("supporting_evidence 为空")

        # 检查 2.3 行动设计的可理解性
        if "phase2_3" in upstream_outputs:
            action_output = upstream_outputs["phase2_3"]

            # 检查是否有分阶段计划
            phased_plan = action_output.get("phased_plan", [])
            if not phased_plan:
                issues.append("2.3 缺少分阶段计划")
                evidence.append("phased_plan 为空")

            # 检查是否有 Go/No-Go 条件
            go_no_go_criteria = action_output.get("go_no_go_criteria", {})
            if not go_no_go_criteria:
                issues.append("2.3 缺少 Go/No-Go 条件")
                evidence.append("go_no_go_criteria 为空")

        # 判断状态
        if not issues:
            status = CheckStatus.PASS
            details = "输出可被人类理解，关键判断有足够解释"
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
