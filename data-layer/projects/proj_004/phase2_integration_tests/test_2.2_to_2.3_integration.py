"""
Phase 2.2 -> 2.3 联调测试

测试目标：
1. 验证 2.2 输出的 OpportunityObject 可被 2.3 正确消费
2. 验证完整链路（信号 -> 机会判断 -> 行动设计）
3. 识别接口兼容性问题
"""

import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../phase2.2_implementation'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../phase2.3_implementation/src'))

from schemas import OpportunityJudgmentRequest
from judgment_engine import JudgmentEngine
from models import OpportunityObject as Phase23OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner


def convert_2_2_to_2_3_opportunity(opp_2_2):
    """
    将 2.2 的 OpportunityObject 转换为 2.3 期望的格式

    2.2 输出 12 字段，2.3 只需要 7 个核心字段
    """
    return Phase23OpportunityObject(
        opportunity_title=opp_2_2.opportunity_title,
        opportunity_thesis=opp_2_2.opportunity_thesis,
        supporting_evidence=opp_2_2.supporting_evidence,
        counter_evidence=opp_2_2.counter_evidence,
        key_assumptions=opp_2_2.key_assumptions,
        uncertainty_map={
            item.split(":")[0].strip(): item.split(":", 1)[1].strip() if ":" in item else item
            for item in opp_2_2.uncertainty_map
        },
        priority_level=opp_2_2.priority_level
    )


def test_case_1_high_priority():
    """测试案例1：高优先级机会（deep_dive）"""
    print("=" * 80)
    print("测试案例1：高优先级机会 - AI 代理在企业客服自动化")
    print("=" * 80)

    # Step 1: 构造 2.1 信号输入（模拟）
    request_2_2 = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_integration_001",
            "signals": [
                {
                    "signal_id": "sig_tech_ai_agent",
                    "signal_type": "technical",
                    "signal_summary": "AI 代理技术在客服场景成熟度提升，GPT-4 级别模型可处理 80% 常见问题",
                    "intensity": 8,
                    "confidence": 8,
                    "source": "技术评测报告"
                },
                {
                    "signal_id": "sig_market_demand",
                    "signal_type": "market",
                    "signal_summary": "企业客服成本压力大，市场对自动化解决方案需求强烈",
                    "intensity": 7,
                    "confidence": 8,
                    "source": "市场调研"
                },
                {
                    "signal_id": "sig_capital_investment",
                    "signal_type": "capital",
                    "signal_summary": "多家 AI 客服公司获得融资，红杉、IDG 等头部机构入场",
                    "intensity": 7,
                    "confidence": 9,
                    "source": "融资公告"
                },
                {
                    "signal_id": "sig_team_talent",
                    "signal_type": "team",
                    "signal_summary": "AI 对话系统人才市场活跃，薪资溢价明显",
                    "intensity": 6,
                    "confidence": 7,
                    "source": "招聘数据"
                }
            ]
        }
    )

    # Step 2: 调用 2.2 机会判断引擎
    print("\n[Phase 2.2] 执行机会判断...")
    engine_2_2 = JudgmentEngine()
    result_2_2 = engine_2_2.judge(request_2_2)

    if result_2_2.status != "success":
        print(f"[FAIL] 2.2 判断失败: {result_2_2.status}")
        if result_2_2.error:
            print(f"   错误: {result_2_2.error.message}")
        return False

    opp_2_2 = result_2_2.opportunity
    print(f"[OK] 2.2 判断成功")
    print(f"   优先级: {opp_2_2.priority_level}")
    print(f"   论点: {opp_2_2.opportunity_thesis}")
    print(f"   支持证据: {len(opp_2_2.supporting_evidence)} 条")
    print(f"   反对证据: {len(opp_2_2.counter_evidence)} 条")
    print(f"   关键假设: {len(opp_2_2.key_assumptions)} 条")
    print(f"   处理耗时: {opp_2_2.processing_time_ms}ms")

    # Step 3: 转换为 2.3 格式
    print("\n[接口转换] 2.2 -> 2.3 格式转换...")
    opp_2_3 = convert_2_2_to_2_3_opportunity(opp_2_2)
    print(f"[OK] 转换成功")
    print(f"   保留字段: opportunity_title, opportunity_thesis, supporting_evidence, counter_evidence, key_assumptions, uncertainty_map, priority_level")

    # Step 4: 调用 2.3 行动设计器
    print("\n[Phase 2.3] 执行行动设计...")
    request_2_3 = ActionDesignRequest(
        request_id="req_integration_001",
        opportunity_object=opp_2_3
    )

    designer_2_3 = ActionDesigner()
    result_2_3 = designer_2_3.design_action(request_2_3)

    action_obj = result_2_3.action_decision
    print(f"[OK] 2.3 设计成功")
    print(f"   行动姿态: {action_obj.decision_posture}")
    print(f"   姿态理由: {action_obj.why_this_posture}")
    print(f"   分阶段计划: {len(action_obj.phased_plan)} 个阶段")
    print(f"   顶级风险: {len(action_obj.top_risks)} 个")
    print(f"   处理耗时: {result_2_3.processing_time_ms}ms")

    # Step 5: 验证输出完整性
    print("\n[验证] 检查输出完整性...")
    checks = {
        "姿态判断": action_obj.decision_posture in ["watch", "validate", "pilot", "escalate", "hold", "stop"],
        "姿态理由": len(action_obj.why_this_posture) > 0,
        "分阶段计划": len(action_obj.phased_plan) > 0,
        "Go/No-Go": all(len(stage.go_no_go_criteria) > 0 for stage in action_obj.phased_plan),
        "退出条件": all(len(stage.exit_conditions) > 0 for stage in action_obj.phased_plan),
        "资源承诺逻辑": len(action_obj.resource_commitment_logic) > 0,
        "备选路径": len(action_obj.fallback_path) > 0,
        "开放问题": len(action_obj.open_questions) > 0
    }

    all_passed = all(checks.values())
    for check_name, passed in checks.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"   {status} {check_name}")

    print("\n" + "=" * 80)
    print(f"测试案例1: {'[OK] 通过' if all_passed else '[FAIL] 失败'}")
    print("=" * 80)

    return all_passed


