"""
Phase 2.2 机会判断模块 - 核心判断引擎

实现6步判断流程：信号聚类 → 论点形成 → [RAG检索] → 证据组织+不确定性+分级+升级（LLM）
"""

import importlib.util
import json
import os
import re
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


def _extract_context_data(context_packet) -> dict:
    """从 ContextPacket 按 content_type 提取 prompt 可用数据。

    兼容两种输入：
    - 新路径（packets 字段）：2.4 ContextPacket v1.0 结构化证据包列表，按 content_type 分拣
    - 旧路径（similar_cases 等旧字段）：直接透传，向后兼容

    content_type 映射规则（来自 ContextPacket v1.0 协议）：
    - case_record / market_data → similar_cases（支持论点的外部案例与数据）
    - constraint_rule           → counter_examples（边界约束，作为反向检验依据）
    - few_shot_example          → methodology_hints（判断方法参考）
    - glossary / background     → 辅助理解，不直接注入（避免 prompt 噪音）
    """
    if context_packet is None:
        return {"similar_cases": [], "counter_examples": [], "methodology_hints": [], "supporting_data": []}

    packets = getattr(context_packet, "packets", None)
    if packets:
        similar_cases = []
        counter_examples = []
        methodology_hints = []
        for p in packets:
            ct = getattr(p, "content_type", "")
            trust = getattr(p, "trust_level", "low")
            title = getattr(p, "source_title", "")
            excerpt = getattr(p, "excerpt", "")
            reason = getattr(p, "reason_for_match", "")
            entry = f"[{trust}][{title}] {excerpt}（命中原因：{reason}）"
            if ct in ("case_record", "market_data"):
                similar_cases.append(entry)
            elif ct == "constraint_rule":
                counter_examples.append(entry)
            elif ct == "few_shot_example":
                methodology_hints.append(entry)
            # glossary / background 不注入，避免 prompt 噪音
        return {
            "similar_cases": similar_cases,
            "counter_examples": counter_examples,
            "methodology_hints": methodology_hints,
            "supporting_data": similar_cases,  # _llm_judge 旧字段兼容
        }

    # 旧路径：直接读旧字段
    return {
        "similar_cases":     getattr(context_packet, "similar_cases", []) or [],
        "counter_examples":  getattr(context_packet, "counter_examples", []) or [],
        "methodology_hints": getattr(context_packet, "methodology_hints", []) or [],
        "supporting_data":   getattr(context_packet, "similar_cases", []) or [],
    }


