"""
Phase 2.2 机会判断模块 - Schema 定义

定义 OpportunityObject、OpportunityJudgmentRequest、OpportunityJudgmentResult 的数据结构
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
    """机会对象 - Phase 2.2 的核心输出对象"""

    # 基础标识
    opportunity_id: str = Field(..., description="机会对象唯一标识")
    opportunity_title: str = Field(..., description="机会标题（简短描述）")
    opportunity_thesis: str = Field(..., description="机会论点（核心判断）")

    # 信号关联
    related_signals: List[Dict[str, Any]] = Field(..., description="关联的信号列表（来自2.1）")

    # 证据组织
    supporting_evidence: List[str] = Field(..., description="支持证据列表")
    counter_evidence: List[str] = Field(..., description="反对证据列表")
    key_assumptions: List[str] = Field(..., description="关键假设列表")
    uncertainty_map: List[str] = Field(..., description="不确定性列表")

    # 判断结果
    priority_level: Literal["watch", "research", "deep_dive", "escalate"] = Field(
        ..., description="优先级分级"
    )

    # 升级建议
    next_validation_questions: List[str] = Field(..., description="下一步验证问题")

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
    """判断配置"""
    min_confidence_threshold: Optional[float] = Field(0.3, description="最小置信度阈值")
    enable_counter_evidence_check: Optional[bool] = Field(True, description="启用反证检查")
    max_processing_time_ms: Optional[int] = Field(30000, description="最大处理时间（毫秒）")


class OpportunityJudgmentRequest(BaseModel):
    """机会判断请求 - Phase 2.2 的输入

    消费语义（已拍板 2026-03-28）：
    - 接收多条 DecodedIntelligence，由 2.2 自己决定哪些信号可以组合成一个机会
    - 每条 DecodedIntelligence 带完整上下文（signals 含打分、source_type、source_id）
    - 2.1 的打分（intensity/confidence/timeliness）是 2.2 判断信号权重的依据，必须完整传入
    - 2.4 的 context_packet 是可选增强输入，为机会判断提供历史案例和外部知识支撑
    """

    # 必填：来自 2.1 的输入（多条，支持跨文章信号组合判断）
    decoded_intelligences: List[Any] = Field(
        ...,
        description="来自2.1的解码情报列表（List[DecodedIntelligence]），"
                    "含完整信号打分和来源上下文，由2.2决定信号组合策略"
    )

    # 可选：来自 2.4 的增强输入
    context_packet: Optional[ContextPacket] = Field(None, description="来自2.4的证据包")

    # 可选：判断配置
    judgment_config: Optional[JudgmentConfig] = Field(None, description="判断配置")


class Diagnostics(BaseModel):
    """诊断信息"""
    signal_count: int = Field(..., description="信号数量")
    evidence_completeness: float = Field(..., description="证据完整度 (0-1)")
    boundary_warnings: List[str] = Field(default_factory=list, description="边界警告")


class ErrorInfo(BaseModel):
    """错误信息"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")


class OpportunityJudgmentResult(BaseModel):
    """机会判断结果 - Phase 2.2 的输出"""

    # 核心输出
    opportunity: OpportunityObject = Field(..., description="机会对象")

    # 判断状态
    status: Literal["success", "insufficient_evidence", "error"] = Field(
        ..., description="判断状态"
    )

    # 诊断信息
    diagnostics: Optional[Diagnostics] = Field(None, description="诊断信息")

    # 错误信息
    error: Optional[ErrorInfo] = Field(None, description="错误信息")
