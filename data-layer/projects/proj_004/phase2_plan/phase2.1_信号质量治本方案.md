# Phase 2.1 V2 拍板稿：结构化逻辑字段与信号可靠性增强

> **文档类型**：设计方案 / V2 拍板稿
> **状态**：✅ 建议拍板
> **提出日期**：2026-04-01
> **作者**：助理
> **关联模块**：`phase2.1_implementation/decoder.py`、`prompt_templates.py`、`schemas.py`
> **关联背景**：`docs/step_a_design_discussion.md`、`background/2.2 Discussion/2_2StepA方案_*.txt`、`phase2.1_implementation/docs/PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md`

---

## 一、为什么这份方案要重写

这份文档原本聚焦于：

- 在 `2.1` 后处理阶段增加打分截断
- 对 `signal_type` 做强枚举校验
- 补一个 `score_rationale`

这个方向并非完全错误，但在补充了 `Step A` 痛点复盘、`OpenClaw` 对三家 AI 方案的综合结论，以及 `2.1 / 2.2` 的第一性原理定位之后，可以确认：

> **上一版方案更像“后验修补”，而不是“治本升级”。**

真正触发 `2.1` 重写的，不是“分数偶尔不稳”本身，而是 `2.2 Step A` 暴露出的系统性问题：

- `Step A` 退化为按语义相似或领域重叠做粗分组
- 错误分组污染 `Step C` 判断前提
- 跨域机会链条被拆散
- `description[:100]` 的信息密度不足以支撑“逻辑互补判断”

也就是说，问题根源不在于“打分没有第二个裁判”，而在于：

> **`2.1` 输出给 `2.2` 的信号，缺少足够稳定的结构化逻辑信息。**

因此，本次 `V2` 重写不再把重点放在“在线二次裁分”，而是转向：

- **增加结构化逻辑字段，提升信号的信息密度与可计算性**
- **保留轻量可靠性审计，但不让 `2.1` 越界变成 mini `2.2`**

---

## 二、需求来源与当前整体计划

### 2.1 需求来源

本次 `2.1 V2` 不是孤立产生，而是来自以下三层共识叠加：

#### 1）来自 `Step A` 痛点复盘

根据 [step_a_design_discussion.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\docs\step_a_design_discussion.md) 的结论，当前核心痛点是：

- `Step A` 不应继续承担“硬分组裁判”的职责
- `Step A` 退化为语义相似分组，不是 prompt 文案小问题，而是输入信号信息密度不足
- 真正重要的是让 `Step C` 接收“候选逻辑路径 / 候选集”，而不是被提前硬隔离的错误子集

#### 2）来自 `OpenClaw` 汇总的三家 AI 结论

综合 `Gemini / Kimi / DeepSeek` 三份方案，可以收敛出三个稳定结论：

- **准确性最关键的改动**：在 `2.1` 阶段增加结构化逻辑字段，如 `what_changed`、`change_direction`、`affects`
- **效率最优的中等批次方案**：`Anchor-based Window`，即以高价值信号为锚，拉取互补信号组成 10–15 条候选集
- **架构上最该先修的点**：`Step A` 输出应从 `signal_groups` 转向 `logical_scenarios` / 软约束，而非继续做硬分组

#### 3）来自 `2.1 / 2.2` 的第一性原理定位

- `2.1` 的本质是**范式信号解码层**，负责把高熵外部情报转成低歧义、可进入后续工作流的信号单元
- `2.2` 的本质是**机会判断层**，负责把信号升级为可被组织进一步处理的机会对象

因此 `2.1` 应该做的是：

- 提供更稳定、更可追溯、更可组合的信号输入

而不应该做的是：

- 再加一个 LLM 在线裁判“这个分数到底对不对”
- 提前替 `2.2` 完成机会级判断

---

### 2.2 当前整体计划（与 `2.2` 对齐）

本方案默认以下路径已经成立：

#### Step 1（已完成）

- **小批次 `≤ 15` 条信号**：跳过 `Step A`，全量直送 `Step C`
- 目标：避免小批次场景下的过度预处理与前置污染

