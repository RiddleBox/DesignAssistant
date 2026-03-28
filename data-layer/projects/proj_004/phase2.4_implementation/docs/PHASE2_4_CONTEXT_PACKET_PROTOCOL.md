# Phase 2.4 ContextPacket 协议规范

**文档类型**: 跨模块交付协议（冻结版）
**适用链路**: Phase 2.4 → Phase 2.1 / 2.2 / 2.3
**归档对象**: `proj_004 / phase2.4_implementation`
**版本**: v1.0
**状态**: ✅ 已冻结（可作为实现基准）
**创建日期**: 2026-03-28

---

## 一、协议目的

本协议定义 Phase 2.4 向下游模块（2.1/2.2/2.3）交付上下文时的**最小标准单元**，以及配套的请求/响应结构。

协议的核心价值不是"定义 API 形状"，而是：

> **让下游模块拿到的不是"检索结果文档"，而是"带性质标注、带命中理由、可直接消费的证据包"。**

---

## 二、核心设计原则

### 2.1 `content_type` 而非 `use_as`

2.4 描述内容的**性质**（是什么），不预判内容的**用途**（怎么用）。

原因：同一条证据在不同下游语境中扮演的角色不同：
- 一条"AI NPC 商业化案例"对 2.1 可能是 `few_shot_example`，对 2.2 是用来查证假设的 `case_record`，对 2.3 外部观察者是可引用的 `precedent`
- 如果 2.4 预设用途，会越权且引入歧义
- `content_type` 提供足够线索，由 2.1/2.2/2.3 在各自判断流程中自行决定如何消费

### 2.2 片段级交付，而非全文交付

交付 `excerpt`（命中片段），不是整篇 `content`。原因：
- 减少下游 token 消耗
- 减少无关内容干扰
- 让命中点可追溯

### 2.3 检索 / 组装 / 生成三层分离

- **检索层**：找候选证据（向量召回 + 元数据过滤）
- **组装层**：按 `content_type` 控制组合，而非堆 top-k
- **生成层**：可选归纳，不是主要交付出口

### 2.4 可降级运行

`context_packets` 可为空数组，下游模块在无上下文时必须能正常降级运行，不能硬依赖 2.4。

---

## 三、`ContextPacket`：最小交付单元

### 3.1 字段定义

| 字段 | 类型 | 必填 | 含义 | 备注 |
|------|------|------|------|------|
| `packet_id` | `string` | Y | 上下文包唯一 ID | 格式：`ctx_<uuid_short>` |
| `source_id` | `string` | Y | 来源文档 ID | 对应知识库 `kb_xxx` |
| `source_title` | `string` | Y | 来源文档标题 | 便于人工核查 |
| `content_type` | `string` | Y | 内容性质（见枚举） | 2.4 描述"是什么"，不描述"怎么用" |
| `excerpt` | `string` | Y | 命中片段 | 精确片段，不是全文；最多 500 字符 |
| `reason_for_match` | `string` | Y | 命中原因 | 说明与当前请求的关联关系 |
| `tags` | `string[]` | Y | 标签列表 | 来自原文档 tags 字段 |
| `trust_level` | `string` | Y | 信任等级（见枚举） | 基于来源和置信度评定 |
| `score` | `float` | Y | 检索相似度分数 | 仅作支持信号，不等于事实可信度 |
| `metadata` | `object` | Y | 来源元数据 | 含 `source / last_updated / confidence` |
| `category` | `string` | N | 所属主题分类 | `game_design / market_trend / tech_innovation` |

### 3.2 `content_type` 枚举

| 值 | 含义 | 典型内容 | 主要消费方 |
|----|------|----------|------------|
| `glossary` | 术语定义 | 行业术语、机制名词的精确定义 | 2.1（消歧）|
| `few_shot_example` | 高质量样例 | 抽取/判断/设计的示范案例，含输入输出对 | 2.1（格式参考）/ 2.2（判断参考）|
| `constraint_rule` | 判定规则 / 边界约束 | 字段分类规则、边界条件、硬约束 | 2.1（字段约束）/ 2.2（避免越界）|
| `case_record` | 真实行业事件 | 有主体 + 动作 + 结果的具体事件记录 | 2.2（查证假设）/ 2.3（引用论据）|
| `market_data` | 数据 / 行业基准 | 市场规模、增长率、成本数据等可引用数字 | 2.2（支撑/反驳假设）/ 2.3（数据支撑）|
| `background` | 背景知识 | 补充理解所需的上下文，非核心判断依据 | 2.1（辅助理解）/ 通用 |

### 3.3 `trust_level` 枚举

| 值 | 含义 | 评定标准 |
|----|------|----------|
| `high` | 高可信 | 来源权威（GDC/公开财报/权威报告）+ confidence ≥ 0.8 |
| `medium` | 中等可信 | 来源清晰但非一手 + confidence 0.5–0.8 |
| `low` | 低可信 | 来源模糊 / 合成内容 / confidence < 0.5 |

