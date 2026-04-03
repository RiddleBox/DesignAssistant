# Phase 2.2 Signal Store 迭代设计方案 v2

> **文档类型**：2.2 内部迭代设计方案
> **创建日期**：2026-03-30
> **状态**：📝 设计完成，待实现
> **范围**：纯 2.2 内部改造，不改变 2.1→2.2 输入契约、2.2→2.3 输出契约

---

## 一、背景与问题定义

### 1.1 当前设计的核心缺陷

**现状**：2.1 提取出信号 → 2.2 直接进入"寻找机会"的判断框架，默认信号一定能形成机会。

**问题**：现实中大量"有信号但不构成机会"的情况无法处理：

| 情况 | 当前行为 | 期望行为 |
|------|---------|---------|
| 单条信号缺少佐证，论点不完整 | 强行输出低质量机会对象，或规则引擎 fallback 输出空壳 | 暂存信号，等待补全 |
| 信号是威胁/风险，而非机会 | 被误判为机会，或输出"watch"级别机会混淆决策 | 标记为风险信号，不进入机会流程 |
| 跨批次积累才能成立的机会 | 每批次独立判断，永远看不到全貌 | 信号跨批次积累，条件成熟时触发判断 |

**典型场景**：
- `incoming_005`（EU DMA 罚苹果）：强度9的监管信号，单独看对中国手游团队是风险监控而非进攻机会；但若6个月后出现"开发者大量出走App Store"+"安卓侧载松动"，三条信号组合才形成"移动端分发格局重构"的机会论点
- `incoming_025`（腾讯GDC GenAI动画）：技术信号，被粗筛误杀为噪音；即使通过，单独也难以形成完整机会论点

### 1.2 需求定义

**核心需求**：
1. 2.2 有合法的"当前无法形成机会"出口，不强行结论
2. 未成机会的信号保留并积累，参与后续批次的组合尝试
3. 信号规模增长后，检索效率不应线性下降（O(n) 遍历不可接受）
4. 新信号进来时能主动找到历史中"等待它"的信号，实现跨批次唤醒

**约束条件**：
- 纯 2.2 内部改造：2.1→2.2 接口（`List[DecodedIntelligence]`）不变，2.2→2.3 接口（`OpportunityObject`）不变
- 尽量复用现有 2.4 RAG 基础设施，不重建存储层
- 每批次 50-100 条信号的处理效率要求：单批次处理时间增量 < 30s（不含冷却等待）

---

## 二、设计方案

### 2.1 总体架构

```
2.1 提取的当次信号池
        ↓
┌─────────────────────────────────────────┐
│  2.2 新三步流程（纯内部）               │
│                                         │
│  Step A：批内聚类 + 信号角色标注        │
│      ↓ 批内可组合 → Step C             │
│      ↓ 孤立信号  → Step B              │
│                                         │
│  Step B：历史信号检索（角色缺口匹配）   │
│      ↓ 找到伙伴 → 轻量确认 → Step C   │
│      ↓ 未找到   → 写入 Signal Store    │
│                                         │
│  Step C：完整机会判断（现有逻辑，不变） │
│      ↓ 有机会 → OpportunityObject → 2.3│
│      ↓ 无机会 → 信号写入 Signal Store  │
└─────────────────────────────────────────┘
        ↓
  2.3 消费 OpportunityObject（接口不变）
```

**关键原则**：2.3 收到的 OpportunityObject 格式与现在完全一致；如果当批次没有机会产出，2.3 不被调用（现有行为也是如此）。

---

### 2.2 Signal Store 存储设计

**存储位置**：复用 2.4 RAG 的 FAISS 索引 + pickle 存储，增加独立分区（独立的 pkl 文件），不与背景知识库混存。

**为什么独立分区而不是混入**：
- RAG 知识库存"静态背景知识"（案例模式/行业规律/判断规则）
- Signal Store 存"动态时效事件"（具体信号片段，有时效性，有状态变化）
- 混在一起检索会互相干扰：知识库文档会污染信号的精确匹配，信号会稀释知识库的通用性

**字段设计**（复用现有 `Document` schema，通过 tags 区分）：

```python
# Signal Store 中一条记录的字段映射
{
    "doc_id":      "sig_{source_id}_{signal_type}_{timestamp}",
    "title":       signal.signal_label,           # 信号标签
    "content":     f"{signal.description} | 证据：{signal.evidence_text}",
    "content_type": "case_record",               # 信号本质是真实事件记录
    "tags": [
        "signal",                                 # 标识这是 Signal Store 条目
        "pending",                                # 状态：pending / matched / archived
        f"signal_type:{signal.signal_type}",      # regulatory/capital/market/technical/team
        f"role:{primary_role}",                   # 主角色（见角色枚举）
        f"role:{secondary_role}",                 # 可选次角色
        f"needs:{gap1}",                          # 构成机会还需要的角色1
        f"needs:{gap2}",                          # 构成机会还需要的角色2
        f"domain:{domain}",                       # 领域标签：gaming/ai/mobile/regulation/capital
        f"intensity:{signal.intensity_score}",    # 原始强度
        f"batch:{batch_date}",                    # 写入批次日期
    ],
    "trust_level": _map_confidence(signal.confidence_score),
    "metadata": {
        "source_id":        signal source_id,
        "original_intensity": signal.intensity_score,
        "effective_intensity": signal.intensity_score,  # 随时间衰减更新
        "timestamp":        ISO timestamp,
        "waiting_for_text": "一句话描述：我在等待什么样的伙伴信号",  # 轻量LLM生成
        "attempt_log":      [],   # 记录尝试过的组合，避免重复
        "matched_opportunity_id": None,  # 成功成为机会后填入
    }
}
```

**`waiting_for_text` 的作用**：不是用于 embedding 检索（向量检索在逻辑互补场景下效果差），而是在 Step B 分层漏斗的 L3 阶段提供语义精排依据，以及在 dashboard 展示时解释信号在等待什么。

---

### 2.3 信号角色枚举

| 角色 | 含义 | 典型 signal_type |
|------|------|----------------|
| `catalyst` | 触发机会的外部事件/压力 | regulatory, market |
| `demand_evidence` | 证明需求侧存在 | market, team |
| `resource_validation` | 证明资源/能力/资金到位 | capital, technical |
| `competitive_gap` | 竞品退出/收缩/受限 | team, market, capital |
| `execution_risk` | 执行层面的障碍或风险 | technical, regulatory |
| `timing_signal` | 时间窗口/紧迫性证据 | 任意类型 |
| `negative_validator` | 证伪/削弱机会论点的反向信号 | 任意类型 |

