"""
Normalizer：RawRecord → NormalizedRecord
负责字段映射、日期解析、source_id 生成、去重判定。
"""
import re
import hashlib
import logging
import json
from datetime import datetime, timezone
from pathlib import Path

from ingestion.models import RawRecord, NormalizedRecord

logger = logging.getLogger(__name__)

# signal_type → source_type 映射（统一为 news，语义为"数据类型"而非领域）
_SOURCE_TYPE_MAP = {
    'capital': 'news',
    'market': 'news',
    'technical': 'news',
    'regulatory': 'news',
    'team': 'news',
    'tech': 'news',
}

# 日期解析格式列表
_DATE_FMTS = [
    '%Y-%m-%d',
    '%Y/%m/%d',
    '%Y.%m.%d',
    '%B %d, %Y',
    '%b %d, %Y',
]

_DATE_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2})')


def _parse_date(raw_date: str, origin_file: str) -> tuple[str, bool]:
    """
    解析日期，返回 (ISO 8601 字符串, is_inferred)。
    is_inferred=True 表示从文件路径或当前时间兜底。
    """
    # 1. 直接解析 raw_date
    if raw_date:
        for fmt in _DATE_FMTS:
            try:
                d = datetime.strptime(raw_date.strip(), fmt)
                return d.strftime('%Y-%m-%dT00:00:00Z'), False
            except ValueError:
                continue
        # 从 raw_date 中提取 YYYY-MM-DD 片段
        m = _DATE_PATTERN.search(raw_date)
        if m:
            try:
                d = datetime.strptime(m.group(1), '%Y-%m-%d')
                return d.strftime('%Y-%m-%dT00:00:00Z'), False
            except ValueError:
                pass

    # 2. 从 origin_file 路径提取日期
    m = _DATE_PATTERN.search(origin_file)
    if m:
        try:
            d = datetime.strptime(m.group(1), '%Y-%m-%d')
            logger.debug(f"日期从路径推断: {origin_file} → {d.date()}")
            return d.strftime('%Y-%m-%dT00:00:00Z'), True
        except ValueError:
            pass

    # 3. 兜底：当前时间
    now = datetime.now(timezone.utc)
    logger.warning(f"无法解析日期，使用当前时间兜底: {origin_file}")
    return now.strftime('%Y-%m-%dT%H:%M:%SZ'), True


