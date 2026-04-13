from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRAFT_PATH = BASE / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"
REPORTS_DIR = BASE / "reports"
RECOMMENDATIONS_PATH = REPORTS_DIR / "benchmark_review_81_100_recommendations.json"
BACKFILL_PATH = REPORTS_DIR / "benchmark_review_81_100_backfill_pending.json"

TRANCHE_IDS = [
    "B1D019", "B1D024", "B1D030", "B1D031", "B1D033", "B1D036", "B1D044", "B1D065", "B1D070", "B1D073",
    "B1D078", "B1D081", "B1D093", "B1D096", "B1D097", "B1D104", "B1D107", "B1D108", "B1D006", "B1D015",
]


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def main() -> None:
    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    by_id = {sample["sample_id"]: sample for sample in draft["samples"]}

    recommendation_rules = {
        "B1D019": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Expansion-launch and quest content coverage is routine game update reporting, not structural signal material.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D024": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "This post-launch compatibility issue does not change player behavior, business model, or industry power structure, so it should remain noise.",
            "review_note": "Keep as noise. This is a local support issue, not a paradigm or structural signal.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D030": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "New game announcement coverage is outside the benchmark's structural-signal target.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D031": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical", "market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "An executive framing games around 'massive disruption' points to a strategic platform and market-shift narrative, not just a pure technical tag.",
            "review_note": "Keep as signal. This is better typed as technical plus market because it is about strategic response to industry disruption.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "technical",
                    "signal_label": "platform_shift_signal",
                    "description": "Disney is explicitly reacting to a disruptive shift in how games are built and distributed, implying changing platform and production assumptions.",
                    "intensity_score": 7,
                    "confidence_score": 7,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "platform_shift_signal",
                    "description": "The comments frame gaming as undergoing market-level disruption that requires strategic repositioning from large IP holders.",
                    "intensity_score": 7,
                    "confidence_score": 7,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D033": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "The tonal shift is interesting, but this single DLC item is not strong enough on its own to count as a structural signal without broader corroborating evidence.",
            "review_note": "Keep as noise for now. It may support a broader trendline when combined with other samples such as Pokopia, but this item alone is too weak to promote.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D036": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Voice acting anecdote and recording process coverage do not indicate structural industry change.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D044": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "This is a routine capital-market correction rather than a paradigm signal, even if it reveals investor weakness in reading community self-repair dynamics.",
            "review_note": "Keep as noise. It exposes a 2026 investor blind spot around the self-repair capacity of community sentiment, but the item itself is still not a structural benchmark signal.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D065": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "This reflects a governance-paradigm shift from static walls toward a more dynamic adaptive ecosystem for player-generated expression and platform control.",
            "review_note": "Keep as signal. Treat this as a governance-paradigm signal rather than routine policy noise.",
            "decision": "accepted",
            "corrected_expected_signals": [
                {
                    "signal_type": "technical",
                    "signal_label": "governance_paradigm_signal",
                    "description": "Nintendo's stricter image-sharing controls indicate a governance shift from static platform restrictions toward more adaptive ecosystem management of player expression.",
                    "intensity_score": 7,
                    "confidence_score": 7,
                    "timeliness_score": 5,
                    "entities": [],
                }
            ],
        },
        "B1D070": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Actor typecasting commentary is entertainment-industry color, not benchmark signal material.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D073": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Movie casting news is outside the benchmark's target scope.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D078": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "Discussion of a possible Switch 2 port remains speculative platform planning, not a confirmed structural signal.",
            "review_note": "Keep as noise unless you want speculative platform expansion intent counted.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D081": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Film leak confirmation remains entertainment coverage, not a games-industry structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D093": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Adaptation PR commentary is outside the benchmark signal target.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D096": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "This sample supports a broader convergence toward denser emotional interaction, but the narrated gameplay item alone is too weak to treat as a standalone structural signal.",
            "review_note": "Keep as noise for now. It may serve as supporting evidence for a cross-sample trend toward high-density emotional interaction when read with adjacent cases such as Hello Kitty, but it should not stand alone as a benchmark signal.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D097": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "high",
            "one_line_reason": "A trophy achievement story is community novelty content, not a structural signal.",
            "review_note": "Downgrade to noise.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D104": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "high",
            "one_line_reason": "Celebrity or athlete play impressions are feature coverage, not industry-signal material.",
            "review_note": "Downgrade to noise.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D107": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Franchise teasing and concept art discussion are not structural benchmark signals.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D108": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Set photos from a TV adaptation remain outside the benchmark's intended scope.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D006": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market", "technical"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "Long development cycles eroding youth connection to Final Fantasy is a design-production lag signal with direct market consequences.",
            "review_note": "Keep as signal, but this is not capital. It is better framed as technical plus market around development-cycle mismatch and audience attrition.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "technical",
                    "signal_label": "development_cycle_mismatch_signal",
                    "description": "The comment highlights a production-model lag where long AAA development cycles no longer match contemporary audience engagement rhythms.",
                    "intensity_score": 7,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "development_cycle_mismatch_signal",
                    "description": "Long release gaps are weakening younger audience connection and creating generational engagement risk for a major franchise.",
                    "intensity_score": 7,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D015": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "high",
            "one_line_reason": "Emergent gameplay examples around tool usage are feature-story material, not structural signal content.",
            "review_note": "Downgrade to noise.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
    }

    recommendation_items = []
    backfill_samples = []

    for rank, sample_id in enumerate(TRANCHE_IDS, start=81):
        sample = clone(by_id[sample_id])
        draft_bucket = sample["draft_meta"]["candidate_bucket"]
        draft_signal_types = [signal["signal_type"] for signal in sample.get("annotation", {}).get("expected_signals", [])]
        rule = recommendation_rules[sample_id]

        recommendation_items.append(
            {
                "rank": rank,
                "sample_id": sample_id,
                "title": sample["title"],
                "source_name": sample["source_name"],
                "published_at": sample["published_at"],
                "source_url": sample["source_url"],
                "draft_bucket": draft_bucket,
                "draft_signal_types": draft_signal_types,
                "recommended_bucket": rule["recommended_bucket"],
                "recommended_signal_types": rule["recommended_signal_types"],
                "review_focus": rule["review_focus"],
                "suggestion_confidence": rule["suggestion_confidence"],
                "one_line_reason": rule["one_line_reason"],
                "review_note": rule["review_note"],
            }
        )

        sample["human_review"] = {
            "decision": rule["decision"],
            "corrected_bucket": rule["recommended_bucket"],
            "corrected_signal_types": rule["recommended_signal_types"],
            "corrected_expected_signals": rule["corrected_expected_signals"],
            "review_notes": rule["review_note"],
            "reviewer": "",
            "reviewed_at": "",
        }
        backfill_samples.append(sample)

    recommendations_doc = {
        "source_queue": str(REPORTS_DIR / "benchmark_review_queue_batch1.json"),
        "source_benchmark": str(DRAFT_PATH),
        "range": "81-100",
        "generated_for": "assisted second-pass review",
        "items": recommendation_items,
    }

    backfill_doc = {
        "generated_at": "2026-04-13T16:45:00Z",
        "source_report": str(RECOMMENDATIONS_PATH),
        "selection_policy": {
            "included_samples": "review tranche 81-100 from benchmark review queue",
            "review_mode": "assistant-prefilled pending confirmation",
            "alignment_note": "recommendations updated to reflect paradigm-signal, squeeze-signal, reverse-paradigm, and market-sentiment logic",
        },
        "summary": {
            "selected_total": len(backfill_samples),
            "range": "81-100",
        },
        "samples": backfill_samples,
    }

    RECOMMENDATIONS_PATH.write_text(json.dumps(recommendations_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    BACKFILL_PATH.write_text(json.dumps(backfill_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"generated {RECOMMENDATIONS_PATH}")
    print(f"generated {BACKFILL_PATH}")


if __name__ == "__main__":
    main()