**多角色说明**：同一信号可有 1-2 个主角色（tags 叠加，如 `role:catalyst` + `role:timing_signal`）。写入时由轻量 LLM（haiku）判断。

**`negative_validator` 的特殊用途**：Step C 完整判断时，强制检索一次是否存在针对当前机会方向的反向信号，纳入 counter_evidence。防止系统盲目乐观（确认偏误）。

---

### 2.4 Step A：批内聚类 + 角色标注

**目标**：在当次批次内发现可直接组合的信号，同时完成所有信号的角色标注。

**实现**：
```
输入：当次全部信号（50-100条的摘要列表）
LLM（haiku）单次调用：
  - 任务1：信号分组（哪些信号属于同一机会方向的不同侧面？）
  - 任务2：每条信号的角色标注（role + needs + domain）
  - 任务3：每条信号生成 waiting_for_text（10-20字）
输出：
  - 可组合的信号组列表 → 进 Step C
  - 孤立信号列表（含角色标注）→ 进 Step B
```

**Fallback**：LLM 调用失败时，所有信号视为孤立，全部进 Step B，记录失败批次供人工 review。

**关键约束**：分组依据是"逻辑互补"而非"语义相似"——语义差异很大的信号（监管+资本+技术）可以组合成同一机会。Prompt 需要 few-shot 示例专门示范这一点。

---

### 2.5 Step B：历史信号检索 / 历史关系唤醒（分层漏斗）

**目标**：为孤立信号在 Signal Store 中找到跨批次的互补伙伴，同时优先激活"已经出现但尚未闭环"的半成品关系结构，不遗漏长尾积累。

**先拍板的职责边界**：
- Step B 的主职责是**跨批次关系召回、补槽、激活旧场景**。
- Step B 仍可使用 RAG / embedding 能力，但它们是**辅助支撑层**，不是主召回层。
- 只有在已经形成候选场景后，才值得进一步拉取 RAG 证据补强；不建议对所有孤立信号做重型主动检索。

**基础版处理顺序**：

```
B0: 新信号进入
    → 先查 scenario_candidates 的 missing_slots（我是不是在补旧场景缺口？）
    → 再查 emerging_links（我是不是能把旧关系升级成候选场景？）
    → 最后才回到原始 pending signals（我能不能帮孤立旧信号找到伙伴？）
```

**四层漏斗设计**（当前工程主线，按"补槽优先"扩展）：

```
L1: Tag 粗筛（O(1)，无 LLM）
    → 查询对象：pending signals + scenario_candidates + emerging_links
    → 条件：status=active/pending + needs 或 missing_slots 中包含当前信号的 role
    → 作用：优先找出"正在等我这种角色 / 这种对象"的历史半成品
    → 输出：候选池（可能 10-50 条）

L2: 规则硬过滤（O(n)，n=候选池，无 LLM）
    → 条件1：domain 重叠（至少1个共同 domain tag）
    → 条件2：时间窗口兼容（写入时间差 ≤ 90 天，可配置）
    → 条件3：强度互补（高 intensity 信号不配低 intensity 伙伴，阈值可配置）
    → 条件4：排除已尝试过的相同组合（查 attempt_log）
    → 条件5：若命中的是 scenario_candidate，则优先判断是否真的补上关键 missing_slot
    → 输出：精选池（5-15 条）

L3: 语义精排（Top-K，复用 2.4 embedding）
    → 用 waiting_for_text / missing_slot_text 的 embedding 在精选池上做余弦相似度排序
    → 取 Top-3
    → 注意：这里是"精排"而非"检索"——输入已是 L2 过滤后的小集合，不依赖向量距离做召回
    → 输出：最终候选（0-3 条）

L4: 轻量 LLM 确认（haiku，仅当 L3 有候选时触发）
    → 输入：当前新信号 + Top-3 历史候选（可能是原始信号 / emerging_link / scenario_candidate）
    → 问题："这些信号或半成品关系，是否已经形成值得验证的机会假说？"
    → 输出：
       - 已形成可验证假说 → 进 Step C
       - 尚未形成完整假说，但值得继续长 → 回写 scenario_candidates / emerging_links
       - 仍无价值 → 当前信号写入 Signal Store
```

**效率估算**（基于 50 条孤立信号）：
- L1+L2：纯规则，< 1s 总计
- L3：embedding 计算，< 2s 总计
- L4：只在有 L3 命中时触发，预计 30% 命中率 → ~15 次 haiku 调用，< 20s 总计
- **总增量 < 25s**，满足约束

**L2 极端情况处理**：
- 返回 0 条 → 跳过 L3/L4，当前信号直接写入 Signal Store
- 返回 > 20 条 → 取时间最近且补槽优先级最高的 20 条进入 L3
- L3 Top-3 相似度均 < 0.4 → 视为"无有效匹配"，跳过 L4

**分流规则（与 Relation Graph v1 对齐）**：
- Step B 不做"单一总分淘汰"
- 只要关系为真且具备补槽价值，即使当前不完整，也应保留到 `scenario_candidates / emerging_links`
- 只有形成"可验证机会假说"时才送 Step C
- 明显无关系或重复噪声时才丢弃

**与探索通道的衔接（本轮新增拍板）**：
- 对于 `promotion_score` 尚未达到主通道阈值、但 `option_value_score` 很高的候选，Step B 可将其标记为**探索通道候选**
- 探索通道候选不应挤占主通道的主要容量，只保留少量上送名额
- 若探索候选同时满足"补上关键 missing_slot"或"首次激活长期沉睡场景"，则优先级可上调

**RAG 触发边界（必须拍稳）**：
- Step B **不**对所有孤立信号主动发起重型 RAG 检索
- Step B **只在以下场景**考虑主动补 RAG 支撑：
  1. 已形成 `scenario_candidate`
  2. 已命中探索通道、准备送 Step C
  3. 需要补 `supporting_evidence / counter_evidence / similar case_record / mechanism explanation`
- RAG 在 Step B 中的职责是**补强候选**，不是**负责召回候选**
- 若当前只有单条孤立信号、且尚未形成关系候选，则不建议触发主动 RAG

**当前工程内的最小交接入口（2026-04-02 补充）**：
- 评测 runner：`phase2.2_implementation/run_step_b_idealized_eval.py`
- 样本文件：`phase2.2_implementation/step_b_idealized_eval_samples_not_real_data.py`
- 快照输出目录：`phase2.2_implementation/eval_outputs/step_b/`
- 回归测试入口：`unit_tests_phase22.py` 中 `TestStepBIdealizedEvalRunner`

