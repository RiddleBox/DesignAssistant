"""Phase 2.3 核心数据模型"""
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field

# 行动姿态枚举
DecisionPosture = Literal["watch", "validate", "pilot", "escalate", "hold", "stop"]

@dataclass
class OpportunityObject:
    """来自2.2的机会对象"""
    opportunity_title: str
    opportunity_thesis: str
    supporting_evidence: List[str]
    counter_evidence: List[str]
    key_assumptions: List[str]
    uncertainty_map: Dict[str, str]
    priority_level: str
    # 2026-03-28 新增：对齐 2.2 多机会重构后的新增字段（可选，向后兼容）
    why_now: Optional[str] = None
    warnings: Optional[List[str]] = None
    next_validation_questions: Optional[List[str]] = None

@dataclass
class ActionDesignRequest:
    """2.3输入契约"""
    request_id: str
    opportunity_object: OpportunityObject
    context_packet: Optional[List[Dict]] = None
    org_constraints: Optional[Dict] = None

@dataclass
class PhaseResources:
    """阶段资源需求"""
    people: str
    budget: str
    time: str
    # 资源与假设验证的绑定说明：解释这批资源为什么在这个阶段投入
    # 格式："投入X人/Y万元，是为了验证[假设A]和[假设B]，验证通过后才释放后续资源"
    resource_rationale: str = ""

@dataclass
class PhasedPlanStage:
    """分阶段计划的单个阶段"""
    stage: str
    objective: str
    key_assumptions_to_test: List[str]
    actions: List[str]
    resources: PhaseResources
    milestones: List[str]
    go_no_go_criteria: List[str]
    exit_conditions: List[str]

@dataclass
class TopRisk:
    """顶级风险"""
    risk: str
    impact_on_plan: str
    mitigation: str
    # 风险触发时影响哪个阶段（对应 PhasedPlanStage.stage 的名称，空字符串表示全局影响）
    # 作用：让风险从"附录描述"变成"可约束行动结构"的实体
    blocks_stage: str = ""

@dataclass
class DebateSummary:
    """多 Agent 辩论摘要（行动设计推理链透明化）

    第1轮：鹰派陈述 / 鸽派陈述 / 执行者陈述（可行性）
    第2轮：鸽派反驳鹰派 / 执行者回应可行性挑战
    第3轮：仲裁者综合全局输出最终判断
    """
    hawk_stance: str            # 鹰派核心论点（第1轮）
    dove_stance: str            # 鸽派核心论点（第1轮）
    executor_stance: str = ""   # 执行者核心论点（第1轮，聚焦可行性）
    dove_rebuttal: str = ""     # 鸽派对鹰派的反驳（第2轮）
    executor_rebuttal: str = "" # 执行者对可行性挑战的回应（第2轮）
    resolution: str = ""        # 仲裁理由（第3轮）

@dataclass
class ActionDecisionObject:
    """2.3核心输出对象"""
    opportunity_title: str
    decision_posture: DecisionPosture
    why_this_posture: str
    phased_plan: List[PhasedPlanStage]
    top_risks: List[TopRisk]
    resource_commitment_logic: str
    fallback_path: str
    open_questions: List[str]
    # 辩论摘要：推理链透明化，让"为什么选这个 posture"有迹可循
    debate_summary: Optional[DebateSummary] = None

@dataclass
class ActionDesignResult:
    """2.3完整输出包装"""
    request_id: str
    action_decision: ActionDecisionObject
    global_summary: Optional[str] = None
    designer_version: str = "v0.1-mvp"
    processing_time_ms: int = 0
