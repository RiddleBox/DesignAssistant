"""Phase 2.3 综合验证脚本

案例设计原则：
- priority_level 对齐 2.2 新枚举：escalate / deep_dive / research / watch
- 每个案例提供 why_now 和 next_validation_questions（2.2 新字段）
- 场景贴近游戏行业，覆盖 4 个优先级级别
- 案例4 模拟多机会场景：2 个机会对象分别跑 2.3，验证多机会分发路径
"""
import sys
sys.path.insert(0, '../src')

from models import OpportunityObject, ActionDesignRequest
from action_designer import ActionDesigner

PRIORITY_LEVELS = ["escalate", "deep_dive", "research", "watch"]


def validate_case(case_name, opportunity, expected_posture_hint=None):
    """验证单个案例，输出结构化结果"""
    print("\n" + "=" * 70)
    print(f"案例: {case_name}")
    print(f"优先级: {opportunity.priority_level} | why_now: {opportunity.why_now or '（无）'}")
    print("=" * 70)

    request = ActionDesignRequest(
        request_id=f"val_{case_name}",
        opportunity_object=opportunity
    )

    designer = ActionDesigner()
    result = designer.design_action(request)
    decision = result.action_decision

    print(f"\n行动姿态: {decision.decision_posture}")
    if expected_posture_hint:
        print(f"预期参考: {expected_posture_hint}")
    print(f"原因: {decision.why_this_posture}")

    print(f"\n分阶段计划（{len(decision.phased_plan)} 个阶段）:")
    for i, stage in enumerate(decision.phased_plan, 1):
        print(f"  阶段{i}「{stage.stage}」")
        print(f"    目标: {stage.objective}")
        assumptions = stage.key_assumptions_to_test or []
        print(f"    验证假设: {assumptions[0] if assumptions else 'N/A'}")
        print(f"    资源: {stage.resources.people} | {stage.resources.budget} | {stage.resources.time}")
        criteria = stage.go_no_go_criteria or []
        exits = stage.exit_conditions or []
        print(f"    Go标准: {criteria[0] if criteria else 'N/A'}")
        print(f"    退出条件: {exits[0] if exits else 'N/A'}")

    if hasattr(decision, 'debate_summary') and decision.debate_summary:
        ds = decision.debate_summary
        print(f"\n三方辩论摘要:")
        print(f"  鹰派: {getattr(ds, 'hawk_stance', '') or ds.get('hawk_stance','') if isinstance(ds, dict) else getattr(ds,'hawk_stance','')}")
        print(f"  鸽派: {getattr(ds, 'dove_stance', '') or ds.get('dove_stance','') if isinstance(ds, dict) else getattr(ds,'dove_stance','')}")
        print(f"  仲裁: {getattr(ds, 'resolution', '') or ds.get('resolution','') if isinstance(ds, dict) else getattr(ds,'resolution','')}")

    print(f"\n资源承诺逻辑: {decision.resource_commitment_logic}")
    print(f"备选路径: {decision.fallback_path}")

    # 结构完整性检查
    checks = {
        "行动姿态明确": decision.decision_posture in {"watch", "validate", "pilot", "escalate", "hold", "stop"},
        "有分阶段计划": len(decision.phased_plan) > 0,
        "有Go/No-Go门槛": any(s.go_no_go_criteria for s in decision.phased_plan),
        "有退出条件":    any(s.exit_conditions for s in decision.phased_plan),
        "资源承诺逻辑存在": bool(decision.resource_commitment_logic),
        "备选路径存在":  bool(decision.fallback_path),
        "风险已识别":    len(decision.top_risks) > 0,
    }
    all_pass = all(checks.values())
    print(f"\n结构检查 ({'PASS' if all_pass else 'FAIL'}):")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")

    return result, all_pass


