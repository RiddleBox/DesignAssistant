from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRAFT_PATH = BASE / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"
BACKFILL_PATH = BASE / "reports" / "benchmark_review_41_60_backfill_pending.json"


def main() -> None:
    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    backfill = json.loads(BACKFILL_PATH.read_text(encoding="utf-8"))

    backfill_by_id = {sample["sample_id"]: sample for sample in backfill["samples"]}
    updated = 0

    for sample in draft["samples"]:
        sample_id = sample.get("sample_id")
        if sample_id not in backfill_by_id:
            continue

        source = backfill_by_id[sample_id]
        sample["human_review"] = source.get("human_review", {})
        updated += 1

    DRAFT_PATH.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {updated} samples in {DRAFT_PATH}")


if __name__ == "__main__":
    main()
