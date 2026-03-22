"""
Phase 2.3 -> 2.5 接口联调测试 (P1-3)

验证 ActionDesignResult -> upstream_outputs[phase2_3] -> OutputChecker 全流程
运行方式: python integration_test_2.3_to_2.5.py
"""

import os
import sys
import importlib.util
from dataclasses import asdict

BASE = os.path.dirname(os.path.abspath(__file__))

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# 加载 2.3
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OpportunityObject23, ActionDesignRequest
from action_designer import ActionDesigner

# 加载 2.5
sys.path.insert(0, os.path.join(BASE, 'phase2.5_implementation'))
from schemas.system_retrospective_schema import CheckStatus
from core.output_checker import OutputChecker


def action_result_to_upstream_dict(result, decoded_signals=None, opportunity_dict=None) -> dict:
    """
    适配器: ActionDesignResult -> upstream_outputs["phase2_3"]
    将 2.3 dataclass 输出转为 2.5 OutputChecker 期望的 Dict 格式
    """
    decision = result.action_decision
    phased_plan = []
    for stage in decision.phased_plan:
        phased_plan.append({
            "stage": stage.stage,
            "objective": stage.objective,
            "go_no_go_criteria": stage.go_no_go_criteria,
            "exit_conditions": stage.exit_conditions,
            "resources": asdict(stage.resources),
        })

    upstream_outputs = {
        "phase2_1": decoded_signals or {
            "signals": [{"signal_id": "sig_001", "signal_type": "technical", "summary": "测试信号"}],
            "signal_schema_validation": "passed",
            "benchmark_summary": "联调测试信号"
        },
        "phase2_2": opportunity_dict or {
            "opportunity_title": decision.opportunity_title,
            "opportunity_thesis": "联调测试论点",
            "supporting_evidence": ["支撑证据1"],
            "counter_evidence": [],
            "priority_level": "deep_dive",
            "uncertainty_map": {"risk_1": "medium"}
        },
        "phase2_3": {
            "decision_posture": decision.decision_posture,
            "why_this_posture": decision.why_this_posture,
            "phased_plan": phased_plan,
            "go_no_go_criteria": {
                stage.stage: stage.go_no_go_criteria
                for stage in decision.phased_plan
            },
            "resource_commitment_logic": decision.resource_commitment_logic,
            "fallback_path": decision.fallback_path,
            "top_risks": [asdict(r) for r in decision.top_risks],
            "open_questions": decision.open_questions,
        }
    }
    return upstream_outputs


def run_case(name: str, opp: OpportunityObject23, designer: ActionDesigner, checker: OutputChecker):
    print(f"\n{'='*60}")
    print(f"案例: {name}")
    print(f"{'='*60}")

    # 2.3 设计行动
    request = ActionDesignRequest(request_id=f"req_{name[:6]}", opportunity_object=opp)
    result = designer.design_action(request)
    decision = result.action_decision
    print(f"2.3 输出姿态: {decision.decision_posture}")
    print(f"2.3 计划阶段数: {len(decision.phased_plan)}")

    # 转换为 2.5 输入格式
    upstream_outputs = action_result_to_upstream_dict(result)
    workflow_run_record = {
        "run_id": f"run_{name[:6]}",
        "start_time": "2026-03-22T00:00:00Z",
        "end_time": "2026-03-22T00:00:30Z",
        "processing_time_ms": result.processing_time_ms,
        "errors": [],
        "status": "completed"
    }

    # 2.5 输出检查
    checks = checker.check_all(workflow_run_record, upstream_outputs)

    print(f"\n2.5 OutputChecker 结果 ({len(checks)} 项检查):")
    all_pass = True
    for check in checks:
        status_str = "PASS" if check.status == CheckStatus.PASS else ("WARN" if check.status == CheckStatus.WARNING else "FAIL")
        print(f"  [{status_str}] {check.check_type.value}: {check.details[:80]}")
        if check.status == CheckStatus.FAIL:
            all_pass = False

    # 联调验收标准：无 FAIL（WARNING 可接受）
    print(f"\n联调检查: {'PASS' if all_pass else 'FAIL'}")
    return all_pass


def main():
    print("\nPhase 2.3 -> 2.5 联调测试 (P1-3)")
    print("="*60)

    designer = ActionDesigner()
    checker = OutputChecker()

    # 案例1: pilot 姿态（正常完整输出）
    case1 = OpportunityObject23(
        opportunity_title="AI NPC 对话系统",
        opportunity_thesis="LLM 驱动 NPC 将重构游戏叙事体验",
        supporting_evidence=["OpenAI 与大厂合作", "市场规模 50 亿"],
        counter_evidence=["玩家接受度未知"],
        key_assumptions=["玩家愿意付费", "延迟可控"],
        uncertainty_map={"business_model": "不确定", "regulation": "不确定"},
        priority_level="high"
    )

    # 案例2: watch 姿态（信号弱）
    case2 = OpportunityObject23(
        opportunity_title="量子计算渲染加速",
        opportunity_thesis="量子计算未来可能提升游戏渲染效率",
        supporting_evidence=["IBM 量子研究进展"],
        counter_evidence=["商业化超 10 年", "成本极高", "无实际应用"],
        key_assumptions=["量子纠错可解决"],
        uncertainty_map={"timeline": "极度不确定"},
        priority_level="low"
    )

    results = [
        run_case("AI NPC pilot 姿态", case1, designer, checker),
        run_case("量子计算 watch 姿态", case2, designer, checker),
    ]

    print(f"\n{'='*60}")
    print("联调总结 (P1-3)")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r)
    print(f"通过: {passed}/{len(results)}")
    if passed == len(results):
        print("P1-3 联调: PASS -- 可进入 P1-4（端到端链路联调）")
    else:
        print("P1-3 联调: FAIL -- 检查 OutputChecker 对 phase2_3 字段的期望")


if __name__ == "__main__":
    main()