"""
Phase 2.2 机会判断模块 - 核心判断引擎

实现6步判断流程：信号聚类 → 论点形成 → [RAG检索] → 证据组织+不确定性+分级+升级（LLM）
"""

import importlib.util
import json
import os
import time
import uuid
from typing import Dict, Any, List, Tuple, Optional
from schemas import (
    OpportunityJudgmentRequest,
    OpportunityJudgmentResult,
    OpportunityObject,
    Diagnostics,
    ErrorInfo
)
from validators import BoundaryValidator, EvidenceValidator


class JudgmentEngine:
    """机会判断引擎"""

    def __init__(self, llm_client=None, rag_retriever=None, api_key: str = None, model: str = None):
        """
        初始化判断引擎

        Args:
            llm_client: 保留兼容，已不使用
            rag_retriever: 可调用对象 (query: str) -> Optional[ContextPacket]，由调用方注入
            api_key: Anthropic API key，传入后启用 LLM 判断模式；None 时从 llm_config 读取
            model: 使用的模型；None 时从 llm_config 读取
        """
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        # 从统一配置加载（优先使用传入参数）
        cfg = self._load_llm_config("2.2")
        self.api_key  = api_key or cfg.get("api_key", "")
        self.model    = model   or cfg.get("model", "claude-sonnet-4-6")
        self.base_url = cfg.get("base_url", "https://api.anthropic.com")
        self.judgment_version = "v2.0-llm" if self.api_key else "v1.0-rules"
        self.boundary_validator = BoundaryValidator()
        self.evidence_validator = EvidenceValidator()
        self._llm = self._load_llm_client()

    def _load_llm_config(self, phase: str) -> dict:
        """加载统一 LLM 配置（llm_config.py 在 proj_004/ 根目录）"""
        try:
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
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
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
            path = os.path.join(proj_root, "llm_client.py")
            if not os.path.exists(path):
                return None
            spec = importlib.util.spec_from_file_location("llm_client", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.LLMClient(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            return None

    def judge(self, request: OpportunityJudgmentRequest) -> OpportunityJudgmentResult:
        """
        执行机会判断

        Args:
            request: 机会判断请求

        Returns:
            OpportunityJudgmentResult: 判断结果
        """
        start_time = time.time()

        try:
            # 边界检查：信号来源检查
            is_valid, error_msg = self.boundary_validator.check_signal_source(request)
            if not is_valid:
                return self._create_error_result(
                    "INVALID_INPUT",
                    error_msg,
                    int((time.time() - start_time) * 1000)
                )

            # 提取信号
            signals = request.decoded_intelligence.get("signals", [])

            # 检查信号数量
            if len(signals) == 0:
                return self._create_insufficient_evidence_result(
                    signals,
                    ["没有可用信号"],
                    int((time.time() - start_time) * 1000)
                )

            # 执行6步判断流程
            opportunity = self._execute_judgment_pipeline(request, signals)

            # 边界检查：证据完整性
            is_valid, warnings = self.boundary_validator.check_evidence_completeness(opportunity)

            # 边界检查：输出边界
            _, boundary_warnings = self.boundary_validator.check_output_boundary(opportunity)
            warnings.extend(boundary_warnings)

            # 计算处理时间
            processing_time = int((time.time() - start_time) * 1000)
            opportunity.processing_time_ms = processing_time

            # 计算证据完整度
            evidence_completeness = self.evidence_validator.calculate_evidence_completeness(
                opportunity.supporting_evidence,
                opportunity.counter_evidence,
                opportunity.key_assumptions,
                opportunity.uncertainty_map
            )

            # 构建诊断信息
            diagnostics = Diagnostics(
                signal_count=len(signals),
                evidence_completeness=evidence_completeness,
                boundary_warnings=warnings
            )

            # 返回成功结果
            return OpportunityJudgmentResult(
                opportunity=opportunity,
                status="success",
                diagnostics=diagnostics
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return self._create_error_result(
                "INTERNAL_ERROR",
                str(e),
                processing_time
            )

    def _execute_judgment_pipeline(
        self,
        request: OpportunityJudgmentRequest,
        signals: List[Dict[str, Any]]
    ) -> OpportunityObject:
        """执行6步判断流程"""

        # 步骤1：信号聚类与主题识别
        theme = self._cluster_signals_and_identify_theme(signals)

        # 步骤2：机会论点形成
        thesis = self._form_opportunity_thesis(signals, theme)

        # 步骤2.5：按需向 2.4 RAG 发起定向查询（由 2.2 主题驱动）
        context_packet = request.context_packet  # 外部传入优先
        if context_packet is None and self.rag_retriever is not None:
            rag_query = self._build_rag_query(theme, thesis)
            context_packet = self.rag_retriever(rag_query)

        # 步骤3-6：LLM 判断模式 or 规则 fallback
        if self.api_key:
            try:
                llm_result = self._llm_judge(signals, theme, thesis, context_packet)
                opportunity = OpportunityObject(
                    opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
                    opportunity_title=llm_result.get("opportunity_title", theme),
                    opportunity_thesis=llm_result.get("opportunity_thesis", thesis),
                    related_signals=signals,
                    supporting_evidence=llm_result.get("supporting_evidence", []),
                    counter_evidence=llm_result.get("counter_evidence", []),
                    key_assumptions=llm_result.get("key_assumptions", []),
                    uncertainty_map=llm_result.get("uncertainty_map", []),
                    priority_level=llm_result.get("priority_level", "watch"),
                    next_validation_questions=llm_result.get("next_validation_questions", []),
                    judgment_version=self.judgment_version,
                    processing_time_ms=0
                )
                return opportunity
            except Exception as _llm_e:
                # LLM 失败时 fallback 到规则引擎
                print(f"  [2.2 LLM] 调用失败，fallback 到规则引擎: {_llm_e}")

        # 规则引擎（fallback 或无 api_key 时）
        supporting, counter, assumptions = self._organize_evidence(signals, context_packet)
        uncertainty_map = self._assess_uncertainty(signals, supporting, counter)
        priority_level = self._classify_priority(signals, supporting, counter, uncertainty_map)
        validation_questions = self._generate_validation_questions(priority_level, uncertainty_map)

        # 构建机会对象
        opportunity = OpportunityObject(
            opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
            opportunity_title=theme,
            opportunity_thesis=thesis,
            related_signals=signals,
            supporting_evidence=supporting,
            counter_evidence=counter,
            key_assumptions=assumptions,
            uncertainty_map=uncertainty_map,
            priority_level=priority_level,
            next_validation_questions=validation_questions,
            judgment_version=self.judgment_version,
            processing_time_ms=0  # 将在外层设置
        )

        return opportunity

    def _build_rag_query(self, theme: str, thesis: str) -> str:
        """根据 2.2 已识别的主题和论点，构造定向 RAG 查询"""
        # 取 theme 前60字 + thesis 前80字，拼成自然语言查询
        theme_part = theme[:60].split('：')[0]  # 去掉统计后缀，只留核心标题
        thesis_part = thesis[:80]
        return f"{theme_part} {thesis_part}".strip()

    def _cluster_signals_and_identify_theme(self, signals: List[Dict[str, Any]]) -> str:
        """步骤1：信号聚类与主题识别"""
        # 统计各类型信号数量
        signal_types = [s.get("signal_type", "unknown") for s in signals]
        type_counts = {}
        for st in signal_types:
            type_counts[st] = type_counts.get(st, 0) + 1

        dominant_type = max(type_counts, key=type_counts.get)

        # 语义化类型标签
        type_labels = {
            "technical":  "技术",
            "market":     "市场",
            "team":       "团队",
            "capital":    "资本",
            "regulatory": "监管",
        }
        dominant_label = type_labels.get(dominant_type, dominant_type)

        # 从强度最高的前3个信号提取关键词构建标题
        sorted_signals = sorted(signals, key=lambda s: s.get("intensity_score", 0), reverse=True)
        top_labels = [
            s.get("signal_label", "").strip()
            for s in sorted_signals[:3]
            if s.get("signal_label", "").strip()
        ]

        if top_labels:
            # 用最强信号标签作为主题核心
            core = top_labels[0]
            total = len(signals)
            dominant_count = type_counts[dominant_type]
            other_types = [type_labels.get(t, t) for t in type_counts if t != dominant_type]
            other_str = ("、".join(other_types) + "信号交叉印证") if other_types else ""
            suffix = f"（{other_str}）" if other_str else ""
            return f"{core}：{dominant_label}类机会（{dominant_count}/{total} 个{dominant_label}信号{suffix}）"
        else:
            return f"{dominant_label}类机会（{type_counts[dominant_type]}/{len(signals)} 个信号）"

    def _form_opportunity_thesis(
        self,
        signals: List[Dict[str, Any]],
        theme: str
    ) -> str:
        """步骤2：机会论点形成"""
        # MVP实现：基于信号摘要形成论点
        signal_summaries = [s.get("signal_summary", "") for s in signals if s.get("signal_summary")]

        if len(signal_summaries) == 1:
            return f"基于{theme}，{signal_summaries[0]}"
        else:
            return f"基于{len(signals)}个{theme}信号，存在潜在机会"

    def _organize_evidence(
        self,
        signals: List[Dict[str, Any]],
        context_packet
    ) -> Tuple[List[str], List[str], List[str]]:
        """步骤3：证据组织"""
        supporting = []
        counter = []
        assumptions = []

        # 从信号中提取支持证据
        for i, signal in enumerate(signals):
            signal_id = signal.get("signal_id", f"signal_{i}")
            summary = signal.get("signal_summary", "未知信号")
            supporting.append(f"[{signal_id}] {summary}")

        # 从2.4证据包补充证据
        if context_packet:
            if context_packet.similar_cases:
                for case in context_packet.similar_cases:
                    supporting.append(f"[2.4-similar] {case}")

            if context_packet.counter_examples:
                for example in context_packet.counter_examples:
                    counter.append(f"[2.4-counter] {example}")

        # 如果没有反对证据，添加默认项
        if not counter:
            if len(signals) == 1:
                counter.append("[推断] 信号来源单一，缺少交叉验证")
            else:
                counter.append("[推断] 未发现明显反对证据，但需警惕潜在风险")

        # 生成关键假设
        assumptions.append(f"假设：当前{len(signals)}个信号能够代表真实趋势 [重要性: critical]")
        if not context_packet:
            assumptions.append("假设：无外部证据验证的情况下，信号可靠性足够 [重要性: important]")

        return supporting, counter, assumptions

    def _assess_uncertainty(
        self,
        signals: List[Dict[str, Any]],
        supporting: List[str],
        counter: List[str]
    ) -> List[str]:
        """步骤4：不确定性评估"""
        uncertainty = []

        # 证据完整度不确定性
        if len(signals) < 3:
            uncertainty.append("evidence_completeness: high - 信号数量不足，缺少交叉验证")
        elif len(signals) < 5:
            uncertainty.append("evidence_completeness: medium - 信号数量中等，建议补充")

        # 信号可靠性不确定性
        if len(supporting) <= len(counter):
            uncertainty.append("signal_reliability: medium - 反对证据较多，需谨慎判断")

        # 高强度信号的执行风险
        avg_intensity = sum(s.get("intensity", 0) for s in signals) / max(len(signals), 1)
        if avg_intensity >= 8:
            uncertainty.append("execution_risk: medium - 高强度机会需要快速决策，存在执行风险")

        return uncertainty

    def _classify_priority(
        self,
        signals: List[Dict[str, Any]],
        supporting: List[str],
        counter: List[str],
        uncertainty: List[str]
    ) -> str:
        """步骤5：分级判断"""
        signal_count = len(signals)
        evidence_ratio = len(supporting) / max(len(counter), 1)
        uncertainty_level = len([u for u in uncertainty if "high" in u])

        # 计算信号强度
        avg_intensity = sum(s.get("intensity", 0) for s in signals) / max(signal_count, 1)

        # 检测escalate触发条件：高强度+多信号+竞争压力
        has_urgency = any(
            "竞争" in s.get("signal_summary", "") or
            "窗口期" in s.get("signal_summary", "") or
            "抢占" in s.get("signal_summary", "")
            for s in signals
        )

        if signal_count >= 5 and avg_intensity >= 8 and has_urgency:
            return "escalate"
        elif signal_count >= 4 and evidence_ratio >= 1.5:
            return "deep_dive"
        elif signal_count >= 2 and evidence_ratio >= 1.5:
            return "research"
        elif signal_count == 1 or uncertainty_level >= 2:
            return "watch"
        else:
            return "watch"

    def _generate_validation_questions(
        self,
        priority_level: str,
        uncertainty_map: List[str]
    ) -> List[str]:
        """步骤6：升级建议"""
        questions = []

        if priority_level == "watch":
            questions.append("是否有更多相关信号出现？")
            questions.append("当前信号的可靠性如何验证？")
        elif priority_level == "research":
            questions.append("是否存在相似的成功/失败案例？")
            questions.append("市场对此的接受度如何？")
        elif priority_level == "deep_dive":
            questions.append("如何量化该机会的潜在影响？")
            questions.append("竞争对手是否有类似布局？")
        elif priority_level == "escalate":
            questions.append("是否需要立即启动深度调研？")
            questions.append("时间窗口期有多长？")

        # 基于不确定性补充问题
        if any("evidence_completeness" in u for u in uncertainty_map):
            questions.append("如何补充缺失的关键证据？")

        return questions

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用统一 LLM 客户端并解析 JSON 响应"""
        if not self._llm:
            raise RuntimeError("LLM client is not initialized")

        response = self._llm.call(
            prompt=prompt,
            model=self.model,
        )

        if not response or not response.strip():
            raise ValueError("LLM returned empty response")

        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON response: {e}") from e

    def _llm_judge(
        self,
        signals: List[Dict[str, Any]],
        theme: str,
        thesis: str,
        context_packet
    ) -> Dict[str, Any]:
        """使用 LLM 生成步骤3-6的判断结果"""
        signal_lines = []
        for i, signal in enumerate(signals, 1):
            signal_lines.append(
                f"{i}. [{signal.get('signal_type', 'unknown')}] "
                f"label={signal.get('signal_label', '')}; "
                f"summary={signal.get('signal_summary', '')}; "
                f"intensity={signal.get('intensity_score', signal.get('intensity', 0))}"
            )

        context_data = {
            "similar_cases": getattr(context_packet, "similar_cases", []) if context_packet else [],
            "counter_examples": getattr(context_packet, "counter_examples", []) if context_packet else [],
            "supporting_data": getattr(context_packet, "supporting_data", []) if context_packet else [],
        }

        prompt = f"""你是 Phase 2.2 机会判断引擎。请基于输入信号输出严格 JSON，不要输出任何额外说明。

职责边界（重要）：
- 信号由 Phase 2.1 粗筛而来，intensity/confidence 是单条信号的自身强度评估
- 你的任务是：把多个信号组装在一起，结合 2.4 的知识证据串联逻辑链，判断是否构成机会
- 单个信号不等于机会；机会需要多信号互相印证 + 2.4 的历史案例/行业知识支撑才可靠

任务：
- 组织 supporting_evidence / counter_evidence / key_assumptions
- 评估 uncertainty_map
- 给出 priority_level（仅允许：watch, research, deep_dive, escalate）
- 给出 next_validation_questions
- 可微调 opportunity_title 和 opportunity_thesis

输入：
- theme: {theme}
- thesis: {thesis}
- signals:
{chr(10).join(signal_lines)}
- context_packet: {json.dumps(context_data, ensure_ascii=False)}

输出 JSON schema：
{{
  "opportunity_title": "string",
  "opportunity_thesis": "string",
  "supporting_evidence": ["string"],
  "counter_evidence": ["string"],
  "key_assumptions": ["string"],
  "uncertainty_map": ["string"],
  "priority_level": "watch|research|deep_dive|escalate",
  "next_validation_questions": ["string"]
}}

要求：
1. 所有字段必须存在。
2. 每个列表至少 1 项；若证据不足请明确写出原因。
3. 只输出合法 JSON，不要输出任何其他内容。
4. 禁止在 JSON 字符串值内使用中文引号（“”「」），只允许使用半角双引号。"""

        result = self._call_llm(prompt)

        priority = result.get("priority_level", "watch")
        if priority not in {"watch", "research", "deep_dive", "escalate"}:
            result["priority_level"] = "watch"

        for key in [
            "supporting_evidence",
            "counter_evidence",
            "key_assumptions",
            "uncertainty_map",
            "next_validation_questions",
        ]:
            value = result.get(key)
            if not isinstance(value, list) or not value:
                result[key] = ["信息不足"]

        result["opportunity_title"] = result.get("opportunity_title") or theme
        result["opportunity_thesis"] = result.get("opportunity_thesis") or thesis
        return result

    def _create_error_result(
        self,
        error_code: str,
        error_message: str,
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建错误结果"""
        return OpportunityJudgmentResult(
            opportunity=None,
            status="error",
            error=ErrorInfo(code=error_code, message=error_message)
        )

    def _create_insufficient_evidence_result(
        self,
        signals: List[Dict[str, Any]],
        warnings: List[str],
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建证据不足结果"""
        # 创建最小机会对象
        opportunity = OpportunityObject(
            opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
            opportunity_title="证据不足",
            opportunity_thesis="当前信号不足以形成有效判断",
            related_signals=signals,
            supporting_evidence=[],
            counter_evidence=["[系统] 信号数量不足"],
            key_assumptions=["假设：需要更多信号才能形成有效判断"],
            uncertainty_map=["evidence_completeness: high - 缺少足够信号"],
            priority_level="watch",
            next_validation_questions=["是否有更多相关信号？", "当前信号是否可靠？"],
            judgment_version=self.judgment_version,
            processing_time_ms=processing_time
        )

        diagnostics = Diagnostics(
            signal_count=len(signals),
            evidence_completeness=0.0,
            boundary_warnings=warnings
        )

        return OpportunityJudgmentResult(
            opportunity=opportunity,
            status="insufficient_evidence",
            diagnostics=diagnostics
        )
