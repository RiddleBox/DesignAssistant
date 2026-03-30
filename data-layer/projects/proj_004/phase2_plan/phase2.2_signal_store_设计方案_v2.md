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

- Top-down 假设驱动：专家预设战略假设，Signal Store 充当"假设进度条"（详见第七章）
- 预计算组合索引：写入时异步预计算所有可能组合，查询变为 O(1)（详见第八章）
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
