from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRAFT_PATH = BASE / "phase2.1_implementation" / "data" / "benchmark_samples_batch1_draft.json"
REPORTS_DIR = BASE / "reports"
RECOMMENDATIONS_PATH = REPORTS_DIR / "benchmark_review_61_80_recommendations.json"
BACKFILL_PATH = REPORTS_DIR / "benchmark_review_61_80_backfill_pending.json"

TRANCHE_IDS = [
    "B1D049", "B1D058", "B1D062", "B1D063", "B1D075", "B1D076", "B1D077", "B1D080", "B1D084", "B1D088",
    "B1D089", "B1D091", "B1D094", "B1D098", "B1D100", "B1D101", "B1D103", "B1D105", "B1D106", "B1D004",
]


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def main() -> None:
    draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    by_id = {sample["sample_id"]: sample for sample in draft["samples"]}

    recommendation_rules = {
        "B1D049": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team", "market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "Sunsetting Fortnite modes amid layoffs is both a workforce contraction signal and a product-portfolio retrenchment signal.",
            "review_note": "Keep as signal. This is stronger as team plus market, not team alone.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "team",
                    "signal_label": "retrenchment_signal",
                    "description": "Layoffs around Fortnite support a workforce contraction interpretation.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "retrenchment_signal",
                    "description": "Mode shutdowns indicate product portfolio retrenchment and demand or monetization reprioritization.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D058": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Trailer tease plus bonus content or quality-of-life update is routine promotional coverage, not a structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D062": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Game details and design teases remain feature or preview coverage, not a structural industry signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D063": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical", "market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "AI infrastructure causing component shortages and hardware price hikes is a direct technical-to-market spillover signal.",
            "review_note": "Keep as signal. This is a strong AI infrastructure externality signal and should include market impact.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "technical",
                    "signal_label": "ai_infrastructure_externality_signal",
                    "description": "Rapid AI infrastructure expansion is creating memory or component shortages that affect game-adjacent hardware makers.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "market",
                    "signal_label": "ai_infrastructure_externality_signal",
                    "description": "Component shortages are translating into consumer hardware price hikes and market pressure.",
                    "intensity_score": 7,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D075": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Use of generative AI for prototyping and placeholder iteration is still a meaningful production-pipeline signal even if final assets are replaced.",
            "review_note": "Keep as signal. This is a clean AI-in-production workflow signal.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D076": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "A single player ban and trading-drama story reads more like community incident coverage than a structural technical signal.",
            "review_note": "Downgrade to noise unless you explicitly want platform-governance micro-incidents in scope.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D077": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "This is mostly quality or narrative criticism, not a structural technical or business signal.",
            "review_note": "Downgrade to noise unless the article is being kept specifically as a reverse-signal around AI overproduction and product quality collapse.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D080": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "A major console price hike is a clear market signal and should not be typed as technical.",
            "review_note": "Keep as signal, but retag to market. This is hardware pricing pressure, not a technical shift.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "market",
                    "signal_label": "hardware_price_pressure_signal",
                    "description": "Sony's repeated PS5 price hikes indicate sustained pricing pressure and changing market conditions in console hardware.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                }
            ],
        },
        "B1D084": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team", "capital"],
            "review_focus": "type",
            "suggestion_confidence": "high",
            "one_line_reason": "Studio shutdown due to inability to raise funds is both a workforce loss signal and a capital squeeze signal.",
            "review_note": "Keep as signal. This should be tagged team plus capital.",
            "decision": "modified",
            "corrected_expected_signals": [
                {
                    "signal_type": "team",
                    "signal_label": "studio_shutdown_signal",
                    "description": "The studio shutdown represents direct team contraction and loss of operating capacity.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
                {
                    "signal_type": "capital",
                    "signal_label": "studio_shutdown_signal",
                    "description": "Failure to secure funding indicates capital-market tightening for game studios.",
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 5,
                    "entities": [],
                },
            ],
        },
        "B1D088": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["market"],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "If the article is grounded in concrete player-count performance, it can remain a market signal rather than pure feature coverage.",
            "review_note": "Keep as signal if you want strong product-demand evidence in scope.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D089": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["team"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Mass layoffs affecting 124 people are a direct and unambiguous workforce contraction signal.",
            "review_note": "Keep as signal.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D091": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Crafting streamlining and feature additions are routine game-update coverage, not structural signal material.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D094": {
            "recommended_bucket": "signal",
            "recommended_signal_types": ["technical"],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Replacing detected AI artwork after backlash is a strong technical-governance and reverse-paradigm signal.",
            "review_note": "Keep as signal. This clearly fits your reverse-paradigm logic.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D098": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "bucket",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "This mostly reads as criticism of story quality rather than a structural technical signal, despite adjacent AI context.",
            "review_note": "Downgrade to noise unless you are intentionally collecting quality-collapse companion samples around Crimson Desert.",
            "decision": "modified",
            "corrected_expected_signals": [],
        },
        "B1D100": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Hardware review coverage should remain a clean negative sample.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D101": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "New handheld unveiling is standard product announcement coverage, not a structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D103": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Review content should remain a negative benchmark sample.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D105": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Live-event tips and tomestone guidance are routine player-help content, not structural signals.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D106": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "medium-high",
            "one_line_reason": "Community showcase speculation about GTA 6 remains feature or preview-style content rather than a confirmed structural signal.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
        "B1D004": {
            "recommended_bucket": "noise",
            "recommended_signal_types": [],
            "review_focus": "confirm",
            "suggestion_confidence": "high",
            "one_line_reason": "Review content should remain a clean negative sample.",
            "review_note": "Keep as noise.",
            "decision": "accepted",
            "corrected_expected_signals": [],
        },
    }

    recommendation_items = []
    backfill_samples = []

    for rank, sample_id in enumerate(TRANCHE_IDS, start=61):
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
        "range": "61-80",
        "generated_for": "assisted second-pass review",
        "items": recommendation_items,
    }

    backfill_doc = {
        "generated_at": "2026-04-13T16:05:00Z",
        "source_report": str(RECOMMENDATIONS_PATH),
        "selection_policy": {
            "included_samples": "review tranche 61-80 from benchmark review queue",
            "review_mode": "assistant-prefilled pending confirmation",
            "alignment_note": "recommendations updated to reflect paradigm-signal, squeeze-signal, and reverse-paradigm logic",
        },
        "summary": {
            "selected_total": len(backfill_samples),
            "range": "61-80",
        },
        "samples": backfill_samples,
    }

    RECOMMENDATIONS_PATH.write_text(json.dumps(recommendations_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    BACKFILL_PATH.write_text(json.dumps(backfill_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"generated {RECOMMENDATIONS_PATH}")
    print(f"generated {BACKFILL_PATH}")


if __name__ == "__main__":
    main()