# ─────────────────────────────────────────────
# 案例1：escalate 级 — 游戏 AI NPC 赛道爆发窗口
# ─────────────────────────────────────────────
case1 = OpportunityObject(
    opportunity_title="生成式 AI 驱动游戏 NPC 商业化窗口",
    opportunity_thesis="GPT-4 级模型深度集成主流引擎，NPC 对话质量突破商用门槛，多家头部游戏厂商已开始采购，资本同步跟进，赛道进入快速商业化期",
    supporting_evidence=[
        "GPT-4 已规模化集成至 UE5/Unity NPC 对话系统",
        "腾讯、网易等头部厂商已立项 AI NPC 产品线",
        "本季度 AI 游戏初创公司合计 A 轮融资超 2 亿美元",
    ],
    counter_evidence=[
        "推理成本仍偏高，实时对话延迟未完全解决",
        "玩家对 AI NPC 的沉浸感接受度尚待大规模验证",
    ],
    key_assumptions=[
        "推理成本在 6 个月内下降至可接受水平",
        "头部厂商采购意愿可转化为稳定合同",
    ],
    uncertainty_map={
        "推理成本下降速度": "中等不确定性",
        "竞争格局集中速度": "高不确定性",
    },
    priority_level="escalate",
    why_now="头部厂商采购窗口期约 3 个月，GPU 新系列刚发布推理成本正在快速下降，竞争方尚未完成产品化",
    next_validation_questions=[
        "当前团队是否具备 UE5/Unity 插件交付能力？",
        "头部厂商的采购决策周期是多久？是否来得及在窗口期内签约？",
    ],
    warnings=["两条来源信号均为新闻报道，非官方公告，存在信息解读偏差风险"],
)

# ─────────────────────────────────────────────
# 案例2：deep_dive 级 — AI 游戏测试自动化
# ─────────────────────────────────────────────
case2 = OpportunityObject(
    opportunity_title="AI 驱动游戏自动化测试平台机会",
    opportunity_thesis="大模型具备游戏场景理解和路径探索能力，可大幅压缩 QA 人力成本，多家厂商已开始内部试点",
    supporting_evidence=[
        "基于 LLM 的游戏 Bug 自动发现工具已有内测版本",
        "头部厂商 QA 团队规模缩减信号明显",
        "AI 测试工具链投资同比增长 150%",
    ],
    counter_evidence=[
        "游戏类型差异大，通用化工具覆盖率有限",
        "厂商数据安全顾虑可能阻碍外部服务采购",
    ],
    key_assumptions=[
        "工具可覆盖至少 60% 的常规回归测试场景",
        "厂商愿意接受外部 SaaS 方案而非自建",
    ],
    uncertainty_map={
        "通用化覆盖率": "中等不确定性",
        "厂商自建意愿": "高不确定性",
    },
    priority_level="deep_dive",
    why_now="QA 成本压力在 2026 年集中爆发，多家厂商裁员后留下真空期，是切入时机",
    next_validation_questions=[
        "目标厂商的 QA 预算规模和外采意愿如何？",
        "现有工具在主流游戏类型（RPG/射击/休闲）的覆盖率是多少？",
    ],
)

# ─────────────────────────────────────────────
# 案例3：research 级 — AI 生成游戏关卡内容
# ─────────────────────────────────────────────
case3 = OpportunityObject(
    opportunity_title="AI 辅助生成游戏关卡与叙事内容",
    opportunity_thesis="生成式 AI 可显著提升关卡设计和剧情创作效率，降低中小厂商的内容生产成本，已有早期工具出现",
    supporting_evidence=[
        "Midjourney/DALL-E 在美术资产生成中已有实际应用",
        "多家中小厂商反馈内容生产是核心瓶颈",
    ],
    counter_evidence=[
        "关卡设计质量评估标准不统一，AI 输出难以自动验收",
        "创作者对 AI 替代的抵触情绪明显",
        "现有工具更多是辅助而非替代，效率提升有限",
    ],
    key_assumptions=[
        "中小厂商愿意为内容工具付费",
        "AI 生成质量达到设计师可接受的基线",
    ],
    uncertainty_map={
        "质量基线定义": "高不确定性",
        "付费意愿": "中等不确定性",
        "创作者接受度": "高不确定性",
    },
    priority_level="research",
    why_now=None,
    next_validation_questions=[
        "目标用户（中小厂商设计师）对 AI 辅助工具的实际付费意愿调研结果如何？",
    ],
)

