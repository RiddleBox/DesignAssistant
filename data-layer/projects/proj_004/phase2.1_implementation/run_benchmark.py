"""
Phase 2.1 首轮 Baseline Benchmark 执行脚本
基于 benchmark_samples.json 中的 28 个已标注样本
"""

import json
import os
import time
from collections import Counter
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import importlib.util

from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest, DecodedIntelligence, Signal, SourceType


_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
_LLM_CONFIG_PATH = _PROJECT_ROOT / "llm_config.py"


def _load_llm_config(phase: str) -> Dict[str, Any]:
    spec = importlib.util.spec_from_file_location("llm_config", _LLM_CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Failed to load llm_config from {_LLM_CONFIG_PATH}"
    spec.loader.exec_module(module)
    return module.get_llm_config(phase)


class BenchmarkRunner:
    """Benchmark 执行器"""

    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.decoder = IntelligenceDecoder(
            api_key=llm_config.get("api_key", ""),
            model=llm_config.get("model", "claude-opus-4-6"),
            provider=llm_config.get("provider", "anthropic"),
            base_url=llm_config.get("base_url", ""),
        )
        self.results = []
        self.metrics = {}

    def load_samples(self, file_path: str) -> List[Dict[str, Any]]:
        """加载标注样本"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("samples", [])

    def run_benchmark(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行 benchmark"""
        print(f"开始执行 benchmark，共 {len(samples)} 个样本\n")

        total_samples = len(samples)
        schema_valid_count = 0
        total_processing_time = 0

        # 信号级别统计
        true_positives = 0  # 正确抽取的信号
        false_positives = 0  # 误报的信号
        false_negatives = 0  # 漏报的信号

        # 2.1 V2 结构化覆盖与审计统计
        total_actual_signals = 0
        logic_frame_present_count = 0
        logic_frame_complete_count = 0
        affects_non_empty_count = 0
        change_direction_counter = Counter()
        audit_flag_counter = Counter()

        # 错误案例收集
        false_positive_cases = []
        false_negative_cases = []
        boundary_cases = []
        high_quality_cases = []

        for idx, sample in enumerate(samples, 1):
            print(f"[{idx}/{total_samples}] 处理样本 {sample['sample_id']}...")

            # 构建请求
            request = IntelligenceDecodeRequest(
                source_id=sample['sample_id'],
                source_type=SourceType(sample['source_type']),
                title=sample.get('title'),
                content=sample['content'],
                published_at=sample.get('published_at'),
                source_name=sample.get('source_name')
            )

            # 执行解码
            try:
                result = self.decoder.decode(request)

                # Schema 合法性检查
                if result.signals is not None:
                    schema_valid_count += 1

                total_processing_time += result.processing_time_ms

                # 信号级别评估
                expected_signals = sample['annotation']['expected_signals']
                actual_signals = result.signals

                signal_stats = self._collect_signal_contract_stats(actual_signals)
                total_actual_signals += signal_stats['total_actual_signals']
                logic_frame_present_count += signal_stats['logic_frame_present_count']
                logic_frame_complete_count += signal_stats['logic_frame_complete_count']
                affects_non_empty_count += signal_stats['affects_non_empty_count']
                change_direction_counter.update(signal_stats['change_direction_counter'])
                audit_flag_counter.update(signal_stats['audit_flag_counter'])

                # 计算 TP, FP, FN
                tp, fp, fn, case_analysis = self._evaluate_signals(
                    sample, expected_signals, actual_signals
                )

                true_positives += tp
                false_positives += fp
                false_negatives += fn

                # 收集案例
                if case_analysis['is_high_quality']:
                    high_quality_cases.append(case_analysis)
                if case_analysis['false_positives']:
                    false_positive_cases.append(case_analysis)
                if case_analysis['false_negatives']:
                    false_negative_cases.append(case_analysis)
                if case_analysis['is_boundary']:
                    boundary_cases.append(case_analysis)

                # 保存结果
                self.results.append({
                    'sample_id': sample['sample_id'],
                    'source_type': sample['source_type'],
                    'expected_count': len(expected_signals),
                    'actual_count': len(actual_signals),
                    'logic_frame_stats': {
                        'total_actual_signals': signal_stats['total_actual_signals'],
                        'logic_frame_present_count': signal_stats['logic_frame_present_count'],
                        'logic_frame_complete_count': signal_stats['logic_frame_complete_count'],
                        'affects_non_empty_count': signal_stats['affects_non_empty_count'],
                        'change_direction_counter': dict(signal_stats['change_direction_counter']),
                        'audit_flag_counter': dict(signal_stats['audit_flag_counter']),
                    },
                    'tp': tp,
                    'fp': fp,
                    'fn': fn,
                    'processing_time_ms': result.processing_time_ms,
                    'warnings': result.warnings,
                    'case_analysis': case_analysis
                })

                print(f"  [OK] 完成 (TP={tp}, FP={fp}, FN={fn}, 耗时={result.processing_time_ms}ms)")

            except Exception as e:
                print(f"  [ERROR] 失败: {str(e)}")
                self.results.append({
                    'sample_id': sample['sample_id'],
                    'error': str(e)
                })

        # 计算指标
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        self.metrics = {
            'total_samples': total_samples,
            'schema_valid_rate': schema_valid_count / total_samples,
            'avg_processing_time_ms': total_processing_time / total_samples,
            'signal_level_precision': precision,
            'signal_level_recall': recall,
            'signal_level_f1': f1,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'logic_frame_coverage': {
                'total_actual_signals': total_actual_signals,
                'logic_frame_present_count': logic_frame_present_count,
                'logic_frame_complete_count': logic_frame_complete_count,
                'affects_non_empty_count': affects_non_empty_count,
                'logic_frame_present_rate': logic_frame_present_count / total_actual_signals if total_actual_signals else 0,
                'logic_frame_complete_rate': logic_frame_complete_count / total_actual_signals if total_actual_signals else 0,
                'affects_non_empty_rate': affects_non_empty_count / total_actual_signals if total_actual_signals else 0,
                'change_direction_distribution': dict(change_direction_counter),
            },
            'audit_statistics': {
                'signals_with_audit_flags': sum(audit_flag_counter.values()),
                'audit_flag_counts': dict(audit_flag_counter),
            },
            'high_quality_cases': high_quality_cases[:2],
            'false_positive_cases': false_positive_cases[:2],
            'false_negative_cases': false_negative_cases[:2],
            'boundary_cases': boundary_cases[:2]
        }

        return self.metrics

    def _collect_signal_contract_stats(self, actual: List[Signal]) -> Dict[str, Any]:
        """统计 2.1 V2 logic_frame 覆盖率与 audit flags。"""
        stats = {
            'total_actual_signals': len(actual),
            'logic_frame_present_count': 0,
            'logic_frame_complete_count': 0,
            'affects_non_empty_count': 0,
            'change_direction_counter': Counter(),
            'audit_flag_counter': Counter(),
        }

        for signal in actual:
            logic_frame = getattr(signal, 'logic_frame', None)
            if logic_frame:
                stats['logic_frame_present_count'] += 1
                what_changed = str(getattr(logic_frame, 'what_changed', '') or '').strip()
                change_direction = getattr(logic_frame, 'change_direction', None)
                affects = getattr(logic_frame, 'affects', []) or []

                if what_changed and change_direction:
                    stats['logic_frame_complete_count'] += 1
                    stats['change_direction_counter'][str(change_direction.value if hasattr(change_direction, 'value') else change_direction)] += 1

                if affects:
                    stats['affects_non_empty_count'] += 1

            metadata = getattr(signal, 'metadata', None) or {}
            audit = metadata.get('audit', {}) if isinstance(metadata, dict) else {}
            flags = audit.get('audit_flags', []) if isinstance(audit, dict) else []
            for flag in flags:
                stats['audit_flag_counter'][str(flag)] += 1

        return stats

    def _evaluate_signals(
        self,
        sample: Dict[str, Any],
        expected: List[Dict[str, Any]],
        actual: List[Signal]
    ) -> Tuple[int, int, int, Dict[str, Any]]:
        """评估信号级别的 TP, FP, FN"""

        tp = 0
        fp = 0
        fn = 0

        matched_expected = set()
        matched_actual = set()

        false_positive_details = []
        false_negative_details = []

        # 宽松匹配逻辑：主要看信号类型和语义相似度
        for i, exp_sig in enumerate(expected):
            matched = False
            for j, act_sig in enumerate(actual):
                if j in matched_actual:
                    continue

                # 宽松匹配：类型相同即可视为匹配（因为标签命名风格不同）
                # 如果一个样本只有一个预期信号，且类型匹配，则认为是正确的
                if exp_sig['signal_type'] == act_sig.signal_type.value:
                    # 进一步检查：描述是否语义相关
                    if self._semantic_match(exp_sig, act_sig, sample):
                        tp += 1
                        matched_expected.add(i)
                        matched_actual.add(j)
                        matched = True
                        break

            if not matched:
                fn += 1
                false_negative_details.append({
                    'expected_type': exp_sig['signal_type'],
                    'expected_label': exp_sig['signal_label'],
                    'expected_description': exp_sig['description']
                })

        # 未匹配的 actual 为误报
        for j, act_sig in enumerate(actual):
            if j not in matched_actual:
                fp += 1
                false_positive_details.append({
                    'actual_type': act_sig.signal_type.value,
                    'actual_label': act_sig.signal_label,
                    'actual_description': act_sig.description,
                    'confidence_score': act_sig.confidence_score
                })

        # 案例分析
        is_high_quality = (tp > 0 and fp == 0 and fn == 0)
        is_boundary = sample['sample_id'].startswith('E')  # 边界样本

        case_analysis = {
            'sample_id': sample['sample_id'],
            'source_type': sample['source_type'],
            'title': sample.get('title', ''),
            'is_high_quality': is_high_quality,
            'is_boundary': is_boundary,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'false_positives': false_positive_details,
            'false_negatives': false_negative_details
        }

        return tp, fp, fn, case_analysis

    def _semantic_match(self, expected: Dict[str, Any], actual: Signal, sample: Dict[str, Any]) -> bool:
        """语义匹配判断"""
        # 如果样本只有一个预期信号，且类型已匹配，则认为是正确的
        if len(sample['annotation']['expected_signals']) == 1:
            return True

        # 多信号情况：检查关键词重叠
        exp_text = (expected.get('description', '') + ' ' + expected.get('signal_label', '')).lower()
        act_text = (actual.description + ' ' + actual.signal_label).lower()

        # 提取关键词（简单分词）
        import re
        exp_words = set(re.findall(r'\w+', exp_text))
        act_words = set(re.findall(r'\w+', act_text))

        # 计算重叠度
        if len(exp_words) > 0:
            overlap = len(exp_words & act_words) / len(exp_words)
            return overlap > 0.3  # 30% 重叠即认为匹配

        return False

    def generate_report(self, output_path: str):
        """生成 benchmark 报告"""
        report = {
            'benchmark_info': {
                'run_at': datetime.utcnow().isoformat() + 'Z',
                'decoder_version': self.decoder.decoder_version,
                'model': self.decoder.model
            },
            'metrics': self.metrics,
            'detailed_results': self.results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Benchmark 报告已保存至: {output_path}")


def main():
    """主函数"""
    llm_config = _load_llm_config("2.1")
    if not llm_config.get("api_key"):
        print("错误: 未找到 2.1 LLM API key")
        print("请在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 api_key")
        return

    runner = BenchmarkRunner(llm_config=llm_config)

    samples_path = _THIS_DIR / "data" / "benchmark_samples.json"
    samples = runner.load_samples(str(samples_path))

    metrics = runner.run_benchmark(samples)

    print("\n" + "="*60)
    print("Phase 2.1 首轮 Baseline Benchmark 结果")
    print("="*60)
    print(f"\n[核心指标]")
    print(f"  样本总数: {metrics['total_samples']}")
    print(f"  Schema 合法率: {metrics['schema_valid_rate']:.2%}")
    print(f"  平均处理耗时: {metrics['avg_processing_time_ms']:.0f} ms")
    print(f"\n[信号级别指标]")
    print(f"  Precision: {metrics['signal_level_precision']:.2%}")
    print(f"  Recall: {metrics['signal_level_recall']:.2%}")
    print(f"  F1 Score: {metrics['signal_level_f1']:.2%}")
    print(f"\n[信号统计]")
    print(f"  True Positives (TP): {metrics['true_positives']}")
    print(f"  False Positives (FP): {metrics['false_positives']}")
    print(f"  False Negatives (FN): {metrics['false_negatives']}")
    print(f"\n[2.1 V2 结构化覆盖]")
    print(f"  实际信号总数: {metrics['logic_frame_coverage']['total_actual_signals']}")
    print(f"  logic_frame 覆盖率: {metrics['logic_frame_coverage']['logic_frame_present_rate']:.2%}")
    print(f"  logic_frame 完整率: {metrics['logic_frame_coverage']['logic_frame_complete_rate']:.2%}")
    print(f"  affects 非空率: {metrics['logic_frame_coverage']['affects_non_empty_rate']:.2%}")
    print(f"  change_direction 分布: {metrics['logic_frame_coverage']['change_direction_distribution']}")
    print(f"\n[audit 统计]")
    print(f"  audit flag 总数: {metrics['audit_statistics']['signals_with_audit_flags']}")
    print(f"  audit flag 分布: {metrics['audit_statistics']['audit_flag_counts']}")

    report_path = _THIS_DIR / "data" / "benchmark_report.json"
    runner.generate_report(str(report_path))

    print("\n" + "="*60)


if __name__ == '__main__':
    main()