**这个 runner 解决什么问题**：
- 它不是生产效果评估器，而是 **Step B 排序 / 分流收敛器**
- 用理想化样本稳定观测：
  - `scenario_memory`、`emerging_link`、`signal_entry` 三类来源是否都能被正确召回
  - `step_c_ready / store_for_later / none` 分流是否符合预期
  - Top-1 候选是否落在预期来源和预期 route 上
  - 每轮权重微调后，基线是否保持可对比、可回退

**最常用运行方式**：
- `python phase2.2_implementation/run_step_b_idealized_eval.py`
- `python phase2.2_implementation/run_step_b_idealized_eval.py --json`
- `python phase2.2_implementation/run_step_b_idealized_eval.py --json --save-report`
- `python phase2.2_implementation/run_step_b_idealized_eval.py --case-id step_b_scenario_primary_001 --json`

**输出判读建议（后续调 Step B 时优先看这几项）**：
- `top1_route_counts`：Top-1 落在 `step_c_ready / store_for_later / none` 的分布
- `top1_source_kind_counts`：Top-1 是 `scenario_memory / emerging_link / signal_entry / none` 的分布
- `top1_rank_score_avg`：Top-1 平均排序分，观察整体排序抬升/塌缩
- `candidate_rank_score_avg`：全部候选平均排序分，观察排序是否整体抬升或塌缩
- `case_overview`：逐 case 看 `top_group_id / top_route / top_source_kind / top_rank_score`

**当前基线（v0.3 理想化样本，2026-04-02）**：
- `5/5 PASS`
- `top1_route_counts = {step_c_ready: 2, store_for_later: 2, none: 1}`
- `top1_source_kind_counts = {scenario_memory: 2, emerging_link: 1, signal_entry: 1, none: 1}`
- 新增边界 case：`step_b_scenario_beats_strong_signal_001`
  - 当前观测锚点：Top-1 仍为 `scenario_memory`
  - 这个 case 的意义不是追求更高分，而是锁住一个关键排序边界：**当 richer scenario 已形成机会、强单条历史信号仍只是机会前状态时，前者应稳定排第一**
- 现阶段推荐把 `step_c_ready > store_for_later` 的路由稳定性，以及 `scenario_memory > strong signal_entry` 的相对顺序，一起视为粗基线；后续微调优先保持这两个方向稳定，再追求更细的排序收敛

**什么时候应该改 runner / 样本**：
- 新增或调整 Step B 路由规则
- 修改排序权重
- 新增一种需要稳定观察的来源类型或边界 case

**什么时候不该依赖它**：
- 评估真实业务收益时
- 代替端到端真实样本验证时
- 推断 LLM 路径真实命中率时（当前 `runtime_mode=rules_only`）

---

### 2.6 Step C：完整机会判断（现有逻辑，输入扩展）

**不改动 prompt**，只扩展输入来源：
- 原来：只有当次批次的信号
- 现在：Step A/B 筛选出的候选机会路径（可能包含历史 Signal Store 中的信号、`scenario_candidates` 激活结果、或探索通道候选）

**进入 Step C 的条件重新拍稳**：
- `2.2` 送入 Step C 的，不是"高分边"，而是已经形成**可验证假说**的候选路径
- 即使候选仍不成熟，也可以送 Step C；成熟度判断仍属于 `2.3`
- 未达到 Step C 条件、但具有明显期权价值的候选，继续留在 Signal Store 生长，而不是被淘汰

**新增：反向信号强制检索**（Gemini 建议的 Negative Validator）：
- 在 Step C 开始前，检索 Signal Store 中 `role:negative_validator` + domain 匹配的信号
- 找到 → 注入 prompt 的 counter_evidence 区域
- 防止系统只看到支持机会的信号，忽视反向证据

**可选：候选形成后再补 RAG 支撑信息**：
- 当 Step B 已形成较可信的 `scenario_candidate` 或 `logical_scenario` 时，可主动检索 2.4 RAG，补充：
  - supporting_evidence
  - counter_evidence
  - similar case_record
  - 术语 / 机制解释
- 这些信息的作用是帮助 Step C 做更稳的判断，而不是替代 Step B 的关系召回

**输出**：OpportunityObject（schema 不变），增加 `source_signals` 字段记录参与组合的所有信号 ID（含历史信号），方便追溯。

---

### 2.7 信号状态管理

| 状态 | 含义 | 触发条件 |
|------|------|---------|
| `pending` | 等待伙伴组合 | 写入时默认 |
| `matched` | 已参与机会判断（不论最终成不成） | Step C 被消费时 |
| `archived` | 过期，不再参与检索 | 超过有效期（默认90天）|
| `converted` | 已成机会，转化为 case_record | Step C 输出 OpportunityObject 时 |

**时效性衰减**：信号价值随时间连续衰减，不是 90 天突然失效：
```
effective_intensity = original_intensity × e^(-λt)
λ 由 signal_type 决定：
  regulatory: λ = 0.008（半衰期约87天，监管事件影响持久）
  market:     λ = 0.023（半衰期约30天，市场热点消退快）
  capital:    λ = 0.012（半衰期约58天）
  technical:  λ = 0.015（半衰期约46天）
  team:       λ = 0.020（半衰期约35天，人事变动影响消退）
```
L2 过滤和 L3 精排时使用 effective_intensity 而非 original_intensity。

---

### 2.8 已成机会的知识沉淀（闭环关键）

当 Step C 输出有效 OpportunityObject 时（priority_level ≠ null），自动执行：
1. 参与组合的所有信号标记为 `converted`，写入 `matched_opportunity_id`
2. 生成一条 `content_type=case_record` 的文档写入 **2.4 RAG 知识库**：
   - title：opportunity_title
   - content：opportunity_thesis + 信号组合摘要 + why_now
   - tags：`["golden_pattern", signal_type组合, domain, priority_level]`
3. 这条 case_record 之后会被 2.2 的 Step C 在检索 RAG 时召回，作为"历史上类似信号组合成功的先例"，提升置信度

**这是整个方案唯一写入 2.4 知识库的操作**，不改变 2.4 的任何接口和现有文档。

---

## 三、与现有架构的关系

### 3.1 完全不变的部分

| 模块 | 不变点 |
|------|--------|
| 2.1 情报解码 | 输出格式完全不变 |
| 2.2→2.3 接口 | OpportunityObject schema 完全不变（仅新增可选字段 source_signals） |
| 2.3 行动设计 | 完全不变 |
| 2.4 RAG 接口 | 检索接口不变；仅新增 Signal Store 独立 pkl 文件 |
| 2.5 复盘归因 | 完全不变 |
| 2.2 Step C prompt | 完全不变；输入信号集合可能包含历史信号，但格式一致 |

