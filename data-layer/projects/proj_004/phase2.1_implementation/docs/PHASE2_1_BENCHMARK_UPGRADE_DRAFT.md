# Phase 2.1 Benchmark 升级草案

**文档类型**: 评测设计草案 / Benchmark 升级文档  
**适用模块**: `Phase 2.1` 情报解码模块  
**归档位置**: `proj_004 / phase2.1_implementation / docs`  
**归档时间**: 2026-03-14  
**状态**: Draft v0.1（用于后续 benchmark 扩展与验收对齐）

---

## 一、为什么现在要补这份文档

当前 `Phase 2.1` 已经具备一个可以运行的 MVP 解码闭环：

- 有固定 `Signal` 契约
- 有 Prompt-first 解码链路
- 有基础 few-shot 样例
- 有标注规范、样本准备指南和 benchmark 验收指南

这意味着 `2.1` 的问题已经不再只是“能不能跑通”，而开始转向：

> **它到底是不是在稳定地产出对后续战略工作流真正有用的信号。**

如果只沿用当前基础 benchmark 口径，虽然可以回答：

- 字段抽得对不对
- JSON 合不合法
- 基本准确率和召回率是否达标

但还不够回答更本质的问题：

- 抽出来的是否真的是高价值变化
- 是否把行业噪音、营销话术、PR 表达误报成正式信号
- 模糊样本上是否能保持克制
- 输出是否真的更利于 `2.2` 等下游继续判断

因此，这份文档的目标不是推翻现有 benchmark，而是：

> **在保留 MVP 可执行性的前提下，把 `2.1` 的评测口径从“字段级正确”升级为“字段级正确 + 信号价值 + 噪音抑制 + 下游可消费性”。**

---

## 二、这次 benchmark 升级想解决什么问题

如果沿着 [PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md) 的模块定位继续往前推，`2.1` 不是普通抽取器，而是：

> **面向战略研究、项目孵化与生态投资的范式信号解码层。**

这会直接反推 benchmark 的关注点。

也就是说，未来我们评 `2.1` 的好坏，不能只看：

- 抽出几个 `signal`
- `signal_type` 对没对
- `description` 顺不顺

还要看：

- 这些信号是否值得进入战略雷达
- 是否压住了无价值噪音
- 是否在边界样本上保持低歧义
- 是否对后续排序、筛选和升级判断形成稳定输入

所以从第一性原理看，这次 benchmark 升级要解决的是四个问题：

1. **价值识别问题**：不是所有事实都值得作为正式信号进入系统
2. **噪音抑制问题**：不是所有看起来像变化的表述都应该被抽出来
3. **边界稳定问题**：模糊样本不能总是被高置信度提纯成信号
4. **下游消费问题**：结构化输出必须真的减少后续模块的二次解释负担

---

## 三、升级原则

### 3.1 不推翻现有 benchmark，而是在其上分层扩展

当前现有文档：

- [annotation_guidelines.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\annotation_guidelines.md)
- [sample_preparation_guide.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\sample_preparation_guide.md)
- [benchmark_validation_guide.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\benchmark_validation_guide.md)

已经足够支撑第一轮 MVP 验收。

因此这次升级不应重来，而应该分成：

- **MVP 基础验收层**：继续保留字段准确率、召回率、Schema 合法率
- **MVP 观察增强层**：增加价值密度、噪音抑制、边界样本稳定性观察
- **后续产品评测层**：等 `2.2 / 2.4` 联调更明确后，再纳入下游增益类指标

### 3.2 先保证可执行，再追求完整

如果 benchmark 口径一次扩太大，最容易出现的问题是：

- 标注成本失控
- 评测标准讨论过多、执行过慢
- 还没形成第一轮 baseline，就陷入抽象指标争论

因此本草案坚持一个原则：

> **先让 benchmark 升级为“可运行的轻量增强版”，而不是一次性做成最终版。**

### 3.3 先测“误报风险”，再谈“更聪明的生成”

对 `2.1` 来说，当前阶段更危险的问题通常不是“少抽了一点”，而是：

- 把普通新闻包装成战略信号
- 把营销稿包装成市场判断
- 把边界信息用高 `confidence_score` 输出

所以 benchmark 升级优先级应先偏向：

- precision
- noise suppression
- boundary stability

而不是优先追求更花哨的覆盖能力。

---

## 四、建议的 benchmark 分层结构

## 4.1 第一层：MVP 基础验收层（必须）

这部分继续沿用现有 benchmark 主骨架，作为正式验收项。

### 核心指标

- **Schema 合法率**
- **Signal-level Precision**
- **Signal-level Recall**
- **单次处理耗时**
- **输入源覆盖率**

### 仍然需要回答的问题

