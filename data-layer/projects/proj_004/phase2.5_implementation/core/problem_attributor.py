"""
Phase 2.5 Problem Attributor

问题归因器：把链路运行暴露的问题组织为可解释、可追踪、层级化的归因结构。

归因策略（两层）：
1. LLM 语义归因（主路径）：由 LLMAttributor 分析完整链路输出，识别语义层失真点
2. 规则归因（fallback）：LLM 不可用或失败时，基于字段存在性 + 枚举比对做基础归因

设计原则：
- 归因必须有证据：每条 SuspectedRootCause 必须引用具体字段值
- 不确定性显式表达：不能把"怀疑"写成"确定"
- 不重做上游职责：只定位问题所在层级，不在 2.5 内修复
"""

from typing import List, Dict, Any, Tuple, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    CriticalFinding,
    SuspectedRootCause,
    OutputCheck,
    SeverityLevel,
    AttributionLayer,
    ConfidenceLevel,
    CheckStatus,
)
from core.llm_attributor import LLMAttributor


class ProblemAttributor:
    """
    问题归因器

    主路径：LLM 语义归因
    Fallback：规则归因（字段检查 + 枚举比对）
    """

    def __init__(self):
        self.finding_counter = 0
        self.cause_counter = 0
        self.llm_attributor = LLMAttributor()

    def attribute_problems(
        self,
        output_checks: List[OutputCheck],
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any],
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """
        执行问题归因。

        Args:
            output_checks: OutputChecker 的规则检查结果（作为 LLM 的补充上下文）
            workflow_run_record: 链路运行记录
            upstream_outputs: 上游模块输出字典

        Returns:
            (关键发现列表, 初步归因列表)
        """
        # 把规则检查结果转为摘要字符串，注入 LLM 上下文
        checks_summary = [
            f"[{c.check_type.value}] {c.status.value}: {c.details}"
            for c in output_checks
            if c.status != CheckStatus.PASS
        ]

        # ── 主路径：LLM 语义归因
        if self.llm_attributor.available:
            llm_result = self.llm_attributor.attribute(
                upstream_outputs=upstream_outputs,
                output_checks_summary=checks_summary,
                workflow_run_record=workflow_run_record,
            )
            if llm_result is not None:
                findings, causes = self._parse_llm_result(llm_result)
                # 补充运行时错误（规则检测，不依赖语义）
                rt_findings, rt_causes = self._detect_runtime_errors(workflow_run_record)
                return findings + rt_findings, causes + rt_causes

        # ── Fallback：规则归因
        print("[INFO] ProblemAttributor: 使用规则 fallback 归因")
        return self._rule_based_attribution(output_checks, workflow_run_record, upstream_outputs)

    # ─────────────────────────────────────────
    # LLM 结果解析
    # ─────────────────────────────────────────

    def _parse_llm_result(
        self,
        llm_result: Dict[str, Any],
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """把 LLM 返回的 dict 列表转换为 pydantic 对象"""
        findings = []
        causes = []

        severity_map = {
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
        }
        layer_map = {
            "signal": AttributionLayer.SIGNAL,
            "opportunity": AttributionLayer.OPPORTUNITY,
            "action": AttributionLayer.ACTION,
            "context": AttributionLayer.CONTEXT,
            "orchestration": AttributionLayer.ORCHESTRATION,
            "validation": AttributionLayer.VALIDATION,
        }
        confidence_map = {
            "high_confidence": ConfidenceLevel.HIGH_CONFIDENCE,
            "medium_confidence": ConfidenceLevel.MEDIUM_CONFIDENCE,
            "low_confidence": ConfidenceLevel.LOW_CONFIDENCE,
        }

        for f in llm_result.get("critical_findings", []):
            try:
                self.finding_counter += 1
                findings.append(CriticalFinding(
                    finding_id=f.get("finding_id", f"finding_{self.finding_counter:03d}"),
                    summary=f.get("summary", "（LLM 归因未提供摘要）"),
                    severity=severity_map.get(f.get("severity", "medium"), SeverityLevel.MEDIUM),
                    layer=layer_map.get(f.get("layer", "orchestration"), AttributionLayer.ORCHESTRATION),
                    evidence=f.get("evidence", []) or ["（LLM 归因未提供证据）"],
                    impact=f.get("impact", ""),
                ))
            except Exception as e:
                print(f"[WARN] finding 解析失败（跳过）：{e}")

        for c in llm_result.get("suspected_root_causes", []):
            try:
                self.cause_counter += 1
                causes.append(SuspectedRootCause(
                    cause_id=c.get("cause_id", f"cause_{self.cause_counter:03d}"),
                    suspected_root_cause=c.get("suspected_root_cause", ""),
                    confidence=confidence_map.get(
                        c.get("confidence", "medium_confidence"),
                        ConfidenceLevel.MEDIUM_CONFIDENCE,
                    ),
                    reasoning=c.get("reasoning", ""),
                    evidence=c.get("evidence", []),
                    limitations=c.get("limitations", []),
                    related_findings=c.get("related_findings", []),
                ))
            except Exception as e:
                print(f"[WARN] cause 解析失败（跳过）：{e}")

        return findings, causes

    # ─────────────────────────────────────────
    # 运行时错误检测（规则，不依赖语义）
    # ─────────────────────────────────────────

    def _detect_runtime_errors(
        self,
        workflow_run_record: Dict[str, Any],
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """检测运行时错误和性能异常，不依赖 LLM"""
        findings = []
        causes = []

        errors = workflow_run_record.get("errors", [])
        if errors:
            self.finding_counter += 1
            self.cause_counter += 1
            fid = f"finding_{self.finding_counter:03d}"
            findings.append(CriticalFinding(
                finding_id=fid,
                summary=f"运行时错误：{len(errors)} 个模块执行异常",
                severity=SeverityLevel.HIGH,
                layer=AttributionLayer.ORCHESTRATION,
                evidence=[str(e) for e in errors[:3]],
                impact="运行时错误可能导致部分模块输出缺失或不可信",
            ))
            causes.append(SuspectedRootCause(
                cause_id=f"cause_{self.cause_counter:03d}",
                suspected_root_cause="模块执行过程中出现异常，可能是输入格式不符或接口调用失败",
                confidence=ConfidenceLevel.HIGH_CONFIDENCE,
                reasoning=f"直接观察到 {len(errors)} 个运行时错误记录",
                evidence=[str(e) for e in errors[:3]],
                limitations=[],
                related_findings=[fid],
            ))

        processing_time = workflow_run_record.get("processing_time_ms", 0)
        if processing_time > 120_000:  # 超过 2 分钟
            self.finding_counter += 1
            self.cause_counter += 1
            fid = f"finding_{self.finding_counter:03d}"
            findings.append(CriticalFinding(
                finding_id=fid,
                summary=f"耗时异常：总处理时间 {processing_time // 1000}s，超过预期阈值",
                severity=SeverityLevel.MEDIUM,
                layer=AttributionLayer.ORCHESTRATION,
                evidence=[f"processing_time_ms={processing_time}"],
                impact="耗时过长可能影响实时性，也可能暗示某模块存在重试或阻塞",
            ))
            causes.append(SuspectedRootCause(
                cause_id=f"cause_{self.cause_counter:03d}",
                suspected_root_cause="可能某模块存在 LLM 调用重试或网络延迟，需查看各模块耗时分布",
                confidence=ConfidenceLevel.LOW_CONFIDENCE,
                reasoning=f"总耗时 {processing_time}ms 超过 120s 阈值，但无模块级耗时数据",
                evidence=[f"processing_time_ms={processing_time}"],
                limitations=["缺少各模块级耗时数据，无法定位具体瓶颈"],
                related_findings=[fid],
            ))

        return findings, causes

    # ─────────────────────────────────────────
    # 规则归因（fallback）
    # ─────────────────────────────────────────

    def _rule_based_attribution(
        self,
        output_checks: List[OutputCheck],
        workflow_run_record: Dict[str, Any],
        upstream_outputs: Dict[str, Any],
    ) -> Tuple[List[CriticalFinding], List[SuspectedRootCause]]:
        """规则归因：LLM 不可用时的 fallback"""
        findings = []
        causes = []

        for check in output_checks:
            if check.status in [CheckStatus.WARNING, CheckStatus.FAIL]:
                f, c = self._rule_attribute_check(check, upstream_outputs)
                if f:
                    findings.append(f)
                if c:
                    causes.append(c)

        rt_f, rt_c = self._detect_runtime_errors(workflow_run_record)
        findings.extend(rt_f)
        causes.extend(rt_c)

        return findings, causes

    def _rule_attribute_check(
        self,
        check: OutputCheck,
        upstream_outputs: Dict[str, Any],
    ) -> Tuple[Optional[CriticalFinding], Optional[SuspectedRootCause]]:
        """单条规则归因"""
        self.finding_counter += 1
        self.cause_counter += 1
        fid = f"finding_{self.finding_counter:03d}"

        severity = SeverityLevel.HIGH if check.status == CheckStatus.FAIL else SeverityLevel.MEDIUM

        # 归因层级：根据 details 中的关键词猜测
        details = check.details.lower()
        if "2.1" in details or "signal" in details:
            layer = AttributionLayer.SIGNAL
            cause_text = "信号提取阶段可能遗漏关键信息或字段缺失"
        elif "2.2" in details or "opportunit" in details:
            layer = AttributionLayer.OPPORTUNITY
            cause_text = "机会判断阶段可能未完整生成必需字段"
        elif "2.3" in details or "action" in details or "posture" in details:
            layer = AttributionLayer.ACTION
            cause_text = "行动设计阶段可能未完整生成必需字段"
        elif "2.4" in details or "rag" in details or "retriev" in details:
            layer = AttributionLayer.CONTEXT
            cause_text = "知识检索可能未生效（fallback 跳过）"
        else:
            layer = AttributionLayer.ORCHESTRATION
            cause_text = "模块协作或接口传递可能导致信息丢失"

        finding = CriticalFinding(
            finding_id=fid,
            summary=f"[规则检测] {check.check_type.value} 问题：{check.details}",
            severity=severity,
            layer=layer,
            evidence=check.evidence or ["（规则检测无直接证据）"],
            impact="缺失字段可能导致下游判断或行动设计无法正常进行",
        )
        cause = SuspectedRootCause(
            cause_id=f"cause_{self.cause_counter:03d}",
            suspected_root_cause=cause_text,
            confidence=ConfidenceLevel.LOW_CONFIDENCE,
            reasoning=f"基于规则检查推断：{check.details}（注：LLM 归因不可用，结论可信度较低）",
            evidence=check.evidence or [],
            limitations=["规则归因仅基于字段存在性，无语义理解能力；建议 LLM 归因可用后重跑"],
            related_findings=[fid],
        )
        return finding, cause
