"""
RAG系统数据模型定义
MVP版本 - Phase 2.4
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


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
        return cls(**data)


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
    score: float = 0.0  # 检索时填充

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
