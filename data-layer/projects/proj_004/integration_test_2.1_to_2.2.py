"""
Phase 2.1 -> 2.2 接口联调测试

P1-1: 验证 DecodedIntelligence -> OpportunityJudgmentRequest -> OpportunityObject 全流程
运行方式: python integration_test_2.1_to_2.2.py
"""

import os
import sys
import time

# 路径设置 - 用 importlib 避免两个 schemas.py 冲突
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

m21 = load_module('schemas_21', os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
m22 = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))

DecodedIntelligence = m21.DecodedIntelligence
Signal = m21.Signal
SignalType = m21.SignalType
SourceType = m21.SourceType

OpportunityJudgmentRequest = m22.OpportunityJudgmentRequest

# judgment_engine 依赖 sys.path 中的 schemas，需在 2.2 目录下加载
sys.path.insert(0, os.path.join(BASE, 'phase2.2_implementation'))
from judgment_engine import JudgmentEngine


def build_request_from_decoded(decoded: DecodedIntelligence) -> OpportunityJudgmentRequest:
    """
    适配器：DecodedIntelligence -> OpportunityJudgmentRequest
    2.2 接收 decoded_intelligence: Dict[str, Any]，直接用 .model_dump() 转换
    """
    return OpportunityJudgmentRequest(
        decoded_intelligence=decoded.model_dump()
    )


def run_case(name: str, decoded: DecodedIntelligence, engine: JudgmentEngine):
    print(f"\n{'='*60}")
    print(f"案例: {name}")
    print(f"{'='*60}")
    print(f"信号数量: {len(decoded.signals)}")
    for s in decoded.signals:
        print(f"  - [{s.signal_type.value}] {s.signal_label} (强度:{s.intensity_score} 可信:{s.confidence_score})")

    request = build_request_from_decoded(decoded)
    result = engine.judge(request)

    print(f"\n判断状态: {result.status}")
    if result.status in ("success", "insufficient_evidence"):
        opp = result.opportunity
        print(f"机会标题: {opp.opportunity_title}")
        print(f"优先级:   {opp.priority_level}")
        print(f"核心论点: {opp.opportunity_thesis[:80]}..." if len(opp.opportunity_thesis) > 80 else f"核心论点: {opp.opportunity_thesis}")
        print(f"关键假设数: {len(opp.key_assumptions)}")
        print(f"不确定性数: {len(opp.uncertainty_map)}")
        if result.diagnostics:
            print(f"证据完整度: {result.diagnostics.evidence_completeness:.0%}")
            if result.diagnostics.boundary_warnings:
                print(f"边界警告: {result.diagnostics.boundary_warnings}")
    elif result.status == "error":
        print(f"ERROR: {result.error.message}")
        return False

    # 可拍板性检查
    checks = {
        "有机会标题": bool(result.opportunity.opportunity_title),
        "有优先级分级": bool(result.opportunity.priority_level),
        "有核心论点": bool(result.opportunity.opportunity_thesis),
        "有下一步问题": len(result.opportunity.next_validation_questions) > 0,
        "schema合法": True,  # 能走到这里说明已通过 Pydantic 校验
    }
    all_pass = all(checks.values())
    print(f"\n可拍板性检查: {'PASS' if all_pass else 'FAIL'}")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")
    return all_pass


def main():
    print("\nPhase 2.1 -> 2.2 联调测试")
    print("="*60)

    engine = JudgmentEngine()

    # --- 案例1：高强度 AI 信号（预期 deep_dive 或 escalate）---
    case1 = DecodedIntelligence(
        source_id="src_001",
        source_type=SourceType.NEWS,
        signals=[
            Signal(
                signal_id="sig_001",
                signal_type=SignalType.TECHNICAL,
                signal_label="大语言模型游戏 NPC 对话",
                description="OpenAI 与多家游戏公司合作，将 GPT-4 集成进 NPC 对话系统",
                evidence_text="OpenAI announced partnerships with EA, Ubisoft and Riot Games to integrate GPT-4 into NPC dialogue systems",
                entities=["OpenAI", "EA", "Ubisoft", "Riot Games"],
                intensity_score=9,
                confidence_score=9,
                timeliness_score=9,
                source_ref="src_001",
                extracted_at="2026-03-22T00:00:00Z"
            ),
            Signal(
                signal_id="sig_002",
                signal_type=SignalType.MARKET,
                signal_label="AI NPC 市场规模预测",
                description="AI NPC 市场规模预计 2027 年达到 50 亿美元",
                evidence_text="Market analysts forecast AI NPC market to reach $5B by 2027, driven by player demand for dynamic storytelling",
                entities=["AI NPC"],
                intensity_score=8,
                confidence_score=7,
                timeliness_score=8,
                source_ref="src_001",
                extracted_at="2026-03-22T00:00:00Z"
            ),
            Signal(
                signal_id="sig_003",
                signal_type=SignalType.CAPITAL,
                signal_label="AI 游戏初创融资",
                description="多家 AI 游戏初创公司获得 A 轮融资，合计超过 2 亿美元",
                evidence_text="Three AI gaming startups raised Series A rounds totaling $200M in Q1 2026",
                entities=["AI gaming startups"],
                intensity_score=8,
                confidence_score=8,
                timeliness_score=9,
                source_ref="src_001",
                extracted_at="2026-03-22T00:00:00Z"
            ),
        ],
        summary="AI NPC 领域出现强信号：大厂合作、市场规模、资本涌入三重共振",
        decoder_version="v1.2",
        processing_time_ms=1200
    )

    # --- 案例2：弱信号单条（预期 watch）---
    case2 = DecodedIntelligence(
        source_id="src_002",
        source_type=SourceType.REPORT,
        signals=[
            Signal(
                signal_id="sig_004",
                signal_type=SignalType.TECHNICAL,
                signal_label="区块链游戏道具",
                description="某小型工作室尝试将区块链用于游戏道具确权",
                evidence_text="A small studio announced blockchain-based item ownership system, currently in alpha",
                entities=["blockchain", "small studio"],
                intensity_score=3,
                confidence_score=4,
                timeliness_score=5,
                source_ref="src_002",
                extracted_at="2026-03-22T00:00:00Z"
            ),
        ],
        summary="区块链游戏道具弱信号，尚处 alpha 阶段",
        decoder_version="v1.2",
        processing_time_ms=800
    )

    # --- 案例3：信号为空（预期降级处理）---
    case3 = DecodedIntelligence(
        source_id="src_003",
        source_type=SourceType.ANNOUNCEMENT,
        signals=[],
        summary="未检测到范式信号",
        decoder_version="v1.2",
        processing_time_ms=500
    )

    results = [
        run_case("AI NPC 三重共振（高强度）", case1, engine),
        run_case("区块链道具弱信号", case2, engine),
        run_case("空信号降级处理", case3, engine),
    ]

    print(f"\n{'='*60}")
    print("联调总结")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r)
    print(f"通过: {passed}/{len(results)}")
    if passed == len(results):
        print("P1-1 联调: PASS -- 可进入 P1-2（2.2->2.3 联调）")
    else:
        print("P1-1 联调: FAIL -- 需修复后重新验证")


if __name__ == "__main__":
    main()