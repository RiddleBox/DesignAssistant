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
        # 注意：api_key=None → 从配置读取；api_key='' → 强制规则引擎模式（不读配置）
        cfg = self._load_llm_config("2.2")
        self.api_key   = cfg.get("api_key", "") if api_key is None else api_key
        self.model     = model or cfg.get("model", "claude-sonnet-4-6")
        self.base_url  = cfg.get("base_url", "https://api.anthropic.com")
        self.max_tokens = cfg.get("max_tokens", 4096)
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
                llm_results = self._llm_judge_v2(enriched_signals, context_packet)
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
        context_packet
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

        raw = self._call_llm(prompt)

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

    def _execute_judgment_pipeline(
        self,
        request: OpportunityJudgmentRequest,
        signals: List[Dict[str, Any]]
    ) -> OpportunityObject:
        """v1 判断流程（保留兼容，新流程走 _execute_judgment_pipeline_v2）"""

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
        signal_summaries = [s.get("description", "") for s in signals if s.get("description")]

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
            summary = signal.get("description", "未知信号")
            supporting.append(f"[{signal_id}] {summary}")

        # 从2.4证据包补充证据（通过 _extract_context_data 统一分拣）
        if context_packet:
            cd = _extract_context_data(context_packet)
            for case in cd["similar_cases"]:
                supporting.append(f"[2.4-evidence] {case}")
            for example in cd["counter_examples"]:
                counter.append(f"[2.4-constraint] {example}")

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
        avg_intensity = sum(s.get("intensity_score", s.get("intensity", 0)) for s in signals) / max(len(signals), 1)
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
        avg_intensity = sum(s.get("intensity_score", s.get("intensity", 0)) for s in signals) / max(signal_count, 1)

        # 检测escalate触发条件：高强度+多信号+竞争压力
        has_urgency = any(
            "竞争" in s.get("description", "") or
            "窗口期" in s.get("description", "") or
            "抢占" in s.get("description", "")
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

    def _infer_why_now(self, signals: List[Dict[str, Any]], priority_level: str) -> str:
        """
        规则引擎 fallback 下，基于信号类型和优先级推断 why_now。
        LLM 模式下此字段由 LLM 直接生成，此处仅作兜底。
        """
        signal_types = list({s.get("signal_type", "") for s in signals})
        type_str = "/".join(t for t in signal_types if t)

        if priority_level == "escalate":
            return f"[规则引擎] 当前 {type_str} 类信号已达升级门槛，时间窗口紧迫，需立即响应"
        elif priority_level == "deep_dive":
            return f"[规则引擎] {type_str} 类信号强度高，有多条交叉验证证据，是深度研究的合适时机"
        elif priority_level == "research":
            return f"[规则引擎] {type_str} 类信号出现，存在后续演化可能，当前适合展开初步研究"
        else:
            return f"[规则引擎] {type_str} 类信号处于观察阶段，暂无明确时机催化剂，持续跟踪"

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用统一 LLM 客户端并解析 JSON 响应"""
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
        import re as _re
        if "```" in text:
            m = _re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
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
                f"summary={signal.get('description', '')}; "
                f"intensity={signal.get('intensity_score', signal.get('intensity', 0))}"
            )

        context_data = _extract_context_data(context_packet)

        prompt = f"""你是 Phase 2.2 机会判断引擎。请基于输入信号输出严格 JSON，不要输出任何额外说明。

职责边界（重要）：
- 信号由 Phase 2.1 粗筛而来，intensity/confidence 是单条信号的自身强度评估
- 你的任务是：把多个信号组装在一起，结合 2.4 的知识证据串联逻辑链，判断是否构成机会
- 单个信号不等于机会；机会需要多信号互相印证 + 2.4 的历史案例/行业知识支撑才可靠

任务：
- 组织 supporting_evidence / counter_evidence / key_assumptions
- 评估 uncertainty_map
- 给出 priority_level（仅允许：watch, research, deep_dive, escalate）
- 给出 next_validation_questions（供 2.3 行动设计使用的关键前置问题；聚焦「2.3 做行动决策前必须回答的问题」，如时效窗口、核心假设是否成立、go/no-go 判断依据；不要写外部信息收集任务）
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
  "next_validation_questions": ["供 2.3 行动决策使用的关键前置问题，如时效窗口/核心假设/go-no-go 依据"]
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
        带 Signal Store 的机会判断入口。

        流程：
          Step A → 批内聚类 + 角色标注
          Step B → 历史信号检索（分层漏斗）
          Step C → 完整机会判断（复用现有 judge()）

        现有 judge() 方法完全保留，本方法是独立的新入口。
        2.1→2.2 输入接口、2.2→2.3 输出接口均不变。

        Args:
            request: 标准 OpportunityJudgmentRequest
            signal_store: SignalStore 实例；None 时自动初始化
            rag_store_add_fn: 可选，黄金模板写入函数；None 时自动尝试加载

        Returns:
            OpportunityJudgmentResult（schema 与 judge() 完全一致）
        """
        import time as _time
        import importlib.util as _ilu
        import sys as _sys
        from datetime import date

        start_time = _time.time()

        # 延迟导入：用 importlib 按绝对路径加载，解决从 run_batch_real.py
        # 调用时 phase2.2_implementation 不在 sys.path 的问题
        _impl_dir = os.path.dirname(os.path.abspath(__file__))

        def _load_sibling(name: str):
            """加载同目录下的兄弟模块，已加载则复用"""
            cache_key = f"_phase22_{name}"
            if cache_key in _sys.modules:
                return _sys.modules[cache_key]
            path = os.path.join(_impl_dir, f"{name}.py")
            spec = _ilu.spec_from_file_location(cache_key, path)
            mod = _ilu.module_from_spec(spec)
            _sys.modules[cache_key] = mod   # 先注册，防止循环 import
            spec.loader.exec_module(mod)
            return mod

        try:
            _ss_mod  = _load_sibling("signal_store")
            _sa_mod  = _load_sibling("step_a_cluster")
            _sb_mod  = _load_sibling("step_b_retrieval")
            _gp_mod  = _load_sibling("golden_pattern")
            SignalStore        = _ss_mod.SignalStore
            build_signal_entry = _ss_mod.build_signal_entry
            run_step_a         = _sa_mod.run_step_a
            run_step_b         = _sb_mod.run_step_b
            maybe_write_golden_pattern = _gp_mod.maybe_write_golden_pattern
        except Exception as e:
            # 任意模块加载失败时，退化为原有 judge()
            print(f"[judge_with_signal_store] 模块加载失败，退化为 judge(): {e}")
            return self.judge(request)

        # 初始化 Signal Store
        if signal_store is None:
            signal_store = SignalStore()

        # 归档过期信号（每次调用时顺带执行，成本极低）
        archived = signal_store.archive_expired()
        if archived:
            print(f"[Signal Store] 归档过期信号 {archived} 条")

        today = date.today().isoformat()

        # ── Step A：批内聚类 + 角色标注 ─────────────────────
        enriched_signals = self._extract_enriched_signals(request.decoded_intelligences)

        if not enriched_signals:
            return self._create_insufficient_evidence_result(
                [], ["没有可用信号"],
                int((_time.time() - start_time) * 1000)
            )

        step_a_result = run_step_a(
            enriched_signals=enriched_signals,
            llm_client=self._llm,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
        )

        if step_a_result.fallback_used:
            print("[Step A] 使用规则 fallback（LLM 未响应）")

        # ── Step C（批内直接组合）────────────────────────────
        all_opportunities = []
        source_signal_map = {}  # opportunity_id → List[SignalEntry]

        for group in step_a_result.signal_groups:
            # 将信号组注入 request，调用现有判断逻辑
            group_request = self._build_group_request(request, group)
            result = self.judge(group_request)
            all_opportunities.extend(result.opportunities or [])
            # 记录信号来源（用于黄金模板）
            for opp in (result.opportunities or []):
                source_signal_map[opp.opportunity_id] = group

        # ── Step B + Step C（孤立信号 → 历史检索）────────────
        signals_to_store = []   # 最终需要写入 Signal Store 的孤立信号

        for iso_signal in step_a_result.isolated_signals:
            step_b_result = run_step_b(
                isolated_signal=iso_signal,
                signal_store=signal_store,
                llm_client=self._llm,
                model=self.model,
            )

            if step_b_result.matched:
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
                        # iso_signal 本身也写入 Signal Store 并标记 matched
                        # 使得：统计准确 + 黄金模板 source_signal_entries 完整
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
        for opp in all_opportunities:
            src_entries = source_signal_map.get(opp.opportunity_id, [])
            if src_entries:
                maybe_write_golden_pattern(
                    opportunity=opp,
                    source_signal_entries=src_entries,
                    rag_store_add_fn=rag_store_add_fn,
                )

        # ── 构建最终结果 ─────────────────────────────────────
        processing_time = int((_time.time() - start_time) * 1000)
        if all_opportunities:
            from schemas import Diagnostics
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
            from schemas import Diagnostics
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
        from schemas import OpportunityJudgmentRequest
        # 将 dict 格式信号包装回 DecodedIntelligence-like 对象
        # 直接传 enriched_signals 格式（_execute_judgment_pipeline_v2 已支持）
        new_req = OpportunityJudgmentRequest(
            decoded_intelligences=original_request.decoded_intelligences,
            context_packet=original_request.context_packet,
        )
        # 临时注入：用信号直接覆盖，让 pipeline 只看这组信号
        # 写入前按 source_id 去重，防止同一来源在同一机会中被重复计数
        new_req._override_signals = self._dedup_signals_by_source(signals)
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
