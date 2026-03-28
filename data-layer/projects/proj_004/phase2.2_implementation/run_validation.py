"""
Phase 2.2 机会判断模块 - 验证运行器

运行所有验证案例，生成验收报告

变更记录：
- 2026-03-28 v2：适配多机会输出（opportunities: List[OpportunityObject]）
"""

from judgment_engine import JudgmentEngine
from validation_cases import VALIDATION_CASES
import json
from datetime import datetime


class ValidationRunner:
    """验证运行器"""

    def __init__(self):
        self.engine = JudgmentEngine()
        self.results = []

    def run_all_cases(self):
        """运行所有验证案例"""
        print("=" * 80)
        print("Phase 2.2 机会判断模块 - 验证运行")
        print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"案例数量: {len(VALIDATION_CASES)}")
        print("=" * 80)

        for i, case in enumerate(VALIDATION_CASES, 1):
            print(f"\n[{i}/{len(VALIDATION_CASES)}] 运行案例: {case['case_id']}")
            print(f"描述: {case['description']}")
            print(f"预期优先级: {case.get('expected_priority', 'N/A')}")
            print("-" * 80)

            # 执行判断
            result = self.engine.judge(case["request"])

            # 验证结果
            validation = self._validate_result(case, result)

            # 保存结果
            self.results.append({
                "case": case,
                "result": result,
                "validation": validation
            })

            # 输出结果
            self._print_result(result, validation)

        # 生成验收报告
        self._generate_report()

    def _validate_result(self, case, result):
        """验证结果是否符合预期（适配多机会输出）"""
        validation = {
            "schema_valid": True,
            "priority_match": False,
            "evidence_parallel": False,
            "assumptions_explicit": False,
            "uncertainty_marked": False,
            "boundary_respected": True,
            "opportunity_count": 0,
            "errors": []
        }

        try:
            # error 状态
            if result.status == "error":
                validation["schema_valid"] = False
                validation["errors"].append(f"返回错误状态: {result.error}")
                return validation

            opportunities = result.opportunities
            validation["opportunity_count"] = len(opportunities)

            # insufficient_evidence：空列表属正常
            if result.status == "insufficient_evidence":
                validation["evidence_parallel"] = True
                validation["assumptions_explicit"] = True
                validation["uncertainty_marked"] = True
                return validation

            if not opportunities:
                validation["errors"].append("success 状态但 opportunities 为空")
                return validation

            # 检查预期优先级：用第一个机会（最高优先级）匹配
            expected_priority = case.get("expected_priority")
            best_level_order = ["escalate", "deep_dive", "research", "watch"]
            sorted_opps = sorted(
                opportunities,
                key=lambda o: best_level_order.index(o.priority_level)
                if o.priority_level in best_level_order else 99
            )
            if expected_priority:
                if sorted_opps[0].priority_level == expected_priority:
                    validation["priority_match"] = True
                else:
                    validation["errors"].append(
                        f"最高优先级不匹配: 预期={expected_priority}, "
                        f"实际={sorted_opps[0].priority_level}"
                    )

            # 逐个机会检查完整性
            all_evidence_ok = True
            all_assumptions_ok = True
            all_uncertainty_ok = True

            for opp in opportunities:
                if not (opp.supporting_evidence and opp.counter_evidence):
                    all_evidence_ok = False
                    validation["errors"].append(
                        f"[{opp.opportunity_title}] 支持/反对证据未并列"
                    )
                if not opp.key_assumptions:
                    all_assumptions_ok = False
                    validation["errors"].append(
                        f"[{opp.opportunity_title}] 关键假设未显式化"
                    )
                if not opp.uncertainty_map:
                    all_uncertainty_ok = False
                    validation["errors"].append(
                        f"[{opp.opportunity_title}] 不确定性未标注"
                    )

            validation["evidence_parallel"] = all_evidence_ok
            validation["assumptions_explicit"] = all_assumptions_ok
            validation["uncertainty_marked"] = all_uncertainty_ok

            # 边界检查
            if result.diagnostics and result.diagnostics.boundary_warnings:
                for warning in result.diagnostics.boundary_warnings:
                    if "越界" in warning:
                        validation["boundary_respected"] = False
                        validation["errors"].append(f"边界警告: {warning}")

        except Exception as e:
            validation["schema_valid"] = False
            validation["errors"].append(f"验证异常: {str(e)}")

        return validation

    def _print_result(self, result, validation):
        """打印结果（适配多机会输出）"""
        print(f"状态: {result.status}")
        print(f"识别机会数: {len(result.opportunities)}")

        for j, opp in enumerate(result.opportunities, 1):
            print(f"\n  机会 #{j}: {opp.opportunity_title}")
            print(f"  优先级: {opp.priority_level}")
            print(f"  论点: {opp.opportunity_thesis[:80]}...")
            if opp.why_now:
                print(f"  时机: {opp.why_now[:60]}...")
            print(f"  支持证据: {len(opp.supporting_evidence)}条 | "
                  f"反对证据: {len(opp.counter_evidence)}条 | "
                  f"假设: {len(opp.key_assumptions)}条 | "
                  f"不确定性: {len(opp.uncertainty_map)}条")
            if opp.warnings:
                print(f"  ⚠️ warnings: {opp.warnings}")

        if result.diagnostics:
            print(f"\n诊断: 信号={result.diagnostics.signal_count} | "
                  f"机会数={result.diagnostics.opportunity_count} | "
                  f"平均证据完整度={result.diagnostics.evidence_completeness:.2f}")
            if result.diagnostics.boundary_warnings:
                print(f"边界警告: {result.diagnostics.boundary_warnings}")

        # 验证结果
        print(f"\n验证结果:")
        print(f"  Schema合法: {'✅' if validation['schema_valid'] else '❌'}")
        print(f"  优先级匹配: {'✅' if validation['priority_match'] else '❌'}")
        print(f"  证据并列: {'✅' if validation['evidence_parallel'] else '❌'}")
        print(f"  假设显式: {'✅' if validation['assumptions_explicit'] else '❌'}")
        print(f"  不确定性标注: {'✅' if validation['uncertainty_marked'] else '❌'}")
        print(f"  边界遵守: {'✅' if validation['boundary_respected'] else '❌'}")

        if validation["errors"]:
            print(f"  ❌ 错误详情: {validation['errors']}")

    def _generate_report(self):
        """生成验收报告"""
        print("\n" + "=" * 80)
        print("验收报告")
        print("=" * 80)

        total = len(self.results)
        schema_valid      = sum(1 for r in self.results if r["validation"]["schema_valid"])
        priority_match    = sum(1 for r in self.results if r["validation"]["priority_match"])
        evidence_parallel = sum(1 for r in self.results if r["validation"]["evidence_parallel"])
        assumptions_ok    = sum(1 for r in self.results if r["validation"]["assumptions_explicit"])
        uncertainty_ok    = sum(1 for r in self.results if r["validation"]["uncertainty_marked"])
        boundary_ok       = sum(1 for r in self.results if r["validation"]["boundary_respected"])
        total_opps        = sum(r["validation"]["opportunity_count"] for r in self.results)

        print(f"\n总案例数: {total} | 识别机会总数: {total_opps} | 平均每案例: {total_opps/total:.1f}")
        print(f"\n验收检查项:")
        print(f"  Schema合法性:   {schema_valid}/{total} ({schema_valid/total*100:.0f}%) - 目标: 100%")
        print(f"  优先级匹配:     {priority_match}/{total} ({priority_match/total*100:.0f}%) - 目标: 80%")
        print(f"  证据并列:       {evidence_parallel}/{total} ({evidence_parallel/total*100:.0f}%) - 目标: 100%")
        print(f"  假设显式化:     {assumptions_ok}/{total} ({assumptions_ok/total*100:.0f}%) - 目标: 100%")
        print(f"  不确定性标注:   {uncertainty_ok}/{total} ({uncertainty_ok/total*100:.0f}%) - 目标: 100%")
        print(f"  边界遵守:       {boundary_ok}/{total} ({boundary_ok/total*100:.0f}%) - 目标: 100%")

        # 验收结论
        passed = (
            schema_valid == total and
            evidence_parallel == total and
            assumptions_ok == total and
            uncertainty_ok == total and
            boundary_ok == total and
            priority_match >= total * 0.8
        )
        print(f"\n验收结论: {'[PASS] 可推进' if passed else '[FAIL] 需返工'}")
        if not passed:
            if schema_valid < total:      print("  - Schema合法性未达标")
            if evidence_parallel < total: print("  - 证据并列未达标")
            if assumptions_ok < total:    print("  - 假设显式化未达标")
            if uncertainty_ok < total:    print("  - 不确定性标注未达标")
            if boundary_ok < total:       print("  - 边界遵守未达标")
            if priority_match < total * 0.8:
                print(f"  - 优先级匹配率 {priority_match/total*100:.0f}% 低于80%")


if __name__ == "__main__":
    runner = ValidationRunner()
    runner.run_all_cases()