### 3.2 新增的部分

| 新增项 | 位置 | 说明 |
|--------|------|------|
| `signal_store.py` | `phase2.2_implementation/` | Signal Store 读写接口 |
| `step_a_cluster.py` | `phase2.2_implementation/` | 批内聚类 + 角色标注逻辑 |
| `step_b_retrieval.py` | `phase2.2_implementation/` | 分层漏斗检索逻辑 |
| `signal_store.pkl` | `phase2.4_implementation/rag_system/data/` | Signal Store 独立存储文件 |
| Step A/B/C 编排 | `judgment_engine.py` 顶层新增方法 | 不改动现有 `_llm_judge_v2` 方法 |

### 3.3 小改的部分

| 文件 | 改动内容 |
|------|---------|
| `judgment_engine.py` | 新增 `judge_with_signal_store()` 入口方法（现有 `judge()` 保留不变） |
| `schemas.py` | OpportunityObject 新增可选字段 `source_signals: Optional[List[str]]` |
| `run_batch_real.py` | 调用 `judge_with_signal_store()` 替代 `judge()`（1行改动） |

---

## 四、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Step A 批内聚类 LLM 调用超时 | 中 | 批次延迟 | Fallback：所有信号视为孤立，正常进 Step B |
| L4 haiku 调用量超预期（误判命中率） | 低 | 成本增加 | L3 相似度阈值兜底（< 0.4 跳过 L4） |
| Signal Store 积累速度过快 | 低 | 存储/检索变慢 | 90天过期 + effective_intensity 衰减机制 |
| 角色标注不准（信号被分配错误角色） | 中 | L1 召回漏失 | 多角色标注（1-2个角色）+ L4 LLM 做最终确认兜底 |
| 反向信号 false positive（正常信号被误判为 negative_validator） | 低 | counter_evidence 噪声增加 | negative_validator 标注需要显式的"削弱"语义，而非普通的风险信号 |
| 已成机会的 case_record 质量差（影响未来判断） | 低 | 知识库污染 | 只在 priority_level=deep_dive/escalate 时才写入知识库 |

---

## 五、迭代规划

### MVP（第一阶段，当前实现目标）

**目标**：实现基本的信号积累和跨批次组合，验证方案可行性

**范围**：
- ✅ Signal Store 存储层（signal_store.py）
- ✅ Step A：批内聚类 + 角色标注（haiku 单次调用）
- ✅ Step B：L1+L2 规则过滤（不含 L3 embedding 精排）
- ✅ Step B：L4 LLM 轻量确认
- ✅ 信号状态管理（pending/matched/archived）
- ✅ 已成机会 → 写入 2.4 RAG 知识库

**暂缓到 v1.1**：
- L3 embedding 精排（待验证 L1+L2 漏斗效果后决定是否必要）
- effective_intensity 衰减（用简单线性衰减代替指数衰减，待规模验证后调整）
- negative_validator 角色（MVP 验证基础流程，v1.1 加入）
- Top-down 假设驱动路径（v2.0 考虑）

### v1.1（第二阶段）

- L3 embedding 精排（如 MVP 中 L1+L2 召回精度不足）
- negative_validator 角色 + Step C 反向信号检索
- effective_intensity 指数衰减
- dashboard：Signal Store 状态展示（待组合 / 已成机会 / 已过期）

### v2.0（第三阶段，条件触发）

触发条件：Signal Store 积累 > 200 条，或出现明显的跨批次机会漏判

- Top-down 假设驱动：专家预设战略假设，Signal Store 充当"假设进度条"（详见第七章）
- 预计算组合索引：写入时异步预计算所有可能组合，查询变为 O(1)（详见第八章）
- 信号观察报告：每周/每月汇总哪些信号 pending 最久、哪些缺口最频繁

---

## 六、Relation Graph / Scenario Memory 衔接设计（新增）

> **定位**：本节用于承接 [step_a_optimization_design.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\docs\step_a_optimization_design.md) 中的 `Relation Graph v1`，定义哪些中间态需要进入 Signal Store 才能支持跨批次生长。
> **边界说明**：本节仍属于纯 `2.2` 内部设计，不触碰 `2.3` 的成熟度判断与行动姿态。

### 6.1 为什么要新增 Scenario Memory

如果 Signal Store 只存原始信号，而不存"已经出现但尚未闭环"的关系结构，那么系统只能做：
- 当前批次内连边
- 当前批次内判断
- 当前批次结束后等待下次重新从原始信号盲搜

这不足以支持以下核心目标：
- 多条信号分散在不同批次中，逐步长成一个机会
- 三天前、三个月前、甚至更早的结构性信号，被今天的小信号重新激活
- 信号量增大后，系统不是只"存得更多"，而是更会把旧关系重新串起来

因此，Signal Store 需要从"信号仓库"升级为"信号 + 中间态关系记忆"。

### 6.2 持久化什么：不是保存全图，而是保存高价值关系痕迹

不建议把所有 pairwise 边都永久存储，否则规模会快速膨胀并污染检索。建议仅持久化以下 4 类对象：

#### A. `emerging_links`
已出现真实关系，但还不足以形成场景的边。

```python
class EmergingLink:
    link_id: str
    signal_ids: List[str]          # 通常 2 条
    edge_type: str
    strength_band: str             # emerging / strong
    shared_affects: List[str]
    missing_slots: List[str]
    reasoning: str
    last_validated_at: str
    expires_at: str
```

#### B. `scenario_candidates`
已经形成局部子图，但尚未准备送 Step C 的候选场景。

```python
class ScenarioCandidate:
    candidate_id: str
    signal_ids: List[str]
    covered_roles: List[str]
    missing_slots: List[str]
    shared_affects: List[str]
    state: str                     # seed / emerging / developing / ready_for_step_c
    reasoning_path: str
    activated_by: Optional[str]
    last_activated_at: str
    expires_at: str
```

#### C. `missing_slots`
场景当前仍缺的拼图，不单独作为实体表，也可内嵌在 `emerging_links` / `scenario_candidates` 中。其意义是：新信号来时优先做"补槽"，而不是对全量历史信号重新暴力组合。

#### D. `anchor_traces`
记录哪些信号曾经是高价值锚点、拉出过哪些局部关系，供后续 `Anchor-based Window` 使用。

### 6.3 新信号进入时的处理策略：补槽优先，非全局重算

新信号进入 `2.2` 时，建议按以下顺序处理：

