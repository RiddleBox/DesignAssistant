# Phase 2.5 MVP 实现总结

> **文档类型**：实现总结文档（含执行进展）
> **初始完成时间**：2026-03-16
> **最后更新**：2026-03-29
> **状态**：✅ MVP 完成 → ✅ LLM 归因真实链路跑通

---

## 一、实现概述

Phase 2.5 MVP 最小闭环已成功实现，并于 2026-03-29 完成 LLM 语义归因的真实链路接入与跑通。

### 能力层级说明

| 层级 | 能力 | 状态 | 说明 |
|------|------|------|------|
| L1 | 输入输出契约（Schema） | ✅ 完成 | 3月16日完成，字段已冻结 |
| L2 | 规则层检查（完整性/一致性/可理解性） | ✅ 完成 | `OutputChecker` 三类规则正常运行 |
| L3 | LLM 语义检查（OutputChecker） | ✅ 完成 | 能识别"RAG 噪声混入证据"等语义层问题 |
| L4 | LLM 深层归因（LLMAttributor） | ✅ **2026-03-29 跑通** | findings=5，全部为真实有价值的系统性发现 |
| L5 | 优先级收口（PriorityCloser） | ✅ 完成 | 从归因自然导出，phase3_priorities=5 |
| L6 | 真实链路接入 | ✅ **2026-03-29 完成** | upstream_outputs 来自真实 2.1→2.2→2.3→2.4 运行 |

---

## 二、核心组件

### 2.1 Schema 定义（`schemas/`）

**文件**：`system_retrospective_schema.py`

**核心类型**：`SystemRetrospectiveRequest`、`SystemRetrospectiveObject`、`SystemRetrospectiveResult`、`CriticalFinding`、`SuspectedRootCause`、`Phase3PriorityItem`、`OutputCheck`

**枚举类型**：`SeverityLevel`、`AttributionLayer`（6层）、`CheckType`、`CheckStatus`、`ConfidenceLevel`、`PriorityScope`、`ValidationMode`

### 2.2 输出检查器（`core/output_checker.py`）

- 规则层：完整性/一致性/可理解性三类检查
- LLM 语义层：调用 `LLMClient` 做跨字段语义一致性判断
- JSON 解析：兼容 LLM 前缀说明文字（取第一个 `{` ~ 最后一个 `}` 区间）
- 2026-03-29 改动：system prompt 加"第一个字符必须是 `{`"约束，`max_tokens` 提升至 800

### 2.3 LLM 归因器（`core/llm_attributor.py`）

**2026-03-29 新增**，替代 `ProblemAttributor` 的单纯规则逻辑：

- 接收全链路 `upstream_outputs`（2.1~2.4 真实输出）
- 构建压缩 prompt（evidence 只传标题/首句 ≤80字，不传全文）
- 调用 `LLMClient`（流式模式，`max_tokens=4000`）
- 输出 `critical_findings` + `suspected_root_causes`（JSON）
- 失败时 fallback 到 `ProblemAttributor` 规则层

**prompt 约束（2026-03-29 拍板）**：
- system prompt 明确"第一个字符必须是 `{`，不要任何前缀"
- 每字符串字段限 ≤80字，列表最多 3 条，总输出 ≤1500字
- 信号字段名对齐真实 `Signal` schema：`description`/`intensity_score`/`confidence_score`

### 2.4 问题归因器（`core/problem_attributor.py`）

现定位为 LLMAttributor 的规则 fallback，不再作为主归因路径。

### 2.5 优先级收口器（`core/priority_closer.py`）

从关键发现和归因中自然导出优先级项，按严重度排序。

### 2.6 系统复盘分析器（`core/system_retrospective_analyzer.py`）

主流程编排：真实链路运行 → 输出检查 → LLM 归因 → 优先级收口。

---

## 三、2026-03-29 真实链路验证结果

### 3.1 运行条件

- 样本：3 条真实 incoming 样本（incoming_005/014/018）
- 链路：2.1→2.2（规则 fallback）→2.3（规则 fallback）→2.4（RAG 跑通）→2.5（LLM 归因）
- 报告文件：`reports/2026-03-29_1555_watch_欧盟_DMA_裁定苹果违规并处以_5_亿欧元罚款监管类机会1.md`

### 3.2 LLM 归因输出（5 条发现，全部准确）

| # | 发现 | 层 | 严重度 | 是否准确 |
|---|------|----|--------|----------|
| 1 | RAG完全失效，supporting_evidence均为降级fallback伪证据 | context | HIGH | ✅ |
| 2 | counter_evidence与DMA主题完全无关，反证逻辑形同虚设 | opportunity | HIGH | ✅ |
| 3 | why_now字段为空，机会时效性论证完全缺失 | opportunity | HIGH | ✅ |
| 4 | 2.2仅处理1个信号，另外2个信号（technical/market）被完全丢弃 | orchestration | MEDIUM | ✅（规则引擎行为，LLM模式下会改善） |
| 5 | exit_conditions_count为0，watch姿态缺乏终止条件设计 | action | MEDIUM | ✅ |

