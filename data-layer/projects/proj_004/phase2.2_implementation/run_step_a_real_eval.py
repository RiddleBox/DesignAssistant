"""
Phase 2.2 Step A real evaluation runner.

Important:
- This runner evaluates first-round real-source Step A samples.
- It must remain separated from idealized synthetic samples.
- It mirrors the production policy where batches <= 15 skip Step A.

Usage examples:
- python run_step_a_real_eval.py
- python run_step_a_real_eval.py --mode rules
- python run_step_a_real_eval.py --mode llm
- python run_step_a_real_eval.py --case-id step_a_real_cross_domain_mobile_distribution_001
"""

import argparse
import json
from datetime import datetime
from typing import List, Optional

from judgment_engine import JudgmentEngine
from step_a_cluster import run_step_a
from step_a_real_eval_samples import (
    REAL_SAMPLE_DATA_NATURE,
    STEP_A_REAL_EVAL_CASES_VERSION,
    STEP_A_REAL_EVAL_SAMPLES,
)


SMALL_BATCH_THRESHOLD = 15


class StepARealEvalRunner:
    """Runner for first-round real Step A evaluation samples."""

    def __init__(
        self,
        mode: str = "auto",
        case_id: Optional[str] = None,
        fail_fast: bool = False,
        json_output: bool = False,
    ):
        self.mode = mode
        self.case_id = case_id
        self.fail_fast = fail_fast
        self.json_output = json_output
        self.results: List[dict] = []

        self.engine = self._build_engine(mode)
        self.llm_client = self.engine._llm
        self.model = self.engine.model
        self.runtime_mode = self._resolve_runtime_mode(mode, self.llm_client)

    def _build_engine(self, mode: str) -> JudgmentEngine:
        if mode == "rules":
            return JudgmentEngine(api_key="")

        engine = JudgmentEngine()
        if mode == "llm" and not engine._llm:
            raise RuntimeError("LLM mode requested but no Step A / 2.2 LLM client is available")
        return engine

    @staticmethod
    def _resolve_runtime_mode(requested_mode: str, llm_client) -> str:
        if requested_mode == "rules":
            return "rules"
        if requested_mode == "llm":
            return "llm"
        return "llm" if llm_client else "rules(auto_fallback)"

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

        if self.json_output:
            print(json.dumps(self._build_json_report(), ensure_ascii=False, indent=2))
        else:
            self._print_summary()

    def _get_target_cases(self) -> List[dict]:
        if self.case_id:
            matches = [
                case for case in STEP_A_REAL_EVAL_SAMPLES
                if case["case_id"] == self.case_id
            ]
            if not matches:
                raise ValueError(f"Case not found: {self.case_id}")
            return matches
        return STEP_A_REAL_EVAL_SAMPLES

    def _run_case(self, case: dict) -> dict:
        signals = [dict(signal) for signal in case["signals"]]
        effective_batch_size = case.get("batch_size", len(signals))
        expected = case.get("expected_step_a", {})

        if effective_batch_size <= SMALL_BATCH_THRESHOLD:
            execution = {
                "step_a_skipped": True,
                "skip_reason": "small_batch_threshold",
                "effective_batch_size": effective_batch_size,
                "signal_count": len(signals),
                "logical_scenarios": [],
                "role_annotations": {},
                "isolated_signal_ids": [s["signal_id"] for s in signals],
                "fallback_used": False,
            }
        else:
            step_a_result = run_step_a(
                enriched_signals=signals,
                llm_client=self.llm_client,
                model=self.model,
            )
            execution = {
                "step_a_skipped": False,
                "skip_reason": None,
                "effective_batch_size": effective_batch_size,
                "signal_count": len(signals),
                "logical_scenarios": [sc.to_dict() for sc in step_a_result.logical_scenarios],
                "role_annotations": step_a_result.role_annotations,
                "isolated_signal_ids": [
                    s.get("signal_id") or s.get("id") for s in step_a_result.isolated_signals
                ],
                "fallback_used": step_a_result.fallback_used,
            }

        validation = self._validate_case(case, execution)
        baseline_metrics = self._extract_case_baseline_metrics(case, execution, validation)

        return {
            "case": case,
            "execution": execution,
            "validation": validation,
            "baseline_metrics": baseline_metrics,
        }

    def _validate_case(self, case: dict, execution: dict) -> dict:
        expected = case.get("expected_step_a", {})
        signals = case["signals"]
        signal_ids = {s["signal_id"] for s in signals}
        scenarios = execution["logical_scenarios"]

        validation = {
            "passed": True,
            "skip_policy_match": True,
            "scenario_count_match": True,
            "expected_core_match": True,
            "forbidden_pairings_ok": True,
            "annotations_complete": True,
            "isolated_coverage_ok": True,
            "errors": [],
        }

        should_skip = bool(expected.get("should_skip_step_a"))
        if should_skip:
            if not execution["step_a_skipped"]:
                validation["passed"] = False
                validation["skip_policy_match"] = False
                validation["errors"].append("Expected Step A to be skipped, but it was executed")
            if expected.get("expected_reason") and execution["skip_reason"] != expected.get("expected_reason"):
                validation["passed"] = False
                validation["skip_policy_match"] = False
                validation["errors"].append(
                    f"Skip reason mismatch: expected={expected.get('expected_reason')}, actual={execution['skip_reason']}"
                )
            return validation

        if execution["step_a_skipped"]:
            validation["passed"] = False
            validation["skip_policy_match"] = False
            validation["errors"].append(
                "Expected Step A execution, but sample fell into small-batch direct-pass branch"
            )
            return validation

        scenario_checks_enabled = self.runtime_mode.startswith("llm")
        if scenario_checks_enabled:
            scenario_count = len(scenarios)
            min_scenarios = expected.get("min_scenarios")
            max_scenarios = expected.get("max_scenarios")

            if min_scenarios is not None and scenario_count < min_scenarios:
                validation["passed"] = False
                validation["scenario_count_match"] = False
                validation["errors"].append(
                    f"Scenario count below expectation: expected>={min_scenarios}, actual={scenario_count}"
                )
            if max_scenarios is not None and scenario_count > max_scenarios:
                validation["passed"] = False
                validation["scenario_count_match"] = False
                validation["errors"].append(
                    f"Scenario count above expectation: expected<={max_scenarios}, actual={scenario_count}"
                )

            primary_sets = [set(sc.get("primary_signal_ids", [])) for sc in scenarios]
            full_sets = [
                set(sc.get("primary_signal_ids", [])) | set(sc.get("context_signal_ids", []))
                for sc in scenarios
            ]

            expected_core_signal_ids = expected.get("expected_core_signal_ids")
            if expected_core_signal_ids:
                expected_core = set(expected_core_signal_ids)
                if not any(expected_core.issubset(primary_ids) for primary_ids in primary_sets):
                    validation["passed"] = False
                    validation["expected_core_match"] = False
                    validation["errors"].append(
                        f"Expected core signals not found in any scenario primary set: {expected_core_signal_ids}"
                    )

            expected_core_signal_sets = expected.get("expected_core_signal_sets", [])
            for expected_set in expected_core_signal_sets:
                expected_core = set(expected_set)
                if not any(expected_core.issubset(primary_ids) for primary_ids in primary_sets):
                    validation["passed"] = False
                    validation["expected_core_match"] = False
                    validation["errors"].append(
                        f"Expected core signal set not found in any scenario primary set: {expected_set}"
                    )

            for pair in expected.get("forbidden_pairings", []):
                pair_set = set(pair)
                if any(pair_set.issubset(signal_set) for signal_set in full_sets):
                    validation["passed"] = False
                    validation["forbidden_pairings_ok"] = False
                    validation["errors"].append(f"Forbidden pairing detected inside one scenario: {pair}")

        annotations = execution["role_annotations"]
        if not execution["step_a_skipped"]:
            if set(annotations.keys()) != signal_ids:
                validation["passed"] = False
                validation["annotations_complete"] = False
                validation["errors"].append(
                    f"Role annotation coverage mismatch: expected={sorted(signal_ids)}, actual={sorted(annotations.keys())}"
                )
            else:
                for sid, ann in annotations.items():
                    if not ann.get("roles") or not ann.get("domains"):
                        validation["passed"] = False
                        validation["annotations_complete"] = False
                        validation["errors"].append(f"Incomplete annotation for signal {sid}")

        isolated_ids = set(execution["isolated_signal_ids"])
        if isolated_ids != signal_ids:
            validation["passed"] = False
            validation["isolated_coverage_ok"] = False
            validation["errors"].append(
                f"Isolated signal coverage mismatch: expected={sorted(signal_ids)}, actual={sorted(isolated_ids)}"
            )

        return validation

    def _extract_case_baseline_metrics(self, case: dict, execution: dict, validation: dict) -> dict:
        scenarios = execution["logical_scenarios"]
        case_type = case.get("case_type")
        expected = case.get("expected_step_a", {})

        primary_sets = [set(sc.get("primary_signal_ids", [])) for sc in scenarios]
        expected_core_signal_ids = expected.get("expected_core_signal_ids") or []
        expected_core_signal_sets = expected.get("expected_core_signal_sets", [])

        expected_core_match = False
        if expected_core_signal_ids:
            expected_core = set(expected_core_signal_ids)
            expected_core_match = any(expected_core.issubset(primary_ids) for primary_ids in primary_sets)
        elif expected_core_signal_sets:
            expected_core_match = any(
                set(expected_set).issubset(primary_ids)
                for expected_set in expected_core_signal_sets
                for primary_ids in primary_sets
            )

        logical_scenario_hit = False
        if case_type == "cross_domain_positive":
            logical_scenario_hit = len(scenarios) > 0 and expected_core_match
        elif case_type == "semantic_similarity_negative":
            logical_scenario_hit = len(scenarios) == 0
        elif case_type == "small_batch_direct_pass":
            logical_scenario_hit = execution["step_a_skipped"]

        cross_domain_recall_hit = case_type == "cross_domain_positive" and len(scenarios) > 0 and expected_core_match
        semantic_similarity_false_positive = case_type == "semantic_similarity_negative" and len(scenarios) > 0
        step_c_effective_opportunity_ready = case_type == "cross_domain_positive" and len(scenarios) > 0 and expected_core_match

        return {
            "logical_scenarios_hit": logical_scenario_hit,
            "cross_domain_recall_hit": cross_domain_recall_hit,
            "semantic_similarity_false_positive": semantic_similarity_false_positive,
            "step_c_effective_opportunity_ready": step_c_effective_opportunity_ready,
        }

    def _aggregate_baseline_metrics(self) -> dict:
        total = len(self.results)
        if total == 0:
            return {}

        cross_domain_cases = [r for r in self.results if r["case"]["case_type"] == "cross_domain_positive"]
        negative_cases = [r for r in self.results if r["case"]["case_type"] == "semantic_similarity_negative"]

        logical_hits = sum(1 for r in self.results if r["baseline_metrics"]["logical_scenarios_hit"])
        cross_domain_hits = sum(1 for r in cross_domain_cases if r["baseline_metrics"]["cross_domain_recall_hit"])
        semantic_fp = sum(1 for r in negative_cases if r["baseline_metrics"]["semantic_similarity_false_positive"])
        step_c_ready = sum(1 for r in self.results if r["baseline_metrics"]["step_c_effective_opportunity_ready"])

        return {
            "logical_scenarios_hit_rate": logical_hits / total,
            "cross_domain_recall_rate": (cross_domain_hits / len(cross_domain_cases)) if cross_domain_cases else 0.0,
            "semantic_similarity_false_positive_rate": (semantic_fp / len(negative_cases)) if negative_cases else 0.0,
            "step_c_effective_opportunity_ready_rate": step_c_ready / total,
        }

    def _print_header(self, cases: List[dict]):
        print("=" * 80)
        print("Phase 2.2 Step A - Real Evaluation Runner")
        print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sample version: {STEP_A_REAL_EVAL_CASES_VERSION}")
        print(f"Sample count: {len(cases)}")
        print(f"Requested mode: {self.mode}")
        print(f"Runtime mode: {self.runtime_mode}")
        print(f"Small-batch threshold: <= {SMALL_BATCH_THRESHOLD}")
        print(f"Data scope: {REAL_SAMPLE_DATA_NATURE}")
        print("=" * 80)

    def _print_case_result(self, index: int, total: int, result: dict):
        case = result["case"]
        execution = result["execution"]
        validation = result["validation"]
        baseline = result["baseline_metrics"]

        print(f"\n[{index}/{total}] Case: {case['case_id']}")
        print(f"Type: {case['case_type']}")
        print(f"Description: {case['description']}")
        print(
            f"Effective batch size: {execution['effective_batch_size']} "
            f"| represented signals: {execution['signal_count']}"
        )

        if execution["step_a_skipped"]:
            print(f"Execution: skipped Step A ({execution['skip_reason']})")
        else:
            print(
                f"Execution: Step A ran | scenarios={len(execution['logical_scenarios'])} "
                f"| fallback_used={execution['fallback_used']}"
            )
            for scenario in execution["logical_scenarios"]:
                print(
                    f"  - {scenario['scenario_id']}: primary={scenario['primary_signal_ids']} "
                    f"| context={scenario['context_signal_ids']}"
                )

        print(
            "Baseline: "
            f"logical_hit={'✅' if baseline['logical_scenarios_hit'] else '❌'} | "
            f"cross_domain={'✅' if baseline['cross_domain_recall_hit'] else '❌'} | "
            f"semantic_fp={'⚠️' if baseline['semantic_similarity_false_positive'] else '✅'} | "
            f"step_c_ready={'✅' if baseline['step_c_effective_opportunity_ready'] else '❌'}"
        )
        print(f"Result: {'PASS' if validation['passed'] else 'FAIL'}")
        if validation["errors"]:
            print(f"Errors: {validation['errors']}")

    def _print_summary(self):
        print("\n" + "=" * 80)
        print("Step A real evaluation summary")
        print("=" * 80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["validation"]["passed"])
        skipped = sum(1 for r in self.results if r["execution"]["step_a_skipped"])
        executed = total - skipped
        fallback_used = sum(
            1 for r in self.results
            if (not r["execution"]["step_a_skipped"]) and r["execution"]["fallback_used"]
        )
        baseline = self._aggregate_baseline_metrics()

        print(f"Total cases: {total}")
        print(f"Passed: {passed}/{total} ({(passed / total * 100) if total else 0:.0f}%)")
        print(f"Executed Step A: {executed}")
        print(f"Skipped by small-batch policy: {skipped}")
        print(f"Fallback-used executions: {fallback_used}")
        print("\nFirst-round baseline metrics:")
        print(f"- logical_scenarios hit rate: {baseline.get('logical_scenarios_hit_rate', 0.0):.2%}")
        print(f"- cross-domain recall rate: {baseline.get('cross_domain_recall_rate', 0.0):.2%}")
        print(f"- semantic-similarity false-positive rate: {baseline.get('semantic_similarity_false_positive_rate', 0.0):.2%}")
        print(f"- Step C effective-opportunity-ready rate: {baseline.get('step_c_effective_opportunity_ready_rate', 0.0):.2%}")

        overall_pass = passed == total
        print(f"\nConclusion: {'[PASS] first-round real baseline runnable' if overall_pass else '[WARN] baseline runnable, but some real cases need review'}")

    def _build_json_report(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["validation"]["passed"])
        return {
            "runner": "run_step_a_real_eval.py",
            "sample_version": STEP_A_REAL_EVAL_CASES_VERSION,
            "data_nature": REAL_SAMPLE_DATA_NATURE,
            "requested_mode": self.mode,
            "runtime_mode": self.runtime_mode,
            "small_batch_threshold": SMALL_BATCH_THRESHOLD,
            "total_cases": total,
            "passed_cases": passed,
            "baseline_metrics": self._aggregate_baseline_metrics(),
            "results": self.results,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step A real evaluation samples")
    parser.add_argument(
        "--mode",
        choices=["auto", "llm", "rules"],
        default="auto",
        help="Execution mode. auto=prefer configured LLM and fallback to rules, llm=LLM required, rules=force no LLM",
    )
    parser.add_argument("--case-id", help="Run only one case by case_id")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failed case")
    parser.add_argument("--json", action="store_true", help="Print JSON report instead of console summary")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    runner = StepARealEvalRunner(
        mode=args.mode,
        case_id=args.case_id,
        fail_fast=args.fail_fast,
        json_output=args.json,
    )
    runner.run()
