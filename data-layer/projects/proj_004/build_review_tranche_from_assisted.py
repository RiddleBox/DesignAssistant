from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "phase2.1_implementation" / "data"

DEFAULT_ASSISTED_INPUT = REPORTS_DIR / "benchmark_review_assisted_batch2_pass1.json"
DEFAULT_DRAFT_INPUT = DATA_DIR / "benchmark_samples_batch2_draft.json"
DEFAULT_RECOMMENDATIONS_OUTPUT = REPORTS_DIR / "benchmark_review_batch2_top20_recommendations.json"
DEFAULT_BACKFILL_OUTPUT = REPORTS_DIR / "benchmark_review_batch2_top20_backfill_pending.json"
DEFAULT_SUGGESTION_LIST = "priority_shortlist"
DEFAULT_START_RANK = 1
DEFAULT_LIMIT = 20
DEFAULT_RANGE_LABEL = "batch2_top20"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _confidence_score(confidence_band: str) -> int:
    mapping = {
        "high": 8,
        "medium": 7,
        "low": 6,
    }
    return mapping.get(str(confidence_band).lower(), 6)


def _suggestion_confidence(priority_score: int) -> str:
    if priority_score >= 10:
        return "high"
    if priority_score >= 6:
        return "medium"
    return "low"


def _build_signal_annotations(sample: dict[str, Any], suggested_signal_types: list[str]) -> list[dict[str, Any]]:
    if not suggested_signal_types:
        return []

    title = str(sample.get("title") or "")
    sample_id = str(sample.get("sample_id") or "")
    expected_signals = sample.get("annotation", {}).get("expected_signals") or []
    existing_by_type = {
        str(item.get("signal_type") or ""): item
        for item in expected_signals
        if item.get("signal_type")
    }

    score_signal = int(sample.get("draft_meta", {}).get("score_signal") or 0)
    confidence_band = str(sample.get("draft_meta", {}).get("confidence_band") or "")

    output: list[dict[str, Any]] = []
    for signal_type in suggested_signal_types:
        existing = _clone(existing_by_type.get(signal_type) or {})
        if existing:
            existing["signal_label"] = "ai_suggested_signal"
            existing["description"] = f"AI-assisted review suggestion for {sample_id}: {title}"
            existing["confidence_score"] = _confidence_score(confidence_band)
            output.append(existing)
            continue

        output.append(
            {
                "signal_type": signal_type,
                "signal_label": "ai_suggested_signal",
                "description": f"AI-assisted review suggestion for {sample_id}: {title}",
                "intensity_score": max(3, min(9, score_signal or 5)),
                "confidence_score": _confidence_score(confidence_band),
                "timeliness_score": 5,
                "entities": [],
            }
        )

    return output


def _build_review_note(suggestion: dict[str, Any]) -> str:
    rationale = [str(item).strip() for item in (suggestion.get("rationale") or []) if str(item).strip()]
    if rationale:
        return " ".join(rationale)

    review_focus = str(suggestion.get("review_focus") or "confirm")
    if review_focus == "bucket":
        return "Confirm whether the sample should stay in the current bucket or move to the suggested bucket."
    if review_focus == "type":
        return "Confirm whether the signal type should be corrected to the suggested type set."
    return "Confirm whether the current draft labeling is still appropriate."


