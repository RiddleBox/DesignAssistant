from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
PHASE21_DATA_DIR = BASE_DIR / "phase2.1_implementation" / "data"

DEFAULT_SOURCE_REPORT = REPORTS_DIR / "2026-04-13_1311_batch1_bucket_candidates.json"
DEFAULT_EXCLUDE_DRAFT = PHASE21_DATA_DIR / "benchmark_samples_batch1_draft.json"
DEFAULT_OUTPUT_PREFIX = REPORTS_DIR / "batch2_bucket_candidates"
DEFAULT_DERIVATION_LABEL = "batch2_from_batch1_remaining"
DEFAULT_TOP_N = 20

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
FIELDNAMES = [
    "file_name",
    "source_id",
    "title",
    "source_name",
    "published_at",
    "signal_type_hint",
    "candidate_bucket",
    "recommended_set",
    "confidence_band",
    "manual_review_priority",
    "score_signal",
    "score_noise",
    "score_boundary",
    "reasons",
    "source_url",
    "content_excerpt",
]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_excluded_origin_files(draft: dict[str, Any]) -> set[str]:
    excluded: set[str] = set()
    for sample in draft.get("samples") or []:
        draft_meta = sample.get("draft_meta") or {}
        origin_file = str(draft_meta.get("origin_file") or "").strip()
        if origin_file:
            excluded.add(origin_file)
    return excluded


def _row_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        PRIORITY_ORDER.get(str(row.get("manual_review_priority") or "low"), 9),
        CONFIDENCE_ORDER.get(str(row.get("confidence_band") or "high"), 9),
        -max(
            int(row.get("score_signal") or 0),
            int(row.get("score_noise") or 0),
            int(row.get("score_boundary") or 0),
        ),
        str(row.get("file_name") or ""),
    )


def _build_shortlist(rows: list[dict[str, Any]], top_n: int) -> dict[str, list[dict[str, Any]]]:
    shortlist: dict[str, list[dict[str, Any]]] = {}
    for bucket in ("signal", "boundary", "noise"):
        bucket_rows = [row for row in rows if str(row.get("candidate_bucket") or "") == bucket]
        shortlist[bucket] = sorted(bucket_rows, key=_row_sort_key)[: max(0, top_n)]
    return shortlist


def derive_followup_report(
    source_report: dict[str, Any],
    excluded_origin_files: set[str],
    *,
    source_report_path: Path,
    exclude_draft_path: Path,
    derivation_label: str,
    top_n: int,
) -> dict[str, Any]:
    all_rows = list(source_report.get("rows") or [])
    remaining_rows = [
        row
        for row in all_rows
        if str(row.get("file_name") or "") not in excluded_origin_files
    ]

    bucket_counter = Counter(str(row.get("candidate_bucket") or "unknown") for row in remaining_rows)
    priority_counter = Counter(str(row.get("manual_review_priority") or "unknown") for row in remaining_rows)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "derivation_label": derivation_label,
        "source_report": str(source_report_path),
        "excluded_draft": str(exclude_draft_path),
        "source_rules_version": source_report.get("rules_version") or "",
        "source_total_rows": len(all_rows),
        "excluded_origin_file_count": len(excluded_origin_files),
        "excluded_origin_files": sorted(excluded_origin_files),
        "remaining_samples": len(remaining_rows),
        "bucket_counts": dict(bucket_counter),
        "review_priority_counts": dict(priority_counter),
        "notes": [
            "This follow-up artifact excludes rows whose origin_file has already been materialized into the provided draft benchmark file.",
            "Rows remain heuristic candidates until they are reviewed and consolidated into a formal benchmark draft.",
            "Keep this artifact together with the derived draft and review queue so later batches can be reproduced exactly.",
        ],
        "shortlist": _build_shortlist(remaining_rows, top_n=top_n),
        "rows": remaining_rows,
    }


def write_outputs(report: dict[str, Any], out_prefix: Path) -> tuple[Path, Path]:
    json_path = out_prefix.with_suffix(".json")
    csv_path = out_prefix.with_suffix(".csv")

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in report.get("rows") or []:
            csv_row = dict(row)
            csv_row["reasons"] = " | ".join(csv_row.get("reasons") or [])
            writer.writerow(csv_row)

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive a follow-up batch candidate report by excluding rows already used in an existing draft benchmark file.")
    parser.add_argument("--source-report", default=str(DEFAULT_SOURCE_REPORT), help="Path to the source candidate report JSON.")
    parser.add_argument("--exclude-draft", default=str(DEFAULT_EXCLUDE_DRAFT), help="Path to the existing draft benchmark JSON whose origin_file entries should be excluded.")
    parser.add_argument("--output-prefix", default=str(DEFAULT_OUTPUT_PREFIX), help="Output path prefix for the derived JSON and CSV artifacts.")
    parser.add_argument("--derivation-label", default=DEFAULT_DERIVATION_LABEL, help="Human-readable label recorded in the derived report metadata.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of shortlist rows to keep per bucket.")
    args = parser.parse_args()

    source_report_path = Path(args.source_report)
    exclude_draft_path = Path(args.exclude_draft)
    output_prefix = Path(args.output_prefix)

    source_report = _load_json(source_report_path)
    exclude_draft = _load_json(exclude_draft_path)
    excluded_origin_files = _collect_excluded_origin_files(exclude_draft)

    report = derive_followup_report(
        source_report,
        excluded_origin_files,
        source_report_path=source_report_path,
        exclude_draft_path=exclude_draft_path,
        derivation_label=args.derivation_label,
        top_n=args.top_n,
    )

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = write_outputs(report, output_prefix)

    print(f"Source total rows          : {report['source_total_rows']}")
    print(f"Excluded used origin files : {report['excluded_origin_file_count']}")
    print(f"Remaining samples          : {report['remaining_samples']}")
    print(f"Bucket counts              : {report['bucket_counts']}")
    print(f"Review priorities          : {report['review_priority_counts']}")
    print(f"JSON artifact              : {json_path}")
    print(f"CSV artifact               : {csv_path}")


if __name__ == "__main__":
    main()
