from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "reports" / "benchmark_review_queue_batch1.json"
DEFAULT_OUTPUT = BASE_DIR / "reports" / "benchmark_review_assisted_pass1.json"

TEAM_KEYWORDS = (
    "layoff",
    "lays off",
    "laid off",
    "job cuts",
    "cuts jobs",
    "downsizes",
    "downsizes",
    "closing their doors",
    "shuts down",
    "shutdown",
    "closing",
    "closes",
    "staff",
    "employees",
)

CAPITAL_KEYWORDS = (
    "acquire",
    "acquires",
    "acquisition",
    "buy",
    "buys",
    "investment",
    "funding",
    "deal",
    "stake",
    "merger",
)

TECHNICAL_KEYWORDS = (
    "ai",
    "genai",
    "generative ai",
    "tool",
    "tools",
    "pipeline",
    "technology",
    "engine",
    "dlss",
)

MARKET_KEYWORDS = (
    "sales",
    "sold",
    "copies",
    "player base",
    "concurrent",
    "launch",
    "price",
    "demand",
)

NOISE_PATTERNS = (
    "preview",
    "announced during",
    "showcase",
    "special celebratory artwork",
    "anniversary",
    "review",
    "dlc",
    "expansion announced",
    "coming later this year",
    "new info",
    "fans",
)

NON_GAME_PATTERNS = (
    "missing_game_context",
    "non_game_context",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _detect_signal_type(title: str, content: str) -> str | None:
    text = f"{title} {content}".lower()
    if _contains_any(text, TEAM_KEYWORDS):
        return "team"
    if _contains_any(text, CAPITAL_KEYWORDS):
        return "capital"
    if _contains_any(text, TECHNICAL_KEYWORDS):
        return "technical"
    if _contains_any(text, MARKET_KEYWORDS):
        return "market"
    return None


def _build_suggestion(row: dict[str, Any]) -> dict[str, Any] | None:
    title = str(row.get("title") or "")
    content = str(row.get("content_preview") or "")
    reasons = [str(item) for item in (row.get("reasons") or [])]
    draft_bucket = str(row.get("draft_bucket") or "")
    draft_signal_types = [str(item) for item in (row.get("draft_signal_types") or [])]
    confidence_band = str(row.get("confidence_band") or "")
    score_boundary = int(row.get("score_boundary") or 0)
    score_signal = int(row.get("score_signal") or 0)
    score_noise = int(row.get("score_noise") or 0)

    suggested_bucket = draft_bucket
    suggested_signal_types = list(draft_signal_types)
    issue_tags: list[str] = []
    rationale: list[str] = []
    priority_score = 0

    detected_type = _detect_signal_type(title, content)

    if any(tag in reasons for tag in NON_GAME_PATTERNS):
        issue_tags.append("non_game_context")
        rationale.append("Source looks outside game-industry scope and should be manually confirmed.")
        priority_score += 5
        if draft_bucket == "signal":
            suggested_bucket = "noise"
            issue_tags.append("possible_false_positive")
            rationale.append("Draft is signal but queue reasons explicitly indicate non-game or missing game context.")
            priority_score += 4

    if _contains_any(title + " " + content, NOISE_PATTERNS) and draft_bucket == "signal":
        suggested_bucket = "noise"
        issue_tags.append("announcement_or_feature_noise")
        rationale.append("Title/content matches common non-structural announcement or feature-news patterns.")
        priority_score += 4

    if draft_bucket == "signal" and detected_type and draft_signal_types and detected_type not in draft_signal_types:
        suggested_signal_types = [detected_type]
        issue_tags.append("possible_type_mismatch")
        rationale.append(f"Draft signal type looks suspicious; keyword evidence leans toward `{detected_type}`.")
        priority_score += 3

    if draft_bucket == "signal" and score_boundary >= 3:
        issue_tags.append("high_boundary_tension")
        rationale.append("High boundary score suggests the sample is signal-like but still ambiguous.")
        priority_score += 3

    if draft_bucket == "signal" and score_noise >= max(4, score_signal - 4):
        issue_tags.append("signal_noise_tension")
        rationale.append("Signal and noise evidence are relatively close; worth human confirmation.")
        priority_score += 2

    if draft_bucket == "noise" and detected_type and score_signal >= 4 and score_noise <= 6:
        issue_tags.append("possible_false_negative")
        rationale.append("Noise sample still shows some structural signal cues and deserves a quick second look.")
        priority_score += 2

    if confidence_band != "high":
        priority_score += 1

    if not issue_tags:
        return None

    review_focus = "bucket" if suggested_bucket != draft_bucket else "type" if suggested_signal_types != draft_signal_types else "confirm"

    return {
        "sample_id": row.get("sample_id"),
        "title": title,
        "source_name": row.get("source_name"),
        "published_at": row.get("published_at"),
        "source_url": row.get("source_url"),
        "draft_bucket": draft_bucket,
        "suggested_bucket": suggested_bucket,
        "draft_signal_types": draft_signal_types,
        "suggested_signal_types": suggested_signal_types,
        "manual_review_priority": row.get("manual_review_priority"),
        "confidence_band": confidence_band,
        "score_signal": score_signal,
        "score_noise": score_noise,
        "score_boundary": score_boundary,
        "issue_tags": issue_tags,
        "review_focus": review_focus,
        "priority_score": priority_score,
        "rationale": rationale,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an assisted first-pass review suggestion list from the benchmark review queue.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to the flattened review queue JSON.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to the assisted review suggestion JSON.")
    parser.add_argument("--top-n", type=int, default=40, help="Maximum number of highest-priority suggestions to include in the priority shortlist.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    data = _load_json(input_path)
    rows = data.get("rows") or []

    suggestions = [item for item in (_build_suggestion(row) for row in rows) if item is not None]
    suggestions.sort(key=lambda item: (-int(item["priority_score"]), str(item.get("sample_id") or "")))

    issue_counter = Counter(tag for item in suggestions for tag in item.get("issue_tags") or [])
    shortlist = suggestions[: max(0, args.top_n)]

    output = {
        "source_queue": str(input_path),
        "total_rows": len(rows),
        "suggestion_count": len(suggestions),
        "priority_shortlist_count": len(shortlist),
        "issue_tag_counts": dict(issue_counter),
        "priority_shortlist": shortlist,
        "all_suggestions": suggestions,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Total rows           : {len(rows)}")
    print(f"Suggestion count     : {len(suggestions)}")
    print(f"Priority shortlist   : {len(shortlist)}")
    print(f"Output               : {output_path}")


if __name__ == "__main__":
    main()
