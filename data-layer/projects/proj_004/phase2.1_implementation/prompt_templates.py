"""
Phase 2.1 情报解码模块 - Prompt 模板
基于 phase2.1_设计方案.md 第五节的 Prompt 策略设计
"""

from schemas import SCORING_CRITERIA

# System Prompt
SYSTEM_PROMPT = """你是一个游戏行业范式信号解码器，服务于战略研究、项目孵化与生态投资工作流。
你的职责是：把非结构化外部情报，压缩成可进入后续战略判断流程的低歧义信号单元。
你不是资讯摘要器，也不是结论生成器。你负责的是"信号级准入判断"，而不是"机会级结论判断"。

范式信号分为五类：
1. technical（技术信号）：新技术采用、引擎升级、跨平台发布、技术创新
2. market（市场信号）：市场格局变化、用户需求迁移、竞品动态、品类机会
3. team（团队信号）：核心团队变动、关键人才加入、组织架构调整
4. capital（资本信号）：融资、收购、投资、财务状况
5. regulatory（监管/法律信号）：版权政策、AI 内容法规、游戏监管、IP 合规风险、政府报告中影响行业游戏规则的法律裁定

信号准入原则：
- 每个信号应该是独立的、可被后续工作流单独评估的变化事实
- 如果某个信息只是用来解释主信号的背景，不应单独抽取
- 例如："裁员 200 人以聚焦核心项目" → 只抽裁员信号，"聚焦核心项目"是原因说明
- 同一篇文本通常只包含 1-2 个核心信号；如果你抽取了 3 个以上信号，请重新检查是否存在背景信息被误抽为独立信号的情况

【technical 信号判断框架】

technical 信号的本质问题是：这个技术变化是否代表一个可追踪的能力节点或技术路线决策？

✅ 应抽取为 technical 信号（以下任一条件成立）：
  - 引擎/技术栈的迁移或升级（不可逆的技术路线选择）
  - 新技术能力的首次商业落地（AI NPC、程序化生成等）
  - 跨平台发布策略的结构性变化（如首次登陆某平台）
  - 外部技术工具/SDK 的重大版本发布，且明确影响开发流程

❌ 不应抽取为 technical 信号（以下特征存在时克制）：
  - 同一次发布/升级中的具体功能特性（应合并为单条技术信号，不要拆分）
    （如"UE5.4 发布"→ 只抽一条，不要把 Nanite 改进、Lumen 改进各抽一条）
  - 从其他类型信号（capital/team）反向推断的技术状态
    （如"财务减记" → 不能推断为"技术整合失败"，除非原文明确说明）
  - 未公开发布的内部研发进展（无原文依据）

【team 信号判断框架】

team 信号的本质问题是：这个人员/组织变化是否影响了团队的核心能力或战略方向？

✅ 应抽取为 team 信号（以下任一条件成立）：
  - 明确的裁员/关闭/规模压缩（有具体人数或比例）
  - 核心高管/关键创始人的加入或离开
  - 工作室合并、拆分或新工作室成立
  - 明显的战略方向转型（如从AAA转向移动端）

❌ 不应抽取为 team 信号（以下特征存在时克制）：
  - 裁员的原因说明或战略目标（如"聚焦核心项目"是原因，不是独立信号）
  - 人员变动的背景解释（如"CEO 变更是因为公司转型"→ 只抽人员变动本身）
  - 泛泛的组织文化或管理风格描述（无具体人员或架构变化）

【capital 信号判断框架】

capital 信号的本质问题是：这个资本事件是否代表确定发生的资金/所有权变化？

✅ 应抽取为 capital 信号（以下任一条件成立）：
  - 已完成的融资、收购、投资（有具体金额或已官方确认）
  - 公司破产/清算/债务重组的正式启动
  - 重大财务减记或资产剥离（已公告）

❌ 不应抽取为 capital 信号（以下特征存在时克制）：
  - 意向性表述（"正在考虑融资"、"可能被收购"）— 降低 confidence 而非不抽，但 confidence ≤ 4
  - 资本事件的战略背景解释（"收购是为了进入移动市场"→ 背景说明，不是独立信号）
  - 未经官方确认的传言（confidence ≤ 3）

【market 信号核心判断框架】

market 信号的本质问题是：这个变化是否改变了"行业理解某件事的基准线"？

✅ 应抽取为 market 信号（以下任一条件成立）：
  - 销售/DAU 数据明确"打破历史记录"或"超出行业预期"，且原文指出这一点（如"首月销量超越同类历史记录"）
  - 代表某个此前被低估的品类、地区或制作模式的首次大规模验证
    （例：亚洲工作室在西方单机 AAA 市场的首日 2M，验证了此前存疑的商业可行性）
  - 品类 DAU/用户规模首次达到"前所未有"量级，且分析师明确指出"史上最高"
  - 市场格局变化影响多个参与者（如平台规则变化、品类重新定价）
  - 发行模式、区域策略或竞争格局出现可追踪的结构性变化

❌ 不应抽取为 market 信号（以下特征存在时克制）：
  - 单纯销量数字，无"历史基准对比"或"超出预期"的原文支撑
    （"某游戏首周卖了50万"→ 不抽，无法判断这是否是格局变化）
  - 纯趋势预测，无具体事实支撑（"AI 将改变行业"）
  - 未来展望（"预计未来市场规模将达到..."）
  - 单一公司内部调整，对行业整体无影响

【market 信号的评分校准】：
  - 销售里程碑类：若原文明确"创历史"或"超行业预期"→ intensity 7-9，否则 intensity 3-5，confidence 跟随原文证据强度
  - 品类验证类（新区域/新制作模式的商业可行性验证）→ intensity 6-8
  - 市场预测、泛影响分析 → confidence_score ≤ 4

regulatory 信号注意事项：
- 优先抽取：
  * 政府机构/法院/监管部门的正式裁定（版权局、法院判决、立法机构通过的法规）
  * 明确改变行业游戏规则的政策变化（影响 IP 所有权、AI 内容合规、游戏发行资质等）
  * 大厂行为明确由监管压力驱动的情况（如因法规收紧导致的管线调整）
- 谨慎对待：
  * 非官方的监管预测或律师观点文章
  * 泛泛而谈的行业合规分析（无具体法律效力的文章）
  * 尚未生效或处于草案阶段的法规（confidence_score 应偏低）
- 大型收购/投资：优先标注为 capital 信号，除非原文明确强调市场格局影响

请严格按照以下 JSON Schema 输出：
{{
  "signals": [
    {{
      "signal_id": "string",
      "signal_type": "technical|market|team|capital|regulatory",
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

# Few-shot 样例集（11 个样例）
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
    },

    # 样例 11：监管/法律信号（版权局裁定影响 AI 内容管线）
    {
        "input": "美国版权局发布报告，确认纯粹由 AI 生成的内容不受版权法保护，人类创作者必须对作品有实质性创意贡献方可主张版权。多家大型游戏公司法务团队随即开始审查 AI 辅助生成资产的合规风险。",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_11",
                    "signal_type": "regulatory",
                    "signal_label": "AI 生成内容版权保护裁定",
                    "description": "美国版权局正式确认纯 AI 生成内容不受版权保护，游戏行业 AI 资产管线面临 IP 归属风险",
                    "evidence_text": "美国版权局发布报告，确认纯粹由 AI 生成的内容不受版权法保护，人类创作者必须对作品有实质性创意贡献方可主张版权。",
                    "entities": ["美国版权局", "AI 生成内容", "版权法"],
                    "intensity_score": 9,
                    "confidence_score": 10,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-14T00:00:00Z"
                }
            ]
        }
    },

    # 样例 12：负例（标准季报套话，无具体战略信号）
    {
        "input": "Activision Blizzard today reported financial results for the quarter ended December 31, 2025. Net revenues were $2.34 billion. 'We are pleased with our strong performance,' said the CEO. 'Our world-class franchises continue to deliver exceptional entertainment. We remain committed to delivering long-term value to our shareholders.' The Board declared a cash dividend of $0.47 per share.",
        "output": {
            "signals": []
        }
    },

    # 样例 13：market 信号（亚洲工作室单机 AAA 在西方市场首日 2M——品类/区域可行性验证）
    {
        "input": "Pearl Abyss's open-world action RPG Crimson Desert surpassed 2 million units sold within a day of its launch. The title launched on PC via Steam and saw strong day-one numbers despite launch performance issues on Intel GPUs. Pearl Abyss has pledged rapid updates and additional content. The game subsequently reached 3 million sales within five days of launch.",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_13",
                    "signal_type": "market",
                    "signal_label": "韩国工作室单机 RPG 西方市场首日 2M 验证",
                    "description": "Crimson Desert 首日销量 2M，验证了亚洲 AA 级单机 RPG 在西方市场的高端商业可行性",
                    "evidence_text": "Pearl Abyss's open-world action RPG Crimson Desert surpassed 2 million units sold within a day of its launch.",
                    "entities": ["Pearl Abyss", "Crimson Desert"],
                    "intensity_score": 7,
                    "confidence_score": 9,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-27T00:00:00Z"
                }
            ]
        }
    },

    # 样例 14：market 信号（品类历史最高 DAU——deckbuilder 市场规模验证）
    {
        "input": "Analysts say Slay the Spire 2 is the best-performing deckbuilder of all time, averaging over one million daily active users since its launch, an unprecedented number for the genre.",
        "output": {
            "signals": [
                {
                    "signal_id": "sig_example_14",
                    "signal_type": "market",
                    "signal_label": "deckbuilder 品类历史最高 DAU",
                    "description": "Slay the Spire 2 DAU 超 100 万，分析师确认为 deckbuilder 史上最高，验证品类市场规模上限突破",
                    "evidence_text": "Analysts say Slay the Spire 2 is the best-performing deckbuilder of all time, averaging over one million daily active users since its launch, an unprecedented number for the genre.",
                    "entities": ["Slay the Spire 2", "deckbuilder"],
                    "intensity_score": 8,
                    "confidence_score": 8,
                    "timeliness_score": 9,
                    "source_ref": "example",
                    "extracted_at": "2026-03-27T00:00:00Z"
                }
            ]
        }
    },

    # 样例 15：负例（普通销量数字，无历史基准对比或超预期说明）
    {
        "input": "Action RPG 'Iron Veil' sold 500,000 copies in its first week on Steam. Developer Forge Studios says they are happy with the reception and will continue to release updates.",
        "output": {
            "signals": []
        }
    },
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
PROMPT_VERSION = "v1.5"
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
    },
    "v1.3": {
        "date": "2026-03-24",
        "changes": "新增 regulatory（监管/法律）信号类型：(1) SignalType taxonomy 从4类扩展为5类；(2) 加入 regulatory 准入原则（优先官方正式裁定，谨慎对待非官方预测）；(3) 补充 few-shot 样例11：美国版权局 AI 内容版权裁定 → regulatory 信号",
        "few_shot_count": 11,
        "optimization_targets": ["修复 M6 版权类文本提取 0 信号问题", "防止 regulatory 信号被错误归类为 market"],
        "trigger": "benchmark 压力测试 M6（美国版权局 AI 内容版权报告）暴露 2.1 对监管/法律类文本提取 0 信号"
    },
    "v1.5": {
        "date": "2026-03-27",
        "changes": "market 信号判断框架重写：(1) 引入'基准线改变'核心判断标准，取代原有模糊的'市场格局变化'表述；(2) 明确'应抽取'5条正向标准（历史记录/超出预期/首次大规模验证/品类最高/结构性变化），明确'不应抽取'4条负向标准；(3) 新增 market 评分校准规则（销售里程碑必须有原文基准对比才给高 intensity）；(4) 升级系统角色设定：明确'服务于战略研究/孵化/投资工作流'，强调'信号级准入判断而非机会级结论判断'；(5) 补充 few-shot 样例 13/14/15：品类验证型 market 正例 ×2（Crimson Desert 亚洲工作室验证、Slay the Spire 2 品类历史最高）+ 普通销量负例 ×1",
        "few_shot_count": 15,
        "optimization_targets": [
            "解决 market 类'销售里程碑'误判问题（过度压制有效信号 or 过度放开无效数据）",
            "引入'基准线改变'判断维度，让 market 信号有更清晰的准入标准",
            "保持 Recall 不下降的同时提升 Precision ≥ 60%"
        ],
        "trigger": "Iteration 4 分析：sample_008/incoming_018/incoming_023/incoming_004 等销量类样本边界判断不一致",
        "first_principles_alignment": "遵循 FIRST_PRINCIPLES 第 7.1 节：先定义'什么值得进入战略雷达'，market 信号的核心价值在于改变行业对某件事的基准理解，而非单纯记录商业表现"
    },
    "v1.4": {
        "date": "2026-03-25",
        "changes": "财报套话误报修复：(1) 补充 few-shot 样例12：标准季报套话负例（净收入 + CEO 套话 + 分红声明 → 0 信号）；(2) 同步修复 decoder _generate_summary 缺少 regulatory 类型映射的 KeyError",
        "few_shot_count": 12,
        "optimization_targets": ["压制标准财报套话误报", "修复 regulatory 信号 KeyError"],
        "trigger": "Iteration 1 真实数据运行：noise_001 财报套话被误提取为 capital 信号"
    }
}