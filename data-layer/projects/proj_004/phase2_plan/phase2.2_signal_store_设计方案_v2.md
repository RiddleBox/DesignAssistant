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

### 2.5 Step B：历史信号检索（分层漏斗）

**目标**：为孤立信号在 Signal Store 中找到跨批次的互补伙伴，不遗漏长尾积累。

**四层漏斗设计**（DeepSeek 方案优化版）：

```
L1: Tag 粗筛（O(1)，无 LLM）
    → 条件：status=pending + needs 中包含当前信号的 role
    → 作用：找出"需要我这种角色"的历史信号
    → 输出：候选池（可能 10-50 条）

L2: 规则硬过滤（O(n)，n=候选池，无 LLM）
    → 条件1：domain 重叠（至少1个共同 domain tag）
    → 条件2：时间窗口兼容（写入时间差 ≤ 90 天，可配置）
    → 条件3：强度互补（高 intensity 信号不配低 intensity 伙伴，阈值可配置）
    → 条件4：排除已尝试过的相同组合（查 attempt_log）
    → 输出：精选池（5-15 条）

L3: 语义精排（Top-K，复用 2.4 embedding）
    → 用 waiting_for_text 的 embedding 在精选池上做余弦相似度排序
    → 取 Top-3
    → 注意：这里是"精排"而非"检索"——输入已是 L2 过滤后的小集合，不依赖向量距离做召回
    → 输出：最终候选（0-3 条）

L4: 轻量 LLM 确认（haiku，仅当 L3 有候选时触发）
    → 输入：当前孤立信号 + Top-3 候选历史信号
    → 问题："这些信号有没有能构成机会逻辑链的组合？"
    → 输出：有组合 → 进 Step C；无组合 → 当前信号写入 Signal Store
```

**效率估算**（基于 50 条孤立信号）：
- L1+L2：纯规则，< 1s 总计
- L3：embedding 计算，< 2s 总计
- L4：只在有 L3 命中时触发，预计 30% 命中率 → ~15 次 haiku 调用，< 20s 总计
- **总增量 < 25s**，满足约束

**L2 极端情况处理**：
- 返回 0 条 → 跳过 L3/L4，当前信号直接写入 Signal Store
- 返回 > 20 条 → 取时间最近的 20 条进入 L3（信号时效性优先）
- L3 Top-3 相似度均 < 0.4 → 视为"无有效匹配"，跳过 L4

---

### 2.6 Step C：完整机会判断（现有逻辑，输入扩展）

**不改动 prompt**，只扩展输入来源：
- 原来：只有当次批次的信号
- 现在：Step A/B 筛选出的信号组合（可能包含历史 Signal Store 中的信号）

**新增：反向信号强制检索**（Gemini 建议的 Negative Validator）：
- 在 Step C 开始前，检索 Signal Store 中 `role:negative_validator` + domain 匹配的信号
- 找到 → 注入 prompt 的 counter_evidence 区域
- 防止系统只看到支持机会的信号，忽视反向证据

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

- Top-down 假设驱动：专家预设战略假设，Signal Store 充当"假设进度条"
- 预计算组合索引：写入时异步预计算所有可能组合，查询变为 O(1)
- 信号观察报告：每周/每月汇总哪些信号 pending 最久、哪些缺口最频繁

---

## 六、开放问题（待拍板）

| # | 问题 | 当前倾向 | 状态 |
|---|------|---------|------|
| 1 | 角色枚举的 7 个角色是否完备？ | 先用这 7 个，遇到无法分类的信号时扩展 | ⏳ 待验证 |
| 2 | `domain` 标签如何定义？需要预定义枚举还是自由文本？ | 预定义枚举（gaming/ai/mobile/regulation/capital/geopolitics），自由文本维护成本高 | ⏳ 待拍板 |
| 3 | Signal Store 与 2.4 RAG 的检索隔离如何实现？ | 独立 pkl 文件 + 独立检索接口，互不调用 | ✅ 方案确定 |
| 4 | `judge_with_signal_store()` 与现有 `judge()` 并存多久？ | MVP 阶段并存，验证稳定后 `judge()` 降为 legacy | ⏳ 待定 |
| 5 | 已成机会写入 RAG 的质量门槛（priority_level 阈值）？ | 仅 deep_dive/escalate 级别 | ⏳ 待拍板 |

---

*文档维护：每次实现阶段完成后更新"执行进展"，不修改本设计文档。如设计有重大变更，创建 v3 版本文档。*
