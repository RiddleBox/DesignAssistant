"""Phase 2.3 行动设计核心处理器"""
import importlib.util
import json
import os
from pathlib import Path
from typing import List
from models import (
    ActionDesignRequest, ActionDecisionObject, ActionDesignResult,
    PhasedPlanStage, PhaseResources, TopRisk, DecisionPosture,
    CommitmentMode, DebateSummary, DisplayDecision, PostureBasis
)


_DEBUG_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "debug_artifacts"


def _phase23_debug_enabled() -> bool:
    return os.environ.get("PHASE23_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _write_phase23_artifact(name: str, content: str) -> None:
    if not _phase23_debug_enabled():
        return
    try:
        _DEBUG_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        (_DEBUG_ARTIFACT_DIR / name).write_text(content or "", encoding="utf-8")
    except Exception:
        pass
class ActionDesigner:
    """行动设计器 - LLM 判断模式（规则引擎 fallback）"""

    def __init__(self, api_key: str = None, model: str = None, base_url: str = None, provider: str = None):
        # 从统一配置加载（优先使用非空传入参数，避免不同 phase 的配置混用）
        cfg = self._load_llm_config("2.3")
        _raw_api_key = api_key  # 保留原始传入值，用于判断是否强制规则引擎
        self.provider  = provider or cfg.get("provider") or "anthropic"
        self.api_key   = api_key if api_key not in (None, "") else (cfg.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", ""))
        self._force_rules = (_raw_api_key == '')  # api_key='' 时强制走规则引擎（测试用）
        self.model     = model if model not in (None, "") else cfg.get("model", "claude-sonnet-4-6")
        self.base_url  = base_url if base_url not in (None, "") else cfg.get("base_url", "https://api.anthropic.com")
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
            return mod.LLMClient(api_key=self.api_key, base_url=self.base_url, provider=self.provider)
        except Exception:
            return None

    def _call_llm(self, prompt: str) -> dict:
        """调用统一 LLM 客户端并解析 JSON 响应"""
        if not self._llm:
            raise RuntimeError("LLM client is not initialized")
        _write_phase23_artifact("phase23_arbitrator_prompt.txt", prompt)
        response = self._llm.call(prompt=prompt, model=self.model, max_tokens=self.max_tokens)
        if not response or not response.strip():
            _write_phase23_artifact("phase23_arbitrator_raw_response.txt", response or "")
            raise ValueError("LLM returned empty response")
        text = response.strip()
        _write_phase23_artifact("phase23_arbitrator_raw_response.txt", text)
        if "```" in text:
            start_fence = text.find("```")
            end_fence = text.rfind("```")
            if start_fence != -1 and end_fence != -1 and end_fence > start_fence:
                fenced = text[start_fence + 3:end_fence].strip()
                if fenced.lower().startswith("json"):
                    fenced = fenced[4:].strip()
                text = fenced
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        _write_phase23_artifact("phase23_arbitrator_json_candidate.txt", text)
        try:
            parsed = json.loads(text)
            _write_phase23_artifact("phase23_arbitrator_parsed.json", json.dumps(parsed, ensure_ascii=False, indent=2))
            return parsed
        except json.JSONDecodeError as e:
            preview = text[:300].replace("\n", " ")
            _write_phase23_artifact("phase23_arbitrator_parse_error.txt", f"{type(e).__name__}: {e}\n\n{text}")
            raise ValueError(f"Failed to parse LLM JSON: {e}; preview={preview}") from e

    def _derive_commitment_mode(self, posture: DecisionPosture) -> CommitmentMode:
        mapping = {
            "watch": "observation",
            "validate": "validation",
            "pilot": "limited_real_world_trial",
            "escalate": "scaled_commitment",
            "hold": "observation",
            "stop": "observation",
        }
        return mapping.get(posture, "validation")

    def _normalize_evidence_readiness(self, value) -> str:
        return value if value in {"weak", "partial", "sufficient", "strong"} else "partial"

    def _normalize_commitment_ceiling(self, value) -> CommitmentMode:
        return value if value in {"observation", "validation", "limited_real_world_trial", "scaled_commitment"} else "validation"

    def _normalize_reversibility(self, value) -> str:
        return value if value in {"high", "medium", "low"} else "medium"

    def _normalize_cost_level(self, value) -> str:
        return value if value in {"low", "medium", "high"} else "medium"

    def _infer_cost_of_delay_from_opportunity(self, opp) -> str:
        priority = (getattr(opp, "priority_level", "") or "").lower()

        if priority in {"watch", "low"} or "观察" in priority:
            return "low"
        if priority in {"escalate", "critical"}:
            return "high"
        if priority in {"deep_dive", "high"}:
            return "medium"
        return "medium"

    def _infer_cost_of_wrong_commitment_from_basis(self, basis: PostureBasis) -> str:
        if basis.commitment_ceiling_consensus == "observation":
            return "low"
        if basis.commitment_ceiling_consensus == "validation":
            return "high" if basis.critical_unknowns_blocking_real_world_action or basis.evidence_readiness_consensus in {"weak", "partial"} else "medium"
        if basis.commitment_ceiling_consensus == "limited_real_world_trial":
            return "medium" if basis.reversibility_consensus in {"high", "medium"} else "high"
        if basis.commitment_ceiling_consensus == "scaled_commitment":
            return "medium" if basis.evidence_readiness_consensus in {"sufficient", "strong"} else "high"
        return "medium"

    def _stabilize_posture_basis_for_opportunity(self, opp, basis: PostureBasis) -> PostureBasis:
        if opp is None:
            return basis
        stabilized_delay_cost = self._infer_cost_of_delay_from_opportunity(opp)
        pre_stabilized_basis = PostureBasis(
            evidence_readiness_consensus=basis.evidence_readiness_consensus,
            critical_unknowns_blocking_real_world_action=basis.critical_unknowns_blocking_real_world_action,
            commitment_ceiling_consensus=basis.commitment_ceiling_consensus,
            reversibility_consensus=basis.reversibility_consensus,
            cost_of_delay_consensus=stabilized_delay_cost,
            cost_of_wrong_commitment_consensus=basis.cost_of_wrong_commitment_consensus,
        )
        return PostureBasis(
            evidence_readiness_consensus=pre_stabilized_basis.evidence_readiness_consensus,
            critical_unknowns_blocking_real_world_action=pre_stabilized_basis.critical_unknowns_blocking_real_world_action,
            commitment_ceiling_consensus=pre_stabilized_basis.commitment_ceiling_consensus,
            reversibility_consensus=pre_stabilized_basis.reversibility_consensus,
            cost_of_delay_consensus=pre_stabilized_basis.cost_of_delay_consensus,
            cost_of_wrong_commitment_consensus=self._infer_cost_of_wrong_commitment_from_basis(pre_stabilized_basis),
        )

    def _default_posture_basis_from_posture(self, posture: DecisionPosture) -> PostureBasis:
        mapping = {
            "watch": PostureBasis(
                evidence_readiness_consensus="weak",
                critical_unknowns_blocking_real_world_action=True,
                commitment_ceiling_consensus="observation",
                reversibility_consensus="high",
                cost_of_delay_consensus="low",
                cost_of_wrong_commitment_consensus="low",
            ),
            "validate": PostureBasis(
                evidence_readiness_consensus="partial",
                critical_unknowns_blocking_real_world_action=True,
                commitment_ceiling_consensus="validation",
                reversibility_consensus="high",
                cost_of_delay_consensus="medium",
                cost_of_wrong_commitment_consensus="medium",
            ),
            "pilot": PostureBasis(
                evidence_readiness_consensus="sufficient",
                critical_unknowns_blocking_real_world_action=False,
                commitment_ceiling_consensus="limited_real_world_trial",
                reversibility_consensus="medium",
                cost_of_delay_consensus="medium",
                cost_of_wrong_commitment_consensus="medium",
            ),
            "escalate": PostureBasis(
                evidence_readiness_consensus="strong",
                critical_unknowns_blocking_real_world_action=False,
                commitment_ceiling_consensus="scaled_commitment",
                reversibility_consensus="low",
                cost_of_delay_consensus="high",
                cost_of_wrong_commitment_consensus="medium",
            ),
            "hold": PostureBasis(
                evidence_readiness_consensus="partial",
                critical_unknowns_blocking_real_world_action=True,
                commitment_ceiling_consensus="observation",
                reversibility_consensus="high",
                cost_of_delay_consensus="low",
                cost_of_wrong_commitment_consensus="medium",
            ),
            "stop": PostureBasis(
                evidence_readiness_consensus="weak",
                critical_unknowns_blocking_real_world_action=True,
                commitment_ceiling_consensus="observation",
                reversibility_consensus="high",
                cost_of_delay_consensus="low",
                cost_of_wrong_commitment_consensus="high",
            ),
        }
        return mapping.get(posture, mapping["validate"])

    def _coerce_posture_basis(self, raw_basis: dict, fallback_posture: DecisionPosture = "validate") -> PostureBasis:
        fallback = self._default_posture_basis_from_posture(fallback_posture)
        raw_basis = raw_basis if isinstance(raw_basis, dict) else {}
        return PostureBasis(
            evidence_readiness_consensus=self._normalize_evidence_readiness(raw_basis.get("evidence_readiness_consensus", fallback.evidence_readiness_consensus)),
            critical_unknowns_blocking_real_world_action=bool(raw_basis.get("critical_unknowns_blocking_real_world_action", fallback.critical_unknowns_blocking_real_world_action)),
            commitment_ceiling_consensus=self._normalize_commitment_ceiling(raw_basis.get("commitment_ceiling_consensus", fallback.commitment_ceiling_consensus)),
            reversibility_consensus=self._normalize_reversibility(raw_basis.get("reversibility_consensus", fallback.reversibility_consensus)),
            cost_of_delay_consensus=self._normalize_cost_level(raw_basis.get("cost_of_delay_consensus", fallback.cost_of_delay_consensus)),
            cost_of_wrong_commitment_consensus=self._normalize_cost_level(raw_basis.get("cost_of_wrong_commitment_consensus", fallback.cost_of_wrong_commitment_consensus)),
        )

    def _derive_decision_posture_from_basis(self, basis: PostureBasis) -> DecisionPosture:
        if basis.evidence_readiness_consensus == "weak":
            if basis.cost_of_delay_consensus == "high" and basis.cost_of_wrong_commitment_consensus == "low":
                return "validate"
            return "watch"

        if basis.critical_unknowns_blocking_real_world_action:
            return "validate"

        if basis.commitment_ceiling_consensus == "observation":
            return "watch"
        if basis.commitment_ceiling_consensus == "validation":
            return "validate"
        if basis.commitment_ceiling_consensus == "limited_real_world_trial":
            if basis.reversibility_consensus == "low" and basis.cost_of_wrong_commitment_consensus != "low":
                return "validate"
            if basis.cost_of_wrong_commitment_consensus == "high" and basis.cost_of_delay_consensus != "high":
                return "validate"
            return "pilot"
        if basis.commitment_ceiling_consensus == "scaled_commitment":
            if basis.cost_of_wrong_commitment_consensus == "high" and basis.cost_of_delay_consensus != "high":
                return "pilot"
            return "escalate"

        return "validate"

    def _infer_posture_basis_from_opportunity(self, opp) -> PostureBasis:
        priority = (getattr(opp, "priority_level", "") or "").lower()
        assumption_count = len(getattr(opp, "key_assumptions", []) or [])
        counter_count = len(getattr(opp, "counter_evidence", []) or [])
        delay_cost = self._infer_cost_of_delay_from_opportunity(opp)

        if priority in {"watch", "low"} or "观察" in priority:
            evidence = "weak"
            ceiling = "observation"
            blocking = True
        elif priority in {"escalate", "critical"}:
            evidence = "strong" if assumption_count <= 1 else "sufficient"
            ceiling = "scaled_commitment" if assumption_count <= 1 and counter_count == 0 else "limited_real_world_trial"
            blocking = False if ceiling != "validation" else True
        elif priority in {"deep_dive", "high"}:
            evidence = "sufficient" if assumption_count <= 2 else "partial"
            ceiling = "limited_real_world_trial" if assumption_count <= 2 else "validation"
            blocking = assumption_count > 2
        else:
            evidence = "partial"
            ceiling = "validation"
            blocking = True

        if counter_count >= 2 or assumption_count >= 4:
            wrong_commitment = "high"
        elif counter_count >= 1 or assumption_count >= 2:
            wrong_commitment = "medium"
        else:
            wrong_commitment = "low"

        reversibility = {
            "observation": "high",
            "validation": "high",
            "limited_real_world_trial": "medium",
            "scaled_commitment": "low",
        }.get(ceiling, "medium")

        return PostureBasis(
            evidence_readiness_consensus=evidence,
            critical_unknowns_blocking_real_world_action=blocking,
            commitment_ceiling_consensus=ceiling,
            reversibility_consensus=reversibility,
            cost_of_delay_consensus=delay_cost,
            cost_of_wrong_commitment_consensus=wrong_commitment,
        )

    def _derive_display(self, posture: DecisionPosture, commitment_mode: CommitmentMode) -> DisplayDecision:
        label_map = {
            "watch": "建议持续观察",
            "validate": "建议先验证",
            "pilot": "建议小范围试点",
            "escalate": "建议升级投入",
            "hold": "建议暂缓推进",
            "stop": "建议停止",
        }
        title_mode_map = {
            ("watch", "observation"): "watch-oriented",
            ("validate", "validation"): "validation-oriented",
            ("pilot", "limited_real_world_trial"): "pilot-oriented",
            ("escalate", "scaled_commitment"): "escalation-oriented",
        }
        return DisplayDecision(
            display_judgment_label=label_map.get(posture, "建议先验证"),
            display_badge=posture,
            display_title_mode=title_mode_map.get((posture, commitment_mode), f"{posture}-oriented"),
        )

    def _collect_key_gates(self, phased_plan: List[PhasedPlanStage]) -> List[str]:
        gates = []
        for stage in phased_plan:
            for item in getattr(stage, "go_no_go_criteria", []) or []:
                if item and item not in gates:
                    gates.append(item)
        return gates

    def _collect_exit_conditions(self, phased_plan: List[PhasedPlanStage]) -> List[str]:
        exit_conditions = []
        for stage in phased_plan:
            for item in getattr(stage, "exit_conditions", []) or []:
                if item and item not in exit_conditions:
                    exit_conditions.append(item)
        return exit_conditions

    def _infer_stage_1_objective(self, phased_plan: List[PhasedPlanStage]) -> str:
        if not phased_plan:
            return ""
        return getattr(phased_plan[0], "objective", "") or ""

    def _ensure_action_contract_fields(self, payload: dict, opp=None) -> dict:
        raw_posture = payload.get("decision_posture")
        if raw_posture not in {"watch", "validate", "pilot", "escalate", "hold", "stop"}:
            raw_posture = "validate"

        posture_basis = self._coerce_posture_basis(payload.get("posture_basis"), fallback_posture=raw_posture)
        posture_basis = self._stabilize_posture_basis_for_opportunity(opp, posture_basis)
        posture = raw_posture if raw_posture in {"hold", "stop"} else self._derive_decision_posture_from_basis(posture_basis)
        payload["decision_posture"] = posture
        payload["posture_basis"] = {
            "evidence_readiness_consensus": posture_basis.evidence_readiness_consensus,
            "critical_unknowns_blocking_real_world_action": posture_basis.critical_unknowns_blocking_real_world_action,
            "commitment_ceiling_consensus": posture_basis.commitment_ceiling_consensus,
            "reversibility_consensus": posture_basis.reversibility_consensus,
            "cost_of_delay_consensus": posture_basis.cost_of_delay_consensus,
            "cost_of_wrong_commitment_consensus": posture_basis.cost_of_wrong_commitment_consensus,
        }

        commitment_mode = self._derive_commitment_mode(posture)
        payload["commitment_mode"] = commitment_mode

        for key in ["why_this_posture", "resource_commitment_logic", "fallback_path"]:
            if not payload.get(key):
                payload[key] = "待补充"
        for key in ["phased_plan", "top_risks", "open_questions", "key_gates", "exit_conditions", "open_disagreements"]:
            if not isinstance(payload.get(key), list):
                payload[key] = []
        if not isinstance(payload.get("debate_summary"), dict):
            payload["debate_summary"] = {}
        if not payload.get("stage_1_objective") and payload["phased_plan"]:
            payload["stage_1_objective"] = payload["phased_plan"][0].get("objective", "")
        if not payload.get("display"):
            display = self._derive_display(posture, commitment_mode)
            payload["display"] = {
                "display_judgment_label": display.display_judgment_label,
                "display_badge": display.display_badge,
                "display_title_mode": display.display_title_mode,
            }
        return payload

    def _llm_design(self, opp) -> dict:
        """多 Agent 辩论（方案C）：
        第1轮：鹰派 / 鸽派 / 执行者（可行性）
        第2轮：鸽派反驳鹰派 / 执行者回应可行性挑战
        第3轮：仲裁者综合全局，输出 JSON
        """
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

        # ── 第1轮：三方独立陈述 ──────────────────────────────────────────
        hawk_prompt = f"""你是激进派战略顾问，倾向于抓住机会、快速行动、接受风险。
基于以下机会，给出你的行动建议（纯文字，不超过150字）：

{opp_context}

重点：放大支持证据，论证为何应立即推进，提出激进的行动姿态。"""
        _write_phase23_artifact("phase23_hawk_prompt.txt", hawk_prompt)
        hawk_view = self._llm.call(
            prompt=hawk_prompt,
            model=self.model, max_tokens=500)
        _write_phase23_artifact("phase23_hawk_response.txt", (hawk_view or "").strip())
        if not hawk_view:
            raise ValueError("Hawk agent returned empty response")

        dove_prompt = f"""你是保守派风险顾问，倾向于审慎验证、降低风险、分阶段承诺。
基于以下机会，给出你的行动建议（纯文字，不超过150字）：

{opp_context}

重点：放大反对证据和不确定性，论证为何应谨慎，指出激进行动的潜在风险。"""
        _write_phase23_artifact("phase23_dove_prompt.txt", dove_prompt)
        dove_view = self._llm.call(
            prompt=dove_prompt,
            model=self.model, max_tokens=500)
        _write_phase23_artifact("phase23_dove_response.txt", (dove_view or "").strip())
        if not dove_view:
            raise ValueError("Dove agent returned empty response")

        executor_prompt = f"""你是落地执行专家，只关注"这个方案现实中能不能做"。
不讨论机会是否值得，专注评估执行可行性：谁来做、需要什么资源、最大卡点在哪里、第一步能否在30天内启动。
基于以下机会，给出你的可行性评估（纯文字，不超过150字）：

{opp_context}

重点：指出资源、能力、时间的现实约束，评估第一阶段能否真正落地。"""
        _write_phase23_artifact("phase23_executor_prompt.txt", executor_prompt)
        executor_view = self._llm.call(
            prompt=executor_prompt,
            model=self.model, max_tokens=500)
        _write_phase23_artifact("phase23_executor_response.txt", (executor_view or "").strip())
        if not executor_view:
            raise ValueError("Executor agent returned empty response")

        # ── 第2轮：针对性反驳 ────────────────────────────────────────────
        dove_rebuttal = self._llm.call(
            prompt=f"""你是保守派风险顾问。你刚才看到了激进派的观点，现在针对性反驳（纯文字，不超过100字）：

激进派观点：{hawk_view.strip()}

针对激进派的具体论点，指出其最脆弱的假设或最容易失败的环节。""",
            model=self.model, max_tokens=300)
        if not dove_rebuttal:
            dove_rebuttal = "（无补充反驳）"

        executor_rebuttal = self._llm.call(
            prompt=f"""你是落地执行专家。你看到了激进派和保守派的观点，现在回应可行性层面最关键的挑战（纯文字，不超过100字）：

激进派观点：{hawk_view.strip()}
保守派观点：{dove_view.strip()}

只回应：如果要推进，第一步最难跨越的执行障碍是什么，如何降低它。""",
            model=self.model, max_tokens=300)
        if not executor_rebuttal:
            executor_rebuttal = "（无补充回应）"

        # ── 第3轮：仲裁者综合全局，输出 JSON ────────────────────────────
        arbitrator_prompt = f"""你是 Phase 2.3 行动设计仲裁者。你看完了完整的多方辩论，做出最终判断。

机会背景：
{opp_context}

═══ 第1轮陈述 ═══
激进派：{hawk_view.strip()}
保守派：{dove_view.strip()}
执行者（可行性）：{executor_view.strip()}

═══ 第2轮反驳 ═══
保守派反驳激进派：{dove_rebuttal.strip()}
执行者回应可行性挑战：{executor_rebuttal.strip()}

请综合三方观点和两轮辩论，输出最终行动设计。只输出合法 JSON，不要任何额外说明。

输出 JSON schema：
{{
  "posture_basis": {{
    "evidence_readiness_consensus": "weak|partial|sufficient|strong",
    "critical_unknowns_blocking_real_world_action": true,
    "commitment_ceiling_consensus": "observation|validation|limited_real_world_trial|scaled_commitment",
    "reversibility_consensus": "high|medium|low",
    "cost_of_delay_consensus": "low|medium|high",
    "cost_of_wrong_commitment_consensus": "low|medium|high"
  }},
  "decision_posture": "watch|validate|pilot|escalate",
  "commitment_mode": "observation|validation|limited_real_world_trial|scaled_commitment",
  "why_this_posture": "string（综合三方观点，100字以内）",
  "stage_1_objective": "string（第一阶段最核心目标，30字以内）",
  "key_gates": ["string（关键推进闸门，20字以内，1-2条）"],
  "exit_conditions": ["string（全局退出条件，20字以内，1-2条）"],
  "open_disagreements": ["string（仍保留的分歧，20字以内，0-2条）"],
  "debate_summary": {{
    "hawk_stance": "string（鹰派核心论点，40字以内）",
    "dove_stance": "string（鸽派核心论点，40字以内）",
    "executor_stance": "string（执行者核心可行性判断，40字以内）",
    "dove_rebuttal": "string（鸽派对鹰派的关键反驳，40字以内）",
    "executor_rebuttal": "string（执行者对可行性挑战的核心回应，40字以内）",
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
1. 先判断 `posture_basis` 六个槽位，再给出最终行动设计；如果 `posture_basis` 与 `decision_posture` 不一致，以 `posture_basis` 可归约出的 posture 为准。
2. decision_posture 必须是 watch/validate/pilot/escalate 之一。
3. commitment_mode 必须与 decision_posture 匹配：watch→observation，validate→validation，pilot→limited_real_world_trial，escalate→scaled_commitment。
4. phased_plan 1-2 个阶段（watch 只需1个），严格遵守每个字段的字数上限。
5. top_risks 2 条，每条必须填写 blocks_stage。
6. resource_rationale 必须说明资源与假设验证的绑定关系（50字以内）。
7. **执行者视角**：phased_plan 的 actions 和第一阶段 objective 必须体现执行者指出的可行性约束。
8. **时机判断（why_now）**：若 why_now 有内容，必须在 why_this_posture 中体现，并影响第一阶段节奏。
9. **前置问题（next_validation_questions）**：必须映射到 key_assumptions_to_test 或 go_no_go_criteria 中。
10. stage_1_objective 应与 phased_plan[0].objective 保持一致或高度一致。
11. key_gates 应是跨阶段最关键的推进闸门，不要简单重复所有 go_no_go_criteria。
12. 只输出合法 JSON，不要任何额外说明。
13. 禁止在 JSON 字符串值内使用中文引号（""「」），只允许使用半角双引号。
14. 总 JSON 输出必须控制在 3000 字以内。"""

        result = self._call_llm(arbitrator_prompt)
        result = self._ensure_action_contract_fields(result, opp)

        # 把第2轮辩论结果注入 debate_summary
        ds = result.get("debate_summary", {})
        if isinstance(ds, dict):
            ds.setdefault("dove_rebuttal", dove_rebuttal.strip()[:80])
            ds.setdefault("executor_rebuttal", executor_rebuttal.strip()[:80])
            ds.setdefault("executor_stance", executor_view.strip()[:80])
        result["debate_summary"] = ds

        return result

    def design_action(self, request: ActionDesignRequest) -> ActionDesignResult:
        """核心方法：从机会对象生成行动决策对象"""
        opp = request.opportunity_object

        if self.api_key and not self._force_rules:
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
                # 解析辩论摘要（含第2轮反驳字段）
                debate_raw = llm_result.get("debate_summary", {})
                debate_summary = DebateSummary(
                    hawk_stance=debate_raw.get("hawk_stance", ""),
                    dove_stance=debate_raw.get("dove_stance", ""),
                    executor_stance=debate_raw.get("executor_stance", ""),
                    dove_rebuttal=debate_raw.get("dove_rebuttal", ""),
                    executor_rebuttal=debate_raw.get("executor_rebuttal", ""),
                    resolution=debate_raw.get("resolution", ""),
                ) if debate_raw else None
                commitment_mode = llm_result.get("commitment_mode") or self._derive_commitment_mode(llm_result["decision_posture"])
                display_raw = llm_result.get("display") or {}
                display = DisplayDecision(
                    display_judgment_label=display_raw.get("display_judgment_label", self._derive_display(llm_result["decision_posture"], commitment_mode).display_judgment_label),
                    display_badge=display_raw.get("display_badge", self._derive_display(llm_result["decision_posture"], commitment_mode).display_badge),
                    display_title_mode=display_raw.get("display_title_mode", self._derive_display(llm_result["decision_posture"], commitment_mode).display_title_mode),
                )
                posture_basis_raw = llm_result.get("posture_basis") or {}
                posture_basis = self._coerce_posture_basis(posture_basis_raw, fallback_posture=llm_result["decision_posture"])
                action_decision = ActionDecisionObject(
                    opportunity_title=opp.opportunity_title,
                    decision_posture=llm_result["decision_posture"],
                    why_this_posture=llm_result["why_this_posture"],
                    phased_plan=phased_plan,
                    top_risks=top_risks,
                    resource_commitment_logic=llm_result["resource_commitment_logic"],
                    fallback_path=llm_result["fallback_path"],
                    open_questions=llm_result.get("open_questions", []),
                    commitment_mode=commitment_mode,
                    stage_1_objective=llm_result.get("stage_1_objective") or self._infer_stage_1_objective(phased_plan),
                    key_gates=llm_result.get("key_gates") or self._collect_key_gates(phased_plan),
                    exit_conditions=llm_result.get("exit_conditions") or self._collect_exit_conditions(phased_plan),
                    open_disagreements=llm_result.get("open_disagreements", []),
                    display=display,
                    posture_basis=posture_basis,
                    debate_summary=debate_summary,
                )
                # global_summary：从辩论结果提炼一句话摘要
                posture_label = display.display_badge
                why_short = llm_result["why_this_posture"][:60] if llm_result.get("why_this_posture") else ""
                global_summary = f"[{posture_label}] {opp.opportunity_title}——{why_short}"
                return ActionDesignResult(
                    request_id=request.request_id,
                    action_decision=action_decision,
                    global_summary=global_summary,
                    designer_version="v1.1-llm-contract",
                )
            except Exception as e:
                print(
                    f"  [2.3 LLM] 调用失败，fallback 到规则引擎: {type(e).__name__}: {e} | "
                    f"provider={self.provider} model={self.model} base_url={self.base_url} max_tokens={self.max_tokens}"
                )

        # 规则引擎 fallback
        posture_basis = self._infer_posture_basis_from_opportunity(opp)
        posture_basis = self._stabilize_posture_basis_for_opportunity(opp, posture_basis)
        posture = self._derive_decision_posture_from_basis(posture_basis)
        phased_plan = self._design_phased_plan(opp, posture)
        top_risks = self._identify_top_risks(opp)
        resource_logic = self._generate_resource_commitment_logic(phased_plan, posture)
        fallback = self._design_fallback_path(opp, posture)
        open_questions = self._collect_open_questions(opp)
        commitment_mode = self._derive_commitment_mode(posture)
        display = self._derive_display(posture, commitment_mode)

        action_decision = ActionDecisionObject(
            opportunity_title=opp.opportunity_title,
            decision_posture=posture,
            why_this_posture=f"[fallback] {self._explain_posture(opp, posture)}",
            phased_plan=phased_plan,
            top_risks=top_risks,
            resource_commitment_logic=resource_logic,
            fallback_path=fallback,
            open_questions=open_questions,
            commitment_mode=commitment_mode,
            stage_1_objective=self._infer_stage_1_objective(phased_plan),
            key_gates=self._collect_key_gates(phased_plan),
            exit_conditions=self._collect_exit_conditions(phased_plan),
            open_disagreements=[],
            display=display,
            posture_basis=posture_basis
        )

        return ActionDesignResult(
            request_id=request.request_id,
            action_decision=action_decision,
            global_summary=f"[{display.display_badge}] {opp.opportunity_title}——{self._explain_posture(opp, posture)[:60]}",
            designer_version="v1.1-rules-contract",
        )

    def _determine_posture(self, opp) -> DecisionPosture:
        """判断行动姿态"""
        return self._derive_decision_posture_from_basis(self._infer_posture_basis_from_opportunity(opp))

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