### 3.4 JSON 示例

```json
{
  "packet_id": "ctx_a3f2b1",
  "source_id": "kb_021",
  "source_title": "AI NPC 商业化路径：三家头部厂商案例复盘",
  "content_type": "case_record",
  "excerpt": "育碧在《刺客信条：幻景》中引入 GPT-4 驱动的 NPC 对话系统，首月 MAU 提升 18%，但推理成本占运营成本比例达 23%，最终选择降级到本地小模型。",
  "reason_for_match": "请求假设为「端侧推理成本已达商业化门槛」，本案例提供了成本占比的真实数据，可用于支撑或反驳该假设。",
  "tags": ["NPC", "商业化", "推理成本", "育碧"],
  "trust_level": "high",
  "score": 0.84,
  "metadata": {
    "source": "GDC 2024 后续报告",
    "last_updated": "2024-09-15",
    "confidence": 0.85
  },
  "category": "market_trend"
}
```

---

## 四、请求协议

### 4.1 通用请求对象：`ContextRequest`

适用于 2.1 / 2.2 / 2.3 三个模块的统一请求入口。

| 字段 | 类型 | 必填 | 含义 | 备注 |
|------|------|------|------|------|
| `request_id` | `string` | Y | 请求唯一 ID | 用于链路追踪 |
| `caller` | `string` | Y | 调用方模块 | `phase2.1 / phase2.2 / phase2.3` |
| `query` | `string` | Y | 核心查询文本 | 原文片段 / 假设命题 / 论点描述 |
| `needed_content_types` | `string[]` | N | 期望的内容类型 | 若指定，组装层优先返回对应类型；空则不限 |
| `top_k` | `int` | N | 期望返回包数量上限 | 默认 5，最大 10 |
| `category_filter` | `string[]` | N | 主题分类过滤 | 限定召回范围，如 `["market_trend"]` |
| `min_trust_level` | `string` | N | 最低信任等级 | `high / medium / low`，默认 `low`（不过滤）|

### 4.2 调用方差异说明

不同模块请求时 `needed_content_types` 的典型配置：

| 调用方 | 典型 `needed_content_types` | 说明 |
|--------|--------------------------|------|
| 2.1（信号抽取时） | `["glossary", "few_shot_example", "constraint_rule"]` | 帮助字段判断和术语消歧 |
| 2.2（机会判断时） | `["case_record", "market_data", "few_shot_example"]` | 查证假设、支撑/反驳机会判断 |
| 2.3（外部观察者发言时） | `["case_record", "market_data"]` | 为论点提供可引用的具体证据 |

### 4.3 请求示例（2.2 调用）

```json
{
  "request_id": "req_phase22_20260328_001",
  "caller": "phase2.2",
  "query": "端侧推理成本在2024年是否已具备游戏NPC商业化条件",
  "needed_content_types": ["case_record", "market_data"],
  "top_k": 5,
  "category_filter": ["market_trend", "tech_innovation"],
  "min_trust_level": "medium"
}
```

---

## 五、响应协议

### 5.1 响应对象：`ContextResponse`

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `request_id` | `string` | Y | 回传请求 ID |
| `context_packets` | `ContextPacket[]` | Y | 上下文包列表，可为空数组 |
| `retrieval_summary` | `string` | N | 本次检索摘要，便于调试 |
| `retrieval_notes` | `string[]` | N | 检索备注（如"未命中 case_record，仅返回 background"）|
| `retrieval_time_ms` | `int` | Y | 检索耗时（毫秒）|
| `protocol_version` | `string` | Y | 协议版本，当前 `v1.0` |

### 5.2 响应示例

```json
{
  "request_id": "req_phase22_20260328_001",
  "context_packets": [
    {
      "packet_id": "ctx_a3f2b1",
      "source_id": "kb_021",
      "source_title": "AI NPC 商业化路径：三家头部厂商案例复盘",
      "content_type": "case_record",
      "excerpt": "育碧在《刺客信条：幻景》中引入 GPT-4 驱动的 NPC 对话系统，首月 MAU 提升 18%，但推理成本占运营成本比例达 23%，最终选择降级到本地小模型。",
      "reason_for_match": "请求假设为「端侧推理成本已达商业化门槛」，本案例提供成本占比真实数据，可支撑或反驳该假设。",
      "tags": ["NPC", "商业化", "推理成本", "育碧"],
      "trust_level": "high",
      "score": 0.84,
      "metadata": {
        "source": "GDC 2024 后续报告",
        "last_updated": "2024-09-15",
        "confidence": 0.85
      },
      "category": "market_trend"
    }
  ],
  "retrieval_summary": "命中 1 条 case_record，0 条 market_data；查询：端侧推理成本商业化条件",
  "retrieval_notes": ["market_data 类型当前知识库覆盖不足，仅返回 case_record"],
  "retrieval_time_ms": 42,
  "protocol_version": "v1.0"
}
```

