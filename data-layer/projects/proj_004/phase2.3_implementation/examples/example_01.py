"""Phase 2.3 示例：AI代理技术机会"""
import sys
sys.path.insert(0, '../src')

from models import OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner

# 构造示例机会对象
opportunity = OpportunityObject(
    opportunity_title="AI代理技术在企业自动化中的应用",
    opportunity_thesis="AI代理技术成熟度提升，可用于企业流程自动化",
    supporting_evidence=[
        "GPT-4等大模型能力显著提升",
        "多家企业开始试点AI代理",
        "技术成本持续下降"
    ],
    counter_evidence=[
        "企业对AI可靠性仍有顾虑",
        "集成现有系统存在技术挑战"
    ],
    key_assumptions=[
        "企业愿意为AI代理付费",
        "技术方案可在3个月内实现",
        "用户接受度达到预期"
    ],
    uncertainty_map={
        "市场需求": "中等不确定性",
        "技术可行性": "低不确定性",
        "竞争格局": "高不确定性"
    },
    priority_level="high"
)

# 创建请求
request = ActionDesignRequest(
    request_id="req_001",
    opportunity_object=opportunity
)

# 执行行动设计
designer = ActionDesigner()
result = designer.design_action(request)

# 输出结果
print("=" * 60)
print(f"机会标题: {result.action_decision.opportunity_title}")
print(f"行动姿态: {result.action_decision.decision_posture}")
print(f"姿态解释: {result.action_decision.why_this_posture}")
print("\n分阶段计划:")
for i, stage in enumerate(result.action_decision.phased_plan, 1):
    print(f"\n阶段{i}: {stage.stage}")
    print(f"  目标: {stage.objective}")
    print(f"  资源: {stage.resources.people}, {stage.resources.budget}, {stage.resources.time}")
    print(f"  Go/No-Go: {', '.join(stage.go_no_go_criteria)}")

print(f"\n资源承诺逻辑:\n{result.action_decision.resource_commitment_logic}")
print(f"\n备选路径: {result.action_decision.fallback_path}")
print("=" * 60)
