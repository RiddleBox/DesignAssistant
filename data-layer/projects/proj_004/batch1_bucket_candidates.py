from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DESIGN_ASSISTANT_ROOT = BASE_DIR.parent.parent.parent
INCOMING_DIR = DESIGN_ASSISTANT_ROOT / "background" / "real_intel_samples" / "incoming"
REPORTS_DIR = BASE_DIR / "reports"

SIGNAL_PATTERNS = {
    "capital": [
        r"\bacqui(?:re|res|red|sition)\b",
        r"\binvest(?:s|ment|ed|ing)?\b",
        r"\bfunding\b",
        r"\braises?\b",
        r"\bvalu(?:ation|ed)\b",
        r"\bstake\b",
        r"\bbuyout\b",
        r"\bmerger\b",
        r"\bipo\b",
    ],
    "team": [
        r"\blayoffs?\b",
        r"\blaid off\b",
        r"\bcuts? jobs\b",
        r"\bjob cuts\b",
        r"\bshutdown\b",
        r"\bshut down\b",
        r"\bclosure\b",
        r"\bclose(?:s|d)?\b",
        r"\bunion\b",
        r"\bstrike\b",
        r"\bappoint(?:s|ed|ment)?\b",
        r"\bsteps down\b",
        r"\bresigns?\b",
        r"\bexits?\b",
    ],
    "technical": [
        r"\bai\b",
        r"\bgenerative ai\b",
        r"\bgenai\b",
        r"\bllm\b",
        r"\bautomation\b",
        r"\btoolchain\b",
        r"\bworkflow\b",
        r"\bpipeline\b",
        r"\btechnology\b",
        r"\bengine\b",
        r"\bpartnership\b",
    ],
    "market": [
        r"\bsales\b",
        r"\brevenue\b",
        r"\bbookings\b",
        r"\bdau\b",
        r"\bmau\b",
        r"\bplayers?\b",
        r"\bwishlist\b",
        r"\bchart(?:s|ing)?\b",
        r"\bdemand\b",
        r"\bprice\b",
        r"\bspending\b",
    ],
    "regulatory": [
        r"\blawsuit\b",
        r"\bsues?\b",
        r"\bregulat(?:ion|ory|or)\b",
        r"\bfine[sd]?\b",
        r"\bdma\b",
        r"\bantitrust\b",
        r"\blegal\b",
        r"\bcourt\b",
        r"\bban(?:ned|s)?\b",
    ],
}

NOISE_PATTERNS = [
    r"\breview\b",
    r"\bpreview\b",
    r"\bimpressions\b",
    r"\binterview\b",
    r"\bguide\b",
    r"\bwalkthrough\b",
    r"\b99 cents\b",
    r"\bdiscount\b",
    r"\bon sale\b",
    r"\banniversary\b",
    r"\bcelebrat(?:e|es|ing)\b",
    r"\btrailer\b",
    r"\bscreenshot\b",
    r"\bcosmetic\b",
    r"\bskin\b",
    r"\broadmap\b",
    r"\bpatch notes?\b",
    r"\bupdate notes?\b",
    r"\bevent\b",
    r"\besports\b",
    r"\bturns one\b",
    r"\bbirthday\b",
    r"\bworth playing\b",
    r"\bfan theory\b",
    r"\beverything announced\b",
    r"\bshowcase\b",
    r"\bround[- ]?up\b",
    r"\bplayers have\b",
    r"\baccidentally confirms\b",
    r"\bon the hunt\b",
    r"\buseless bottles\b",
    r"\bchoice-driven rpg\b",
]

BOUNDARY_PATTERNS = [
    r"\breport\b",
    r"\brumou?r\b",
    r"\binsider\b",
    r"\bcould\b",
    r"\bmay\b",
    r"\bmight\b",
    r"\bplans? to\b",
    r"\bworking on\b",
    r"\baiming to\b",
    r"\bexpected to\b",
    r"\baccording to\b",
]

LOW_INFORMATION_PATTERNS = [
    r"\bread more\b",
    r"\bclick here\b",
    r"\bwatch now\b",
    r"\bhere'?s what\b",
]

NON_GAME_PATTERNS = [
    r"\btesla\b",
    r"\bopenai\b",
    r"\bmeta\b",
    r"\bgoogle cloud\b",
    r"\bamazon\b",
    r"\bnvidia\b",
]

GAME_CONTEXT_PATTERNS = [
    r"\bgame\b",
    r"\bgames\b",
    r"\bgaming\b",
    r"\bstudio\b",
    r"\bdeveloper\b",
    r"\bpublisher\b",
    r"\bsteam\b",
    r"\bxbox\b",
    r"\bplaystation\b",
    r"\bnintendo\b",
    r"\bmobile game\b",
    r"\blive service\b",
]

HIGH_VALUE_ENTITIES = [
    "ubisoft", "sony", "microsoft", "xbox", "playstation", "nintendo",
    "tencent", "netease", "epic", "capcom", "square enix", "embracer",
    "savvy", "disney", "apple", "google", "meta", "unity",
]


