"""
Phase 2.2 机会判断模块 - 校验逻辑

实现边界检查和证据完整性校验
"""

from typing import List, Dict, Any, Tuple
from schemas import OpportunityObject, OpportunityJudgmentRequest


class BoundaryValidator:
    """边界检查器"""

    @staticmethod
    def check_signal_source(request: OpportunityJudgmentRequest) -> Tuple[bool, str]:
        """检查点1：信号来源检查"""
        decoded_intel = request.decoded_intelligence

        if "signals" not in decoded_intel:
            return False, "输入缺少signals字段，必须来自2.1的DecodedIntelligence"

        if not isinstance(decoded_intel["signals"], list):
            return False, "signals字段必须是列表类型"

        return True, ""

    @staticmethod
    def check_evidence_completeness(opportunity: OpportunityObject) -> Tuple[bool, List[str]]:
        """检查点4：证据完整性检查"""
        warnings = []

        # 检查支持证据和反对证据是否并列存在
        if not opportunity.supporting_evidence:
            warnings.append("缺少支持证据")

        if not opportunity.counter_evidence:
            warnings.append("缺少反对证据 - 必须并列存在")

        # 检查关键假设是否显式化
        if not opportunity.key_assumptions:
            warnings.append("缺少关键假设 - 必须显式化")

        # 检查不确定性是否标注
        if not opportunity.uncertainty_map:
            warnings.append("缺少不确定性标注")

        is_valid = len(warnings) == 0
        return is_valid, warnings

    @staticmethod
    def check_output_boundary(opportunity: OpportunityObject) -> Tuple[bool, List[str]]:
        """检查点3：输出边界检查 - 确保不越界到2.3"""
        warnings = []

        # 检查next_validation_questions是否越界
        for question in opportunity.next_validation_questions:
            # 简单检查：如果包含"投入"、"资源"、"预算"等关键词，可能越界
            if any(keyword in question for keyword in ["投入", "资源分配", "预算", "人员安排"]):
                warnings.append(f"验证问题可能越界到行动方案层: {question}")

        is_valid = len(warnings) == 0
        return is_valid, warnings


class EvidenceValidator:
    """证据校验器"""

    @staticmethod
    def validate_evidence_format(evidence_list: List[str]) -> Tuple[bool, List[str]]:
        """校验证据格式 - 必须可追溯"""
        warnings = []

        for evidence in evidence_list:
            # 检查是否包含来源标识 [来源]
            if not evidence.startswith("["):
                warnings.append(f"证据缺少来源标识: {evidence[:50]}...")

        is_valid = len(warnings) == 0
        return is_valid, warnings

    @staticmethod
    def calculate_evidence_completeness(
        supporting: List[str],
        counter: List[str],
        assumptions: List[str],
        uncertainty: List[str]
    ) -> float:
        """计算证据完整度 (0-1)"""
        score = 0.0

        # 支持证据 (30%)
        if supporting:
            score += 0.3

        # 反对证据 (30%)
        if counter:
            score += 0.3

        # 关键假设 (20%)
        if assumptions:
            score += 0.2

        # 不确定性 (20%)
        if uncertainty:
            score += 0.2

        return score
