"""Phase 2.3 行动设计核心处理器"""
from typing import List
from models import (
    ActionDesignRequest, ActionDecisionObject, ActionDesignResult,
    PhasedPlanStage, PhaseResources, TopRisk, DecisionPosture
)

class ActionDesigner:
    """行动设计器 - MVP最小实现"""

    def design_action(self, request: ActionDesignRequest) -> ActionDesignResult:
        """核心方法：从机会对象生成行动决策对象"""
        opp = request.opportunity_object

        # 步骤1：判断行动姿态
        posture = self._determine_posture(opp)

        # 步骤2：设计分阶段计划
        phased_plan = self._design_phased_plan(opp, posture)

        # 步骤3：识别顶级风险
        top_risks = self._identify_top_risks(opp)

        # 步骤4：生成资源承诺逻辑
        resource_logic = self._generate_resource_commitment_logic(phased_plan, posture)

        # 步骤5：设计备选路径
        fallback = self._design_fallback_path(opp, posture)

        # 步骤6：整理开放问题
        open_questions = self._collect_open_questions(opp)

        # 构建行动决策对象
        action_decision = ActionDecisionObject(
            opportunity_title=opp.opportunity_title,
            decision_posture=posture,
            why_this_posture=self._explain_posture(opp, posture),
            phased_plan=phased_plan,
            top_risks=top_risks,
            resource_commitment_logic=resource_logic,
            fallback_path=fallback,
            open_questions=open_questions
        )

        return ActionDesignResult(
            request_id=request.request_id,
            action_decision=action_decision
        )

    def _determine_posture(self, opp) -> DecisionPosture:
        """判断行动姿态"""
        # 简化规则：基于优先级和假设数量
        priority = opp.priority_level.lower()
        assumption_count = len(opp.key_assumptions)

        # 兼容 2.2 的 priority_level 值（watch/research/deep_dive/escalate）
        if priority == "watch" or priority == "low" or "观察" in priority:
            return "watch"
        elif priority == "escalate" or priority == "critical":
            return "escalate"
        elif priority == "deep_dive" or (priority == "high" and assumption_count <= 2):
            return "pilot"
        elif priority == "research" or (assumption_count > 3 and priority == "medium"):
            return "validate"
        else:
            return "validate"

    def _explain_posture(self, opp, posture: DecisionPosture) -> str:
        """解释姿态选择"""
        explanations = {
            "watch": f"机会'{opp.opportunity_title}'当前优先级为{opp.priority_level}，建议持续观察",
            "validate": f"机会存在{len(opp.key_assumptions)}个关键假设需要验证",
            "pilot": f"关键假设较少且优先级高，建议进入小规模试点",
            "escalate": f"机会优先级为{opp.priority_level}，建议准备升级投入",
            "hold": "当前条件不适合推进，建议暂停",
            "stop": "机会不再成立，建议停止"
        }
        return explanations.get(posture, "基于当前评估结果")

    def _design_phased_plan(self, opp, posture: DecisionPosture) -> List[PhasedPlanStage]:
        """设计分阶段计划"""
        stages = []
        
        if posture == "watch":
            # 观察姿态：单阶段轻量跟踪
            stages.append(PhasedPlanStage(
                stage="持续观察",
                objective="跟踪关键信号变化",
                key_assumptions_to_test=opp.key_assumptions[:1] if opp.key_assumptions else [],
                actions=["定期检查相关信息", "记录关键变化"],
                resources=PhaseResources(people="0.1人", budget="<5万", time="持续"),
                milestones=["建立观察机制"],
                go_no_go_criteria=["关键信号出现"],
                exit_conditions=["机会窗口关闭"]
            ))
        
        elif posture == "validate":
            # 验证姿态：1-2阶段验证关键假设
            stages.append(PhasedPlanStage(
                stage="关键假设验证",
                objective="验证最关键的假设",
                key_assumptions_to_test=opp.key_assumptions[:2],
                actions=["用户访谈", "桌面研究", "专家咨询"],
                resources=PhaseResources(people="1-2人", budget="10-20万", time="2-3个月"),
                milestones=["完成验证报告"],
                go_no_go_criteria=["至少70%假设得到验证"],
                exit_conditions=["关键假设被证伪"]
            ))
        
        elif posture == "pilot":
            # 试点姿态：2-3阶段渐进式试点
            stages.extend([
                PhasedPlanStage(
                    stage="技术验证",
                    objective="验证技术可行性",
                    key_assumptions_to_test=[opp.key_assumptions[0]] if opp.key_assumptions else [],
                    actions=["开发最小原型", "技术预研"],
                    resources=PhaseResources(people="2-3人", budget="20-30万", time="2个月"),
                    milestones=["原型验证通过"],
                    go_no_go_criteria=["技术方案可行"],
                    exit_conditions=["技术方案不可行"]
                ),
                PhasedPlanStage(
                    stage="小规模试点",
                    objective="验证商业可行性",
                    key_assumptions_to_test=opp.key_assumptions[1:],
                    actions=["小范围用户测试", "收集反馈"],
                    resources=PhaseResources(people="5-8人", budget="50-80万", time="3个月"),
                    milestones=["试点成功"],
                    go_no_go_criteria=["用户留存率>50%"],
                    exit_conditions=["用户反馈负面"]
                )
            ])
        
        elif posture == "escalate":
            # 升级姿态：准备扩大投入
            stages.append(PhasedPlanStage(
                stage="准备升级",
                objective="准备规模化投入",
                key_assumptions_to_test=[],
                actions=["组建正式团队", "申请正式预算", "制定扩展计划"],
                resources=PhaseResources(people="15-20人", budget="200-300万", time="6个月"),
                milestones=["获得升级批准"],
                go_no_go_criteria=["管理层批准", "资源到位"],
                exit_conditions=["市场窗口关闭"]
            ))
        
        return stages

    def _identify_top_risks(self, opp) -> List[TopRisk]:
        """识别顶级风险"""
        risks = []
        
        # 基于反面证据识别风险
        for evidence in opp.counter_evidence[:2]:
            risks.append(TopRisk(
                risk=evidence,
                impact_on_plan="可能影响假设验证结果",
                mitigation="在早期阶段重点验证相关假设"
            ))
        
        # 基于不确定性识别风险
        for key, uncertainty in list(opp.uncertainty_map.items())[:2]:
            risks.append(TopRisk(
                risk=f"{key}存在不确定性: {uncertainty}",
                impact_on_plan="可能导致计划调整",
                mitigation="设置阶段性检查点"
            ))
        
        return risks[:3]  # 最多返回3个顶级风险

    def _generate_resource_commitment_logic(self, phased_plan: List[PhasedPlanStage], posture: DecisionPosture) -> str:
        """生成资源承诺逻辑说明"""
        if not phased_plan:
            return "当前无需资源投入"
        
        first_stage = phased_plan[0]
        logic_parts = [
            f"第一阶段投入{first_stage.resources.people}，预算{first_stage.resources.budget}，"
            f"用于{first_stage.objective}。"
        ]
        
        if len(phased_plan) > 1:
            logic_parts.append(
                f"只有在{first_stage.go_no_go_criteria[0] if first_stage.go_no_go_criteria else '第一阶段成功'}后，"
                f"才释放后续阶段资源。"
            )
        
        logic_parts.append("这样可以避免在假设未验证前过早投入。")
        
        return "".join(logic_parts)

    def _design_fallback_path(self, opp, posture: DecisionPosture) -> str:
        """设计备选路径"""
        fallback_map = {
            "validate": "如果验证失败，降级为持续观察",
            "pilot": "如果试点失败，可考虑调整方案后重新验证",
            "escalate": "如果升级条件不满足，保持当前试点规模",
            "watch": "如果机会窗口关闭，停止跟踪",
            "hold": "如果阻塞条件解除，重新评估",
            "stop": "整理经验教训，归档"
        }
        return fallback_map.get(posture, "根据实际情况调整")

    def _collect_open_questions(self, opp) -> List[str]:
        """整理开放问题"""
        questions = []
        
        # 从关键假设生成问题
        for assumption in opp.key_assumptions[:3]:
            questions.append(f"{assumption}是否成立？")
        
        # 从不确定性生成问题
        for key in list(opp.uncertainty_map.keys())[:2]:
            questions.append(f"{key}的具体情况如何？")
        
        return questions[:5]  # 最多5个开放问题
