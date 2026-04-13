from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRAFT_PATH = BASE / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"
REPORTS_DIR = BASE / "reports"
RECOMMENDATIONS_PATH = REPORTS_DIR / "benchmark_review_41_60_recommendations.json"
BACKFILL_PATH = REPORTS_DIR / "benchmark_review_41_60_backfill_pending.json"

TRANCHE_IDS = [
    "B1D016", "B1D020", "B1D025", "B1D035", "B1D039", "B1D046", "B1D056", "B1D059", "B1D069", "B1D086",
    "B1D090", "B1D099", "B1D001", "B1D007", "B1D012", "B1D018", "B1D021", "B1D037", "B1D038", "B1D043",
]


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def main() -> None:
    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    by_id = {sample["sample_id"]: sample for sample in draft["samples"]}

    recommendation_rules = {
        "B1D016": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Celebratory anniversary artwork and DLC speculation remain routine fandom or promo coverage, not a structural industry signal.",
            "review_note": "Keep as noise. Anniversary celebration plus DLC speculation is standard promotional coverage.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D020": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "Leadership exits are organizational change signals and fit team better than technical.",
            "review_note": "Keep as signal, but retag to team because executive departures reflect org structure change.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "team",
                    "signal_label": "leadership_change_signal",
                    "description": "Leadership exits at Xbox indicate organizational restructuring rather than a technical shift.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                }
            ],
        },
        "B1D025": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Production cuts tied to weak U.S. sales are a clear squeeze signal in hardware demand and supply planning.",
            "review_note": "Keep as signal. This is a strong market squeeze indicator.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D035": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Actor interview and farewell framing is feature coverage, not a structural business or paradigm signal.",
            "review_note": "Keep as noise. Human-interest or cast-interview content is outside benchmark scope.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D039": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Fan-theory and movie age-rating speculation are entertainment-news noise, not structural game-industry change.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D046": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team"],
            "review_focus": "boundary",
            "suggestion_confidence": "medium",
            "one_line_reason": "It points at layoff consequences, but the piece may lean heavily editorial rather than reporting a fresh structural event.",
            "review_note": "Keep as signal only if you accept commentary that crystallizes layoff consequences as paradigm evidence; otherwise boundary.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D056": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team", "market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "Layoff analysis here functions as both workforce contraction evidence and a broader market squeeze signal.",
            "review_note": "Keep as signal. Multi-type makes sense if your taxonomy allows team plus market for paradigm squeeze interpretation.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "team",
                    "signal_label": "industry_squeeze_signal",
                    "description": "Epic layoffs are used as evidence of ongoing workforce contraction in the game industry.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "industry_squeeze_signal",
                    "description": "The article frames layoffs as evidence that market conditions and growth expectations are deteriorating across the industry.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D059": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Leak-followed-by-official-reveal coverage is standard announcement news rather than a structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D069": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "This is a strong paradox or compression signal: record sales coexist with falling stock sentiment and reduced production expectations.",
            "review_note": "Keep as signal. It captures a market contradiction rather than simple success reporting.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D086": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team"],
            "review_focus": "boundary",
            "suggestion_confidence": "medium",
            "one_line_reason": "The human impact case is meaningful, but it may function more as anecdotal fallout of an already-known layoff event.",
            "review_note": "Keep as signal if downstream worker fallout from layoffs is valid benchmark evidence; otherwise boundary.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D090": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team"],
            "review_focus": "boundary",
            "suggestion_confidence": "medium",
            "one_line_reason": "Similar to B1D086, this is strong layoff fallout evidence but may be derivative of an already captured event.",
            "review_note": "Keep as signal if second-order worker impact belongs in scope; otherwise boundary.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D099": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Hands-on multiplayer impressions are review-style product coverage, not a structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D001": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["regulatory", "market"],
            "review_focus": "type",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "Settlement-driven return to Google Play is better understood as platform-regulatory distribution change than pure technical signal.",
            "review_note": "Keep as signal. Prefer regulatory as primary; include market if your taxonomy allows distribution impact.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "regulatory",
                    "signal_label": "platform_settlement_signal",
                    "description": "The Epic-Google settlement changes platform access and distribution conditions for Fortnite on Google Play.",
                    "intensity_score": 7,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "platform_settlement_signal",
                    "description": "Return to Google Play materially affects market access and player distribution reach.",
                    "intensity_score": 6,
                    "confidence_score": 7,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D007": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market"],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "A price-cut driven player surge is still a market signal if your benchmark includes demand elasticity and long-tail monetization effects.",
            "review_note": "Keep as signal if you accept concrete market response signals, not just strategic events.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D012": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Game update and controversy framing still reads as standard live-service or content update coverage.",
            "review_note": "Keep as noise unless the full article contains a concrete business policy shift.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D018": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Undisclosed genAI asset use followed by an audit is a strong technical governance and AI-boundary signal.",
            "review_note": "Keep as signal. This also fits reverse-paradigm or AI-boundary logic.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D021": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Discount recommendation and niche game praise are standard consumer-facing feature content.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D037": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Review content should remain a clean negative benchmark sample.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D038": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "high",
            "one_line_reason": "A commemorative music video is promotional nostalgia content, not a technical or structural industry signal.",
            "review_note": "Downgrade to noise. This is promo/media content, not a structural signal.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D043": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical", "market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "The DLSS 5 dispute is not just a market reaction; it is a technical adoption conflict with market consequences.",
            "review_note": "Keep as signal. This is a technical controversy with clear market and developer-ecosystem implications.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "technical",
                    "signal_label": "reverse_paradigm_signal",
                    "description": "Developer backlash against DLSS 5 shows resistance to an AI-assisted graphics paradigm and questions its value.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "reverse_paradigm_signal",
                    "description": "Calls to stop collaborating and tank sales show the technical dispute spilling into market and ecosystem behavior.",
                    "intensity_score": 7,
                    "confidence_score": 7,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
    }

    recommendation_items = []
    backfill_samples = []

    for rank, sample_id in enumerate(TRANCHE_IDS, start=41):
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
        "range": "41-60",
        "generated_for": "assisted second-pass review",
        "items": recommendation_items,
    }

    backfill_doc = {
        "generated_at": "2026-04-13T15:42:45Z",
        "source_report": str(RECOMMENDATIONS_PATH),
        "selection_policy": {
            "included_samples": "review tranche 41-60 from benchmark review queue",
            "review_mode": "assistant-prefilled pending confirmation",
            "alignment_note": "recommendations updated to reflect paradigm-signal, squeeze-signal, and reverse-paradigm logic",
        },
        "summary": {
            "selected_total": len(backfill_samples),
            "range": "41-60",
        },
        "samples": backfill_samples,
    }

    RECOMMENDATIONS_PATH.write_text(json.dumps(recommendations_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    BACKFILL_PATH.write_text(json.dumps(backfill_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"generated {RECOMMENDATIONS_PATH}")
    print(f"generated {BACKFILL_PATH}")


if __name__ == "__main__":
    main()
