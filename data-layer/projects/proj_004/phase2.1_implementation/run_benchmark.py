"""
Phase 2.1 首轮 Baseline Benchmark 执行脚本
基于 benchmark_samples.json 中的 28 个已标注样本
"""

import json
import os
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest, DecodedIntelligence, Signal, SourceType


class BenchmarkRunner:
    """Benchmark 执行器"""

    def __init__(self, api_key: str):
        self.decoder = IntelligenceDecoder(api_key=api_key)
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
            'high_quality_cases': high_quality_cases[:2],
            'false_positive_cases': false_positive_cases[:2],
            'false_negative_cases': false_negative_cases[:2],
            'boundary_cases': boundary_cases[:2]
        }

        return self.metrics

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
    # 从环境变量读取 API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        # 尝试从 .env 文件读取
        env_path = 'd:/AIProjects/DesignAssistant/.env'
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('ANTHROPIC_API_KEY='):
                        api_key = line.strip().split('=', 1)[1].strip('"').strip("'")
                        break

    if not api_key:
        print("错误: 未找到 ANTHROPIC_API_KEY")
        print("请设置环境变量或在项目根目录创建 .env 文件")
        return

    # 初始化 runner
    runner = BenchmarkRunner(api_key=api_key)

    # 加载样本
    samples_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_samples.json'
    samples = runner.load_samples(samples_path)

    # 执行 benchmark
    metrics = runner.run_benchmark(samples)

    # 输出核心指标
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

    # 生成报告
    report_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_report.json'
    runner.generate_report(report_path)

    print("\n" + "="*60)


if __name__ == '__main__':
    main()