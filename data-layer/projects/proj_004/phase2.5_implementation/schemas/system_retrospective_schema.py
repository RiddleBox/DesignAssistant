"""
Phase 2.5 System Retrospective Schema Definitions

定义 Phase 2.5 整合验证与复盘模块的核心数据结构。
主产物：结构化系统复盘对象（SystemRetrospectiveObject）

版本：v0.1
最后更新：2026-03-16
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# 枚举定义
# ============================================================================

class SeverityLevel(str, Enum):
    """严重级别枚举"""
    HIGH = "high"      # 严重影响系统可用性或输出质量，必须优先修复
    MEDIUM = "medium"  # 明显影响用户体验或部分场景失效，应尽快修复
    LOW = "low"        # 轻微问题或边缘场景，可后续优化


class AttributionLayer(str, Enum):
    """归因层级枚举"""
    SIGNAL = "signal"              # 信号级问题（2.1 相关）
    OPPORTUNITY = "opportunity"    # 机会级问题（2.2 相关）
    ACTION = "action"              # 行动级问题（2.3 相关）
    CONTEXT = "context"            # 上下文问题（2.4 相关）
    ORCHESTRATION = "orchestration"  # 编排级问题（模块协作、接口、流程）
    VALIDATION = "validation"      # 验证级问题（2.5 自身验证逻辑）


class CheckType(str, Enum):
    """检查类型枚举"""
    COMPLETENESS = "completeness"      # 完整性检查
    CONSISTENCY = "consistency"        # 一致性检查
    UNDERSTANDABILITY = "understandability"  # 可理解性检查


class CheckStatus(str, Enum):
    """检查状态枚举"""
    PASS = "pass"        # 通过
    WARNING = "warning"  # 警告
    FAIL = "fail"        # 失败


class ConfidenceLevel(str, Enum):
    """可信度等级枚举"""
    HIGH_CONFIDENCE = "high_confidence"      # 有充分证据支持，归因基本确定
    MEDIUM_CONFIDENCE = "medium_confidence"  # 有部分证据支持，归因较为合理
    LOW_CONFIDENCE = "low_confidence"        # 证据不足，归因仅为怀疑


class PriorityScope(str, Enum):
    """优先级作用范围枚举"""
    MODULE = "module"    # 模块级
    SYSTEM = "system"    # 系统级
    WORKFLOW = "workflow"  # 工作流级


class ValidationMode(str, Enum):
    """验证模式枚举"""
    MVP_SINGLE_CASE = "mvp_single_case"  # MVP 单案例模式（默认）
    BATCH_CASES = "batch_cases"          # 批量案例模式
    REGRESSION = "regression"            # 回归测试模式


# ============================================================================
# 输入契约：SystemRetrospectiveRequest
# ============================================================================

class SystemRetrospectiveRequest(BaseModel):
    """
    系统复盘请求对象

    这是 Phase 2.5 的输入契约，定义了进行系统级复盘所需的最小输入。
    """

    request_id: str = Field(
        ...,
        description="本次系统复盘请求唯一ID，用于追踪与回放"
    )

    case_id: str = Field(
        ...,
        description="真实案例唯一ID，至少对应一条高价值样本"
    )

    workflow_run_record: Dict[str, Any] = Field(
        ...,
        description="本次真实链路运行记录，包含中间对象、运行证据和关键产出"
    )

    upstream_outputs: Dict[str, Any] = Field(
        ...,
        description="2.1~2.4 的关键输出集合，允许按最小字段消费"
    )

    review_notes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="人工复核记录（轻量增强项）"
    )

    validation_mode: ValidationMode = Field(
        default=ValidationMode.MVP_SINGLE_CASE,
        description="验证模式，默认为 MVP 单案例模式"
    )

    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="约束与提醒，如排除条件、优先级约束等"
    )


# ============================================================================
# 输出契约核心组件
# ============================================================================

class OutputCheck(BaseModel):
    """
    输出检查结果

    记录对系统输出的结构化检查结果（完整性、一致性、可理解性）
    """

    check_type: CheckType = Field(
        ...,
        description="检查类型"
    )

    status: CheckStatus = Field(
        ...,
        description="检查状态"
    )

    details: str = Field(
        ...,
        description="检查详情说明"
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="支撑证据"
    )


class CriticalFinding(BaseModel):
    """
    关键发现对象

    记录系统运行中发现的关键问题（现象层），与归因层分离。
    """

    finding_id: str = Field(
        ...,
        description="关键发现唯一ID，用于引用与跟踪"
    )

    summary: str = Field(
        ...,
        description="关键发现摘要，一句话说清问题"
    )

    severity: SeverityLevel = Field(
        ...,
        description="严重级别"
    )

    layer: AttributionLayer = Field(
        ...,
        description="所属层级"
    )

    evidence: List[str] = Field(
        ...,
        min_items=1,
        description="支撑证据，至少一项"
    )

    impact: str = Field(
        ...,
        description="影响说明，为什么值得进入优先级"
    )


class SuspectedRootCause(BaseModel):
    """
    初步归因对象

    记录对问题的初步归因（解释层），明确表达"怀疑"而非"确定"。
    """

    cause_id: str = Field(
        ...,
        description="归因唯一ID"
    )

    suspected_root_cause: str = Field(
        ...,
        description="初步归因说明"
    )

    confidence: ConfidenceLevel = Field(
        ...,
        description="可信度等级"
    )

    reasoning: str = Field(
        ...,
        description="归因推理过程"
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="支撑证据"
    )

    limitations: List[str] = Field(
        default_factory=list,
        description="归因限制条件"
    )

    related_findings: List[str] = Field(
        default_factory=list,
        description="关联的 finding_id 列表"
    )


class Phase3PriorityItem(BaseModel):
    """
    阶段3优先级项

    从复盘对象中自然导出的优先级项，不是外贴结论。
    """

    priority_id: str = Field(
        ...,
        description="优先级项唯一ID"
    )

    title: str = Field(
        ...,
        description="优先级标题，一句话说明"
    )

    reason: str = Field(
        ...,
        description="收口原因，对应关键发现与归因"
    )

    scope: PriorityScope = Field(
        ...,
        description="作用范围"
    )

    suggested_order: int = Field(
        ...,
        description="建议顺序，用于阶段3排序"
    )

    expected_impact: Optional[str] = Field(
        default=None,
        description="预期影响说明"
    )

    related_findings: List[str] = Field(
        default_factory=list,
        description="关联的 finding_id 列表"
    )


# ============================================================================
# 输出契约：SystemRetrospectiveObject
# ============================================================================

class SystemRetrospectiveObject(BaseModel):
    """
    系统复盘对象

    这是 Phase 2.5 的核心主产物，结构化记录系统级复盘结果。
    复盘报告是本对象的派生视图，而不是主产物。
    """

    # 基础信息
    retrospective_id: str = Field(
        ...,
        description="复盘对象唯一ID"
    )

    case_id: str = Field(
        ...,
        description="对应案例ID，与输入对齐"
    )

    retrospective_version: str = Field(
        ...,
        description="复盘版本号，便于基线对照"
    )

    processing_time_ms: int = Field(
        ...,
        description="处理耗时（毫秒）"
    )

    # 核心内容
    workflow_summary: str = Field(
        ...,
        description="本次真实链路摘要，说明跑了什么、产出了什么"
    )

    output_checks: List[OutputCheck] = Field(
        ...,
        description="输出检查结果，至少覆盖完整性/一致性/可理解性"
    )

    critical_findings: List[CriticalFinding] = Field(
        ...,
        description="关键发现列表（现象层）"
    )

    suspected_root_causes: List[SuspectedRootCause] = Field(
        ...,
        description="初步归因结果（解释层）"
    )

    phase3_priorities: List[Phase3PriorityItem] = Field(
        ...,
        description="阶段3优先级收口"
    )

    # 辅助信息
    confidence_notes: List[str] = Field(
        ...,
        description="可信度与限制说明，允许为空数组但必须返回"
    )

    warnings: Optional[List[str]] = Field(
        default=None,
        description="风险或异常提示，如'证据不足''人工复核缺失'等"
    )


# ============================================================================
# 输出契约：SystemRetrospectiveResult
# ============================================================================

class SystemRetrospectiveResult(BaseModel):
    """
    系统复盘结果

    包装 SystemRetrospectiveObject 的最终返回对象。
    """

    request_id: str = Field(
        ...,
        description="请求ID，与输入对齐"
    )

    retrospective: SystemRetrospectiveObject = Field(
        ...,
        description="系统复盘对象（正式主产物）"
    )

    global_summary: Optional[str] = Field(
        default=None,
        description="当前整体复盘摘要（辅助阅读）"
    )

    analyzer_version: str = Field(
        ...,
        description="分析器版本号，用于基线与回放"
    )

    processing_time_ms: int = Field(
        ...,
        description="总耗时（毫秒）"
    )


# ============================================================================
# Schema 导出
# ============================================================================

__all__ = [
    # 枚举
    "SeverityLevel",
    "AttributionLayer",
    "CheckType",
    "CheckStatus",
    "ConfidenceLevel",
    "PriorityScope",
    "ValidationMode",
    # 输入契约
    "SystemRetrospectiveRequest",
    # 输出契约组件
    "OutputCheck",
    "CriticalFinding",
    "SuspectedRootCause",
    "Phase3PriorityItem",
    # 输出契约
    "SystemRetrospectiveObject",
    "SystemRetrospectiveResult",
]