# ─────────────────────────────────────────────
# 案例4a/4b：多机会场景 — 两个不同方向的 deep_dive 机会
# 模拟 2.2 产出 2 个机会 → 调用方逐一送 2.3 处理
# ─────────────────────────────────────────────
case4a = OpportunityObject(
    opportunity_title="游戏 AI 推理芯片需求爆发（硬件侧）",
    opportunity_thesis="生成式 AI NPC 普及将大幅拉动端侧推理芯片需求，GPU/NPU 厂商正在定向布局游戏场景",
    supporting_evidence=[
        "英伟达 RTX50 系列专项宣传游戏 AI 推理性能",
        "Sega 大规模游戏 AI 研发投入，Sega 减值可能预示行业洗牌",
    ],
    counter_evidence=[
        "硬件采购周期长，短期需求转化慢",
        "云端推理可能部分替代端侧需求",
    ],
    key_assumptions=[
        "端侧推理成为主流部署方式而非云端",
        "游戏厂商采购节奏与芯片发布节奏匹配",
    ],
    uncertainty_map={
        "端云分工格局": "高不确定性",
        "采购转化速度": "中等不确定性",
    },
    priority_level="deep_dive",
    why_now="RTX50 系列刚发布，窗口期约 6 个月，是切入时机",
    next_validation_questions=[
        "端侧 vs 云端推理的经济性拐点何时到来？",
    ],
)

case4b = OpportunityObject(
    opportunity_title="游戏 AI 推理云服务需求（云端侧）",
    opportunity_thesis="中小游戏厂商无力自建端侧推理基础设施，云端 AI 推理服务将是更低门槛的入口",
    supporting_evidence=[
        "中小厂商 GPU 采购成本是主要障碍",
        "云厂商已开始推出游戏 AI 推理 API 套餐",
    ],
    counter_evidence=[
        "实时对话场景对延迟极敏感，云端有天然劣势",
        "大厂倾向自建，云端市场可能只剩中小厂商",
    ],
    key_assumptions=[
        "中小厂商云端延迟容忍度足够高",
        "云厂商定价可覆盖中小厂商预算",
    ],
    uncertainty_map={
        "延迟容忍度": "高不确定性",
        "市场规模（仅中小厂商）": "中等不确定性",
    },
    priority_level="research",
    why_now=None,
    next_validation_questions=[
        "目标中小厂商对云端 AI 推理的延迟容忍上限是多少毫秒？",
    ],
)


# ─────────────────────────────────────────────
# 执行验证
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("Phase 2.3 综合验证（v2，游戏行业场景）")
print("=" * 70)

results = []
cases = [
    ("C1_游戏NPC商业化_escalate",  case1,  "escalate/pilot（时机紧迫）"),
    ("C2_游戏自动化测试_deep_dive", case2,  "validate/pilot"),
    ("C3_关卡内容生成_research",    case3,  "research/validate"),
    ("C4a_推理芯片硬件侧_deep_dive",case4a, "validate/pilot"),
    ("C4b_推理云服务云侧_research", case4b, "watch/validate"),
]

for name, opp, hint in cases:
    r, ok = validate_case(name, opp, hint)
    results.append((name, opp.priority_level, r.action_decision.decision_posture, ok))

# ─────────────────────────────────────────────
# 验证总结
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("验证总结")
print("=" * 70)
passed = sum(1 for *_, ok in results if ok)
total  = len(results)
print(f"结构检查通过率: {passed}/{total}")
print()
print(f"{'案例':<35} {'优先级':<12} {'实际姿态':<12} {'检查'}")
print("-" * 70)
for name, prio, posture, ok in results:
    print(f"{name:<35} {prio:<12} {posture:<12} {'PASS' if ok else 'FAIL'}")

# C4a + C4b 多机会场景说明
print("\n[多机会场景说明] C4a/C4b 来自同一批信号（硬件+资本），")
print("  模拟 2.2 产出 2 个不同方向的机会 → 调用方逐一分发给 2.3 独立处理。")
print("  验证多机会分发路径结构完整性。")

print(f"\n总结: {'ALL PASS' if passed == total else f'{passed}/{total} 通过'}")
