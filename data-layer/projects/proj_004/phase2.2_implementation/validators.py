"""
Phase 2.2 机会判断模块 - 校验逻辑

实现边界检查和证据完整性校验
"""

from typing import List, Dict, Any, Tuple
from schemas import OpportunityObject, OpportunityJudgmentRequest


class BoundaryValidator:
    """边界检查器"""

    @staticmethod
    def check_signal_source_v2(enriched_signals: list) -> Tuple[bool, str]:
        """检查点1 v2：适配多条 DecodedIntelligence 提取后的 enriched_signals"""
        if not isinstance(enriched_signals, list):
            return False, "enriched_signals 必须是列表类型"
        # 允许空列表（由上层单独处理 insufficient_evidence）
        return True, ""

    @staticmethod
    def check_signal_source(request) -> Tuple[bool, str]:
        """检查点1 v1（保留兼容）"""
        decoded_intel = getattr(request, "decoded_intelligence", None)
        if decoded_intel is None:
            decoded_intel = {}
        if isinstance(decoded_intel, dict):
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
        """检查点3：输出边界检查 - 确保不越界到2.3

        边界说明：
        - 合法（2.2 范围内）：验证问题、信息收集问题、观察指标、预算窗口判断
        - 越界（2.3 范围）：资源分配、人员安排、执行计划、立项决策
        """
        warnings = []

        # 仅在出现明确的行动指令类词汇时才判越界
        # 注意：「预算窗口」「预算规模」是观察词，不越界；「预算分配」「预算申请」是行动词
        BOUNDARY_KEYWORDS = ["资源分配", "人员安排", "立项", "启动项目", "分配预算", "申请预算"]

        for question in opportunity.next_validation_questions:
            if any(keyword in question for keyword in BOUNDARY_KEYWORDS):
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
    def check_signal_traceability(related_signals: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """
        检查信号可追溯性：每条 enriched signal 是否有有效的 source_ref。

        返回：
            - traceability_score (0.0~1.0)：有 source_ref 的信号占比
            - warnings：不可追溯信号的警告列表
        """
        if not related_signals:
            return 0.0, ["无关联信号，无法评估可追溯性"]

        warnings = []
        traceable = 0
        for sig in related_signals:
            ref = sig.get("source_ref", "")
            if ref and ref.strip() and ref != "unknown":
                traceable += 1
            else:
                label = sig.get("signal_label", sig.get("signal_id", "unknown"))
                warnings.append(f"信号缺少 source_ref，无法追溯来源：{label[:40]}")

        score = traceable / len(related_signals)
        return score, warnings

    @staticmethod
    def calculate_evidence_completeness(
        supporting: List[str],
        counter: List[str],
        assumptions: List[str],
        uncertainty: List[str],
        related_signals: List[Dict[str, Any]] = None
    ) -> float:
        """
        计算证据完整度 (0.0~1.0)

        评分维度：
          支持证据存在       15%
          支持证据 2+ 条     10%（单条只拿基础分）
          反对证据存在       15%
          反对证据 2+ 条     10%
          关键假设           15%
          不确定性标注       15%
          信号可追溯性       20%（source_ref 覆盖率）
        """
        score = 0.0

        # 支持证据（25%）
        if supporting:
            score += 0.15
            if len(supporting) >= 2:
                score += 0.10

        # 反对证据（25%）
        if counter:
            score += 0.15
            if len(counter) >= 2:
                score += 0.10

        # 关键假设（15%）
        if assumptions:
            score += 0.15

        # 不确定性标注（15%）
        if uncertainty:
            score += 0.15

        # 信号可追溯性（20%）
        if related_signals is not None:
            traceability, _ = EvidenceValidator.check_signal_traceability(related_signals)
            score += 0.20 * traceability

        return round(score, 3)
