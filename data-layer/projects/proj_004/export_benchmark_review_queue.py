from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"
DEFAULT_OUTPUT = BASE_DIR / "reports" / "benchmark_review_queue_batch1.json"

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_bucket(sample: dict[str, Any]) -> str:
    signals = ((sample.get("annotation") or {}).get("expected_signals") or [])
    return "signal" if signals else "noise"


def _signal_types(sample: dict[str, Any]) -> list[str]:
    signals = ((sample.get("annotation") or {}).get("expected_signals") or [])
    return [str(item.get("signal_type") or "") for item in signals if item.get("signal_type")]


def _build_row(sample: dict[str, Any]) -> dict[str, Any]:
    draft_meta = sample.get("draft_meta") or {}
    human_review = sample.get("human_review") or {}
    title = sample.get("title") or ""
    content = sample.get("content") or ""

    return {
        "sample_id": sample.get("sample_id"),
        "origin_file": draft_meta.get("origin_file"),
        "title": title,
        "content_preview": content[:280],
        "source_name": sample.get("source_name") or "",
        "published_at": sample.get("published_at") or "",
        "source_url": sample.get("source_url") or "",
        "draft_bucket": draft_meta.get("candidate_bucket"),
        "draft_signal_types": _signal_types(sample),
        "confidence_band": draft_meta.get("confidence_band"),
        "manual_review_priority": draft_meta.get("manual_review_priority"),
        "score_signal": draft_meta.get("score_signal"),
        "score_noise": draft_meta.get("score_noise"),
        "score_boundary": draft_meta.get("score_boundary"),
        "reasons": draft_meta.get("reasons") or [],
        "current_expected_bucket": _expected_bucket(sample),
        "review_decision": human_review.get("decision") or "pending",
        "corrected_bucket": human_review.get("corrected_bucket") or draft_meta.get("candidate_bucket"),
        "corrected_signal_types": human_review.get("corrected_signal_types") or [],
        "review_notes": human_review.get("review_notes") or "",
    }


def _sort_key(row: dict[str, Any]) -> tuple:
    return (
        PRIORITY_ORDER.get(str(row.get("manual_review_priority") or "low"), 9),
        CONFIDENCE_ORDER.get(str(row.get("confidence_band") or "high"), 9),
        -max(int(row.get("score_boundary") or 0), int(row.get("score_signal") or 0), int(row.get("score_noise") or 0)),
        str(row.get("sample_id") or ""),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a reviewer-friendly queue from the benchmark draft JSON.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to the draft benchmark JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the flattened review queue JSON.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    data = _load_json(input_path)
    samples = data.get("samples") or []
    rows = [_build_row(sample) for sample in samples]
    rows.sort(key=_sort_key)

    output = {
        "source_benchmark": str(input_path),
        "total": len(rows),
        "pending": sum(1 for row in rows if row.get("review_decision") == "pending"),
        "rows": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Exported rows : {output['total']}")
    print(f"Pending rows  : {output['pending']}")
    print(f"Output        : {output_path}")


if __name__ == "__main__":
    main()
