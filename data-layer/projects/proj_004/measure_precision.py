"""
2.1 Precision 测量脚本
用途：对 processed/ 中的样本重跑 2.1，与 ground truth 对比，输出 Precision/Recall/F1

Ground truth 规则（基于文件名）：
  - 文件名含 "noise" → 预期 signals=[]（负例）
  - 其余 → 预期 signals 非空（正例）

特殊边界（手动覆盖）：
  - incoming_040_market_crimson_desert_3m_day5  → noise（续报，无新增格局信号）
  - incoming_028_market_disney_gaming_ambition   → noise（泛战略表态，无具体事实）
  - incoming_032_technical_zuckerberg_ai_coceo   → noise（与游戏行业无直接关联）

运行方式:
  python measure_precision.py [--sample-dir processed|incoming] [--limit N]
"""

import os
import sys
import json
import time
import argparse
import importlib.util
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_ROOT = os.path.join(BASE, "..", "..", "..", "background", "real_intel_samples")


# ── 手动覆盖：这些文件名（不含扩展名前缀匹配）强制视为噪音 ──────────────────
NOISE_OVERRIDES = {
    "incoming_040_market_crimson_desert_3m_day5",   # 续报，无新格局信号
    "incoming_028_market_disney_gaming_ambition",   # 泛战略表态
    "incoming_032_technical_zuckerberg_ai_coceo",   # 与游戏无直接关联
}

# ── 手动覆盖：这些文件名强制视为正例（即使含 noise 字样也有价值）─────────────
SIGNAL_OVERRIDES = set()


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


def is_noise_sample(filename: str) -> bool:
    """根据文件名判断 ground truth 是否为噪音（预期 0 信号）"""
    stem = os.path.splitext(filename)[0]
    if stem in SIGNAL_OVERRIDES:
        return False
    if stem in NOISE_OVERRIDES:
        return True
    return "noise" in stem.lower()


def classify_signal_output(signals: list) -> str:
    """将解码输出分类：'signal'（有信号）或 'noise'（无信号）"""
    return "signal" if len(signals) > 0 else "noise"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", default="processed",
                        help="样本目录：processed 或 incoming（默认 processed）")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制样本数量（调试用）")
    parser.add_argument("--verbose", action="store_true",
                        help="输出每条样本的判断详情")
    args = parser.parse_args()

    # 加载环境变量
    _load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY 未设置")
        sys.exit(1)

    # 加载 2.1 模块
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

    decoder = IntelligenceDecoder(api_key=api_key, model="claude-sonnet-4-6")
    print(f"Prompt version: {m21_prompts.PROMPT_VERSION}")
    print(f"Model: claude-sonnet-4-6")

    # 加载样本
    sample_dir = os.path.join(SAMPLES_ROOT, args.sample_dir)
    files = sorted([f for f in os.listdir(sample_dir) if f.endswith('.json')])
    if args.limit:
        files = files[:args.limit]

    print(f"\n样本目录: {args.sample_dir}/  ({len(files)} 个文件)")
    print(f"{'='*65}")

    # ── 逐条解码并记录结果 ─────────────────────────────────────────────────
    results = []

    for fname in files:
        fpath = os.path.join(sample_dir, fname)
        with open(fpath, encoding='utf-8') as f:
            data = json.load(f)
        data.pop("_noise_label", None)

        gt_is_noise = is_noise_sample(fname)

        try:
            req = IntelligenceDecodeRequest(
                source_id=data['source_id'],
                source_type=data['source_type'],
                title=data.get('title'),
                content=data['content'],
                published_at=data.get('published_at'),
                source_name=data.get('source_name'),
                language=data.get('language', 'en'),
                mode=data.get('mode', 'prompt_first'),
            )
            result = decoder.decode(req)
            signals = result.signals
            pred_is_noise = (len(signals) == 0)

        except Exception as e:
            signals = []
            pred_is_noise = True
            print(f"  ERROR [{fname}]: {e}")

        # 判断 TP/TN/FP/FN
        if not gt_is_noise and not pred_is_noise:
            verdict = "TP"   # 正例，预测有信号 ✅
        elif gt_is_noise and pred_is_noise:
            verdict = "TN"   # 噪音，预测无信号 ✅
        elif not gt_is_noise and pred_is_noise:
            verdict = "FN"   # 正例，预测无信号 ❌ 漏报
        else:
            verdict = "FP"   # 噪音，预测有信号 ❌ 误报

        results.append({
            "file": fname,
            "gt_noise": gt_is_noise,
            "pred_noise": pred_is_noise,
            "signal_count": len(signals),
            "verdict": verdict,
            "signals": [(s.signal_type, s.signal_label, s.intensity_score, s.confidence_score)
                        for s in signals],
        })

        icon = "✅" if verdict in ("TP", "TN") else "❌"
        tag = f"[{verdict}]"
        sig_summary = f"{len(signals)} 信号" if not pred_is_noise else "0 信号"
        gt_tag = "GT:noise" if gt_is_noise else "GT:signal"
        print(f"  {icon} {tag:4s} {gt_tag:10s} {sig_summary:8s}  {fname}")

        if args.verbose and signals:
            for s in signals:
                print(f"         - [{s.signal_type}] {s.signal_label} (I={s.intensity_score}, C={s.confidence_score})")

    # ── 统计 ────────────────────────────────────────────────────────────────
    tp = sum(1 for r in results if r['verdict'] == 'TP')
    tn = sum(1 for r in results if r['verdict'] == 'TN')
    fp = sum(1 for r in results if r['verdict'] == 'FP')
    fn = sum(1 for r in results if r['verdict'] == 'FN')

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy  = (tp + tn) / len(results) if results else 0

    print(f"\n{'='*65}")
    print(f"  Prompt 版本 : {m21_prompts.PROMPT_VERSION}")
    print(f"  样本总数    : {len(results)}")
    print(f"  TP={tp}  TN={tn}  FP={fp}  FN={fn}")
    print(f"  Precision   : {precision:.1%}   (抽出来的有多少是真正应该抽的)")
    print(f"  Recall      : {recall:.1%}   (应该抽的有多少被抽到了)")
    print(f"  F1          : {f1:.1%}")
    print(f"  Accuracy    : {accuracy:.1%}")
    print(f"{'='*65}")

    # FP 详情
    fp_list = [r for r in results if r['verdict'] == 'FP']
    if fp_list:
        print(f"\n⚠️  FP 误报详情（{len(fp_list)} 条）：")
        for r in fp_list:
            print(f"  {r['file']}")
            for sig in r['signals']:
                print(f"    - [{sig[0]}] {sig[1]} (I={sig[2]}, C={sig[3]})")

    fn_list = [r for r in results if r['verdict'] == 'FN']
    if fn_list:
        print(f"\n⚠️  FN 漏报详情（{len(fn_list)} 条）：")
        for r in fn_list:
            print(f"  {r['file']}")

    # 保存结果
    out = {
        "prompt_version": m21_prompts.PROMPT_VERSION,
        "run_at": datetime.utcnow().isoformat() + "Z",
        "sample_dir": args.sample_dir,
        "total": len(results),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "details": results,
    }
    out_path = os.path.join(BASE, f"precision_report_{m21_prompts.PROMPT_VERSION}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n报告已保存: {os.path.basename(out_path)}")


if __name__ == "__main__":
    main()
