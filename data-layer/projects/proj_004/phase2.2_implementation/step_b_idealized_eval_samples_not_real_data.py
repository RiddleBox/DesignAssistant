"""
Phase 2.2 Step B idealized evaluation samples.

Important:
- This file contains idealized synthetic test samples.
- It is NOT real production data.
- It is intended for controlled Step B evaluation only.
"""


def _signal(
    signal_id,
    signal_type,
    label,
    description,
    intensity_score,
    confidence_score=8,
    timeliness_score=7,
    source_id=None,
):
    return {
        "signal_id": signal_id,
        "source_id": source_id or f"src_{signal_id}",
        "signal_type": signal_type,
        "signal_label": label,
        "description": description,
        "evidence_text": description,
        "intensity_score": intensity_score,
        "confidence_score": confidence_score,
        "timeliness_score": timeliness_score,
    }


IDEALIZED_SAMPLE_DATA_NATURE = "idealized_synthetic_test_samples_not_real_data"


STEP_B_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA = [
    {
        "case_id": "step_b_scenario_primary_001",
        "case_type": "scenario_primary_with_signal_noise",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "A scenario memory that closes the core loop should become Step-C-ready, while a weaker standalone signal remains store-for-later.",
        "isolated_signal": {
            "signal": _signal(
                "iso_scn_001",
                "regulatory",
                "Platform pressure intensifies",
                "A platform policy escalation creates immediate pressure on mobile game distribution.",
                8,
                9,
                9,
            ),
            "roles": ["catalyst"],
            "domains": ["gaming", "mobile"],
            "waiting_for_text": "Waiting for demand evidence or resource validation already in store.",
        },
        "history_signals": [
            {
                "signal": _signal(
                    "hist_scn_market_001",
                    "market",
                    "Studios seek alternative channels",
                    "Mobile studios actively search for alternative distribution channels after policy tightening.",
                    7,
                    8,
                    8,
                ),
                "roles": ["demand_evidence"],
                "needs": ["resource_validation"],
                "domains": ["gaming", "mobile"],
                "waiting_for_text": "Waiting for proof that resources or catalysts are aligning.",
            },
            {
                "signal": _signal(
                    "hist_scn_team_001",
                    "team",
                    "Channel operations team expands",
                    "A publisher expands a dedicated channel operations team to support multi-store distribution.",
                    7,
                    8,
                    7,
                ),
                "roles": ["resource_validation"],
                "needs": ["catalyst"],
                "domains": ["gaming"],
                "waiting_for_text": "Waiting for an external catalyst to make the preparation actionable.",
            },
            {
                "signal": _signal(
                    "hist_scn_noise_001",
                    "market",
                    "Watchlist noise candidate",
                    "A smaller partner signal is somewhat complementary but does not close the full scenario loop.",
                    6,
                    7,
                    7,
                ),
                "roles": ["timing_signal"],
                "needs": ["catalyst"],
                "domains": ["gaming"],
                "waiting_for_text": "Waiting for a catalyst to confirm timing.",
            },
        ],
        "scenario_memories": [
            {
                "scenario_id": "scn_primary_001",
                "anchor_signal_ids": ["hist_scn_market_001"],
                "member_signal_ids": ["hist_scn_market_001", "hist_scn_team_001"],
                "covered_roles": ["demand_evidence", "resource_validation"],
                "missing_slots": ["catalyst"],
                "shared_affects": ["mobile distribution shift"],
                "state": "developing",
                "promotion_score": 0.78,
                "option_value_score": 0.74,
                "novelty_score": 0.62,
                "gap_fill_value": 0.81,
                "cross_domain_bonus": 0.2,
                "reasoning_path": "Demand + readiness exist; current catalyst should unlock the scenario.",
            }
        ],
        "emerging_links": [],
        "expected_step_b": {
            "matched": True,
            "fallback_used": True,
            "candidate_count_at_least": 2,
            "min_step_c_ready_groups": 1,
            "min_store_for_later_groups": 1,
            "expected_source_kinds": ["scenario_memory", "signal_entry"],
            "top_group_prefix": "scenario::",
            "top_route": "step_c_ready",
            "min_scenario_hits": 1,
        },
    },
    {
        "case_id": "step_b_link_store_for_later_001",
        "case_type": "emerging_link_store_for_later",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "A promising but incomplete emerging link should be retained as store-for-later rather than sent to Step C.",
        "isolated_signal": {
            "signal": _signal(
                "iso_link_001",
                "technical",
                "Realtime AI deployment friction rises",
                "Studios report new deployment and latency friction when attempting realtime AI-assisted workflows.",
                7,
                8,
                8,
            ),
            "roles": ["execution_risk"],
            "domains": ["ai", "gaming"],
            "waiting_for_text": "Waiting for demand or validation signals that make the risk commercially meaningful.",
        },
        "history_signals": [
            {
                "signal": _signal(
                    "hist_link_market_001",
                    "market",
                    "Studios still increase AI workflow usage",
                    "Despite friction, studios continue to expand AI-assisted asset workflow adoption.",
                    7,
                    8,
                    8,
                ),
                "roles": ["demand_evidence"],
                "needs": ["resource_validation"],
                "domains": ["ai", "gaming"],
                "waiting_for_text": "Waiting for stronger enabling signals.",
            },
            {
                "signal": _signal(
                    "hist_link_team_001",
                    "team",
                    "Internal workflow team forms",
                    "A mid-sized studio builds an internal team to manage AI content workflows.",
                    6,
                    7,
                    7,
                ),
                "roles": ["timing_signal"],
                "needs": ["demand_evidence"],
                "domains": ["ai"],
                "waiting_for_text": "Waiting for clearer market pull.",
            },
        ],
        "scenario_memories": [],
        "emerging_links": [
            {
                "link_id": "link_explore_001",
                "signal_ids": ["hist_link_market_001", "hist_link_team_001"],
                "edge_type": "complementary",
                "strength_band": "emerging",
                "gate_passed": True,
                "final_score": 0.58,
                "reasoning": "Demand-side adoption and workflow preparation are related but still incomplete.",
                "shared_affects": ["ai production workflow"],
            }
        ],
        "expected_step_b": {
            "matched": False,
            "fallback_used": False,
            "candidate_count_at_least": 1,
            "min_step_c_ready_groups": 0,
            "min_store_for_later_groups": 1,
            "expected_source_kinds": ["emerging_link"],
            "top_group_prefix": "link::",
            "top_route": "store_for_later",
            "min_link_hits": 1,
        },
    },
    {
        "case_id": "step_b_signal_store_for_later_001",
        "case_type": "standalone_signal_store_for_later",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "A single strong historical signal that only fills one gap should be retained for later rather than automatically escalated to Step C.",
        "isolated_signal": {
            "signal": _signal(
                "iso_sig_001",
                "regulatory",
                "Regulatory shock arrives",
                "A new compliance shock creates a strong catalyst for studios serving a specific segment.",
                8,
                8,
                9,
            ),
            "roles": ["catalyst"],
            "domains": ["gaming"],
            "waiting_for_text": "Waiting for demand-side evidence already present in the store.",
        },
        "history_signals": [
            {
                "signal": _signal(
                    "hist_sig_market_001",
                    "market",
                    "Studios already report urgent demand",
                    "Studios had already been reporting unmet demand and urgency before the regulatory catalyst arrived.",
                    8,
                    8,
                    8,
                ),
                "roles": ["demand_evidence"],
                "needs": ["catalyst"],
                "domains": ["gaming"],
                "waiting_for_text": "Waiting for an external catalyst.",
            }
        ],
        "scenario_memories": [],
        "emerging_links": [],
        "expected_step_b": {
            "matched": False,
            "fallback_used": False,
            "candidate_count_at_least": 1,
            "min_step_c_ready_groups": 0,
            "min_store_for_later_groups": 1,
            "expected_source_kinds": ["signal_entry"],
            "top_group_prefix": "signal::",
            "top_route": "store_for_later",
        },
    },
    {
        "case_id": "step_b_scenario_beats_strong_signal_001",
        "case_type": "scenario_step_c_ready_beats_signal_store_for_later",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "When both a rich scenario memory and a strong standalone historical signal exist, only the scenario that closes the loop should be Step-C-ready and rank first.",
        "isolated_signal": {
            "signal": _signal(
                "iso_mix_001",
                "regulatory",
                "New ad policy shock lands",
                "A major platform ad policy change creates a fresh catalyst for mobile studios that were already preparing alternative acquisition plans.",
                8,
                8,
                9,
            ),
            "roles": ["catalyst"],
            "domains": ["gaming", "mobile"],
            "waiting_for_text": "Waiting for demand and readiness evidence already accumulated in the store.",
        },
        "history_signals": [
            {
                "signal": _signal(
                    "hist_mix_market_001",
                    "market",
                    "Studios urgently seek alternative acquisition channels",
                    "Studios report urgent need for alternative acquisition channels as paid performance becomes less reliable.",
                    8,
                    8,
                    8,
                ),
                "roles": ["demand_evidence"],
                "needs": ["resource_validation"],
                "domains": ["gaming", "mobile"],
                "waiting_for_text": "Waiting for operational readiness and an external catalyst.",
            },
            {
                "signal": _signal(
                    "hist_mix_team_001",
                    "team",
                    "UA operations pod already formed",
                    "A publisher has already formed a dedicated UA operations pod to support alternative channel execution.",
                    7,
                    8,
                    7,
                ),
                "roles": ["resource_validation"],
                "needs": ["catalyst"],
                "domains": ["gaming", "mobile"],
                "waiting_for_text": "Waiting for a catalyst that makes the readiness actionable.",
            },
            {
                "signal": _signal(
                    "hist_mix_signal_001",
                    "market",
                    "Urgent historical demand spike",
                    "An older but still strong demand spike directly complements the new catalyst and can stand alone as a strong historical partner, but does not close a full opportunity loop on its own.",
                    9,
                    8,
                    8,
                ),
                "roles": ["demand_evidence"],
                "needs": ["catalyst"],
                "domains": ["gaming", "mobile"],
                "waiting_for_text": "Waiting for a strong catalyst to unlock demand.",
            }
        ],
        "scenario_memories": [
            {
                "scenario_id": "scn_mix_001",
                "anchor_signal_ids": ["hist_mix_market_001"],
                "member_signal_ids": ["hist_mix_market_001", "hist_mix_team_001"],
                "covered_roles": ["demand_evidence", "resource_validation"],
                "missing_slots": ["catalyst"],
                "shared_affects": ["mobile acquisition reshuffle"],
                "state": "developing",
                "promotion_score": 0.83,
                "option_value_score": 0.8,
                "novelty_score": 0.6,
                "gap_fill_value": 0.84,
                "cross_domain_bonus": 0.2,
                "reasoning_path": "Demand + readiness are already present; the current catalyst should unlock a richer scenario than any single pending signal.",
            }
        ],
        "emerging_links": [],
        "expected_step_b": {
            "matched": True,
            "fallback_used": True,
            "candidate_count_at_least": 2,
            "min_step_c_ready_groups": 1,
            "min_store_for_later_groups": 1,
            "expected_source_kinds": ["scenario_memory", "signal_entry"],
            "top_group_prefix": "scenario::",
            "top_route": "step_c_ready",
            "min_scenario_hits": 1,
        },
    },
    {
        "case_id": "step_b_no_match_001",
        "case_type": "negative_no_match",
        "data_nature": IDEALIZED_SAMPLE_DATA_NATURE,
        "description": "No stored scenario, link, or pending signal should be recalled when domains and role needs do not line up.",
        "isolated_signal": {
            "signal": _signal(
                "iso_none_001",
                "regulatory",
                "Regional compliance note",
                "A narrow compliance clarification appears in a different domain without broader strategic implications.",
                4,
                7,
                6,
            ),
            "roles": ["negative_validator"],
            "domains": ["regulation"],
            "waiting_for_text": "No specific partner is expected.",
        },
        "history_signals": [
            {
                "signal": _signal(
                    "hist_none_001",
                    "regulatory",
                    "Unrelated gaming regulation",
                    "An older gaming regulation signal exists but is not waiting for a negative validator and does not share the same domain packet.",
                    5,
                    7,
                    6,
                ),
                "roles": ["catalyst"],
                "needs": ["resource_validation"],
                "domains": ["gaming"],
                "waiting_for_text": "Waiting for resource validation.",
            }
        ],
        "scenario_memories": [],
        "emerging_links": [],
        "expected_step_b": {
            "matched": False,
            "fallback_used": False,
            "candidate_count_at_most": 0,
            "min_step_c_ready_groups": 0,
            "min_store_for_later_groups": 0,
            "expected_source_kinds": [],
        },
    },
]


STEP_B_IDEALIZED_EVAL_CASES_VERSION = "v0.3"


def get_step_b_idealized_case(case_id: str):
    for case in STEP_B_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA:
        if case["case_id"] == case_id:
            return case
    return None
