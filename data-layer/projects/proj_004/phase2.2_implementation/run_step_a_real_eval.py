"""
Phase 2.2 Step A real-sample evaluation runner.

Important:
- This runner evaluates real samples from background/real_intel_samples.
- Offline evaluation uses the stable fixture pool at the root plus the snapshot expansion pool under incoming/.
- It should not depend on processed/ because processed/ represents online pipeline state rather than evaluation semantics.
- It complements, rather than replaces, the idealized evaluation runner.
- The first version focuses on a minimal executable baseline for layered evaluation.

Usage examples:
- python run_step_a_real_eval.py
- python run_step_a_real_eval.py --mode rules
- python run_step_a_real_eval.py --mode llm
- python run_step_a_real_eval.py --case-id step_a_real_medium_mixed_001
- python run_step_a_real_eval.py --json
- python run_step_a_real_eval.py --fixture-mode prefer_fixture --json
- python run_step_a_real_eval.py --fixture-mode fixture_only --json
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(CURRENT_DIR)
DA_ROOT = os.path.normpath(os.path.join(PROJ_DIR, "..", "..", ".."))
REAL_SAMPLE_ROOT = os.path.join(DA_ROOT, "background", "real_intel_samples")
PHASE21_DIR = os.path.join(PROJ_DIR, "phase2.1_implementation")
PHASE22_DIR = os.path.join(PROJ_DIR, "phase2.2_implementation")

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def load_module(name, path, dep_modules=None):
    if dep_modules:
        for dep_name, dep_mod in dep_modules.items():
            sys.modules[dep_name] = dep_mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    if dep_modules:
        for dep_name in dep_modules:
            if dep_name != name:
                sys.modules.pop(dep_name, None)
    return mod


def load_llm_config(phase: str) -> dict:
    spec = importlib.util.spec_from_file_location("llm_config_eval", os.path.join(PROJ_DIR, "llm_config.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["llm_config_eval"] = mod
    spec.loader.exec_module(mod)
    return mod.get_llm_config(phase)


m22_schemas = load_module("schemas_22_eval", os.path.join(PHASE22_DIR, "schemas.py"))
m22_validators = load_module(
    "validators_eval",
    os.path.join(PHASE22_DIR, "validators.py"),
    dep_modules={"schemas": m22_schemas},
)
judgment_mod = load_module(
    "judgment_engine_eval",
    os.path.join(PHASE22_DIR, "judgment_engine.py"),
    dep_modules={"schemas": m22_schemas, "validators": m22_validators},
)
JudgmentEngine = judgment_mod.JudgmentEngine

m21_schemas = load_module("schemas_21_eval", os.path.join(PHASE21_DIR, "schemas.py"))
m21_prompts = load_module(
    "prompt_templates_eval",
    os.path.join(PHASE21_DIR, "prompt_templates.py"),
    dep_modules={"schemas": m21_schemas},
)
decoder_mod = load_module(
    "decoder_eval",
    os.path.join(PHASE21_DIR, "decoder.py"),
    dep_modules={"schemas": m21_schemas, "prompt_templates": m21_prompts},
)
IntelligenceDecoder = decoder_mod.IntelligenceDecoder
IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest

from step_a_cluster import run_step_a
from step_a_real_eval_samples import (
    REAL_SAMPLE_DATA_NATURE,
    STEP_A_REAL_EVAL_CASES_VERSION,
    STEP_A_REAL_EVAL_SAMPLES,
)


PHASE21_LLM_CONFIG = load_llm_config("2.1")

SMALL_BATCH_THRESHOLD = 15
REAL_EVAL_CONNECT_TIMEOUT_SECONDS = 5
REAL_EVAL_READ_TIMEOUT_SECONDS = 15
REAL_EVAL_MAX_RETRIES = 1
REAL_EVAL_DECODE_TIMEOUT_SECONDS = 15
REAL_EVAL_FIXTURE_ROOT = os.path.join(PHASE22_DIR, "real_eval_decode_fixtures")


def build_phase21_decoder(
    fast_decode: bool = True,
    connect_timeout_seconds: int = REAL_EVAL_CONNECT_TIMEOUT_SECONDS,
    read_timeout_seconds: int = REAL_EVAL_READ_TIMEOUT_SECONDS,
    max_retries: int = REAL_EVAL_MAX_RETRIES,
) -> IntelligenceDecoder:
    if not PHASE21_LLM_CONFIG.get("api_key"):
        raise RuntimeError(
            "Phase 2.1 LLM config is missing api_key; real-sample Step A evaluation requires real decode output"
        )

    # Real evaluation temporarily defaults to fast decode so we can unblock baseline runs.
    # After Phase 2.1 connectivity and timeout issues are stabilized, rerun with two-stage on.
    return IntelligenceDecoder(
        api_key=PHASE21_LLM_CONFIG.get("api_key", ""),
        model=PHASE21_LLM_CONFIG.get("model", "claude-opus-4-6"),
        provider=PHASE21_LLM_CONFIG.get("provider", "anthropic"),
        base_url=PHASE21_LLM_CONFIG.get("base_url", ""),
        enable_two_stage=not fast_decode,
        connect_timeout_seconds=connect_timeout_seconds,
        read_timeout_seconds=read_timeout_seconds,
        max_retries=max_retries,
    )


def run_internal_decode_sample(
    relative_path: str,
    fast_decode: bool = True,
    connect_timeout_seconds: int = REAL_EVAL_CONNECT_TIMEOUT_SECONDS,
    read_timeout_seconds: int = REAL_EVAL_READ_TIMEOUT_SECONDS,
    max_retries: int = REAL_EVAL_MAX_RETRIES,
) -> int:
    print(
        f"[internal-decode] start relative_path={relative_path} fast_decode={fast_decode}",
        file=sys.stderr,
        flush=True,
    )
    abs_path = os.path.join(REAL_SAMPLE_ROOT, relative_path)
    if not os.path.exists(abs_path):
        processed_candidates = [
            os.path.join(REAL_SAMPLE_ROOT, "processed", relative_path.replace("/", os.sep)),
            os.path.join(REAL_SAMPLE_ROOT, "processed", os.path.basename(relative_path)),
        ]
        for candidate_path in processed_candidates:
            if os.path.exists(candidate_path):
                abs_path = candidate_path
                break
        else:
            print(json.dumps({
                "ok": False,
                "relative_path": relative_path,
                "error": f"Real sample file not found: {relative_path}",
            }, ensure_ascii=True))
            return 1

    with open(abs_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    payload = dict(payload)
    payload.pop("_noise_label", None)

    try:
        request = IntelligenceDecodeRequest(**payload)
        decoder = build_phase21_decoder(
            fast_decode=fast_decode,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
            max_retries=max_retries,
        )
        print(
            f"[internal-decode] request_ready source_id={payload.get('source_id', 'unknown')}",
            file=sys.stderr,
            flush=True,
        )
        result = decoder.decode(request)
        print(
            f"[internal-decode] decode_done source_id={payload.get('source_id', 'unknown')}",
            file=sys.stderr,
            flush=True,
        )
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result
        print(json.dumps({
            "ok": True,
            "relative_path": relative_path,
            "source_id": payload.get("source_id", "unknown"),
            "payload": payload,
            "result": result_dict,
        }, ensure_ascii=True))
        return 0
    except Exception as e:
        print(
            f"[internal-decode] error source_id={payload.get('source_id', 'unknown')} error={str(e)}",
            file=sys.stderr,
            flush=True,
        )
        print(json.dumps({
            "ok": False,
            "relative_path": relative_path,
            "source_id": payload.get("source_id", "unknown"),
            "error": str(e),
        }, ensure_ascii=True))
        return 1


class StepARealEvalRunner:
    """Runner for Step A real-sample layered evaluation."""

    def __init__(
        self,
        mode: str = "auto",
        case_id: Optional[str] = None,
        fail_fast: bool = False,
        json_output: bool = False,
        verbose: bool = False,
        fast_decode: bool = True,
        connect_timeout_seconds: int = REAL_EVAL_CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds: int = REAL_EVAL_READ_TIMEOUT_SECONDS,
        max_retries: int = REAL_EVAL_MAX_RETRIES,
        decode_timeout_seconds: int = REAL_EVAL_DECODE_TIMEOUT_SECONDS,
        decode_execution_mode: str = "subprocess",
        fixture_mode: str = "prefer_fixture",
        fixture_root: str = REAL_EVAL_FIXTURE_ROOT,
        max_parallel_decodes: int = 3,
        report_output_path: Optional[str] = None,
        sample_paths: Optional[List[str]] = None,
        ad_hoc_run_label: str = "ad_hoc_batch",
    ):
        self.mode = mode
        self.case_id = case_id
        self.fail_fast = fail_fast
        self.json_output = json_output
        self.verbose = verbose
        self.fast_decode = fast_decode
        self.connect_timeout_seconds = connect_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.max_retries = max_retries
        self.decode_timeout_seconds = decode_timeout_seconds
        self.decode_execution_mode = decode_execution_mode
        self.fixture_mode = fixture_mode
        self.fixture_root = fixture_root
        self.max_parallel_decodes = max(1, int(max_parallel_decodes or 1))
        self.report_output_path = report_output_path
        self.sample_paths = list(sample_paths or [])
        self.ad_hoc_run_label = ad_hoc_run_label or "ad_hoc_batch"
        self.results: List[dict] = []
        self.decode_cache: Dict[str, dict] = {}

        self.engine = self._build_engine(mode)
        self.llm_client = self.engine._llm
        self.model = self.engine.model
        self.runtime_mode = self._resolve_runtime_mode(mode, self.llm_client)
        self.decoder = self._build_decoder(mode)

    def _log(self, message: str):
        if self.verbose:
            print(f"[real-eval] {message}", flush=True)

    def _build_engine(self, mode: str) -> JudgmentEngine:
        if mode == "rules":
            return JudgmentEngine(api_key="")

        engine = JudgmentEngine()
        if mode == "llm" and not engine._llm:
            raise RuntimeError("LLM mode requested but no Step A / 2.2 LLM client is available")
        return engine

    def _build_decoder(self, mode: str) -> IntelligenceDecoder:
        decoder = build_phase21_decoder(
            fast_decode=self.fast_decode,
            connect_timeout_seconds=self.connect_timeout_seconds,
            read_timeout_seconds=self.read_timeout_seconds,
            max_retries=self.max_retries,
        )
        self._log(
            f"Initialized Phase 2.1 decoder provider={PHASE21_LLM_CONFIG.get('provider', 'anthropic')} "
            f"model={PHASE21_LLM_CONFIG.get('model', 'claude-opus-4-6')} "
            f"two_stage={'off' if self.fast_decode else 'on'} "
            f"timeout=({self.connect_timeout_seconds},{self.read_timeout_seconds}) "
            f"retries={self.max_retries} decode_timeout={self.decode_timeout_seconds}"
        )
        return decoder

    def _build_fixture_path(self, relative_path: str) -> str:
        sanitized_relative_path = relative_path.replace("/", os.sep)
        fixture_relative_path = f"{sanitized_relative_path}.decoded.json"
        return os.path.join(self.fixture_root, fixture_relative_path)

    def _load_decode_fixture(self, relative_path: str) -> Optional[dict]:
        fixture_path = self._build_fixture_path(relative_path)
        if not os.path.exists(fixture_path):
            return None

        with open(fixture_path, "r", encoding="utf-8") as f:
            fixture_payload = json.load(f)

        result_payload = fixture_payload.get("result")
        if not result_payload:
            raise ValueError(f"Decode fixture is missing result payload: {fixture_path}")

        result_obj = m21_schemas.DecodedIntelligence(**result_payload)
        return {
            "ok": True,
            "relative_path": fixture_payload.get("relative_path", relative_path),
            "source_id": fixture_payload.get("source_id", "unknown"),
            "elapsed_seconds": fixture_payload.get("elapsed_seconds"),
            "payload": fixture_payload.get("payload", {}),
            "result": result_obj,
            "fixture_path": fixture_path,
            "fixture_hit": True,
            "fixture_metadata": fixture_payload.get("fixture_metadata", {}),
        }

    def _save_decode_fixture(self, decode_result: dict):
        if not decode_result.get("ok"):
            return

        fixture_path = self._build_fixture_path(decode_result["relative_path"])
        os.makedirs(os.path.dirname(fixture_path), exist_ok=True)
        result_obj = decode_result["result"]
        result_payload = result_obj.model_dump() if hasattr(result_obj, "model_dump") else result_obj
        fixture_document = {
            "relative_path": decode_result["relative_path"],
            "source_id": decode_result["source_id"],
            "elapsed_seconds": decode_result.get("elapsed_seconds"),
            "payload": decode_result.get("payload", {}),
            "result": result_payload,
            "fixture_metadata": {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "fast_decode": self.fast_decode,
                "connect_timeout_seconds": self.connect_timeout_seconds,
                "read_timeout_seconds": self.read_timeout_seconds,
                "max_retries": self.max_retries,
                "decode_execution_mode": self.decode_execution_mode,
            },
        }
        with open(fixture_path, "w", encoding="utf-8") as f:
            json.dump(fixture_document, f, ensure_ascii=False, indent=2)

    def _decode_sample_inline(self, item: dict, payload: dict, source_id: str):
        started_at = time.perf_counter()
        try:
            request = IntelligenceDecodeRequest(**payload)
            result_obj = self.decoder.decode(request)
            elapsed_seconds = round(time.perf_counter() - started_at, 3)
            return {
                "ok": True,
                "relative_path": item["relative_path"],
                "source_id": source_id,
                "elapsed_seconds": elapsed_seconds,
                "payload": payload,
                "result": result_obj,
                "fixture_hit": False,
            }
        except Exception as e:
            elapsed_seconds = round(time.perf_counter() - started_at, 3)
            return {
                "ok": False,
                "relative_path": item["relative_path"],
                "source_id": source_id,
                "elapsed_seconds": elapsed_seconds,
                "error": str(e),
                "fixture_hit": False,
            }

    def _decode_sample_subprocess(self, item: dict, payload: dict, source_id: str):
        command = [
            sys.executable,
            "-u",
            os.path.abspath(__file__),
            "--internal-decode-sample",
            item["relative_path"],
            "--internal-connect-timeout",
            str(self.connect_timeout_seconds),
            "--internal-read-timeout",
            str(self.read_timeout_seconds),
            "--internal-max-retries",
            str(self.max_retries),
        ]
        if not self.fast_decode:
            command.append("--internal-keep-two-stage")

        started_at = time.perf_counter()
        proc = None
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=PROJ_DIR,
            )
            stdout_text, stderr_text = proc.communicate(timeout=self.decode_timeout_seconds)
            elapsed_seconds = round(time.perf_counter() - started_at, 3)
            stdout_text = (stdout_text or "").strip()
            stderr_text = (stderr_text or "").strip()
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "relative_path": item["relative_path"],
                    "source_id": source_id,
                    "elapsed_seconds": elapsed_seconds,
                    "error": stderr_text or stdout_text or f"decode subprocess failed with code {proc.returncode}",
                }

            output_lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
            if not output_lines:
                return {
                    "ok": False,
                    "relative_path": item["relative_path"],
                    "source_id": source_id,
                    "elapsed_seconds": elapsed_seconds,
                    "error": "decode subprocess returned empty stdout",
                }

            parsed = json.loads(output_lines[-1])
            if not parsed.get("ok"):
                return {
                    "ok": False,
                    "relative_path": item["relative_path"],
                    "source_id": parsed.get("source_id", source_id),
                    "elapsed_seconds": elapsed_seconds,
                    "error": parsed.get("error", "unknown decode error"),
                }

            result_obj = m21_schemas.DecodedIntelligence(**parsed["result"])
            return {
                "ok": True,
                "relative_path": item["relative_path"],
                "source_id": parsed.get("source_id", source_id),
                "elapsed_seconds": elapsed_seconds,
                "payload": parsed.get("payload", payload),
                "result": result_obj,
                "fixture_hit": False,
            }
        except subprocess.TimeoutExpired:
            if proc is not None:
                proc.kill()
                timeout_stdout, timeout_stderr = proc.communicate()
            else:
                timeout_stdout, timeout_stderr = "", ""
            elapsed_seconds = round(time.perf_counter() - started_at, 3)
            timeout_stdout = (timeout_stdout or "").strip()
            timeout_stderr = (timeout_stderr or "").strip()
            timeout_detail = timeout_stderr or timeout_stdout or "no subprocess output captured before kill"
            return {
                "ok": False,
                "relative_path": item["relative_path"],
                "source_id": source_id,
                "elapsed_seconds": elapsed_seconds,
                "error": f"decode subprocess timeout after {self.decode_timeout_seconds}s",
                "timeout_detail": timeout_detail,
            }
        except Exception as e:
            elapsed_seconds = round(time.perf_counter() - started_at, 3)
            return {
                "ok": False,
                "relative_path": item["relative_path"],
                "source_id": source_id,
                "elapsed_seconds": elapsed_seconds,
                "error": str(e),
            }

    @staticmethod
    def _resolve_runtime_mode(requested_mode: str, llm_client) -> str:
        if requested_mode == "rules":
            return "rules"
        if requested_mode == "llm":
            return "llm"
        return "llm" if llm_client else "rules(auto_fallback)"

    def run(self):
        if self.sample_paths:
            result = self._run_ad_hoc_batch()
            self.results = [result]

            if self.json_output:
                report = self._build_json_report()
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                self._print_header([result["case"]])
                self._print_case_result(1, 1, result)
                self._print_summary()

            self._write_json_report(self._build_json_report())
            return

        cases = self._get_target_cases()

        if not self.json_output:
            self._print_header(cases)
        else:
            self._log(f"Loaded {len(cases)} cases for JSON execution")

        for index, case in enumerate(cases, 1):
            self._log(f"Starting case {index}/{len(cases)}: {case['case_id']}")
            result = self._run_case(case)
            self.results.append(result)
            self._log(f"Finished case {case['case_id']} with passed={result['validation']['passed']}")

            if not self.json_output:
                self._print_case_result(index, len(cases), result)

            if self.fail_fast and not result["validation"]["passed"]:
                self._log("Fail-fast triggered; stopping evaluation")
                break

        report = self._build_json_report() if (self.json_output or self.report_output_path) else None
        if self.json_output and report is not None:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self._print_summary()

        if report is not None:
            self._write_json_report(report)

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
        loaded_samples = self._load_case_samples(case)
        self._log(f"Loaded {len(loaded_samples)} sample files for {case['case_id']}")

        self._log(f"Decoding loaded samples for {case['case_id']}")
        decoded_samples, decode_errors = self._decode_case_samples(loaded_samples)
        self._log(
            f"Decoded {len(decoded_samples)} samples for {case['case_id']} with {len(decode_errors)} decode errors"
        )

        signals, source_signal_map = self._build_enriched_signals(decoded_samples)
        effective_batch_size = len(signals)
        self._log(f"Built {effective_batch_size} enriched signals for {case['case_id']}")
        expected = case.get("expected_step_a", {})

        if effective_batch_size <= SMALL_BATCH_THRESHOLD:
            self._log(f"Case {case['case_id']} stays in small-batch bypass branch")
            execution = {
                "step_a_skipped": True,
                "skip_reason": "small_batch_threshold",
                "effective_batch_size": effective_batch_size,
                "signal_count": len(signals),
                "logical_scenarios": [],
                "exploration_scenarios": [],
                "role_annotations": {},
                "isolated_signal_ids": [s["signal_id"] for s in signals],
                "fallback_used": False,
            }
        else:
            self._log(f"Running Step A for {case['case_id']}")
            step_a_result = run_step_a(
                enriched_signals=signals,
                llm_client=self.llm_client,
                model=self.model,
            )
            self._log(
                f"Step A finished for {case['case_id']} with {len(step_a_result.logical_scenarios)} logical scenarios"
            )
            execution = {
                "step_a_skipped": False,
                "skip_reason": None,
                "effective_batch_size": effective_batch_size,
                "signal_count": len(signals),
                "logical_scenarios": [sc.to_dict() for sc in step_a_result.logical_scenarios],
                "exploration_scenarios": [sc.to_dict() for sc in step_a_result.exploration_scenarios],
                "role_annotations": step_a_result.role_annotations,
                "isolated_signal_ids": [
                    s.get("signal_id") or s.get("id") for s in step_a_result.isolated_signals
                ],
                "fallback_used": step_a_result.fallback_used,
            }

        dataset = {
            "loaded_samples": loaded_samples,
            "decoded_samples": decoded_samples,
            "decode_errors": decode_errors,
            "signals": signals,
            "source_signal_map": source_signal_map,
        }
        validation = self._validate_case(case, dataset, execution)

        return {
            "case": case,
            "dataset": self._build_dataset_report(dataset),
            "execution": execution,
            "validation": validation,
        }

    def _run_ad_hoc_batch(self) -> dict:
        case = {
            "case_id": self.ad_hoc_run_label,
            "case_type": "ad_hoc_batch",
            "validation_profile": "ad_hoc",
            "data_nature": REAL_SAMPLE_DATA_NATURE,
            "description": f"Ad hoc batch extraction for {len(self.sample_paths)} real sample files.",
            "sample_files": list(self.sample_paths),
            "expected_step_a": {},
        }
        loaded_samples = self._load_samples_from_relative_paths(self.sample_paths)
        self._log(f"Loaded {len(loaded_samples)} ad hoc sample files for {case['case_id']}")

        decoded_samples, decode_errors = self._decode_case_samples(loaded_samples)
        self._log(
            f"Decoded {len(decoded_samples)} ad hoc samples for {case['case_id']} with {len(decode_errors)} decode errors"
        )

        signals, source_signal_map = self._build_enriched_signals(decoded_samples)
        effective_batch_size = len(signals)
        self._log(f"Built {effective_batch_size} enriched signals for {case['case_id']}")

        if effective_batch_size <= SMALL_BATCH_THRESHOLD:
            execution = {
                "step_a_skipped": True,
                "skip_reason": "small_batch_threshold",
                "effective_batch_size": effective_batch_size,
                "signal_count": len(signals),
                "logical_scenarios": [],
                "exploration_scenarios": [],
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
                "exploration_scenarios": [sc.to_dict() for sc in step_a_result.exploration_scenarios],
                "role_annotations": step_a_result.role_annotations,
                "isolated_signal_ids": [
                    s.get("signal_id") or s.get("id") for s in step_a_result.isolated_signals
                ],
                "fallback_used": step_a_result.fallback_used,
            }

        dataset = {
            "loaded_samples": loaded_samples,
            "decoded_samples": decoded_samples,
            "decode_errors": decode_errors,
            "signals": signals,
            "source_signal_map": source_signal_map,
        }
        validation = self._build_ad_hoc_validation(dataset, execution)

        return {
            "case": case,
            "dataset": self._build_dataset_report(dataset),
            "execution": execution,
            "validation": validation,
        }

    def _load_case_samples(self, case: dict) -> List[dict]:
        return self._load_samples_from_relative_paths(case.get("sample_files", []))

    def _load_samples_from_relative_paths(self, relative_paths: List[str]) -> List[dict]:
        loaded = []
        for rel_path in relative_paths:
            abs_path = os.path.join(REAL_SAMPLE_ROOT, rel_path)
            if not os.path.exists(abs_path):
                processed_candidates = [
                    os.path.join(REAL_SAMPLE_ROOT, "processed", rel_path.replace("/", os.sep)),
                    os.path.join(REAL_SAMPLE_ROOT, "processed", os.path.basename(rel_path)),
                ]
                for candidate_path in processed_candidates:
                    if os.path.exists(candidate_path):
                        abs_path = candidate_path
                        break
                else:
                    raise FileNotFoundError(f"Real sample file not found: {rel_path}")
            with open(abs_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            loaded.append({
                "relative_path": rel_path,
                "absolute_path": abs_path,
                "payload": payload,
            })
        return loaded

    def _decode_case_samples(self, loaded_samples: List[dict]) -> Tuple[List[dict], List[dict]]:
        decoded_samples = []
        decode_errors = []
        ordered_results: List[Tuple[dict, dict, str, dict]] = []
        live_decode_queue: List[Tuple[dict, dict, str, str]] = []

        for item in loaded_samples:
            payload = dict(item["payload"])
            payload.pop("_noise_label", None)
            source_id = payload.get("source_id", "unknown")
            cache_key = item["relative_path"]

            if cache_key in self.decode_cache:
                decode_result = dict(self.decode_cache[cache_key])
                self._log(f"Reusing cached decode for source {source_id} from {item['relative_path']}")
                ordered_results.append((item, payload, source_id, decode_result))
                continue

            decode_result = None
            if self.fixture_mode in {"prefer_fixture", "fixture_only"}:
                try:
                    decode_result = self._load_decode_fixture(item["relative_path"])
                except Exception as e:
                    decode_result = {
                        "ok": False,
                        "relative_path": item["relative_path"],
                        "source_id": source_id,
                        "elapsed_seconds": None,
                        "error": f"invalid decode fixture: {str(e)}",
                        "fixture_hit": True,
                    }
                if decode_result and decode_result.get("ok"):
                    self._log(f"Loaded decode fixture for source {source_id} from {item['relative_path']}")
                    self.decode_cache[cache_key] = decode_result
                    ordered_results.append((item, payload, source_id, decode_result))
                    continue

            if decode_result is not None:
                self.decode_cache[cache_key] = decode_result
                ordered_results.append((item, payload, source_id, decode_result))
                continue

            if self.fixture_mode == "fixture_only":
                decode_result = {
                    "ok": False,
                    "relative_path": item["relative_path"],
                    "source_id": source_id,
                    "elapsed_seconds": None,
                    "error": "decode fixture not found in fixture_only mode",
                    "fixture_hit": False,
                }
                self.decode_cache[cache_key] = decode_result
                ordered_results.append((item, payload, source_id, decode_result))
                continue

            live_decode_queue.append((item, payload, source_id, cache_key))

        if live_decode_queue:
            if self.decode_execution_mode == "subprocess" and self.max_parallel_decodes > 1 and len(live_decode_queue) > 1:
                worker_count = min(self.max_parallel_decodes, len(live_decode_queue))
                self._log(f"Running {len(live_decode_queue)} live decodes with parallel subprocess workers={worker_count}")
                future_map = {}
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    for item, payload, source_id, cache_key in live_decode_queue:
                        self._log(f"Queueing live decode for source {source_id} from {item['relative_path']}")
                        future = executor.submit(self._decode_sample_subprocess, item, payload, source_id)
                        future_map[future] = (item, payload, source_id, cache_key)

                    parallel_results = {}
                    for future in as_completed(future_map):
                        item, payload, source_id, cache_key = future_map[future]
                        try:
                            decode_result = future.result()
                        except Exception as e:
                            decode_result = {
                                "ok": False,
                                "relative_path": item["relative_path"],
                                "source_id": source_id,
                                "elapsed_seconds": None,
                                "error": str(e),
                                "fixture_hit": False,
                            }
                        if decode_result.get("ok"):
                            self._save_decode_fixture(decode_result)
                            self._log(f"Saved decode fixture for source {source_id} from {item['relative_path']}")
                        self.decode_cache[cache_key] = decode_result
                        parallel_results[cache_key] = decode_result

                for item, payload, source_id, cache_key in live_decode_queue:
                    ordered_results.append((item, payload, source_id, parallel_results[cache_key]))
            else:
                for item, payload, source_id, cache_key in live_decode_queue:
                    self._log(f"Decoding source {source_id} from {item['relative_path']}")
                    if self.decode_execution_mode == "inline":
                        decode_result = self._decode_sample_inline(item, payload, source_id)
                    else:
                        decode_result = self._decode_sample_subprocess(item, payload, source_id)
                    if decode_result.get("ok"):
                        self._save_decode_fixture(decode_result)
                        self._log(f"Saved decode fixture for source {source_id} from {item['relative_path']}")
                    self.decode_cache[cache_key] = decode_result
                    ordered_results.append((item, payload, source_id, decode_result))

        for item, payload, source_id, decode_result in ordered_results:
            if not decode_result.get("ok"):
                decode_errors.append({
                    "relative_path": decode_result["relative_path"],
                    "source_id": decode_result["source_id"],
                    "elapsed_seconds": decode_result.get("elapsed_seconds"),
                    "error": decode_result.get("error", "unknown decode error"),
                    "fixture_hit": decode_result.get("fixture_hit", False),
                    **({"timeout_detail": decode_result["timeout_detail"]} if decode_result.get("timeout_detail") else {}),
                })
                self._log(
                    f"Decode failed for source {source_id}: {decode_result.get('error', 'unknown decode error')}"
                )
                continue

            result_obj = decode_result["result"]
            decoded_samples.append({
                "relative_path": decode_result["relative_path"],
                "source_id": decode_result["source_id"],
                "elapsed_seconds": decode_result.get("elapsed_seconds"),
                "payload": decode_result["payload"],
                "result": result_obj,
                "fixture_hit": decode_result.get("fixture_hit", False),
                "fixture_path": decode_result.get("fixture_path"),
                "fixture_metadata": decode_result.get("fixture_metadata", {}),
            })
            signal_count = len(getattr(result_obj, "signals", []) or [])
            self._log(
                f"Decoded source {source_id} successfully with {signal_count} signals"
            )

        return decoded_samples, decode_errors

    def _build_enriched_signals(self, decoded_samples: List[dict]) -> Tuple[List[dict], Dict[str, List[str]]]:
        decoded_intelligences = []
        for item in decoded_samples:
            result = item["result"]
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result
            result_dict["source_type"] = item["payload"].get("source_type", "unknown")
            decoded_intelligences.append(result_dict)

        enriched_signals = self.engine._extract_enriched_signals(decoded_intelligences)

        stabilized = []
        source_signal_map: Dict[str, List[str]] = {}
        for index, signal in enumerate(enriched_signals, 1):
            signal_copy = dict(signal)
            original_signal_id = signal_copy.get("signal_id") or f"sig_{index}"
            source_id = signal_copy.get("_source_id", "unknown")
            stable_signal_id = f"{source_id}__{original_signal_id}"
            signal_copy["signal_id"] = stable_signal_id
            signal_copy["_original_signal_id"] = original_signal_id
            stabilized.append(signal_copy)
            source_signal_map.setdefault(source_id, []).append(stable_signal_id)

        return stabilized, source_signal_map

    def _validate_case(self, case: dict, dataset: dict, execution: dict) -> dict:
        expected = case.get("expected_step_a", {})
        validation_profile = case.get("validation_profile", "strict")
        source_signal_map = dataset["source_signal_map"]
        all_source_ids = sorted(source_signal_map.keys())
        noise_source_ids = self._extract_noise_source_ids(dataset)
        monitored_noise_source_ids = set(expected.get("monitor_noise_source_ids", []))

        validation = {
            "passed": True,
            "decode_success": True,
            "skip_policy_match": True,
            "signal_volume_ok": True,
            "noise_expectation_ok": True,
            "source_coverage_ok": True,
            "scenario_count_match": True,
            "expected_core_match": True,
            "forbidden_pairings_ok": True,
            "annotations_complete": True,
            "errors": [],
            "warnings": [],
            "metrics": {
                "cross_domain_complement_recall": None,
                "false_merge_rate": None,
                "noise_inclusion_rate": None,
                "step_c_opportunity_ready_proxy_rate": None,
                "matched_expected_core_sets": 0,
                "expected_core_sets": 0,
                "forbidden_pairings_detected": 0,
                "noise_scenarios": 0,
                "opportunity_ready_scenarios": 0,
                "scenario_count": 0,
            },
            "error_attribution": [],
            "dominant_error_attribution": "none",
        }

        if dataset["decode_errors"]:
            validation["passed"] = False
            validation["decode_success"] = False
            validation["errors"].append(f"Decode errors detected: {dataset['decode_errors']}")

        min_total_signals = expected.get("min_total_signals")
        if min_total_signals is not None and execution["signal_count"] < min_total_signals:
            validation["passed"] = False
            validation["signal_volume_ok"] = False
            validation["errors"].append(
                f"Signal volume below expectation: expected>={min_total_signals}, actual={execution['signal_count']}"
            )

        expected_non_noise_source_ids = set(expected.get("expected_non_noise_source_ids", []))
        if expected_non_noise_source_ids and not expected_non_noise_source_ids.issubset(set(all_source_ids)):
            validation["passed"] = False
            validation["source_coverage_ok"] = False
            validation["errors"].append(
                f"Expected non-noise sources missing from decoded set: expected={sorted(expected_non_noise_source_ids)}, actual={all_source_ids}"
            )

        expected_noise_source_ids = set(expected.get("expected_noise_source_ids", []))
        unexpected_noise_hits = sorted(expected_noise_source_ids.intersection(set(all_source_ids)))
        if unexpected_noise_hits:
            validation["passed"] = False
            validation["noise_expectation_ok"] = False
            validation["errors"].append(
                f"Expected noise-only sources unexpectedly produced signals: {unexpected_noise_hits}"
            )

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
            validation["error_attribution"] = self._build_error_attribution(validation)
            validation["dominant_error_attribution"] = validation["error_attribution"][0] if validation["error_attribution"] else "none"
            return validation

        if execution["step_a_skipped"]:
            validation["passed"] = False
            validation["skip_policy_match"] = False
            validation["errors"].append(
                "Expected Step A execution, but the decoded signal count still fell into the small-batch branch"
            )
            validation["error_attribution"] = self._build_error_attribution(validation)
            validation["dominant_error_attribution"] = validation["error_attribution"][0] if validation["error_attribution"] else "none"
            return validation

        signals = dataset["signals"]
        signal_ids = {s["signal_id"] for s in signals}
        annotations = execution["role_annotations"]
        if set(annotations.keys()) != signal_ids:
            validation["passed"] = False
            validation["annotations_complete"] = False
            validation["errors"].append(
                f"Role annotation coverage mismatch: expected={sorted(signal_ids)}, actual={sorted(annotations.keys())}"
            )

        scenario_count = len(execution["logical_scenarios"])
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

        source_sets = self._scenario_source_sets(execution["logical_scenarios"], signals)
        expected_core_sets = expected.get("expected_core_source_sets", [])
        matched_expected_core_sets = 0
        for expected_sources in expected_core_sets:
            expected_source_set = set(expected_sources)
            if any(expected_source_set.issubset(item) for item in source_sets):
                matched_expected_core_sets += 1
            else:
                if validation_profile == "strict":
                    validation["passed"] = False
                    validation["expected_core_match"] = False
                    validation["errors"].append(
                        f"Expected core source set not found in any scenario: {expected_sources}"
                    )
                else:
                    validation["warnings"].append(
                        f"Exploratory expectation not met for source set: {expected_sources}"
                    )

        forbidden_pairings_detected = 0
        for forbidden_pair in expected.get("forbidden_source_pairings", []):
            forbidden_set = set(forbidden_pair)
            if any(forbidden_set.issubset(item) for item in source_sets):
                forbidden_pairings_detected += 1
                if validation_profile == "strict":
                    validation["passed"] = False
                    validation["forbidden_pairings_ok"] = False
                    validation["errors"].append(
                        f"Forbidden source pairing detected inside one scenario: {forbidden_pair}"
                    )
                else:
                    validation["warnings"].append(
                        f"Exploratory forbidden source pairing observed: {forbidden_pair}"
                    )

        scenario_noise_hits = 0
        opportunity_ready_scenarios = 0
        for source_set in source_sets:
            effective_noise_sources = noise_source_ids.union(monitored_noise_source_ids)
            if source_set.intersection(effective_noise_sources):
                scenario_noise_hits += 1
            non_noise_sources = source_set.difference(effective_noise_sources)
            if len(non_noise_sources) >= 2:
                opportunity_ready_scenarios += 1

        if monitored_noise_source_ids and scenario_noise_hits > 0:
            validation["warnings"].append(
                f"Monitored noise sources entered {scenario_noise_hits} scenario(s): {sorted(monitored_noise_source_ids)}"
            )

        validation["metrics"] = {
            "cross_domain_complement_recall": self._safe_rate(matched_expected_core_sets, len(expected_core_sets)),
            "false_merge_rate": self._safe_rate(forbidden_pairings_detected, scenario_count),
            "noise_inclusion_rate": self._safe_rate(scenario_noise_hits, scenario_count),
            "step_c_opportunity_ready_proxy_rate": self._safe_rate(opportunity_ready_scenarios, scenario_count),
            "matched_expected_core_sets": matched_expected_core_sets,
            "expected_core_sets": len(expected_core_sets),
            "forbidden_pairings_detected": forbidden_pairings_detected,
            "noise_scenarios": scenario_noise_hits,
            "opportunity_ready_scenarios": opportunity_ready_scenarios,
            "scenario_count": scenario_count,
        }
        validation["error_attribution"] = self._build_error_attribution(validation)
        validation["dominant_error_attribution"] = validation["error_attribution"][0] if validation["error_attribution"] else "none"
        return validation

    def _build_ad_hoc_validation(self, dataset: dict, execution: dict) -> dict:
        validation = {
            "passed": True,
            "decode_success": True,
            "skip_policy_match": True,
            "signal_volume_ok": True,
            "noise_expectation_ok": True,
            "source_coverage_ok": True,
            "scenario_count_match": True,
            "expected_core_match": True,
            "forbidden_pairings_ok": True,
            "annotations_complete": True,
            "errors": [],
            "warnings": [],
            "metrics": {
                "cross_domain_complement_recall": None,
                "false_merge_rate": None,
                "noise_inclusion_rate": None,
                "step_c_opportunity_ready_proxy_rate": None,
                "matched_expected_core_sets": 0,
                "expected_core_sets": 0,
                "forbidden_pairings_detected": 0,
                "noise_scenarios": 0,
                "opportunity_ready_scenarios": 0,
                "scenario_count": len(execution["logical_scenarios"]),
            },
            "error_attribution": [],
            "dominant_error_attribution": "none",
        }

        if dataset["decode_errors"]:
            validation["passed"] = False
            validation["decode_success"] = False
            validation["errors"].append(f"Decode errors detected: {dataset['decode_errors']}")

        signals = dataset["signals"]
        signal_ids = {s["signal_id"] for s in signals}
        if not execution["step_a_skipped"]:
            annotations = execution["role_annotations"]
            if set(annotations.keys()) != signal_ids:
                validation["passed"] = False
                validation["annotations_complete"] = False
                validation["errors"].append(
                    f"Role annotation coverage mismatch: expected={sorted(signal_ids)}, actual={sorted(annotations.keys())}"
                )

        noise_source_ids = self._extract_noise_source_ids(dataset)
        source_sets = self._scenario_source_sets(execution["logical_scenarios"], signals)
        scenario_noise_hits = 0
        opportunity_ready_scenarios = 0
        for source_set in source_sets:
            if source_set.intersection(noise_source_ids):
                scenario_noise_hits += 1
            non_noise_sources = source_set.difference(noise_source_ids)
            if len(non_noise_sources) >= 2:
                opportunity_ready_scenarios += 1

        validation["metrics"] = {
            "cross_domain_complement_recall": None,
            "false_merge_rate": None,
            "noise_inclusion_rate": self._safe_rate(scenario_noise_hits, len(source_sets)),
            "step_c_opportunity_ready_proxy_rate": self._safe_rate(opportunity_ready_scenarios, len(source_sets)),
            "matched_expected_core_sets": 0,
            "expected_core_sets": 0,
            "forbidden_pairings_detected": 0,
            "noise_scenarios": scenario_noise_hits,
            "opportunity_ready_scenarios": opportunity_ready_scenarios,
            "scenario_count": len(source_sets),
        }
        validation["error_attribution"] = self._build_error_attribution(validation)
        validation["dominant_error_attribution"] = validation["error_attribution"][0] if validation["error_attribution"] else "none"
        return validation

    @staticmethod
    def _safe_rate(numerator: int, denominator: int):
        if denominator <= 0:
            return None
        return round(numerator / denominator, 4)

    @staticmethod
    def _extract_noise_source_ids(dataset: dict) -> set:
        noise_source_ids = set()
        for item in dataset.get("loaded_samples", []):
            payload = item.get("payload", {}) or {}
            source_id = payload.get("source_id")
            if not source_id:
                continue
            if payload.get("_noise_label") or source_id.startswith("noise_") or source_id.startswith("incoming_noise_"):
                noise_source_ids.add(source_id)
        return noise_source_ids

    @staticmethod
    def _build_error_attribution(validation: dict) -> List[str]:
        attribution = []
        if not validation.get("decode_success", True):
            attribution.append("phase2_1_decode")
        if not validation.get("signal_volume_ok", True) or not validation.get("source_coverage_ok", True):
            attribution.append("phase2_1_signal_extraction")
        if not validation.get("skip_policy_match", True):
            attribution.append("step_a_branching")
        if not validation.get("expected_core_match", True):
            attribution.append("step_a_cross_domain_recall")
        if not validation.get("forbidden_pairings_ok", True):
            attribution.append("step_a_false_merge")
        if not validation.get("annotations_complete", True):
            attribution.append("step_a_annotation")
        if not attribution and validation.get("warnings"):
            attribution.append("exploratory_gap")
        return attribution

    @staticmethod
    def _scenario_source_sets(logical_scenarios: List[dict], signals: List[dict]) -> List[set]:
        signal_source_map = {s["signal_id"]: s.get("_source_id", "unknown") for s in signals}
        source_sets = []
        for scenario in logical_scenarios:
            ids = list(scenario.get("primary_signal_ids", [])) + list(scenario.get("context_signal_ids", []))
            source_sets.append({signal_source_map.get(signal_id, "unknown") for signal_id in ids})
        return source_sets

    @staticmethod
    def _build_dataset_report(dataset: dict) -> dict:
        decoded_samples = []
        for item in dataset["decoded_samples"]:
            result = item["result"]
            signal_count = len(getattr(result, "signals", []) or [])
            decoded_samples.append({
                "relative_path": item["relative_path"],
                "source_id": item["source_id"],
                "elapsed_seconds": item.get("elapsed_seconds"),
                "signal_count": signal_count,
                "fixture_hit": item.get("fixture_hit", False),
                "fixture_path": item.get("fixture_path"),
                "fixture_metadata": item.get("fixture_metadata", {}),
                "warnings": list(getattr(result, "warnings", []) or []),
            })

        signal_preview = []
        for signal in dataset["signals"]:
            signal_preview.append({
                "signal_id": signal.get("signal_id"),
                "source_id": signal.get("_source_id"),
                "signal_type": signal.get("signal_type"),
                "signal_label": signal.get("signal_label"),
                "intensity_score": signal.get("intensity_score"),
                "logic_frame": signal.get("logic_frame"),
            })

        return {
            "decoded_samples": decoded_samples,
            "decode_errors": dataset["decode_errors"],
            "signal_count": len(dataset["signals"]),
            "source_signal_map": dataset["source_signal_map"],
            "noise_source_ids": sorted(StepARealEvalRunner._extract_noise_source_ids(dataset)),
            "signals": signal_preview,
        }

    def _print_header(self, cases: List[dict]):
        print("=" * 80)
        print("Phase 2.2 Step A - Real Sample Evaluation Runner")
        print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sample version: {STEP_A_REAL_EVAL_CASES_VERSION}")
        print(f"Sample count: {len(cases)}")
        print(f"Requested mode: {self.mode}")
        print(f"Runtime mode: {self.runtime_mode}")
        print(f"Fast decode: {'on' if self.fast_decode else 'off'}")
        print(f"Decode timeout per sample: {self.decode_timeout_seconds}s")
        print(f"Decode execution mode: {self.decode_execution_mode}")
        print(f"Max parallel decodes: {self.max_parallel_decodes}")
        print(f"Fixture mode: {self.fixture_mode}")
        print(f"Fixture root: {self.fixture_root}")
        print(f"Phase 2.1 HTTP timeout: connect={self.connect_timeout_seconds}s read={self.read_timeout_seconds}s retries={self.max_retries}")
        print(f"Small-batch threshold: <= {SMALL_BATCH_THRESHOLD}")
        print(f"Real sample root: {REAL_SAMPLE_ROOT}")
        print("=" * 80)

    def _print_case_result(self, index: int, total: int, result: dict):
        case = result["case"]
        dataset = result["dataset"]
        execution = result["execution"]
        validation = result["validation"]
        metrics = validation.get("metrics", {})

        print(f"\n[{index}/{total}] Case: {case['case_id']}")
        print(f"Type: {case['case_type']} | profile={case.get('validation_profile', 'strict')}")
        print(f"Description: {case['description']}")
        print(f"Decoded sources: {len(dataset['decoded_samples'])} | total signals: {dataset['signal_count']}")

        if dataset["decoded_samples"]:
            decode_timing = [
                f"{item['source_id']}={item.get('elapsed_seconds', 'n/a')}s"
                for item in dataset["decoded_samples"]
            ]
            fixture_hits = sum(1 for item in dataset["decoded_samples"] if item.get("fixture_hit"))
            print(f"Decode timing: {', '.join(decode_timing)}")
            print(f"Fixture hits: {fixture_hits}/{len(dataset['decoded_samples'])}")

        if dataset["noise_source_ids"]:
            print(f"Noise sources in dataset: {dataset['noise_source_ids']}")

        if dataset["decode_errors"]:
            print(f"Decode errors: {dataset['decode_errors']}")

        if execution["step_a_skipped"]:
            print(f"Execution: skipped Step A ({execution['skip_reason']})")
        else:
            print(
                f"Execution: Step A ran | scenarios={len(execution['logical_scenarios'])} "
                f"| exploration={len(execution['exploration_scenarios'])} "
                f"| fallback_used={execution['fallback_used']}"
            )
            for scenario in execution["logical_scenarios"]:
                print(
                    f"  - {scenario['scenario_id']}: primary={scenario['primary_signal_ids']} "
                    f"| context={scenario['context_signal_ids']}"
                )
            print(
                "Metrics: "
                f"cross_domain_recall={metrics.get('cross_domain_complement_recall')} | "
                f"false_merge_rate={metrics.get('false_merge_rate')} | "
                f"noise_inclusion_rate={metrics.get('noise_inclusion_rate')} | "
                f"step_c_ready_proxy={metrics.get('step_c_opportunity_ready_proxy_rate')}"
            )

        print(
            "Checks: "
            f"decode={'OK' if validation['decode_success'] else 'FAIL'} | "
            f"skip={'OK' if validation['skip_policy_match'] else 'FAIL'} | "
            f"volume={'OK' if validation['signal_volume_ok'] else 'FAIL'} | "
            f"noise={'OK' if validation['noise_expectation_ok'] else 'FAIL'} | "
            f"coverage={'OK' if validation['source_coverage_ok'] else 'FAIL'} | "
            f"count={'OK' if validation['scenario_count_match'] else 'FAIL'} | "
            f"core={'OK' if validation['expected_core_match'] else 'FAIL'} | "
            f"forbidden={'OK' if validation['forbidden_pairings_ok'] else 'FAIL'} | "
            f"annotations={'OK' if validation['annotations_complete'] else 'FAIL'}"
        )
        print(f"Attribution: {validation.get('error_attribution', []) or ['none']}")
        print(f"Result: {'PASS' if validation['passed'] else 'FAIL'}")
        if validation["errors"]:
            print(f"Errors: {validation['errors']}")
        if validation["warnings"]:
            print(f"Warnings: {validation['warnings']}")

    def _print_summary(self):
        print("\n" + "=" * 80)
        print("Step A real-sample evaluation summary")
        print("=" * 80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["validation"]["passed"])
        skipped = sum(1 for r in self.results if r["execution"]["step_a_skipped"])
        executed = total - skipped
        fallback_used = sum(
            1 for r in self.results
            if (not r["execution"]["step_a_skipped"]) and r["execution"]["fallback_used"]
        )
        executed_results = [r for r in self.results if not r["execution"]["step_a_skipped"]]

        print(f"Total cases: {total}")
        print(f"Passed: {passed}/{total} ({(passed / total * 100) if total else 0:.0f}%)")
        print(f"Executed Step A: {executed}")
        print(f"Skipped by small-batch policy: {skipped}")
        print(f"Fallback-used executions: {fallback_used}")

        for key, label in [
            ("decode_success", "Decode success"),
            ("skip_policy_match", "Skip policy match"),
            ("signal_volume_ok", "Signal volume"),
            ("noise_expectation_ok", "Noise expectation"),
            ("source_coverage_ok", "Source coverage"),
            ("scenario_count_match", "Scenario count match"),
            ("expected_core_match", "Expected core match"),
            ("forbidden_pairings_ok", "Forbidden pairings"),
            ("annotations_complete", "Annotation coverage"),
        ]:
            ok = sum(1 for r in self.results if r["validation"][key])
            print(f"{label}: {ok}/{total} ({(ok / total * 100) if total else 0:.0f}%)")

        print(
            "Cross-domain complement recall (executed avg): "
            f"{self._average_metric(executed_results, 'cross_domain_complement_recall')}"
        )
        print(
            "False merge rate (executed avg): "
            f"{self._average_metric(executed_results, 'false_merge_rate')}"
        )
        print(
            "Noise inclusion rate (executed avg): "
            f"{self._average_metric(executed_results, 'noise_inclusion_rate')}"
        )
        print(
            "Step C opportunity-ready proxy rate (executed avg): "
            f"{self._average_metric(executed_results, 'step_c_opportunity_ready_proxy_rate')}"
        )

        attribution_counts = {}
        for item in self.results:
            dominant = item["validation"].get("dominant_error_attribution", "none")
            attribution_counts[dominant] = attribution_counts.get(dominant, 0) + 1
        print(f"Dominant attribution breakdown: {attribution_counts}")

        overall_pass = passed == total
        print(
            f"\nConclusion: {'[PASS] real-sample baseline v1 usable for trend comparison' if overall_pass else '[FAIL] baseline exposed gaps; review attribution and labels'}"
        )

    @staticmethod
    def _average_metric(results: List[dict], metric_key: str):
        values = []
        for item in results:
            value = item["validation"].get("metrics", {}).get(metric_key)
            if value is not None:
                values.append(value)
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _build_json_report(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["validation"]["passed"])
        executed_results = [r for r in self.results if not r["execution"]["step_a_skipped"]]
        strict_cases = [r for r in self.results if r["case"].get("validation_profile") == "strict"]
        exploratory_cases = [r for r in self.results if r["case"].get("validation_profile") != "strict"]
        strict_passed = sum(1 for r in strict_cases if r["validation"]["passed"])
        exploratory_passed = sum(1 for r in exploratory_cases if r["validation"]["passed"])

        case_type_counts = {}
        for item in self.results:
            case_type = item["case"].get("case_type", "unknown")
            case_type_counts[case_type] = case_type_counts.get(case_type, 0) + 1

        baseline_v1 = {
            "label": "real_world_baseline_v1",
            "status": "pass" if passed == total else "needs_review",
            "trend_comparison_ready": passed == total,
            "strict_case_passed": strict_passed,
            "strict_case_total": len(strict_cases),
            "exploratory_case_passed": exploratory_passed,
            "exploratory_case_total": len(exploratory_cases),
            "layered_case_coverage": case_type_counts,
        }

        return {
            "runner": "run_step_a_real_eval.py",
            "sample_version": STEP_A_REAL_EVAL_CASES_VERSION,
            "requested_mode": self.mode,
            "runtime_mode": self.runtime_mode,
            "fast_decode": self.fast_decode,
            "decode_timeout_seconds": self.decode_timeout_seconds,
            "decode_execution_mode": self.decode_execution_mode,
            "max_parallel_decodes": self.max_parallel_decodes,
            "fixture_mode": self.fixture_mode,
            "fixture_root": self.fixture_root,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
            "max_retries": self.max_retries,
            "max_llm_calls_per_sample": 1 if self.fast_decode else 2,
            "small_batch_threshold": SMALL_BATCH_THRESHOLD,
            "real_sample_root": REAL_SAMPLE_ROOT,
            "total_cases": total,
            "passed_cases": passed,
            "baseline_v1": baseline_v1,
            "summary": {
                "executed_step_a_cases": len(executed_results),
                "skipped_step_a_cases": total - len(executed_results),
                "strict_cases": len(strict_cases),
                "exploratory_cases": len(exploratory_cases),
                "avg_cross_domain_complement_recall": self._average_metric(executed_results, "cross_domain_complement_recall"),
                "avg_false_merge_rate": self._average_metric(executed_results, "false_merge_rate"),
                "avg_noise_inclusion_rate": self._average_metric(executed_results, "noise_inclusion_rate"),
                "avg_step_c_opportunity_ready_proxy_rate": self._average_metric(executed_results, "step_c_opportunity_ready_proxy_rate"),
            },
            "results": self.results,
        }

    def _write_json_report(self, report: dict):
        if not self.report_output_path:
            return

        report_path = os.path.abspath(self.report_output_path)
        report_dir = os.path.dirname(report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self._log(f"Saved JSON report to {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step A real-sample evaluation cases")
    parser.add_argument(
        "--mode",
        choices=["auto", "llm", "rules"],
        default="auto",
        help="Execution mode. auto=prefer configured LLM and fallback to rules, llm=LLM required, rules=force no LLM",
    )
    parser.add_argument("--case-id", help="Run only one case by case_id")
    parser.add_argument(
        "--sample-path",
        action="append",
        dest="sample_paths",
        help="Relative real sample path for ad hoc batch extraction. Repeat this flag to include multiple samples.",
    )
    parser.add_argument(
        "--sample-list-file",
        help="Optional text file containing one relative sample path per line for ad hoc batch extraction.",
    )
    parser.add_argument(
        "--ad-hoc-run-label",
        default="ad_hoc_batch",
        help="Case label used in reports when running an ad hoc sample batch.",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failed case")
    parser.add_argument("--json", action="store_true", help="Print JSON report instead of console summary")
    parser.add_argument("--verbose", action="store_true", help="Print lightweight progress logs for diagnosis")
    parser.add_argument(
        "--report-output",
        help="Optional path to persist the JSON evaluation report to disk regardless of terminal output stability.",
    )
    parser.add_argument("--connect-timeout", type=int, default=REAL_EVAL_CONNECT_TIMEOUT_SECONDS, help="Phase 2.1 HTTP connect timeout in seconds")
    parser.add_argument("--read-timeout", type=int, default=REAL_EVAL_READ_TIMEOUT_SECONDS, help="Phase 2.1 HTTP read timeout in seconds")
    parser.add_argument("--decode-timeout", type=int, default=REAL_EVAL_DECODE_TIMEOUT_SECONDS, help="Per-sample subprocess timeout in seconds")
    parser.add_argument("--max-retries", type=int, default=REAL_EVAL_MAX_RETRIES, help="Phase 2.1 LLM max retries per call")
    parser.add_argument(
        "--decode-execution-mode",
        choices=["subprocess", "inline"],
        default="inline",
        help="Choose how real evaluation invokes Phase 2.1 decode. inline is more diagnosis-friendly on Windows; subprocess keeps hard timeout isolation.",
    )
    parser.add_argument(
        "--fixture-mode",
        choices=["live", "prefer_fixture", "fixture_only"],
        default="prefer_fixture",
        help="Decode fixture strategy. live=always decode online, prefer_fixture=reuse saved fixture and backfill missing ones, fixture_only=offline replay only.",
    )
    parser.add_argument(
        "--fixture-root",
        default=REAL_EVAL_FIXTURE_ROOT,
        help="Directory used to read/write persisted decoded fixtures for real eval.",
    )
    parser.add_argument(
        "--max-parallel-decodes",
        type=int,
        default=3,
        help="Maximum number of missing live decodes to backfill concurrently when using subprocess decode mode.",
    )
    parser.add_argument(
        "--no-fast-decode",
        action="store_true",
        # This switch exists so evaluation can return to the production-like two-stage path after diagnosis.
        help="Keep Phase 2.1 two-stage screening on during real evaluation (slower but closer to production)",
    )
    parser.add_argument("--internal-decode-sample", help=argparse.SUPPRESS)
    parser.add_argument("--internal-keep-two-stage", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--internal-connect-timeout", type=int, default=REAL_EVAL_CONNECT_TIMEOUT_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--internal-read-timeout", type=int, default=REAL_EVAL_READ_TIMEOUT_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--internal-max-retries", type=int, default=REAL_EVAL_MAX_RETRIES, help=argparse.SUPPRESS)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.internal_decode_sample:
        raise SystemExit(
            run_internal_decode_sample(
                relative_path=args.internal_decode_sample,
                fast_decode=not args.internal_keep_two_stage,
                connect_timeout_seconds=args.internal_connect_timeout,
                read_timeout_seconds=args.internal_read_timeout,
                max_retries=args.internal_max_retries,
            )
        )

    sample_paths = list(args.sample_paths or [])
    if args.sample_list_file:
        with open(args.sample_list_file, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                sample_paths.append(line)
    if sample_paths:
        deduped_sample_paths = []
        seen_sample_paths = set()
        for rel_path in sample_paths:
            if rel_path in seen_sample_paths:
                continue
            seen_sample_paths.add(rel_path)
            deduped_sample_paths.append(rel_path)
        sample_paths = deduped_sample_paths

    runner = StepARealEvalRunner(
        mode=args.mode,
        case_id=args.case_id,
        fail_fast=args.fail_fast,
        json_output=args.json,
        verbose=args.verbose,
        fast_decode=not args.no_fast_decode,
        connect_timeout_seconds=args.connect_timeout,
        read_timeout_seconds=args.read_timeout,
        max_retries=args.max_retries,
        decode_timeout_seconds=args.decode_timeout,
        decode_execution_mode=args.decode_execution_mode,
        fixture_mode=args.fixture_mode,
        fixture_root=args.fixture_root,
        max_parallel_decodes=args.max_parallel_decodes,
        report_output_path=args.report_output,
        sample_paths=sample_paths,
        ad_hoc_run_label=args.ad_hoc_run_label,
    )
    runner.run()
