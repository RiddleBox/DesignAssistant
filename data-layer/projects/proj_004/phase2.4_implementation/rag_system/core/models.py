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
        industry: 行业标识（见 INDUSTRY_VALUES），用于跨行业扩展后的隔离过滤；当前默认 "gaming"
        category: 主题域（见 CATEGORY_VALUES），行业内的粗粒度分类
        tags: 细粒度主题标签（实体/产品名/地区/技术名词等，不含 content_type/category/industry 值）
        metadata: 元数据
        score: 相似度分数（检索时返回）
        content_type: 内容性质标注（见 CONTENT_TYPE_VALUES）；None 表示未标注
    """
    id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    score: float = 0.0  # 检索时返回
    content_type: Optional[str] = None  # 内容性质标注（见 CONTENT_TYPE_VALUES）；None 表示未标注
    industry: str = "gaming"            # 行业标识（见 INDUSTRY_VALUES）；默认 gaming

    def to_dict(self, include_score: bool = False) -> dict:
        """转换为字典（用于API响应）"""
        result = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "industry": self.industry,
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
            industry=data.get("industry", "gaming"),
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

# industry 合法枚举值（行业标识，用于跨行业扩展后的隔离过滤）
INDUSTRY_VALUES = {
    "gaming",       # 游戏行业（当前唯一行业）
    # 未来扩展示例："film", "ecommerce", "music" 等
}

# category 合法枚举值及边界定义（gaming 行业内的主题域）
CATEGORY_VALUES = {
    "game_design",      # 游戏设计：玩法机制、经济系统、关卡/叙事设计、用户体验等
    "market_trend",     # 市场与行业动态：市场数据、行业趋势、公司/产品层面的具体事件（含并购/发布/关服等）
    "tech_innovation",  # 技术创新：引擎技术、AI工具、云游戏、渲染/物理等技术能力
}


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
class MetadataFilter:
    """
    元数据过滤器 —— 在向量检索前对候选文档集做元数据层面的范围限定。

    各字段独立生效，空列表 = 不限该维度。
    设计原则：过滤的是"候选集范围"，不改变 query 语义，也不替代 content_type 分桶。

    字段说明：
        industry:        按行业隔离（见 INDUSTRY_VALUES）；扩展多行业后使用，当前默认不限
        category:        按主题域过滤（见 CATEGORY_VALUES）；行业内进一步缩小范围
        min_trust_level: 按最低信任等级过滤；"low"=不过滤（默认）

    典型用法：
        - 只用游戏行业文档：industry=["gaming"]
        - 只看市场相关主题：category=["market_trend"]
        - 只要高可信文档：  min_trust_level="high"
        - 不过滤（默认）：  MetadataFilter()（所有字段空/默认）
    """
    industry: List[str] = field(default_factory=list)       # 空=不限行业
    category: List[str] = field(default_factory=list)       # 空=不限主题域
    min_trust_level: str = "low"                            # low=不过滤


@dataclass
class ContextRequest:
    """
    证据包请求 —— 调用方向 2.4 发起的上下文请求

    调用方典型配置：
    - 2.1（信号抽取）：needed_content_types=["glossary","few_shot_example","constraint_rule"]
    - 2.2（机会判断）：needed_content_types=["case_record","market_data","few_shot_example"]
    - 2.3（外部观察者）：needed_content_types=["case_record","market_data"]

    metadata_filter 说明：
    - 当前单行业阶段，industry 通常不设（默认不限）
    - 多行业扩展后，可用 metadata_filter.industry=["gaming"] 隔离行业噪音
    - category 过滤适合在同一行业内进一步缩小主题范围时使用
    """
    request_id: str                         # 请求唯一ID，用于链路追踪
    caller: str                             # 调用方：phase2.1 / phase2.2 / phase2.3
    query: str                              # 核心查询文本
    needed_content_types: List[str] = field(default_factory=list)   # 期望内容类型（空=不限）
    top_k: int = 5                          # 期望返回包数量上限（最大10）
    metadata_filter: MetadataFilter = field(default_factory=MetadataFilter)  # 元数据过滤器

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
        if self.metadata_filter.min_trust_level not in TRUST_LEVEL_VALUES:
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