#### Step 2（短期，`2.2` 侧）

- `Step A` 输出从 `signal_groups` 改为 `logical_scenarios`
- `Step C` 接收“候选逻辑场景 + 候选信号”，而非“硬隔离子集”
- 同步增强 `Step A prompt few-shot`

#### Step 3（中期，`2.1` 侧，本文核心）

- 在 `2.1` 解码阶段增加结构化逻辑字段
- 让 `Step A` 的粗筛从“读模糊短文本做推理”变成“基于结构化字段做规则匹配 / 轻量推理”

#### Step 4（大批次，按需）

- 当 `50+` 条高密度复杂信号出现时，再引入假说驱动 / 漏斗式处理
- 该阶段依赖 `Step 3` 的结构化字段作为基础，不宜倒序推进

---

## 三、对上一版方案的修正结论

基于新增背景，本方案对上一版做如下明确修正。

### 3.1 不再把“在线二次裁分”作为主方案

上一版把重点放在：

- `intensity_score` 截断
- `confidence_score` 语义 warning
- `score_rationale` 辅助解释

这类措施可以保留一小部分，但它们只能解决**表现层异常**，不能解决 `Step A` 为何拿不到足够逻辑信息的问题。

因此，`V2` 结论是：

> **后验规则审计保留，但降级为辅助层；主方案切换为“结构化逻辑字段增强”。**

### 3.2 强枚举只解决“契约稳定”，不能替代“语义正确”

上一版默认：

- 非法 `signal_type` 直接丢弃

现在明确调整为：

- 强枚举依然需要
- 但它解决的是**输出契约稳定性问题**，不是“`capital` 被误判成 `market`”这种语义归类错误
- 因此不能把强枚举当作分类质量方案的主体

### 3.3 `score_rationale` 不再是 `V2` 的中心

`score_rationale` 有调试价值，但它不是当前最关键的能力缺口。

当前最关键的缺口是：

- 信号是否足够表达“发生了什么变化”
- 变化方向是什么
- 影响对象是谁

因此 `score_rationale` 从 `V2` 主轴降级为：

- 可选调试增强项
- 非本轮必须交付项

---

## 四、`2.1 V2` 的目标与边界

### 4.1 目标

`2.1 V2` 的目标不是让 `2.1` 更会“解释”，而是让它更稳定地输出：

- **高价值信号事实**
- **结构化逻辑信息**
- **可被 `Step A / Step B / Step C` 消费的中间层字段**
- **轻量但可追溯的可靠性状态**

### 4.2 非目标

本方案明确不做以下事情：

- 不引入第二个 LLM 做在线“分数仲裁”
- 不让 `2.1` 输出机会假说、机会论点或优先级
- 不让 `2.1` 变成 `2.2` 的缩写版
- 不试图在本轮通过复杂规则彻底修正所有语义误判

### 4.3 一句话定义

> **`2.1 V2` 的本质，是把“可追溯信号”进一步升级为“可逻辑组合、可规则消费、可可靠性标记”的信号对象。**

---

## 五、`V2` 核心方案

`2.1 V2` 由两层组成：

- **主层：结构化逻辑字段增强**
- **辅层：轻量可靠性审计与修复**

### 5.1 主层：结构化逻辑字段增强（治本层）

这是 `V2` 的核心。

#### 设计原则

新增字段必须满足两条约束：

- **足够帮助 `Step A` 做逻辑互补判断**
- **又不越界到机会判断层**

因此本轮不推荐直接让 `2.1` 输出“机会意义”或“投资含义”，而是推荐输出最小必要的逻辑框架。

#### 推荐新增字段

建议在 `Signal` 中新增一个嵌套对象 `logic_frame`：

```json
{
  "logic_frame": {
    "what_changed": "string",
    "change_direction": "increase|decrease|tighten|loosen|enter|exit|shift|validate|invalidate|unknown",
    "affects": ["string"]
  }
}
```

#### 字段定义

##### `what_changed`

