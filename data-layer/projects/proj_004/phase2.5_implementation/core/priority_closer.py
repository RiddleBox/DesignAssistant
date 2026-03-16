"""
Phase 2.5 Priority Closer

实现阶段3优先级收口逻辑：从复盘对象中自然导出优先级项。
"""

from typing import List, Dict
import sys
from pathlib import Path

# 添加父目录到路径以支持导入
sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    CriticalFinding,
    SuspectedRootCause,
    Phase3PriorityItem,
    SeverityLevel,
    AttributionLayer,
    PriorityScope
)


class PriorityCloser:
    """
    优先级收口器

    负责把验证结果转成阶段3可消费的优先级项与排序建议。
    优先级从复盘对象中自然导出，而不是外贴结论。
    """

    def __init__(self):
        self.priority_counter = 0

    def generate_priorities(
        self,
        critical_findings: List[CriticalFinding],
        suspected_root_causes: List[SuspectedRootCause]
    ) -> List[Phase3PriorityItem]:
        """
        生成阶段3优先级项

        Args:
            critical_findings: 关键发现列表
            suspected_root_causes: 初步归因列表

        Returns:
            优先级项列表（已排序）
        """
        priorities = []

        # 按严重度分组关键发现
        high_severity_findings = [f for f in critical_findings if f.severity == SeverityLevel.HIGH]
        medium_severity_findings = [f for f in critical_findings if f.severity == SeverityLevel.MEDIUM]
        low_severity_findings = [f for f in critical_findings if f.severity == SeverityLevel.LOW]

        # 为高严重度问题生成优先级项
        for finding in high_severity_findings:
            priority = self._create_priority_from_finding(finding, suspected_root_causes, order_base=1)
            if priority:
                priorities.append(priority)

        # 为中严重度问题生成优先级项
        for finding in medium_severity_findings:
            priority = self._create_priority_from_finding(finding, suspected_root_causes, order_base=100)
            if priority:
                priorities.append(priority)

        # 为低严重度问题生成优先级项（可选）
        for finding in low_severity_findings:
            priority = self._create_priority_from_finding(finding, suspected_root_causes, order_base=200)
            if priority:
                priorities.append(priority)

        # 按建议顺序排序
        priorities.sort(key=lambda p: p.suggested_order)

        return priorities

    def _create_priority_from_finding(
        self,
        finding: CriticalFinding,
        suspected_root_causes: List[SuspectedRootCause],
        order_base: int
    ) -> Phase3PriorityItem:
        """
        从关键发现创建优先级项
        """
        self.priority_counter += 1

        # 查找相关归因
        related_causes = [
            cause for cause in suspected_root_causes
            if finding.finding_id in cause.related_findings
        ]

        # 构建收口原因
        if related_causes:
            cause_summary = related_causes[0].suspected_root_cause
            reason = f"{finding.summary}。初步归因：{cause_summary}"
        else:
            reason = finding.summary

        # 判断作用范围
        scope = self._determine_scope(finding)

        # 构建优先级标题
        title = self._generate_priority_title(finding, scope)

        # 计算建议顺序
        suggested_order = order_base + self.priority_counter

        # 构建预期影响
        expected_impact = self._generate_expected_impact(finding, related_causes)

        return Phase3PriorityItem(
            priority_id=f"priority_{self.priority_counter:03d}",
            title=title,
            reason=reason,
            scope=scope,
            suggested_order=suggested_order,
            expected_impact=expected_impact,
            related_findings=[finding.finding_id]
        )

    def _determine_scope(self, finding: CriticalFinding) -> PriorityScope:
        """
        判断优先级作用范围
        """
        if finding.layer == AttributionLayer.ORCHESTRATION:
            return PriorityScope.SYSTEM
        elif finding.layer in [AttributionLayer.SIGNAL, AttributionLayer.OPPORTUNITY, AttributionLayer.ACTION]:
            return PriorityScope.MODULE
        else:
            return PriorityScope.WORKFLOW

    def _generate_priority_title(self, finding: CriticalFinding, scope: PriorityScope) -> str:
        """
        生成优先级标题
        """
        layer_name_map = {
            AttributionLayer.SIGNAL: "信号提取",
            AttributionLayer.OPPORTUNITY: "机会判断",
            AttributionLayer.ACTION: "行动设计",
            AttributionLayer.CONTEXT: "上下文支撑",
            AttributionLayer.ORCHESTRATION: "模块协作",
            AttributionLayer.VALIDATION: "验证逻辑"
        }

        layer_name = layer_name_map.get(finding.layer, "系统")

        if finding.severity == SeverityLevel.HIGH:
            return f"优先修复{layer_name}的关键问题"
        elif finding.severity == SeverityLevel.MEDIUM:
            return f"改进{layer_name}的输出质量"
        else:
            return f"优化{layer_name}的细节表达"

    def _generate_expected_impact(
        self,
        finding: CriticalFinding,
        related_causes: List[SuspectedRootCause]
    ) -> str:
        """
        生成预期影响说明
        """
        if finding.severity == SeverityLevel.HIGH:
            base_impact = "修复后将显著提升系统可用性和输出质量"
        elif finding.severity == SeverityLevel.MEDIUM:
            base_impact = "改进后将提升用户体验和决策可信度"
        else:
            base_impact = "优化后将提升输出的专业性和可读性"

        # 如果有归因，补充具体影响
        if related_causes and related_causes[0].confidence.value == "high_confidence":
            base_impact += "，归因明确，修复杠杆清晰"
        elif related_causes:
            base_impact += "，需进一步验证归因后再实施修复"

        return base_impact

    def generate_priority_summary(self, priorities: List[Phase3PriorityItem]) -> Dict[str, any]:
        """
        生成优先级摘要

        Args:
            priorities: 优先级项列表

        Returns:
            优先级摘要字典
        """
        summary = {
            "total_priorities": len(priorities),
            "by_scope": {
                "system": len([p for p in priorities if p.scope == PriorityScope.SYSTEM]),
                "module": len([p for p in priorities if p.scope == PriorityScope.MODULE]),
                "workflow": len([p for p in priorities if p.scope == PriorityScope.WORKFLOW])
            },
            "top_3_priorities": [
                {
                    "priority_id": p.priority_id,
                    "title": p.title,
                    "scope": p.scope.value
                }
                for p in priorities[:3]
            ]
        }

        return summary
