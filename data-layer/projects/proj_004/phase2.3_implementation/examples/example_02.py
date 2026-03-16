"""Phase 2.3 示例：低优先级观察机会"""
import sys
sys.path.insert(0, '../src')

from models import OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner

# 构造低优先级机会对象
opportunity = OpportunityObject(
    opportunity_title="区块链在供应链中的潜在应用",
    opportunity_thesis="区块链技术可能改善供应链透明度",
    supporting_evidence=[
        "部分行业开始探索区块链",
        "技术标准逐步成熟"
    ],
    counter_evidence=[
        "实施成本高",
        "企业接受度低",
        "技术成熟度仍需观察"
    ],
    key_assumptions=[
        "企业愿意投入区块链改造",
        "技术方案能解决实际问题"
    ],
    uncertainty_map={
        "市场需求": "高不确定性",
        "技术成熟度": "中等不确定性"
    },
    priority_level="low"
)

request = ActionDesignRequest(
    request_id="req_002",
    opportunity_object=opportunity
)

designer = ActionDesigner()
result = designer.design_action(request)

print("=" * 60)
print(f"Opportunity: {result.action_decision.opportunity_title}")
print(f"Posture: {result.action_decision.decision_posture}")
print(f"Why: {result.action_decision.why_this_posture}")
print(f"\nPhases: {len(result.action_decision.phased_plan)}")
for stage in result.action_decision.phased_plan:
    print(f"  - {stage.stage}: {stage.objective}")
print(f"\nTop Risks: {len(result.action_decision.top_risks)}")
for risk in result.action_decision.top_risks:
    print(f"  - {risk.risk}")
print("=" * 60)
