"""
Phase 2.1 情报解码模块 - Prompt 模板
基于 phase2.1_设计方案.md 第五节的 Prompt 策略设计
"""

from schemas import SCORING_CRITERIA

# System Prompt
SYSTEM_PROMPT = """你是一个游戏行业情报分析专家，负责从非结构化文本中提取范式信号。

范式信号分为四类：
1. technical（技术信号）：新技术采用、引擎升级、跨平台发布、技术创新
2. market（市场信号）：市场趋势、用户需求变化、竞品动态、品类机会
3. team（团队信号）：核心团队变动、关键人才加入、组织架构调整
4. capital（资本信号）：融资、收购、投资、财务状况

请严格按照以下 JSON Schema 输出：
{{
  "signals": [
    {{
      "signal_id": "string",
      "signal_type": "technical|market|team|capital",
      "signal_label": "string",
      "description": "string",
      "evidence_text": "string",
      "entities": ["string"],
      "intensity_score": integer(1-10),
      "confidence_score": integer(1-10),
      "timeliness_score": integer(1-10),
      "source_ref": "string",
      "extracted_at": "ISO8601 string"
    }}
  ]
}}

评分口径：
- intensity_score（强度）：1-3 弱信号，4-7 中等，8-10 强信号
- confidence_score（可信度）：1-3 传闻，4-7 可信来源，8-10 官方确认
- timeliness_score（时效性）：1-3 过时，4-7 近期，8-10 最新

重要规则：
1. 如果文本中没有明确的范式信号，返回空的 signals 数组
2. 每个信号必须有明确的证据原文片段（evidence_text）
3. 评分必须基于上述口径，不要随意打分
4. entities 可以为空数组，但如果有明确实体请提取
"""

# Few-shot 样例集（6 个样例）
FEW_SHOT_EXAMPLES = [
    # 样例 1：技术信号
    {
        "input": "某游戏工作室宣布项目从 Unity 迁移到 Unreal Engine 5，将采用 Nanite 和 Lumen 技术提升画面表现。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_1",
                    "signal_type": "technical",
                    "signal_label": "引擎迁移至 UE5",
                    "description": "项目从 Unity 迁移到 Unreal Engine 5，采用 Nanite 和 Lumen 技术",
                    "evidence_text": "某游戏工作室宣布项目从 Unity 迁移到 Unreal Engine 5，将采用 Nanite 和 Lumen 技术提升画面表现。",
                    "entities": ["Unity", "Unreal Engine 5", "Nanite", "Lumen"],
                    "intensity_score": 8,
                    "confidence_score": 10,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 2：市场信号
    {
        "input": "根据最新市场报告，Roguelike 品类在 2025 年增长了 45%，成为独立游戏市场的热门品类。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_2",
                    "signal_type": "market",
                    "signal_label": "Roguelike 品类增长",
                    "description": "Roguelike 品类在 2025 年增长 45%，成为独立游戏热门品类",
                    "evidence_text": "根据最新市场报告，Roguelike 品类在 2025 年增长了 45%，成为独立游戏市场的热门品类。",
                    "entities": ["Roguelike", "独立游戏"],
                    "intensity_score": 7,
                    "confidence_score": 8,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 3：团队信号
    {
        "input": "前暴雪资深制作人 John Doe 宣布加入某独立游戏工作室，担任创意总监。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_3",
                    "signal_type": "team",
                    "signal_label": "前暴雪制作人加入",
                    "description": "前暴雪资深制作人 John Doe 加入担任创意总监",
                    "evidence_text": "前暴雪资深制作人 John Doe 宣布加入某独立游戏工作室，担任创意总监。",
                    "entities": ["John Doe", "暴雪"],
                    "intensity_score": 7,
                    "confidence_score": 9,
                    "timeliness_score": 10,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 4：资本信号
    {
        "input": "某游戏工作室宣布完成 A 轮融资，获得 500 万美元投资，由知名游戏基金领投。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_4",
                    "signal_type": "capital",
                    "signal_label": "A 轮融资 500 万美元",
                    "description": "完成 A 轮融资，获得 500 万美元投资",
                    "evidence_text": "某游戏工作室宣布完成 A 轮融资，获得 500 万美元投资，由知名游戏基金领投。",
                    "entities": ["A 轮融资"],
                    "intensity_score": 7,
                    "confidence_score": 10,
                    "timeliness_score": 10,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 5：边界例（模糊信号）
    {
        "input": "市场传闻某公司正在洽谈新一轮融资，但官方尚未确认。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_5",
                    "signal_type": "capital",
                    "signal_label": "融资传闻",
                    "description": "市场传闻正在洽谈新一轮融资，未官方确认",
                    "evidence_text": "市场传闻某公司正在洽谈新一轮融资，但官方尚未确认。",
                    "entities": [],
                    "intensity_score": 4,
                    "confidence_score": 3,
                    "timeliness_score": 8,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 6：负例（无信号）
    {
        "input": "游戏画面精美，玩法有趣，敬请期待后续消息。",
        "output": {
            "signals": []
        }
    }
]


def build_prompt(content: str, source_id: str) -> str:
    """构建完整的 Prompt"""

    # 构建 few-shot 部分
    few_shot_text = "\n\n".join([
        f"示例 {i+1}：\n输入：{ex['input']}\n输出：{ex['output']}"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES)
    ])

    # 完整 Prompt
    prompt = f"""{SYSTEM_PROMPT}

以下是一些示例：

{few_shot_text}

现在请分析以下文本：

输入：{content}

请输出 JSON 格式的结果（只输出 JSON，不要其他说明文字）：
"""

    return prompt


# Prompt 版本管理
PROMPT_VERSION = "v1.0"
PROMPT_CHANGELOG = {
    "v1.0": {
        "date": "2026-03-14",
        "changes": "初始版本，包含 6 个 few-shot 样例（4 类信号 + 1 边界例 + 1 负例）",
        "few_shot_count": 6
    }
}