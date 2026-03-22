"""
Phase 2.2 -> 2.3 接口联调测试 (P1-2)

验证 OpportunityObject(Pydantic) -> ActionDesignRequest(dataclass) 全流程
关键差异:
  - 2.2 uncertainty_map: List[str]
  - 2.3 uncertainty_map: Dict[str, str]  <- 需要适配
运行方式: python integration_test_2.2_to_2.3.py
"""

import os
import sys
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# 加载 2.2 schemas
m22 = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))
OpportunityObject22 = m22.OpportunityObject

# 加载 2.3 模块
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OpportunityObject23, ActionDesignRequest
from action_designer import ActionDesigner


def adapt_opportunity(opp22: OpportunityObject22) -> OpportunityObject23:
    """
    适配器: 2.2 OpportunityObject(Pydantic) -> 2.3 OpportunityObject(dataclass)

    关键转换:
    - uncertainty_map: List[str] -> Dict[str, str]
      策略: 用索引作 key ("uncertainty_1", "uncertainty_2", ...)
    """
    uncertainty_dict = {
        f"uncertainty_{i+1}": item
        for i, item in enumerate(opp22.uncertainty_map)
    }
    return OpportunityObject23(
        opportunity_title=opp22.opportunity_title,
        opportunity_thesis=opp22.opportunity_thesis,
        supporting_evidence=opp22.supporting_evidence,
        counter_evidence=opp22.counter_evidence,
        key_assumptions=opp22.key_assumptions,
        uncertainty_map=uncertainty_dict,
        priority_level=opp22.priority_level,
    )


def run_case(name: str, opp22: OpportunityObject22, designer: ActionDesigner, expected_posture: str = None):
    print(f"\n{'='*60}")
    print(f"案例: {name}")
    print(f"{'='*60}")
    print(f"优先级: {opp22.priority_level}")
    print(f"关键假设数: {len(opp22.key_assumptions)}")
    print(f"不确定性数: {len(opp22.uncertainty_map)}")

    # 适配
    opp23 = adapt_opportunity(opp22)
    request = ActionDesignRequest(
        request_id=f"req_{name[:8]}",
        opportunity_object=opp23
    )

    # 执行
    result = designer.design_action(request)
    decision = result.action_decision

    print(f"\n行动姿态: {decision.decision_posture}")
    print(f"姿态原因: {decision.why_this_posture}")
    print(f"计划阶段数: {len(decision.phased_plan)}")
    print(f"顶级风险数: {len(decision.top_risks)}")
    print(f"开放问题数: {len(decision.open_questions)}")
    if decision.phased_plan:
        stage = decision.phased_plan[0]
        print(f"阶段1 Go/No-Go: {stage.go_no_go_criteria}")
        print(f"阶段1 退出条件: {stage.exit_conditions}")

    # 可拍板性检查
    checks = {
        "有行动姿态": bool(decision.decision_posture),
        "有姿态解释": bool(decision.why_this_posture),
        "有分阶段计划": len(decision.phased_plan) > 0,
        "有Go/No-Go": len(decision.phased_plan[0].go_no_go_criteria) > 0 if decision.phased_plan else False,
        "有退出条件": len(decision.phased_plan[0].exit_conditions) > 0 if decision.phased_plan else False,
        "有资源承诺逻辑": bool(decision.resource_commitment_logic),
        "有备选路径": bool(decision.fallback_path),
    }
    if expected_posture:
        checks[f"姿态符合预期({expected_posture})"] = decision.decision_posture == expected_posture

    all_pass = all(checks.values())
    print(f"\n可拍板性检查: {'PASS' if all_pass else 'FAIL'}")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")
    return all_pass