1. **批内连边**：先与当批次信号生成 `RelationEdge`
2. **补旧场景缺口**：查询 `scenario_candidates / emerging_links` 中哪些 `missing_slots` 可能被当前信号补上
3. **激活旧关系**：若当前信号与旧 `emerging_links` 高匹配，则把边升级为新的 `scenario_candidate`
4. **桥接两个半成品**（增强版目标，非 MVP）
5. **仍无匹配**：将当前信号作为新的 pending 信号写入 Store

这样可以把"重新扫描整个历史库"的代价收敛为"优先扫描等待我这种信号的半成品关系"。

### 6.4 场景状态机（基础版即应支持）

建议为 `scenario_candidates` 定义统一状态机：

| 状态 | 含义 | 触发动作 |
|------|------|---------|
| `seed` | 刚形成 1 条有效边或 2 条初始互补信号 | 写入 Store，等待补槽 |
| `emerging` | 已出现明确机会方向，但缺关键角色 | 优先参与后续新信号补槽 |
| `developing` | 结构逐渐完整，已有 3-4 条互补信号 | 可进入锚点候选池 |
| `ready_for_step_c` | 已形成当前值得验证的候选机会路径 | 送 Step C 做完整机会判断 |
| `archived` | 长期未被激活或时效性消退 | 从主动检索中移除 |

**重要说明**：这个状态机不是机会成熟度状态机，而是"关系结构是否值得继续生长"的状态机；仍属于 `2.2` 范围。

### 6.5 时效策略：不是统一 90 天一刀切

为了支持跨批次长链机会，又避免 Store 变成垃圾场，建议将"可激活寿命"按信号类型差异化处理：

| 信号类型 | 可激活寿命倾向 | 说明 |
|---------|---------------|------|
| `regulatory` / 平台规则 / 基础设施变化 | 长 | 半年前的信号仍可能构成今天机会的上游约束 |
| `capital` / `team` / 能力迁移 | 中 | 会衰减，但可能持续数月影响格局 |
| `market` 热点 / 短期舆情 | 短 | 若长期无后续共振，应更快归档 |

同时建议引入：
- **被新信号激活即续命**：`last_activated_at` 更新时顺延有效期
- **长期未激活则降级**：从 `developing` 回落为 `emerging` 或直接 `archived`

### 6.6 对"6 个信号分散在不同批次中组成一个机会"的支持边界

**基础版承诺**：
- 支持 `2-4` 条信号的跨批次渐进组合
- 支持部分 `5-6` 条机会链逐步长成，但不承诺完整覆盖所有长链弱信号场景
- 支持旧场景被新信号重新激活，而不是每批次独立判断后永久遗忘

**当前不承诺**：
- 任意 6 条弱信号、跨很长时间、没有明显锚点和对象收敛时都能稳定被系统找出
- 多跳桥接和复杂长链图搜索在 MVP 中可靠落地

这类能力属于后续增强 / 高级版路线，见本节后续规划。

### 6.7 与现有 Step B 漏斗的关系

当前 Step B 的 L1-L4 漏斗仍然成立，但其查询对象会从"只查原始历史信号"逐步扩展到：
- 原始 pending signals
- `emerging_links`
- `scenario_candidates`
- （未来）`anchor_traces`

也就是说，Step B 不再只是"帮孤立信号找伙伴"，而会逐步升级为"帮新信号补旧场景、激活旧关系"。

### 6.7.1 查询职责拆分（避免后续实现混层）

建议后续工程实现时直接拆成三类主查询：
- **信号查询**：从原始 `pending signals` 中找互补伙伴
- **关系查询**：从 `emerging_links` 中找可被激活的关系边
- **场景查询**：从 `scenario_candidates` 中找可补槽的半成品场景

以及一类可选辅助查询：
- **RAG 支撑查询**：仅在候选已成形后，补拉 `supporting_evidence / counter_evidence / case_record`

这样可以避免把"关系召回"和"知识支撑"混成一个模糊检索入口。

### 6.8 分阶段路线（结合本轮拍板后的统一口径）

#### 基础版（当前应实现的目标）

**目标**：让机会结构可以跨批次"长出来"，而不是每批次独立判断后消失。

**应覆盖能力**：
- 原始信号写入 Signal Store
- `emerging_links / scenario_candidates / missing_slots` 持久化
- 新信号优先做补槽和激活旧场景
- 场景状态机 `seed → emerging → developing → ready_for_step_c`
- 支持 `2-4` 条跨批次信号稳定生长，并开始覆盖一部分 `5-6` 条长链机会
- 保留少量探索通道名额，避免高期权价值候选长期被主通道压制

#### 基础版实现顺序（本轮补充）

建议按以下顺序落地，避免一次性把系统做重：
1. 先支持 `scenario_candidates / emerging_links` 的持久化
2. 再实现"补槽优先"的 Step B 查询顺序
3. 再实现探索通道的受控上送
4. 最后补候选形成后的 RAG 支撑检索

这样可以保证：
- 主召回层先稳定
- 跨批次生长先成立
- RAG 只在必要位置补强，而不会反客为主

#### 增强版（下一阶段）

**目标**：在中大批次中兼顾效率与跨域召回。

**应覆盖能力**：
- `Anchor-based Window` 正式落地
- 锚点选择从"只看强度"升级为"强度 + 时效 + 结构杠杆 + 补槽价值"
- Step B 查询从角色缺口扩展到关系痕迹和场景缺口
- 预计算关系索引开始承担查询加速

#### 高级版（后续研究方向）

**目标**：更稳定地发现"6 条以上、分散在更长时间、且单条都不够强"的长链机会结构。

**应覆盖能力**：
- 桥接两个旧半成品场景
- dormant scenario 唤醒
- 多跳 / 长链关系搜索
- Bottom-up 与 Top-down 假设驱动联动
- 更强的观察报告与图索引维护机制

---

## 七、开放问题（待拍板）

| # | 问题 | 当前倾向 | 状态 |
|---|------|---------|------|
| 1 | 角色枚举的 7 个角色是否完备？ | 先用这 7 个，遇到无法分类的信号时扩展 | ⏳ 待验证 |
| 2 | `domain` 标签如何定义？需要预定义枚举还是自由文本？ | 预定义枚举（gaming/ai/mobile/regulation/capital/geopolitics），自由文本维护成本高 | ⏳ 待拍板 |
| 3 | Signal Store 与 2.4 RAG 的检索隔离如何实现？ | 独立 pkl 文件 + 独立检索接口，互不调用 | ✅ 方案确定 |
| 4 | `judge_with_signal_store()` 与现有 `judge()` 并存多久？ | MVP 阶段并存，验证稳定后 `judge()` 降为 legacy | ⏳ 待定 |
| 5 | 已成机会写入 RAG 的质量门槛（priority_level 阈值）？ | 仅 deep_dive/escalate 级别 | ⏳ 待拍板 |

