"""
Phase 2.2 机会判断模块 - 使用示例

演示如何使用判断引擎进行机会判断
"""

from schemas import OpportunityJudgmentRequest, ContextPacket
from judgment_engine import JudgmentEngine
import json


def example_1_single_signal():
    """示例1：单一信号 - 预期输出 watch 级别"""
    print("=" * 60)
    print("示例1：单一技术信号（预期：watch级别）")
    print("=" * 60)

    # 构造输入
    request = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_001",
            "signals": [
                {
                    "signal_id": "sig_tech_001",
                    "signal_type": "technical",
                    "signal_summary": "某公司发布新AI芯片专利申请",
                    "intensity": 6,
                    "confidence": 7
                }
            ]
        }
    )

    # 执行判断
    engine = JudgmentEngine()
    result = engine.judge(request)

    # 输出结果
    print(f"\n状态: {result.status}")
    print(f"优先级: {result.opportunity.priority_level}")
    print(f"论点: {result.opportunity.opportunity_thesis}")
    print(f"支持证据: {len(result.opportunity.supporting_evidence)}条")
    print(f"反对证据: {len(result.opportunity.counter_evidence)}条")
    print(f"不确定性: {result.opportunity.uncertainty_map}")
    print(f"下一步验证问题: {result.opportunity.next_validation_questions}")
    print(f"证据完整度: {result.diagnostics.evidence_completeness:.2f}")
    print(f"处理耗时: {result.opportunity.processing_time_ms}ms")


def example_2_multiple_signals():
    """示例2：多信号聚类 - 预期输出 research 级别"""
    print("\n" + "=" * 60)
    print("示例2：多信号聚类（预期：research级别）")
    print("=" * 60)

    request = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_002",
            "signals": [
                {
                    "signal_id": "sig_tech_002",
                    "signal_type": "technical",
                    "signal_summary": "公司A发布量子计算突破",
                    "intensity": 7,
                    "confidence": 8
                },
                {
                    "signal_id": "sig_market_001",
                    "signal_type": "market",
                    "signal_summary": "量子计算市场规模预测增长50%",
                    "intensity": 6,
                    "confidence": 7
                },
                {
                    "signal_id": "sig_team_001",
                    "signal_type": "team",
                    "signal_summary": "公司A招聘量子算法专家",
                    "intensity": 5,
                    "confidence": 6
                }
            ]
        }
    )

    engine = JudgmentEngine()
    result = engine.judge(request)

    print(f"\n状态: {result.status}")
    print(f"优先级: {result.opportunity.priority_level}")
    print(f"论点: {result.opportunity.opportunity_thesis}")
    print(f"支持证据数量: {len(result.opportunity.supporting_evidence)}")
    print(f"关键假设: {result.opportunity.key_assumptions}")
    print(f"证据完整度: {result.diagnostics.evidence_completeness:.2f}")


def example_3_with_context_packet():
    """示例3：带2.4证据包 - 演示降级策略对比"""
    print("\n" + "=" * 60)
    print("示例3：带2.4证据包 vs 无证据包（降级策略对比）")
    print("=" * 60)

    base_request = {
        "intelligence_id": "intel_003",
        "signals": [
            {
                "signal_id": "sig_tech_003",
                "signal_type": "technical",
                "signal_summary": "新能源电池技术突破",
                "intensity": 7,
                "confidence": 7
            }
        ]
    }

    # 无2.4证据包
    print("\n--- 无2.4证据包（降级模式）---")
    request_without_context = OpportunityJudgmentRequest(
        decoded_intelligence=base_request
    )

    engine = JudgmentEngine()
    result1 = engine.judge(request_without_context)

    print(f"优先级: {result1.opportunity.priority_level}")
    print(f"支持证据: {result1.opportunity.supporting_evidence}")
    print(f"反对证据: {result1.opportunity.counter_evidence}")
    print(f"不确定性: {result1.opportunity.uncertainty_map}")

    # 有2.4证据包
    print("\n--- 有2.4证据包（增强模式）---")
    request_with_context = OpportunityJudgmentRequest(
        decoded_intelligence=base_request,
        context_packet=ContextPacket(
            similar_cases=["特斯拉电池技术成功商业化案例"],
            counter_examples=["某公司类似技术失败案例"]
        )
    )

    result2 = engine.judge(request_with_context)

    print(f"优先级: {result2.opportunity.priority_level}")
    print(f"支持证据数量: {len(result2.opportunity.supporting_evidence)}")
    print(f"反对证据数量: {len(result2.opportunity.counter_evidence)}")
    print(f"证据完整度对比: 无2.4={result1.diagnostics.evidence_completeness:.2f}, 有2.4={result2.diagnostics.evidence_completeness:.2f}")


def example_4_insufficient_evidence():
    """示例4：证据不足 - 预期返回 insufficient_evidence"""
    print("\n" + "=" * 60)
    print("示例4：证据不足场景")
    print("=" * 60)

    request = OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_004",
            "signals": []  # 空信号列表
        }
    )

    engine = JudgmentEngine()
    result = engine.judge(request)

    print(f"\n状态: {result.status}")
    print(f"优先级: {result.opportunity.priority_level}")
    print(f"论点: {result.opportunity.opportunity_thesis}")
    print(f"边界警告: {result.diagnostics.boundary_warnings}")
    print(f"下一步验证问题: {result.opportunity.next_validation_questions}")


if __name__ == "__main__":
    # 运行所有示例
    example_1_single_signal()
    example_2_multiple_signals()
    example_3_with_context_packet()
    example_4_insufficient_evidence()

    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)
