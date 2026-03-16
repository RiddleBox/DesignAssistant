"""
Phase 2.5 System Retrospective Analyzer

主流程编排逻辑：真实链路运行 → 输出检查 → 问题归因 → 阶段3优先级收口
"""

import time
from typing import Dict, Any
import sys
from pathlib import Path

# 添加父目录到路径以支持导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    SystemRetrospectiveRequest,
    SystemRetrospectiveObject,
    SystemRetrospectiveResult
)
from core.output_checker import OutputChecker
from core.problem_attributor import ProblemAttributor
from core.priority_closer import PriorityCloser


class SystemRetrospectiveAnalyzer:
    """
    系统复盘分析器

    Phase 2.5 的核心入口，负责编排整个复盘流程：
    1. 真实链路运行（消费上游输出）
    2. 输出检查（完整性、一致性、可理解性）
    3. 问题归因（层级化、证据收集、可信度表达）
    4. 阶段3优先级收口（从归因导出优先级）
    """

    VERSION = "0.1.0"

    def __init__(self):
        self.output_checker = OutputChecker()
        self.problem_attributor = ProblemAttributor()
        self.priority_closer = PriorityCloser()

    def analyze(self, request: SystemRetrospectiveRequest) -> SystemRetrospectiveResult:
        """
        执行系统复盘分析

        Args:
            request: 系统复盘请求

        Returns:
            系统复盘结果
        """
        start_time = time.time()

        # 步骤1：真实链路运行（当前 MVP 阶段，直接消费上游输出）
        workflow_run_record = request.workflow_run_record
        upstream_outputs = request.upstream_outputs

        # 步骤2：输出检查
        output_checks = self.output_checker.check_all(workflow_run_record, upstream_outputs)

        # 步骤3：问题归因
        critical_findings, suspected_root_causes = self.problem_attributor.attribute_problems(
            output_checks,
            workflow_run_record,
            upstream_outputs
        )

        # 步骤4：阶段3优先级收口
        phase3_priorities = self.priority_closer.generate_priorities(
            critical_findings,
            suspected_root_causes
        )

        # 生成工作流摘要
        workflow_summary = self._generate_workflow_summary(
            workflow_run_record,
            upstream_outputs
        )

        # 生成可信度说明
        confidence_notes = self._generate_confidence_notes(
            critical_findings,
            suspected_root_causes,
            request.review_notes
        )

        # 生成警告
        warnings = self._generate_warnings(
            request,
            critical_findings,
            suspected_root_causes
        )

        # 计算处理时间
        processing_time_ms = int((time.time() - start_time) * 1000)

        # 构建系统复盘对象
        retrospective = SystemRetrospectiveObject(
            retrospective_id=f"retro_{request.case_id}_{int(time.time())}",
            case_id=request.case_id,
            retrospective_version=self.VERSION,
            processing_time_ms=processing_time_ms,
            workflow_summary=workflow_summary,
            output_checks=output_checks,
            critical_findings=critical_findings,
            suspected_root_causes=suspected_root_causes,
            phase3_priorities=phase3_priorities,
            confidence_notes=confidence_notes,
            warnings=warnings
        )

        # 生成全局摘要
        global_summary = self._generate_global_summary(retrospective)

        # 构建返回结果
        result = SystemRetrospectiveResult(
            request_id=request.request_id,
            retrospective=retrospective,
            global_summary=global_summary,
            analyzer_version=self.VERSION,
            processing_time_ms=processing_time_ms
        )

        return result

    def _generate_workflow_summary(
        self,
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any]
    ) -> str:
        """
        生成工作流摘要
        """
        summary_parts = []

        # 统计上游输出
        if "phase2_1" in upstream_outputs:
            signals_count = len(upstream_outputs["phase2_1"].get("signals", []))
            summary_parts.append(f"信号提取：{signals_count}个信号")

        if "phase2_2" in upstream_outputs:
            opportunity_title = upstream_outputs["phase2_2"].get("opportunity_title", "未知机会")
            summary_parts.append(f"机会判断：{opportunity_title}")

        if "phase2_3" in upstream_outputs:
            decision_posture = upstream_outputs["phase2_3"].get("decision_posture", "未知姿态")
            summary_parts.append(f"行动设计：{decision_posture}")

        # 统计运行状态
        errors = workflow_run_record.get("errors", [])
        if errors:
            summary_parts.append(f"运行异常：{len(errors)}个错误")
        else:
            summary_parts.append("运行正常")

        return "；".join(summary_parts)

    def _generate_confidence_notes(
        self,
        critical_findings: list,
        suspected_root_causes: list,
        review_notes: list
    ) -> list:
        """
        生成可信度说明
        """
        notes = []

        # 基于关键发现数量
        if len(critical_findings) == 0:
            notes.append("未发现明显问题，但建议保持持续监控")
        elif len(critical_findings) <= 3:
            notes.append(f"发现 {len(critical_findings)} 个关键问题，归因基于输出检查和运行记录")
        else:
            notes.append(f"发现 {len(critical_findings)} 个关键问题，建议优先处理高严重度问题")

        # 基于归因可信度
        high_confidence_causes = [c for c in suspected_root_causes if c.confidence.value == "high_confidence"]
        if high_confidence_causes:
            notes.append(f"{len(high_confidence_causes)} 个归因具有高可信度，可直接进入修复")

        low_confidence_causes = [c for c in suspected_root_causes if c.confidence.value == "low_confidence"]
        if low_confidence_causes:
            notes.append(f"{len(low_confidence_causes)} 个归因可信度较低，需进一步验证")

        # 基于人工复核
        if not review_notes:
            notes.append("当前未进行人工复核，建议补充人工走读以提升归因质量")

        return notes

    def _generate_warnings(
        self,
        request: SystemRetrospectiveRequest,
        critical_findings: list,
        suspected_root_causes: list
    ) -> list:
        """
        生成警告
        """
        warnings = []

        # 检查人工复核
        if not request.review_notes:
            warnings.append("人工复核缺失：建议补充轻量人工走读")

        # 检查证据充分性
        findings_without_evidence = [f for f in critical_findings if not f.evidence]
        if findings_without_evidence:
            warnings.append(f"证据不足：{len(findings_without_evidence)} 个关键发现缺少支撑证据")

        # 检查归因覆盖率
        findings_without_causes = []
        for finding in critical_findings:
            has_cause = any(finding.finding_id in cause.related_findings for cause in suspected_root_causes)
            if not has_cause:
                findings_without_causes.append(finding)

        if findings_without_causes:
            warnings.append(f"归因覆盖不足：{len(findings_without_causes)} 个关键发现未找到对应归因")

        # 检查样本规模
        if request.validation_mode.value == "mvp_single_case":
            warnings.append("样本规模过小：当前仅基于单案例，结论可能不具备普遍性")

        return warnings if warnings else None

    def _generate_global_summary(self, retrospective: SystemRetrospectiveObject) -> str:
        """
        生成全局摘要
        """
        summary_parts = []

        # 工作流摘要
        summary_parts.append(f"工作流：{retrospective.workflow_summary}")

        # 检查结果摘要
        passed_checks = len([c for c in retrospective.output_checks if c.status.value == "pass"])
        total_checks = len(retrospective.output_checks)
        summary_parts.append(f"输出检查：{passed_checks}/{total_checks} 通过")

        # 关键发现摘要
        high_severity_count = len([f for f in retrospective.critical_findings if f.severity.value == "high"])
        if high_severity_count > 0:
            summary_parts.append(f"发现 {high_severity_count} 个高严重度问题")
        else:
            summary_parts.append(f"发现 {len(retrospective.critical_findings)} 个问题")

        # 优先级摘要
        summary_parts.append(f"生成 {len(retrospective.phase3_priorities)} 个阶段3优先级项")

        return "；".join(summary_parts)