@dataclass
class BucketResult:
    file_name: str
    source_id: str
    title: str
    source_name: str
    published_at: str
    signal_type_hint: str
    candidate_bucket: str
    recommended_set: str
    confidence_band: str
    score_signal: int
    score_noise: int
    score_boundary: int
    manual_review_priority: str
    reasons: list[str]
    source_url: str
    content_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "source_id": self.source_id,
            "title": self.title,
            "source_name": self.source_name,
            "published_at": self.published_at,
            "signal_type_hint": self.signal_type_hint,
            "candidate_bucket": self.candidate_bucket,
            "recommended_set": self.recommended_set,
            "confidence_band": self.confidence_band,
            "score_signal": self.score_signal,
            "score_noise": self.score_noise,
            "score_boundary": self.score_boundary,
            "manual_review_priority": self.manual_review_priority,
            "reasons": self.reasons,
            "source_url": self.source_url,
            "content_excerpt": self.content_excerpt,
        }


def _matches_any(patterns: list[str], text: str) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def _count_signal_hits(text: str) -> tuple[int, list[str]]:
    total = 0
    reasons: list[str] = []
    for signal_type, patterns in SIGNAL_PATTERNS.items():
        hits = _matches_any(patterns, text)
        if hits:
            total += len(hits)
            reasons.append(f"signal_pattern:{signal_type}:{len(hits)}")
    return total, reasons


def _shorten(text: str, limit: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _recommended_set(bucket: str) -> str:
    if bucket == "signal":
        return "main_baseline_candidate"
    if bucket == "boundary":
        return "boundary_observation_candidate"
    return "noise_suppression_candidate"


def _confidence_band(top_score: int, second_score: int) -> str:
    gap = top_score - second_score
    if gap >= 4:
        return "high"
    if gap >= 2:
        return "medium"
    return "low"


def _review_priority(bucket: str, confidence_band: str, reasons: list[str]) -> str:
    if bucket == "boundary":
        return "high"
    if confidence_band == "low":
        return "high"
    if any(reason.startswith("non_game_context") for reason in reasons):
        return "high"
    if bucket == "signal" and confidence_band == "medium":
        return "medium"
    return "low"


def classify_sample(file_name: str, data: dict[str, Any]) -> BucketResult:
    title = str(data.get("title") or "")
    content = str(data.get("content") or "")
    source_name = str(data.get("source_name") or "")
    source_url = str(data.get("source_url") or "")
    published_at = str(data.get("published_at") or "")
    ingestion_meta = data.get("ingestion_meta") or {}
    signal_type_hint = str(ingestion_meta.get("signal_type_hint") or "unknown").lower()

    text = " ".join([title, content, source_name]).lower()
    reasons: list[str] = []

    signal_score = 0
    noise_score = 0
    boundary_score = 0

    signal_hits, signal_reasons = _count_signal_hits(text)
    signal_score += signal_hits * 2
    reasons.extend(signal_reasons)

    if signal_type_hint in SIGNAL_PATTERNS:
        signal_score += 1
        reasons.append(f"hint:{signal_type_hint}")

    high_value_hits = [entity for entity in HIGH_VALUE_ENTITIES if entity in text]
    if high_value_hits:
        signal_score += min(len(high_value_hits), 3)
        reasons.append(f"high_value_entities:{','.join(high_value_hits[:3])}")

    game_context_hits = _matches_any(GAME_CONTEXT_PATTERNS, text)
    if game_context_hits:
        signal_score += 1
        reasons.append("game_context")
    else:
        noise_score += 2
        reasons.append("missing_game_context")

    noise_hits = _matches_any(NOISE_PATTERNS, text)
    if noise_hits:
        noise_score += len(noise_hits) * 2
        reasons.append(f"noise_patterns:{len(noise_hits)}")

    low_information_hits = _matches_any(LOW_INFORMATION_PATTERNS, text)
    if low_information_hits:
        noise_score += 2
        reasons.append("low_information_excerpt")

    boundary_hits = _matches_any(BOUNDARY_PATTERNS, text)
    if boundary_hits:
        boundary_score += len(boundary_hits) * 2
        reasons.append(f"boundary_patterns:{len(boundary_hits)}")

    non_game_hits = _matches_any(NON_GAME_PATTERNS, text)
    if non_game_hits and not game_context_hits:
        noise_score += 3
        reasons.append("non_game_context")

    if any(token in text for token in ["reportedly", "according to a new report", "insider gaming"]):
        boundary_score += 2
        reasons.append("rumor_or_report_sourcing")

    if re.search(r"\b\d+(?:\.\d+)?\s*(?:m|million|b|billion|%)\b", text, flags=re.IGNORECASE):
        signal_score += 2
        reasons.append("concrete_numbers")

    if len(content) < 100:
        noise_score += 2
        reasons.append("very_short_excerpt")
    elif len(content) < 180:
        boundary_score += 1
        reasons.append("short_excerpt")

    if "read more" in text:
        noise_score += 1
        reasons.append("truncated_article")

    announcement_style = any(word in text for word in ["announced", "launches", "comes to", "available now"])
    if announcement_style:
        boundary_score += 1
        reasons.append("announcement_style")

    if announcement_style and (low_information_hits or "read more" in text or len(content) < 180):
        noise_score += 3
        reasons.append("shallow_announcement_penalty")

    if any(word in text for word in ["layoff", "laid off", "acquisition", "shutdown", "lawsuit", "antitrust", "investment"]):
        signal_score += 2
        reasons.append("structural_change_keywords")

    scores = {
        "signal": signal_score,
        "noise": noise_score,
        "boundary": boundary_score,
    }
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    bucket = ordered[0][0]
    confidence_band = _confidence_band(ordered[0][1], ordered[1][1])

    if bucket == "signal" and boundary_score >= signal_score - 1:
        bucket = "boundary"
        reasons.append("promoted_to_boundary_due_to_close_scores")
    if bucket == "signal" and noise_score >= signal_score:
        bucket = "boundary"
        reasons.append("promoted_to_boundary_due_to_noise_tension")
    if bucket == "noise" and signal_score >= noise_score - 1 and signal_score >= 4:
        bucket = "boundary"
        reasons.append("promoted_to_boundary_due_to_signal_evidence")

    return BucketResult(
        file_name=file_name,
        source_id=str(data.get("source_id") or file_name.removesuffix(".json")),
        title=title,
        source_name=source_name,
        published_at=published_at,
        signal_type_hint=signal_type_hint,
        candidate_bucket=bucket,
        recommended_set=_recommended_set(bucket),
        confidence_band=confidence_band,
        score_signal=signal_score,
        score_noise=noise_score,
        score_boundary=boundary_score,
        manual_review_priority=_review_priority(bucket, confidence_band, reasons),
        reasons=reasons,
        source_url=source_url,
        content_excerpt=_shorten(content),
    )


def generate_candidates(sample_dir: Path, limit: int | None = None) -> dict[str, Any]:
    files = sorted(sample_dir.glob("*.json"))
    if limit is not None:
        files = files[:limit]

    rows: list[BucketResult] = []
    for path in files:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        rows.append(classify_sample(path.name, data))

    bucket_counter = Counter(row.candidate_bucket for row in rows)
    priority_counter = Counter(row.manual_review_priority for row in rows)

    shortlist = {
        bucket: [
            row.to_dict()
            for row in sorted(
                (r for r in rows if r.candidate_bucket == bucket),
                key=lambda r: (
                    0 if r.manual_review_priority == "high" else 1 if r.manual_review_priority == "medium" else 2,
                    0 if r.confidence_band == "low" else 1 if r.confidence_band == "medium" else 2,
                    -max(r.score_signal, r.score_noise, r.score_boundary),
                    r.file_name,
                ),
            )[:20]
        ]
        for bucket in ("signal", "boundary", "noise")
    }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_dir": str(sample_dir),
        "total_samples": len(rows),
        "bucket_counts": dict(bucket_counter),
        "review_priority_counts": dict(priority_counter),
        "rules_version": "batch1_bucket_candidates_v1",
        "notes": [
            "This is a heuristic review artifact, not the formal benchmark truth source.",
            "Formal truth should still be consolidated into phase2.1_implementation/data/benchmark_samples.json after human review.",
            "Boundary samples and low-confidence candidates should be reviewed first.",
        ],
        "shortlist": shortlist,
        "rows": [row.to_dict() for row in rows],
    }