def build_tranche(
    assisted: dict[str, Any],
    draft: dict[str, Any],
    *,
    assisted_input_path: Path,
    draft_input_path: Path,
    suggestion_list_name: str,
    start_rank: int,
    limit: int,
    range_label: str,
    recommendations_output: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    suggestions = list(assisted.get(suggestion_list_name) or [])
    start_index = max(0, start_rank - 1)
    selected = suggestions[start_index : start_index + max(0, limit)]

    draft_by_id = {
        str(sample.get("sample_id") or ""): sample
        for sample in draft.get("samples") or []
    }

    recommendation_items: list[dict[str, Any]] = []
    backfill_samples: list[dict[str, Any]] = []

    for offset, suggestion in enumerate(selected, start=start_rank):
        sample_id = str(suggestion.get("sample_id") or "")
        if sample_id not in draft_by_id:
            raise KeyError(f"sample_id not found in draft: {sample_id}")

        sample = _clone(draft_by_id[sample_id])
        recommended_bucket = str(suggestion.get("suggested_bucket") or sample.get("draft_meta", {}).get("candidate_bucket") or "noise")
        recommended_signal_types = [
            str(item)
            for item in (suggestion.get("suggested_signal_types") or [])
            if str(item)
        ]
        if recommended_bucket != "signal":
            recommended_signal_types = []

        priority_score = int(suggestion.get("priority_score") or 0)
        review_note = _build_review_note(suggestion)
        issue_tags = [str(item) for item in (suggestion.get("issue_tags") or [])]
        rationale = [str(item) for item in (suggestion.get("rationale") or [])]
        draft_signal_types = [
            str(item.get("signal_type") or "")
            for item in (sample.get("annotation", {}).get("expected_signals") or [])
            if item.get("signal_type")
        ]

        recommendation_items.append(
            {
                "rank": offset,
                "sample_id": sample_id,
                "title": sample.get("title"),
                "source_name": sample.get("source_name"),
                "published_at": sample.get("published_at"),
                "source_url": sample.get("source_url"),
                "draft_bucket": sample.get("draft_meta", {}).get("candidate_bucket"),
                "draft_signal_types": draft_signal_types,
                "recommended_bucket": recommended_bucket,
                "recommended_signal_types": recommended_signal_types,
                "review_focus": suggestion.get("review_focus") or "confirm",
                "suggestion_confidence": _suggestion_confidence(priority_score),
                "priority_score": priority_score,
                "issue_tags": issue_tags,
                "one_line_reason": rationale[0] if rationale else review_note,
                "review_note": review_note,
            }
        )

        sample["human_review"] = {
            "decision": "suggested",
            "corrected_bucket": recommended_bucket,
            "corrected_signal_types": recommended_signal_types,
            "corrected_expected_signals": _build_signal_annotations(sample, recommended_signal_types),
            "review_notes": review_note,
            "reviewer": "",
            "reviewed_at": "",
        }
        backfill_samples.append(sample)

    recommendations_doc = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_assisted_suggestions": str(assisted_input_path),
        "source_queue": assisted.get("source_queue") or "",
        "source_benchmark": str(draft_input_path),
        "range_label": range_label,
        "suggestion_list": suggestion_list_name,
        "start_rank": start_rank,
        "selected_total": len(recommendation_items),
        "generated_for": "assisted second-pass review",
        "items": recommendation_items,
    }

    backfill_doc = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_recommendations": str(recommendations_output),
        "source_benchmark": str(draft_input_path),
        "purpose": f"Reviewer confirmation backfill draft for `{range_label}` derived from `{suggestion_list_name}`.",
        "instructions_for_reviewer": {
            "how_to_use": [
                "Check each row's suggested human_review fields.",
                "Change human_review.decision from `suggested` to `accepted` if you agree.",
                "If you disagree, keep decision as `modified` or `rejected` and edit corrected_bucket / corrected_signal_types / corrected_expected_signals / review_notes.",
                "After confirmation, merge only accepted or modified rows back into the formal benchmark draft.",
            ],
            "decision_meaning": {
                "suggested": "AI-prepared recommendation, not yet confirmed by human.",
                "accepted": "Human confirmed the suggestion as final.",
                "modified": "Human changed one or more suggested fields.",
                "rejected": "Human rejected the suggestion and plans to keep original draft labeling.",
            },
        },
        "summary": {
            "selected_total": len(backfill_samples),
            "range_label": range_label,
            "suggestion_list": suggestion_list_name,
            "start_rank": start_rank,
        },
        "samples": backfill_samples,
    }

    return recommendations_doc, backfill_doc


def main() -> None:
    parser = argparse.ArgumentParser(description="Build review tranche recommendation and backfill-pending artifacts from assisted review suggestions.")
    parser.add_argument("--assisted-input", default=str(DEFAULT_ASSISTED_INPUT), help="Path to the assisted review suggestion JSON.")
    parser.add_argument("--draft-input", default=str(DEFAULT_DRAFT_INPUT), help="Path to the target benchmark draft JSON.")
    parser.add_argument("--recommendations-output", default=str(DEFAULT_RECOMMENDATIONS_OUTPUT), help="Path to the recommendations JSON output.")
    parser.add_argument("--backfill-output", default=str(DEFAULT_BACKFILL_OUTPUT), help="Path to the backfill-pending JSON output.")
    parser.add_argument("--suggestion-list", default=DEFAULT_SUGGESTION_LIST, choices=["priority_shortlist", "all_suggestions"], help="Which suggestion list to slice from the assisted suggestions artifact.")
    parser.add_argument("--start-rank", type=int, default=DEFAULT_START_RANK, help="1-based rank inside the selected suggestion list.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum number of suggested rows to include in this tranche.")
    parser.add_argument("--range-label", default=DEFAULT_RANGE_LABEL, help="Human-readable label for this tranche.")
    args = parser.parse_args()

    assisted_input = Path(args.assisted_input)
    draft_input = Path(args.draft_input)
    recommendations_output = Path(args.recommendations_output)
    backfill_output = Path(args.backfill_output)

    assisted = _load_json(assisted_input)
    draft = _load_json(draft_input)

    recommendations_doc, backfill_doc = build_tranche(
        assisted,
        draft,
        assisted_input_path=assisted_input,
        draft_input_path=draft_input,
        suggestion_list_name=args.suggestion_list,
        start_rank=args.start_rank,
        limit=args.limit,
        range_label=args.range_label,
        recommendations_output=recommendations_output,
    )

    recommendations_output.parent.mkdir(parents=True, exist_ok=True)
    backfill_output.parent.mkdir(parents=True, exist_ok=True)
    recommendations_output.write_text(json.dumps(recommendations_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    backfill_output.write_text(json.dumps(backfill_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Selected suggestions : {recommendations_doc['selected_total']}")
    print(f"Recommendations      : {recommendations_output}")
    print(f"Backfill pending     : {backfill_output}")


if __name__ == "__main__":
    main()
