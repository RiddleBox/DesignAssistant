# Phase 2.1 情报解码模块设计方案

> **文档类型**：设计方案（多角色讨论产物）
> **适用模块**：Phase 2.1 情报解码模块
> **产出方式**：由 7 个职责视角协作讨论产出
> **状态**：草案，待用户拍板
> **最后更新**：2026-03-14

---

## 一、方案概述

### 1.1 设计目标

Phase 2.1 的核心目标是：**将非结构化信息（新闻、报告、公告）转化为可追溯、可评分、可被下游稳定消费的结构化范式信号**。

### 1.2 设计原则

- **Prompt-first**：MVP 阶段优先使用 Prompt 实现，避免过早引入复杂规则
- **Schema 稳定**：先冻结最小字段，再逐步增强
- **证据可追溯**：每个信号必须能回到原文片段
- **评分是信号级**：不是机会级，不越界到 2.2
- **对 2.4 弱耦合**：可选增强，不强依赖

### 1.3 非目标（明确不做）

- ❌ 不在 2.1 内直接生成 2.2 层的机会高低结论
- ❌ 不把多 Agent 辩论、综合打分、行动建议提前塞进 2.1
- ❌ 不在 2.4 真实能力未稳定前，过度绑定其最终输出格式
- ❌ 不在首轮拍板前扩张过多信号类别、复杂规则引擎或多模型投票链路

---

## 二、信号定义与分类

### 2.1 四类范式信号

| 信号类型 | 英文标识 | 定义 | 示例 |
|----------|----------|------|------|
| **技术信号** | `technical` | 新技术采用、引擎升级、跨平台发布、技术创新 | UE5 升级、跨平台发行、新工具链 |
| **市场信号** | `market` | 市场趋势、用户需求变化、竞品动态、品类机会 | Roguelike 热度上升、移动端增长 |
| **团队信号** | `team` | 核心团队变动、关键人才加入、组织架构调整 | 前暴雪制作人加入、团队扩张 |
| **资本信号** | `capital` | 融资、收购、投资、财务状况 | A 轮融资、被收购、IPO |

### 2.2 信号判断标准

**技术信号**：
- 明确提到技术栈、引擎、工具、平台
- 涉及技术升级、迁移、创新
- 有具体的技术名词（如 UE5、Unity、Nanite）

**市场信号**：
- 涉及市场趋势、用户需求、品类机会
- 提到竞品、市场份额、增长数据
- 包含市场分析、预测

**团队信号**：
- 涉及核心人员变动（加入、离职）
- 组织架构调整、团队扩张
- 关键人才背景（如"前暴雪"、"前腾讯"）

**资本信号**：
- 融资、投资、收购、IPO
- 财务数据（营收、利润）
- 资本运作（股权变动）

### 2.3 边界样本

**正例**（明确信号）：
- "某游戏工作室宣布完成 A 轮融资 500 万美元" → capital
- "项目从 UE4 升级到 UE5，采用 Nanite 技术" → technical
- "前暴雪资深制作人 John Doe 加入团队担任创意总监" → team

**边界例**（模糊信号）：
- "市场传闻某公司正在洽谈融资" → capital（但 confidence_score 较低）
- "游戏可能支持跨平台" → technical（但需要更多证据）

**负例**（无信号）：
- "游戏画面精美，玩法有趣" → 纯营销软文，无实质信号
- "敬请期待后续消息" → 无实质信息

---

## 三、结构化契约设计

### 3.1 Signal 最小字段（MVP 版本）

```json
{
  "signal_id": "string",           // 必填，唯一标识，如 "sig_001"
  "signal_type": "enum",           // 必填，technical|market|team|capital
  "signal_label": "string",        // 必填，信号标签，如 "UE5 升级"
  "description": "string",         // 必填，信号描述
  "evidence_text": "string",       // 必填，证据原文片段
  "entities": "string[]",          // 必填，关联实体，可为空数组
  "intensity_score": "integer",    // 必填，强度评分 1-10
  "confidence_score": "integer",   // 必填，可信度评分 1-10
  "timeliness_score": "integer",   // 必填，时效性评分 1-10
  "source_ref": "string",          // 必填，对应原始来源 ID
  "extracted_at": "string",        // 必填，抽取时间 ISO8601
  "metadata": "object"             // 可选，扩展信息
}
```

### 3.2 DecodedIntelligence 最小字段

