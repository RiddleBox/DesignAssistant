"""
Phase 2.2 机会判断模块 - 核心判断引擎

实现6步判断流程：信号聚类 → 论点形成 → 证据组织 → 不确定性评估 → 分级判断 → 升级建议
"""

import time
import uuid
from typing import Dict, Any, List, Tuple
from schemas import (
    OpportunityJudgmentRequest,
    OpportunityJudgmentResult,
    OpportunityObject,
    Diagnostics,
    ErrorInfo
)
from validators import BoundaryValidator, EvidenceValidator


class JudgmentEngine:
    """机会判断引擎"""

    def __init__(self, llm_client=None):
        """
        初始化判断引擎

        Args:
            llm_client: LLM客户端（用于Prompt-first实现）
        """
        self.llm_client = llm_client
        self.judgment_version = "v1.0-mvp"
        self.boundary_validator = BoundaryValidator()
        self.evidence_validator = EvidenceValidator()

    def judge(self, request: OpportunityJudgmentRequest) -> OpportunityJudgmentResult:
        """
        执行机会判断

        Args:
            request: 机会判断请求

        Returns:
            OpportunityJudgmentResult: 判断结果
        """
        start_time = time.time()

        try:
            # 边界检查：信号来源检查
            is_valid, error_msg = self.boundary_validator.check_signal_source(request)
            if not is_valid:
                return self._create_error_result(
                    "INVALID_INPUT",
                    error_msg,
                    int((time.time() - start_time) * 1000)
                )

            # 提取信号
            signals = request.decoded_intelligence.get("signals", [])

            # 检查信号数量
            if len(signals) == 0:
                return self._create_insufficient_evidence_result(
                    signals,
                    ["没有可用信号"],
                    int((time.time() - start_time) * 1000)
                )

            # 执行6步判断流程
            opportunity = self._execute_judgment_pipeline(request, signals)

            # 边界检查：证据完整性
            is_valid, warnings = self.boundary_validator.check_evidence_completeness(opportunity)

            # 边界检查：输出边界
            _, boundary_warnings = self.boundary_validator.check_output_boundary(opportunity)
            warnings.extend(boundary_warnings)

            # 计算处理时间
            processing_time = int((time.time() - start_time) * 1000)
            opportunity.processing_time_ms = processing_time

            # 计算证据完整度
            evidence_completeness = self.evidence_validator.calculate_evidence_completeness(
                opportunity.supporting_evidence,
                opportunity.counter_evidence,
                opportunity.key_assumptions,
                opportunity.uncertainty_map
            )

            # 构建诊断信息
            diagnostics = Diagnostics(
                signal_count=len(signals),
                evidence_completeness=evidence_completeness,
                boundary_warnings=warnings
            )

            # 返回成功结果
            return OpportunityJudgmentResult(
                opportunity=opportunity,
                status="success",
                diagnostics=diagnostics
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return self._create_error_result(
                "INTERNAL_ERROR",
                str(e),
                processing_time
            )

    def _execute_judgment_pipeline(
        self,
        request: OpportunityJudgmentRequest,
        signals: List[Dict[str, Any]]
    ) -> OpportunityObject:
        """执行6步判断流程"""

        # 步骤1：信号聚类与主题识别
        theme = self._cluster_signals_and_identify_theme(signals)

        # 步骤2：机会论点形成
        thesis = self._form_opportunity_thesis(signals, theme)

        # 步骤3：证据组织
        supporting, counter, assumptions = self._organize_evidence(
            signals,
            request.context_packet
        )

        # 步骤4：不确定性评估
        uncertainty_map = self._assess_uncertainty(signals, supporting, counter)

        # 步骤5：分级判断
        priority_level = self._classify_priority(signals, supporting, counter, uncertainty_map)

        # 步骤6：升级建议
        validation_questions = self._generate_validation_questions(
            priority_level,
            uncertainty_map
        )

        # 构建机会对象
        opportunity = OpportunityObject(
            opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
            opportunity_title=theme,
            opportunity_thesis=thesis,
            related_signals=signals,
            supporting_evidence=supporting,
            counter_evidence=counter,
            key_assumptions=assumptions,
            uncertainty_map=uncertainty_map,
            priority_level=priority_level,
            next_validation_questions=validation_questions,
            judgment_version=self.judgment_version,
            processing_time_ms=0  # 将在外层设置
        )

        return opportunity

    def _cluster_signals_and_identify_theme(self, signals: List[Dict[str, Any]]) -> str:
        """步骤1：信号聚类与主题识别"""
        # MVP实现：基于信号类型简单聚类
        signal_types = [s.get("signal_type", "unknown") for s in signals]
        type_counts = {}
        for st in signal_types:
            type_counts[st] = type_counts.get(st, 0) + 1

        dominant_type = max(type_counts, key=type_counts.get)
        return f"{dominant_type}类机会主题"

    def _form_opportunity_thesis(
        self,
        signals: List[Dict[str, Any]],
        theme: str
    ) -> str:
        """步骤2：机会论点形成"""
        # MVP实现：基于信号摘要形成论点
        signal_summaries = [s.get("signal_summary", "") for s in signals if s.get("signal_summary")]

        if len(signal_summaries) == 1:
            return f"基于{theme}，{signal_summaries[0]}"
        else:
            return f"基于{len(signals)}个{theme}信号，存在潜在机会"

    def _organize_evidence(
        self,
        signals: List[Dict[str, Any]],
        context_packet
    ) -> Tuple[List[str], List[str], List[str]]:
        """步骤3：证据组织"""
        supporting = []
        counter = []
        assumptions = []

        # 从信号中提取支持证据
        for i, signal in enumerate(signals):
            signal_id = signal.get("signal_id", f"signal_{i}")
            summary = signal.get("signal_summary", "未知信号")
            supporting.append(f"[{signal_id}] {summary}")

        # 从2.4证据包补充证据
        if context_packet:
            if context_packet.similar_cases:
                for case in context_packet.similar_cases:
                    supporting.append(f"[2.4-similar] {case}")

            if context_packet.counter_examples:
                for example in context_packet.counter_examples:
                    counter.append(f"[2.4-counter] {example}")

        # 如果没有反对证据，添加默认项
        if not counter:
            if len(signals) == 1:
                counter.append("[推断] 信号来源单一，缺少交叉验证")
            else:
                counter.append("[推断] 未发现明显反对证据，但需警惕潜在风险")

        # 生成关键假设
        assumptions.append(f"假设：当前{len(signals)}个信号能够代表真实趋势 [重要性: critical]")
        if not context_packet:
            assumptions.append("假设：无外部证据验证的情况下，信号可靠性足够 [重要性: important]")

        return supporting, counter, assumptions

    def _assess_uncertainty(
        self,
        signals: List[Dict[str, Any]],
        supporting: List[str],
        counter: List[str]
    ) -> List[str]:
        """步骤4：不确定性评估"""
        uncertainty = []

        # 证据完整度不确定性
        if len(signals) < 3:
            uncertainty.append("evidence_completeness: high - 信号数量不足，缺少交叉验证")
        elif len(signals) < 5:
            uncertainty.append("evidence_completeness: medium - 信号数量中等，建议补充")

        # 信号可靠性不确定性
        if len(supporting) <= len(counter):
            uncertainty.append("signal_reliability: medium - 反对证据较多，需谨慎判断")

        # 高强度信号的执行风险
        avg_intensity = sum(s.get("intensity", 0) for s in signals) / max(len(signals), 1)
        if avg_intensity >= 8:
            uncertainty.append("execution_risk: medium - 高强度机会需要快速决策，存在执行风险")

        return uncertainty

    def _classify_priority(
        self,
        signals: List[Dict[str, Any]],
        supporting: List[str],
        counter: List[str],
        uncertainty: List[str]
    ) -> str:
        """步骤5：分级判断"""
        signal_count = len(signals)
        evidence_ratio = len(supporting) / max(len(counter), 1)
        uncertainty_level = len([u for u in uncertainty if "high" in u])

        # 计算信号强度
        avg_intensity = sum(s.get("intensity", 0) for s in signals) / max(signal_count, 1)

        # 检测escalate触发条件：高强度+多信号+竞争压力
        has_urgency = any(
            "竞争" in s.get("signal_summary", "") or
            "窗口期" in s.get("signal_summary", "") or
            "抢占" in s.get("signal_summary", "")
            for s in signals
        )

        if signal_count >= 5 and avg_intensity >= 8 and has_urgency:
            return "escalate"
        elif signal_count >= 4 and evidence_ratio >= 1.5:
            return "deep_dive"
        elif signal_count >= 2 and evidence_ratio >= 1.5:
            return "research"
        elif signal_count == 1 or uncertainty_level >= 2:
            return "watch"
        else:
            return "watch"

    def _generate_validation_questions(
        self,
        priority_level: str,
        uncertainty_map: List[str]
    ) -> List[str]:
        """步骤6：升级建议"""
        questions = []

        if priority_level == "watch":
            questions.append("是否有更多相关信号出现？")
            questions.append("当前信号的可靠性如何验证？")
        elif priority_level == "research":
            questions.append("是否存在相似的成功/失败案例？")
            questions.append("市场对此的接受度如何？")
        elif priority_level == "deep_dive":
            questions.append("如何量化该机会的潜在影响？")
            questions.append("竞争对手是否有类似布局？")
        elif priority_level == "escalate":
            questions.append("是否需要立即启动深度调研？")
            questions.append("时间窗口期有多长？")

        # 基于不确定性补充问题
        if any("evidence_completeness" in u for u in uncertainty_map):
            questions.append("如何补充缺失的关键证据？")

        return questions

    def _create_error_result(
        self,
        error_code: str,
        error_message: str,
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建错误结果"""
        return OpportunityJudgmentResult(
            opportunity=None,
            status="error",
            error=ErrorInfo(code=error_code, message=error_message)
        )

    def _create_insufficient_evidence_result(
        self,
        signals: List[Dict[str, Any]],
        warnings: List[str],
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建证据不足结果"""
        # 创建最小机会对象
        opportunity = OpportunityObject(
            opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
            opportunity_title="证据不足",
            opportunity_thesis="当前信号不足以形成有效判断",
            related_signals=signals,
            supporting_evidence=[],
            counter_evidence=["[系统] 信号数量不足"],
            key_assumptions=["假设：需要更多信号才能形成有效判断"],
            uncertainty_map=["evidence_completeness: high - 缺少足够信号"],
            priority_level="watch",
            next_validation_questions=["是否有更多相关信号？", "当前信号是否可靠？"],
            judgment_version=self.judgment_version,
            processing_time_ms=processing_time
        )

        diagnostics = Diagnostics(
            signal_count=len(signals),
            evidence_completeness=0.0,
            boundary_warnings=warnings
        )

        return OpportunityJudgmentResult(
            opportunity=opportunity,
            status="insufficient_evidence",
            diagnostics=diagnostics
        )