表示**哪一个变量发生了变化**，不是机会结论，不是观点包装。

示例：

- `platform_policy`
- `ai_tool_cost`
- `studio_headcount`
- `funding_availability`
- `distribution_access`
- `genre_demand`

##### `change_direction`

表示变化方向，尽量使用小而稳定的枚举，而不是自然语言自由发挥。

建议首版枚举：

- `increase`
- `decrease`
- `tighten`
- `loosen`
- `enter`
- `exit`
- `shift`
- `validate`
- `invalidate`
- `unknown`

**拍板规则**：`change_direction` 在首版中保持**单值**。

原因不是现实世界只有一个方向，而是：

- 一个 `logic_frame` 需要稳定描述**一个主变化变量**
- 如果方向改成多值，下游会立刻失去“这个方向到底对应哪个变量”的可计算语义
- `Step A / Step B` 需要的是稳定规则消费字段，而不是把所有复杂现实压进一个对象

如果一段原文同时包含多个方向不同的独立变化，优先策略不是把 `change_direction` 变成数组，而是：

- **优先拆成多条 `Signal`**
- 每条 `Signal` 各自维护单独的 `logic_frame`

##### `affects`

表示这条变化主要影响谁。

示例：

- `indie studios`
- `mid-size publishers`
- `mobile developers`
- `ugc platforms`
- `western console audience`

**拍板规则**：`affects` 允许**多值**。

原因是受影响对象天然可能不止一个，而这类多对象表达不会破坏 `logic_frame` 的主语义稳定性。也就是说：

- `what_changed`：单值，描述一个主变量
- `change_direction`：单值，描述该主变量的变化方向
- `affects`：多值，描述这一变化主要影响哪些对象

#### 为什么是这三个字段

因为这三个字段已经足够让下游回答：

- 这条信号在说**什么变量**变了
- 这个变量是**朝什么方向**变了
- 这件事主要**影响谁**

这正是 `Step A` 从“模糊文本匹配”走向“逻辑互补匹配”所需的最低信息集。

#### 多对象 / 多方向影响的编码规则（拍板建议）

这是本轮最容易产生歧义的地方，因此单独拍板如下：

- **允许一个变化影响多个对象**：因此 `affects` 使用 `List[str]`
- **不允许一个 `logic_frame` 同时表达多个方向**：因此 `change_direction` 保持单值
- **如果原文同时包含多个独立变化**，优先拆成多条 `Signal`，而不是在一条 `Signal` 的 `logic_frame` 中塞多个方向

例如：

- `platform_fee_rate` 下降
- `developer_margin` 上升

这更适合拆成两条 `Signal`，而不是写成一个带双方向的 `logic_frame`。

这条规则的底层原则是：

> **结构化字段的首要目标不是完整复刻现实复杂度，而是保证下游可消费性、可匹配性与可计算性。**

#### 多独立变化拆分的可实施规范（工程口径）

为避免“设计已拍板，但实现时各自理解不同”，本轮补充如下工程口径：

##### 1）什么时候必须拆成多条 `Signal`

满足任一条件时，应拆成多条 `Signal`：

- 原文中出现了**两个以上主变量**分别发生变化
- 原文中出现了**两个以上方向不同**的独立变化
- 同一段文字中，若把内容写进一个 `logic_frame` 后，会导致 `what_changed` 与 `change_direction` 无法稳定一一对应

典型例子：

- `platform_policy` 收紧，同时 `distribution_access` 放宽
- `studio_headcount` 下降，同时 `outsourcing_demand` 上升

##### 2）什么时候不应拆分

以下情况不应拆成多条 `Signal`：

- 只是**一个主变化影响多个对象**
- 只是主变化的背景解释、原因说明、结果说明
- 只是同一资本/团队/监管事件的补充上下文

此时应保留一条 `Signal`，并通过：

- `affects` 表达多个受影响对象
- `description` 保留必要上下文

##### 3）拆分职责归属

本轮明确：