```json
{
  "source_id": "string",           // 必填，原始输入 ID
  "source_type": "string",         // 必填，news|report|announcement
  "signals": "Signal[]",           // 必填，抽取后的信号列表，可为空数组
  "summary": "string",             // 可选，人类可读摘要
  "decoder_version": "string",     // 必填，解码版本号，如 "v1.0"
  "processing_time_ms": "integer", // 必填，处理耗时（毫秒）
  "warnings": "string[]"           // 可选，风险或异常提示
}
```

### 3.3 评分口径

| 评分维度 | 1-3 分 | 4-7 分 | 8-10 分 |
|----------|--------|--------|---------|
| **intensity_score（强度）** | 弱信号，影响有限 | 中等信号，有一定影响 | 强信号，重大影响 |
| **confidence_score（可信度）** | 传闻、未证实 | 可信来源、间接证据 | 官方确认、直接证据 |
| **timeliness_score（时效性）** | 过时信息（>6 个月） | 近期信息（1-6 个月） | 最新信息（<1 个月） |

### 3.4 兼容策略

- **字段名不可变**：只能新增字段，不能修改或删除现有字段
- **枚举值不可删除**：只能新增枚举值，不能删除现有值
- **预留扩展字段**：`metadata` 用于后续增强
- **版本号管理**：`decoder_version` 用于基线对照

### 3.5 向 2.2 交付样例

```json
{
  "source_id": "news_001",
  "source_type": "news",
  "signals": [
    {
      "signal_id": "sig_001",
      "signal_type": "technical",
      "signal_label": "Unreal Engine 5 升级",
      "description": "项目宣布从 UE4 升级到 UE5，采用 Nanite 和 Lumen 技术",
      "evidence_text": "官方公告：我们很高兴宣布项目将升级到 Unreal Engine 5，并采用 Nanite 虚拟几何体和 Lumen 全局光照技术...",
      "entities": ["Unreal Engine 5", "Nanite", "Lumen"],
      "intensity_score": 8,
      "confidence_score": 10,
      "timeliness_score": 9,
      "source_ref": "news_001",
      "extracted_at": "2026-03-14T10:00:00Z"
    }
  ],
  "summary": "某游戏项目宣布技术升级，从 UE4 迁移到 UE5",
  "decoder_version": "v1.0",
  "processing_time_ms": 6500,
  "warnings": []
}
```

---

## 四、抽取流程设计

### 4.1 整体流程

```
原始输入（IntelligenceDecodeRequest）
  ↓
[1] 文本预处理
  ↓
[2] Prompt 调用（LLM）
  ↓
[3] 后处理与规范化
  ↓
[4] Schema 校验
  ↓
[5] 输出（DecodedIntelligence）
```

### 4.2 各步骤详细说明

**[1] 文本预处理**：
- 去除多余空格、换行
- 统一标点符号
- 保留原文结构（不做过度清洗）

**[2] Prompt 调用**：
- 使用 Claude Opus 4.6
- Prompt 结构：System Prompt + Few-shot Examples + User Input
- 输出格式：JSON

**[3] 后处理与规范化**：
- 格式规范化：去除多余空格、统一标点
- 字段补全：如果 entities 为空，尝试从 evidence_text 提取
- 评分校验：确保 1-10 范围
- 去重：同一 source 内的重复信号

**[4] Schema 校验**：
- 使用 JSON Schema validator
- 必填字段检查
- 类型检查
- 枚举值检查

**[5] 输出**：
- 返回 DecodedIntelligence
- 记录处理耗时
- 记录 warnings（如果有）

### 4.3 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| **LLM API 限流** | 重试 3 次，指数退避 |
| **JSON 解析失败** | 记录 warning，返回空 signals |
| **Schema 校验失败** | 记录 warning，尝试修复或丢弃该信号 |
| **原文过短（<50 字）** | 记录 warning，继续处理 |
| **无信号** | 返回空 signals，不算错误 |

---

## 五、Prompt 策略设计

### 5.1 Prompt 结构

```
System Prompt:
你是一个游戏行业情报分析专家，负责从非结构化文本中提取范式信号。

范式信号分为四类：
1. technical（技术信号）：新技术采用、引擎升级、跨平台发布、技术创新
2. market（市场信号）：市场趋势、用户需求变化、竞品动态、品类机会
3. team（团队信号）：核心团队变动、关键人才加入、组织架构调整
4. capital（资本信号）：融资、收购、投资、财务状况

请严格按照以下 JSON Schema 输出：
{JSON Schema}

评分口径：
- intensity_score（强度）：1-3 弱信号，4-7 中等，8-10 强信号
- confidence_score（可信度）：1-3 传闻，4-7 可信来源，8-10 官方确认
- timeliness_score（时效性）：1-3 过时，4-7 近期，8-10 最新

Few-shot Examples:
{Few-shot 样例}

User Input:
{原始文本}
```