---

*文档维护：每次实现阶段完成后更新"执行进展"，不修改本设计文档。如设计有重大变更，创建 v3 版本文档。*

---

## 七、黄金模板（Golden Pattern）设计方案

> **对应迭代阶段**：MVP 即实现（已成机会写回 RAG 是 MVP 范围内）
> **确定性**：高，设计无悬念

### 7.1 定义与价值

黄金模板是从**真实成功机会**中自动提炼的信号组合模式，写入 2.4 RAG 知识库。其价值在于：

- Step C 在判断时，RAG 检索会命中历史上相似的成功模式，提升置信度
- 随系统运行自动积累，不需要人工预设，冷启动后自然增长
- 闭合"判断 → 沉淀 → 再判断"的学习循环

**与"预设模板"的区别**：黄金模板是后验的（从成功案例中提炼），预设模板是先验的（人工设计空壳等信号填充）。两者不互斥，黄金模板是现在做的，预设模板是假设驱动（第九章）里的一部分。

### 7.2 触发条件

Step C 输出 OpportunityObject 且满足以下条件时自动触发写入：
- `priority_level` 为 `deep_dive` 或 `escalate`（watch/research 级别质量不足，不写入）
- `supporting_evidence` 非空（有实际证据支撑，非纯推断）

### 7.3 生成逻辑

```python
def create_golden_pattern(opportunity: OpportunityObject, source_signals: List[SignalStoreEntry]):
    """
    从成功机会自动生成黄金模板，写入 2.4 RAG 知识库。
    每个 OpportunityObject 最多生成一条黄金模板。
    """
    signal_combo_summary = _summarize_signal_combination(source_signals)
    # 格式："{signal_type1}（{role1}）+ {signal_type2}（{role2}）+ ..."

    content = f"""
    机会论点：{opportunity.opportunity_thesis}

    信号组合模式：{signal_combo_summary}
    信号数量：{len(source_signals)} 条
    信号强度范围：{min_intensity} ~ {max_intensity}
    时间跨度：{time_span_days} 天内

    成立条件摘要：{opportunity.key_assumptions 前3条}

    验证问题（供后续对照）：{opportunity.next_validation_questions 前2条}
    """

    doc = Document(
        doc_id=f"golden_{opportunity.opportunity_id}",
        title=f"[黄金模板] {opportunity.opportunity_title}",
        content=content,
        content_type="case_record",  # 复用现有枚举，不新增类型
        tags=[
            "golden_pattern",
            f"combo:{'+'.join(signal_types)}",          # 如 "regulatory+market+capital"
            f"domain:{primary_domain}",
            f"priority:{opportunity.priority_level}",
            f"batch:{today_date}",
        ],
        trust_level="high",   # 已验证机会，信任度高
        industry=primary_industry,
    )
    rag_knowledge_store.add(doc)
```

### 7.4 检索时的使用方式

Step C 调用 2.4 RAG 时，`needed_content_types` 已包含 `case_record`，黄金模板会自然被检索到，**不需要额外的检索逻辑**。

RAG 会在命中时返回：
```
ContextPacketItem(
    content_type="case_record",
    source_title="[黄金模板] 监管压力型移动端入场机会",
    excerpt="机会论点：... 信号组合模式：regulatory(catalyst) + market(competitive_gap)...",
    reason_for_match="当前信号组合与历史成功模式高度相似",
)
```

LLM 在 Step C 的 prompt 中看到这条证据，会自然地用它来加强机会判断的论点。

### 7.5 质量保障

**防止低质量模板污染 RAG**：
- 只写 deep_dive/escalate，过滤掉探索性机会
- 每条黄金模板唯一对应一个 OpportunityObject，不重复写入
- 同一信号组合类型（combo tag 完全相同）最多保留5条最新模板，防止单一模式过度占据检索结果

**冷启动期**：Signal Store MVP 刚上线时黄金模板库为空，Step C 退化为现有行为（无历史模式参考），这是正常的，系统会随使用自然积累。

---

## 八、预计算组合索引设计方案

> **对应迭代阶段**：v2.0（触发条件：Signal Store 积累 > 200 条）
> **确定性**：高，设计无悬念；实现时机待条件触发

### 8.1 问题背景

当前 Step B 的分层漏斗（L1+L2+L3+L4）在信号量 < 200 条时足够高效，但随着 Signal Store 持续积累：

- L1 候选池（需要我这种角色的历史信号）可能增长到数百条
- L2 规则过滤仍然是 O(n)，n 随积累线性增长
- 整体检索时间从"可忽略"变为"显著延迟"

预计算组合索引的目标：**把"查询时计算"变成"写入时计算"**，查询退化为 O(1) 主键查询。

### 8.2 数据结构

```python
# 组合候选索引表（独立存储，signal_combo_index.json 或 SQLite）
class CombinationCandidate:
    combo_id: str           # f"combo_{signal_id_a}_{signal_id_b}"
    signal_ids: List[str]   # 参与组合的信号 ID（2-4条）
    domain_overlap: List[str]  # 共同的 domain 标签
    role_coverage: List[str]   # 此组合覆盖的角色类型
    estimated_completeness: float  # 0.0-1.0，组合能覆盖多完整的机会论点
    time_span_days: int     # 最早到最晚信号的时间跨度
    created_at: str         # 索引创建时间
    status: str             # active / consumed / expired

# 倒排索引：signal_id → List[combo_id]
SignalToComboIndex: Dict[str, List[str]]
```

### 8.3 写入时的异步预计算

```
信号 X 写入 Signal Store 时（非阻塞，异步 Job）：

1. 取信号 X 的角色列表（role tags）
2. 查询 Signal Store：找出 needs 中包含 X 角色 + domain 重叠的 pending 信号
   （即现在的 L1+L2 过滤逻辑，在写入时跑一次，结果持久化）
3. 对每个匹配到的历史信号 Y：
   a. 估算组合完整度：(X的角色 + Y的角色) 覆盖了哪些机会论点维度？
   b. 生成 CombinationCandidate 记录
   c. 写入组合候选索引
4. 更新倒排索引：signal_X_id → [combo_id_1, combo_id_2, ...]
```

### 8.4 查询时的使用

