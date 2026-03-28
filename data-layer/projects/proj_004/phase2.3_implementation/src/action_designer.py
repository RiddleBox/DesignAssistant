"""Phase 2.3 行动设计核心处理器"""
import importlib.util
import json
import os
from typing import List
from models import (
    ActionDesignRequest, ActionDecisionObject, ActionDesignResult,
    PhasedPlanStage, PhaseResources, TopRisk, DecisionPosture,
    DebateSummary
)

class ActionDesigner:
    """行动设计器 - LLM 判断模式（规则引擎 fallback）"""

    def __init__(self, api_key: str = None, model: str = None):
        # 从统一配置加载（优先使用传入参数）
        cfg = self._load_llm_config("2.3")
        self.api_key   = api_key or cfg.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model     = model   or cfg.get("model", "claude-sonnet-4-6")
        self.base_url  = cfg.get("base_url", "https://api.anthropic.com")
        self.max_tokens = cfg.get("max_tokens", 4096)
        self._llm = self._load_llm_client()

    def _load_llm_config(self, phase: str) -> dict:
        """加载统一 LLM 配置（llm_config.py 在 proj_004/ 根目录）"""
        try:
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            path = os.path.join(proj_root, "llm_config.py")
            if not os.path.exists(path):
                return {}
            spec = importlib.util.spec_from_file_location("llm_config", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.get_llm_config(phase)
        except Exception:
            return {}

    def _load_llm_client(self):
        """加载统一 LLM 客户端（llm_client.py 在 proj_004/ 根目录）"""
        try:
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            path = os.path.join(proj_root, "llm_client.py")
            if not os.path.exists(path):
                return None
            spec = importlib.util.spec_from_file_location("llm_client", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.LLMClient(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            return None

    def _call_llm(self, prompt: str) -> dict:
        """调用统一 LLM 客户端并解析 JSON 响应"""
        if not self._llm:
            raise RuntimeError("LLM client is not initialized")
        response = self._llm.call(prompt=prompt, model=self.model, max_tokens=self.max_tokens)
        if not response or not response.strip():
            raise ValueError("LLM returned empty response")
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:] if lines and lines[0].startswith("```") else lines
            lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
            text = "\n".join(lines).strip()
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON: {e}") from e

    def _llm_design(self, opp) -> dict:
        """三轮辩论：鹰派 → 鸽派 → 仲裁，最终输出行动设计"""
        uncertainty_text = ""
        if isinstance(opp.uncertainty_map, dict):
            uncertainty_text = "; ".join(f"{k}: {v}" for k, v in opp.uncertainty_map.items())
        elif isinstance(opp.uncertainty_map, list):
            uncertainty_text = "; ".join(opp.uncertainty_map)

        opp_context = f"""机会：{opp.opportunity_title}
论点：{opp.opportunity_thesis}
优先级：{opp.priority_level}
支持证据：{json.dumps(opp.supporting_evidence, ensure_ascii=False)}
反对证据：{json.dumps(opp.counter_evidence, ensure_ascii=False)}
关键假设：{json.dumps(opp.key_assumptions, ensure_ascii=False)}
不确定性：{uncertainty_text}
时机判断（why_now）：{opp.why_now or '（未提供）'}
2.3前置问题（next_validation_questions）：{json.dumps(opp.next_validation_questions or [], ensure_ascii=False)}"""

        # --- 第一轮：鹰派（激进行动） ---
        hawk_prompt = f"""你是激进派战略顾问。你倾向于抓住机会、快速行动、接受风险。
请基于以下机会信息，给出你的行动建议（纯文字，不超过200字）：

{opp_context}

重点：放大支持证据，论证为何应该立即推进，提出激进的行动姿态和计划。"""
        hawk_view = self._llm.call(prompt=hawk_prompt, model=self.model, max_tokens=self.max_tokens)
        if not hawk_view:
            raise ValueError("Hawk agent returned empty response")

        # --- 第二轮：鸽派（保守谨慎） ---
        dove_prompt = f"""你是保守派风险顾问。你倾向于审慎验证、降低风险、分阶段承诺。
请基于以下机会信息，给出你的行动建议（纯文字，不超过200字）：

{opp_context}

重点：放大反对证据和不确定性，论证为何应该谨慎，指出激进行动的潜在风险。"""
        dove_view = self._llm.call(prompt=dove_prompt, model=self.model, max_tokens=self.max_tokens)
        if not dove_view:
            raise ValueError("Dove agent returned empty response")

        # --- 第三轮：仲裁者（综合输出 JSON） ---
        arbitrator_prompt = f"""你是 Phase 2.3 行动设计仲裁者。你听取了两方观点后，做出平衡的最终判断。

机会背景：
{opp_context}

激进派观点：
{hawk_view.strip()}

保守派观点：
{dove_view.strip()}

请综合两方观点，输出最终行动设计。只输出合法 JSON，不要任何额外说明。

输出 JSON schema：
{{
  "decision_posture": "watch|validate|pilot|escalate",
  "why_this_posture": "string（综合两方观点，100字以内）",
  "debate_summary": {{
    "hawk_stance": "string（鹰派核心论点，50字以内）",
    "dove_stance": "string（鸽派核心论点，50字以内）",
    "resolution": "string（仲裁理由，50字以内）"
  }},
  "phased_plan": [
    {{
      "stage": "string（阶段名，10字以内）",
      "objective": "string（30字以内）",
      "key_assumptions_to_test": ["string（20字以内，1-2条）"],
      "actions": ["string（20字以内，1-2条）"],
      "resources": {{
        "people": "string（10字以内）",
        "budget": "string（10字以内）",
        "time": "string（10字以内）",
        "resource_rationale": "string（50字以内：投入X是为了验证[假设]，通过后才释放下阶段资源）"
      }},
      "milestones": ["string（20字以内，1条）"],
      "go_no_go_criteria": ["string（20字以内，1-2条）"],
      "exit_conditions": ["string（20字以内，1条）"]
    }}
  ],
  "top_risks": [
    {{
      "risk": "string（20字以内）",
      "impact_on_plan": "string（20字以内）",
      "mitigation": "string（20字以内）",
      "blocks_stage": "string（阶段名或'全局'）"
    }}
  ],
  "resource_commitment_logic": "string（60字以内）",
  "fallback_path": "string（30字以内）",
  "open_questions": ["string（20字以内，1-2条）"]
}}

要求：
1. decision_posture 必须是 watch/validate/pilot/escalate 之一。
2. phased_plan 1-2 个阶段（watch 只需1个），严格遵守每个字段的字数上限。
3. top_risks 2 条，每条必须填写 blocks_stage。
4. resource_rationale 必须说明资源与假设验证的绑定关系（50字以内）。
5. **时机判断（why_now）**：若 why_now 字段有内容，必须在 why_this_posture 中体现时机判断，并影响第一阶段节奏。
6. **前置问题（next_validation_questions）**：若该字段有内容，必须将关键问题映射到 key_assumptions_to_test 或 go_no_go_criteria 中。
7. 只输出合法 JSON，不要任何额外说明。
8. 禁止在 JSON 字符串值内使用中文引号（""「」），只允许使用半角双引号。
9. 总 JSON 输出必须控制在 3000 字以内。"""

        result = self._call_llm(arbitrator_prompt)

        # 校验
        if result.get("decision_posture") not in {"watch", "validate", "pilot", "escalate"}:
            result["decision_posture"] = "validate"
        for key in ["why_this_posture", "resource_commitment_logic", "fallback_path"]:
            if not result.get(key):
                result[key] = "待补充"
        for key in ["phased_plan", "top_risks", "open_questions"]:
            if not isinstance(result.get(key), list) or not result[key]:
                result[key] = []
        return result

    def design_action(self, request: ActionDesignRequest) -> ActionDesignResult:
        """核心方法：从机会对象生成行动决策对象"""
        opp = request.opportunity_object

        if self.api_key:
            try:
                llm_result = self._llm_design(opp)
                phased_plan = [
                    PhasedPlanStage(
                        stage=s.get("stage", ""),
                        objective=s.get("objective", ""),
                        key_assumptions_to_test=s.get("key_assumptions_to_test", []),
                        actions=s.get("actions", []),
                        resources=PhaseResources(
                            people=s.get("resources", {}).get("people", ""),
                            budget=s.get("resources", {}).get("budget", ""),
                            time=s.get("resources", {}).get("time", ""),
                            resource_rationale=s.get("resources", {}).get("resource_rationale", ""),
                        ),
                        milestones=s.get("milestones", []),
                        go_no_go_criteria=s.get("go_no_go_criteria", []),
                        exit_conditions=s.get("exit_conditions", []),
                    )
                    for s in llm_result.get("phased_plan", [])
                ]
                top_risks = [
                    TopRisk(
                        risk=r.get("risk", ""),
                        impact_on_plan=r.get("impact_on_plan", ""),
                        mitigation=r.get("mitigation", ""),
                        blocks_stage=r.get("blocks_stage", ""),
                    )
                    for r in llm_result.get("top_risks", [])
                ]
                # 解析辩论摘要
                debate_raw = llm_result.get("debate_summary", {})
                debate_summary = DebateSummary(
                    hawk_stance=debate_raw.get("hawk_stance", ""),
                    dove_stance=debate_raw.get("dove_stance", ""),
                    resolution=debate_raw.get("resolution", ""),
                ) if debate_raw else None
                action_decision = ActionDecisionObject(
                    opportunity_title=opp.opportunity_title,
                    decision_posture=llm_result["decision_posture"],
                    why_this_posture=llm_result["why_this_posture"],
                    phased_plan=phased_plan,
                    top_risks=top_risks,
                    resource_commitment_logic=llm_result["resource_commitment_logic"],
                    fallback_path=llm_result["fallback_path"],
                    open_questions=llm_result.get("open_questions", []),
                    debate_summary=debate_summary,
                )
                return ActionDesignResult(
                    request_id=request.request_id,
                    action_decision=action_decision,
                    designer_version="v1.0-llm",
                )
            except Exception as e:
                print(f"  [2.3 LLM] 调用失败，fallback 到规则引擎: {e}")

        # 规则引擎 fallback
        posture = self._determine_posture(opp)
        phased_plan = self._design_phased_plan(opp, posture)
        top_risks = self._identify_top_risks(opp)
        resource_logic = self._generate_resource_commitment_logic(phased_plan, posture)
        fallback = self._design_fallback_path(opp, posture)
        open_questions = self._collect_open_questions(opp)

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

