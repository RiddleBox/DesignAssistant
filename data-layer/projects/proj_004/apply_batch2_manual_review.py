from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TARGET_PATH = BASE_DIR / "phase2.1_implementation" / "data" / "benchmark_samples_batch2_draft.json"
REPORTS_DIR = BASE_DIR / "reports"
SUMMARY_PATH = REPORTS_DIR / "batch2_final_review_summary.json"
EVAL_EXPORT_PATH = REPORTS_DIR / "benchmark_batch2_eval_dataset.json"
REGRESSION_EXPORT_PATH = BASE_DIR / "phase2.1_implementation" / "data" / "benchmark_samples_batch2_regression.json"

FINAL_LABELS = {
    "B2D012": {"bucket": "noise", "types": []},
    "B2D015": {"bucket": "signal", "types": ["technical"]},
    "B2D028": {"bucket": "signal", "types": ["team"]},
    "B2D050": {"bucket": "signal", "types": ["market"]},
    "B2D057": {"bucket": "signal", "types": ["market"]},
    "B2D093": {"bucket": "signal", "types": ["technical"]},
    "B2D100": {"bucket": "signal", "types": ["technical"]},
    "B2D101": {"bucket": "signal", "types": ["market"]},
    "B2D102": {"bucket": "signal", "types": ["market"]},
    "B2D112": {"bucket": "noise", "types": []},
    "B2D116": {"bucket": "noise", "types": []},
    "B2D117": {"bucket": "signal", "types": ["capital"]},
    "B2D121": {"bucket": "signal", "types": ["capital"]},
    "B2D124": {"bucket": "signal", "types": ["capital"]},
    "B2D141": {"bucket": "signal", "types": ["technical"]},
    "B2D146": {"bucket": "signal", "types": ["team"]},
    "B2D152": {"bucket": "signal", "types": ["market"]},
    "B2D161": {"bucket": "signal", "types": ["capital", "team"]},
    "B2D166": {"bucket": "signal", "types": ["capital"]},
    "B2D173": {"bucket": "signal", "types": ["market"]},
}

REVIEWED_SIGNAL_IDS = set(FINAL_LABELS)


def build_expected_signals(types: list[str]) -> list[dict]:
    return [{"signal_type": signal_type, "rationale": "manual_review_confirmed"} for signal_type in types]


def ensure_human_review(sample: dict) -> dict:
    human_review = sample.get("human_review")
    if not isinstance(human_review, dict):
        human_review = {}
        sample["human_review"] = human_review
    return human_review


def set_final_review(sample: dict, *, bucket: str, types: list[str], decision_source: str, notes: str) -> None:
    sample["human_review"] = {
        "status": "reviewed",
        "decision_source": decision_source,
        "final_bucket": bucket,
        "final_types": types,
        "notes": notes,
    }
    sample.setdefault("draft_meta", {})["candidate_bucket"] = bucket
    sample.setdefault("draft_meta", {})["review_status"] = "final_reviewed"
    sample["annotation"] = {"expected_signals": build_expected_signals(types)}


def build_summary(samples: list[dict]) -> dict:
    bucket_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    multi_type_signal_ids: list[str] = []
    signal_ids: list[str] = []
    noise_ids: list[str] = []

    for sample in samples:
        human_review = sample.get("human_review") or {}
        bucket = human_review.get("final_bucket", "unknown")
        final_types = human_review.get("final_types") or []
        sample_id = sample.get("sample_id")

        bucket_counter[bucket] += 1
        if bucket == "signal":
            signal_ids.append(sample_id)
            for signal_type in final_types:
                type_counter[signal_type] += 1
            if len(final_types) > 1:
                multi_type_signal_ids.append(sample_id)
        elif bucket == "noise":
            noise_ids.append(sample_id)

    return {
        "dataset_name": "benchmark_samples_batch2_draft_finalized",
        "source_file": str(TARGET_PATH),
        "total_samples": len(samples),
        "bucket_counts": dict(sorted(bucket_counter.items())),
        "signal_type_counts": dict(sorted(type_counter.items())),
        "multi_type_signal_ids": multi_type_signal_ids,
        "signal_ids": signal_ids,
        "noise_ids": noise_ids,
    }


