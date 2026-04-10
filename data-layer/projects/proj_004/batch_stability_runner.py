import json
import os
import random
import time
from datetime import datetime

from run_batch_real import (
    SAMPLES_ROOT,
    PROCESSED_DIR,
    ensure_dirs,
    load_llm_config,
    load_samples,
    run_step1_decode,
    build_rag_retriever,
    run_step2_judgment,
    run_step3_action,
    run_step4_retro,
)

BASE = os.path.dirname(os.path.abspath(__file__))
STABILITY_DIR = os.path.join(BASE, "stability_reports")


def _list_candidate_files() -> list[str]:
    candidates = []
    for root in [SAMPLES_ROOT, PROCESSED_DIR]:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.lower().endswith(".json"):
                continue
            candidates.append(os.path.join(root, name))
    deduped = []
    seen = set()
    for path in candidates:
        name = os.path.basename(path)
        if name in seen:
            continue
        seen.add(name)
        deduped.append(path)
    return deduped


def _pick_files(files: list[str], sample_size: int, seed: int) -> list[str]:
    if sample_size <= 0 or sample_size >= len(files):
        return list(files)
    rng = random.Random(seed)
    return sorted(rng.sample(files, sample_size))


def _serialize_summary(run_index: int, selected_files: list[str], all_signals, decode_results, judgment_result, action_result, retro_result, total_ms: int) -> dict:
    opp = judgment_result.opportunities[0] if judgment_result and judgment_result.opportunities else None
    act = getattr(action_result, "action_decision", None) if action_result else None
    retro = getattr(retro_result, "retrospective", None) if retro_result else None
    display = getattr(act, "display", None) if act else None
    posture_basis = getattr(act, "posture_basis", None) if act else None
    return {
        "run_index": run_index,
        "selected_files": [os.path.basename(p) for p in selected_files],
        "source_ids": [getattr(dr, "source_id", "") for dr in decode_results],
        "signal_count": len(all_signals),
        "opportunity_key": getattr(opp, "opportunity_key", "") if opp else "",
        "opportunity_title": getattr(opp, "opportunity_title", "") if opp else "",
        "priority_level": str(getattr(opp, "priority_level", "")) if opp else "",
        "action_posture": str(getattr(act, "decision_posture", "")) if act else "",
        "commitment_mode": str(getattr(act, "commitment_mode", "")) if act else "",
        "display_badge": getattr(display, "display_badge", "") if display else "",
        "display_judgment_label": getattr(display, "display_judgment_label", "") if display else "",
        "display_title_mode": getattr(display, "display_title_mode", "") if display else "",
        "posture_basis": {
            "evidence_readiness_consensus": getattr(posture_basis, "evidence_readiness_consensus", "") if posture_basis else "",
            "critical_unknowns_blocking_real_world_action": getattr(posture_basis, "critical_unknowns_blocking_real_world_action", "") if posture_basis else "",
            "commitment_ceiling_consensus": getattr(posture_basis, "commitment_ceiling_consensus", "") if posture_basis else "",
            "reversibility_consensus": getattr(posture_basis, "reversibility_consensus", "") if posture_basis else "",
            "cost_of_delay_consensus": getattr(posture_basis, "cost_of_delay_consensus", "") if posture_basis else "",
            "cost_of_wrong_commitment_consensus": getattr(posture_basis, "cost_of_wrong_commitment_consensus", "") if posture_basis else "",
        },
        "stage_1_objective": getattr(act, "stage_1_objective", "") if act else "",
        "key_gates": list(getattr(act, "key_gates", []) or []) if act else [],
        "exit_conditions": list(getattr(act, "exit_conditions", []) or []) if act else [],
        "open_disagreements": list(getattr(act, "open_disagreements", []) or []) if act else [],
        "critical_findings": len(getattr(retro, "critical_findings", []) or []) if retro else 0,
        "phase3_priorities": len(getattr(retro, "phase3_priorities", []) or []) if retro else 0,
        "total_ms": total_ms,
    }


