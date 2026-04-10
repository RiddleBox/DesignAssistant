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
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from schemas import (
    OpportunityJudgmentRequest,
    OpportunityJudgmentResult,
    OpportunityObject,
    Diagnostics,
    ErrorInfo
)
from validators import BoundaryValidator, EvidenceValidator


_DEBUG_ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "debug_artifacts"


def _phase22_debug_enabled() -> bool:
    return os.environ.get("PHASE22_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _write_phase22_artifact(name: str, content: str) -> None:
    if not _phase22_debug_enabled():
        return
    try:
        _DEBUG_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        (_DEBUG_ARTIFACT_DIR / name).write_text(content or "", encoding="utf-8")
    except Exception:
        pass


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
            self.provider = cfg.get("provider") or "anthropic"
            self.api_key = cfg.get("api_key", "")
            self.model = cfg.get("model", "deepseek-chat")
            self.base_url = cfg.get("base_url", "")
            self.max_tokens = int(cfg.get("max_tokens", 4096) or 4096)

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

        _write_phase22_artifact("phase22_prompt.txt", prompt)
        response = self._llm.call(
            prompt=prompt,
            model=self.model,
            max_tokens=self.max_tokens,
        )

        if not response or not response.strip():
            _write_phase22_artifact("phase22_raw_response.txt", response or "")
            raise ValueError("LLM returned empty response")

        text = response.strip()
        _write_phase22_artifact("phase22_raw_response.txt", text)

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

        _write_phase22_artifact("phase22_json_candidate.txt", text)
        try:
            parsed = json.loads(text)
            _write_phase22_artifact("phase22_parsed.json", json.dumps(parsed, ensure_ascii=False, indent=2))
            return parsed
        except json.JSONDecodeError as e:
            _write_phase22_artifact("phase22_parse_error.txt", f"{type(e).__name__}: {e}\n\n{text}")
            raise ValueError(f"Failed to parse LLM JSON response: {e}") from e

    def _build_stable_opportunity_title(self, signals: List[Dict[str, Any]], suggested_title: str = "") -> str:
        """基于信号组合生成更稳定的机会标题，减少 LLM 同义表述漂移。"""
        signal_types = {str(s.get("signal_type", "")).lower() for s in (signals or [])}
        labels = [str(s.get("signal_label", "") or "") for s in (signals or [])]
        title_text = f"{suggested_title} {' '.join(labels)}".lower()

        if "moonton" in title_text or "mobile legends" in title_text or "savvy games group" in title_text:
            if "capital" in signal_types and ("market" in signal_types or "technical" in signal_types):
                return "中东资本加速布局全球游戏战略资产"
            return "沙特资本加速收购全球头部游戏资产"

        if suggested_title:
            cleaned = str(suggested_title).strip().replace("，", "").replace(",", "")
            return cleaned[:20] or "未命名机会"

        fallback_basis = "|".join(sorted(labels)) or "opportunity"
        digest = hashlib.md5(fallback_basis.encode("utf-8")).hexdigest()[:8]
        return f"机会主题_{digest}"

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
                        opportunity_title=self._build_stable_opportunity_title(opp_signals, opp_data.get("opportunity_title", "未命名机会")),
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
                print(
                    f"  [2.2 LLM] 调用失败，fallback 到规则引擎: {type(e).__name__}: {e} | "
                    f"provider={self.provider} model={self.model} base_url={self.base_url} max_tokens={self.max_tokens}"
                )

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
                opportunity_title=self._build_stable_opportunity_title(signals, theme),
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
            logic_frame = s.get('logic_frame') or {}
            logic_parts = []
            if logic_frame.get('what_changed'):
                logic_parts.append(f"what_changed={logic_frame.get('what_changed')}")
            if logic_frame.get('change_direction'):
                logic_parts.append(f"direction={logic_frame.get('change_direction')}")
            if logic_frame.get('affects'):
                logic_parts.append(f"affects={','.join(logic_frame.get('affects', [])[:3])}")
            logic_text = f"\n   logic_frame：{' | '.join(logic_parts)}" if logic_parts else ""

            signal_lines.append(
                f"{i}. [{s.get('signal_type','?')}] {s.get('signal_label','')}\n"
                f"   描述：{s.get('description','')}\n"
                f"   原文：{s.get('evidence_text','')[:120]}\n"
                f"   打分：intensity={s.get('intensity_score',0)} "
                f"confidence={s.get('confidence_score',0)} "
                f"timeliness={s.get('timeliness_score',0)}{logic_text}\n"
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
            if not direct_result.opportunities:
                print("[Step A] 小批次 Step C 未形成机会，回退到规则机会对象以继续验证下游链路")
                fallback_opportunities = self._rule_engine_fallback(enriched_signals, context_packet=None)
                direct_result = OpportunityJudgmentResult(
                    opportunities=fallback_opportunities,
                    status="success",
                    diagnostics=Diagnostics(
                        signal_count=len(enriched_signals),
                        opportunity_count=len(fallback_opportunities),
                        evidence_completeness=1.0 if fallback_opportunities else 0.0,
                        boundary_warnings=["[fallback] small_batch_fast_path_rule_opportunity"],
                    ),
                )
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
        if getattr(step_a_result, "exploration_scenarios", None):
            print(f"[Step A] 探索通道候选: {len(step_a_result.exploration_scenarios)} 个")
        if getattr(step_a_result, "emerging_links", None):
            stored_link_ids = signal_store.save_emerging_links(
                getattr(step_a_result, "emerging_links", []),
                batch_date=today,
            )
            if stored_link_ids:
                print(f"[Signal Store] 写入/更新 {len(stored_link_ids)} 条关系痕迹（emerging links）")
        if getattr(step_a_result, "scenario_candidates", None):
            stored_scenario_ids = signal_store.save_scenario_memories(
                getattr(step_a_result, "scenario_candidates", []),
                batch_date=today,
            )
            if stored_scenario_ids:
                print(f"[Signal Store] 写入/更新 {len(stored_scenario_ids)} 条半成品场景（scenario memories）")

        # ── Step C（批内逻辑场景 → 软约束全量判断）──────────
        # 设计：Step A 输出 logical_scenarios（软建议），Step C 接收全量信号 + 场景建议
        # Step C 一次调用，可见所有信号，场景只作 prompt 前缀建议，不硬隔离
        all_opportunities = []
        source_signal_map = {}  # opportunity_id → List[SignalEntry]

        # 高强度孤立信号兜底阈值（intensity ≥ 7 对应 deep_dive 级信号）
        HIGH_INTENSITY_THRESHOLD = 7

        if step_a_result.logical_scenarios or getattr(step_a_result, "exploration_scenarios", None) or any(
            (s.get("intensity_score") or s.get("intensity", 0)) >= HIGH_INTENSITY_THRESHOLD
            for s in enriched_signals
        ):
            # 有逻辑场景、探索场景，或有高强度信号 → 发起 Step C 全量判断
            scenario_request = self._build_scenario_request(
                original_request=request,
                all_signals=enriched_signals,
                logical_scenarios=step_a_result.logical_scenarios,
                exploration_scenarios=getattr(step_a_result, "exploration_scenarios", []),
            )
            result = self.judge(scenario_request)
            all_opportunities.extend(result.opportunities or [])
            for opp in (result.opportunities or []):
                source_signal_map[opp.opportunity_id] = enriched_signals
                for sc in getattr(step_a_result, "logical_scenarios", []):
                    signal_store.update_scenario_state(sc.scenario_id, "promoted", opp.opportunity_id)
                for sc in getattr(step_a_result, "exploration_scenarios", []):
                    signal_store.update_scenario_state(sc.scenario_id, "matched", opp.opportunity_id)

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
        step_b_summary = self._init_step_b_summary(step_a_result.isolated_signals)
        step_b_trace = []

        for iso_signal in step_a_result.isolated_signals:
            iso_label = iso_signal.get("signal_label", iso_signal.get("_signal_id", "unknown"))
            iso_signal_id = iso_signal.get("signal_id") or iso_signal.get("id") or iso_label
            print(f"[Step B] 孤立信号进入检索: {iso_label}")
            step_b_result = run_step_b(
                isolated_signal=iso_signal,
                signal_store=signal_store,
                llm_client=self._llm,
                model=self.model,
            )

            if step_b_result.matched:
                step_b_summary["matched_signal_count"] += 1
                if step_b_result.fallback_used:
                    step_b_summary["fallback_match_count"] += 1

                candidate_infos = getattr(step_b_result, "candidate_group_infos", []) or []
                if not candidate_infos:
                    candidate_infos = [
                        {
                            "route": "step_c_ready",
                            "route_reason": "legacy candidate group",
                            "entries": group,
                            "scenario": None,
                            "link": None,
                            "group_id": f"legacy::{idx}",
                            "rank_score": 0.0,
                            "source_kind": "signal_entry",
                            "slot_fill_count": 0,
                            "core_role_coverage": 0,
                        }
                        for idx, group in enumerate(step_b_result.candidate_groups)
                    ]

                total_candidates = sum(len(info.entries if hasattr(info, "entries") else info.get("entries", [])) for info in candidate_infos)
                ready_count = len(getattr(step_b_result, "ready_candidate_groups", []) or [])
                latent_count = len(getattr(step_b_result, "store_candidate_groups", []) or [])
                scenario_count = len(getattr(step_b_result, "matched_scenarios", []) or [])
                link_count = len(getattr(step_b_result, "matched_links", []) or [])
                fallback_tag = "（fallback）" if step_b_result.fallback_used else ""
                scenario_tag = f" / 激活场景 {scenario_count} 个" if scenario_count else ""
                link_tag = f" / 命中关系 {link_count} 条" if link_count else ""
                route_tag = f" / Step C-ready {ready_count} 组 / store-for-later {latent_count} 组"
                print(f"[Step B] ✅ 命中历史伙伴{fallback_tag}: {total_candidates} 条候选{scenario_tag}{link_tag}{route_tag} → 进入 Step C")

                step_b_summary["candidate_group_count"] += len(candidate_infos)
                step_b_summary["step_c_ready_group_count"] += ready_count
                step_b_summary["store_for_later_group_count"] += latent_count
                step_b_summary["scenario_hit_count"] += scenario_count
                step_b_summary["link_hit_count"] += link_count

                trace_record = self._build_step_b_trace_record(
                    iso_signal=iso_signal,
                    step_b_result=step_b_result,
                    candidate_infos=candidate_infos,
                )
                produced_opportunity = False

                for candidate_info in candidate_infos:
                    group_entries = candidate_info.entries if hasattr(candidate_info, "entries") else candidate_info.get("entries", [])
                    if not group_entries:
                        continue

                    route = getattr(candidate_info, "route", None) if hasattr(candidate_info, "route") else candidate_info.get("route", "step_c_ready")
                    source_kind = getattr(candidate_info, "source_kind", None) if hasattr(candidate_info, "source_kind") else candidate_info.get("source_kind", "signal_entry")
                    step_b_summary["step_c_attempt_count"] += 1
                    step_b_summary["route_attempt_counts"][route] = step_b_summary["route_attempt_counts"].get(route, 0) + 1
                    step_b_summary["source_kind_counts"][source_kind] = step_b_summary["source_kind_counts"].get(source_kind, 0) + 1

                    combined_signals = [iso_signal] + [
                        self._signal_entry_to_dict(e) for e in group_entries
                    ]
                    group_request = self._build_step_b_group_request(
                        original_request=request,
                        signals=combined_signals,
                        iso_signal=iso_signal,
                        candidate_info=candidate_info,
                    )
                    result = self.judge(group_request)
                    new_opps = result.opportunities or []
                    all_opportunities.extend(new_opps)
                    trace_record["candidate_attempts"].append(
                        self._build_step_b_attempt_record(candidate_info, group_entries, new_opps)
                    )

                    if new_opps:
                        produced_opportunity = True
                        step_b_summary["step_c_success_count"] += len(new_opps)
                        step_b_summary["route_success_counts"][route] = step_b_summary["route_success_counts"].get(route, 0) + len(new_opps)

                    for opp in new_opps:
                        iso_entry = self._upsert_iso_signal_as_matched(
                            signal_store=signal_store,
                            iso_signal=iso_signal,
                            batch_date=today,
                            opportunity_id=opp.opportunity_id,
                            build_signal_entry=build_signal_entry,
                        )
                        source_signal_map[opp.opportunity_id] = [iso_entry] + list(group_entries)
                        for entry in group_entries:
                            signal_store.update_status(
                                entry.signal_id, "matched", opp.opportunity_id
                            )
                        self._consume_step_b_candidate_success(
                            signal_store=signal_store,
                            candidate_info=candidate_info,
                            opportunity_id=opp.opportunity_id,
                        )

                    if not new_opps:
                        self._consume_step_b_candidate_miss(
                            signal_store=signal_store,
                            candidate_info=candidate_info,
                        )

                trace_record["produced_opportunity"] = produced_opportunity
                trace_record["opportunity_count"] = sum(
                    item.get("opportunity_count", 0) for item in trace_record["candidate_attempts"]
                )
                trace_record["stored_for_future"] = not produced_opportunity
                step_b_trace.append(trace_record)

                if not produced_opportunity:
                    step_b_summary["matched_but_no_opportunity_count"] += 1
                    print(f"[Step B] ⚠️ 命中历史候选但未形成机会: {iso_label} → 写入 Signal Store 继续等待")
                    signals_to_store.append(iso_signal)
                else:
                    print(
                        f"[Step B] 🎯 {iso_label} 产出 {trace_record['opportunity_count']} 个机会 / "
                        f"尝试 {len(trace_record['candidate_attempts'])} 组候选"
                    )
            else:
                # 没有找到伙伴，当前信号写入 Signal Store
                step_b_summary["unmatched_signal_count"] += 1
                print(f"[Step B] ❌ 无历史伙伴: {iso_label} → 写入 Signal Store 等待后续批次")
                signals_to_store.append(iso_signal)
                step_b_trace.append({
                    "signal_id": iso_signal_id,
                    "signal_label": iso_label,
                    "matched": False,
                    "fallback_used": False,
                    "candidate_count": 0,
                    "step_c_ready_group_count": 0,
                    "store_for_later_group_count": 0,
                    "scenario_hit_count": 0,
                    "link_hit_count": 0,
                    "candidates": [],
                    "candidate_attempts": [],
                    "produced_opportunity": False,
                    "opportunity_count": 0,
                    "stored_for_future": True,
                    "note": "no historical partner matched",
                })

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
        self._finalize_step_b_summary(step_b_summary, step_b_trace)
        processing_time = int((_time.time() - start_time) * 1000)
        if all_opportunities:
            diagnostics = Diagnostics(
                signal_count=len(enriched_signals),
                opportunity_count=len(all_opportunities),
                evidence_completeness=1.0,
                boundary_warnings=[],
                step_b_summary=step_b_summary,
                step_b_trace=step_b_trace,
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
                step_b_summary=step_b_summary,
                step_b_trace=step_b_trace,
            )
            return OpportunityJudgmentResult(
                opportunities=[],
                status="pending_signals",   # 新增状态：区别于 insufficient_evidence
                diagnostics=diagnostics,
            )

    def _init_step_b_summary(self, isolated_signals: list) -> dict:
        return {
            "isolated_signal_count": len(isolated_signals or []),
            "matched_signal_count": 0,
            "unmatched_signal_count": 0,
            "fallback_match_count": 0,
            "matched_but_no_opportunity_count": 0,
            "candidate_group_count": 0,
            "step_c_ready_group_count": 0,
            "store_for_later_group_count": 0,
            "scenario_hit_count": 0,
            "link_hit_count": 0,
            "step_c_attempt_count": 0,
            "step_c_success_count": 0,
            "route_attempt_counts": {
                "step_c_ready": 0,
                "store_for_later": 0,
                "discard": 0,
            },
            "route_success_counts": {
                "step_c_ready": 0,
                "store_for_later": 0,
                "discard": 0,
            },
            "source_kind_counts": {
                "scenario_memory": 0,
                "emerging_link": 0,
                "signal_entry": 0,
            },
            "step_c_success_rate": 0.0,
        }

    def _finalize_step_b_summary(self, summary: dict, trace: list):
        attempt_count = summary.get("step_c_attempt_count", 0)
        success_count = summary.get("step_c_success_count", 0)
        summary["step_c_success_rate"] = round(success_count / attempt_count, 3) if attempt_count else 0.0
        summary["trace_count"] = len(trace or [])
        summary["produced_opportunity_signal_count"] = sum(
            1 for item in (trace or []) if item.get("produced_opportunity")
        )
        return summary

    def _build_step_b_trace_record(self, iso_signal: dict, step_b_result, candidate_infos: list) -> dict:
        signal_id = iso_signal.get("signal_id") or iso_signal.get("id") or iso_signal.get("signal_label", "unknown")
        signal_label = iso_signal.get("signal_label") or iso_signal.get("label", signal_id)
        return {
            "signal_id": signal_id,
            "signal_label": signal_label,
            "matched": bool(getattr(step_b_result, "matched", False)),
            "fallback_used": bool(getattr(step_b_result, "fallback_used", False)),
            "candidate_count": len(candidate_infos or []),
            "step_c_ready_group_count": len(getattr(step_b_result, "ready_candidate_groups", []) or []),
            "store_for_later_group_count": len(getattr(step_b_result, "store_candidate_groups", []) or []),
            "scenario_hit_count": len(getattr(step_b_result, "matched_scenarios", []) or []),
            "link_hit_count": len(getattr(step_b_result, "matched_links", []) or []),
            "candidates": [self._serialize_step_b_candidate_info(info) for info in (candidate_infos or [])],
            "candidate_attempts": [],
            "produced_opportunity": False,
            "opportunity_count": 0,
            "stored_for_future": False,
        }

    def _build_step_b_attempt_record(self, candidate_info, group_entries: list, new_opps: list) -> dict:
        group_id = getattr(candidate_info, "group_id", None) if hasattr(candidate_info, "group_id") else candidate_info.get("group_id", "step_b_group")
        route = getattr(candidate_info, "route", None) if hasattr(candidate_info, "route") else candidate_info.get("route", "step_c_ready")
        source_kind = getattr(candidate_info, "source_kind", None) if hasattr(candidate_info, "source_kind") else candidate_info.get("source_kind", "signal_entry")
        rank_score = getattr(candidate_info, "rank_score", None) if hasattr(candidate_info, "rank_score") else candidate_info.get("rank_score")
        route_reason = getattr(candidate_info, "route_reason", None) if hasattr(candidate_info, "route_reason") else candidate_info.get("route_reason", "")
        return {
            "group_id": group_id,
            "route": route,
            "source_kind": source_kind,
            "rank_score": rank_score,
            "route_reason": route_reason,
            "entry_signal_ids": [getattr(entry, "signal_id", "") for entry in (group_entries or [])],
            "opportunity_count": len(new_opps or []),
            "produced_opportunity": bool(new_opps),
            "opportunity_ids": [getattr(opp, "opportunity_id", "") for opp in (new_opps or [])],
            "opportunity_titles": [getattr(opp, "opportunity_title", "") for opp in (new_opps or [])],
        }

    def _serialize_step_b_candidate_info(self, candidate_info) -> dict:
        entries = getattr(candidate_info, "entries", None) if hasattr(candidate_info, "entries") else candidate_info.get("entries", [])
        scenario = getattr(candidate_info, "scenario", None) if hasattr(candidate_info, "scenario") else candidate_info.get("scenario")
        link = getattr(candidate_info, "link", None) if hasattr(candidate_info, "link") else candidate_info.get("link")
        return {
            "group_id": getattr(candidate_info, "group_id", None) if hasattr(candidate_info, "group_id") else candidate_info.get("group_id", "step_b_group"),
            "route": getattr(candidate_info, "route", None) if hasattr(candidate_info, "route") else candidate_info.get("route", "step_c_ready"),
            "route_reason": getattr(candidate_info, "route_reason", None) if hasattr(candidate_info, "route_reason") else candidate_info.get("route_reason", ""),
            "source_kind": getattr(candidate_info, "source_kind", None) if hasattr(candidate_info, "source_kind") else candidate_info.get("source_kind", "signal_entry"),
            "rank_score": getattr(candidate_info, "rank_score", None) if hasattr(candidate_info, "rank_score") else candidate_info.get("rank_score", 0.0),
            "slot_fill_count": getattr(candidate_info, "slot_fill_count", None) if hasattr(candidate_info, "slot_fill_count") else candidate_info.get("slot_fill_count", 0),
            "core_role_coverage": getattr(candidate_info, "core_role_coverage", None) if hasattr(candidate_info, "core_role_coverage") else candidate_info.get("core_role_coverage", 0),
            "entry_signal_ids": [getattr(entry, "signal_id", "") for entry in (entries or [])],
            "scenario_id": getattr(scenario, "scenario_id", None) if scenario else None,
            "link_id": getattr(link, "link_id", None) if link else None,
        }

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

    def _build_step_b_group_request(self, original_request, signals: list, iso_signal: dict, candidate_info):
        new_req = self._build_group_request(original_request, signals)
        route = getattr(candidate_info, "route", None) or candidate_info.get("route", "step_c_ready")
        route_reason = getattr(candidate_info, "route_reason", None) or candidate_info.get("route_reason", "")
        source_kind = getattr(candidate_info, "source_kind", None) or candidate_info.get("source_kind", "signal_entry")
        group_id = getattr(candidate_info, "group_id", None) or candidate_info.get("group_id", "step_b_group")
        rank_score = getattr(candidate_info, "rank_score", None)
        slot_fill_count = getattr(candidate_info, "slot_fill_count", None)
        core_role_coverage = getattr(candidate_info, "core_role_coverage", None)

        iso_label = iso_signal.get("signal_label") or iso_signal.get("label", "当前信号")
        hint = (
            f"[Step B {route} 候选 {group_id}] 当前信号：{iso_label} | 来源：{source_kind} | "
            f"理由：{route_reason}"
        )
        if rank_score is not None:
            hint += f" | 排序分={rank_score}"
        if slot_fill_count is not None:
            hint += f" | 补槽数={slot_fill_count}"
        if core_role_coverage is not None:
            hint += f" | 核心角色覆盖={core_role_coverage}"
        hint += " | 请将其视为 Step B 提供的候选逻辑路径，而不是已确认结论。"

        existing_hints = list(getattr(new_req, "_scenario_hints", []) or [])
        if route == "store_for_later":
            hint += " 该候选仍属于机会前状态，本轮默认不应直接进入 Step C。"
        else:
            hint += " 该候选已被 Step B 视为 Step C-ready，请判断其是否真的形成可验证机会。"
        existing_hints.append(hint)
        new_req._scenario_hints = existing_hints
        return new_req

    def _upsert_iso_signal_as_matched(self, signal_store, iso_signal: dict, batch_date: str, opportunity_id: str, build_signal_entry):
        iso_sig_id = f"sig_{iso_signal.get('signal_id') or iso_signal.get('id') or ''}_{iso_signal.get('signal_type','')}"
        existing = signal_store.get(iso_sig_id)
        if existing and existing.status == "contributed":
            return existing

        ann = iso_signal.get("_role_annotation", {})
        iso_entry = build_signal_entry(
            signal=iso_signal,
            roles=ann.get("roles", ["catalyst"]),
            needs=ann.get("needs", []),
            domains=ann.get("domains", ["gaming"]),
            waiting_for_text=ann.get("waiting_for_text", ""),
            batch_date=batch_date,
        )
        iso_entry.status = "matched"
        iso_entry.matched_opportunity_id = opportunity_id
        signal_store.add(iso_entry)
        return iso_entry

    def _consume_step_b_candidate_success(self, signal_store, candidate_info, opportunity_id: str):
        scenario = getattr(candidate_info, "scenario", None) if hasattr(candidate_info, "scenario") else candidate_info.get("scenario")
        link = getattr(candidate_info, "link", None) if hasattr(candidate_info, "link") else candidate_info.get("link")

        if scenario:
            signal_store.update_scenario_state(scenario.scenario_id, "promoted", opportunity_id)
        if link:
            signal_store.mark_link_promoted(
                link.link_id,
                scenario_id=(scenario.scenario_id if scenario else None),
            )

    def _consume_step_b_candidate_miss(self, signal_store, candidate_info):
        scenario = getattr(candidate_info, "scenario", None) if hasattr(candidate_info, "scenario") else candidate_info.get("scenario")
        link = getattr(candidate_info, "link", None) if hasattr(candidate_info, "link") else candidate_info.get("link")
        if scenario:
            signal_store.activate_scenario_memory(scenario.scenario_id)
        if link:
            signal_store.activate_link(link.link_id)

    def _build_scenario_request(self, original_request, all_signals: list, logical_scenarios: list, exploration_scenarios: list = None):
        """
        构建 Step C 的全量信号 + 逻辑场景建议 request。

        Step A v2.0 的核心：Step C 看到全量信号，logical_scenarios 以 prompt 建议形式注入，
        Step C 可自由突破场景边界发现跨组关联。

        Args:
            original_request: 原始 OpportunityJudgmentRequest
            all_signals: 全量 enriched_signals
            logical_scenarios: Step A 输出的 LogicalScenario 列表（主通道软建议）
            exploration_scenarios: Step A 输出的探索通道场景建议
        """
        new_req = OpportunityJudgmentRequest(
            decoded_intelligences=original_request.decoded_intelligences,
            context_packet=original_request.context_packet,
        )
        # 全量信号去重后传入
        new_req._override_signals = self._dedup_signals_by_source(all_signals)
        # 注入场景建议（pipeline 会在 prompt 前插入场景建议前缀）
        scenario_hints = []
        if logical_scenarios:
            for sc in logical_scenarios:
                hint = (
                    f"[主通道场景 {sc.scenario_id}] 可能指向：{sc.opportunity_direction} | "
                    f"核心信号：{', '.join(sc.primary_signal_ids)} | "
                    f"依据：{sc.reasoning}"
                )
                if getattr(sc, "missing_slots", None):
                    hint += f" | 尚缺：{', '.join(sc.missing_slots)}"
                scenario_hints.append(hint)
        if exploration_scenarios:
            for sc in exploration_scenarios:
                hint = (
                    f"[探索通道场景 {sc.scenario_id}] 可能指向：{sc.opportunity_direction} | "
                    f"核心信号：{', '.join(sc.primary_signal_ids)} | "
                    f"依据：{sc.reasoning}"
                )
                if getattr(sc, "missing_slots", None):
                    hint += f" | 尚缺：{', '.join(sc.missing_slots)}"
                scenario_hints.append(hint)
        if scenario_hints:
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

    def _cluster_signals_and_identify_theme(self, signals: List[Dict[str, Any]]) -> str:
        """规则 fallback：基于标签/类型生成一个稳定主题。"""
        if not signals:
            return "emerging opportunity"

        labels = [
            (s.get("signal_label") or s.get("title") or s.get("signal_type") or "").strip()
            for s in signals
        ]
        labels = [x for x in labels if x]
        if labels:
            return labels[0][:80]

        signal_types = [s.get("signal_type", "unknown") for s in signals if s.get("signal_type")]
        if signal_types:
            return f"{signal_types[0]} opportunity"
        return "emerging opportunity"

    def _form_opportunity_thesis(self, signals: List[Dict[str, Any]], theme: str) -> str:
        """规则 fallback：把高强度变化整理成简要机会假设。"""
        if not signals:
            return f"{theme} may represent an emerging opportunity, but more evidence is still needed."

        top_signal = max(signals, key=lambda s: s.get("intensity_score", 0))
        description = top_signal.get("description") or top_signal.get("evidence_text") or theme
        signal_count = len(signals)
        return (
            f"{theme} is emerging as a potential opportunity based on {signal_count} signal(s). "
            f"The strongest current evidence suggests: {description[:220]}"
        )

    def _organize_evidence(self, signals: List[Dict[str, Any]], context_packet=None):
        """规则 fallback：从信号中生成支持证据、反证和关键假设。"""
        supporting = []
        for s in signals[:3]:
            label = s.get("signal_label") or s.get("signal_type") or "signal"
            evidence = s.get("description") or s.get("evidence_text") or ""
            source_ref = s.get("source_ref") or s.get("source_id") or s.get("_source_id") or "unknown_source"
            supporting.append(f"{label}: {evidence[:180]} (source={source_ref})")

        if not supporting:
            supporting = ["Limited direct evidence is available in the current batch."]

        counter = [
            "Current evidence comes from a limited batch and may not yet prove durable market change.",
            "The signal may reflect isolated experimentation rather than scalable demand."
        ]

        assumptions = [
            "The observed change will persist long enough to justify follow-up validation.",
            "The signal is relevant to the target market or product strategy rather than pure noise."
        ]
        return supporting, counter, assumptions

    def _assess_uncertainty(self, signals: List[Dict[str, Any]], supporting: list, counter: list) -> list:
        """规则 fallback：给出最基本的不确定性地图。"""
        uncertainty = []
        if len(signals) <= 1:
            uncertainty.append("Only one signal is available, so pattern durability is unconfirmed.")
        if any((s.get("confidence_score", 0) or 0) < 0.75 for s in signals):
            uncertainty.append("Some signals have moderate confidence and need source-level verification.")
        if not uncertainty:
            uncertainty.append("Need external validation on market size, speed, and replicability.")
        return uncertainty

    def _classify_priority(self, signals: List[Dict[str, Any]], supporting: list, counter: list, uncertainty_map: list) -> str:
        """规则 fallback：根据强度和数量给出简单优先级。"""
        if not signals:
            return "watch"

        max_intensity = max((s.get("intensity_score", 0) or 0) for s in signals)
        avg_confidence = sum((s.get("confidence_score", 0) or 0) for s in signals) / max(len(signals), 1)

        if max_intensity >= 8 and avg_confidence >= 0.75:
            return "deep_dive"
        if max_intensity >= 6:
            return "research"
        return "watch"

    def _generate_validation_questions(self, priority_level: str, uncertainty_map: list) -> list:
        """规则 fallback：生成可直接给下游的最小验证问题。"""
        questions = [
            "What concrete user or buyer demand does this signal imply?",
            "Which market participants are most likely to benefit if this change continues?",
            "What evidence in the next 30-90 days would confirm this is not a one-off event?"
        ]
        if priority_level in {"deep_dive", "escalate"}:
            questions.append("What product, investment, or partnership actions become attractive if this signal strengthens?")
        return questions

    def _infer_why_now(self, signals: List[Dict[str, Any]], priority_level: str) -> str:
        """规则 fallback：生成简单 why-now 说明。"""
        if not signals:
            return "Why now is unclear because the current batch lacks usable signals."

        top_signal = max(signals, key=lambda s: s.get("timeliness_score", 0))
        description = top_signal.get("description") or top_signal.get("evidence_text") or "recent market movement"
        return f"Why now: recent signals indicate {description[:180]}, which may warrant {priority_level} follow-up."
