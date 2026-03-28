"""
RAG系统数据模型定义
Phase 2.4

包含两套协议：
  - 文档级协议（MVP原有）：Document / RetrieveRequest / RetrieveResponse / GenerateRequest / GenerateResponse
  - 证据包级协议（v1.0新增）：ContextPacket / ContextRequest / ContextResponse
    设计依据：PHASE2_4_CONTEXT_PACKET_PROTOCOL.md v1.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import uuid


@dataclass
class DocumentMetadata:
    """文档元数据"""
    source: str = ""           # 来源（如 "GDC 2021"）
    confidence: float = 0.0    # 置信度（0-1）
    last_updated: str = ""     # 最后更新时间（ISO 8601格式）

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "confidence": self.confidence,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentMetadata":
        # 只取已知字段，忽略多余 key（如 collector_version / origin_file 等）
        known = {k: data[k] for k in ("source", "confidence", "last_updated") if k in data}
        return cls(**known)


@dataclass
class Document:
    """
    知识库文档对象

    Attributes:
        id: 文档唯一ID（如 "kb_001"）
        title: 文档标题
        content: 文档内容（最多2000字符）
        category: 分类（game_design/market_trend/tech_innovation）
        tags: 标签列表
        metadata: 元数据
        score: 相似度分数（检索时返回）
    """
    id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    score: float = 0.0  # 检索时返回
    content_type: Optional[str] = None  # 内容性质标注（见 CONTENT_TYPE_VALUES）；None 表示未标注

    def to_dict(self, include_score: bool = False) -> dict:
        """转换为字典（用于API响应）"""
        result = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "metadata": self.metadata.to_dict()
        }
        if include_score:
            result["score"] = self.score
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """从字典创建对象"""
        metadata = DocumentMetadata.from_dict(data.get("metadata", {}))
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            category=data["category"],
            tags=data.get("tags", []),
            metadata=metadata,
            score=data.get("score", 0.0)
        )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Document":
        """从YAML文件加载"""
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class RetrieveRequest:
    """检索请求"""
    query: str
    top_k: int = 5

    def validate(self) -> tuple[bool, Optional[str]]:
        """验证请求"""
        if not self.query or len(self.query.strip()) == 0:
            return False, "查询文本不能为空"
        if len(self.query) > 1000:
            return False, "查询文本过长（最大1000字符）"
        if self.top_k < 1 or self.top_k > 20:
            return False, "top_k必须在1-20之间"
        return True, None


@dataclass
class RetrieveResponse:
    """检索响应"""
    documents: List[Document]
    total: int
    query_time_ms: int

    def to_dict(self) -> dict:
        return {
            "documents": [doc.to_dict(include_score=True) for doc in self.documents],
            "total": self.total,
            "query_time_ms": self.query_time_ms
        }


@dataclass
class GenerateRequest:
    """生成请求"""
    query: str
    context_ids: List[str]
    temperature: float = 0.7

    def validate(self) -> tuple[bool, Optional[str]]:
        """验证请求"""
        if not self.query or len(self.query.strip()) == 0:
            return False, "查询文本不能为空"
        if len(self.query) > 1000:
            return False, "查询文本过长（最大1000字符）"
        if not self.context_ids or len(self.context_ids) == 0:
            return False, "上下文文档ID不能为空"
        if len(self.context_ids) > 10:
            return False, "上下文文档过多（最大10个）"
        if self.temperature < 0 or self.temperature > 1:
            return False, "temperature必须在0-1之间"
        return True, None


@dataclass
class GenerateResponse:
    """生成响应"""
    answer: str
    sources: List[Document]
    confidence: float
    generation_time_ms: int

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": [doc.to_dict(include_score=True) for doc in self.sources],
            "confidence": self.confidence,
            "generation_time_ms": self.generation_time_ms
        }


# ─────────────────────────────────────────────────────────────────────────────
# 证据包级协议 v1.0
# 设计依据：PHASE2_4_CONTEXT_PACKET_PROTOCOL.md
# 新增 /api/v1/context 接口使用，原文档级接口不受影响
# ─────────────────────────────────────────────────────────────────────────────

# content_type 合法枚举值
CONTENT_TYPE_VALUES = {
    "glossary",         # 术语定义：行业术语、机制名词的精确定义
    "few_shot_example", # 高质量样例：抽取/判断/设计的示范案例，含输入输出对
    "constraint_rule",  # 判定规则/边界约束：字段分类规则、边界条件、硬约束
    "case_record",      # 真实行业事件：有主体+动作+结果的具体事件记录
    "market_data",      # 数据/行业基准：市场规模、增长率、成本数据等可引用数字
    "background",       # 背景知识：补充理解所需的上下文，非核心判断依据
}

# trust_level 合法枚举值
TRUST_LEVEL_VALUES = {"high", "medium", "low"}

# caller 合法枚举值
CALLER_VALUES = {"phase2.1", "phase2.2", "phase2.3"}


@dataclass
class ContextPacket:
    """
    证据包 —— 2.4 向下游交付的最小上下文单元

    设计原则：
    - content_type 描述内容性质（是什么），不预判用途（怎么用）
    - excerpt 是命中片段，不是全文
    - reason_for_match 必须说明与当前 query 的关联，不能为空
    - trust_level 和 score 是两个独立维度（前者描述可信度，后者是检索相似度）
    """
    packet_id: str                          # 唯一ID，用于日志追踪
    source_id: str                          # 来源文档ID（kb_xxx）
    source_title: str                       # 来源文档标题（人工可读）
    content_type: str                       # 内容性质枚举（见 CONTENT_TYPE_VALUES）
    excerpt: str                            # 命中片段（≤500字符）
    reason_for_match: str                   # 命中原因（说明与 query 的关联）
    trust_level: str                        # 信任等级：high/medium/low
    score: float                            # 向量检索相似度分数（非可信度）
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    tags: List[str] = field(default_factory=list)   # 主题标签（透传自原文档）
    category: Optional[str] = None         # 所属主题分类（透传自原文档）

    def to_dict(self) -> dict:
        return {
            "packet_id": self.packet_id,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "content_type": self.content_type,
            "excerpt": self.excerpt,
            "reason_for_match": self.reason_for_match,
            "trust_level": self.trust_level,
            "score": self.score,
            "metadata": self.metadata.to_dict(),
            "tags": self.tags,
            "category": self.category,
        }

    @classmethod
    def new_id(cls) -> str:
        """生成唯一 packet_id"""
        return f"ctx_{uuid.uuid4().hex[:8]}"


@dataclass
class ContextRequest:
    """
    证据包请求 —— 调用方向 2.4 发起的上下文请求

    调用方典型配置：
    - 2.1（信号抽取）：needed_content_types=["glossary","few_shot_example","constraint_rule"]
    - 2.2（机会判断）：needed_content_types=["case_record","market_data","few_shot_example"]
    - 2.3（外部观察者）：needed_content_types=["case_record","market_data"]
    """
    request_id: str                         # 请求唯一ID，用于链路追踪
    caller: str                             # 调用方：phase2.1 / phase2.2 / phase2.3
    query: str                              # 核心查询文本
    needed_content_types: List[str] = field(default_factory=list)   # 期望内容类型（空=不限）
    top_k: int = 5                          # 期望返回包数量上限（最大10）
    category_filter: List[str] = field(default_factory=list)        # 主题分类过滤（空=不限）
    min_trust_level: str = "low"            # 最低信任等级（low=不过滤）

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.query or len(self.query.strip()) == 0:
            return False, "query 不能为空"
        if len(self.query) > 2000:
            return False, "query 过长（最大2000字符）"
        if self.caller not in CALLER_VALUES:
            return False, f"caller 非法，必须是 {CALLER_VALUES} 之一"
        if self.top_k < 1 or self.top_k > 10:
            return False, "top_k 必须在 1-10 之间"
        for ct in self.needed_content_types:
            if ct not in CONTENT_TYPE_VALUES:
                return False, f"content_type '{ct}' 非法，合法值：{CONTENT_TYPE_VALUES}"
        if self.min_trust_level not in TRUST_LEVEL_VALUES:
            return False, f"min_trust_level 非法，必须是 {TRUST_LEVEL_VALUES} 之一"
        return True, None


@dataclass
class ContextResponse:
    """
    证据包响应 —— 2.4 返回给调用方的结果

    context_packets 可为空数组，下游必须能在无上下文时正常降级运行。
    """
    request_id: str                         # 回传请求ID
    context_packets: List[ContextPacket]    # 证据包列表（可为空）
    retrieval_time_ms: int                  # 检索耗时（毫秒）
    protocol_version: str = "v1.0"         # 协议版本
    retrieval_summary: Optional[str] = None        # 检索摘要（调试用）
    retrieval_notes: List[str] = field(default_factory=list)  # 检索备注

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "context_packets": [p.to_dict() for p in self.context_packets],
            "retrieval_time_ms": self.retrieval_time_ms,
            "protocol_version": self.protocol_version,
            "retrieval_summary": self.retrieval_summary,
            "retrieval_notes": self.retrieval_notes,
        }