def main():
    print("\nPhase 2.2 -> 2.3 联调测试 (P1-2)")
    print("="*60)

    designer = ActionDesigner()

    # 案例1: deep_dive 级别 -> 预期 pilot
    case1 = OpportunityObject22(
        opportunity_id="opp_001",
        opportunity_title="AI NPC 对话系统商业化机会",
        opportunity_thesis="LLM 驱动的 NPC 对话系统将重构游戏叙事体验，形成新的竞争壁垒",
        related_signals=[
            {"signal_id": "sig_001", "signal_type": "technical", "intensity_score": 9},
            {"signal_id": "sig_002", "signal_type": "market", "intensity_score": 8},
            {"signal_id": "sig_003", "signal_type": "capital", "intensity_score": 8},
        ],
        supporting_evidence=["OpenAI 与 EA/Ubisoft 合作", "市场规模预计 50 亿美元", "A 轮融资超 2 亿"],
        counter_evidence=["玩家接受度未知", "内容审核成本高"],
        key_assumptions=["玩家愿意为 AI NPC 付费", "延迟可控制在 200ms 内"],
        uncertainty_map=["商业模式不确定", "监管政策不确定"],
        priority_level="deep_dive",
        next_validation_questions=["玩家调研结果如何？", "API 成本结构如何？"],
        judgment_version="v1.0-mvp",
        processing_time_ms=1200
    )

    # 案例2: research 级别，多假设 -> 预期 validate
    case2 = OpportunityObject22(
        opportunity_id="opp_002",
        opportunity_title="元宇宙虚拟会议平台",
        opportunity_thesis="VR 硬件普及后，虚拟会议将替代部分线下商务场景",
        related_signals=[
            {"signal_id": "sig_004", "signal_type": "market", "intensity_score": 6},
            {"signal_id": "sig_005", "signal_type": "technical", "intensity_score": 5},
        ],
        supporting_evidence=["Meta Quest 销量增长", "远程办公趋势持续"],
        counter_evidence=["VR 硬件渗透率仍低", "晕动症问题未解决", "企业采购意愿不明"],
        key_assumptions=["VR 设备价格降至 500 元以下", "5G 延迟满足实时互动", "企业愿意改变会议习惯", "内容生态足够丰富", "监管允许跨境虚拟会议"],
        uncertainty_map=["硬件普及时间线不确定", "用户习惯改变速度不确定", "竞争格局不确定"],
        priority_level="research",
        next_validation_questions=["VR 设备渗透率预测？"],
        judgment_version="v1.0-mvp",
        processing_time_ms=900
    )

    # 案例3: watch 级别 -> 预期 watch
    case3 = OpportunityObject22(
        opportunity_id="opp_003",
        opportunity_title="量子计算游戏渲染加速",
        opportunity_thesis="量子计算未来可能大幅提升游戏物理模拟和渲染效率",
        related_signals=[
            {"signal_id": "sig_006", "signal_type": "technical", "intensity_score": 3},
        ],
        supporting_evidence=["IBM 量子计算机研究进展"],
        counter_evidence=["技术成熟度极低", "商业化时间线超过 10 年", "当前无实际游戏应用"],
        key_assumptions=["量子纠错问题可解决", "成本可降至商业可行水平"],
        uncertainty_map=["技术路线不确定", "时间窗口极度不确定"],
        priority_level="watch",
        next_validation_questions=["量子计算商业化时间线？"],
        judgment_version="v1.0-mvp",
        processing_time_ms=600
    )

    results = [
        run_case("AI NPC deep_dive", case1, designer, expected_posture="pilot"),
        run_case("元宇宙 research + 多假设", case2, designer, expected_posture="validate"),
        run_case("量子计算 watch", case3, designer, expected_posture="watch"),
    ]

    print(f"\n{'='*60}")
    print("联调总结 (P1-2)")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r)
    print(f"通过: {passed}/{len(results)}")
    if passed == len(results):
        print("P1-2 联调: PASS -- 可进入 P1-3（2.3->2.5 联调）")
    else:
        print("P1-2 联调: FAIL -- 需修复后重新验证")
        print("\n注意: uncertainty_map 适配策略（List->Dict）已在 adapt_opportunity() 中处理")
        print("如有 FAIL 项，检查 priority_level 到 posture 的映射是否符合预期")


if __name__ == "__main__":
    main()