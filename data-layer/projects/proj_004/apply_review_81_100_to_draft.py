from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PENDING_PATH = BASE / "reports" / "benchmark_review_81_100_backfill_pending.json"
DRAFT_PATH = BASE / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"


def main() -> None:
    pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))

    pending_reviews = {
        sample["sample_id"]: sample["human_review"]
        for sample in pending["samples"]
    }

    updated = []
    for sample in draft["samples"]:
        sample_id = sample.get("sample_id")
        if sample_id in pending_reviews:
            sample["human_review"] = pending_reviews[sample_id]
            updated.append(sample_id)

    DRAFT_PATH.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"updated {len(updated)} samples")
    print("sample_ids=" + ",".join(updated))


if __name__ == "__main__":
    main()