- 输出是否稳定符合 `schemas.py` 契约
- 是否能从 `news / report / announcement` 中抽出关键信号
- 是否达到当前 MVP 约定的性能底线

这部分是当前 `2.1 MVP` 能否“成立”的最小证明。

---

## 4.2 第二层：MVP 观察增强层（强烈建议）

这一层不一定立刻作为硬门槛，但应该从首轮 benchmark 开始记录。

### 新增观察维度 1：信号价值密度

核心问题：

> 抽出来的 `signals` 中，有多少是真正值得进入战略雷达的正式变化。

建议增加标注字段：

- `is_high_value_change`: 是否属于高价值变化
- `should_enter_formal_signal`: 是否应该进入正式信号
- `should_background_only`: 是否只应作为背景保留

重点不是让 `2.1` 直接做战略结论，而是观察它是否把大量低价值事实误包装成正式信号。

### 新增观察维度 2：噪音抑制能力

核心问题：

> 面对 PR 话术、泛行业空话、营销型表达时，模型是否足够克制。

建议增加标注字段：

- `is_pr_or_marketing`: 是否属于 PR / 营销型表达
- `is_industry_noise`: 是否属于行业噪音
- `false_positive_risk`: 若被抽出，是否属于高风险误报

### 新增观察维度 3：边界样本稳定性

核心问题：

> 模糊样本、传闻样本、弱证据样本上，模型是否能保持边界感。

建议增加标注字段：

- `is_boundary_case`: 是否属于边界样本
- `evidence_strength`: `strong | medium | weak`
- `should_lower_confidence`: 是否应显著压低 `confidence_score`

### 新增观察维度 4：下游初步可消费性

核心问题：

> 当前输出是否足够让后续模块少做一次“重新理解”。

建议增加人工观察字段：

- `label_is_actionable`: `signal_label` 是否足够清晰可比较
- `description_is_structured`: `description` 是否表达了明确变化事实
- `evidence_is_traceable`: `evidence_text` 是否能回到原文定位

这部分先以人工观察和案例复盘为主，不必在 MVP 阶段就做复杂自动化分数。

---

## 4.3 第三层：后续联合评测层（后置）

这部分建议等 `2.2` 或 `2.4 -> 2.1` 联调更明确后，再升级为正式 benchmark。

### 可能纳入的指标

- `2.2` 对 `Signal` 的可排序性评价
- 增强上下文前后 `signal_type` 准确率变化
- 引入 `ContextPacket` 后误报率是否下降
- 下游人工分析耗时是否下降
- 是否减少“重新读原文才能判断”的情况

这一层非常重要，但不建议在当前 MVP 阶段作为首轮硬门槛。

---

## 五、建议补充的样本类型结构

如果 benchmark 只按 `news / report / announcement` 来分，还不够覆盖真实风险。

建议在样本准备时，再叠加一个“语义场景类型”视角。

### 5.1 推荐的语义场景类型

- **明确高价值变化样本**
  - 融资、关键团队变化、技术路线升级、关键合作、明确能力跃迁
- **普通行业信息样本**
  - 一般市场动态、常规功能更新、常规项目进展
- **PR / 营销样本**
  - 宣发口号、泛趋势空话、带强宣传色彩的内容
- **边界样本**
  - 传闻、二手引用、弱证据推断、表达含糊不清
- **背景型样本**
  - 有信息量，但更适合作为背景知识，而非正式信号

### 5.2 为什么要这样分

因为当前 `2.1` 最值得防的产品风险不是“不会抽”，而是：

- 会不会把普通信息抽成高价值信号
- 会不会把营销文本抽成正式变化
- 会不会在边界材料上过度自信

所以 benchmark 样本的结构必须能暴露这些问题。

---

## 六、推荐的升级后标注表字段

在现有标注字段之外，建议增加一组轻量扩展字段：

| 字段 | 含义 | 阶段建议 |
|------|------|----------|
| `is_high_value_change` | 是否属于高价值变化 | MVP 观察项 |
| `should_enter_formal_signal` | 是否应进入正式信号 | MVP 观察项 |
| `should_background_only` | 是否应只做背景保留 | MVP 观察项 |
| `is_pr_or_marketing` | 是否为 PR / 营销表达 | MVP 观察项 |
| `is_industry_noise` | 是否为行业噪音 | MVP 观察项 |
| `is_boundary_case` | 是否为边界样本 | MVP 观察项 |
| `evidence_strength` | 原文证据强度 | MVP 观察项 |
| `should_lower_confidence` | 是否应下调 `confidence_score` | MVP 观察项 |
| `label_is_actionable` | 标签是否清晰可比较 | 人工复盘项 |
| `description_is_structured` | 描述是否表达明确变化 | 人工复盘项 |
| `evidence_is_traceable` | 证据是否可追溯 | 人工复盘项 |

这样做的好处是：

