"""
Exporter：NormalizedRecord → incoming/*.json + manifest + quarantine
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ingestion.models import NormalizedRecord

logger = logging.getLogger(__name__)

# 输出契约：必须包含的核心字段
_REQUIRED_FIELDS = {
    'source_id', 'source_type', 'title', 'content',
    'published_at', 'source_name', 'language', 'mode'
}


def _validate_schema(record: NormalizedRecord) -> list[str]:
    """返回 schema 违规列表，空列表表示通过。"""
    errors = []
    d = record.to_dict()
    for f in _REQUIRED_FIELDS:
        if not d.get(f):
            errors.append(f"missing_or_empty: {f}")
    # published_at 格式检查
    pa = d.get('published_at', '')
    try:
        datetime.strptime(pa, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        errors.append(f"invalid_published_at: {pa!r}")
    # source_id 格式
    sid = d.get('source_id', '')
    if not sid.startswith('incoming_'):
        errors.append(f"invalid_source_id_prefix: {sid!r}")
    return errors


class Exporter:
    """
    将 NormalizedRecord 列表写入 incoming/ 目录，
    并输出 manifest 审计记录和 quarantine 失败隔离文件。
    """

    def __init__(
        self,
        incoming_dir: str | Path,
        manifest_dir: str | Path,
        quarantine_dir: str | Path,
    ):
        self._incoming = Path(incoming_dir)
        self._manifest_runs = Path(manifest_dir) / 'runs'
        self._quarantine = Path(quarantine_dir)

        self._incoming.mkdir(parents=True, exist_ok=True)
        self._manifest_runs.mkdir(parents=True, exist_ok=True)
        self._quarantine.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        normalized: list[NormalizedRecord],
        skipped: list[dict],
        quarantined: list[dict],
        provider: str,
        date_processed: str,
        mode: str = 'export',
        scanned: int = 0,
        parseable: int = 0,
    ) -> dict:
        """
        mode:
          'dry-run'      — 只打印，不落盘
          'validate'     — schema 校验，不落盘
          'export'       — 正式写入
        返回 run summary dict。
        """
        run_id = f"{provider}-{date_processed.replace('-','')}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Schema 校验（validate / export 都做）
        schema_errors: list[dict] = []
        valid_records: list[NormalizedRecord] = []
        if mode in ('validate', 'export'):
            for rec in normalized:
                errs = _validate_schema(rec)
                if errs:
                    schema_errors.append({
                        'source_id': rec.source_id,
                        'origin_file': rec.ingestion_meta.get('origin_file', ''),
                        'errors': errs,
                    })
                else:
                    valid_records.append(rec)
        else:
            valid_records = normalized

        exported_files: list[str] = []

        if mode == 'export':
            for rec in valid_records:
                filename = f"{rec.source_id}.json"
                dest = self._incoming / filename
                dest.write_text(
                    json.dumps(rec.to_dict(), ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                exported_files.append(filename)
                logger.debug(f"写入: {dest}")

        # 写 quarantine（export 模式下）
        quarantine_file = ''
        all_quarantined = quarantined + [
            {'status': 'quarantined', 'reason': f"schema_error: {e['errors']}", **e}
            for e in schema_errors
        ]
        if mode == 'export' and all_quarantined:
            quarantine_file = f"{run_id}_rejects.jsonl"
            qpath = self._quarantine / quarantine_file
            lines = [json.dumps(q, ensure_ascii=False) for q in all_quarantined]
            qpath.write_text('\n'.join(lines), encoding='utf-8')
            logger.info(f"隔离文件: {qpath} ({len(all_quarantined)} 条)")

        # 构建 summary
        summary = {
            'run_id': run_id,
            'provider': provider,
            'mode': mode,
            'date_processed': date_processed,
            'stats': {
                'scanned': scanned,
                'parseable': parseable,
                'dedup_skipped': len(skipped),
                'quarantined': len(all_quarantined),
                'schema_errors': len(schema_errors),
                'exported': len(exported_files),
            },
            'exported_files': exported_files,
            'quarantine_file': quarantine_file,
            'timestamp': ts,
        }

        # 写 manifest（export 模式下）
        if mode == 'export':
            mpath = self._manifest_runs / f"{run_id}.json"
            mpath.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            logger.info(f"Manifest: {mpath}")

        return summary

    def print_summary(self, summary: dict, mode: str):
        s = summary['stats']
        tag = f"[{mode.upper()}]"
        print(f"\n{tag} Run: {summary['run_id']}")
        print(f"  日期: {summary['date_processed']}  Provider: {summary['provider']}")
        print(f"  扫描: {s['scanned']}  可解析: {s['parseable']}")
        print(f"  去重跳过: {s['dedup_skipped']}  隔离: {s['quarantined']}  Schema错误: {s['schema_errors']}")
        if mode == 'export':
            print(f"  ✅ 导出: {s['exported']} 条 → incoming/")
        elif mode == 'validate':
            print(f"  ✅ 校验通过: {s['exported']} 条（未落盘）")
        else:
            print(f"  ✅ 预计导出: {len(summary['exported_files']) + s['exported']} 条（未落盘）")
        if summary.get('quarantine_file'):
            print(f"  ⚠️  隔离文件: quarantine/{summary['quarantine_file']}")
        print()
