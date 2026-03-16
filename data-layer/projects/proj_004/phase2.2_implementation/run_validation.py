"""
Phase 2.2 机会判断模块 - 验证运行器

运行所有验证案例，生成验收报告
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
        """验证结果是否符合预期"""
        validation = {
            "schema_valid": True,
            "priority_match": False,
            "evidence_parallel": False,
            "assumptions_explicit": False,
            "uncertainty_marked": False,
            "boundary_respected": True,
            "errors": []
        }

        try:
            # 检查Schema合法性
            if result.opportunity is None and result.status == "error":
                validation["schema_valid"] = False
                validation["errors"].append("返回错误状态")
                return validation

            opp = result.opportunity

            # 检查优先级匹配
            expected_priority = case.get("expected_priority")
            if expected_priority and opp.priority_level == expected_priority:
                validation["priority_match"] = True
            elif expected_priority:
                validation["errors"].append(
                    f"优先级不匹配: 预期={expected_priority}, 实际={opp.priority_level}"
                )

            # 检查证据并列（insufficient_evidence状态豁免）
            if result.status == "insufficient_evidence":
                validation["evidence_parallel"] = True if opp.counter_evidence else False
            elif opp.supporting_evidence and opp.counter_evidence:
                validation["evidence_parallel"] = True
            else:
                validation["errors"].append("支持/反对证据未并列")

            # 检查假设显式化
            if opp.key_assumptions:
                validation["assumptions_explicit"] = True
            else:
                validation["errors"].append("关键假设未显式化")

            # 检查不确定性标注
            if opp.uncertainty_map:
                validation["uncertainty_marked"] = True
            else:
                validation["errors"].append("不确定性未标注")

            # 检查边界遵守
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
        """打印结果"""
        print(f"状态: {result.status}")

        if result.opportunity:
            opp = result.opportunity
            print(f"优先级: {opp.priority_level}")
            print(f"论点: {opp.opportunity_thesis}")
            print(f"支持证据: {len(opp.supporting_evidence)}条")
            print(f"反对证据: {len(opp.counter_evidence)}条")
            print(f"关键假设: {len(opp.key_assumptions)}条")
            print(f"不确定性: {len(opp.uncertainty_map)}条")

        if result.diagnostics:
            print(f"证据完整度: {result.diagnostics.evidence_completeness:.2f}")
            if result.diagnostics.boundary_warnings:
                print(f"边界警告: {result.diagnostics.boundary_warnings}")

        # 验证结果
        print(f"\n验证结果:")
        print(f"  [OK] Schema合法: {validation['schema_valid']}")
        print(f"  [OK] 优先级匹配: {validation['priority_match']}")
        print(f"  [OK] 证据并列: {validation['evidence_parallel']}")
        print(f"  [OK] 假设显式: {validation['assumptions_explicit']}")
        print(f"  [OK] 不确定性标注: {validation['uncertainty_marked']}")
        print(f"  [OK] 边界遵守: {validation['boundary_respected']}")

        if validation["errors"]:
            print(f"  [FAIL] 错误: {validation['errors']}")

    def _generate_report(self):
        """生成验收报告"""
        print("\n" + "=" * 80)
        print("验收报告")
        print("=" * 80)

        total = len(self.results)
        schema_valid = sum(1 for r in self.results if r["validation"]["schema_valid"])
        priority_match = sum(1 for r in self.results if r["validation"]["priority_match"])
        evidence_parallel = sum(1 for r in self.results if r["validation"]["evidence_parallel"])
        assumptions_explicit = sum(1 for r in self.results if r["validation"]["assumptions_explicit"])
        uncertainty_marked = sum(1 for r in self.results if r["validation"]["uncertainty_marked"])
        boundary_respected = sum(1 for r in self.results if r["validation"]["boundary_respected"])

        print(f"\n总案例数: {total}")
        print(f"\n验收检查项:")
        print(f"  Schema合法性: {schema_valid}/{total} ({schema_valid/total*100:.0f}%) - 目标: 100%")
        print(f"  优先级匹配: {priority_match}/{total} ({priority_match/total*100:.0f}%) - 目标: 80%")
        print(f"  证据并列: {evidence_parallel}/{total} ({evidence_parallel/total*100:.0f}%) - 目标: 100%")
        print(f"  假设显式化: {assumptions_explicit}/{total} ({assumptions_explicit/total*100:.0f}%) - 目标: 100%")
        print(f"  不确定性标注: {uncertainty_marked}/{total} ({uncertainty_marked/total*100:.0f}%) - 目标: 100%")
        print(f"  边界遵守: {boundary_respected}/{total} ({boundary_respected/total*100:.0f}%) - 目标: 100%")

        # 验收结论
        print(f"\n验收结论:")
        if (schema_valid == total and
            evidence_parallel == total and
            assumptions_explicit == total and
            uncertainty_marked == total and
            boundary_respected == total and
            priority_match >= total * 0.8):
            print("  [PASS] 可推进 - 通过所有必需检查项，可进入2.3联调")
        else:
            print("  [FAIL] 需返工 - 未通过关键检查项")
            if schema_valid < total:
                print(f"    - Schema合法性未达标")
            if evidence_parallel < total:
                print(f"    - 证据并列未达标")
            if assumptions_explicit < total:
                print(f"    - 假设显式化未达标")
            if uncertainty_marked < total:
                print(f"    - 不确定性标注未达标")
            if boundary_respected < total:
                print(f"    - 边界遵守未达标")
            if priority_match < total * 0.8:
                print(f"    - 优先级匹配率低于80%")


if __name__ == "__main__":
    runner = ValidationRunner()
    runner.run_all_cases()
