import importlib.util
import json
import os
from pathlib import Path

from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest, SourceType


REAL_CASE_ID = "step_a_real_cross_domain_mobile_distribution_001"
REAL_SIGNAL_ID = "r1"


def _load_real_case():
    current_dir = Path(__file__).resolve().parent
    sample_path = current_dir.parent / "phase2.2_implementation" / "step_a_real_eval_samples.py"
    spec = importlib.util.spec_from_file_location("step_a_real_eval_samples", sample_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Failed to load sample module: {sample_path}"
    spec.loader.exec_module(module)
    case = module.get_step_a_real_case(REAL_CASE_ID)
    assert case, f"Real case not found: {REAL_CASE_ID}"
    signal = next((item for item in case["signals"] if item["signal_id"] == REAL_SIGNAL_ID), None)
    assert signal, f"Real signal not found: {REAL_SIGNAL_ID}"
    return case, signal


def _build_request(case, signal, suffix):
    content = (
        f"Case: {case['description']} "
        f"Signal label: {signal['signal_label']}. "
        f"Signal description: {signal['description']} "
        f"Validation suffix: {suffix}."
    )
    return IntelligenceDecodeRequest(
        source_id=f"minimal_decoder_validation_{suffix}",
        source_type=SourceType.NEWS,
        title=signal["signal_label"],
        content=content,
        source_name="minimal_validation",
        language="en-US",
    )


def _signal_to_dict(signal):
    if hasattr(signal, "model_dump"):
        return signal.model_dump()
    return signal.dict()


def _run_decode(case, signal, suffix, llm_payload):
    os.environ.setdefault("ANTHROPIC_BASE_URL", "https://dummy.local")
    decoder = IntelligenceDecoder(api_key="dummy-key", enable_two_stage=False)
    decoder._call_llm = lambda *args, **kwargs: json.dumps(llm_payload, ensure_ascii=False)
    request = _build_request(case, signal, suffix)
    result = decoder.decode(request)
    return {
        "warnings": result.warnings or [],
        "summary": result.summary,
        "signals": [_signal_to_dict(item) for item in result.signals],
    }


def main():
    case, real_signal = _load_real_case()

    single_direction_payload = {
        "signals": [
            {
                "signal_id": "sig_single_001",
                "signal_type": "regulatory",
                "signal_label": real_signal["signal_label"],
                "description": real_signal["description"],
                "evidence_text": real_signal["description"],
                "entities": ["Apple", "European Commission"],
                "intensity_score": 8,
                "confidence_score": 9,
                "timeliness_score": 7,
                "logic_frame": {
                    "what_changed": "platform_policy",
                    "change_direction": "tighten",
                    "affects": ["mobile developers", "app store operators"],
                },
            }
        ]
    }

    clear_multi_direction_payload = {
        "signals": [
            {
                "signal_id": "sig_multi_001",
                "signal_type": "market",
                "signal_label": "Mobile platform reconfiguration",
                "description": "European distribution rules tighten for anti-steering compliance; Android payment access loosens for third-party systems",
                "evidence_text": "European Commission forces anti-steering rule changes on Apple; antitrust ruling opens competing payment systems on Android",
                "entities": ["Apple", "Google Play", "Epic"],
                "intensity_score": 8,
                "confidence_score": 8,
                "timeliness_score": 8,
                "logic_frame": {
                    "what_changed": "platform_policy / distribution_access",
                    "change_direction": "tighten / loosen",
                    "affects": ["mobile developers", "platform challengers"],
                },
            }
        ]
    }

    unstable_multi_direction_payload = {
        "signals": [
            {
                "signal_id": "sig_multi_002",
                "signal_type": "market",
                "signal_label": "Ambiguous mobile platform change",
                "description": "Platform policy changes in one area while access changes elsewhere",
                "evidence_text": "Policy pressure rises while payment opening may expand",
                "entities": ["Apple", "Android"],
                "intensity_score": 7,
                "confidence_score": 6,
                "timeliness_score": 8,
                "logic_frame": {
                    "what_changed": "platform_policy",
                    "change_direction": "tighten / loosen",
                    "affects": ["mobile developers"],
                },
            }
        ]
    }

    single_result = _run_decode(case, real_signal, "single_direction", single_direction_payload)
    clear_multi_result = _run_decode(case, real_signal, "clear_multi_direction", clear_multi_direction_payload)
    unstable_multi_result = _run_decode(case, real_signal, "unstable_multi_direction", unstable_multi_direction_payload)

    assert len(single_result["signals"]) == 1, "Single-direction sample should not be split"
    single_flags = single_result["signals"][0].get("metadata", {}).get("audit", {}).get("audit_flags", [])
    assert "decoder_split_by_direction_fallback" not in single_flags, "Single-direction sample must not receive split fallback flag"
    assert single_result["signals"][0].get("logic_frame", {}).get("change_direction") == "tighten", "Single-direction sample should preserve tighten"

    assert len(clear_multi_result["signals"]) == 2, "Clear multi-direction sample should be split into 2 signals"
    clear_directions = [item.get("logic_frame", {}).get("change_direction") for item in clear_multi_result["signals"]]
    assert clear_directions == ["tighten", "loosen"], "Clear multi-direction sample should split into tighten and loosen"
    for item in clear_multi_result["signals"]:
        flags = item.get("metadata", {}).get("audit", {}).get("audit_flags", [])
        assert "decoder_split_by_direction_fallback" in flags, "Split signals should carry decoder split fallback flag"

    assert len(unstable_multi_result["signals"]) == 1, "Unstable multi-direction sample should not be split"
    unstable_flags = unstable_multi_result["signals"][0].get("metadata", {}).get("audit", {}).get("audit_flags", [])
    assert "multi_direction_detected_not_split" in unstable_flags, "Unstable multi-direction sample should record not-split audit flag"
    assert unstable_multi_result["signals"][0].get("logic_frame", {}).get("change_direction") == "unknown", "Unstable multi-direction sample should normalize direction to unknown"

    output = {
        "selected_real_case": {
            "case_id": case["case_id"],
            "signal_id": real_signal["signal_id"],
            "signal_label": real_signal["signal_label"],
        },
        "validation_status": "PASS",
        "checks": {
            "single_direction_not_split": {
                "signal_count": len(single_result["signals"]),
                "audit_flags": single_flags,
                "change_direction": single_result["signals"][0].get("logic_frame", {}).get("change_direction"),
            },
            "clear_multi_direction_split": {
                "signal_count": len(clear_multi_result["signals"]),
                "directions": clear_directions,
                "audit_flags_per_signal": [
                    item.get("metadata", {}).get("audit", {}).get("audit_flags", [])
                    for item in clear_multi_result["signals"]
                ],
            },
            "unstable_multi_direction_flag_only": {
                "signal_count": len(unstable_multi_result["signals"]),
                "audit_flags": unstable_flags,
                "change_direction": unstable_multi_result["signals"][0].get("logic_frame", {}).get("change_direction"),
            },
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