def write_outputs(report: dict[str, Any], out_prefix: Path) -> tuple[Path, Path]:
    json_path = out_prefix.with_suffix(".json")
    csv_path = out_prefix.with_suffix(".csv")

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "file_name",
        "source_id",
        "title",
        "source_name",
        "published_at",
        "signal_type_hint",
        "candidate_bucket",
        "recommended_set",
        "confidence_band",
        "manual_review_priority",
        "score_signal",
        "score_noise",
        "score_boundary",
        "reasons",
        "source_url",
        "content_excerpt",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["rows"]:
            row = dict(row)
            row["reasons"] = " | ".join(row.get("reasons") or [])
            writer.writerow(row)

    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Batch 1 signal/noise/boundary candidate buckets for incoming samples.")
    parser.add_argument("--sample-dir", default=str(INCOMING_DIR), help="Directory containing incoming JSON samples.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N samples.")
    args = parser.parse_args()

    sample_dir = Path(args.sample_dir)
    if not sample_dir.exists():
        raise SystemExit(f"Sample directory not found: {sample_dir}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_prefix = REPORTS_DIR / f"{timestamp}_batch1_bucket_candidates"

    report = generate_candidates(sample_dir=sample_dir, limit=args.limit)
    json_path, csv_path = write_outputs(report, out_prefix)

    print(f"Processed samples : {report['total_samples']}")
    print(f"Bucket counts     : {report['bucket_counts']}")
    print(f"Review priorities : {report['review_priority_counts']}")
    print(f"JSON artifact     : {json_path}")
    print(f"CSV artifact      : {csv_path}")


if __name__ == "__main__":
    main()