Step B 完全替换为：
```python
def step_b_with_precomputed_index(signal: SignalStoreEntry) -> List[CombinationCandidate]:
    # O(1) 主键查询
    combo_ids = signal_to_combo_index.get(signal.signal_id, [])
    candidates = [combo_index[cid] for cid in combo_ids if combo_index[cid].status == "active"]
    # 按 estimated_completeness 降序，取 Top-5
    return sorted(candidates, key=lambda c: c.estimated_completeness, reverse=True)[:5]
```

**L4 LLM 确认保留**：预计算只做规则层面的组合筛选，最终"逻辑链是否成立"仍由 L4 LLM 判断，不省略。

### 8.5 存储选型

| 选项 | 适用场景 | 说明 |
|------|---------|------|
| JSON 文件 | 组合数 < 5000 | 与 Signal Store pkl 风格一致，无额外依赖 |
| SQLite | 组合数 5000-50000 | 支持 SQL 查询，迁移成本低 |
| PostgreSQL | 组合数 > 50000 | 超出当前规模预期，暂不考虑 |

**当前选型**：JSON 文件（与现有 pkl 存储风格一致，迁移到 SQLite 时只需替换读写层）

### 8.6 索引维护

**信号过期时**：将该信号参与的所有 CombinationCandidate 标记为 expired，从倒排索引中移除。

**信号成功转化为机会时**：将参与的 CombinationCandidate 标记为 consumed，避免被重复消费。

**索引重建**：Signal Store 结构变更时（如角色枚举扩展），提供 `rebuild_combo_index.py` 脚本全量重建，预计运行时间 < 5 分钟（数百条信号规模）。

---

## 九、假设驱动（Top-down）设计方案

> **对应迭代阶段**：v2.0（触发条件：有明确的长周期战略假设需要追踪）
> **确定性**：中；核心待拍板点：假设来源（人工 vs 自动生成）

### 9.1 定位与价值

当前方案（Bottom-up）的局限：
- 跨度超过 90 天的战略机会，每批次信号量太少，积累速度慢，难以自然拼出
- 系统不知道"我在找什么"，只是被动等信号凑齐

假设驱动是 Bottom-up 的**并行补充路径**，不替代：
- Bottom-up：信号积累 → 系统自发现机会
- Top-down：预设战略假设 → 信号填充假设的证据维度 → 达到阈值触发判断

两条路径共享 Signal Store，互不干扰。

### 9.2 核心数据结构

```python
class StrategicHypothesis:
    hypothesis_id: str          # hyp_001
    title: str                  # "移动端平台分发格局重构机会"
    description: str            # 假设的详细描述
    required_dimensions: List[HypothesisDimension]  # 成立所需的证据维度
    trigger_threshold: float    # 完成度达到此值时触发 Step C（默认 0.7）
    domain: List[str]           # 关联领域
    created_by: str             # "human" 或 "agent"（待拍板）
    created_at: str
    status: str                 # active / triggered / archived
    current_progress: float     # 当前完成度（0.0-1.0）

class HypothesisDimension:
    dimension_id: str           # dim_001
    label: str                  # "主要平台受到外部压制"
    required_roles: List[str]   # 填充此维度需要哪些信号角色：["catalyst"]
    required_signal_types: List[str]  # ["regulatory", "market"]
    weight: float               # 此维度在整体完成度中的权重（各维度之和=1.0）
    filled_by: Optional[str]    # 填充此维度的信号 ID（filled 后写入）
    status: str                 # empty / filled
```

### 9.3 进度条机制

```
每次新信号写入 Signal Store 时，额外执行：

1. 遍历所有 active 假设（数量通常 < 20，遍历成本可接受）
2. 对每个假设，检查新信号是否能填充任意未填充的维度：
   - 条件：信号 role ∩ dimension.required_roles 非空
           AND 信号 signal_type ∈ dimension.required_signal_types
           AND 信号 domain ∩ hypothesis.domain 非空
3. 满足条件 → 将维度标记为 filled，记录填充信号 ID
4. 重新计算假设完成度：
   current_progress = sum(dim.weight for dim in dims if dim.status == "filled")
5. current_progress >= trigger_threshold → 触发 Step C，传入所有 filled_by 信号

```

**为什么遍历假设而不是检索**：假设数量通常 < 20（战略假设不会无限膨胀），全量遍历成本远低于任何检索开销，且逻辑最简单。

### 9.4 假设完成度展示（进度条）

```
假设：移动端平台分发格局重构机会（完成度 60%）

  ✅ 维度1：主要平台受到外部压制（权重 25%）
     └── 填充信号：EU DMA 罚苹果5亿欧元（2026-01-15）

  ✅ 维度2：开发者行为变化（权重 25%）
     └── 填充信号：Epic 旗下独立工作室迁出 App Store（2026-02-20）

  ✅ 维度3：替代渠道出现（权重 10%）
     └── 填充信号：安卓侧载政策松动传言（2026-03-10）

  ⬜ 维度4：头部内容迁移（权重 25%）—— 尚无信号
  ⬜ 维度5：资本进入替代方向（权重 15%）—— 尚无信号

  触发阈值：70% → 还差：维度4 或 维度5 任意一个填充即可触发
```

### 9.5 ⚠️ 核心待拍板点：假设来源

这是整个方案最大的不确定性，影响系统复杂度和使用体验。

**选项A：纯人工维护**
- 实现：一个 `hypotheses.yaml` 配置文件，人工编写和维护
- 优点：简单，假设质量有保障
- 缺点：需要人定期更新，冷启动需要时间，可能跟不上市场变化
- 适合：战略方向相对稳定，团队有专人负责战略假设维护

**选项B：LLM 自动生成假设**
- 实现：每批次处理完成后，LLM 基于当前 Signal Store 中的 pending 信号，尝试推导"这批信号在等什么才能成为机会"，自动生成新假设
- 优点：不依赖人工，能发现意料之外的假设方向
- 缺点：假设质量不可控，可能产生大量低价值假设；需要假设去重和质量过滤
- 适合：信号来源多样、战略方向不固定的场景

**选项C：混合（推荐，待拍板）**
- 人工预设核心战略假设（3-5个，稳定方向）
- LLM 基于 pending 信号生成"候选假设"，需要人工审核后激活
- 审核界面在 dashboard 上，不阻塞主流程

**⏳ 待拍板**：选 A、B 还是 C？以及假设的维度设计是否由人工定义，还是 LLM 自动分解？

### 9.6 与 Bottom-up 路径的关系

