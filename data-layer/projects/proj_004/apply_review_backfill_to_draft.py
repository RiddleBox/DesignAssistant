from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "phase2.1_implementation" / "data"

DEFAULT_PENDING = REPORTS_DIR / "benchmark_review_batch2_top20_backfill_pending.json"
DEFAULT_DRAFT = DATA_DIR / "benchmark_samples_batch2_draft.json"
DEFAULT_ALLOWED_DECISIONS = "accepted,modified,rejected"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_csv_arg(raw_value: str) -> set[str]:
    return {
        item.strip().lower()
        for item in str(raw_value).split(",")
        if item.strip()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply human-confirmed review backfill data into a benchmark draft JSON.")
    parser.add_argument("--pending", default=str(DEFAULT_PENDING), help="Path to the backfill-pending JSON file.")
    parser.add_argument("--draft", default=str(DEFAULT_DRAFT), help="Path to the benchmark draft JSON file to update.")
    parser.add_argument("--output", default="", help="Optional output path. If omitted, the draft file is updated in place.")
    parser.add_argument("--allowed-decisions", default=DEFAULT_ALLOWED_DECISIONS, help="Comma-separated human_review decisions that are allowed to overwrite the draft.")
    args = parser.parse_args()

    pending_path = Path(args.pending)
    draft_path = Path(args.draft)
    output_path = Path(args.output) if args.output else draft_path
    allowed_decisions = _parse_csv_arg(args.allowed_decisions)

    pending = _load_json(pending_path)
    draft = _load_json(draft_path)

    pending_reviews = {}
    skipped = []
    for sample in pending.get("samples") or []:
        sample_id = str(sample.get("sample_id") or "")
        human_review = sample.get("human_review") or {}
        decision = str(human_review.get("decision") or "").lower()
        if decision in allowed_decisions:
            pending_reviews[sample_id] = human_review
        else:
            skipped.append(sample_id)

    updated = []
    for sample in draft.get("samples") or []:
        sample_id = str(sample.get("sample_id") or "")
        if sample_id in pending_reviews:
            sample["human_review"] = pending_reviews[sample_id]
            updated.append(sample_id)

    output_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Allowed decisions : {sorted(allowed_decisions)}")
    print(f"Updated samples   : {len(updated)}")
    print(f"Skipped pending   : {len(skipped)}")
    print(f"Output            : {output_path}")
    if updated:
        print("sample_ids=" + ",".join(updated))


if __name__ == "__main__":
    main()
