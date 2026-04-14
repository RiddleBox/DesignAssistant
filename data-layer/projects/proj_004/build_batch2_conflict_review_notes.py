from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DRAFT = BASE_DIR / "phase2.1_implementation" / "data" / "benchmark_samples_batch2_draft.json"
OUTPUT_MD = BASE_DIR / "reports" / "batch2_conflict_review_notes.md"

USER_TEXT = """B2D001	Signal	Team
B2D004	Signal	market
B2D008	Signal	market
B2D009	Signal	market
B2D012	Signal	tech
B2D015	Signal	Tech
B2D020	Signal	tech
B2D022	Signal	tech
B2D024	Signal	tech
B2D028	Signal	team
B2D031	Signal	Capital
B2D032	Signal	Capital
B2D039	Signal	team
B2D041	Signal	team
B2D050	Signal	Market
B2D051	Signal	Tech
B2D053	Signal	Tech
B2D054	Signal	Tech
B2D056	Signal	Capital
B2D057	Signal	Market
B2D070	Signal	Tech
B2D086	Signal	Market
B2D099	Signal	Tech
B2D100	Signal	Tech
B2D101	Signal	Market
B2D102	Signal	Market
B2D112	Signal	Market
B2D115	Signal	Tech
B2D121	Signal	Capital
B2D132	Signal	Tech
B2D140	Signal	Market
B2D146	Sigal	Tech
B2D150	Signal	Tech
B2D152	Signal	Market
B2D161	Signal	Team/Capital
B2D166	Signal	Capital
B2D173	Signal	Market"""

TYPE_MAP = {
    "team": "team",
    "capital": "capital",
    "market": "market",
    "tech": "technical",
    "technical": "technical",
    "regulatory": "regulatory",
}

KEYWORD_MAP = {
    "team": ["layoff", "laid off", "job cuts", "staff", "employees", "executive", "founder", "ceo", "leadership", "union"],
    "capital": ["funding", "investment", "investor", "acquisition", "acquire", "merger", "stake", "valuation", "buyout"],
    "technical": ["ai", "genai", "generative ai", "tool", "engine", "pipeline", "technology", "model", "gpu", "dlss"],
    "market": ["sales", "sold", "copies", "price", "demand", "launch", "revenue", "market", "players", "steam"],
    "regulatory": ["regulator", "antitrust", "lawsuit", "court", "settlement", "policy", "ban", "compliance"],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_user_labels(raw: str) -> dict[str, dict[str, list[str] | str]]:
    result: dict[str, dict[str, list[str] | str]] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"\s+", line)
        sample_id = parts[0].strip()
        bucket = (parts[1] if len(parts) > 1 else "").strip().lower()
        signal_types = (parts[2] if len(parts) > 2 else "").strip()

        if bucket.startswith("sig"):
            bucket = "signal"

        normalized_types: list[str] = []
        if signal_types:
            for raw_type in re.split(r"[/,;]+", signal_types.lower()):
                raw_type = raw_type.strip()
                if not raw_type:
                    continue
                normalized_types.append(TYPE_MAP.get(raw_type, raw_type))

        result[sample_id] = {
            "bucket": bucket or "signal",
            "types": sorted(set(normalized_types)),
        }

    return result


def get_draft_bucket(sample: dict) -> str:
    bucket = str(((sample.get("draft_meta") or {}).get("candidate_bucket") or "")).lower()
    if bucket in {"signal", "noise"}:
        return bucket
    signals = ((sample.get("annotation") or {}).get("expected_signals") or [])
    return "signal" if signals else "noise"


def get_draft_types(sample: dict) -> list[str]:
    signals = ((sample.get("annotation") or {}).get("expected_signals") or [])
    types = []
    for item in signals:
        signal_type = str(item.get("signal_type") or "").strip().lower()
        if signal_type:
            types.append(signal_type)
    return sorted(set(types))


def get_excerpt(sample: dict, limit: int) -> str:
    text = str(sample.get("content") or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:limit]


def get_surface_cues(sample: dict) -> str:
    title = str(sample.get("title") or "").lower()
    content = str(sample.get("content") or "").lower()
    text = f"{title} {content}"

    hits = []
    for signal_type, patterns in KEYWORD_MAP.items():
        matched = [pattern for pattern in patterns if pattern in text]
        if matched:
            hits.append(f"{signal_type}: {', '.join(matched[:4])}")

    if not hits:
        return "Surface cues are weak, which is exactly why this sample needs second-pass human review."

    return "Surface cues I would use on a quick pass: " + "; ".join(hits) + "."


