"""Phase 2.3 综合验证脚本"""
import sys
sys.path.insert(0, '../src')

from models import OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner

def validate_case(case_name, opportunity):
    """验证单个案例"""
    print("\n" + "=" * 70)
    print(f"案例: {case_name}")
    print("=" * 70)

    request = ActionDesignRequest(
        request_id=f"val_{case_name}",
        opportunity_object=opportunity
    )

    designer = ActionDesigner()
    result = designer.design_action(request)
    decision = result.action_decision

    # 输出核心信息
    print(f"\n机会: {decision.opportunity_title}")
    print(f"行动姿态: {decision.decision_posture}")
    print(f"原因: {decision.why_this_posture}")

    print(f"\n分阶段计划 ({len(decision.phased_plan)}个阶段):")
    for i, stage in enumerate(decision.phased_plan, 1):
        print(f"  阶段{i}: {stage.stage}")
        print(f"    目标: {stage.objective}")
        print(f"    资源: {stage.resources.people}, {stage.resources.budget}")
        print(f"    Go标准: {stage.go_no_go_criteria[0] if stage.go_no_go_criteria else 'N/A'}")
        print(f"    退出条件: {stage.exit_conditions[0] if stage.exit_conditions else 'N/A'}")

    print(f"\n资源承诺逻辑:")
    print(f"  {decision.resource_commitment_logic}")

    print(f"\n顶级风险 ({len(decision.top_risks)}个):")
    for risk in decision.top_risks:
        print(f"  - {risk.risk}")

    print(f"\n备选路径: {decision.fallback_path}")

    # 可拍板性检查
    print(f"\nYES 可拍板性检查:")
    print(f"  - 行动姿态明确: {'YES' if decision.decision_posture else 'NO'}")
    print(f"  - 有分阶段计划: {'YES' if decision.phased_plan else 'NO'}")
    print(f"  - 有Go/No-Go门槛: {'YES' if any(s.go_no_go_criteria for s in decision.phased_plan) else 'NO'}")
    print(f"  - 有退出条件: {'YES' if any(s.exit_conditions for s in decision.phased_plan) else 'NO'}")

    return result

# 案例1: 高优先级AI技术机会
case1 = OpportunityObject(
    opportunity_title="AI代理在企业客服自动化中的应用",
    opportunity_thesis="AI代理技术成熟，可显著降低企业客服成本",
    supporting_evidence=[
        "大模型对话能力达到商用水平",
        "多家企业试点效果良好",
        "客服成本压力持续增大"
    ],
    counter_evidence=[
        "复杂问题处理能力仍有限",
        "企业担心用户体验下降"
    ],
    key_assumptions=[
        "AI可处理70%常见问题",
        "用户接受AI客服",
        "6个月内可完成部署"
    ],
    uncertainty_map={
        "技术成熟度": "低不确定性",
        "市场接受度": "中等不确定性"
    },
    priority_level="high"
)

# 案例2: 中优先级但假设多的机会
case2 = OpportunityObject(
    opportunity_title="元宇宙虚拟会议平台",
    opportunity_thesis="远程办公常态化，虚拟会议体验可提升",
    supporting_evidence=[
        "远程办公需求持续",
        "VR设备成本下降",
        "部分企业开始尝试"
    ],
    counter_evidence=[
        "VR设备普及率低",
        "用户使用习惯难改变",
        "技术体验仍不成熟",
        "竞争激烈"
    ],
    key_assumptions=[
        "企业愿意采购VR设备",
        "员工愿意使用VR开会",
        "技术体验足够好",
        "成本可控",
        "能形成差异化优势"
    ],
    uncertainty_map={
        "市场需求": "高不确定性",
        "技术可行性": "中等不确定性",
        "用户接受度": "高不确定性",
        "竞争格局": "高不确定性"
    },
    priority_level="medium"
)

# 案例3: 低优先级早期观察机会
case3 = OpportunityObject(
    opportunity_title="量子计算在金融风控中的应用",
    opportunity_thesis="量子计算可能革新复杂风控模型计算",
    supporting_evidence=[
        "量子计算理论突破",
        "部分研究机构开始探索"
    ],
    counter_evidence=[
        "技术远未成熟",
        "商用时间不确定",
        "成本极高",
        "应用场景不明确"
    ],
    key_assumptions=[
        "量子计算5年内可商用",
        "金融机构愿意尝试"
    ],
    uncertainty_map={
        "技术成熟度": "极高不确定性",
        "商用时间": "极高不确定性",
        "应用价值": "高不确定性"
    },
    priority_level="low"
)

# 执行验证
print("\n" + "=" * 70)
print("Phase 2.3 综合验证")
print("=" * 70)

result1 = validate_case("高优先级AI客服", case1)
result2 = validate_case("中优先级元宇宙会议", case2)
result3 = validate_case("低优先级量子计算", case3)

print("\n" + "=" * 70)
print("验证总结")
print("=" * 70)
print(f"案例1姿态: {result1.action_decision.decision_posture} (预期: pilot/validate)")
print(f"案例2姿态: {result2.action_decision.decision_posture} (预期: validate)")
print(f"案例3姿态: {result3.action_decision.decision_posture} (预期: watch)")
print("\n所有案例均成功生成行动决策对象 YES")
