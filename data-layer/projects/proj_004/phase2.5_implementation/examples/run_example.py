"""
Phase 2.5 Example Runner

运行示例，验证系统复盘分析器的功能。
"""

import json
import sys
from pathlib import Path

# 添加phase2.5_implementation目录到路径
impl_dir = Path(__file__).parent.parent
sys.path.insert(0, str(impl_dir))

from schemas import SystemRetrospectiveRequest
from core import SystemRetrospectiveAnalyzer
from examples.example_data import EXAMPLE_REQUEST_DATA


def run_example():
    """
    运行示例分析
    """
    print("=" * 80)
    print("Phase 2.5 System Retrospective Analyzer - Example Run")
    print("=" * 80)
    print()

    # 创建请求对象
    print("Step 1: Create system retrospective request...")
    request = SystemRetrospectiveRequest(**EXAMPLE_REQUEST_DATA)
    print(f"  [OK] Request ID: {request.request_id}")
    print(f"  [OK] Case ID: {request.case_id}")
    print(f"  [OK] Validation Mode: {request.validation_mode.value}")
    print()

    # 创建分析器
    print("Step 2: Initialize system retrospective analyzer...")
    analyzer = SystemRetrospectiveAnalyzer()
    print(f"  [OK] Analyzer Version: {analyzer.VERSION}")
    print()

    # 执行分析
    print("Step 3: Execute system retrospective analysis...")
    print("  - Real workflow execution (consume upstream outputs)")
    print("  - Output checks (completeness, consistency, understandability)")
    print("  - Problem attribution (layered, evidence collection, confidence)")
    print("  - Phase 3 priority closure (derive priorities from attribution)")
    print()

    result = analyzer.analyze(request)

    print(f"  [OK] Analysis completed, time: {result.processing_time_ms}ms")
    print()

    # 输出结果摘要
    print("=" * 80)
    print("Analysis Results Summary")
    print("=" * 80)
    print()

    retrospective = result.retrospective

    print(f"Retrospective ID: {retrospective.retrospective_id}")
    print(f"Case ID: {retrospective.case_id}")
    print(f"Version: {retrospective.retrospective_version}")
    print()

    print("Workflow Summary:")
    print(f"  {retrospective.workflow_summary}")
    print()

    print("Output Check Results:")
    for check in retrospective.output_checks:
        status_symbol = "[PASS]" if check.status.value == "pass" else ("[WARN]" if check.status.value == "warning" else "[FAIL]")
        print(f"  {status_symbol} {check.check_type.value}: {check.status.value}")
        print(f"     {check.details}")
    print()

    print(f"Critical Findings: {len(retrospective.critical_findings)} items")
    for finding in retrospective.critical_findings:
        severity_symbol = "[HIGH]" if finding.severity.value == "high" else ("[MED]" if finding.severity.value == "medium" else "[LOW]")
        print(f"  {severity_symbol} {finding.summary}")
        print(f"     Layer: {finding.layer.value}")
        print(f"     Impact: {finding.impact}")
    print()

    print(f"Suspected Root Causes: {len(retrospective.suspected_root_causes)} items")
    for cause in retrospective.suspected_root_causes:
        confidence_symbol = "[HIGH]" if cause.confidence.value == "high_confidence" else ("[MED]" if cause.confidence.value == "medium_confidence" else "[LOW]")
        print(f"  {confidence_symbol} {cause.suspected_root_cause}")
        print(f"     Reasoning: {cause.reasoning}")
    print()

    print(f"Phase 3 Priorities: {len(retrospective.phase3_priorities)} items")
    for priority in retrospective.phase3_priorities[:5]:  # 只显示前5个
        print(f"  {priority.suggested_order}. [{priority.scope.value}] {priority.title}")
        print(f"     Reason: {priority.reason}")
    if len(retrospective.phase3_priorities) > 5:
        print(f"  ... and {len(retrospective.phase3_priorities) - 5} more items")
    print()

    print("Confidence Notes:")
    for note in retrospective.confidence_notes:
        print(f"  - {note}")
    print()

    if retrospective.warnings:
        print("Warnings:")
        for warning in retrospective.warnings:
            print(f"  [WARN] {warning}")
        print()

    print("=" * 80)
    print("Global Summary")
    print("=" * 80)
    print(result.global_summary)
    print()

    # 保存完整结果到JSON文件
    output_file = impl_dir / "examples" / "example_output.json"
    print(f"Saving complete results to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.dict(), f, ensure_ascii=False, indent=2)
    print("  [OK] Saved successfully")
    print()

    print("=" * 80)
    print("Example Run Completed")
    print("=" * 80)


if __name__ == "__main__":
    run_example()