- 不需要重写整套 benchmark 工具链
- 可以先用人工标注 / 表格记录跑起来
- 后续如果要程序化统计，也有字段基础

---

## 七、推荐的错误分类框架

为了让 benchmark 真正能指导后续 prompt / few-shot 迭代，建议从第一轮开始就记录错误类型，而不是只看总分。

### 7.1 推荐的一级错误类型

- **漏报**：应该抽出的高价值信号没有抽出来
- **误报**：不应该进入正式信号的内容被抽出来
- **错类**：`signal_type` 分类错误
- **命名漂移**：`signal_label` 不稳定或不可比较
- **描述弱化**：`description` 没有明确表达变化事实
- **证据失真**：`evidence_text` 过泛、不可追溯或非主证据
- **置信度失真**：`confidence_score` 与证据强弱不匹配

### 7.2 特别值得单独关注的误报子类

- **PR 误报**：把营销文案误抽为 `market` / `technical`
- **背景误报**：应保留为背景却被抽成正式信号
- **传闻高置信误报**：弱证据样本却输出高 `confidence_score`
- **泛事实误报**：普通项目动态被包装成高价值变化

这些错误类型会直接反推后续是否需要升级：

- Prompt 角色设定
- few-shot 样例结构
- `2.4` 约束 / glossary / boundary case 增强

---

## 八、推荐的 benchmark 输出物

跑完升级版 benchmark 后，建议不只输出一个总分，而输出四类结果：

### 8.1 基础指标表

- Precision
- Recall
- Schema 合法率
- 平均耗时

### 8.2 价值 / 噪音观察表

- 高价值变化命中情况
- PR / 噪音误报情况
- 背景型内容是否被误升格

### 8.3 错误分布表

- 各类误报占比
- 各类漏报占比
- 不同 `source_type` 的主要问题

### 8.4 代表性案例复盘

至少整理：

- 2 条高质量正例
- 2 条典型误报
- 2 条典型漏报
- 2 条边界样本

这会比单纯看平均分更能指导后续 prompt 和 few-shot 升级。

---

## 九、这会如何影响后续 Prompt / few-shot 迭代

这份 benchmark 草案本身不是独立存在的，它会直接反推 Prompt 设计。

如果首轮 benchmark 发现：

- `PR 误报` 很多
- `market` 分类泛化严重
- 弱证据样本 `confidence_score` 偏高
- `signal_label` 命名不稳定

那么下一步最合理的动作不是盲目增加模型能力，而是：

- 调整角色设定，使其更靠近“战略工作流前端解码器”
- 补边界样本和负例 few-shot
- 补“高价值变化 vs 背景 / 噪音”的判别样例
- 必要时引入 `constraint / glossary / few_shot` 类 `ContextPacket`

也就是说：

> **benchmark 升级的意义，不只是让评测更完整，而是为后续迭代提供更可执行的误差画像。**

---

## 十、MVP 阶段最推荐的落地方式

为了保持实现速度与评测收益平衡，当前最推荐的不是一步到位，而是：

### 10.1 先跑基础 benchmark + 轻量增强字段

即：

- 基础指标照旧
- 在标注表中加入扩展观察字段
- 先以人工复盘方式输出价值 / 噪音 / 边界结论

### 10.2 先不把所有观察项都变成一票否决的硬指标

原因是：

- 当前 MVP 首轮目标是建立 baseline
- 价值密度、噪音抑制等指标还需要通过一轮真实样本复盘进一步收口定义

### 10.3 先基于错误模式决定是否升级 prompt

不要在没跑 benchmark 之前就大改 Prompt 体系。

先测，再改，才能把每次迭代的收益讲清楚。

---

## 十一、当前阶段的结论

如果用一句话总结这份 benchmark 升级草案，可以写成：

> **`2.1` 的 benchmark 不应只回答“抽得对不对”，还应开始回答“抽出来的东西是否值得进入战略工作流”。**

因此，这次升级最适合的方向不是推翻现有 benchmark，而是：

> **在当前 MVP 验收框架上，轻量补入信号价值密度、噪音抑制、边界稳定性和初步下游可消费性观察。**

---

## 十二、下一步建议

基于当前阶段，最推荐的动作是：

1. **在现有标注模板中补充本草案建议的扩展字段**
2. **按“来源类型 + 语义场景类型”双视角准备首轮 benchmark 样本**
3. **首轮 benchmark 报告中增加“误报 / 漏报 / 边界样本”专门章节**
4. **根据错误画像决定是否启动 Prompt 角色设定与 few-shot 样例升级**

---

**文档状态**: ✅ 已完成  
**版本**: v0.1 Draft  
**建议下次更新时机**: 当首轮 benchmark 跑完、错误类型分布清晰，或 `2.1` 正式引入更强的 Prompt / `2.4` 增强策略时
