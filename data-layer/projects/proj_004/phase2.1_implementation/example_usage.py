"""
Phase 2.1 情报解码模块 - 使用示例
演示如何使用解码器
"""

import os
from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest, SourceType


def example_1_technical_signal():
    """示例 1：技术信号"""
    print("=" * 60)
    print("示例 1：技术信号")
    print("=" * 60)

    # 初始化解码器
    api_key = os.getenv("ANTHROPIC_API_KEY")
    decoder = IntelligenceDecoder(api_key=api_key)

    # 构建请求
    request = IntelligenceDecodeRequest(
        source_id="news_001",
        source_type=SourceType.NEWS,
        title="某游戏工作室宣布技术升级",
        content="某知名独立游戏工作室今日宣布，其正在开发的新项目将从 Unity 引擎迁移到 Unreal Engine 5。团队表示，此次升级将采用 UE5 的 Nanite 虚拟几何体技术和 Lumen 全局光照系统，以实现更高质量的画面表现。项目预计在 2026 年底完成技术迁移。",
        published_at="2026-03-14T10:00:00Z",
        source_name="游戏资讯网"
    )

    # 解码
    result = decoder.decode(request)

    # 输出结果
    print(f"\n原始输入 ID: {result.source_id}")
    print(f"处理耗时: {result.processing_time_ms}ms")
    print(f"解码版本: {result.decoder_version}")
    print(f"\n摘要: {result.summary}")
    print(f"\n检测到 {len(result.signals)} 个信号：")

    for i, signal in enumerate(result.signals, 1):
        print(f"\n信号 {i}:")
        print(f"  类型: {signal.signal_type.value}")
        print(f"  标签: {signal.signal_label}")
        print(f"  描述: {signal.description}")
        print(f"  强度: {signal.intensity_score}/10")
        print(f"  可信度: {signal.confidence_score}/10")
        print(f"  时效性: {signal.timeliness_score}/10")
        print(f"  实体: {', '.join(signal.entities) if signal.entities else '无'}")
        print(f"  证据: {signal.evidence_text[:100]}...")

    if result.warnings:
        print(f"\n警告: {result.warnings}")

    # 输出 JSON
    print("\n完整 JSON 输出:")
    print(result.model_dump_json(indent=2, exclude_none=True))


def example_2_capital_signal():
    """示例 2：资本信号"""
    print("\n\n" + "=" * 60)
    print("示例 2：资本信号")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    decoder = IntelligenceDecoder(api_key=api_key)

    request = IntelligenceDecodeRequest(
        source_id="news_002",
        source_type=SourceType.ANNOUNCEMENT,
        title="游戏工作室完成 A 轮融资",
        content="某独立游戏工作室今日宣布完成 A 轮融资，获得 500 万美元投资，由知名游戏产业基金领投。本轮融资将主要用于团队扩张和新项目研发。工作室创始人表示，此次融资将帮助团队加速产品开发进度。",
        published_at="2026-03-14T14:00:00Z",
        source_name="官方公告"
    )

    result = decoder.decode(request)

    print(f"\n原始输入 ID: {result.source_id}")
    print(f"处理耗时: {result.processing_time_ms}ms")
    print(f"\n摘要: {result.summary}")
    print(f"\n检测到 {len(result.signals)} 个信号：")

    for i, signal in enumerate(result.signals, 1):
        print(f"\n信号 {i}:")
        print(f"  类型: {signal.signal_type.value}")
        print(f"  标签: {signal.signal_label}")
        print(f"  强度: {signal.intensity_score}/10")
        print(f"  可信度: {signal.confidence_score}/10")


def example_3_no_signal():
    """示例 3：无信号（负例）"""
    print("\n\n" + "=" * 60)
    print("示例 3：无信号（负例）")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    decoder = IntelligenceDecoder(api_key=api_key)

    request = IntelligenceDecodeRequest(
        source_id="news_003",
        source_type=SourceType.NEWS,
        content="这款游戏画面精美，玩法有趣，深受玩家喜爱。敬请期待后续更多消息。",
        published_at="2026-03-14T16:00:00Z"
    )

    result = decoder.decode(request)

    print(f"\n原始输入 ID: {result.source_id}")
    print(f"处理耗时: {result.processing_time_ms}ms")
    print(f"\n摘要: {result.summary}")
    print(f"\n检测到 {len(result.signals)} 个信号")


if __name__ == "__main__":
    # 运行示例
    # 注意：需要设置 ANTHROPIC_API_KEY 环境变量

    print("Phase 2.1 情报解码模块 - 使用示例\n")

    # 示例 1：技术信号
    example_1_technical_signal()

    # 示例 2：资本信号
    # example_2_capital_signal()

    # 示例 3：无信号
    # example_3_no_signal()