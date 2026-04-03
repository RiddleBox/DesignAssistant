"""
KnowledgeBaseAdapter
读取 game-knowledge-base/00-Inbox/{date}/*.md，解析为 RawRecord。
"""
import re
import logging
from datetime import date, timedelta
from pathlib import Path

import yaml

from ingestion.models import RawRecord
from ingestion.providers.base import ProviderAdapter

logger = logging.getLogger(__name__)

# 中文字符范围
_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')

# 原文链接正则：[原文链接](url) 或 [原文](url)
_URL_RE = re.compile(r'\[(?:原文链接|原文|Source|source)\]\((https?://[^\)]+)\)')

# 摘要区：## 摘要 后到下一个 ## 之前
_SUMMARY_RE = re.compile(
    r'##\s*摘要\s*\n(.*?)(?=\n##|\Z)',
    re.DOTALL
)

# 我的判断区：## 我的判断 后到下一个 ## 或文末
_NOTES_RE = re.compile(
    r'##\s*我的判断\s*\n(.*?)(?=\n##|\Z)',
    re.DOTALL
)

# 标题：# 开头第一行
_TITLE_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """分离 YAML frontmatter 和正文。"""
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].strip()
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _infer_language(text: str) -> str:
    if not text:
        return 'en'
    cjk_count = len(_CJK_RE.findall(text))
    ratio = cjk_count / max(len(text), 1)
    return 'zh' if ratio > 0.05 else 'en'


def _extract_url(body: str) -> str:
    m = _URL_RE.search(body)
    return m.group(1).strip() if m else ''


def _extract_title(body: str) -> str:
    m = _TITLE_RE.search(body)
    return m.group(1).strip() if m else ''


def _extract_summary(body: str) -> str:
    m = _SUMMARY_RE.search(body)
    if not m:
        return ''
    raw = m.group(1).strip()
    # 去掉 Markdown 格式符（粗体、斜体、链接文字、标题等）
    raw = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
    raw = re.sub(r'\*(.+?)\*', r'\1', raw)
    raw = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', raw)
    raw = re.sub(r'`(.+?)`', r'\1', raw)
    return raw.strip()


def _extract_editor_notes(body: str) -> str:
    m = _NOTES_RE.search(body)
    if not m:
        return ''
    notes = m.group(1).strip()
    # 过滤掉空模板（只有 > （移到...））
    if notes.startswith('> （移到') or notes == '> （移到 05-Insights 前在这里写下你的想法，并添加 signal_type frontmatter）':
        return ''
    return notes.strip()


def _parse_md_file(filepath: Path, inbox_root: Path) -> RawRecord | None:
    """解析单个 .md 文件，返回 RawRecord，失败返回 None。"""
    try:
        text = filepath.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning(f"读取文件失败: {filepath} — {e}")
        return None

    fm, body = _parse_frontmatter(text)

    title = _extract_title(body) or filepath.stem
    content = _extract_summary(body)
    url = _extract_url(body)
    editor_notes = _extract_editor_notes(body)
    language = _infer_language(title + content)

    raw_date = str(fm.get('date', '')) or ''
    raw_source = str(fm.get('source', '')) or ''
    raw_signal_type = str(fm.get('signal_type', '')) or 'unknown'
    raw_tags = fm.get('tags', []) or []

    try:
        origin_file = str(filepath.relative_to(inbox_root.parent))
    except ValueError:
        origin_file = str(filepath)

    return RawRecord(
        raw_title=title,
        raw_content=content,
        raw_date=raw_date,
        raw_source=raw_source,
        raw_url=url,
        raw_signal_type=raw_signal_type,
        raw_tags=raw_tags,
        origin_file=origin_file,
        editor_notes=editor_notes,
        language=language,
    )


class KnowledgeBaseAdapter(ProviderAdapter):
    """
    读取 game-knowledge-base/00-Inbox/{date}/*.md。
    支持单日和日期范围两种模式。
    """

    def __init__(self, inbox_root: str | Path):
        self._inbox_root = Path(inbox_root)

    @property
    def provider_id(self) -> str:
        return 'knowledge_base_inbox'

    def fetch(
        self,
        date: str | None = None,
        date_range: tuple[str, str] | None = None,
        limit: int | None = None,
    ) -> list[RawRecord]:
        """
        date: 'YYYY-MM-DD'，处理单日
        date_range: ('YYYY-MM-DD', 'YYYY-MM-DD')，处理区间（含首尾）
        limit: 最多返回条数（用于测试）
        默认：处理昨天
        """
        target_dirs = self._resolve_dirs(date, date_range)
        records: list[RawRecord] = []

        for d in target_dirs:
            dir_path = self._inbox_root / d
            if not dir_path.exists():
                logger.warning(f"Inbox 目录不存在: {dir_path}")
                continue
            md_files = sorted(dir_path.glob('*.md'))
            logger.info(f"[{d}] 发现 {len(md_files)} 个文件")
            for f in md_files:
                rec = _parse_md_file(f, self._inbox_root)
                if rec is not None:
                    records.append(rec)
                if limit and len(records) >= limit:
                    return records

        return records

    def _resolve_dirs(
        self,
        date_str: str | None,
        date_range: tuple[str, str] | None,
    ) -> list[str]:
        if date_str:
            return [date_str]
        if date_range:
            from datetime import datetime
            start = datetime.strptime(date_range[0], '%Y-%m-%d').date()
            end = datetime.strptime(date_range[1], '%Y-%m-%d').date()
            result = []
            cur = start
            while cur <= end:
                result.append(str(cur))
                cur += timedelta(days=1)
            return result
        # 默认：昨天
        yesterday = date.today() - timedelta(days=1)
        return [str(yesterday)]
