"""
Phase 2.1 情报解码模块 - Prompt 模板
基于 phase2.1_设计方案.md 第五节的 Prompt 策略设计
"""

from schemas import SCORING_CRITERIA

# System Prompt
SYSTEM_PROMPT = """你是一个游戏行业范式信号解码器，负责从非结构化文本中提取可进入战略工作流的正式信号。

范式信号分为四类：
1. technical（技术信号）：新技术采用、引擎升级、跨平台发布、技术创新
2. market（市场信号）：市场格局变化、用户需求迁移、竞品动态、品类机会
3. team（团队信号）：核心团队变动、关键人才加入、组织架构调整
4. capital（资本信号）：融资、收购、投资、财务状况

信号准入原则：
- 每个信号应该是独立的、可被后续工作流单独评估的变化事实
- 如果某个信息只是用来解释主信号的背景，不应单独抽取
- 例如："裁员 200 人以聚焦核心项目" → 只抽裁员信号，"聚焦核心项目"是原因说明

market 信号注意事项：
- 优先抽取：
  * 具体的市场格局变化（行业层面的、影响多个参与者的变化）
  * 明确的数据支撑的品类增长（有具体数字或市场份额变化）
  * 可追踪的竞品动态（具体产品、具体策略、具体市场行为）
- 谨慎对待：
  * 纯趋势预测（"AI 将改变行业"）
  * 未来展望（"预计未来..."）
  * 泛泛影响解读（"可能对行业产生影响"）
  * 单一公司的内部调整（除非明确改变市场格局）
- 大型收购/投资：优先标注为 capital 信号，除非原文明确强调市场格局影响

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
- confidence_score（证据稳固度）：
  * 1-3：传闻、二手引用、推断性内容
  * 4-6：间接证据、表述模糊
  * 7-10：官方确认、直接证据、原文明确支持
- timeliness_score（时效性）：1-3 过时，4-7 近期，8-10 最新

重要规则：
1. 如果文本中没有明确的范式信号，返回空的 signals 数组
2. 每个信号必须有明确的证据原文片段（evidence_text）
3. 推断链过长或证据模糊时，降低 confidence_score（不是不抽，而是降分）
4. 不确定时可以抽取，但通过 confidence_score 反映证据强度
"""

# Few-shot 样例集（9 个样例）
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
    },

    # 样例 7：负例（背景误报防护）
    {
        "input": "某工作室裁员 200 人，以聚焦核心项目开发。公司表示将把资源集中在旗舰产品上。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_7",
                    "signal_type": "team",
                    "signal_label": "裁员 200 人",
                    "description": "裁员 200 人，以聚焦核心项目",
                    "evidence_text": "某工作室裁员 200 人，以聚焦核心项目开发。",
                    "entities": [],
                    "intensity_score": 7,
                    "confidence_score": 10,
                    "timeliness_score": 10,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 8：负例（market 泛趋势表述）
    {
        "input": "分析师认为生成式 AI 将在未来三年改变游戏角色创建流程，这可能对整个行业产生深远影响。",
        "output": {
            "signals": []
        }
    },

    # 样例 9：边界例（推断链过长，降低置信度）
    {
        "input": "某公司财报显示对子公司进行了 2 亿美元减记，分析师推测可能与技术整合困难有关。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_9",
                    "signal_type": "capital",
                    "signal_label": "子公司减记 2 亿美元",
                    "description": "对子公司进行 2 亿美元减记",
                    "evidence_text": "某公司财报显示对子公司进行了 2 亿美元减记",
                    "entities": [],
                    "intensity_score": 8,
                    "confidence_score": 10,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 10：负例（单一公司内部调整不是 market 信号）
    {
        "input": "某游戏公司宣布调整产品线，将资源集中在核心品类，停止边缘项目开发。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_10",
                    "signal_type": "team",
                    "signal_label": "产品线调整",
                    "description": "调整产品线，集中资源于核心品类",
                    "evidence_text": "某游戏公司宣布调整产品线，将资源集中在核心品类，停止边缘项目开发。",
                    "entities": [],
                    "intensity_score": 6,
                    "confidence_score": 10,
                    "timeliness_score": 10,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
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
PROMPT_VERSION = "v1.2"
PROMPT_CHANGELOG = {
    "v1.0": {
        "date": "2026-03-14",
        "changes": "初始版本，包含 6 个 few-shot 样例（4 类信号 + 1 边界例 + 1 负例）",
        "few_shot_count": 6
    },
    "v1.1": {
        "date": "2026-03-14",
        "changes": "轻量优化：(1) 强化角色设定为'范式信号解码器'，补充信号准入原则（防止背景信息被抽成独立信号）；(2) 调整 market 定义为'注意事项'而非硬性排除，保持召回的同时提升精度；(3) 修正 confidence_score 口径为'证据稳固度'，强调推断链过长应降分而非不抽；(4) 补充 3 个针对性 few-shot：背景误报防护例、market 泛趋势负例、推断链过长边界例",
        "few_shot_count": 9,
        "optimization_targets": ["压制 market 误报", "防止背景信息被抽成独立信号", "修正边界样本置信度"],
        "balance_note": "v1.1 在 v1.0 基础上收紧约束，但避免过度克制导致召回下降"
    },
    "v1.2": {
        "date": "2026-03-14",
        "changes": "针对 v1.1 顽固误报的定向优化：(1) 进一步收紧 market 定义，明确'市场格局变化'必须是行业层面的、影响多个参与者的变化；(2) 明确大型收购/投资优先标注为 capital 信号；(3) 补充 few-shot 样例 10：单一公司内部调整不是 market 信号",
        "few_shot_count": 10,
        "optimization_targets": ["解决 11 个顽固 market 误报", "明确 capital vs market 分类规则"],
        "v1_1_results": "Precision 42.11%, Recall 80.00%, F1 55.17%",
        "target": "Precision ≥ 50%, 保持 Recall ≥ 75%"
    }
}