from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
PHASE21_DATA_DIR = BASE_DIR / "phase2.1_implementation" / "data"
DEFAULT_CANDIDATE_REPORT = REPORTS_DIR / "2026-04-13_1311_batch1_bucket_candidates.json"
DEFAULT_OUTPUT = PHASE21_DATA_DIR / "benchmark_samples_batch1_draft.json"
DEFAULT_SAMPLE_PREFIX = "B1D"
DEFAULT_ORIGIN_LABEL = "batch1_bucket_candidates"
DEFAULT_SIGNAL_LABEL = "candidate_signal"
DEFAULT_SIGNAL_CONFIDENCE_BANDS = "high"
DEFAULT_NOISE_CONFIDENCE_BANDS = "high"
DEFAULT_NOISE_EXCLUDED_PRIORITIES = "high"
DEFAULT_EXCLUDED_BUCKETS = "boundary"

SUPPORTED_SIGNAL_TYPES = {
    "capital",
    "team",
    "technical",
    "market",
    "regulatory",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_csv_arg(raw_value: str) -> list[str]:
    values = [item.strip().lower() for item in str(raw_value).split(",")]
    return [item for item in values if item]


def _make_signal_annotation(row: dict[str, Any], signal_label: str) -> dict[str, Any]:
    signal_type = str(row.get("signal_type_hint") or "market").lower()
    if signal_type not in SUPPORTED_SIGNAL_TYPES:
        signal_type = "market"

    title = row.get("title") or ""
    excerpt = row.get("content_excerpt") or ""
    description = f"Draft candidate derived from incoming sample `{row.get('file_name')}`: {title}. {excerpt}"

    intensity_score = max(3, min(9, int(row.get("score_signal", 0))))
    confidence_score = 8 if row.get("confidence_band") == "high" else 6
    timeliness_score = 5

    return {
        "signal_type": signal_type,
        "signal_label": signal_label,
        "description": description,
        "intensity_score": intensity_score,
        "confidence_score": confidence_score,
        "timeliness_score": timeliness_score,
        "entities": [],
    }


def _convert_row(row: dict[str, Any], index: int, *, sample_prefix: str, origin_label: str, signal_label: str) -> dict[str, Any]:
    sample_id = f"{sample_prefix}{index:03d}"
    sample = {
        "sample_id": sample_id,
        "source_type": "news",
        "title": row.get("title") or "",
        "content": row.get("content_excerpt") or "",
        "published_at": row.get("published_at") or "",
        "source_name": row.get("source_name") or "",
        "source_url": row.get("source_url") or "",
        "annotation": {
            "expected_signals": [],
        },
        "draft_meta": {
            "origin": origin_label,
            "origin_file": row.get("file_name"),
            "candidate_bucket": row.get("candidate_bucket"),
            "recommended_set": row.get("recommended_set"),
            "confidence_band": row.get("confidence_band"),
            "manual_review_priority": row.get("manual_review_priority"),
            "score_signal": row.get("score_signal"),
            "score_noise": row.get("score_noise"),
            "score_boundary": row.get("score_boundary"),
            "reasons": row.get("reasons") or [],
            "review_status": "draft_unreviewed",
        },
        "human_review": {
            "decision": "pending",
            "corrected_bucket": row.get("candidate_bucket"),
            "corrected_signal_types": [],
            "corrected_expected_signals": [],
            "review_notes": "",
            "reviewer": "",
            "reviewed_at": "",
        },
    }

    if row.get("candidate_bucket") == "signal":
        sample["annotation"]["expected_signals"] = [_make_signal_annotation(row, signal_label)]

    return sample


def _selection_policy_doc(
    *,
    signal_confidence_bands: list[str],
    noise_confidence_bands: list[str],
    noise_excluded_priorities: list[str],
    excluded_buckets: list[str],
) -> dict[str, str]:
    return {
        "included_signal": f"candidate_bucket=signal and confidence_band in {signal_confidence_bands}",
        "included_noise": f"candidate_bucket=noise and confidence_band in {noise_confidence_bands} and manual_review_priority not in {noise_excluded_priorities}",
        "excluded_buckets": f"candidate_bucket in {excluded_buckets}",
    }


def build_draft(
    report: dict[str, Any],
    *,
    source_report_path: Path,
    sample_prefix: str,
    origin_label: str,
    signal_label: str,
    signal_confidence_bands: list[str],
    noise_confidence_bands: list[str],
    noise_excluded_priorities: list[str],
    excluded_buckets: list[str],
) -> dict[str, Any]:
    rows = report.get("rows") or []

    selected: list[dict[str, Any]] = []
    for row in rows:
        bucket = str(row.get("candidate_bucket") or "").lower()
        confidence = str(row.get("confidence_band") or "").lower()
        priority = str(row.get("manual_review_priority") or "").lower()

        if bucket in excluded_buckets:
            continue

        if bucket == "signal" and confidence in signal_confidence_bands:
            selected.append(row)
            continue

        if bucket == "noise" and confidence in noise_confidence_bands and priority not in noise_excluded_priorities:
            selected.append(row)
            continue

    samples = [
        _convert_row(
            row,
            index + 1,
            sample_prefix=sample_prefix,
            origin_label=origin_label,
            signal_label=signal_label,
        )
        for index, row in enumerate(selected)
    ]
    positive = sum(1 for sample in samples if sample["annotation"]["expected_signals"])
    negative = len(samples) - positive

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_report": str(source_report_path),
        "selection_policy": _selection_policy_doc(
            signal_confidence_bands=signal_confidence_bands,
            noise_confidence_bands=noise_confidence_bands,
            noise_excluded_priorities=noise_excluded_priorities,
            excluded_buckets=excluded_buckets,
        ),
        "summary": {
            "selected_total": len(samples),
            "selected_positive": positive,
            "selected_negative": negative,
        },
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a formal benchmark draft from a candidate report JSON.")
    parser.add_argument("--input", default=str(DEFAULT_CANDIDATE_REPORT), help="Path to the candidate report JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the draft benchmark JSON output.")
    parser.add_argument("--sample-prefix", default=DEFAULT_SAMPLE_PREFIX, help="Sample id prefix, for example B1D or B2D.")
    parser.add_argument("--origin-label", default=DEFAULT_ORIGIN_LABEL, help="Origin label written into draft_meta.origin.")
    parser.add_argument("--signal-label", default=DEFAULT_SIGNAL_LABEL, help="Signal label written into expected_signals entries.")
    parser.add_argument("--signal-confidence-bands", default=DEFAULT_SIGNAL_CONFIDENCE_BANDS, help="Comma-separated confidence bands included for signal rows.")
    parser.add_argument("--noise-confidence-bands", default=DEFAULT_NOISE_CONFIDENCE_BANDS, help="Comma-separated confidence bands included for noise rows.")
    parser.add_argument("--noise-excluded-priorities", default=DEFAULT_NOISE_EXCLUDED_PRIORITIES, help="Comma-separated review priorities excluded for noise rows.")
    parser.add_argument("--excluded-buckets", default=DEFAULT_EXCLUDED_BUCKETS, help="Comma-separated buckets to exclude entirely from the formal draft.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    signal_confidence_bands = _parse_csv_arg(args.signal_confidence_bands)
    noise_confidence_bands = _parse_csv_arg(args.noise_confidence_bands)
    noise_excluded_priorities = _parse_csv_arg(args.noise_excluded_priorities)
    excluded_buckets = _parse_csv_arg(args.excluded_buckets)

    report = _load_json(input_path)
    draft = build_draft(
        report,
        source_report_path=input_path,
        sample_prefix=args.sample_prefix,
        origin_label=args.origin_label,
        signal_label=args.signal_label,
        signal_confidence_bands=signal_confidence_bands,
        noise_confidence_bands=noise_confidence_bands,
        noise_excluded_priorities=noise_excluded_priorities,
        excluded_buckets=excluded_buckets,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Selected total    : {draft['summary']['selected_total']}")
    print(f"Selected positive : {draft['summary']['selected_positive']}")
    print(f"Selected negative : {draft['summary']['selected_negative']}")
    print(f"Output            : {output_path}")


if __name__ == "__main__":
    main()