- **主拆分职责在 `prompt + few-shot`**，由 `2.1` 抽取阶段直接输出多条 `Signal`
- **`decoder` 不承担重型语义拆分职责**，只做契约规范化、审计标记和安全降级
- 如果模型未按要求拆分，而是输出了模糊的单条信号，`decoder` 可以：
  - 标记 `audit_flags`
  - 将 `change_direction` 降为 `unknown`
  - 保留信号进入主链路
- **`decoder` 不应基于启发式规则强行把一条信号自动拆成两条**，避免误拆

##### 4）Step A / Step C 的消费语义

当 `2.1` 已将一段原文拆成多条 `Signal` 时：

- `Step A` 应将其视为**多个独立变化单元**参与逻辑互补判断
- `Step C` 应可同时看到这些拆分后的信号，但**不得默认它们必然属于同一个机会对象**
- 是否在机会层再次合并，应由 `2.2` 基于完整逻辑链判断，而不是由 `2.1` 预先绑定

##### 5）验收语义

本轮验收不要求“所有多变化文本都完美拆分”，但至少应满足：

- 多独立变化样本中，模型已能稳定产出一部分拆分正确的样例
- `change_direction` 不再依赖多值表达复杂变化
- `logic_frame` 的缺失或不合法，不会导致整条信号被直接丢弃
- `Step A` 在 `logic_frame` 可用时，优先消费结构化字段；缺失时可回退旧路径

#### `what_changed` 的口径规范（拍板建议）

`what_changed` 是本方案里最容易漂移的字段，因此本拍板稿明确要求：

- **它必须描述“发生变化的变量”**，而不是机会判断、投资含义或行动建议
- **优先写成短语型变量名**，而不是长句解释
- **允许首版保持自由文本**，但必须遵守口径示例；后续若离散度过高，再补词表收口

推荐写法示例：

- `platform_policy`
- `funding_availability`
- `distribution_access`
- `ai_tool_cost`
- `studio_headcount`
- `genre_demand`
- `compliance_cost`
- `publisher_appetite`

不推荐写法示例：

- `indie opportunity is rising`
- `this may create a strategic acquisition window`
- `mobile game teams should pivot to AI`
- `投资价值显著提升`
- `建议公司重点关注`

一句话判断标准：

> **如果这段文字更像“结论”或“建议”，那它就不是合格的 `what_changed`。**

#### `logic_frame` 的不过界规则（拍板建议）

为防止 `2.1` 越界到 `2.2`，本拍板稿对 `logic_frame` 做如下硬约束：

- `what_changed`：只能描述变量变化，**不得**写机会结论
- `change_direction`：只能描述变化方向，**不得**写价值判断
- `affects`：只能描述受影响对象，**不得**写商业含义、投资含义、组织动作

明确禁止出现在 `logic_frame` 中的内容：

- 机会判断
- 投资建议
- 优先级表达
- 行动建议
- 收益推演
- 公司 should / ought / 建议 / 应该 类措辞

如果模型无法在不越界的前提下给出内容，宁可输出：

- `change_direction="unknown"`
- `affects=[]`

也不要为了“看起来完整”而脑补机会结论。

---

### 5.2 辅层：轻量可靠性审计（辅助层）

相比上一版，本方案保留“可靠性治理”，但调整为**审计优先，强改值靠后**。

#### 核心原则

- 先标记异常，再决定是否修复
- 优先做契约稳定，不随意做语义重判
- 原始分数尽量保留，可通过审计信息供下游感知

#### 可靠性审计覆盖内容

##### 1）契约规范化

- `signal_type`：`strip + lower`
- score 范围：`1–10 clamp`
- `source_ref` / `extracted_at` 缺失兜底
- `logic_frame.affects` 缺失时统一为空数组

##### 2）类型合法性检查

允许值仍为：

- `technical`
- `market`
- `team`
- `capital`
- `regulatory`

但处理策略改为三段式：

- **格式问题**：直接规范化
- **低歧义 alias**：安全映射
- **仍非法**：进入隔离 / warning，不再简单视为“这条信号无意义”

