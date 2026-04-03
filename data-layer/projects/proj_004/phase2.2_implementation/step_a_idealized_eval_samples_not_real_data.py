"""
Phase 2.2 Step A idealized evaluation samples.

Important:
- This file contains idealized synthetic test samples.
- It is NOT real production data.
- It is intended for controlled Step A evaluation only.
"""


def _signal(
    signal_id,
    signal_type,
    label,
    description,
    intensity_score,
    confidence_score=8,
    timeliness_score=7,
):
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "signal_label": label,
        "description": description,
        "intensity_score": intensity_score,
        "confidence_score": confidence_score,
        "timeliness_score": timeliness_score,
    }


IDEALIZED_SAMPLE_DATA_NATURE = "idealized_synthetic_test_samples_not_real_data"


STEP_A_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA = [
    {
        "case_id": "step_a_pos_cross_domain_001",
        "case_type": "cross_domain_positive",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "Regulatory pressure + capital readiness + developer migration should form one logical scenario.",
        "batch_size": 18,
        "signals": [
            _signal(
                "s1",
                "regulatory",
                "EU DMA pressure on mobile platform",
                "EU regulators increase compliance pressure on a major mobile platform, raising distribution friction and review uncertainty.",
                8,
                9,
                8,
            ),
            _signal(
                "s2",
                "capital",
                "Publisher announces M&A fund",
                "A major publisher sets up a dedicated acquisition fund for mobile studios facing distribution turbulence.",
                7,
                8,
                7,
            ),
            _signal(
                "s3",
                "market",
                "Indie developers shift away from incumbent channel",
                "Developer migration away from the incumbent mobile distribution channel reaches a two-year high.",
                7,
                8,
                8,
            ),
            _signal(
                "n1",
                "technical",
                "Minor engine UI patch",
                "A game engine ships a small editor usability patch unrelated to distribution or consolidation.",
                3,
                8,
                5,
            ),
        ],
        "expected_step_a": {
            "min_scenarios": 1,
            "expected_core_signal_ids": ["s1", "s2", "s3"],
            "forbidden_pairings": [["n1", "s1"], ["n1", "s2"], ["n1", "s3"]],
        },
    },
    {
        "case_id": "step_a_pos_cross_domain_002",
        "case_type": "cross_domain_positive",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "AI tool cost decline + talent movement + adoption signal should be grouped as one scenario.",
        "batch_size": 19,
        "signals": [
            _signal(
                "s1",
                "technical",
                "Game AI tooling cost drops",
                "A major AI tooling vendor cuts inference cost for real-time game content workflows by more than half.",
                8,
                9,
                9,
            ),
            _signal(
                "s2",
                "team",
                "Engine company forms internal AI workflow team",
                "A top engine company hires a dedicated team to integrate AI-assisted creation into its editor pipeline.",
                7,
                8,
                8,
            ),
            _signal(
                "s3",
                "market",
                "Indie studios adopt AI content workflows",
                "A yearly developer survey shows AI-assisted asset and code workflows doubling among indie studios.",
                7,
                8,
                7,
            ),
            _signal(
                "n1",
                "capital",
                "Console accessory startup seed round",
                "An unrelated console accessory startup closes a small seed round.",
                4,
                7,
                5,
            ),
        ],
        "expected_step_a": {
            "min_scenarios": 1,
            "expected_core_signal_ids": ["s1", "s2", "s3"],
            "forbidden_pairings": [["n1", "s1"], ["n1", "s2"], ["n1", "s3"]],
        },
    },
    {
        "case_id": "step_a_pos_cross_domain_003",
        "case_type": "cross_domain_positive",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "Platform standard change + market response + outsourcing repricing should converge into one scenario.",
        "batch_size": 21,
        "signals": [
            _signal(
                "s1",
                "technical",
                "AI asset certification standard launches",
                "A major asset marketplace launches a standard certification flow for AI-generated game assets.",
                8,
                9,
                9,
            ),
            _signal(
                "s2",
                "market",
                "Competing marketplace follows within one week",
                "A rival marketplace launches a similar AI asset intake standard within the same week.",
                8,
                8,
                10,
            ),
            _signal(
                "s3",
                "capital",
                "Traditional outsourcing vendor repriced by market",
                "Public market investors sharply reprice a leading art outsourcing vendor after the platform shift.",
                7,
                7,
                8,
            ),
            _signal(
                "n1",
                "regulatory",
                "Regional ad disclosure update",
                "A minor regional ad disclosure update does not materially affect asset creation workflows.",
                3,
                8,
                6,
            ),
        ],
        "expected_step_a": {
            "min_scenarios": 1,
            "expected_core_signal_ids": ["s1", "s2", "s3"],
            "forbidden_pairings": [["n1", "s1"]],
        },
    },
    {
        "case_id": "step_a_neg_semantic_similarity_001",
        "case_type": "semantic_similarity_negative",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "Multiple game launch headlines look similar but should not form a logical scenario.",
        "batch_size": 18,
        "signals": [
            _signal("s1", "market", "Tencent launches new fantasy game", "Tencent releases a new fantasy mobile title in China.", 5, 8, 7),
            _signal("s2", "market", "NetEase launches new anime RPG", "NetEase releases a new anime action RPG in Japan.", 5, 8, 7),
            _signal("s3", "market", "miHoYo reveals new trailer", "miHoYo reveals the first trailer for an upcoming cross-platform game.", 4, 8, 6),
        ],
        "expected_step_a": {
            "max_scenarios": 0,
            "forbidden_pairings": [["s1", "s2"], ["s1", "s3"], ["s2", "s3"]],
        },
    },
    {
        "case_id": "step_a_neg_semantic_similarity_002",
        "case_type": "semantic_similarity_negative",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "Several funding headlines in unrelated segments should not be grouped only because they are all capital news.",
        "batch_size": 17,
        "signals": [
            _signal("s1", "capital", "VR hardware startup raises Series A", "A VR treadmill startup raises a Series A round.", 5, 8, 7),
            _signal("s2", "capital", "Mobile adtech startup raises seed", "A mobile adtech measurement startup raises a seed round.", 4, 8, 7),
            _signal("s3", "capital", "Cloud infra startup closes growth round", "A cloud rendering startup closes a growth financing round.", 5, 8, 6),
        ],
        "expected_step_a": {
            "max_scenarios": 0,
            "forbidden_pairings": [["s1", "s2"], ["s1", "s3"], ["s2", "s3"]],
        },
    },
    {
        "case_id": "step_a_small_batch_direct_pass_001",
        "case_type": "small_batch_direct_pass",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "A small batch should bypass Step A and go directly to Step C.",
        "batch_size": 8,
        "signals": [
            _signal("s1", "technical", "New mobile rendering optimization", "A vendor ships a mobile rendering optimization for high-end devices.", 6, 8, 8),
            _signal("s2", "market", "Flagship device performance demand rises", "Premium mobile players increasingly demand higher-end visual fidelity.", 6, 7, 7),
            _signal("s3", "team", "Graphics team expansion", "A studio expands its graphics optimization team for premium devices.", 5, 7, 7),
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
        },
    },
    {
        "case_id": "step_a_small_batch_direct_pass_002",
        "case_type": "small_batch_direct_pass",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "Another small batch control case to confirm the <=15 direct-pass policy.",
        "batch_size": 12,
        "signals": [
            _signal("s1", "regulatory", "Privacy policy clarification", "A platform clarifies one privacy documentation requirement.", 4, 8, 6),
            _signal("s2", "market", "Studios adjust compliance checklists", "Studios update internal compliance checklists after the clarification.", 4, 7, 6),
            _signal("s3", "capital", "Compliance tooling startup seed", "A compliance workflow startup raises a small seed round.", 4, 7, 6),
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
        },
    },
    {
        "case_id": "step_a_medium_batch_mixed_001",
        "case_type": "medium_batch_mixed",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "A medium batch with two true scenarios plus unrelated noise should produce 2-3 logical scenarios, not a single semantic cluster.",
        "batch_size": 28,
        "signals": [
            _signal("a1", "regulatory", "Store policy tightens", "A major app store tightens review rules for external payment paths.", 8, 9, 9),
            _signal("a2", "capital", "Acquisition fund for mobile studios", "A publisher opens a fund to acquire studios exposed to app store distribution risk.", 7, 8, 8),
            _signal("a3", "market", "Developer migration accelerates", "A measurable wave of developers begins diversifying away from the dominant mobile store.", 7, 8, 8),
            _signal("b1", "technical", "AI narrative tool reaches real-time quality", "A narrative AI tool reaches usable quality for live game content iteration.", 8, 9, 8),
            _signal("b2", "team", "AAA studio builds AI story ops team", "A AAA studio creates a new internal team for AI-assisted live narrative operations.", 7, 8, 8),
            _signal("b3", "market", "Live ops teams increase AI workflow usage", "Live ops teams significantly increase AI-assisted narrative workflow adoption.", 7, 8, 7),
            _signal("n1", "market", "Holiday hardware bundle announced", "A console bundle is announced for the holiday season.", 4, 8, 6),
            _signal("n2", "capital", "Esports chair brand financing", "An esports chair brand raises a marketing-focused round.", 3, 7, 5),
            _signal("n3", "technical", "Localization plugin patch", "A localization plugin ships a routine patch.", 3, 8, 5),
        ],
        "expected_step_a": {
            "min_scenarios": 2,
            "expected_core_signal_sets": [["a1", "a2", "a3"], ["b1", "b2", "b3"]],
            "forbidden_pairings": [["n1", "a1"], ["n2", "b1"], ["n3", "a2"]],
        },
    },
]


STEP_A_IDEALIZED_EVAL_CASES_VERSION = "v0.1"


def get_step_a_idealized_case(case_id: str):
    for case in STEP_A_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA:
        if case["case_id"] == case_id:
            return case
    return None
