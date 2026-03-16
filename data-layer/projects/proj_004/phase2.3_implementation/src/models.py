"""Phase 2.3 核心数据模型"""
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass

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

@dataclass
class ActionDesignResult:
    """2.3完整输出包装"""
    request_id: str
    action_decision: ActionDecisionObject
    global_summary: Optional[str] = None
    designer_version: str = "v0.1-mvp"
    processing_time_ms: int = 0
