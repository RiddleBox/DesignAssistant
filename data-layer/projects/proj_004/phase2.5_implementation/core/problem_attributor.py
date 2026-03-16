"""
Phase 2.5 Problem Attributor

实现问题归因逻辑：层级化归因、证据收集、可信度表达。
"""

from typing import List, Dict, Any, Tuple
import sys
from pathlib import Path

# 添加父目录到路径以支持导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    CriticalFinding,
    SuspectedRootCause,
    OutputCheck,
    SeverityLevel,
    AttributionLayer,
    ConfidenceLevel,
    CheckStatus
)


class ProblemAttributor:
    """
    问题归因器

    负责把系统运行中暴露的问题组织成可解释、可追踪、可回写的层级化归因结构。
    """

    def __init__(self):
        self.finding_counter = 0
        self.cause_counter = 0

    def attribute_problems(
        self,
        output_checks: List[OutputCheck],
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """
        执行问题归因

        Args:
            output_checks: 输出检查结果
            workflow_run_record: 真实链路运行记录
            upstream_outputs: 上游输出

        Returns:
            (关键发现列表, 初步归因列表)
        """
        critical_findings = []
        suspected_root_causes = []

        # 从输出检查中识别关键发现
        for check in output_checks:
            if check.status in [CheckStatus.WARNING, CheckStatus.FAIL]:
                findings, causes = self._analyze_check_failure(check, workflow_run_record, upstream_outputs)
                critical_findings.extend(findings)
                suspected_root_causes.extend(causes)

        # 从运行记录中识别额外问题
        additional_findings, additional_causes = self._analyze_runtime_issues(
            workflow_run_record,
            upstream_outputs
        )
        critical_findings.extend(additional_findings)
        suspected_root_causes.extend(additional_causes)

        return critical_findings, suspected_root_causes

    def _analyze_check_failure(
        self,
        check: OutputCheck,
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """
        分析检查失败，产生关键发现与初步归因
        """
        findings = []
        causes = []

        # 根据检查类型进行不同的归因
        if check.check_type.value == "completeness":
            finding, cause = self._attribute_completeness_issue(check, upstream_outputs)
            if finding:
                findings.append(finding)
            if cause:
                causes.append(cause)

        elif check.check_type.value == "consistency":
            finding, cause = self._attribute_consistency_issue(check, upstream_outputs)
            if finding:
                findings.append(finding)
            if cause:
                causes.append(cause)

        elif check.check_type.value == "understandability":
            finding, cause = self._attribute_understandability_issue(check, upstream_outputs)
            if finding:
                findings.append(finding)
            if cause:
                causes.append(cause)

        return findings, causes

    def _attribute_completeness_issue(
        self,
        check: OutputCheck,
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[CriticalFinding, SuspectedRootCause]:
        """
        归因完整性问题
        """
        self.finding_counter += 1
        self.cause_counter += 1

        # 判断严重级别
        severity = SeverityLevel.HIGH if check.status == CheckStatus.FAIL else SeverityLevel.MEDIUM

        # 判断归因层级
        if "phase2_1" in check.details:
            layer = AttributionLayer.SIGNAL
            suspected_cause = "信号提取阶段可能遗漏了关键信息"
            confidence = ConfidenceLevel.MEDIUM_CONFIDENCE
        elif "phase2_2" in check.details:
            layer = AttributionLayer.OPPORTUNITY
            suspected_cause = "机会判断阶段可能未完整生成必需字段"
            confidence = ConfidenceLevel.MEDIUM_CONFIDENCE
        elif "phase2_3" in check.details:
            layer = AttributionLayer.ACTION
            suspected_cause = "行动设计阶段可能未完整生成必需字段"
            confidence = ConfidenceLevel.MEDIUM_CONFIDENCE
        else:
            layer = AttributionLayer.ORCHESTRATION
            suspected_cause = "模块协作或接口传递可能导致信息丢失"
            confidence = ConfidenceLevel.LOW_CONFIDENCE

        finding = CriticalFinding(
            finding_id=f"finding_{self.finding_counter:03d}",
            summary=f"输出完整性问题：{check.details}",
            severity=severity,
            layer=layer,
            evidence=check.evidence,
            impact="缺失的字段可能导致后续判断或行动设计无法正常进行"
        )

        cause = SuspectedRootCause(
            cause_id=f"cause_{self.cause_counter:03d}",
            suspected_root_cause=suspected_cause,
            confidence=confidence,
            reasoning=f"基于输出检查发现：{check.details}",
            evidence=check.evidence,
            limitations=["未获取原始输入材料，无法对比验证"],
            related_findings=[finding.finding_id]
        )

        return finding, cause

    def _attribute_consistency_issue(
        self,
        check: OutputCheck,
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[CriticalFinding, SuspectedRootCause]:
        """
        归因一致性问题
        """
        self.finding_counter += 1
        self.cause_counter += 1

        severity = SeverityLevel.MEDIUM if check.status == CheckStatus.WARNING else SeverityLevel.HIGH

        # 一致性问题通常涉及多个模块
        layer = AttributionLayer.ORCHESTRATION

        finding = CriticalFinding(
            finding_id=f"finding_{self.finding_counter:03d}",
            summary=f"输出一致性问题：{check.details}",
            severity=severity,
            layer=layer,
            evidence=check.evidence,
            impact="不一致的输出可能导致决策混乱或执行偏差"
        )

        cause = SuspectedRootCause(
            cause_id=f"cause_{self.cause_counter:03d}",
            suspected_root_cause="模块间协作逻辑可能存在不一致，或上下游模块对同一概念的理解存在偏差",
            confidence=ConfidenceLevel.MEDIUM_CONFIDENCE,
            reasoning=f"基于一致性检查发现：{check.details}",
            evidence=check.evidence,
            limitations=["需要进一步检查模块间接口定义与协作协议"],
            related_findings=[finding.finding_id]
        )

        return finding, cause

    def _attribute_understandability_issue(
        self,
        check: OutputCheck,
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[CriticalFinding, SuspectedRootCause]:
        """
        归因可理解性问题
        """
        self.finding_counter += 1
        self.cause_counter += 1

        severity = SeverityLevel.LOW if check.status == CheckStatus.WARNING else SeverityLevel.MEDIUM

        # 判断归因层级
        if "2.2" in check.details:
            layer = AttributionLayer.OPPORTUNITY
            suspected_cause = "机会判断阶段可能未提供足够的解释或证据"
        elif "2.3" in check.details:
            layer = AttributionLayer.ACTION
            suspected_cause = "行动设计阶段可能未提供足够的计划细节或决策依据"
        else:
            layer = AttributionLayer.VALIDATION
            suspected_cause = "输出格式或表达方式可能不够清晰"

        finding = CriticalFinding(
            finding_id=f"finding_{self.finding_counter:03d}",
            summary=f"输出可理解性问题：{check.details}",
            severity=severity,
            layer=layer,
            evidence=check.evidence,
            impact="不够清晰的输出可能导致人工复核困难或决策延迟"
        )

        cause = SuspectedRootCause(
            cause_id=f"cause_{self.cause_counter:03d}",
            suspected_root_cause=suspected_cause,
            confidence=ConfidenceLevel.MEDIUM_CONFIDENCE,
            reasoning=f"基于可理解性检查发现：{check.details}",
            evidence=check.evidence,
            limitations=["可理解性判断具有主观性，需要人工复核确认"],
            related_findings=[finding.finding_id]
        )

        return finding, cause

    def _analyze_runtime_issues(
        self,
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any]
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """
        分析运行时问题（如错误、异常、性能问题）
        """
        findings = []
        causes = []

        # 检查是否有运行错误
        errors = workflow_run_record.get("errors", [])
        if errors:
            self.finding_counter += 1
            self.cause_counter += 1

            finding = CriticalFinding(
                finding_id=f"finding_{self.finding_counter:03d}",
                summary=f"运行时错误：发现 {len(errors)} 个错误",
                severity=SeverityLevel.HIGH,
                layer=AttributionLayer.ORCHESTRATION,
                evidence=[str(error) for error in errors[:3]],  # 只取前3个错误作为证据
                impact="运行时错误可能导致系统无法正常完成任务"
            )

            cause = SuspectedRootCause(
                cause_id=f"cause_{self.cause_counter:03d}",
                suspected_root_cause="模块执行过程中可能存在异常处理不当或输入验证不足",
                confidence=ConfidenceLevel.HIGH_CONFIDENCE,
                reasoning=f"直接观察到 {len(errors)} 个运行时错误",
                evidence=[str(error) for error in errors[:3]],
                limitations=[],
                related_findings=[finding.finding_id]
            )

            findings.append(finding)
            causes.append(cause)

        # 检查是否有性能问题
        processing_time = workflow_run_record.get("processing_time_ms", 0)
        if processing_time > 60000:  # 超过60秒
            self.finding_counter += 1
            self.cause_counter += 1

            finding = CriticalFinding(
                finding_id=f"finding_{self.finding_counter:03d}",
                summary=f"性能问题：处理时间过长（{processing_time}ms）",
                severity=SeverityLevel.MEDIUM,
                layer=AttributionLayer.ORCHESTRATION,
                evidence=[f"processing_time_ms={processing_time}"],
                impact="处理时间过长可能影响系统响应速度和用户体验"
            )

            cause = SuspectedRootCause(
                cause_id=f"cause_{self.cause_counter:03d}",
                suspected_root_cause="某个模块可能存在性能瓶颈，或模块间调用次数过多",
                confidence=ConfidenceLevel.LOW_CONFIDENCE,
                reasoning=f"观察到处理时间为 {processing_time}ms，超过预期阈值",
                evidence=[f"processing_time_ms={processing_time}"],
                limitations=["需要更详细的性能分析才能确定具体瓶颈"],
                related_findings=[finding.finding_id]
            )

            findings.append(finding)
            causes.append(cause)

        return findings, causes