---

## 六、组装规则

### 6.1 基本原则

- **不堆 top-k**：不是返回相似度最高的前 N 条，而是按 `needed_content_types` 请求的类型组合返回
- **类型多样性优先**：同一 `content_type` 最多返回 `ceil(top_k / len(needed_types))` 条，避免同质化
- **`reason_for_match` 必须生成**：每个 packet 都需说明与当前 query 的关联，不能留空

### 6.2 当某类型无命中时

- 不补其他类型凑数
- 在 `retrieval_notes` 中说明
- 允许返回比 `top_k` 更少的 packet

### 6.3 `excerpt` 生成规则

- 优先取文档中与 query 最相关的段落，不是固定取头部
- 长度控制在 500 字符以内
- 若文档较短（< 500字），可返回全文作为 excerpt

---

## 七、对现有 API 的兼容策略

协议升级分两步，保持向后兼容：

### Step 1（当前）：新增 `/api/v1/context` 接口

- 新建接口实现 `ContextRequest → ContextResponse` 完整协议
- 原有 `/retrieve` / `/rag` 接口**保持不变**，不破坏已联调的链路

### Step 2（后续）：逐步迁移

- 2.1 / 2.2 / 2.3 新增知识增强时优先走 `/context` 接口
- 原接口作为 legacy 保留，等下游全部迁移后再评估是否废弃

---

## 八、知识文档的配套要求

协议落地需要知识文档同步支持 `content_type` 字段：

### 8.1 现有文档补标注

所有 `kb_001` ~ `kb_043` 需补充 `content_type` 字段，枚举值见第三节。

### 8.2 新增文档的 `content_type` 选填规则

- **强制单值**：每条文档只标注一个 `content_type`（主性质）
- **选填参考**：`case_record` 必须包含主体（who）+ 动作（what）+ 结果（outcome）三要素，否则降级为 `background`
- **`market_data` 标准**：必须包含可引用的具体数字和来源，不能是泛描述

### 8.3 当前知识库内容类型评估

| content_type | 现有覆盖估计 | 说明 |
|---|---|---|
| `glossary` | ✅ 较充足 | kb 中有一定量术语类文档 |
| `few_shot_example` | ⚠️ 少量 | 需逐步补充 |
| `constraint_rule` | ⚠️ 少量 | 需逐步补充 |
| `case_record` | ❌ 严重不足 | 2.2/2.3 的核心需求，优先补充 |
| `market_data` | ❌ 严重不足 | 2.2/2.3 的核心需求，优先补充 |
| `background` | ✅ 较充足 | 多数现有文档属于此类 |

---

## 九、下游消费指南

### 9.1 2.1 消费建议

- 按 `content_type` 分类装配到 prompt 的不同位置：
  - `constraint_rule` → 放在 system prompt 约束区
  - `few_shot_example` → 放在示例区
  - `glossary` → 放在术语解释区
  - `background` → 放在背景区（优先级最低）
- 无上下文时正常运行，不报错

### 9.2 2.2 消费建议

- 用 `case_record` 和 `market_data` 类型的 packet 作为假设查证依据
- 在 `opportunity_thesis` 或 `supporting_evidence` 中引用时，附上 `source_id` 和 `source_title` 作为可追溯来源
- `trust_level = low` 的 packet 可以参考，但不应作为核心判断依据

### 9.3 2.3 消费建议

- 外部观察者发言时，将 `case_record` / `market_data` packet 的 `excerpt` 作为论据引用
- 引用格式建议：`"据 [source_title]（[metadata.source]），[excerpt]"`
- `trust_level` 低于 `medium` 的证据，在发言中需加"参考性数据"标注

---

## 十、验收标准

协议实现完成的判定标准：

| 验收项 | 标准 |
|--------|------|
| 接口存在 | `POST /api/v1/context` 可调用 |
| 字段完整 | `ContextPacket` 所有必填字段均有值 |
| `reason_for_match` 有意义 | 不为空，能说明与 query 的关联 |
| 类型多样性 | 当请求多种 `content_type` 时，返回结果包含多种类型（如有对应知识）|
| 可降级 | `context_packets` 为空时，下游可正常运行 |
| 文档标注 | 现有 43 条文档均有 `content_type` 字段 |
| 新接口不破坏旧接口 | 原 `/retrieve` / `/rag` 接口行为不变 |

---

## 十一、更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-03-28 | v1.0 | 初版冻结；基于 FIRST_PRINCIPLES、TO_2_1_CONTEXT_PROTOCOL_DRAFT、OPTIMIZATION_BACKLOG_DRAFT 及三模块消费场景讨论综合制定 |

---

**文档状态**: ✅ 已冻结
**下次更新时机**: 当 `content_type` 枚举需扩展、下游消费语义发生重要变化、或联合 benchmark 口径确定后
