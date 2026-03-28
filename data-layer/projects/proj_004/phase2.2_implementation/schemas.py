"""
Phase 2.2 机会判断模块 - Schema 定义

定义 OpportunityObject、OpportunityJudgmentRequest、OpportunityJudgmentResult 的数据结构

变更记录：
- 2026-03-28 v2：OpportunityObject 新增 why_now / warnings 字段
- 2026-03-28 v2：OpportunityJudgmentResult 改为 opportunities: List[OpportunityObject]（多机会输出，已拍板）
- 2026-03-28 v2：Diagnostics 改为 per-opportunity，新增 opportunity_count
"""

import importlib.util
import os
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# 精确导入 2.1 的 DecodedIntelligence（不污染 sys.path）
def _import_decoded_intelligence():
    path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "phase2.1_implementation", "schemas.py")
    )
    try:
        spec = importlib.util.spec_from_file_location("phase21_schemas", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.DecodedIntelligence
    except Exception:
        return Dict[str, Any]  # fallback

DecodedIntelligence = _import_decoded_intelligence()


class OpportunityObject(BaseModel):
    """机会对象 - Phase 2.2 的核心输出对象

    字段拍板记录（2026-03-28）：
    - why_now / warnings 为可选字段（N），补入本次梳理后
    - judgment_summary 已拍板移除（与 opportunity_thesis 定位重叠）
    """

    # 基础标识
    opportunity_id: str = Field(..., description="机会对象唯一标识")
    opportunity_title: str = Field(..., description="机会标题（简短描述）")
    opportunity_thesis: str = Field(..., description="机会论点（核心判断，2-4句话说清楚为什么这些信号构成机会）")

    # 信号关联
    related_signals: List[Dict[str, Any]] = Field(..., description="关联的信号列表（来自2.1，含source_ref可追溯）")

    # 证据组织
    supporting_evidence: List[str] = Field(..., description="支持证据列表（引用具体信号或2.4外部知识）")
    counter_evidence: List[str] = Field(..., description="反对证据列表（必须与supporting_evidence并列存在）")
    key_assumptions: List[str] = Field(..., description="关键假设列表（判断成立的前提条件）")
    uncertainty_map: List[str] = Field(..., description="不确定性列表（主要不确定因素及影响程度）")

    # 判断结果
    priority_level: Literal["watch", "research", "deep_dive", "escalate"] = Field(
        ..., description="优先级分级：watch/research/deep_dive/escalate"
    )

    # 时机性判断（可选）
    why_now: Optional[str] = Field(
        None,
        description="当前时点为什么值得关注——时间窗口、催化剂、紧迫性说明（对应 first principle 第5问：为什么是现在）"
    )

    # 升级建议
    next_validation_questions: List[str] = Field(
        ...,
        description="供2.3行动设计使用的关键前置问题（go/no-go判断或行动姿态选择的前置条件）"
    )

    # 风险与异常提示（可选）
    warnings: Optional[List[str]] = Field(
        None,
        description="风险或异常提示，如「证据不足」「信号来源均为新闻（非官方公告）」「分级保守」等"
    )

    # 元数据
    judgment_version: str = Field(..., description="判断版本")
    processing_time_ms: int = Field(..., description="处理耗时（毫秒）")


class ContextPacket(BaseModel):
    """来自 Phase 2.4 的增强输入"""
    similar_cases: Optional[List[str]] = Field(None, description="相似案例")
    counter_examples: Optional[List[str]] = Field(None, description="反例")
    methodology_hints: Optional[List[str]] = Field(None, description="方法论提示")
    domain_constraints: Optional[List[str]] = Field(None, description="领域约束")


class JudgmentConfig(BaseModel):
    """判断配置（预留字段，当前不生效，P2 实现）"""
    min_confidence_threshold: Optional[float] = Field(0.3, description="最小置信度阈值（预留）")
    enable_counter_evidence_check: Optional[bool] = Field(True, description="启用反证检查（预留）")
    max_processing_time_ms: Optional[int] = Field(30000, description="最大处理时间（毫秒）（预留）")


class OpportunityJudgmentRequest(BaseModel):
    """机会判断请求 - Phase 2.2 的输入

    消费语义（已拍板 2026-03-28）：
    - 接收多条 DecodedIntelligence，由 2.2 自己决定哪些信号可以组合成一个或多个机会
    - 每条 DecodedIntelligence 带完整上下文（signals 含打分、source_type、source_id、source_ref）
    - 2.1 的打分（intensity/confidence/timeliness）是 2.2 判断信号权重的依据，必须完整传入
    - 2.4 的 context_packet 是可选增强输入，为机会判断提供历史案例和外部知识支撑
    """

    # 必填：来自 2.1 的输入（多条，支持跨文章信号组合判断）
    decoded_intelligences: List[Any] = Field(
        ...,
        description="来自2.1的解码情报列表（List[DecodedIntelligence]），"
                    "含完整信号打分和来源上下文，由2.2决定信号组合策略，可能产出多个机会对象"
    )

    # 可选：来自 2.4 的增强输入
    context_packet: Optional[ContextPacket] = Field(None, description="来自2.4的证据包")

    # 可选：判断配置
    judgment_config: Optional[JudgmentConfig] = Field(None, description="判断配置（当前不生效）")


class Diagnostics(BaseModel):
    """诊断信息（整体，非 per-opportunity）"""
    signal_count: int = Field(..., description="输入信号总数")
    opportunity_count: int = Field(..., description="识别出的机会对象数量")
    evidence_completeness: float = Field(..., description="平均证据完整度 (0-1)")
    boundary_warnings: List[str] = Field(default_factory=list, description="边界警告列表")


class ErrorInfo(BaseModel):
    """错误信息"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")


class OpportunityJudgmentResult(BaseModel):
    """机会判断结果 - Phase 2.2 的输出

    变更（2026-03-28 已拍板）：
    - opportunities: List[OpportunityObject]（原 opportunity: OpportunityObject）
    - 同一批信号可能识别出多个独立机会方向，符合真实世界多机会并发的实际
    - 空列表表示当前信号不足以构成任何机会（而非 error）
    """

    # 核心输出：多机会列表
    opportunities: List[OpportunityObject] = Field(
        ...,
        description="识别出的机会对象列表（可为空列表，表示当前信号不足以构成机会）"
    )

    # 判断状态
    status: Literal["success", "insufficient_evidence", "error"] = Field(
        ..., description="判断状态：success=正常输出；insufficient_evidence=信号不足；error=系统错误"
    )

    # 诊断信息
    diagnostics: Optional[Diagnostics] = Field(None, description="整体诊断信息")

    # 错误信息
    error: Optional[ErrorInfo] = Field(None, description="错误信息（status=error 时填充）")
