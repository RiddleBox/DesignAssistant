"""
Phase 2.1 v1.0 vs v1.1 对比分析脚本
生成前后对比表和错误类型变化分析
"""

import json
from typing import Dict, Any, List
from collections import defaultdict


class BenchmarkComparator:
    """Benchmark 版本对比分析器"""

    def __init__(self, v1_0_path: str, v1_1_path: str):
        with open(v1_0_path, 'r', encoding='utf-8') as f:
            self.v1_0 = json.load(f)
        with open(v1_1_path, 'r', encoding='utf-8') as f:
            self.v1_1 = json.load(f)

    def compare_metrics(self) -> Dict[str, Any]:
        """对比核心指标"""
        v1_0_metrics = self.v1_0['metrics']
        v1_1_metrics = self.v1_1['metrics']

        return {
            'precision': {
                'v1.0': v1_0_metrics['signal_level_precision'],
                'v1.1': v1_1_metrics['signal_level_precision'],
                'delta': v1_1_metrics['signal_level_precision'] - v1_0_metrics['signal_level_precision']
            },
            'recall': {
                'v1.0': v1_0_metrics['signal_level_recall'],
                'v1.1': v1_1_metrics['signal_level_recall'],
                'delta': v1_1_metrics['signal_level_recall'] - v1_0_metrics['signal_level_recall']
            },
            'f1': {
                'v1.0': v1_0_metrics['signal_level_f1'],
                'v1.1': v1_1_metrics['signal_level_f1'],
                'delta': v1_1_metrics['signal_level_f1'] - v1_0_metrics['signal_level_f1']
            },
            'tp': {
                'v1.0': v1_0_metrics['true_positives'],
                'v1.1': v1_1_metrics['true_positives'],
                'delta': v1_1_metrics['true_positives'] - v1_0_metrics['true_positives']
            },
            'fp': {
                'v1.0': v1_0_metrics['false_positives'],
                'v1.1': v1_1_metrics['false_positives'],
                'delta': v1_1_metrics['false_positives'] - v1_0_metrics['false_positives']
            },
            'fn': {
                'v1.0': v1_0_metrics['false_negatives'],
                'v1.1': v1_1_metrics['false_negatives'],
                'delta': v1_1_metrics['false_negatives'] - v1_0_metrics['false_negatives']
            }
        }

    def analyze_fp_changes(self) -> Dict[str, Any]:
        """分析误报变化"""
        v1_0_results = {r['sample_id']: r for r in self.v1_0['detailed_results']}
        v1_1_results = {r['sample_id']: r for r in self.v1_1['detailed_results']}

        fp_eliminated = []  # 消失的误报
        fp_persistent = []  # 顽固的误报
        fp_new = []  # 新增的误报

        for sample_id in v1_0_results:
            v1_0_fp = v1_0_results[sample_id].get('case_analysis', {}).get('false_positives', [])
            v1_1_fp = v1_1_results[sample_id].get('case_analysis', {}).get('false_positives', [])

            # 简单对比：按类型统计
            v1_0_fp_types = [fp['actual_type'] for fp in v1_0_fp]
            v1_1_fp_types = [fp['actual_type'] for fp in v1_1_fp]

            # 消失的误报
            for fp in v1_0_fp:
                if fp['actual_type'] not in v1_1_fp_types:
                    fp_eliminated.append({
                        'sample_id': sample_id,
                        'type': fp['actual_type'],
                        'label': fp['actual_label']
                    })

            # 顽固的误报（两个版本都存在）
            for fp in v1_1_fp:
                if fp['actual_type'] in v1_0_fp_types:
                    fp_persistent.append({
                        'sample_id': sample_id,
                        'type': fp['actual_type'],
                        'label': fp['actual_label']
                    })

            # 新增的误报
            for fp in v1_1_fp:
                if fp['actual_type'] not in v1_0_fp_types:
                    fp_new.append({
                        'sample_id': sample_id,
                        'type': fp['actual_type'],
                        'label': fp['actual_label']
                    })

        # 按类型统计
        fp_eliminated_by_type = defaultdict(int)
        for fp in fp_eliminated:
            fp_eliminated_by_type[fp['type']] += 1

        fp_persistent_by_type = defaultdict(int)
        for fp in fp_persistent:
            fp_persistent_by_type[fp['type']] += 1

        return {
            'eliminated': {
                'total': len(fp_eliminated),
                'by_type': dict(fp_eliminated_by_type),
                'samples': fp_eliminated[:5]
            },
            'persistent': {
                'total': len(fp_persistent),
                'by_type': dict(fp_persistent_by_type),
                'samples': fp_persistent[:5]
            },
            'new': {
                'total': len(fp_new),
                'samples': fp_new[:5]
            }
        }

    def identify_taxonomy_issues(self) -> List[Dict[str, Any]]:
        """识别 taxonomy 问题样本"""
        taxonomy_issues = []

        v1_1_results = self.v1_1['detailed_results']

        for result in v1_1_results:
            case = result.get('case_analysis', {})

            # 识别可能的 taxonomy 问题
            # 1. 同时有 FP 和 FN，且类型相关
            if case.get('fp', 0) > 0 and case.get('fn', 0) > 0:
                fps = case.get('false_positives', [])
                fns = case.get('false_negatives', [])

                for fp in fps:
                    for fn in fns:
                        # capital vs market 混淆
                        if (fp['actual_type'] == 'capital' and fn['expected_type'] == 'market') or \
                           (fp['actual_type'] == 'market' and fn['expected_type'] == 'capital'):
                            taxonomy_issues.append({
                                'sample_id': result['sample_id'],
                                'issue_type': 'capital_market_confusion',
                                'actual': fp['actual_type'],
                                'expected': fn['expected_type'],
                                'note': '大型收购/投资事件的分类歧义'
                            })

        return taxonomy_issues

    def generate_comparison_report(self, output_path: str):
        """生成对比报告"""
        metrics_comparison = self.compare_metrics()
        fp_changes = self.analyze_fp_changes()
        taxonomy_issues = self.identify_taxonomy_issues()

        report = {
            'comparison_summary': {
                'v1.0_version': self.v1_0['benchmark_info']['decoder_version'],
                'v1.1_version': self.v1_1['benchmark_info']['decoder_version'],
                'optimization_effective': metrics_comparison['precision']['delta'] > 0
            },
            'metrics_comparison': metrics_comparison,
            'fp_changes_analysis': fp_changes,
            'taxonomy_issues': taxonomy_issues,
            'key_findings': self._extract_key_findings(metrics_comparison, fp_changes)
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def _extract_key_findings(self, metrics: Dict, fp_changes: Dict) -> List[str]:
        """提取关键发现"""
        findings = []

        # Precision 变化
        precision_delta = metrics['precision']['delta']
        if precision_delta > 0.05:
            findings.append(f"Precision 提升 {precision_delta:.1%}，误报压制有效")
        elif precision_delta < -0.05:
            findings.append(f"Precision 下降 {abs(precision_delta):.1%}，优化过度或引入新问题")

        # Recall 变化
        recall_delta = metrics['recall']['delta']
        if abs(recall_delta) > 0.05:
            if recall_delta < 0:
                findings.append(f"Recall 下降 {abs(recall_delta):.1%}，约束过强导致漏报增加")
            else:
                findings.append(f"Recall 提升 {recall_delta:.1%}")

        # FP 消除情况
        fp_eliminated = fp_changes['eliminated']['total']
        if fp_eliminated > 0:
            findings.append(f"成功消除 {fp_eliminated} 个误报")
            if 'market' in fp_changes['eliminated']['by_type']:
                findings.append(f"其中 market 误报消除 {fp_changes['eliminated']['by_type']['market']} 个")

        # 顽固 FP
        fp_persistent = fp_changes['persistent']['total']
        if fp_persistent > 10:
            findings.append(f"仍有 {fp_persistent} 个顽固误报未解决")

        return findings

    def print_comparison(self):
        """打印对比摘要"""
        metrics = self.compare_metrics()
        fp_changes = self.analyze_fp_changes()

        print("\n" + "="*60)
        print("Phase 2.1 v1.0 vs v1.1 对比分析")
        print("="*60)

        print(f"\n[核心指标对比]")
        print(f"  Precision: {metrics['precision']['v1.0']:.2%} → {metrics['precision']['v1.1']:.2%} ({metrics['precision']['delta']:+.2%})")
        print(f"  Recall:    {metrics['recall']['v1.0']:.2%} → {metrics['recall']['v1.1']:.2%} ({metrics['recall']['delta']:+.2%})")
        print(f"  F1 Score:  {metrics['f1']['v1.0']:.2%} → {metrics['f1']['v1.1']:.2%} ({metrics['f1']['delta']:+.2%})")

        print(f"\n[信号统计对比]")
        print(f"  TP: {metrics['tp']['v1.0']} → {metrics['tp']['v1.1']} ({metrics['tp']['delta']:+d})")
        print(f"  FP: {metrics['fp']['v1.0']} → {metrics['fp']['v1.1']} ({metrics['fp']['delta']:+d})")
        print(f"  FN: {metrics['fn']['v1.0']} → {metrics['fn']['v1.1']} ({metrics['fn']['delta']:+d})")

        print(f"\n[误报变化分析]")
        print(f"  消除的误报: {fp_changes['eliminated']['total']} 个")
        if fp_changes['eliminated']['by_type']:
            for sig_type, count in fp_changes['eliminated']['by_type'].items():
                print(f"    - {sig_type}: {count} 个")

        print(f"  顽固的误报: {fp_changes['persistent']['total']} 个")
        if fp_changes['persistent']['by_type']:
            for sig_type, count in fp_changes['persistent']['by_type'].items():
                print(f"    - {sig_type}: {count} 个")

        if fp_changes['new']['total'] > 0:
            print(f"  新增的误报: {fp_changes['new']['total']} 个")


def main():
    v1_0_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_report_v1.0.json'
    v1_1_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_report_v1.1.json'
    output_path = 'd:/AIProjects/DesignAssistant/data-layer/projects/proj_004/phase2.1_implementation/data/benchmark_comparison.json'

    comparator = BenchmarkComparator(v1_0_path, v1_1_path)
    comparator.print_comparison()

    report = comparator.generate_comparison_report(output_path)

    print(f"\n[关键发现]")
    for finding in report['key_findings']:
        print(f"  - {finding}")

    if report['taxonomy_issues']:
        print(f"\n[Taxonomy 问题]")
        print(f"  发现 {len(report['taxonomy_issues'])} 个可能的标注歧义样本")
        for issue in report['taxonomy_issues'][:3]:
            print(f"    - {issue['sample_id']}: {issue['issue_type']}")

    print(f"\n[OK] 对比报告已保存至: {output_path}")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()