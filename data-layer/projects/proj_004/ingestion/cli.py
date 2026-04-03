"""
CLI 入口
用法：
  python -m ingestion.cli --mode dry-run --date 2026-04-03
  python -m ingestion.cli --mode validate --date-range 2026-03-24:2026-04-03
  python -m ingestion.cli --mode export --date 2026-04-03
  python -m ingestion.cli --mode export  # 默认处理昨天
"""
import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 把 proj_004/ 加到 sys.path，保证直接运行时 import 正常
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ingestion.config import load_config
from ingestion.normalizer import Normalizer, DedupIndex
from ingestion.exporter import Exporter
from ingestion.providers.knowledge_base import KnowledgeBaseAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('ingestion.cli')


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='python -m ingestion.cli',
        description='样本收集模块 CLI — 从 knowledge-base 导入样本到 incoming/'
    )
    p.add_argument(
        '--provider', default='kb',
        choices=['kb'],
        help='数据来源（默认 kb = knowledge_base_inbox）'
    )
    p.add_argument(
        '--date',
        help='处理指定日期 YYYY-MM-DD（默认：昨天）'
    )
    p.add_argument(
        '--date-range',
        metavar='START:END',
        help='批量处理日期范围，如 2026-03-24:2026-04-03（含首尾）'
    )
    p.add_argument(
        '--mode', default='export',
        choices=['dry-run', 'validate', 'export'],
        help='运行模式（默认 export）'
    )
    p.add_argument(
        '--limit', type=int, default=None,
        help='最多处理 N 条（调试用）'
    )
    p.add_argument(
        '--force-reimport', action='store_true',
        help='跳过去重检查（危险，仅调试用）'
    )
    p.add_argument(
        '--config', default=None,
        help='指定 config.yaml 路径（默认自动定位）'
    )
    return p


def resolve_date_params(args) -> tuple[str | None, tuple[str, str] | None]:
    if args.date_range:
        parts = args.date_range.split(':')
        if len(parts) != 2:
            print(f"[ERROR] --date-range 格式应为 START:END，如 2026-03-24:2026-04-03")
            sys.exit(1)
        return None, (parts[0].strip(), parts[1].strip())
    if args.date:
        return args.date, None
    return None, None


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    # ── 加载配置 ──
    cfg = load_config(args.config)
    provider_cfg = cfg.get('providers', {})
    output_cfg = cfg.get('output', {})
    ingestion_cfg = cfg.get('ingestion', {})

    # ── 构建路径 ──
    module_dir = Path(__file__).parent
    incoming_dir = Path(output_cfg.get('incoming_dir', ''))
    dedup_index_path = module_dir / ingestion_cfg.get('dedup_index_path', 'manifest/dedup_index.json')
    manifest_dir = module_dir / 'manifest'
    quarantine_dir = module_dir / 'quarantine'

    # ── 解析日期参数 ──
    single_date, date_range = resolve_date_params(args)

    # 用于 manifest 记录
    if single_date:
        date_label = single_date
    elif date_range:
        date_label = f"{date_range[0]}:{date_range[1]}"
    else:
        date_label = str(date.today() - timedelta(days=1))

    # ── Provider ──
    kb_cfg = provider_cfg.get('knowledge_base', {})
    inbox_root = kb_cfg.get('inbox_root', '')
    if not inbox_root:
        print("[ERROR] config.yaml 未配置 providers.knowledge_base.inbox_root")
        sys.exit(1)

    adapter = KnowledgeBaseAdapter(inbox_root=inbox_root)

    # ── Fetch ──
    logger.info(f"[{args.mode.upper()}] Provider: {adapter.provider_id}  日期: {date_label}")
    raw_records = adapter.fetch(
        date=single_date,
        date_range=date_range,
        limit=args.limit,
    )
    logger.info(f"获取 RawRecord: {len(raw_records)} 条")

    # ── Normalize ──
    dedup = DedupIndex(dedup_index_path)
    normalizer = Normalizer(dedup_index=dedup, config=cfg)
    normalized, skipped, quarantined = normalizer.normalize(
        raw_records,
        force_reimport=args.force_reimport,
    )
    logger.info(f"标准化完成: 可导出={len(normalized)}  去重跳过={len(skipped)}  隔离={len(quarantined)}")

    # ── Export ──
    exporter = Exporter(
        incoming_dir=incoming_dir,
        manifest_dir=manifest_dir,
        quarantine_dir=quarantine_dir,
    )
    summary = exporter.export(
        normalized=normalized,
        skipped=skipped,
        quarantined=quarantined,
        provider=adapter.provider_id,
        date_processed=date_label,
        mode=args.mode,
        scanned=len(raw_records),
        parseable=len(raw_records) - len(quarantined),
    )

    # 持久化去重索引（只在 export 模式下）
    if args.mode == 'export':
        dedup.save()
        logger.info("去重索引已保存")

    exporter.print_summary(summary, args.mode)


if __name__ == '__main__':
    main()