class JudgmentEngine:
    """机会判断引擎"""

    def __init__(self, rag_retriever=None, api_key: str = None, model: str = None):
        """
        初始化判断引擎

        Args:
            rag_retriever: 可调用对象 (query: str) -> Optional[ContextPacket]，由调用方注入
            api_key: 特殊控制参数：
                       None → 从 llm_config.yaml 读取 phase 2.2 配置（正常模式）
                       ""   → 强制规则引擎模式，不发起任何 LLM 调用
            model:   覆盖 llm_config.yaml 的模型名；None 时以配置为准
        """
        self.rag_retriever = rag_retriever

        # 所有 LLM 配置统一从 llm_config.yaml 读取，不在代码里硬编码任何默认值
        # api_key='' 是特殊值，强制规则引擎模式（不读配置）
        if api_key == "":
            # 强制规则引擎模式
            self._llm = None
            self.api_key = ""
            self.model = model or "claude-sonnet-4-6"
            self.base_url = ""
            self.provider = "anthropic"
            self.max_tokens = 4096
        else:
            # 正常模式：所有 LLM 配置统一从 llm_config.yaml 读取
            self._llm = self._build_llm_client()
            if self._llm:
                self.api_key   = self._llm.api_key
                self.base_url  = self._llm.base_url
                self.provider  = self._llm.provider
            else:
                self.api_key, self.base_url, self.provider = "", "", "anthropic"
            # model / max_tokens 从配置读（LLMClient 不存这两个字段）
            cfg = self._load_llm_config("2.2")
            self.model     = model or cfg.get("model", "claude-sonnet-4-6")
            self.max_tokens = cfg.get("max_tokens", 4096)

        self.judgment_version = "v2.0-llm" if self.api_key else "v1.0-rules"
        self.boundary_validator = BoundaryValidator()
        self.evidence_validator = EvidenceValidator()

    def _load_llm_config(self, phase: str) -> dict:
        """从 llm_config.py 加载指定阶段的 LLM 配置字典"""
        try:
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
            spec = importlib.util.spec_from_file_location(
                "llm_config", os.path.join(proj_root, "llm_config.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.get_llm_config(phase)
        except Exception:
            return {}

    def _build_llm_client(self):
        """通过 llm_config.make_llm_client("2.2") 创建 LLM 客户端。

        所有连接参数（provider/api_key/base_url）均来自 llm_config.yaml，
        此处不硬编码任何默认值，也不重复解析配置文件。
        """
        try:
            proj_root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
            spec = importlib.util.spec_from_file_location(
                "llm_config", os.path.join(proj_root, "llm_config.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.make_llm_client("2.2")
        except Exception:
            return None

    def _call_llm_and_parse(self, prompt: str) -> Dict[str, Any]:
        """
        调用统一 LLM 客户端并解析 JSON 响应。

        原 _call_llm 方法在删除死代码时被误删，此处恢复。
        供 _llm_judge_v2 调用。
        """
        if not self._llm:
            raise RuntimeError("LLM client is not initialized")

        response = self._llm.call(
            prompt=prompt,
            model=self.model,
            max_tokens=self.max_tokens,
        )

        if not response or not response.strip():
            raise ValueError("LLM returned empty response")

        text = response.strip()

        # 提取 JSON：兼容三种形式
        #   1. 直接输出 {}
        #   2. ```json ... ``` 包裹
        #   3. 前缀说明文字 + ```json ... ```（中转 system prompt 行为）
        if "```" in text:
            m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
            if m:
                text = m.group(1).strip()
        # 兜底：取第一个 { 到最后一个 }
        start = text.find("{")
        end   = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM JSON response: {e}") from e

    def judge(self, request: OpportunityJudgmentRequest) -> OpportunityJudgmentResult:
        """
        执行机会判断

        Args:
            request: 机会判断请求（decoded_intelligences: List[DecodedIntelligence]）

        Returns:
            OpportunityJudgmentResult: 判断结果
        """
        start_time = time.time()

        try:
            # 从多条 DecodedIntelligence 中提取所有信号（保留来源上下文）
            enriched_signals = self._extract_enriched_signals(request.decoded_intelligences)

            # 信号隔离注入点（Signal Store 编排使用）
            # ----------------------------------------------------------------
            # judge_with_signal_store() 在构造子 request 时会设置
            # request._override_signals，用于将"筛选后的信号组"（如批内组合组、
            # 历史匹配组合）直接注入，替代从 decoded_intelligences 中重新提取。
            #
            # 设计意图：_execute_judgment_pipeline_v2 只消费 enriched_signals 列表，
            # 不关心来源，因此注入后整条 Step C 链路自然隔离到指定信号组上，
            # 避免多来源批次下 Step C 把无关信号一起纳入判断。
            #
            # 回退：删除或注释这 3 行，judge() 恢复原有从 DI 提取信号的行为。
            # 相关文档：phase2_plan/phase2.2_signal_store_设计方案_v2.md §3.3
            # ----------------------------------------------------------------
            if hasattr(request, "_override_signals") and request._override_signals:
                enriched_signals = request._override_signals

            # 边界检查：信号来源检查
            is_valid, error_msg = self.boundary_validator.check_signal_source_v2(enriched_signals)
            if not is_valid:
                return self._create_error_result(
                    "INVALID_INPUT", error_msg,
                    int((time.time() - start_time) * 1000)
                )

            if len(enriched_signals) == 0:
                return self._create_insufficient_evidence_result(
                    [], ["没有可用信号"],
                    int((time.time() - start_time) * 1000)
                )

            # 执行判断流程（返回 List[OpportunityObject]）
            opportunities = self._execute_judgment_pipeline_v2(request, enriched_signals)

            # 边界检查（对每个机会对象）
            all_warnings = []
            total_completeness = 0.0
            for opp in opportunities:
                _, ev_warnings = self.boundary_validator.check_evidence_completeness(opp)
                _, bd_warnings = self.boundary_validator.check_output_boundary(opp)
                opp_warnings = ev_warnings + bd_warnings
                if opp_warnings:
                    all_warnings.extend([f"[{opp.opportunity_title}] {w}" for w in opp_warnings])
                completeness = self.evidence_validator.calculate_evidence_completeness(
                    opp.supporting_evidence, opp.counter_evidence,
                    opp.key_assumptions, opp.uncertainty_map,
                    related_signals=opp.related_signals
                )
                total_completeness += completeness

            processing_time = int((time.time() - start_time) * 1000)
            avg_completeness = total_completeness / len(opportunities) if opportunities else 0.0

            # 设置每个机会的耗时
            for opp in opportunities:
                opp.processing_time_ms = processing_time

            diagnostics = Diagnostics(
                signal_count=len(enriched_signals),
                opportunity_count=len(opportunities),
                evidence_completeness=avg_completeness,
                boundary_warnings=all_warnings
            )

            return OpportunityJudgmentResult(
                opportunities=opportunities,
                status="success",
                diagnostics=diagnostics
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return self._create_error_result("INTERNAL_ERROR", str(e), processing_time)

    def _extract_enriched_signals(self, decoded_intelligences: list) -> List[Dict[str, Any]]:
        """
        从多条 DecodedIntelligence 中提取信号，保留来源上下文。
        每条信号额外附加：
          _source_id   : DecodedIntelligence 层面的来源 ID
          _source_type : DecodedIntelligence 层面的来源类型（news/report/announcement）
          source_ref   : Signal 层面的原始来源 ID（来自 2.1 schema，用于 EvidenceValidator 可信度审核）
        """
        enriched = []
        for di in decoded_intelligences:
            # 兼容 Pydantic model 和 dict
            if hasattr(di, "model_dump"):
                di_dict = di.model_dump()
            elif hasattr(di, "dict"):
                di_dict = di.dict()
            else:
                di_dict = di if isinstance(di, dict) else {}

            source_id   = di_dict.get("source_id", "unknown")
            source_type = di_dict.get("source_type", "unknown")
            signals     = di_dict.get("signals", [])

            for sig in signals:
                if hasattr(sig, "model_dump"):
                    sig = sig.model_dump()
                elif hasattr(sig, "dict"):
                    sig = sig.dict()
                # 附加来源上下文（保留 Signal 自身的 source_ref 供 EvidenceValidator 审核）
                enriched_sig = dict(sig)
                enriched_sig["_source_id"]   = source_id
                enriched_sig["_source_type"] = source_type
                # source_ref 已在 Signal schema 中定义，此处确保传递不丢失
                enriched_sig.setdefault("source_ref", f"{source_id}:{sig.get('signal_id','')}")
                enriched.append(enriched_sig)
        return enriched

    def _execute_judgment_pipeline_v2(
        self,
        request: OpportunityJudgmentRequest,
        enriched_signals: List[Dict[str, Any]]
    ) -> List[OpportunityObject]:
        """
        v2 判断流程：将带上下文的 enriched_signals 传入 LLM，
        由 LLM 自主完成信号分组 + 多机会识别 + 逻辑链推导 + 分级。
        返回 List[OpportunityObject]（可能包含多个独立机会）。
        规则引擎作为 fallback（按信号类型粗分组，每组一个机会）。
        """
        # 按需向 2.4 RAG 发起查询
        context_packet = request.context_packet
        if context_packet is None and self.rag_retriever is not None:
            labels = [s.get("signal_label", "") for s in enriched_signals[:3]]
            rag_query = " ".join(filter(None, labels))
            context_packet = self.rag_retriever(rag_query)

        if self.api_key:
            try:
                llm_results = self._llm_judge_v2(
                    enriched_signals,
                    context_packet,
                    scenario_hints=getattr(request, "_scenario_hints", None),
                )
                opportunities = []
                for opp_data in llm_results:
                    # 从 related_signal_indices 解析出对应信号子集
                    indices = opp_data.get("related_signal_indices", [])
                    if indices:
                        opp_signals = [enriched_signals[i - 1] for i in indices
                                       if 1 <= i <= len(enriched_signals)]
                    else:
                        opp_signals = enriched_signals  # fallback：全部信号

                    opportunities.append(OpportunityObject(
                        opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
                        opportunity_title=opp_data.get("opportunity_title", "未命名机会"),
                        opportunity_thesis=opp_data.get("opportunity_thesis", ""),
                        related_signals=opp_signals,
                        supporting_evidence=opp_data.get("supporting_evidence", []),
                        counter_evidence=opp_data.get("counter_evidence", []),
                        key_assumptions=opp_data.get("key_assumptions", []),
                        uncertainty_map=opp_data.get("uncertainty_map", []),
                        priority_level=opp_data.get("priority_level", "watch"),
                        why_now=opp_data.get("why_now"),
                        next_validation_questions=opp_data.get("next_validation_questions", []),
                        warnings=opp_data.get("warnings"),
                        judgment_version=self.judgment_version,
                        processing_time_ms=0
                    ))
                return opportunities if opportunities else self._rule_engine_fallback(
                    enriched_signals, context_packet)
            except Exception as e:
                print(f"  [2.2 LLM] 调用失败，fallback 到规则引擎: {e}")

        return self._rule_engine_fallback(enriched_signals, context_packet)

    def _rule_engine_fallback(
        self,
        enriched_signals: List[Dict[str, Any]],
        context_packet=None
    ) -> List[OpportunityObject]:
        """
        规则引擎 fallback：按信号类型粗分组，每组产出一个机会对象。
        分组逻辑：相同 signal_type 的信号归为一组；单信号类型时产出单一机会。
        """
        # 按 signal_type 分组
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for sig in enriched_signals:
            st = sig.get("signal_type", "unknown")
            groups.setdefault(st, []).append(sig)

        # 若只有一种类型，就整体作为一组
        if len(groups) <= 1:
            groups = {"all": enriched_signals}

        opportunities = []
        for group_key, signals in groups.items():
            theme  = self._cluster_signals_and_identify_theme(signals)
            thesis = self._form_opportunity_thesis(signals, theme)
            supporting, counter, assumptions = self._organize_evidence(signals, context_packet)
            uncertainty_map = self._assess_uncertainty(signals, supporting, counter)
            priority_level  = self._classify_priority(signals, supporting, counter, uncertainty_map)
            validation_qs   = self._generate_validation_questions(priority_level, uncertainty_map)

            opportunities.append(OpportunityObject(
                opportunity_id=f"opp_{uuid.uuid4().hex[:12]}",
                opportunity_title=theme,
                opportunity_thesis=thesis,
                related_signals=signals,
                supporting_evidence=supporting,
                counter_evidence=counter,
                key_assumptions=assumptions,
                uncertainty_map=uncertainty_map,
                priority_level=priority_level,
                why_now=self._infer_why_now(signals, priority_level),
                next_validation_questions=validation_qs,
                warnings=["[fallback] LLM 不可用，由规则引擎生成，结果仅供参考"],
                judgment_version=self.judgment_version,
                processing_time_ms=0
            ))
        return opportunities

    def _llm_judge_v2(
        self,
        enriched_signals: List[Dict[str, Any]],
        context_packet,
        scenario_hints: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        v2 LLM 判断 prompt：
        - 完整暴露 2.1 打分（intensity/confidence/timeliness）及 source_ref 作为信号权重和可信度依据
        - 暴露 source_type（news/report/announcement）帮助 LLM 评估来源可信度
        - 由 LLM 自主决定信号分组，识别多个独立机会方向（已拍板：多机会输出）
        - 2.4 context_packet 作为外部知识佐证
        - 返回 List[Dict]，每个 dict 对应一个机会对象的 LLM 输出
        """
        # 构建信号描述（完整上下文，含 source_ref）
        signal_lines = []
        for i, s in enumerate(enriched_signals, 1):
            signal_lines.append(
                f"{i}. [{s.get('signal_type','?')}] {s.get('signal_label','')}\n"
                f"   描述：{s.get('description','')}\n"
                f"   原文：{s.get('evidence_text','')[:120]}\n"
                f"   打分：intensity={s.get('intensity_score',0)} "
                f"confidence={s.get('confidence_score',0)} "
                f"timeliness={s.get('timeliness_score',0)}\n"
                f"   来源类型：{s.get('_source_type','unknown')} / 来源ID：{s.get('_source_id','')} / 信号来源ref：{s.get('source_ref','')}"
            )

        context_data = _extract_context_data(context_packet)

        prompt = f"""你是 Phase 2.2 机会判断引擎。基于多条情报信号，识别所有值得关注的战略机会（可能是多个）。

## 职责边界
- Phase 2.1 已完成噪音过滤，传入的信号已经过筛选
- 你的任务：把信号分组，识别出可能并行存在的多个独立机会方向，每个方向产出一个机会对象
- 同一逻辑链的信号合并为一个机会；指向不同方向的信号分别产出独立机会
- 打分含义：intensity=信号影响力(1-10)，confidence=来源可信度(1-10)，timeliness=时效性(1-10)
- source_type 含义：announcement=官方公告（可信度最高）；report=行业报告（趋势性）；news=新闻报道（需交叉验证）
- source_ref 是信号的原始来源标识，confidence 低（<5）或 source_type=news 时需在 warnings 中提示可信度风险

## 判断要求（每个机会对象）
1. **信号分组**：related_signal_indices 列出属于本机会的信号编号（1-based）
2. **逻辑链**：opportunity_thesis 说清楚「为什么这些信号组合构成机会」（2-4句话）
3. **时机性**：why_now 说明「当前时点为什么值得关注」（催化剂、时间窗口、紧迫性）
4. **证据对立**：supporting_evidence 和 counter_evidence 都必须存在，不能单边
5. **假设显式**：key_assumptions 写出判断成立的前提条件
6. **不确定性**：uncertainty_map 标注主要不确定因素及影响程度
7. **可信度警告**：若信号 confidence<5 或来源均为 news，在 warnings 里提示
8. **优先级依据**：
   - watch：信号单一或 confidence 普遍较低（<5）
   - research：2+ 条互补信号，有初步逻辑链
   - deep_dive：3+ 条高 intensity 信号（≥7），逻辑链清晰，反证可控
   - escalate：多维度信号聚合（technical+capital 或 market+capital），时效紧迫
{f"""
## 初步分析建议（来自 Step A，供参考，可突破）
以下是基于信号初步分析的场景建议，你可以参考，也可以忽略或突破这些建议，以你对全量信号的完整分析为准：
{chr(10).join(f"- {h}" for h in scenario_hints)}
如果发现其他更有价值的信号关联，优先以你的分析为准。
""" if scenario_hints else ""}
## 输入信号（来自 2.1，编号从 1 开始）
{chr(10).join(signal_lines)}

## 外部知识（来自 2.4，可选）
相似案例：{context_data['similar_cases']}
反例：{context_data['counter_examples']}
方法论提示：{context_data['methodology_hints']}

## 输出 JSON（只输出合法 JSON，不要任何额外说明）
{{
  "opportunities": [
    {{
      "related_signal_indices": [1, 2, 3],
      "opportunity_title": "简短机会标题（10-20字）",
      "opportunity_thesis": "机会论点：说清楚为什么这些信号组合构成机会（2-4句话）",
      "why_now": "当前时点为什么值得关注——催化剂、时间窗口、紧迫性",
      "supporting_evidence": ["支持证据1（引用具体信号编号或外部知识）", "..."],
      "counter_evidence": ["反对证据1（必须存在，若无明显反证则写出潜在风险）", "..."],
      "key_assumptions": ["假设1：判断成立的前提条件", "..."],
      "uncertainty_map": [
        "[source_reliability] 两条信号均来自新闻报道，非官方公告，存在信息解读偏差风险",
        "类型可选：source_reliability/evidence_completeness/execution_risk/market_timing/competitive_response"
      ],
      "priority_level": "watch|research|deep_dive|escalate",
      "next_validation_questions": [
        "供 2.3 行动设计使用的关键前置问题（go/no-go 判断或行动姿态选择的前置条件）",
        "聚焦「2.3 做行动决策前必须回答的问题」，不写外部信息收集任务"
      ],
      "warnings": ["可选，如「信号来源均为新闻（非官方公告），可信度待交叉验证」"]
    }}
  ]
}}"""

        raw = self._call_llm_and_parse(prompt)

        # 解析 opportunities 列表
        opps = raw.get("opportunities", [])
        if not isinstance(opps, list) or len(opps) == 0:
            # LLM 返回旧格式（单对象）时兼容处理
            if "opportunity_title" in raw:
                raw.setdefault("related_signal_indices", list(range(1, len(enriched_signals)+1)))
                opps = [raw]
            else:
                opps = []

        # 逐个校验兜底
        validated = []
        for opp in opps:
            if opp.get("priority_level") not in {"watch", "research", "deep_dive", "escalate"}:
                opp["priority_level"] = "watch"
            for key in ["supporting_evidence", "counter_evidence", "key_assumptions",
                        "uncertainty_map", "next_validation_questions"]:
                if not isinstance(opp.get(key), list) or not opp[key]:
                    opp[key] = ["信息不足"]
            opp.setdefault("opportunity_title", "未命名机会")
            opp.setdefault("opportunity_thesis", "信号组合待进一步分析")
            validated.append(opp)

        return validated

    def _create_error_result(
        self,
        error_code: str,
        error_message: str,
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建错误结果"""
        return OpportunityJudgmentResult(
            opportunities=[],
            status="error",
            error=ErrorInfo(code=error_code, message=error_message)
        )

    def _create_insufficient_evidence_result(
        self,
        signals: List[Dict[str, Any]],
        warnings: List[str],
        processing_time: int
    ) -> OpportunityJudgmentResult:
        """创建证据不足结果（返回空机会列表，状态标记 insufficient_evidence）"""
        diagnostics = Diagnostics(
            signal_count=len(signals),
            opportunity_count=0,
            evidence_completeness=0.0,
            boundary_warnings=warnings
        )
        return OpportunityJudgmentResult(
            opportunities=[],
            status="insufficient_evidence",
            diagnostics=diagnostics
        )

    # ══════════════════════════════════════════════════════════
    # Signal Store 编排入口（新增，不改动现有 judge() 方法）
    # ══════════════════════════════════════════════════════════

    def judge_with_signal_store(
        self,
        request: "OpportunityJudgmentRequest",
        signal_store=None,
        rag_store_add_fn=None,
    ) -> "OpportunityJudgmentResult":
        """
        带 Signal Store 的机会判断入口（Signal Store 编排主函数）。

        流程：
          Step A → 批内聚类 + 角色标注（LLM 标注 roles/needs/domains）
          Step B → 孤立信号历史检索（分层漏斗匹配历史伙伴）
          Step C → 完整机会判断（复用现有 judge()，隔离信号组）

        调用约束：
          - signal_store 必须由调用方（run_batch_real.py）用 sys.path.insert 方式
            创建后传入，确保 pickle 序列化的类名为 signal_store.SignalEntry，
            而非 importlib 动态模块名（会导致反序列化失败）
          - 兄弟模块（step_a/step_b/golden_pattern）通过标准 import 加载，
            依赖调用方在启动时已将 phase2.2_implementation 加入 sys.path

        与 judge() 的关系：
          - judge() 完全保留，本方法是独立的新入口
          - 2.1→2.2 输入接口、2.2→2.3 输出接口 schema 完全兼容

        Args:
            request:         标准 OpportunityJudgmentRequest
            signal_store:    SignalStore 实例，必须由调用方传入
            rag_store_add_fn: 可选，黄金模板写入函数（None 时由 golden_pattern 模块自动处理）

        Returns:
            OpportunityJudgmentResult（schema 与 judge() 完全一致）
        """
        import time as _time
        from datetime import date

        start_time = _time.time()

        # signal_store 必须由外部传入，不在内部创建
        # 原因：内部用 importlib 动态加载的类与外部 sys.path import 的类不同，
        # pickle 序列化/反序列化时会因模块名不匹配而失败
        if signal_store is None:
            raise ValueError(
                "signal_store 必须由调用方通过 sys.path.insert 方式创建后传入，"
                "请勿在 judge_with_signal_store 内部自动创建"
            )

        # 兄弟模块通过标准 import 加载（依赖调用方已将 phase2.2_implementation 加入 sys.path）
        # 与外部创建的 signal_store 使用同一模块，类名一致，pickle 安全
        try:
            from signal_store import build_signal_entry, OpportunityStore
            from step_a_cluster import run_step_a
            from step_b_retrieval import run_step_b
            from golden_pattern import maybe_write_golden_pattern
        except ImportError as e:
            print(f"[judge_with_signal_store] 模块导入失败，退化为 judge(): {e}")
            return self.judge(request)

        # 归档过期信号（每次调用时顺带执行，成本极低）
        archived = signal_store.archive_expired()
        if archived:
            print(f"[Signal Store] 归档过期信号 {archived} 条")

        today = date.today().isoformat()

        # ── Step A：批内聚类 + 角色标注 ─────────────────────
        enriched_signals = self._extract_enriched_signals(request.decoded_intelligences)

        # _override_signals 支持：直接注入信号（测试/子请求场景）
        if hasattr(request, "_override_signals") and request._override_signals:
            enriched_signals = request._override_signals

        if not enriched_signals:
            return self._create_insufficient_evidence_result(
                [], ["没有可用信号"],
                int((_time.time() - start_time) * 1000)
            )

        # ── 小批次快速路径：≤ SMALL_BATCH_THRESHOLD 条信号直接全量送 Step C ──
        # 原因：小批次下 Step A 的分组带来前置假设污染，反而降低精度；
        #       全量送 Step C 成本可控（< 20 条信号约 3000–6000 tokens），精度更高。
        SMALL_BATCH_THRESHOLD = 15
        if len(enriched_signals) <= SMALL_BATCH_THRESHOLD:
            print(f"[Step A] 小批次快速路径（{len(enriched_signals)} 条 ≤ {SMALL_BATCH_THRESHOLD}），跳过 Step A，全量送 Step C")
            direct_request = self._build_group_request(request, enriched_signals)
            direct_result = self.judge(direct_request)
            # 小批次所有信号一律视为 contributed / pending（无需 Signal Store 精确绑定）
            from signal_store import build_signal_entry
            for sig in enriched_signals:
                ann = sig.get("_role_annotation", {})
                entry = build_signal_entry(
                    signal=sig if isinstance(sig, dict) else self._signal_entry_to_dict(sig),
                    roles=ann.get("roles", ["catalyst"]),
                    needs=ann.get("needs", []),
                    domains=ann.get("domains", ["gaming"]),
                    waiting_for_text=ann.get("waiting_for_text", ""),
                    batch_date=today,
                )
                # 若 Step C 产出了机会，标记为 contributed；否则 pending 等待后续批次
                if direct_result.opportunities:
                    entry.status = "contributed"
                try:
                    signal_store.add(entry)
                except Exception:
                    pass  # 重复信号忽略
            return direct_result

        step_a_result = run_step_a(
            enriched_signals=enriched_signals,
            llm_client=self._llm,
            model=self.model,
        )

        if step_a_result.fallback_used:
            print("[Step A] 使用规则 fallback（LLM 未响应）")
        print(f"[Step A] 场景识别结果: {len(step_a_result.logical_scenarios)} 个逻辑场景 / {len(step_a_result.isolated_signals)} 条信号（含角色标注）")

        # ── Step C（批内逻辑场景 → 软约束全量判断）──────────
        # 设计：Step A 输出 logical_scenarios（软建议），Step C 接收全量信号 + 场景建议
        # Step C 一次调用，可见所有信号，场景只作 prompt 前缀建议，不硬隔离
        all_opportunities = []
        source_signal_map = {}  # opportunity_id → List[SignalEntry]

        # 高强度孤立信号兜底阈值（intensity ≥ 7 对应 deep_dive 级信号）
        HIGH_INTENSITY_THRESHOLD = 7

        if step_a_result.logical_scenarios or any(
            (s.get("intensity_score") or s.get("intensity", 0)) >= HIGH_INTENSITY_THRESHOLD
            for s in enriched_signals
        ):
            # 有逻辑场景，或有高强度信号 → 发起 Step C 全量判断
            scenario_request = self._build_scenario_request(
                original_request=request,
                all_signals=enriched_signals,
                logical_scenarios=step_a_result.logical_scenarios,
            )
            result = self.judge(scenario_request)
            all_opportunities.extend(result.opportunities or [])
            for opp in (result.opportunities or []):
                source_signal_map[opp.opportunity_id] = enriched_signals

            # 成功产出机会的信号以 contributed 状态写入 Signal Store
            if result.opportunities:
                contributed_entries = []
                def _matches(s_src, ref_set):
                    if not s_src or not ref_set:
                        return True
                    for ref in ref_set:
                        if ref == s_src or ref.startswith(s_src + ":"):
                            return True
                    return False

                for opp in result.opportunities:
                    related_source_refs = set()
                    for rs in (opp.related_signals or []):
                        ref = rs.get("source_ref") or rs.get("source_id", "")
                        if ref:
                            related_source_refs.add(ref)

                    if not related_source_refs and opp.related_signals is not None:
                        print(
                            f"[Bug1][WARN] opp '{opp.opportunity_title}' 的 related_signals "
                            f"全部缺失 source_ref/source_id，精确绑定退化为全量 fallback"
                        )

                    bound_count = 0
                    for s in enriched_signals:
                        s_source = (
                            s.get("source_id") or s.get("_source_id", "")
                        ) if isinstance(s, dict) else ""
                        if related_source_refs and not _matches(s_source, related_source_refs):
                            continue
                        bound_count += 1
                        ann = s.get("_role_annotation", {}) if isinstance(s, dict) else {}
                        entry = build_signal_entry(
                            signal=s if isinstance(s, dict) else self._signal_entry_to_dict(s),
                            roles=ann.get("roles", ["catalyst"]),
                            needs=ann.get("needs", []),
                            domains=ann.get("domains", ["gaming"]),
                            waiting_for_text=ann.get("waiting_for_text", ""),
                            batch_date=today,
                        )
                        entry.status = "contributed"
                        entry.matched_opportunity_id = opp.opportunity_id
                        contributed_entries.append(entry)

                    if related_source_refs and bound_count == 0:
                        print(
                            f"[Bug1][WARN] opp '{opp.opportunity_title}' 精确绑定失败："
                            f"related_source_refs={related_source_refs} 均无法匹配信号，"
                            f"请检查 LLM 输出的 source_ref 格式是否与实际 _source_id 一致"
                        )

                if contributed_entries:
                    signal_store.add_batch(contributed_entries)
                    print(f"[Signal Store] 写入 {len(contributed_entries)} 条已贡献信号（contributed）")

        # ── Step B + Step C（孤立信号 → 历史检索）────────────
        # Step A v2.0：isolated_signals 包含所有信号（角色已标注）
        # 孤立信号 = 未在 Step C 中成功转化为机会的信号，走跨批次 Step B 路径
        # 如果 Step C 已产出机会，参与机会的信号已写入 contributed，不重复写入
        contributed_source_ids = set()
        for entries in source_signal_map.values():
            if isinstance(entries, list):
                for e in entries:
                    sid = e.get("source_id") or e.get("_source_id", "") if isinstance(e, dict) else getattr(e, "source_id", "")
                    if sid:
                        contributed_source_ids.add(sid)

        signals_to_store = []   # 最终需要写入 Signal Store 的孤立信号

        for iso_signal in step_a_result.isolated_signals:
            iso_label = iso_signal.get("signal_label", iso_signal.get("_signal_id", "unknown"))
            print(f"[Step B] 孤立信号进入检索: {iso_label}")
            step_b_result = run_step_b(
                isolated_signal=iso_signal,
                signal_store=signal_store,
                llm_client=self._llm,
                model=self.model,
            )

            if step_b_result.matched:
                total_candidates = sum(len(g) for g in step_b_result.candidate_groups)
                fallback_tag = "（fallback）" if step_b_result.fallback_used else ""
                print(f"[Step B] ✅ 命中历史伙伴{fallback_tag}: {total_candidates} 条候选 → 进入 Step C")
                # 找到历史伙伴，构建组合请求进 Step C
                for candidate_group in step_b_result.candidate_groups:
                    combined_signals = [iso_signal] + [
                        self._signal_entry_to_dict(e) for e in candidate_group
                    ]
                    group_request = self._build_group_request(request, combined_signals)
                    result = self.judge(group_request)
                    new_opps = result.opportunities or []
                    all_opportunities.extend(new_opps)

                    # 标记历史信号状态
                    for opp in new_opps:
                        # iso_signal 写入 Signal Store 并标记 matched
                        # 若该信号已在本批 Step C 中以 contributed 写入，则跳过（不覆盖贡献记录）
                        iso_sig_id = f"sig_{iso_signal.get('signal_id') or iso_signal.get('id') or ''}_{iso_signal.get('signal_type','')}"
                        existing = signal_store.get(iso_sig_id)
                        if existing and existing.status == "contributed":
                            # 已有贡献记录，不重复写 matched，避免状态污染
                            iso_entry = existing
                        else:
                            ann = iso_signal.get("_role_annotation", {})
                            iso_entry = build_signal_entry(
                                signal=iso_signal,
                                roles=ann.get("roles", ["catalyst"]),
                                needs=ann.get("needs", []),
                                domains=ann.get("domains", ["gaming"]),
                                waiting_for_text=ann.get("waiting_for_text", ""),
                                batch_date=today,
                            )
                            iso_entry.status = "matched"
                            iso_entry.matched_opportunity_id = opp.opportunity_id
                            signal_store.add(iso_entry)

                        # source_signal_map 包含 iso_entry + 历史伙伴，黄金模板完整
                        source_signal_map[opp.opportunity_id] = [iso_entry] + list(candidate_group)
                        for entry in candidate_group:
                            signal_store.update_status(
                                entry.signal_id, "matched", opp.opportunity_id
                            )
            else:
                # 没有找到伙伴，当前信号写入 Signal Store
                print(f"[Step B] ❌ 无历史伙伴: {iso_label} → 写入 Signal Store 等待后续批次")
                signals_to_store.append(iso_signal)

        # ── 写入孤立信号到 Signal Store ───────────────────────
        if signals_to_store:
            entries = []
            for s in signals_to_store:
                ann = s.get("_role_annotation", {})
                entry = build_signal_entry(
                    signal=s,
                    roles=ann.get("roles", ["catalyst"]),
                    needs=ann.get("needs", []),
                    domains=ann.get("domains", ["gaming"]),
                    waiting_for_text=ann.get("waiting_for_text", ""),
                    batch_date=today,
                )
                entries.append(entry)
            signal_store.add_batch(entries)
            print(f"[Signal Store] 写入 {len(entries)} 条待组合信号")

        # ── 黄金模板写回（已成机会 → 2.4 RAG）───────────────
        # ── 机会 ID 持久化（跨批次复用 opportunity_id）────────
        opp_store = OpportunityStore()
        for opp in all_opportunities:
            src_entries = source_signal_map.get(opp.opportunity_id, [])

            # 机会 ID 持久化：基于 source_id 重叠判断是否复用历史 ID
            source_ids = {e.source_id for e in src_entries if hasattr(e, "source_id")}
            sig_ids = [e.signal_id for e in src_entries if hasattr(e, "signal_id")]
            resolved_id = opp_store.resolve_opportunity_id(opp, source_ids, sig_ids)
            if resolved_id != opp.opportunity_id:
                print(f"[Opportunity Store] 复用历史 ID: {resolved_id} (原 {opp.opportunity_id})")
                opp.opportunity_id = resolved_id
            else:
                print(f"[Opportunity Store] 新建机会: {resolved_id}")

            # 黄金模板写回
            if src_entries:
                maybe_write_golden_pattern(
                    opportunity=opp,
                    source_signal_entries=src_entries,
                    rag_store_add_fn=rag_store_add_fn,
                )

        # ── 构建最终结果 ─────────────────────────────────────
        processing_time = int((_time.time() - start_time) * 1000)
        if all_opportunities:
            diagnostics = Diagnostics(
                signal_count=len(enriched_signals),
                opportunity_count=len(all_opportunities),
                evidence_completeness=1.0,
                boundary_warnings=[],
            )
            return OpportunityJudgmentResult(
                opportunities=all_opportunities,
                status="success",
                diagnostics=diagnostics,
            )
        else:
            # 当批次无机会产出（信号已写入 Signal Store 等待积累）
            diagnostics = Diagnostics(
                signal_count=len(enriched_signals),
                opportunity_count=0,
                evidence_completeness=0.0,
                boundary_warnings=[
                    f"当批次 {len(signals_to_store)} 条信号已写入 Signal Store，等待后续批次补全"
                ],
            )
            return OpportunityJudgmentResult(
                opportunities=[],
                status="pending_signals",   # 新增状态：区别于 insufficient_evidence
                diagnostics=diagnostics,
            )

    @staticmethod
    def _dedup_signals_by_source(signals: list) -> list:
        """
        按 source_id 去重：同一来源只保留 intensity_score 最高的信号。

        规则：同一信号在同一机会中只计为一条证据，防止同一来源的多篇报道
        在 supporting_evidence 中被重复计数（证据虚胖）。
        跨机会复用同一信号是允许的，去重只在单次 Step C 组合内生效。
        """
        seen: dict = {}
        for s in signals:
            sid = s.get("source_id") or s.get("_source_id", "")
            if not sid:
                # 无 source_id 的信号直接保留（无法判断是否重复）
                seen[id(s)] = s
                continue
            if sid not in seen:
                seen[sid] = s
            else:
                # 保留强度更高的那条
                if s.get("intensity_score", 0) > seen[sid].get("intensity_score", 0):
                    seen[sid] = s
        return list(seen.values())

    def _build_group_request(self, original_request, signals: list):
        """基于原始 request 和指定信号列表，构建子 request（复用 rag_retriever 等配置）"""
        new_req = OpportunityJudgmentRequest(
            decoded_intelligences=original_request.decoded_intelligences,
            context_packet=original_request.context_packet,
        )
        new_req._override_signals = self._dedup_signals_by_source(signals)
        return new_req

    def _build_scenario_request(self, original_request, all_signals: list, logical_scenarios: list):
        """
        构建 Step C 的全量信号 + 逻辑场景建议 request。

        Step A v2.0 的核心：Step C 看到全量信号，logical_scenarios 以 prompt 建议形式注入，
        Step C 可自由突破场景边界发现跨组关联。

        Args:
            original_request: 原始 OpportunityJudgmentRequest
            all_signals: 全量 enriched_signals
            logical_scenarios: Step A 输出的 LogicalScenario 列表（软建议）
        """
        new_req = OpportunityJudgmentRequest(
            decoded_intelligences=original_request.decoded_intelligences,
            context_packet=original_request.context_packet,
        )
        # 全量信号去重后传入
        new_req._override_signals = self._dedup_signals_by_source(all_signals)
        # 注入场景建议（pipeline 会在 prompt 前插入场景建议前缀）
        if logical_scenarios:
            scenario_hints = []
            for sc in logical_scenarios:
                hint = (
                    f"[场景{sc.scenario_id}] 可能指向：{sc.opportunity_direction} | "
                    f"核心信号：{', '.join(sc.primary_signal_ids)} | "
                    f"依据：{sc.reasoning}"
                )
                scenario_hints.append(hint)
            new_req._scenario_hints = scenario_hints
        return new_req

    def _signal_entry_to_dict(self, entry) -> dict:
        """将 SignalEntry 转换为 enriched_signal dict 格式"""
        return {
            "signal_id":       entry.signal_id,
            "signal_label":    entry.signal_label,
            "signal_type":     entry.signal_type,
            "description":     entry.description,
            "evidence_text":   entry.evidence_text,
            "intensity_score": entry.intensity_score,
            "confidence_score": entry.confidence_score,
            "timeliness_score": entry.timeliness_score,
            "source_id":       entry.source_id,
            "_from_signal_store": True,   # 标记来源
            "_role_annotation": {
                "roles":   entry.roles,
                "needs":   entry.needs,
                "domains": entry.domains,
                "waiting_for_text": entry.waiting_for_text,
            },
        }
