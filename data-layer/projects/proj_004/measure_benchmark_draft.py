import os
import sys
import json
import time
import argparse
import importlib.util
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
LLM_CONFIG_PATH = os.path.join(BASE, "llm_config.py")
DEFAULT_BENCHMARK_PATH = os.path.join(BASE, "phase2.1_implementation", "data", "benchmark_samples_batch1_draft.json")


def _load_env_file(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())


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
    spec = importlib.util.spec_from_file_location("llm_config", LLM_CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["llm_config"] = mod
    spec.loader.exec_module(mod)
    return mod.get_llm_config(phase)


def classify_expected(annotation: dict) -> str:
    expected_signals = (annotation or {}).get("expected_signals") or []
    return "signal" if len(expected_signals) > 0 else "noise"


def classify_predicted(signals: list) -> str:
    return "signal" if len(signals) > 0 else "noise"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK_PATH,
                        help="benchmark JSON path")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制样本数量（调试用）")
    parser.add_argument("--verbose", action="store_true",
                        help="输出每条样本的判断详情")
    args = parser.parse_args()

    _load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))

    llm_config = load_llm_config("2.1")
    if not llm_config.get("api_key"):
        print("ERROR: 未找到 phase 2.1 的 LLM API key")
        print("请在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 api_key")
        sys.exit(1)

    m21_schemas = load_module('schemas_21',
        os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
    m21_prompts = load_module('prompt_templates',
        os.path.join(BASE, 'phase2.1_implementation', 'prompt_templates.py'),
        dep_modules={'schemas': m21_schemas})
    decoder_mod = load_module('decoder',
        os.path.join(BASE, 'phase2.1_implementation', 'decoder.py'),
        dep_modules={'schemas': m21_schemas, 'prompt_templates': m21_prompts})

    IntelligenceDecoder = decoder_mod.IntelligenceDecoder
    IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest

    decoder = IntelligenceDecoder(
        api_key=llm_config.get("api_key", ""),
        model=llm_config.get("model", "claude-opus-4-6"),
        provider=llm_config.get("provider", "anthropic"),
        base_url=llm_config.get("base_url", ""),
    )

    benchmark_path = os.path.abspath(args.benchmark)
    with open(benchmark_path, encoding="utf-8") as f:
        benchmark = json.load(f)

    samples = benchmark.get("samples") or []
    if args.limit:
        samples = samples[:args.limit]

    print(f"Prompt version: {m21_prompts.PROMPT_VERSION}")
    print(f"Model: {llm_config.get('model', 'claude-opus-4-6')}")
    print(f"Provider: {llm_config.get('provider', 'anthropic')}")
    print(f"Benchmark: {benchmark_path}")
    print(f"\n样本总数: {len(samples)}")
    print(f"{'='*65}")

    results = []

    for sample in samples:
        expected_class = classify_expected(sample.get("annotation") or {})
        source_id = sample.get("sample_id") or sample.get("draft_meta", {}).get("origin_file") or "unknown"

        try:
            req = IntelligenceDecodeRequest(
                source_id=source_id,
                source_type=sample["source_type"],
                title=sample.get("title"),
                content=sample.get("content") or "",
                published_at=sample.get("published_at"),
                source_name=sample.get("source_name"),
                language=sample.get("language", "en"),
                mode=sample.get("mode", "prompt_first"),
            )
            started = time.time()
            result = decoder.decode(req)
            elapsed_ms = int((time.time() - started) * 1000)
            signals = result.signals
            predicted_class = classify_predicted(signals)
            warnings = result.warnings or []
        except Exception as e:
            elapsed_ms = 0
            signals = []
            predicted_class = "noise"
            warnings = [f"decode_exception: {e}"]

        if expected_class == "signal" and predicted_class == "signal":
            verdict = "TP"
        elif expected_class == "noise" and predicted_class == "noise":
            verdict = "TN"
        elif expected_class == "signal" and predicted_class == "noise":
            verdict = "FN"
        else:
            verdict = "FP"

        expected_labels = [
            f"{item.get('signal_type')}:{item.get('signal_label')}"
            for item in (sample.get("annotation") or {}).get("expected_signals") or []
        ]
        predicted_labels = [
            f"{s.signal_type}:{s.signal_label}"
            for s in signals
        ]

        results.append({
            "sample_id": sample.get("sample_id"),
            "origin_file": (sample.get("draft_meta") or {}).get("origin_file"),
            "expected_class": expected_class,
            "predicted_class": predicted_class,
            "expected_labels": expected_labels,
            "predicted_labels": predicted_labels,
            "verdict": verdict,
            "signal_count": len(signals),
            "processing_time_ms": elapsed_ms,
            "warnings": warnings,
        })

        icon = "✅" if verdict in ("TP", "TN") else "❌"
        print(f"  {icon} [{verdict}] GT:{expected_class:<6} Pred:{predicted_class:<6} Signals:{len(signals):<2}  {sample.get('sample_id')}  {sample.get('title')}")
        if args.verbose and predicted_labels:
            for label in predicted_labels:
                print(f"         - {label}")

    tp = sum(1 for r in results if r["verdict"] == "TP")
    tn = sum(1 for r in results if r["verdict"] == "TN")
    fp = sum(1 for r in results if r["verdict"] == "FP")
    fn = sum(1 for r in results if r["verdict"] == "FN")

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    accuracy = (tp + tn) / len(results) if results else 0

    print(f"\n{'='*65}")
    print(f"  样本总数    : {len(results)}")
    print(f"  TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(f"  Precision   : {precision:.1%}")
    print(f"  Recall      : {recall:.1%}")
    print(f"  F1          : {f1:.1%}")
    print(f"  Accuracy    : {accuracy:.1%}")
    print(f"{'='*65}")

    out = {
        "prompt_version": m21_prompts.PROMPT_VERSION,
        "run_at": datetime.utcnow().isoformat() + "Z",
        "benchmark_path": benchmark_path,
        "total": len(results),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "details": results,
    }
    out_path = os.path.join(BASE, f"benchmark_draft_report_{m21_prompts.PROMPT_VERSION}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n报告已保存: {os.path.basename(out_path)}")


if __name__ == "__main__":
    main()