def test_case_2_medium_priority():
    """测试案例2：中优先级机会（research）"""
    print("\n" + "=" * 80)
    print("测试案例2：中优先级机会 - 量子计算在金融风控")
    print("=" * 80)

    # Step 1: 构造 2.2 输入
    request_2_2 = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_integration_002",
            "signals": [
                {
                    "signal_id": "sig_tech_quantum",
                    "signal_type": "technical",
                    "signal_summary": "量子计算在优化问题上展现潜力，但商业化尚早",
                    "intensity": 6,
                    "confidence": 6,
                    "source": "学术论文"
                },
                {
                    "signal_id": "sig_market_fintech",
                    "signal_type": "market",
                    "signal_summary": "金融机构对风控技术升级有需求，但预算有限",
                    "intensity": 5,
                    "confidence": 7,
                    "source": "行业报告"
                }
            ]
        }
    )

    # Step 2-4: 执行完整链路
    print("\n[Phase 2.2] 执行机会判断...")
    engine_2_2 = JudgmentEngine()
    result_2_2 = engine_2_2.judge(request_2_2)

    if result_2_2.status != "success":
        print(f"[FAIL] 2.2 判断失败")
        return False

    opp_2_2 = result_2_2.opportunity
    print(f"[OK] 2.2 判断成功 - 优先级: {opp_2_2.priority_level}")

    print("\n[接口转换] 2.2 -> 2.3...")
    opp_2_3 = convert_2_2_to_2_3_opportunity(opp_2_2)
    print(f"[OK] 转换成功")

    print("\n[Phase 2.3] 执行行动设计...")
    request_2_3 = ActionDesignRequest(
        request_id="req_integration_002",
        opportunity_object=opp_2_3
    )

    designer_2_3 = ActionDesigner()
    result_2_3 = designer_2_3.design_action(request_2_3)

    action_obj = result_2_3.action_decision
    print(f"[OK] 2.3 设计成功 - 姿态: {action_obj.decision_posture}")

    # 验证
    all_passed = (
        action_obj.decision_posture in ["watch", "validate", "pilot"] and
        len(action_obj.phased_plan) > 0 and
        len(action_obj.resource_commitment_logic) > 0
    )

    print("\n" + "=" * 80)
    print(f"测试案例2: {'[OK] 通过' if all_passed else '[FAIL] 失败'}")
    print("=" * 80)

    return all_passed


def test_case_3_low_priority():
    """测试案例3：低优先级机会（watch）"""
    print("\n" + "=" * 80)
    print("测试案例3：低优先级机会 - 单一技术信号")
    print("=" * 80)

    request_2_2 = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_integration_003",
            "signals": [
                {
                    "signal_id": "sig_tech_single",
                    "signal_type": "technical",
                    "signal_summary": "某公司发布新技术专利",
                    "intensity": 5,
                    "confidence": 6,
                    "source": "专利数据库"
                }
            ]
        }
    )

    print("\n[Phase 2.2] 执行机会判断...")
    engine_2_2 = JudgmentEngine()
    result_2_2 = engine_2_2.judge(request_2_2)

    if result_2_2.status != "success":
        print(f"[FAIL] 2.2 判断失败")
        return False

    opp_2_2 = result_2_2.opportunity
    print(f"[OK] 2.2 判断成功 - 优先级: {opp_2_2.priority_level}")

    print("\n[接口转换] 2.2 -> 2.3...")
    opp_2_3 = convert_2_2_to_2_3_opportunity(opp_2_2)

    print("\n[Phase 2.3] 执行行动设计...")
    request_2_3 = ActionDesignRequest(
        request_id="req_integration_003",
        opportunity_object=opp_2_3
    )

    designer_2_3 = ActionDesigner()
    result_2_3 = designer_2_3.design_action(request_2_3)

    action_obj = result_2_3.action_decision
    print(f"[OK] 2.3 设计成功 - 姿态: {action_obj.decision_posture}")

    # 验证 watch 姿态应该是轻量级的
    all_passed = (
        action_obj.decision_posture == "watch" and
        len(action_obj.phased_plan) == 1  # watch 只需要一个阶段
    )

    print("\n" + "=" * 80)
    print(f"测试案例3: {'[OK] 通过' if all_passed else '[FAIL] 失败'}")
    print("=" * 80)

    return all_passed


def main():
    """运行所有联调测试"""
    print("\n" + "=" * 80)
    print("Phase 2.2 -> 2.3 联调测试")
    print("=" * 80)
    print(f"测试目标：验证 2.2 机会判断 -> 2.3 行动设计 完整链路")
    print("=" * 80)

    results = []

    # 运行测试案例
    results.append(("案例1: 高优先级机会", test_case_1_high_priority()))
    results.append(("案例2: 中优先级机会", test_case_2_medium_priority()))
    results.append(("案例3: 低优先级机会", test_case_3_low_priority()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("联调测试汇总")
    print("=" * 80)

    for test_name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print("\n" + "=" * 80)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("[OK] 联调测试全部通过 - 2.2 -> 2.3 链路验证成功")
    else:
        print("[FAIL] 部分测试失败 - 需要修复接口兼容性问题")

    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