def build_eval_export(samples: list[dict]) -> dict:
    export_samples = []
    for sample in samples:
        human_review = sample.get("human_review") or {}
        export_samples.append(
            {
                "sample_id": sample.get("sample_id"),
                "title": sample.get("title"),
                "content": sample.get("content"),
                "source_name": sample.get("source_name"),
                "source_url": sample.get("source_url"),
                "published_at": sample.get("published_at"),
                "label_bucket": human_review.get("final_bucket", "unknown"),
                "label_types": human_review.get("final_types") or [],
                "expected_signals": (sample.get("annotation") or {}).get("expected_signals") or [],
            }
        )

    return {
        "dataset_name": "benchmark_batch2_eval_dataset",
        "source_file": str(TARGET_PATH),
        "label_source": "human_review.final_bucket/final_types",
        "total_samples": len(export_samples),
        "samples": export_samples,
    }


def build_regression_export(samples: list[dict]) -> dict:
    regression_samples = []
    positive = 0

    for sample in samples:
        human_review = sample.get("human_review") or {}
        expected_signals = (sample.get("annotation") or {}).get("expected_signals") or []
        final_bucket = human_review.get("final_bucket", "unknown")
        final_types = human_review.get("final_types") or []

        if final_bucket == "signal":
            positive += 1

        regression_samples.append(
            {
                "sample_id": sample.get("sample_id"),
                "source_type": sample.get("source_type", "news"),
                "title": sample.get("title"),
                "content": sample.get("content"),
                "published_at": sample.get("published_at"),
                "source_name": sample.get("source_name"),
                "source_url": sample.get("source_url"),
                "annotation": {
                    "expected_signals": expected_signals,
                },
                "ground_truth": {
                    "bucket": final_bucket,
                    "signal_types": final_types,
                    "is_signal": final_bucket == "signal",
                    "decision_source": human_review.get("decision_source", "unknown"),
                },
            }
        )

    return {
        "generated_from": str(TARGET_PATH),
        "summary": {
            "selected_total": len(regression_samples),
            "selected_positive": positive,
            "selected_negative": len(regression_samples) - positive,
        },
        "labeling_policy": {
            "truth_source": "human_review.final_bucket and human_review.final_types",
            "expected_signals_policy": "annotation.expected_signals is synchronized to final confirmed signal types",
            "noise_policy": "noise samples have empty expected_signals",
        },
        "samples": regression_samples,
    }


def main() -> None:
    data = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    updated = 0

    samples = data.get("samples", [])

    for sample in samples:
        sample_id = sample.get("sample_id")
        final = FINAL_LABELS.get(sample_id)
        human_review = ensure_human_review(sample)

        if final is None:
            set_final_review(
                sample,
                bucket="noise",
                types=[],
                decision_source="user_manual_review_round2_default_noise",
                notes="not selected in confirmed round2 list; defaulted to noise per user instruction",
            )
            updated += 1
            continue

        set_final_review(
            sample,
            bucket=final["bucket"],
            types=final["types"],
            decision_source="user_manual_review_round2_confirmed",
            notes="confirmed from conflict review discussion",
        )
        updated += 1

    TARGET_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = build_summary(samples)
    eval_export = build_eval_export(samples)
    regression_export = build_regression_export(samples)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    EVAL_EXPORT_PATH.write_text(json.dumps(eval_export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REGRESSION_EXPORT_PATH.write_text(json.dumps(regression_export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {updated} samples")
    print(f"reviewed signal IDs: {sorted(REVIEWED_SIGNAL_IDS)}")
    print(f"summary written to: {SUMMARY_PATH}")
    print(f"eval export written to: {EVAL_EXPORT_PATH}")
    print(f"regression export written to: {REGRESSION_EXPORT_PATH}")


if __name__ == "__main__":
    main()