def build_reason_lines(sample: dict) -> list[str]:
    draft_meta = sample.get("draft_meta") or {}
    reasons = [str(item) for item in (draft_meta.get("reasons") or [])]
    draft_bucket = get_draft_bucket(sample)
    draft_types = get_draft_types(sample)

    lines = []
    if draft_bucket == "signal":
        lines.append("I currently lean to **signal** because the draft was promoted into the positive set rather than filtered out as routine news/noise.")
    else:
        lines.append("I currently lean to **noise** because the draft did not retain a structural signal annotation after the candidate-to-draft pass.")

    if draft_types:
        lines.append("Current draft type guess: `" + ", ".join(draft_types) + "`. This comes from the existing `expected_signals` annotation in the draft.")

    lines.append(
        "Heuristic scores: "
        f"signal={draft_meta.get('score_signal')}, "
        f"noise={draft_meta.get('score_noise')}, "
        f"boundary={draft_meta.get('score_boundary')}."
    )

    if reasons:
        lines.append("Candidate reasons carried from earlier bucketing: " + "; ".join(reasons) + ".")

    lines.append(get_surface_cues(sample))
    return lines


def append_sample_section(lines: list[str], sample_id: str, sample: dict, user_bucket: str, user_types: list[str], heading_text: str) -> None:
    draft_bucket = get_draft_bucket(sample)
    draft_types = get_draft_types(sample)

    lines.append(f"### {sample_id}")
    lines.append("")
    lines.append(f"- 标题：{sample.get('title', '')}")
    lines.append(f"- 你的判断：`{user_bucket}` / `{', '.join(user_types) if user_types else '-'}`")
    lines.append(f"- 当前 draft：`{draft_bucket}` / `{', '.join(draft_types) if draft_types else '-'}`")
    lines.append(f"- 来源：{sample.get('source_name', '')} | {sample.get('published_at', '')}")
    if sample.get("source_url"):
        lines.append(f"- 链接：{sample.get('source_url')}")

    excerpt = get_excerpt(sample, 380)
    if excerpt:
        lines.append(f"- 摘要：{excerpt}")

    lines.append(f"- {heading_text}")
    for reason in build_reason_lines(sample):
        lines.append(f"  - {reason}")
    lines.append("")


def main() -> None:
    data = load_json(INPUT_DRAFT)
    samples = {sample["sample_id"]: sample for sample in (data.get("samples") or [])}
    user_labels = parse_user_labels(USER_TEXT)

    explicit_conflicts = []
    draft_signal_but_user_omitted = []

    for sample_id, user_label in user_labels.items():
        sample = samples.get(sample_id)
        if not sample:
            continue
        draft_bucket = get_draft_bucket(sample)
        draft_types = get_draft_types(sample)
        if draft_bucket != "signal" or draft_types != user_label["types"]:
            explicit_conflicts.append((sample_id, sample, user_label))

    for sample_id, sample in samples.items():
        if sample_id in user_labels:
            continue
        if get_draft_bucket(sample) == "signal":
            draft_signal_but_user_omitted.append(sample_id)

    explicit_conflicts.sort(key=lambda item: item[0])
    draft_signal_but_user_omitted.sort()

    lines: list[str] = []
    lines.append("## Batch2 差异样本二次复核说明")
    lines.append("")
    lines.append("这份文件用于解释当前 draft 与人工首轮判断之间的差异，帮助进行二次复核。")
    lines.append("")
    lines.append("- 人工规则：用户列出的样本视为 `signal`，其余默认视为 `noise`")
    lines.append("- 当前 draft 来源：`benchmark_samples_batch2_draft.json`")
    lines.append("- 说明目标：把“为什么 draft 会这样判”先说清楚，再决定是否改成 `signal` 或调整类型")
    lines.append("")
    lines.append("## A. 用户判为 signal，但 draft 不同")
    lines.append("")

    for sample_id, sample, user_label in explicit_conflicts:
        append_sample_section(
            lines,
            sample_id,
            sample,
            str(user_label["bucket"]),
            list(user_label["types"]),
            "我为什么会这样倾向：",
        )

    lines.append("## B. draft 判为 signal，但用户本轮未列出（按当前规则默认应为 noise）")
    lines.append("")
    lines.append("这些样本不是说 draft 一定正确，而是它们在当前启发式中被保留为 signal；如果下面理由没有说服力，就应降为 noise。")
    lines.append("")

    for sample_id in draft_signal_but_user_omitted:
        sample = samples[sample_id]
        append_sample_section(
            lines,
            sample_id,
            sample,
            "noise",
            [],
            "我为什么暂时没把它降成 noise：",
        )

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"generated {OUTPUT_MD}")


if __name__ == "__main__":
    main()
