"""
Phase 2.1 情报解码模块 - 数据结构定义
基于 phase2.1_设计方案.md 的 Schema 定义
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """信号类型枚举"""
    TECHNICAL = "technical"  # 技术信号
    MARKET = "market"        # 市场信号
    TEAM = "team"            # 团队信号
    CAPITAL = "capital"      # 资本信号


class SourceType(str, Enum):
    """信息源类型枚举"""
    NEWS = "news"                    # 新闻
    REPORT = "report"                # 报告
    ANNOUNCEMENT = "announcement"    # 公告


class Signal(BaseModel):
    """信号结构 - 最小字段（MVP 版本）"""
    signal_id: str = Field(..., description="信号唯一ID，如 sig_001")
    signal_type: SignalType = Field(..., description="信号分类")
    signal_label: str = Field(..., description="信号标签，如'UE5 升级'")
    description: str = Field(..., description="信号描述")
    evidence_text: str = Field(..., description="证据原文片段")
    entities: List[str] = Field(default_factory=list, description="关联实体，可为空数组")
    intensity_score: int = Field(..., ge=1, le=10, description="强度评分 1-10")
    confidence_score: int = Field(..., ge=1, le=10, description="可信度评分 1-10")
    timeliness_score: int = Field(..., ge=1, le=10, description="时效性评分 1-10")
    source_ref: str = Field(..., description="对应原始来源 ID")
    extracted_at: str = Field(..., description="抽取时间 ISO8601")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="扩展信息")


class DecodedIntelligence(BaseModel):
    """解码后的情报 - 最小字段"""
    source_id: str = Field(..., description="原始输入 ID")
    source_type: SourceType = Field(..., description="输入来源类型")
    signals: List[Signal] = Field(default_factory=list, description="抽取后的信号列表，可为空数组")
    summary: Optional[str] = Field(default=None, description="人类可读摘要")
    decoder_version: str = Field(..., description="解码版本号，如 v1.0")
    processing_time_ms: int = Field(..., description="处理耗时（毫秒）")
    warnings: Optional[List[str]] = Field(default=None, description="风险或异常提示")


class IntelligenceDecodeRequest(BaseModel):
    """解码请求"""
    source_id: str = Field(..., description="原始信息唯一ID")
    source_type: SourceType = Field(..., description="信息源类型")
    title: Optional[str] = Field(default=None, description="原始标题")
    content: str = Field(..., description="原始正文")
    published_at: Optional[str] = Field(default=None, description="发布时间 ISO 风格")
    source_name: Optional[str] = Field(default=None, description="来源名称")
    language: str = Field(default="zh-CN", description="语言标记")
    retrieval_context: Optional[List[Dict[str, Any]]] = Field(default=None, description="来自 2.4 的补充上下文")
    mode: str = Field(default="prompt_first", description="解码模式")


# 评分口径定义（明文规则表）
SCORING_CRITERIA = {
    "intensity_score": {
        "1-3": "弱信号，影响有限",
        "4-7": "中等信号，有一定影响",
        "8-10": "强信号，重大影响"
    },
    "confidence_score": {
        "1-3": "传闻、未证实",
        "4-7": "可信来源、间接证据",
        "8-10": "官方确认、直接证据"
    },
    "timeliness_score": {
        "1-3": "过时信息（>6 个月）",
        "4-7": "近期信息（1-6 个月）",
        "8-10": "最新信息（<1 个月）"
    }
}