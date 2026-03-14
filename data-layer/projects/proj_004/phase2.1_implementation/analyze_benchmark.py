"""
Phase 2.1 Benchmark 结果分析脚本
基于 benchmark_report.json 产出错误画像和优化建议
"""

import json
from typing import Dict, Any, List
from collections import defaultdict


class BenchmarkAnalyzer:
    """Benchmark 结果分析器"""

    def __init__(self, report_path: str):
        with open(report_path, 'r', encoding='utf-8') as f:
            self.report = json.load(f)
        self.metrics = self.report['metrics']
        self.results = self.report['detailed_results']

    def analyze_error_profile(self) -> Dict[str, Any]:
        """分析错误画像"""

        # 误报分析
        fp_by_type = defaultdict(int)
        fp_by_source = defaultdict(int)
        pr_misreports = []
        high_confidence_fps = []

        for result in self.results:
            if 'case_analysis' not in result:
                continue

            case = result['case_analysis']

            # 统计误报
            for fp in case.get('false_positives', []):
                fp_by_type[fp['actual_type']] += 1
                fp_by_source[result['source_type']] += 1

                # 识别高置信度误报
                if fp.get('confidence_score', 0) >= 7:
                    high_confidence_fps.append({
                        'sample_id': result['sample_id'],
                        'type': fp['actual_type'],
                        'label': fp['actual_label'],
                        'confidence': fp['confidence_score']
                    })

        # 漏报分析
        fn_by_type = defaultdict(int)
        fn_by_source = defaultdict(int)

        for result in self.results:
            if 'case_analysis' not in result:
                continue

            case = result['case_analysis']

            for fn in case.get('false_negatives', []):
                fn_by_type[fn['expected_type']] += 1
                fn_by_source[result['source_type']] += 1

        # 边界样本表现
        boundary_performance = {
            'total': 0,
            'perfect': 0,
            'has_fp': 0,
            'has_fn': 0
        }

        for result in self.results:
            if 'case_analysis' not in result:
                continue

            case = result['case_analysis']
            if case.get('is_boundary'):
                boundary_performance['total'] += 1
                if case['fp'] == 0 and case['fn'] == 0:
                    boundary_performance['perfect'] += 1
                if case['fp'] > 0:
                    boundary_performance['has_fp'] += 1
                if case['fn'] > 0:
                    boundary_performance['has_fn'] += 1

        return {
            'false_positive_profile': {
                'by_signal_type': dict(fp_by_type),
                'by_source_type': dict(fp_by_source),
                'high_confidence_fps': high_confidence_fps[:5]
            },
            'false_negative_profile': {
                'by_signal_type': dict(fn_by_type),
                'by_source_type': dict(fn_by_source)
            },
            'boundary_sample_performance': boundary_performance
        }

    def generate_analysis_report(self, output_path: str):
        """生成分析报告"""

        error_profile = self.analyze_error_profile()

        # 判断是否需要优化
        needs_optimization = False
        optimization_triggers = []

        # 触发条件 1: Precision < 80%
        if self.metrics['signal_level_precision'] < 0.80:
            needs_optimization = True
            optimization_triggers.append(
                f"Precision 偏低 ({self.metrics['signal_level_precision']:.1%})，存在较多误报"
            )

        # 触发条件 2: Recall < 70%
        if self.metrics['signal_level_recall'] < 0.70:
            needs_optimization = True
            optimization_triggers.append(
                f"Recall 偏低 ({self.metrics['signal_level_recall']:.1%})，存在较多漏报"
            )

        # 触发条件 3: 高置信度误报 > 3 个
        high_conf_fps = error_profile['false_positive_profile']['high_confidence_fps']
        if len(high_conf_fps) > 3:
            needs_optimization = True
            optimization_triggers.append(
                f"存在 {len(high_conf_fps)} 个高置信度误报，边界判断不稳定"
            )

        # 生成优化建议
        optimization_suggestions = []
        if needs_optimization:
            optimization_suggestions = self._generate_suggestions(error_profile)

        analysis = {
            'summary': {
                'needs_optimization': needs_optimization,
                'optimization_triggers': optimization_triggers,
                'key_findings': self._extract_key_findings(error_profile)
            },
            'error_profile': error_profile,
            'optimization_suggestions': optimization_suggestions,
            'representative_cases': {
                'high_quality': self.metrics.get('high_quality_cases', []),
                'false_positives': self.metrics.get('false_positive_cases', []),
                'false_negatives': self.metrics.get('false_negative_cases', []),
                'boundary': self.metrics.get('boundary_cases', [])
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        return analysis

    def _extract_key_findings(self, error_profile: Dict[str, Any]) -> List[str]:
        """提取关键发现"""
        findings = []

        fp_profile = error_profile['false_positive_profile']
        fn_profile = error_profile['false_negative_profile']

        # 误报最多的信号类型
        if fp_profile['by_signal_type']:
            max_fp_type = max(fp_profile['by_signal_type'].items(), key=lambda x: x[1])
            findings.append(f"{max_fp_type[0]} 信号误报最多 ({max_fp_type[1]} 个)")

        # 漏报最多的信号类型
        if fn_profile['by_signal_type']:
            max_fn_type = max(fn_profile['by_signal_type'].items(), key=lambda x: x[1])
            findings.append(f"{max_fn_type[0]} 信号漏报最多 ({max_fn_type[1]} 个)")

        # 边界样本表现
        boundary = error_profile['boundary_sample_performance']
        if boundary['total'] > 0:
            perfect_rate = boundary['perfect'] / boundary['total']
            findings.append(f"边界样本完美率 {perfect_rate:.1%} ({boundary['perfect']}/{boundary['total']})")

        return findings

    def _generate_suggestions(self, error_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成优化建议（最多 2-5 条）"""
        suggestions = []

        fp_profile = error_profile['false_positive_profile']
        fn_profile = error_profile['false_negative_profile']

        # 建议 1: 针对误报最多的类型
        if fp_profile['by_signal_type']:
            max_fp_type = max(fp_profile['by_signal_type'].items(), key=lambda x: x[1])
            if max_fp_type[1] >= 3:
                suggestions.append({
                    'priority': 'P0',
                    'type': 'few_shot',
                    'description': f"补充 {max_fp_type[0]} 类型的边界样例和负例，压制误报"
                })

        # 建议 2: 针对高置信度误报
        if len(fp_profile['high_confidence_fps']) > 3:
            suggestions.append({
                'priority': 'P0',
                'type': 'prompt_role',
                'description': "在角色设定中强化'证据边界'和'克制原则'，避免过度自信"
            })

        # 建议 3: 针对漏报最多的类型
        if fn_profile['by_signal_type']:
            max_fn_type = max(fn_profile['by_signal_type'].items(), key=lambda x: x[1])
            if max_fn_type[1] >= 3:
                suggestions.append({
                    'priority': 'P1',
                    'type': 'few_shot',
                    'description': f"补充 {max_fn_type[0]} 类型的高质量正例，提升召回"
                })

        # 建议 4: 边界样本稳定性
        boundary = error_profile['boundary_sample_performance']
        if boundary['total'] > 0 and boundary['has_fp'] > boundary['total'] * 0.5:
            suggestions.append({
                'priority': 'P1',
                'type': 'constraint',
                'description': "在 Prompt 中显式说明'模糊样本应降低 confidence_score'"
            })

        return suggestions[:5]  # 最多 5 条

    def print_summary(self):
        """打印摘要"""
        print("\n" + "="*60)
        print("Phase 2.1 Benchmark 错误画像分析")
        print("="*60)

        print(f"\n[核心指标]")
        print(f"  Precision: {self.metrics['signal_level_precision']:.2%}")
        print(f"  Recall: {self.metrics['signal_level_recall']:.2%}")
        print(f"  F1 Score: {self.metrics['signal_level_f1']:.2%}")

        error_profile = self.analyze_error_profile()

        print(f"\n[误报画像]")
        fp_profile = error_profile['false_positive_profile']
        if fp_profile['by_signal_type']:
            for sig_type, count in fp_profile['by_signal_type'].items():
                print(f"  {sig_type}: {count} 个")

        print(f"\n[漏报画像]")
        fn_profile = error_profile['false_negative_profile']
        if fn_profile['by_signal_type']:
            for sig_type, count in fn_profile['by_signal_type'].items():
                print(f"  {sig_type}: {count} 个")

        print(f"\n[边界样本表现]")
        boundary = error_profile['boundary_sample_performance']
        if boundary['total'] > 0:
            print(f"  总数: {boundary['total']}")
            print(f"  完美: {boundary['perfect']} ({boundary['perfect']/boundary['total']:.1%})")
            print(f"  有误报: {boundary['has_fp']}")
            print(f"  有漏报: {boundary['has_fn']}")


def main():
    report_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_report.json'
    output_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_analysis.json'

    analyzer = BenchmarkAnalyzer(report_path)
    analyzer.print_summary()

    analysis = analyzer.generate_analysis_report(output_path)

    print(f"\n[优化建议]")
    if analysis['summary']['needs_optimization']:
        print("  [建议] 建议进行轻量优化")
        for trigger in analysis['summary']['optimization_triggers']:
            print(f"    - {trigger}")
        print(f"\n  具体建议:")
        for sug in analysis['optimization_suggestions']:
            print(f"    [{sug['priority']}] {sug['description']}")
    else:
        print("  [OK] 当前表现良好，暂不需要优化")

    print(f"\n[OK] 分析报告已保存至: {output_path}")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()