所有发现均为**语义层**问题，规则归因层无法识别。

### 3.3 Phase 3 优先项（5 条）

均已落入报告第五节，可直接消费。

---

## 四、关键工程修复记录（2026-03-29）

### 4.1 LLM 响应截断问题（根本解决）

**症状**：JSON 在 ~3000-5000 字符处被截断，`Unterminated string` / `Expecting ','`

**根因**：api123.icu 中转代理对非流式响应体有大小限制

**修复**：`llm_client.py` 切换为流式请求（`stream=True`），新增 `_collect_stream()` 消费 SSE 事件流，逐段拼接 `content_block_delta`

**commit**：`eaae132` — fix(llm_client): 切换为流式请求

### 4.2 LLM 前缀说明文字导致 JSON 解析失败

**症状**：`Expecting value: line 1 column 1`，Raw 以"这是一个纯分析任务..."开头

**根因（两层）**：
1. api123.icu 中转 system prompt 导致模型先解释再输出 JSON（中转侧行为，不可控）
2. 解析端只处理 ` ```json ``` ` 格式，未处理前缀文字

**修复（两层）**：
1. **需求侧**（根本解法）：system prompt 加"第一个字符必须是 `{`，不要任何前缀说明或解释"
2. **防御侧**（兜底）：JSON 提取改为取第一个 `{` ~ 最后一个 `}` 区间，兼容所有包裹形式

**commit**：`1449a3a` — fix(2.5): JSON 解析兼容 LLM 前缀说明文字

### 4.3 prompt 输出体积压缩

**症状**：prompt 中塞入 RAG 证据全文（每条 400+ 字符），LLM 分析它们导致输出体积爆炸

**修复**：evidence 只传标题/首句（≤80字），RAG packets 只传计数不传全文，2.3 字段截断至合理长度；system prompt 加总输出 ≤1500字约束

**commit**：`568910c` — fix(2.5): LLMAttributor prompt 压缩

### 4.4 信号字段名错位

**症状**：LLM 归因 prompt 中信号字段为 `summary`/`intensity`/`confidence`，真实 `Signal` schema 字段为 `description`/`intensity_score`/`confidence_score`，导致 LLM 收到空值

**修复**：`llm_attributor.py` 字段名对齐，加 fallback 兼容旧字段名

**commit**：`568910c`（同上）

---

## 五、文件结构

```
phase2.5_implementation/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   └── system_retrospective_schema.py
├── core/
│   ├── __init__.py
│   ├── output_checker.py           # 规则检查 + LLM 语义检查
│   ├── llm_attributor.py           # LLM 深层归因（2026-03-29 新增，主路径）
│   ├── problem_attributor.py       # 规则归因（降为 fallback）
│   ├── priority_closer.py          # 从归因导出优先级
│   └── system_retrospective_analyzer.py
└── examples/
    ├── example_data.py             # ⚠️ 已过时（3月16日手写mock，字段不匹配）
    ├── run_example.py
    └── example_output.json
```

> **注意**：`example_data.py` 为 3 月 16 日手写 mock，字段已与真实输出不匹配（`priority_level` 枚举值、`uncertainty_map` 结构等）。当前真实验证以 `run_batch_real.py` 运行结果为准，`example_data.py` 待下次清理时用真实输出替换。

---

## 六、已知限制与后续方向

### 6.1 当前限制

| # | 限制 | 影响 | 处理建议 |
|---|------|------|----------|
| 1 | 2.2 LLM 调用仍在 fallback（JSON 截断） | 机会判断由规则引擎生成，2.5 归因只能评估规则引擎产出 | 待 2.2 LLM 稳定后重跑，验证归因对 LLM 输出的评估能力 |
| 2 | 2.3 LLM 偶发 503 | 行动设计偶发规则 fallback | API 侧稳定性问题，重试可恢复 |
| 3 | `example_data.py` 字段过时 | 独立运行 example 时会报错 | 用真实输出替换（低优先级） |
| 4 | 样本规模小（3 条） | 归因结论样本代表性有限 | 积累更多真实运行记录 |

### 6.2 后续增强方向

| 优先级 | 方向 | 触发条件 |
|--------|------|----------|
| P1 | 真实案例积累（20+ 次） | 持续跑 incoming 样本 |
| P1 | 复盘报告纵向对比 | 积累 5+ 次运行后 |
| P2 | 多 Agent 质量审查层 | 2.5 主路径稳定后 |
| P3 | 质量指标看板 | 积累足够运行数据后 |

---

## 七、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-03-16 | 初始创建，MVP 最小闭环验证通过（示例数据） |
| 2026-03-29 | 重大更新：LLM 归因真实链路跑通，findings=5（全部准确），记录四项工程修复（截断/前缀/prompt体积/字段名），能力层级表重新梳理 |

---

**文档状态**：✅ 持续更新中
**版本**：v2.0
**最后更新**：2026-03-29