##### 3）分数一致性审计

本轮不把复杂截断规则作为主轴，而改为生成审计标记，例如：

- `low_conf_high_intensity`
- `short_evidence_high_intensity`
- `uncertain_wording_high_confidence`
- `official_wording_low_confidence`

这些标记用于：

- dashboard 调试
- benchmark 分析
- 未来决定是否需要升级成 hard rule

##### 4）修复痕迹保留

如发生规范化或类型修复，保留：

- `raw_signal_type`
- `normalized_signal_type`
- `type_repair_mode`
- `audit_flags`

---

## 六、Schema 设计建议

### 6.1 本轮建议：核心业务字段入 schema，调试字段入 metadata

和上一版不同，这次建议**有选择地修改 `schemas.py`**。

#### 应入正式 schema 的字段

因为 `logic_frame` 会被 `Step A / Step B / Step C` 稳定消费，属于正式业务契约，所以建议作为正式字段进入 `Signal`：

```python
logic_frame: Optional[SignalLogicFrame] = None
```

#### 不建议入正式 schema 的字段

下列字段优先进入 `metadata.audit`，而不是立刻升级为顶层字段：

- `score_rationale`
- `raw_signal_type`
- `normalized_signal_type`
- `audit_flags`
- `suggested_intensity_ceiling`
- `type_repair_mode`

原因是这些字段当前更偏：

- 调试信息
- 审计信息
- 中间过程痕迹

它们不应在本轮和正式业务字段混为一层。

---

### 6.2 推荐数据结构

建议在 `schemas.py` 中新增：

```python
class SignalLogicFrame(BaseModel):
    what_changed: str = Field(..., description="发生变化的变量")
    change_direction: str = Field(..., description="变化方向")
    affects: List[str] = Field(default_factory=list, description="主要受影响对象")
```

并在 `Signal` 中新增：

```python
logic_frame: Optional[SignalLogicFrame] = Field(
    default=None,
    description="供 Step A / Step B / Step C 消费的最小结构化逻辑框架"
)
```

---

## 七、Prompt 与 Decoder 的改造方向

### 7.1 Prompt 改造重点

`2.1` prompt 不应让模型“更会解释机会”，而应让它：

- 更稳定地区分事实与解释
- 在每条 `Signal` 中补足最小逻辑框架
- 对 `logic_frame` 输出使用约束更强的 schema

#### Prompt 需新增的约束说明

- `what_changed` 只能写“发生变化的变量”，不能写机会结论
- `change_direction` 只能从限定枚举中选
- `affects` 只写受影响对象，不写推导性结论
- 如果原文证据不足，可输出 `unknown` 或空数组，不强行脑补

### 7.2 Few-shot 改造重点

few-shot 不仅要示范 `signal_type` 和 `scores`，还应示范：

- 同一条信号如何抽出 `what_changed`
- 什么叫合格的 `change_direction`
- `affects` 应写“被影响对象”，而不是“后续商业机会”

### 7.3 Decoder 改造重点

建议在 `_post_process()` 之后加入：

- `normalize_signal_contract()`
- `audit_signal_reliability()`

但不建议继续沿用“以大量 hard clipping 为中心”的 `_normalize_signals()` 设计。

更合适的顺序是：

```text
LLM 输出
→ JSON 解析
→ 契约规范化
→ 可靠性审计
→ Schema 校验
→ 输出 DecodedIntelligence
```

---

## 八、`2.1 V2` 如何服务 `Step A / Step C`

### 8.1 对 `Step A` 的直接价值

有了 `logic_frame` 之后，`Step A` 的粗筛依据不再只剩：

- `label`
- `description[:100]`
- `signal_type`
- `intensity_score`

而会变成：

- `signal_type`
- `logic_frame.what_changed`
- `logic_frame.change_direction`
- `logic_frame.affects`
- `intensity/confidence/timeliness`

这会直接带来三个变化：

- `Step A` 更容易做逻辑互补匹配，而不是语义相似匹配
- `Anchor-based Window` 的候选集检索会更稳定
- 一部分匹配甚至可以规则化，不必强依赖轻量 LLM 自由推理