| 维度 | Bottom-up（现有 + Signal Store） | Top-down（假设驱动） |
|------|--------------------------------|-------------------|
| 发现方式 | 信号积累 → 自发现 | 假设预设 → 信号填充 |
| 适合机会类型 | 短中期（<90天可见的信号积累） | 长周期（需要追踪多个月的战略转折） |
| 对假设的依赖 | 无 | 有（需要预设假设） |
| 意外发现能力 | 强（不预设方向） | 弱（只找预设方向的证据） |
| 当前状态 | MVP 实现目标 | v2.0 规划 |

两条路径都共享 Signal Store 的数据，Top-down 路径不新增存储，只新增假设管理逻辑和进度计算逻辑。

---

*文档维护：每次实现阶段完成后更新"执行进展"，不修改本设计文档。如设计有重大变更，创建 v3 版本文档。*

---

## 十、Signal Store / Step B Schema / 接口冻结稿（实现前对齐版）

> **目的**：把本设计稿与当前 [signal_store.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\signal_store.py) 和 [step_b_retrieval.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\step_b_retrieval.py) 的现实代码入口对齐，冻结跨批次生长所需的第一版持久化对象与查询接口。

### 10.1 与当前实现的对齐结论

当前实现已经具备：
- `SignalEntry`
- `SignalStore`
- `StepBResult`
- `query_by_role()` / `query_pending()` / `query_negative_validators()`
- `run_step_b()` 的 L1-L4 漏斗

因此 v1 最稳的演进方式不是推倒重来，而是：
- 在 `SignalEntry` 之上新增**关系层对象**
- 让 `Step B` 从“查历史信号”扩展到“查历史信号 + 关系痕迹 + 半成品场景”
- 保持现有 `run_step_b()` 的主流程骨架不变

### 10.2 持久化对象冻结（v1）

建议新增两类持久化对象：

```python
class EmergingLink:
    link_id: str
    left_signal_id: str
    right_signal_id: str
    edge_type: str
    strength_band: str
    bucket_scores: Dict[str, float]
    final_score: float
    shared_affects: List[str]
    covered_roles: List[str]
    missing_slots: List[str]
    reasoning: str
    created_at: str
    last_seen_at: str
    status: Literal["open", "promoted", "archived"]
```

```python
class ScenarioMemory:
    scenario_id: str
    anchor_signal_ids: List[str]
    member_signal_ids: List[str]
    covered_roles: List[str]
    missing_slots: List[str]
    shared_affects: List[str]
    promotion_score: float
    option_value_score: float
    state: Literal["seed", "emerging", "developing", "ready_for_step_c", "promoted", "archived"]
    reasoning_path: str
    activated_by: Optional[str]
    activation_count: int
    created_at: str
    last_activated_at: Optional[str]
```

冻结原则：
- `EmergingLink` 保存“关系为真但还不足成场景”的痕迹
- `ScenarioMemory` 保存“场景已初步成形，但还未必当前送 Step C”的半成品
- 两者都不替代原始 `SignalEntry`，而是与其并存

### 10.3 `SignalEntry` 最小扩展建议

当前 `SignalEntry` 已足够支撑 MVP。为兼容后续跨批次激活，建议只做最小扩展：

```python
last_activated_at: Optional[str]
activation_count: int = 0
linked_scenario_ids: List[str] = []
linked_edge_ids: List[str] = []
```

作用：
- 方便观察一个信号是否长期反复参与候选激活
- 方便做后续“高杠杆锚点”统计
- 不影响现有 `pending / matched / archived / converted` 状态机

### 10.4 `SignalStore` 查询接口冻结建议

建议在当前 `SignalStore` 上扩展以下接口：

```python
def save_emerging_links(self, links: List[EmergingLink]) -> List[str]: ...
def save_scenario_memories(self, scenarios: List[ScenarioMemory]) -> List[str]: ...
def query_matching_links(self, roles: List[str], domains: List[str], affects: List[str]) -> List[EmergingLink]: ...
def query_matching_scenarios(self, roles: List[str], domains: List[str], affects: List[str]) -> List[ScenarioMemory]: ...
def update_scenario_state(self, scenario_id: str, state: str, activated_by: Optional[str] = None): ...
def mark_link_promoted(self, link_id: str): ...
```

匹配原则建议：
- 先按 `missing_slots` / `covered_roles` 做轻量召回
- 再按 `shared_affects` / `domains` 做二次收敛
- 最后才进入 L4 LLM 轻量确认

### 10.5 `StepBResult` 扩展冻结建议

当前 `StepBResult` 只返回 `candidate_groups`。建议扩展为：

```python
class StepBResult:
    candidate_groups: List[List[SignalEntry]]
    matched_links: List[EmergingLink]
    matched_scenarios: List[ScenarioMemory]
    current_signal_id: str
    matched: bool
    fallback_used: bool = False
```

这样可以显式区分：
- 是命中了原始历史信号
- 还是命中了关系痕迹
- 还是直接激活了半成品场景

### 10.6 `step_b_retrieval.py` 函数边界冻结建议

建议在现有 `run_step_b()` 基础上拆出以下函数：

```python
def _retrieve_pending_signal_candidates(...) -> List[SignalEntry]: ...
def _retrieve_emerging_link_candidates(...) -> List[EmergingLink]: ...
def _retrieve_scenario_memory_candidates(...) -> List[ScenarioMemory]: ...
def _merge_and_rank_candidates(...) -> dict: ...
def _maybe_fetch_rag_support(...) -> dict: ...
```

职责边界：
- 前三者负责“关系召回”
- `_merge_and_rank_candidates()` 负责统一排序与分流
- `_maybe_fetch_rag_support()` 只在候选已成形、准备送 Step C 时触发

### 10.7 RAG 边界冻结结论

为了防止 Step B 变成“有问题就先去查知识库”，这里明确冻结：

- **RAG 不是主召回层**
- **RAG 不负责从单条孤立信号直接凭语义找机会**
- **RAG 只在以下两类情况下触发**：
  - 候选场景已形成，准备送 Step C 前补支持/反证
  - 探索通道候选需要补一条高价值背景或案例支撑，避免纯弱结构裸上送

### 10.8 本轮冻结结论

本轮建议冻结为：
- 原有 `SignalEntry / SignalStore / run_step_b()` 保持主骨架
- 新增 `EmergingLink / ScenarioMemory` 作为跨批次关系层
- Step B 从“找历史信号”升级为“找历史信号 + 找关系痕迹 + 找半成品场景”
- RAG 严格留在候选形成后的支撑补强位置

这样做可以在不把系统做得过重的前提下，先把“跨批次生长”能力建立起来。

---

*文档维护：每次实现阶段完成后更新"执行进展"，不修改本设计文档。如设计有重大变更，创建 v3 版本文档。*