### 5.2 Few-shot 样例集（MVP 版本）

**样例 1：技术信号**
```
输入：某游戏工作室宣布项目从 Unity 迁移到 Unreal Engine 5，将采用 Nanite 和 Lumen 技术提升画面表现。
输出：
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
```

**样例 2：市场信号**
```
输入：根据最新市场报告，Roguelike 品类在 2025 年增长了 45%，成为独立游戏市场的热门品类。
输出：
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
```

**样例 3：团队信号**
```
输入：前暴雪资深制作人 John Doe 宣布加入某独立游戏工作室，担任创意总监。
输出：
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
```

**样例 4：资本信号**
```
输入：某游戏工作室宣布完成 A 轮融资，获得 500 万美元投资，由知名游戏基金领投。
输出：
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
```

**样例 5：边界例（模糊信号）**
```
输入：市场传闻某公司正在洽谈新一轮融资，但官方尚未确认。
输出：
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
```

**样例 6：负例（无信号）**
```
输入：游戏画面精美，玩法有趣，敬请期待后续消息。
输出：
{
  "signals": []
}
```

### 5.3 Prompt 版本管理

- **v1.0**：MVP 基础版（6 个 few-shot 样例）
- 后续版本记录在 `prompt_versions.md`
- 每次 Prompt 调整需要记录版本号、变更原因、效果对比

---

## 六、评测与验收设计

### 6.1 Benchmark 设计

**样本量**：首轮 30 条

**样本分布**：
| 输入类型 | 数量 | 信号分布 |
|----------|------|----------|
| news（新闻） | 10 条 | technical 3, market 3, team 2, capital 2 |
| report（报告） | 10 条 | technical 2, market 3, team 2, capital 3 |
| announcement（公告） | 10 条 | technical 3, market 2, team 3, capital 2 |
| **总计** | **30 条** | **technical 8, market 8, team 7, capital 7** |

**样本来源**：
- 真实游戏行业新闻（脱敏处理）
- 行业报告摘要
- 公司公告

### 6.2 标注规则

**准确率定义**：
- 抽取的信号是否正确（信号类型、标签、描述）
- 计算方式：正确信号数 / 总抽取信号数

**召回率定义**：
- 是否遗漏了应该抽取的信号
- 计算方式：正确抽取信号数 / 应抽取信号总数

**Schema 合法率定义**：
- 输出是否符合 JSON Schema
- 计算方式：合法输出数 / 总输出数

**标注示例**：
```
原文：某游戏工作室宣布完成 A 轮融资 500 万美元

标注：
- 应抽取信号数：1
- signal_type: capital ✓
- signal_label: "A 轮融资" 或 "A 轮融资 500 万美元" ✓
- intensity_score: 7-8 (中等偏强)
- confidence_score: 9-10 (官方宣布)
- timeliness_score: 根据发布时间判断
```

### 6.3 验收口径

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| **Schema 合法率** | 100% | JSON Schema 校验 |
| **准确率** | >= 80% | 人工标注集对比 |
| **召回率** | >= 75% | 人工标注集对比 |
| **单次处理耗时** | < 30s | 本地基准测试 |
| **输入源覆盖** | 至少 3 类 | 样例回归测试 |

### 6.4 效果不达标时的排查顺序

1. **标注口径**：是否标注规则不一致？
2. **Prompt 设计**：是否 Prompt 描述不清晰？
3. **字段定义**：是否字段定义有歧义？
4. **后处理规则**：是否需要增加规范化规则？
5. **2.4 增强上下文质量**：是否需要引入 few-shot 或术语库？

---

## 七、实现方案

### 7.1 技术栈

- **LLM**：Claude Opus 4.6
- **框架**：LangChain
- **校验**：JSON Schema validator（jsonschema 库）
- **存储**：JSON 文件（MVP）
- **语言**：Python 3.10+

### 7.2 核心代码结构

```python
# core/decoder.py
class IntelligenceDecoder:
    def __init__(self, llm, prompt_template, few_shot_examples):
        self.llm = llm
        self.prompt_template = prompt_template
        self.few_shot_examples = few_shot_examples

    def decode(self, request: IntelligenceDecodeRequest) -> DecodedIntelligence:
        # 1. 文本预处理
        cleaned_text = self.preprocess(request.content)

        # 2. 构建 Prompt
        prompt = self.build_prompt(cleaned_text)

        # 3. LLM 调用
        response = self.llm.invoke(prompt)

        # 4. 后处理
        signals = self.post_process(response)

        # 5. Schema 校验
        self.validate_schema(signals)

        # 6. 返回结果
        return DecodedIntelligence(
            source_id=request.source_id,
            source_type=request.source_type,
            signals=signals,
            decoder_version="v1.0",
            processing_time_ms=processing_time,
            warnings=warnings
        )
```

