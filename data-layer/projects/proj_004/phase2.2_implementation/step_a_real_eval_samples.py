"""
Phase 2.2 Step A real-sample evaluation cases.

Important:
- This file contains real sample references from background/real_intel_samples.
- Offline evaluation should use the stable fixture pool at the root plus the snapshot expansion pool under incoming/.
- It should not depend on processed/ because processed/ represents online pipeline state rather than evaluation semantics.
- It is intended for layered evaluation alongside the idealized runner.
- This version expands the starter pool into a layered baseline set that is large enough for repeatable trend comparison.
"""


REAL_SAMPLE_DATA_NATURE = "real_samples_from_background_real_intel_samples"


STEP_A_REAL_EVAL_SAMPLES = [
    {
        "case_id": "step_a_real_small_batch_control_001",
        "case_type": "small_batch_direct_pass",
        "validation_profile": "strict",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A small real batch should bypass Step A and go directly to Step C under the <=15 policy.",
        "sample_files": [
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
            "min_total_signals": 3,
            "expected_non_noise_source_ids": ["real_009", "real_010", "real_011"],
        },
    },
    {
        "case_id": "step_a_real_noise_screening_001",
        "case_type": "small_batch_noise_mixed",
        "validation_profile": "strict",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "Noise-heavy real samples should still respect the small-batch bypass policy while preserving per-source noise behavior.",
        "sample_files": [
            "noise_001_earnings_boilerplate.json",
            "noise_002_routine_patch_note.json",
            "noise_003_pr_anniversary.json",
            "sample_011_market_indie_selfpublish_trend.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
            "expected_noise_source_ids": ["noise_001", "noise_002", "noise_003"],
            "expected_non_noise_source_ids": ["real_011"],
        },
    },
    {
        "case_id": "step_a_real_small_batch_team_signal_001",
        "case_type": "small_batch_team_cluster",
        "validation_profile": "strict",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A focused team/org change batch should remain on the small-batch fast path while preserving source coverage.",
        "sample_files": [
            "sample_003_team_ubisoft_redstorm_layoffs.json",
            "sample_007_team_xbox_leadership_exits.json",
            "incoming/incoming_013_team_xbox_leadership_exits.json",
            "incoming/incoming_031_team_xbox_new_ceo_brand_reset.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
            "min_total_signals": 4,
            "expected_non_noise_source_ids": ["real_003", "real_007", "incoming_013", "incoming_031"],
        },
    },
    {
        "case_id": "step_a_real_small_batch_ai_policy_001",
        "case_type": "small_batch_ai_policy_cluster",
        "validation_profile": "strict",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A compact AI workflow/policy batch should also stay in the small-batch path and keep all meaningful sources.",
        "sample_files": [
            "sample_004_technical_capcom_genai.json",
            "sample_006_technical_squareenix_gemini_npc.json",
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "incoming/incoming_014_technical_capcom_genai_policy.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": True,
            "expected_reason": "small_batch_threshold",
            "min_total_signals": 4,
            "expected_non_noise_source_ids": ["real_004", "real_006", "real_009", "incoming_014"],
        },
    },
    {
        "case_id": "step_a_real_medium_mixed_001",
        "case_type": "medium_batch_mixed_exploratory",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A mixed real batch should execute Step A and ideally surface at least one coherent scenario around platform/distribution change or AI workflow change.",
        "sample_files": [
            "sample_003_team_ubisoft_redstorm_layoffs.json",
            "sample_006_technical_squareenix_gemini_npc.json",
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "sample_001_capital_moonton_acquisition.json",
            "sample_005_market_delta_force_dau.json",
            "sample_008_market_crimson_desert_sales.json",
            "incoming/incoming_005_regulatory_eu_dma_apple_games.json",
            "incoming/incoming_014_technical_capcom_genai_policy.json",
            "incoming/incoming_019_technical_crimson_desert_ai_assets.json",
            "incoming/incoming_025_technical_tencent_genai_animation_gdc.json",
            "incoming/incoming_028_market_disney_gaming_ambition.json",
            "incoming/incoming_029_market_warframe_liveservice_strategy.json",
            "incoming/incoming_030_market_pokemon_champions_monetization.json",
            "incoming/incoming_032_technical_zuckerberg_ai_coceo.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_core_source_sets": [
                ["incoming_005", "real_010", "real_011"],
                ["real_006", "real_009", "incoming_025"],
            ],
            "forbidden_source_pairings": [
                ["real_003", "incoming_005"],
            ],
        },
    },
    {
        "case_id": "step_a_real_medium_ai_workflow_001",
        "case_type": "medium_batch_ai_workflow",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A larger AI workflow batch should execute Step A and recover at least one reusable AI-production scenario without hard grouping pollution.",
        "sample_files": [
            "sample_004_technical_capcom_genai.json",
            "sample_006_technical_squareenix_gemini_npc.json",
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "sample_001_capital_moonton_acquisition.json",
            "sample_005_market_delta_force_dau.json",
            "sample_008_market_crimson_desert_sales.json",
            "incoming/incoming_014_technical_capcom_genai_policy.json",
            "incoming/incoming_017_technical_squareenix_gemini_npc.json",
            "incoming/incoming_019_technical_crimson_desert_ai_assets.json",
            "incoming/incoming_025_technical_tencent_genai_animation_gdc.json",
            "incoming/incoming_028_market_disney_gaming_ambition.json",
            "incoming/incoming_029_market_warframe_liveservice_strategy.json",
            "incoming/incoming_032_technical_zuckerberg_ai_coceo.json",
            "incoming/incoming_036_technical_ram_price_ai_handheld_impact.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_core_source_sets": [
                ["real_004", "incoming_014"],
                ["real_006", "incoming_017"],
                ["real_009", "incoming_025"],
            ],
            "forbidden_source_pairings": [
                ["real_010", "incoming_032"],
            ],
        },
    },
    {
        "case_id": "step_a_real_medium_platform_distribution_001",
        "case_type": "medium_batch_platform_distribution",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A distribution/platform pressure batch should execute Step A and preserve at least one coherent platform strategy scenario.",
        "sample_files": [
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "sample_001_capital_moonton_acquisition.json",
            "sample_002_capital_china_market_q1.json",
            "sample_005_market_delta_force_dau.json",
            "sample_008_market_crimson_desert_sales.json",
            "incoming/incoming_005_regulatory_eu_dma_apple_games.json",
            "incoming/incoming_015_market_nintendo_switch2_production_cut.json",
            "incoming/incoming_026_capital_reforged_headup_acquisition.json",
            "incoming/incoming_028_market_disney_gaming_ambition.json",
            "incoming/incoming_029_market_warframe_liveservice_strategy.json",
            "incoming/incoming_030_market_pokemon_champions_monetization.json",
            "incoming/incoming_034_market_switch2_demand_flag.json",
            "incoming/incoming_037_market_china_games_feb2026_revenue.json",
            "incoming/incoming_038_market_delta_force_50m_dau.json",
            "incoming/incoming_040_market_crimson_desert_3m_day5.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_core_source_sets": [
                ["incoming_005", "real_010", "real_011"],
                ["incoming_028", "incoming_029", "incoming_030"],
            ],
            "forbidden_source_pairings": [
                ["real_002", "incoming_029"],
            ],
        },
    },
    {
        "case_id": "step_a_real_medium_xbox_team_strategy_001",
        "case_type": "medium_batch_team_strategy",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A team and leadership shock batch should execute Step A and preserve at least one Xbox leadership/strategy scenario.",
        "sample_files": [
            "sample_003_team_ubisoft_redstorm_layoffs.json",
            "sample_007_team_xbox_leadership_exits.json",
            "sample_001_capital_moonton_acquisition.json",
            "sample_002_capital_china_market_q1.json",
            "sample_005_market_delta_force_dau.json",
            "sample_008_market_crimson_desert_sales.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "incoming/incoming_012_team_sony_dark_outlaw_shutdown.json",
            "incoming/incoming_013_team_xbox_leadership_exits.json",
            "incoming/incoming_016_team_uk_industry_jobs_decline.json",
            "incoming/incoming_020_team_epic_1000_layoffs.json",
            "incoming/incoming_024_team_sony_bluepoint_darkoutlaw_closures.json",
            "incoming/incoming_031_team_xbox_new_ceo_brand_reset.json",
            "incoming/incoming_035_team_xbox_ceo_asha_sharma.json",
            "incoming/incoming_039_team_epic_fortnite_modes_cut.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_core_source_sets": [
                ["real_007", "incoming_013", "incoming_031"],
                ["incoming_020", "incoming_039"],
            ],
            "forbidden_source_pairings": [
                ["real_008", "incoming_031"],
            ],
        },
    },
    {
        "case_id": "step_a_real_medium_crimson_cluster_001",
        "case_type": "medium_batch_market_technical_cluster",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A market plus technical product cluster should execute Step A and preserve at least one Crimson Desert scenario while avoiding unrelated traction joins.",
        "sample_files": [
            "sample_005_market_delta_force_dau.json",
            "sample_006_technical_squareenix_gemini_npc.json",
            "sample_008_market_crimson_desert_sales.json",
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "sample_001_capital_moonton_acquisition.json",
            "incoming/incoming_018_market_crimson_desert_launch_sales.json",
            "incoming/incoming_019_technical_crimson_desert_ai_assets.json",
            "incoming/incoming_023_market_slaythespire2_performance.json",
            "incoming/incoming_028_market_disney_gaming_ambition.json",
            "incoming/incoming_029_market_warframe_liveservice_strategy.json",
            "incoming/incoming_030_market_pokemon_champions_monetization.json",
            "incoming/incoming_036_technical_ram_price_ai_handheld_impact.json",
            "incoming/incoming_038_market_delta_force_50m_dau.json",
            "incoming/incoming_040_market_crimson_desert_3m_day5.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_core_source_sets": [
                ["real_008", "incoming_018", "incoming_040"],
                ["incoming_019", "incoming_036"],
            ],
            "forbidden_source_pairings": [
                ["real_005", "incoming_019"],
            ],
        },
    },
    {
        "case_id": "step_a_real_medium_noise_intrusion_guard_001",
        "case_type": "medium_batch_noise_guard",
        "validation_profile": "exploratory",
        "data_nature": REAL_SAMPLE_DATA_NATURE,
        "description": "A larger mixed batch with injected noise should still execute Step A while keeping noise out of final scenarios as much as possible.",
        "sample_files": [
            "sample_004_technical_capcom_genai.json",
            "sample_006_technical_squareenix_gemini_npc.json",
            "sample_009_technical_netease_ai_replacing_outsource.json",
            "sample_010_capital_epic_google_antitrust.json",
            "sample_011_market_indie_selfpublish_trend.json",
            "sample_001_capital_moonton_acquisition.json",
            "sample_005_market_delta_force_dau.json",
            "sample_008_market_crimson_desert_sales.json",
            "incoming/incoming_014_technical_capcom_genai_policy.json",
            "incoming/incoming_017_technical_squareenix_gemini_npc.json",
            "incoming/incoming_019_technical_crimson_desert_ai_assets.json",
            "incoming/incoming_025_technical_tencent_genai_animation_gdc.json",
            "incoming/incoming_028_market_disney_gaming_ambition.json",
            "incoming/incoming_029_market_warframe_liveservice_strategy.json",
            "incoming/incoming_030_market_pokemon_champions_monetization.json",
            "incoming/incoming_032_technical_zuckerberg_ai_coceo.json",
            "incoming/incoming_036_technical_ram_price_ai_handheld_impact.json",
            "noise_001_earnings_boilerplate.json",
            "noise_002_routine_patch_note.json",
            "incoming/incoming_noise_001_dlc_roadmap_announcement.json",
        ],
        "expected_step_a": {
            "should_skip_step_a": False,
            "min_total_signals": 16,
            "min_scenarios": 1,
            "expected_noise_source_ids": ["noise_001", "noise_002", "incoming_noise_001"],
            "expected_core_source_sets": [
                ["real_004", "incoming_014"],
                ["real_006", "real_009", "incoming_025"],
            ],
            "forbidden_source_pairings": [
                ["noise_001", "real_004"],
                ["noise_002", "real_009"],
            ],
        },
    },
]




STEP_A_REAL_EVAL_CASES_VERSION = "real_world_baseline_v1"


def get_step_a_real_case(case_id: str):
    for case in STEP_A_REAL_EVAL_SAMPLES:
        if case["case_id"] == case_id:
            return case
    return None
