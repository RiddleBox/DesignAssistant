"""
Phase 2.2 Step B idealized evaluation runner.

Important:
- This runner evaluates idealized synthetic Step B samples.
- The sample file is NOT real production data.
- It directly executes real Step B retrieval against a temporary Signal Store.

Usage examples:
- python run_step_b_idealized_eval.py
- python run_step_b_idealized_eval.py --case-id step_b_scenario_primary_001
- python run_step_b_idealized_eval.py --json
"""

import argparse
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

from signal_store import SignalStore, build_signal_entry
from step_b_retrieval import run_step_b
from step_b_idealized_eval_samples_not_real_data import (
    STEP_B_IDEALIZED_EVAL_CASES_VERSION,
    STEP_B_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA,
)


class StepBIdealizedEvalRunner:
    """Runner for Step B idealized evaluation samples."""

    def __init__(
        self,
        case_id: Optional[str] = None,
        json_output: bool = False,
        fail_fast: bool = False,
        save_report: bool = False,
        report_dir: Optional[str] = None,
    ):
        self.case_id = case_id
        self.json_output = json_output
        self.fail_fast = fail_fast
        self.save_report = save_report
        self.report_dir = report_dir
        self.results: List[dict] = []

    def run(self):
        cases = self._get_target_cases()

        if not self.json_output:
            self._print_header(cases)

        for index, case in enumerate(cases, 1):
            result = self._run_case(case)
            self.results.append(result)

            if not self.json_output:
                self._print_case_result(index, len(cases), result)

            if self.fail_fast and not result["validation"]["passed"]:
                break

        report = self._build_json_report()
        if self.save_report:
            report["saved_report_path"] = self._write_report(report)

        if self.json_output:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self._print_summary()
            if report.get("saved_report_path"):
                print(f"Saved report: {report['saved_report_path']}")

    def _get_target_cases(self) -> List[dict]:
        if self.case_id:
            matches = [
                case for case in STEP_B_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA
                if case["case_id"] == self.case_id
            ]
            if not matches:
                raise ValueError(f"Case not found: {self.case_id}")
            return matches
        return STEP_B_IDEALIZED_EVAL_SAMPLES_NOT_REAL_DATA

    def _run_case(self, case: dict) -> dict:
        with tempfile.TemporaryDirectory(prefix="step_b_eval_") as tmpdir:
            store_path = os.path.join(tmpdir, "signal_store.pkl")
            signal_store = SignalStore(store_path=store_path)
            batch_date = datetime.now().strftime("%Y-%m-%d")

            history_entries = []
            for item in case.get("history_signals", []):
                history_signal = dict(item["signal"])
                history_entries.append(
                    build_signal_entry(
                        signal=history_signal,
                        roles=list(item.get("roles", [])),
                        needs=list(item.get("needs", [])),
                        domains=list(item.get("domains", [])),
                        waiting_for_text=item.get("waiting_for_text", ""),
                        batch_date=batch_date,
                    )
                )
            if history_entries:
                signal_store.add_batch(history_entries)

            if case.get("emerging_links"):
                signal_store.save_emerging_links(case.get("emerging_links", []), batch_date=batch_date)
            if case.get("scenario_memories"):
                signal_store.save_scenario_memories(case.get("scenario_memories", []), batch_date=batch_date)

            isolated_signal = dict(case["isolated_signal"]["signal"])
            isolated_signal["_role_annotation"] = {
                "roles": list(case["isolated_signal"].get("roles", [])),
                "domains": list(case["isolated_signal"].get("domains", [])),
                "waiting_for_text": case["isolated_signal"].get("waiting_for_text", ""),
            }

            step_b_result = run_step_b(
                isolated_signal=isolated_signal,
                signal_store=signal_store,
                llm_client=None,
            )

            execution = self._build_execution(case, step_b_result)
            validation = self._validate_case(case, execution)
            return {
                "case": case,
                "execution": execution,
                "validation": validation,
            }

    def _build_execution(self, case: dict, step_b_result) -> dict:
        candidate_infos = getattr(step_b_result, "candidate_group_infos", []) or []
        latent_candidate_infos = getattr(step_b_result, "latent_candidate_group_infos", []) or []
        visible_candidate_infos = list(candidate_infos) + list(latent_candidate_infos)
        candidate_dicts = []
        route_counts = {"step_c_ready": 0, "store_for_later": 0, "discard": 0}
        source_kind_counts = {
            "scenario_memory": 0,
            "emerging_link": 0,
            "signal_entry": 0,
        }

        for info in visible_candidate_infos:
            route_counts[info.route] = route_counts.get(info.route, 0) + 1
            source_kind_counts[info.source_kind] = source_kind_counts.get(info.source_kind, 0) + 1
            candidate_dicts.append({
                "group_id": info.group_id,
                "source_kind": info.source_kind,
                "route": info.route,
                "route_reason": info.route_reason,
                "rank_score": info.rank_score,
                "slot_fill_count": info.slot_fill_count,
                "core_role_coverage": info.core_role_coverage,
                "domain_overlap_count": info.domain_overlap_count,
                "dormant_reactivation": info.dormant_reactivation,
                "entry_signal_ids": [entry.signal_id for entry in info.entries],
                "entry_original_signal_ids": [getattr(entry, "original_signal_id", entry.signal_id) for entry in info.entries],
            })

        return {
            "matched": bool(step_b_result.matched),
            "fallback_used": bool(step_b_result.fallback_used),
            "candidate_count": len(visible_candidate_infos),
            "step_c_ready_group_count": len(getattr(step_b_result, "ready_candidate_groups", []) or []),
            "store_for_later_group_count": len(getattr(step_b_result, "store_candidate_groups", []) or []),
            "matched_scenario_count": len(getattr(step_b_result, "matched_scenarios", []) or []),
            "matched_link_count": len(getattr(step_b_result, "matched_links", []) or []),
            "route_counts": route_counts,
            "source_kind_counts": source_kind_counts,
            "candidates": candidate_dicts,
            "top_group_id": candidate_dicts[0]["group_id"] if candidate_dicts else None,
            "top_route": candidate_dicts[0]["route"] if candidate_dicts else None,
            "top_source_kind": candidate_dicts[0]["source_kind"] if candidate_dicts else None,
            "top_rank_score": candidate_dicts[0]["rank_score"] if candidate_dicts else None,
            "avg_rank_score": self._average([
                item["rank_score"] for item in candidate_dicts
            ]),
            "step_c_ready_avg_rank_score": self._average([
                item["rank_score"] for item in candidate_dicts if item["route"] == "step_c_ready"
            ]),
            "store_for_later_avg_rank_score": self._average([
                item["rank_score"] for item in candidate_dicts if item["route"] == "store_for_later"
            ]),
        }

    def _validate_case(self, case: dict, execution: dict) -> dict:
        expected = case.get("expected_step_b", {})
        validation = {
            "passed": True,
            "matched_ok": True,
            "fallback_ok": True,
            "candidate_count_ok": True,
            "route_distribution_ok": True,
            "source_kind_ok": True,
            "top_group_ok": True,
            "match_source_hits_ok": True,
            "errors": [],
        }

        if "matched" in expected and execution["matched"] != expected["matched"]:
            validation["passed"] = False
            validation["matched_ok"] = False
            validation["errors"].append(
                f"Matched mismatch: expected={expected['matched']}, actual={execution['matched']}"
            )

        if "fallback_used" in expected and execution["fallback_used"] != expected["fallback_used"]:
            validation["passed"] = False
            validation["fallback_ok"] = False
            validation["errors"].append(
                f"Fallback mismatch: expected={expected['fallback_used']}, actual={execution['fallback_used']}"
            )

        min_count = expected.get("candidate_count_at_least")
        if min_count is not None and execution["candidate_count"] < min_count:
            validation["passed"] = False
            validation["candidate_count_ok"] = False
            validation["errors"].append(
                f"Candidate count below expectation: expected>={min_count}, actual={execution['candidate_count']}"
            )

        max_count = expected.get("candidate_count_at_most")
        if max_count is not None and execution["candidate_count"] > max_count:
            validation["passed"] = False
            validation["candidate_count_ok"] = False
            validation["errors"].append(
                f"Candidate count above expectation: expected<={max_count}, actual={execution['candidate_count']}"
            )

        min_ready = expected.get("min_step_c_ready_groups")
        if min_ready is not None and execution["step_c_ready_group_count"] < min_ready:
            validation["passed"] = False
            validation["route_distribution_ok"] = False
            validation["errors"].append(
                f"Step-C-ready group count below expectation: expected>={min_ready}, actual={execution['step_c_ready_group_count']}"
            )

        min_store = expected.get("min_store_for_later_groups")
        if min_store is not None and execution["store_for_later_group_count"] < min_store:
            validation["passed"] = False
            validation["route_distribution_ok"] = False
            validation["errors"].append(
                f"Store-for-later group count below expectation: expected>={min_store}, actual={execution['store_for_later_group_count']}"
            )

        expected_source_kinds = expected.get("expected_source_kinds", [])
        actual_source_kinds = {
            item["source_kind"] for item in execution["candidates"]
        }
        missing_source_kinds = [kind for kind in expected_source_kinds if kind not in actual_source_kinds]
        if missing_source_kinds:
            validation["passed"] = False
            validation["source_kind_ok"] = False
            validation["errors"].append(
                f"Missing expected source kinds: {missing_source_kinds}, actual={sorted(actual_source_kinds)}"
            )

        top_group_prefix = expected.get("top_group_prefix")
        if top_group_prefix and not (execution["top_group_id"] or "").startswith(top_group_prefix):
            validation["passed"] = False
            validation["top_group_ok"] = False
            validation["errors"].append(
                f"Top group prefix mismatch: expected prefix={top_group_prefix}, actual={execution['top_group_id']}"
            )

        top_route = expected.get("top_route")
        if top_route and execution["top_route"] != top_route:
            validation["passed"] = False
            validation["top_group_ok"] = False
            validation["errors"].append(
                f"Top route mismatch: expected={top_route}, actual={execution['top_route']}"
            )

        min_scenario_hits = expected.get("min_scenario_hits")
        if min_scenario_hits is not None and execution["matched_scenario_count"] < min_scenario_hits:
            validation["passed"] = False
            validation["match_source_hits_ok"] = False
            validation["errors"].append(
                f"Scenario hit count below expectation: expected>={min_scenario_hits}, actual={execution['matched_scenario_count']}"
            )

        min_link_hits = expected.get("min_link_hits")
        if min_link_hits is not None and execution["matched_link_count"] < min_link_hits:
            validation["passed"] = False
            validation["match_source_hits_ok"] = False
            validation["errors"].append(
                f"Link hit count below expectation: expected>={min_link_hits}, actual={execution['matched_link_count']}"
            )

        return validation

    def _print_case_result(self, index: int, total: int, result: dict):
        case = result["case"]
        execution = result["execution"]
        validation = result["validation"]

        print(f"\n[{index}/{total}] Case: {case['case_id']}")
        print(f"Type: {case['case_type']}")
        print(f"Description: {case['description']}")
        print(
            f"Execution: matched={execution['matched']} | fallback={execution['fallback_used']} | "
            f"candidates={execution['candidate_count']} | step_c_ready={execution['step_c_ready_group_count']} | "
            f"store_for_later={execution['store_for_later_group_count']}"
        )
        print(
            f"Sources: scenario_hits={execution['matched_scenario_count']} | "
            f"link_hits={execution['matched_link_count']} | by_kind={execution['source_kind_counts']}"
        )
        if execution["candidates"]:
            print("Top candidates:")
            for candidate in execution["candidates"][:3]:
                print(
                    f"  - {candidate['group_id']} | source={candidate['source_kind']} | "
                    f"route={candidate['route']} | score={candidate['rank_score']} | "
                    f"reason={candidate['route_reason']}"
                )
        print(
            "Checks: "
            f"matched={'✅' if validation['matched_ok'] else '❌'} | "
            f"fallback={'✅' if validation['fallback_ok'] else '❌'} | "
            f"count={'✅' if validation['candidate_count_ok'] else '❌'} | "
            f"route={'✅' if validation['route_distribution_ok'] else '❌'} | "
            f"source={'✅' if validation['source_kind_ok'] else '❌'} | "
            f"top={'✅' if validation['top_group_ok'] else '❌'} | "
            f"hits={'✅' if validation['match_source_hits_ok'] else '❌'}"
        )
        print(f"Result: {'PASS' if validation['passed'] else 'FAIL'}")
        if validation["errors"]:
            print(f"Errors: {validation['errors']}")

    @staticmethod
    def _average(values: List[float]) -> Optional[float]:
        clean = [value for value in values if value is not None]
        if not clean:
            return None
        return round(sum(clean) / len(clean), 3)

    def _build_aggregate_report(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["validation"]["passed"])
        matched = sum(1 for r in self.results if r["execution"]["matched"])
        fallback_used = sum(1 for r in self.results if r["execution"]["fallback_used"])

        aggregate_route_counts = {"step_c_ready": 0, "store_for_later": 0, "discard": 0}
        aggregate_source_kind_counts = {
            "scenario_memory": 0,
            "emerging_link": 0,
            "signal_entry": 0,
        }
        top1_route_counts = {"step_c_ready": 0, "store_for_later": 0, "discard": 0, "none": 0}
        top1_source_kind_counts = {
            "scenario_memory": 0,
            "emerging_link": 0,
            "signal_entry": 0,
            "none": 0,
        }

        for result in self.results:
            execution = result["execution"]
            for route, count in execution["route_counts"].items():
                aggregate_route_counts[route] = aggregate_route_counts.get(route, 0) + count
            for kind, count in execution["source_kind_counts"].items():
                aggregate_source_kind_counts[kind] = aggregate_source_kind_counts.get(kind, 0) + count

            top_route = execution.get("top_route") or "none"
            top_source_kind = execution.get("top_source_kind") or "none"
            top1_route_counts[top_route] = top1_route_counts.get(top_route, 0) + 1
            top1_source_kind_counts[top_source_kind] = top1_source_kind_counts.get(top_source_kind, 0) + 1

        validation_summary = {}
        for key, label in [
            ("matched_ok", "Matched expectation"),
            ("fallback_ok", "Fallback expectation"),
            ("candidate_count_ok", "Candidate count"),
            ("route_distribution_ok", "Route distribution"),
            ("source_kind_ok", "Source kind coverage"),
            ("top_group_ok", "Top-group ranking"),
            ("match_source_hits_ok", "Scenario/link hit coverage"),
        ]:
            ok = sum(1 for r in self.results if r["validation"][key])
            validation_summary[key] = {
                "label": label,
                "ok": ok,
                "total": total,
                "ratio": round((ok / total), 3) if total else 0.0,
            }

        case_overview = []
        for result in self.results:
            case = result["case"]
            execution = result["execution"]
            case_overview.append({
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "passed": result["validation"]["passed"],
                "matched": execution["matched"],
                "candidate_count": execution["candidate_count"],
                "top_group_id": execution.get("top_group_id"),
                "top_route": execution.get("top_route"),
                "top_source_kind": execution.get("top_source_kind"),
                "top_rank_score": execution.get("top_rank_score"),
                "avg_rank_score": execution.get("avg_rank_score"),
                "step_c_ready_avg_rank_score": execution.get("step_c_ready_avg_rank_score"),
                "store_for_later_avg_rank_score": execution.get("store_for_later_avg_rank_score"),
            })

        return {
            "total_cases": total,
            "passed_cases": passed,
            "matched_cases": matched,
            "fallback_used_cases": fallback_used,
            "pass_rate": round((passed / total), 3) if total else 0.0,
            "matched_rate": round((matched / total), 3) if total else 0.0,
            "fallback_rate": round((fallback_used / total), 3) if total else 0.0,
            "aggregate_route_counts": aggregate_route_counts,
            "aggregate_source_kind_counts": aggregate_source_kind_counts,
            "top1_route_counts": top1_route_counts,
            "top1_source_kind_counts": top1_source_kind_counts,
            "top1_rank_score_avg": self._average([
                r["execution"].get("top_rank_score") for r in self.results
            ]),
            "candidate_rank_score_avg": self._average([
                r["execution"].get("avg_rank_score") for r in self.results
            ]),
            "step_c_ready_rank_score_avg": self._average([
                r["execution"].get("step_c_ready_avg_rank_score") for r in self.results
            ]),
            "store_for_later_rank_score_avg": self._average([
                r["execution"].get("store_for_later_avg_rank_score") for r in self.results
            ]),
            "validation_summary": validation_summary,
            "case_overview": case_overview,
        }

    def _print_summary(self):
        print("\n" + "=" * 80)
        print("Step B idealized evaluation summary")
        print("=" * 80)

        aggregate = self._build_aggregate_report()

        print(f"Total cases: {aggregate['total_cases']}")
        print(f"Passed: {aggregate['passed_cases']}/{aggregate['total_cases']} ({aggregate['pass_rate'] * 100:.0f}%)")
        print(f"Matched cases: {aggregate['matched_cases']}/{aggregate['total_cases']} ({aggregate['matched_rate'] * 100:.0f}%)")
        print(f"Fallback-used cases: {aggregate['fallback_used_cases']}/{aggregate['total_cases']} ({aggregate['fallback_rate'] * 100:.0f}%)")
        print(f"Aggregate route counts: {aggregate['aggregate_route_counts']}")
        print(f"Aggregate source-kind counts: {aggregate['aggregate_source_kind_counts']}")
        print(f"Top-1 route counts: {aggregate['top1_route_counts']}")
        print(f"Top-1 source-kind counts: {aggregate['top1_source_kind_counts']}")
        print(
            "Average scores: "
            f"top1={aggregate['top1_rank_score_avg']} | "
            f"all_candidates={aggregate['candidate_rank_score_avg']} | "
            f"step_c_ready={aggregate['step_c_ready_rank_score_avg']} | "
            f"store_for_later={aggregate['store_for_later_rank_score_avg']}"
        )

        for item in aggregate["case_overview"]:
            print(
                f"Case overview: {item['case_id']} | passed={item['passed']} | matched={item['matched']} | "
                f"top={item['top_group_id']} | route={item['top_route']} | source={item['top_source_kind']} | "
                f"score={item['top_rank_score']}"
            )

        for summary in aggregate["validation_summary"].values():
            print(f"{summary['label']}: {summary['ok']}/{summary['total']} ({summary['ratio'] * 100:.0f}%)")

        overall_pass = aggregate["passed_cases"] == aggregate["total_cases"]
        print(
            f"\nConclusion: {'[PASS] Step B baseline observable and diff-friendly' if overall_pass else '[FAIL] review sample expectations or ranking behavior'}"
        )

    def _resolve_report_dir(self) -> str:
        if self.report_dir:
            return os.path.abspath(self.report_dir)
        return os.path.join(os.path.dirname(__file__), "eval_outputs", "step_b")

    def _build_report_filename(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_part = self.case_id or "all_cases"
        return f"step_b_eval_{STEP_B_IDEALIZED_EVAL_CASES_VERSION}_{case_part}_{timestamp}.json"

    def _write_report(self, report: dict) -> str:
        report_dir = self._resolve_report_dir()
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, self._build_report_filename())
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report_path

    def _build_json_report(self) -> dict:
        aggregate = self._build_aggregate_report()
        return {
            "runner": "run_step_b_idealized_eval.py",
            "sample_version": STEP_B_IDEALIZED_EVAL_CASES_VERSION,
            "runtime_mode": "rules_only",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "case_scope": self.case_id or "all_cases",
            "aggregate": aggregate,
            "results": self.results,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step B idealized evaluation samples")
    parser.add_argument("--case-id", help="Run only one case by case_id")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failed case")
    parser.add_argument("--json", action="store_true", help="Print JSON report instead of console summary")
    parser.add_argument("--save-report", action="store_true", help="Save the JSON report to disk for version-to-version comparison")
    parser.add_argument("--report-dir", help="Optional directory used when saving evaluation reports")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    runner = StepBIdealizedEvalRunner(
        case_id=args.case_id,
        json_output=args.json,
        fail_fast=args.fail_fast,
        save_report=args.save_report,
        report_dir=args.report_dir,
    )
    runner.run()
