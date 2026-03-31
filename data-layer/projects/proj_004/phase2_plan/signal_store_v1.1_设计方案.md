# Signal Store v1.1 设计方案

> **文档类型**：迭代设计方案（v1.1 新增功能）
> **创建日期**：2026-03-31
> **状态**：已实现
> **依赖**：phase2.2_signal_store_设计方案_v2.md（MVP 基础）

---

## 一、跨域信号关联

### 1.1 问题

L2 过滤要求信号的 domain 集合必须有交集，但现实中很多机会恰恰来自跨域信号组合：

- `ai` 技术突破 + `gaming` 市场需求 → 无 domain 交集，被 L2 硬过滤掉
- `regulation` 监管压力 + `capital` 资本收购 → 可能构成机会，但 domain 不重叠

### 1.2 设计方案

将 L2 domain 硬过滤改为"domain 重叠 OR signal_type 互补"双条件宽松策略：

```
domain_overlap = len(current_domains ∩ e.domains) > 0
type_complement = current.signal_type != e.signal_type

过滤条件：not domain_overlap AND not type_complement
```

**逻辑含义**：
- domain 有交集 → 通过（同领域关联）
- signal_type 不同 → 通过（跨类型互补，如 technical + market）
- domain 无交集 且 signal_type 相同 → 过滤（同类重复信号，无组合价值）

### 1.3 风险控制

候选集变大时 L4 token 消耗略增，但 L4 是 haiku 级轻量调用，可接受。L4 做最终逻辑链验证，false positive 由 L4 兜底。

### 1.4 改动范围

仅 `step_b_retrieval.py` 的 `_l2_filter` 函数，约 5 行改动。

---

## 二、机会 ID 持久化

### 2.1 问题

`opportunity_id` 每次判断时用 `uuid4()` 生成，跑完即丢。同一机会方向在下一批次再次出现时，会被当作全新机会处理：

- 无法追踪机会的演进过程
- 后续信号无法关联到历史机会
- 无法识别"这是同一个机会的新证据"

### 2.2 识别方式决策

**选项 A**：基于 `opportunity_title` 文本相似度
**选项 B**：基于 `related_signals` 的 `source_id` 集合重叠

**决策：选项 B**（2026-03-31 拍板）

**理由**：
- LLM 每次生成的 title 措辞不稳定，A 方案容易误判为新机会
- B 方案与 Signal Store 的 `matched` 状态天然配合
- `source_id` 是明确的来源标识，重叠即表示"同一批信号组合"

### 2.3 存储设计

新增 `opportunity_store.pkl`（与 `signal_store.pkl` 同目录）。

**OpportunitySnapshot 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `opportunity_id` | str | 持久化 ID（首次生成后不变） |
| `opportunity_title` | str | 标题（展示用，最新覆盖） |
| `priority_level` | str | 最新判断优先级 |
| `source_signal_ids` | Set[str] | 参与信号的 source_id 集合（用于 ID 复用判断） |
| `signal_ids` | List[str] | Signal Store 中对应的 signal_id 列表 |
| `first_seen` | str | ISO 时间，首次发现 |
| `last_updated` | str | ISO 时间，最后更新 |
| `follow_up_signals` | List[str] | 后续批次追加的信号 source_id |

### 2.4 复用逻辑

```
新机会产出
  → 提取 related_signals 的 source_id 集合
  → 与 opportunity_store 中历史机会比对
  → source_id 有重叠（>=1 个）
      → 复用旧 opportunity_id
      → 追加新 source_id 到 source_signal_ids
      → 追加新 source_id 到 follow_up_signals
      → 更新 priority_level / last_updated
  → 无重叠
      → 新建 OpportunitySnapshot，生成新 opportunity_id
      → 写入 opportunity_store
```

### 2.5 影响范围

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `signal_store.py` | 新增 | `OpportunitySnapshot` dataclass + `OpportunityStore` 类 |
| `judgment_engine.py` | 修改 | `judge_with_signal_store()` 产出机会后写回 opportunity_store |
| `run_batch_real.py` | 不变 | 透明，不感知 opportunity_store |
| 2.2→2.3 接口 | 不变 | `OpportunityObject` schema 不变，`opportunity_id` 对 2.3 透明 |

---

## 三、实现状态

| 功能 | 状态 | commit |
|------|------|--------|
| 跨域信号关联（L2 宽松策略） | ✅ 已实现 | `4b8fe13` |
| 机会 ID 持久化（OpportunityStore） | ✅ 已实现 | `4b8fe13` |
| Step B 跨批次匹配端到端验证 | ✅ 已验证 | `77debaf`（batch3）|
| `_call_llm_and_parse` 误删修复 | ✅ 已修复 | `77debaf` |

**batch3 验证结论（2026-03-31）**：
- 孤立信号 `欧洲游戏困境资产收购基金首关` 进入 Step B，L1 命中 Nacon pending 信号（needs=timing_signal）
- Nacon 信号状态从 `pending` → `matched`，matched_opportunity_id=`opp_4e645932ccbd`
- LLM 判断正常产出，priority=`research`，action=`validate`
- Signal Store：9 条记录，7 contributed + 2 matched