### 7.3 性能评估

| 步骤 | 预计耗时 |
|------|----------|
| 文本预处理 | ~0.1s |
| Prompt 调用（LLM） | ~5-10s |
| 后处理 | ~1s |
| Schema 校验 | ~0.1s |
| **总计** | **~6-11s** |

**结论**：远低于 30s 目标，性能充足。

### 7.4 工程风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| **LLM API 限流** | 中 | 高 | 重试机制（3 次，指数退避） |
| **JSON 解析失败** | 中 | 中 | 容错处理，记录 warning |
| **证据提取不准** | 中 | 中 | 后处理规则补充 |
| **评分不一致** | 高 | 中 | 明文评分规则表 + 标注规范 |

---

## 八、待拍板事项

### 8.1 现在必须拍板

| # | 决策项 | 可选方案 | 推荐方案 | 拍板结果 |
|---|--------|----------|----------|----------|
| 1 | **评分口径定义方式** | A. 仅 Prompt 描述；B. Prompt + 明文评分规则表；C. 先不定义 | **B** | ✅ **B**（2026-03-14） |
| 2 | **后处理规则复杂度** | A. 纯 Prompt，无规则；B. 轻量规范化；C. 复杂规则引擎 | **B** | ✅ **B**（2026-03-14） |
| 3 | **Few-shot 样例数量** | A. 每类 1 个（共 4 个）；B. 每类 2 个（共 8 个）；C. 每类 3+ 个 | **B（6 个：4 类 + 1 边界 + 1 负例）** | ✅ **B**（2026-03-14） |
| 4 | **首轮 benchmark 样本量** | A. 10 条；B. 30 条；C. 50+ 条 | **B** | ✅ **B**（2026-03-14） |
| 5 | **是否首轮引入后处理规则** | A. 先无规则；B. 只加轻量规范化；C. 直接上复杂规则引擎 | **B** | ✅ **B**（2026-03-14） |

### 8.2 可后置拍板

| # | 决策项 | 建议何时再定 | 触发条件 |
|---|--------|--------------|----------|
| 6 | **是否引入规则 + LLM 混合链路** | Week 2 | 首轮准确率 / 召回率不达标 |
| 7 | **是否扩充信号类别** | Week 2-3 | 四类无法覆盖主要样本 |
| 8 | **是否增加实体标准化与关系图谱** | Week 3 | 2.2 明确提出强依赖 |
| 9 | **是否让 2.4 上下文成为强制输入** | 待 2.4 真实能力稳定后 | 检索质量与接口形式已冻结 |

---

## 九、下一步行动

### 9.1 拍板已完成（2026-03-14）

✅ 用户已对 8.1 节的 5 个决策项完成拍板，全部采纳推荐方案：
1. 评分口径定义方式：Prompt + 明文评分规则表
2. 后处理规则复杂度：轻量规范化
3. Few-shot 样例数量：6 个（4 类 + 1 边界 + 1 负例）
4. 首轮 benchmark 样本量：30 条
5. 是否首轮引入后处理规则：只加轻量规范化

### 9.2 拍板后立即启动

1. **实现解码模块**：
   - 实现 `IntelligenceDecoder` 类
   - 实现 Prompt 模板
   - 实现后处理与校验

2. **构建 benchmark**：
   - 收集 30 条样本
   - 完成人工标注
   - 建立标注规范

3. **首轮测试**：
   - 运行 benchmark
   - 计算准确率、召回率、Schema 合法率
   - 出具验收报告

### 9.3 预期时间线

| 阶段 | 预计耗时 | 关键里程碑 |
|------|----------|-----------|
| 用户拍板 | 1 天 | 5 个决策项确认 |
| 实现解码模块 | 2-3 天 | 代码可运行 |
| 构建 benchmark | 2-3 天 | 30 条样本标注完成 |
| 首轮测试 | 1 天 | 验收报告产出 |
| **总计** | **6-8 天** | **MVP 闭环完成** |

---

## 十、一句话总结

> Phase 2.1 采用 **Prompt-first + 轻量后处理** 策略，将非结构化信息转化为四类范式信号（technical/market/team/capital），输出稳定的 JSON Schema，准确率 >= 80%、召回率 >= 75%，为 Phase 2.2 提供可稳定消费的结构化输入。