### 8.2 对 `Step C` 的间接价值

`Step C` 不直接消费所有底层字段，但会受益于：

- `Step A` 候选集质量提升
- 跨域信号不再被轻易拆散
- 输入的“逻辑路径提示”更可信

### 8.3 对 `Signal Store / Step B` 的价值

`logic_frame` 还能增强跨批次匹配，因为历史信号可按以下维度查询：

- 变量相近：`what_changed`
- 方向互补 / 一致：`change_direction`
- 影响对象重合：`affects`

这比单靠 `signal_type` 或角色词表更接近真实业务逻辑。

---

## 九、为什么这是当前最优后续方案

结合“实用性、准确性、效率”三个维度，当前最优路径可以明确收敛为：

### 9.1 准确性：`2.1` 增加结构化逻辑字段是最大增益项

这是三家 AI 结论最一致的一点，也是本方案的主轴。

原因：

- `Step A` 误分组的根因是信息层缺失，不是 prompt 小瑕疵
- 若信号本身自带结构化逻辑标签，粗筛能从“猜关系”转为“匹配关系”
- 这类收益是结构性的，不是局部打补丁式的

### 9.2 效率：中等批次应优先配合 `Anchor-based Window`

在 `21–50` 条信号场景下，效率最优的不是动态多轮调用，也不是立刻上完整假说生成，而是：

- 用 `Step A` 生成 `logical_scenarios` / 候选关系
- 以高价值信号为锚，拉取互补信号形成一个 10–15 条候选集
- 将该候选集送入 `Step C`

而这一路径是否稳定，取决于 `2.1` 是否先把逻辑字段补足。

### 9.3 实用性：短期先修架构，中期补信息层，长期再上假说驱动

因此最现实的落地顺序不是“二选一”，而是：

- `Step 2`：修 `2.2 Step A` 架构
- `Step 3`：修 `2.1` 信息密度
- `Step 4`：再考虑大批次假说驱动

也就是说：

> **`Step 2` 解决前提污染，`Step 3` 解决信息不足。两者不是互斥，而是前后衔接。**

---

## 十、实施建议

### 10.1 本轮推荐实施范围

#### 必做

- `schemas.py`：新增 `SignalLogicFrame` 与 `Signal.logic_frame`
- `prompt_templates.py`：扩展 JSON schema 与 few-shot，要求输出 `logic_frame`
- `decoder.py`：新增契约规范化与可靠性审计流程
- `metadata.audit`：承载审计标记与修复痕迹

#### 建议做

- 为 `change_direction` 建一个小枚举，不允许自由文本漂移
- 增加 `logic_frame` 缺失时的 warning，而不是强制丢弃
- 为英文样本与中文样本同时示范 `logic_frame` few-shot

#### `logic_frame` 缺失时的降级策略（拍板建议）

本拍板稿明确：**`logic_frame` 缺失不构成丢弃条件**。

当单条信号缺失 `logic_frame` 或其中字段不完整时，处理策略如下：

1. **信号继续进入主链路**，不因 `logic_frame` 缺失被过滤
2. 在 `metadata.audit` 中增加标记，例如：
   - `missing_logic_frame`
   - `missing_what_changed`
   - `invalid_change_direction`
3. `Step A / Step B` 在消费时：
   - 优先使用结构化字段进行规则匹配
   - 若缺失，则退回现有的 `signal_type + label + description + roles` 轻量推理路径
4. benchmark 与 dashboard 需要统计：
   - `logic_frame` 覆盖率
   - 各字段缺失率
   - 缺失样本对 `Step A` 命中质量的影响

也就是说，本轮策略是：

> **不过滤，只标记；不阻断，只降级。**

#### 本轮不建议做

- 在线第二个 LLM 复核分数
- 大量 hard clipping 改写 `intensity_score`
- 强行引入完整假说生成模块
- 将 `score_rationale` 升级为正式顶层字段

---

