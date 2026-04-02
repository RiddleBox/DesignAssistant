"""
Phase 2.2 Step A real evaluation samples.

Important:
- This file contains real-source evaluation samples.
- It is intended for first-round baseline observation, not gold-standard exhaustive labeling.
- It must remain separated from idealized synthetic samples.
"""


REAL_SAMPLE_DATA_NATURE = "real_source_eval_samples_first_round"
STEP_A_REAL_EVAL_CASES_VERSION = "v0.1"


def _source_signal(
    signal_id,
    signal_type,
    label,
    description,
    intensity_score,
    confidence_score,
    timeliness_score,
    what_changed=None,
    change_direction=None,
    affects=None,
):
    signal = {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "signal_label": label,
        "description": description,
        "intensity_score": intensity_score,
        "confidence_score": confidence_score,
        "timeliness_score": timeliness_score,
    }
    if what_changed:
        signal["logic_frame"] = {
            "what_changed": what_changed,
            "change_direction": change_direction or "unknown",
            "affects": affects or [],
        }
    return signal


STEP_A_REAL_EVAL_SAMPLES = [
    {
        "case_id": "step_a_real_cross_domain_mobile_distribution_001",
        "case_type": "cross_domain_positive",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "DMA anti-steering pressure, Android payment opening, and major mobile M&A capital movement should be interpretable as a cross-domain mobile distribution scenario.",
        "batch_size": 18,
        "signals": [
            _source_signal(
                "r1",
                "regulatory",
                "DMA anti-steering enforcement against Apple",
                "European Commission fines Apple for anti-steering violations and forces distribution rule changes.",
                8,
                10,
                6,
                "platform_policy",
                "tighten",
                ["mobile developers", "app store operators"],
            ),
            _source_signal(
                "r2",
                "market",
                "Fortnite returns with third-party payment opening",
                "Epic restores Fortnite to Google Play after antitrust ruling opens competing payment systems.",
                8,
                8,
                8,
                "distribution_access",
                "loosen",
                ["mobile game publishers", "platform challengers"],
            ),
            _source_signal(
                "r3",
                "capital",
                "Savvy acquires Moonton for $6B",
                "Savvy Games Group acquires Moonton in one of the largest game deals, signaling major mobile capital deployment.",
                8,
                9,
                8,
                "publisher_appetite",
                "increase",
                ["mobile studios", "regional publishers"],
            ),
            _source_signal(
                "n1",
                "market",
                "Routine patch note control",
                "A routine live game patch note with no industry-structure implication.",
                2,
                9,
                8,
            ),
        ],
        "expected_step_a": {
            "min_scenarios": 1,
            "expected_core_signal_ids": ["r1", "r2", "r3"],
            "forbidden_pairings": [["n1", "r1"], ["n1", "r2"], ["n1", "r3"]],
        },
    },
    {
        "case_id": "step_a_real_cross_domain_ai_workflow_001",
        "case_type": "cross_domain_positive",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "LLM-based NPC deployment plus a market-scale FPS validation signal should at least be surfaced as possible but not trivially merged only by AI/game theme.",
        "batch_size": 17,
        "signals": [
            _source_signal(
                "r1",
                "technical",
                "Gemini powers Dragon Quest X NPC dialogue",
                "Square Enix deploys Gemini-backed AI NPC conversations in a live MMORPG.",
                8,
                9,
                8,
                "npc_interaction_capability",
                "validate",
                ["live game operators", "rpg developers"],
            ),
            _source_signal(
                "r2",
                "market",
                "Delta Force reaches 50M DAU",
                "A Chinese FPS reaches 50 million DAU, validating strong demand in a core gameplay category.",
                8,
                8,
                8,
                "genre_demand",
                "increase",
                ["fps developers", "publishers"],
            ),
            _source_signal(
                "n1",
                "announcement",
                "DLC roadmap control",
                "A standard DLC roadmap announcement without structural industry meaning.",
                2,
                9,
                7,
            ),
        ],
        "expected_step_a": {
            "max_scenarios": 1,
            "forbidden_pairings": [["n1", "r1"], ["n1", "r2"]],
        },
    },
    {
        "case_id": "step_a_real_semantic_similarity_negative_001",
        "case_type": "semantic_similarity_negative",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "Routine content roadmap and routine patch-note style content should not be grouped into a logical scenario just because both are game updates.",
        "batch_size": 16,
        "signals": [
            _source_signal(
                "r1",
                "market",
                "Routine content roadmap",
                "A season pass roadmap announcement focused on story expansions and cosmetics.",
                2,
                9,
                7,
            ),
            _source_signal(
                "r2",
                "market",
                "Routine version update",
                "A standard live game version update announcement with rewards and tuning changes.",
                2,
                9,
                8,
            ),
        ],
        "expected_step_a": {
            "max_scenarios": 0,
            "forbidden_pairings": [["r1", "r2"]],
        },
    },
    {
        "case_id": "step_a_real_small_batch_direct_pass_001",
        "case_type": "small_batch_direct_pass",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A small batch of real-source signals should respect the <=15 direct-pass policy.",
        "batch_size": 4,
        "signals": [
            _source_signal(
                "r1",
                "capital",
                "Savvy acquires Moonton for $6B",
                "Savvy Games Group acquires Moonton in one of the largest game deals.",
                8,
                9,
                8,
                "publisher_appetite",
                "increase",
                ["mobile studios"],
            ),
            _source_signal(
                "r2",
                "technical",
                "Gemini powers Dragon Quest X NPC dialogue",
                "Square Enix deploys Gemini-backed AI NPC conversations in a live MMORPG.",
                8,
                9,
                8,
                "npc_interaction_capability",
                "validate",
                ["rpg developers"],
            ),
            _source_signal(
                "r3",
                "regulatory",
                "DMA anti-steering enforcement against Apple",
                "European Commission fines Apple for anti-steering violations.",
                8,
                10,
                6,
                "platform_policy",
                "tighten",
                ["mobile developers"],
            ),
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
        },
    },
]


def get_step_a_real_case(case_id: str):
    for case in STEP_A_REAL_EVAL_SAMPLES:
        if case["case_id"] == case_id:
            return case
    return None
