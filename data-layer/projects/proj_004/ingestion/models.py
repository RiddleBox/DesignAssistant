"""
数据模型：RawRecord（Provider 层内部）和 NormalizedRecord（对外契约）
"""
from dataclasses import dataclass, field


@dataclass
class RawRecord:
    """Provider 层原始数据，格式未经标准化。"""
    raw_title: str
    raw_content: str            # 摘要区内容（不含"我的判断"）
    raw_date: str               # 原始日期字符串，格式不保证
    raw_source: str             # frontmatter source 字段
    raw_url: str                # 原文链接
    raw_signal_type: str        # frontmatter signal_type
    raw_tags: list[str]
    origin_file: str            # 相对路径（用于去重和审计）
    editor_notes: str           # "我的判断"内容（若有），不进入 content
    language: str               # 推断：zh / en


@dataclass
class NormalizedRecord:
    """标准化后的记录，直接对应 incoming/*.json 输出契约。"""
    source_id: str
    source_type: str
    title: str
    content: str
    published_at: str           # ISO 8601
    source_name: str
    source_url: str
    language: str
    mode: str
    ingestion_meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "content": self.content,
            "published_at": self.published_at,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "language": self.language,
            "mode": self.mode,
            "ingestion_meta": self.ingestion_meta,
        }