## 十一、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| `logic_frame` 输出不稳定，反而引入新噪音 | 中 | 用小枚举约束 `change_direction`，few-shot 强示例，允许 `unknown`，避免强行脑补 |
| `2.1` 越界，开始输出机会结论 | 高 | 在 prompt 中明确禁止“机会意义/投资含义”类表述，只允许描述变量变化与受影响对象 |
| 修改 schema 影响下游兼容性 | 中 | `logic_frame` 先设为可选字段，下游渐进消费 |
| 可靠性审计过重，掩盖原始分数 | 中 | 先记 `audit_flags`，后续再根据 benchmark 决定是否升级为 hard rule |
| `what_changed` 自由文本过散 | 中 | 通过 few-shot 和后验归一逐步收口，必要时后续增加词表规范 |

---

## 十二、验收标准

### 12.1 `2.1` 输出层验收

- `Signal` 能稳定输出 `logic_frame`
- `change_direction` 枚举合法率显著提升
- `logic_frame` 缺失率可被统计与追踪
- 审计信息进入 `metadata.audit`，且不影响现有主链路字段

### 12.2 `Step A` 消费层验收

- `Step A` 对跨域互补信号的召回提升
- 按语义相似误分组的比例下降
- `logical_scenarios` 的候选质量高于旧版 `signal_groups`

### 12.3 系统层验收

- `≤ 15` 条小批次仍维持 direct pass，不被复杂化
- `21–50` 条中等批次下，候选集质量提升且调用链未明显变长
- benchmark 中“高质量但跨域”的机会样本召回改善

---

## 十三、拍板结论

| # | 拍板项 | 结论 |
|---|--------|------|
| 1 | `logic_frame` 是否作为正式 schema 字段进入 `Signal` | **通过**。作为正式业务契约进入 schema |
| 2 | `logic_frame` 是否只保留 3 个最小字段 | **通过**。首版固定为 `what_changed / change_direction / affects` |
| 3 | `change_direction` 是否采用小枚举 | **通过**。首版使用小枚举，禁止自由文本 |
| 4 | `change_direction` 是否允许多值 | **不通过**。首版保持单值，复杂多方向影响优先拆为多条 `Signal` |
| 5 | `affects` 是否允许多值 | **通过**。允许多值，用于表达多个受影响对象 |
| 6 | `score_rationale` 是否作为本轮必须项 | **不通过**。本轮不作为必须交付，后置为调试增强 |
| 7 | 是否继续保留上一版“大量 hard clipping 规则” | **不通过**。不作为主方案，只保留轻量 audit flags |
| 8 | `logic_frame` 缺失是否丢弃信号 | **不通过**。信号继续进入主链路，仅做 audit 标记与消费降级 |
| 9 | `what_changed` 是否允许写机会结论/建议 | **不通过**。只能描述变量变化，不得写结论或建议 |

---

## 十四、最终结论

本轮重写后的 `2.1 V2` 结论非常明确：

> **`2.1` 真正要修的不是“再找一个裁判盯分数”，而是“让信号本身带上足够稳定的结构化逻辑信息”。**

因此，从当前阶段的实用性、准确性、效率综合看，最优后续路径是：

1. **承认 `Step 1` 已完成**：小批次 direct pass 继续保留
2. **先推进 `Step 2`**：`Step A` 从硬分组改为 `logical_scenarios` / 软约束
3. **同步推进本文 `Step 3`**：在 `2.1` 中新增 `logic_frame`，提升信息密度与可计算性
4. **将可靠性治理降级为辅助层**：做契约规范化与审计标记，而不是在线二次裁分
5. **把 `Step 4` 假说驱动留到大批次场景**：待结构化字段与候选集机制稳定后再上

一句话总结：

> **`Step 2` 修架构，`Step 3` 修信息层；真正的 `2.1 V2`，应当是“结构化逻辑字段增强 + 轻量可靠性审计”，而不是“后验打分截断器”。**

---

**文档状态**：`v2.0` 草稿，待拍板  
**最后更新**：2026-04-01