def main():
    ensure_dirs()
    os.makedirs(STABILITY_DIR, exist_ok=True)

    sample_size = int(os.environ.get("STABILITY_SAMPLE_SIZE", "4") or 4)
    repeat_runs = int(os.environ.get("STABILITY_REPEAT_RUNS", "3") or 3)
    seed = int(os.environ.get("STABILITY_SEED", "42") or 42)

    llm_config_21 = load_llm_config("2.1")
    if not llm_config_21.get("api_key"):
        raise RuntimeError("未找到 phase 2.1 的 LLM API key")

    all_files = _list_candidate_files()
    if not all_files:
        raise RuntimeError("未找到可用于稳定性验证的 JSON 样本")

    selected_files = _pick_files(all_files, sample_size=sample_size, seed=seed)
    rag_retriever = build_rag_retriever()

    runs = []
    for idx in range(1, repeat_runs + 1):
        t0 = time.time()
        samples = load_samples(selected_files)
        all_signals, decode_results, per_sample_stats = run_step1_decode(samples, llm_config_21)
        judgment_result = run_step2_judgment(all_signals, len(samples), rag_retriever, llm_config_21.get("api_key"))
        action_result = None
        retro_result = None
        if judgment_result is not None and getattr(judgment_result, "opportunities", None):
            action_result = run_step3_action(judgment_result)
            retro_result = run_step4_retro(
                judgment_result,
                action_result,
                decode_results,
                per_sample_stats,
                rag_retriever=rag_retriever,
                t_start=t0,
                run_id=f"stability_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}",
            )
        runs.append(_serialize_summary(
            run_index=idx,
            selected_files=selected_files,
            all_signals=all_signals,
            decode_results=decode_results,
            judgment_result=judgment_result,
            action_result=action_result,
            retro_result=retro_result,
            total_ms=int((time.time() - t0) * 1000),
        ))

    opportunity_key_set = sorted({r["opportunity_key"] for r in runs if r.get("opportunity_key")})
    title_set = sorted({r["opportunity_title"] for r in runs if r.get("opportunity_title")})
    posture_set = sorted({r["action_posture"] for r in runs if r.get("action_posture")})
    display_badge_set = sorted({r["display_badge"] for r in runs if r.get("display_badge")})
    display_label_set = sorted({r["display_judgment_label"] for r in runs if r.get("display_judgment_label")})
    evidence_readiness_set = sorted({str((r.get("posture_basis") or {}).get("evidence_readiness_consensus", "")) for r in runs if (r.get("posture_basis") or {}).get("evidence_readiness_consensus", "") != ""})
    blocking_unknowns_set = sorted({str((r.get("posture_basis") or {}).get("critical_unknowns_blocking_real_world_action", "")) for r in runs if (r.get("posture_basis") or {}).get("critical_unknowns_blocking_real_world_action", "") != ""})
    commitment_ceiling_set = sorted({str((r.get("posture_basis") or {}).get("commitment_ceiling_consensus", "")) for r in runs if (r.get("posture_basis") or {}).get("commitment_ceiling_consensus", "") != ""})
    reversibility_set = sorted({str((r.get("posture_basis") or {}).get("reversibility_consensus", "")) for r in runs if (r.get("posture_basis") or {}).get("reversibility_consensus", "") != ""})
    delay_cost_set = sorted({str((r.get("posture_basis") or {}).get("cost_of_delay_consensus", "")) for r in runs if (r.get("posture_basis") or {}).get("cost_of_delay_consensus", "") != ""})
    wrong_commitment_cost_set = sorted({str((r.get("posture_basis") or {}).get("cost_of_wrong_commitment_consensus", "")) for r in runs if (r.get("posture_basis") or {}).get("cost_of_wrong_commitment_consensus", "") != ""})
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sample_size": sample_size,
        "repeat_runs": repeat_runs,
        "seed": seed,
        "selected_files": [os.path.basename(p) for p in selected_files],
        "opportunity_key_variants": opportunity_key_set,
        "title_variants": title_set,
        "posture_variants": posture_set,
        "display_badge_variants": display_badge_set,
        "display_label_variants": display_label_set,
        "posture_basis_variants": {
            "evidence_readiness_consensus": evidence_readiness_set,
            "critical_unknowns_blocking_real_world_action": blocking_unknowns_set,
            "commitment_ceiling_consensus": commitment_ceiling_set,
            "reversibility_consensus": reversibility_set,
            "cost_of_delay_consensus": delay_cost_set,
            "cost_of_wrong_commitment_consensus": wrong_commitment_cost_set,
        },
        "opportunity_key_stable": len(opportunity_key_set) <= 1,
        "title_stable": len(title_set) <= 1,
        "posture_stable": len(posture_set) <= 1,
        "display_badge_stable": len(display_badge_set) <= 1,
        "display_label_stable": len(display_label_set) <= 1,
        "posture_basis_stable": len(evidence_readiness_set) <= 1 and len(blocking_unknowns_set) <= 1 and len(commitment_ceiling_set) <= 1 and len(reversibility_set) <= 1 and len(delay_cost_set) <= 1 and len(wrong_commitment_cost_set) <= 1,
        "runs": runs,
    }

    out_path = os.path.join(STABILITY_DIR, f"stability_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "out_path": out_path,
        "opportunity_key_variants": opportunity_key_set,
        "title_variants": title_set,
        "posture_variants": posture_set,
        "display_badge_variants": display_badge_set,
        "display_label_variants": display_label_set,
        "posture_basis_variants": {
            "evidence_readiness_consensus": evidence_readiness_set,
            "critical_unknowns_blocking_real_world_action": blocking_unknowns_set,
            "commitment_ceiling_consensus": commitment_ceiling_set,
            "reversibility_consensus": reversibility_set,
            "cost_of_delay_consensus": delay_cost_set,
            "cost_of_wrong_commitment_consensus": wrong_commitment_cost_set,
        },
        "opportunity_key_stable": len(opportunity_key_set) <= 1,
        "title_stable": len(title_set) <= 1,
        "posture_stable": len(posture_set) <= 1,
        "display_badge_stable": len(display_badge_set) <= 1,
        "display_label_stable": len(display_label_set) <= 1,
        "posture_basis_stable": len(evidence_readiness_set) <= 1 and len(blocking_unknowns_set) <= 1 and len(commitment_ceiling_set) <= 1 and len(reversibility_set) <= 1 and len(delay_cost_set) <= 1 and len(wrong_commitment_cost_set) <= 1,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()