def _normalize_title(title: str) -> str:
    """用于去重的标题规范化：小写、去标点、压缩空白。"""
    t = title.lower()
    t = re.sub(r'[^\w\s\u4e00-\u9fff]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _content_hash(content: str) -> str:
    return hashlib.md5(content[:200].encode('utf-8')).hexdigest()


def _url_key(url: str) -> str:
    # 去掉 fragment 和 trailing slash，作为去重主键
    url = url.split('#')[0].rstrip('/')
    return url.lower()


class DedupIndex:
    """
    持久化去重索引。
    键：url_key / title_date_source_hash / content_hash
    值：已导出的 source_id
    """

    def __init__(self, index_path: Path):
        self._path = index_path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def check(self, url: str, title: str, date_str: str, source_name: str, content: str) -> str | None:
        """
        返回已存在的 source_id（需去重），或 None（可以导入）。
        多源报道判定：url 不同 = 不同来源，即使标题相似也不去重。
        """
        # 一级：source_url
        if url:
            key1 = f"url:{_url_key(url)}"
            if key1 in self._data:
                return self._data[key1]

        # 二级：title + date + source_name
        t_norm = _normalize_title(title)
        date_short = date_str[:10] if date_str else ''
        key2 = f"tds:{hashlib.md5(f'{t_norm}|{date_short}|{source_name.lower()}'.encode()).hexdigest()}"
        if key2 in self._data:
            return self._data[key2]

        # 三级：正文前 200 字 hash
        if content:
            key3 = f"ch:{_content_hash(content)}"
            if key3 in self._data:
                return self._data[key3]

        return None

    def register(self, source_id: str, url: str, title: str, date_str: str, source_name: str, content: str):
        """注册新记录到索引。"""
        if url:
            self._data[f"url:{_url_key(url)}"] = source_id
        t_norm = _normalize_title(title)
        date_short = date_str[:10] if date_str else ''
        key2 = f"tds:{hashlib.md5(f'{t_norm}|{date_short}|{source_name.lower()}'.encode()).hexdigest()}"
        self._data[key2] = source_id
        if content:
            self._data[f"ch:{_content_hash(content)}"] = source_id


class Normalizer:
    """
    将 RawRecord 列表转换为 NormalizedRecord 列表。
    同时维护去重状态，返回 (normalized, skipped, quarantined)。
    """

    def __init__(self, dedup_index: DedupIndex, config: dict):
        self._dedup = dedup_index
        self._default_mode = config.get('ingestion', {}).get('default_mode', 'prompt_first')
        self._default_source_type = config.get('ingestion', {}).get('default_source_type', 'news')
        self._content_max = config.get('ingestion', {}).get('content_max_chars', 2000)
        self._seq_counter: dict[str, int] = {}  # date → counter

    def normalize(
        self,
        records: list[RawRecord],
        force_reimport: bool = False,
    ) -> tuple[list[NormalizedRecord], list[dict], list[dict]]:
        """
        返回：
          normalized   — 可以导出的记录
          skipped      — 去重跳过的记录（含原因）
          quarantined  — 解析失败的记录（含原因）
        """
        normalized: list[NormalizedRecord] = []
        skipped: list[dict] = []
        quarantined: list[dict] = []

        for raw in records:
            result = self._process_one(raw, force_reimport)
            if result['status'] == 'ok':
                normalized.append(result['record'])
            elif result['status'] == 'skipped':
                skipped.append(result)
            else:
                quarantined.append(result)

        return normalized, skipped, quarantined

    def _process_one(self, raw: RawRecord, force_reimport: bool) -> dict:
        # ── 必填字段校验 ──
        if not raw.raw_title or not raw.raw_title.strip():
            return self._quarantine(raw, 'missing_title')
        if not raw.raw_content or not raw.raw_content.strip():
            return self._quarantine(raw, 'missing_content')

        title = raw.raw_title.strip()
        content = raw.raw_content.strip()[:self._content_max]
        source_name = raw.raw_source.strip() or 'unknown'
        url = raw.raw_url.strip()

        published_at, inferred = _parse_date(raw.raw_date, raw.origin_file)

        # ── 去重检查 ──
        if not force_reimport:
            existing_id = self._dedup.check(url, title, published_at, source_name, content)
            if existing_id:
                return {
                    'status': 'skipped',
                    'reason': 'dedup_match',
                    'existing_source_id': existing_id,
                    'origin_file': raw.origin_file,
                    'raw_title': title,
                }

        # ── 生成 source_id ──
        date_key = published_at[:10].replace('-', '')
        self._seq_counter[date_key] = self._seq_counter.get(date_key, 0) + 1
        source_id = f"incoming_{date_key}_{self._seq_counter[date_key]:03d}"

        # ── source_type 映射 ──
        source_type = _SOURCE_TYPE_MAP.get(
            raw.raw_signal_type.lower(),
            self._default_source_type
        )

        # ── 构建 ingestion_meta ──
        ingestion_meta: dict = {
            'provider': raw.origin_file.split('/')[0] if '/' in raw.origin_file else 'knowledge_base_inbox',
            'origin_file': raw.origin_file,
            'signal_type_hint': raw.raw_signal_type,
            'raw_tags': raw.raw_tags,
        }
        if raw.editor_notes:
            ingestion_meta['editor_notes'] = raw.editor_notes
        if inferred:
            ingestion_meta['date_inferred'] = True

        # ── 注册去重索引 ──
        self._dedup.register(source_id, url, title, published_at, source_name, content)

        record = NormalizedRecord(
            source_id=source_id,
            source_type=source_type,
            title=title,
            content=content,
            published_at=published_at,
            source_name=source_name,
            source_url=url,
            language=raw.language,
            mode=self._default_mode,
            ingestion_meta=ingestion_meta,
        )
        return {'status': 'ok', 'record': record}

    @staticmethod
    def _quarantine(raw: RawRecord, reason: str) -> dict:
        return {
            'status': 'quarantined',
            'reason': reason,
            'origin_file': raw.origin_file,
            'raw_title': raw.raw_title or '',
        }
