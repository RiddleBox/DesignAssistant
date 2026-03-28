# Phase 2.4 联调与增强计划

> **文档类型**：联调与增强执行计划
> **当前状态**：✅ MVP 骨架完成，✅ 40条知识文档+索引已建，⏳ 等待联调
> **最后更新**：2026-03-22

---

## 一、模块现状摘要

| 项目 | 状态 |
|------|------|
| RAG 系统骨架 | ✅ 完成（/retrieve /generate /rag API） |
| 知识文档 | ✅ 40条（kb_001~kb_040），索引已建 |
| Benchmark 基线 | ✅ 已完成（benchmark_report.json） |
| 真实 LLM API 接入 | ⏳ 当前为模拟服务 |
| 与 2.1/2.2/2.3 联调 | ✅ 完成（P1-5/P1-6/P1-7，2026-03-22） |
| 知识文档扩展至100条 | ☐ 未完成 |

---

## 二、联调任务（优先执行）

### A: 为 2.1 提供知识支持

| 步骤 | 任务 | 输入 | 输出 | 验收标准 |
|------|------|------|------|----------|
| A1 | 确认 2.1 decoder 调用 /retrieve 接口的参数格式 | 2.1 调用需求 + 2.4 API 文档 | 调用样例 | 无格式错误 |
| A2 | 验证信号类型相关知识（technical/market/team/capital）可被正确检索 | 各类型查询 | top-5 文档 | 相关性合理 |
| A3 | 验证 2.1 接入后 Precision 有所提升 | 有/无 2.4 benchmark 对比 | 对比结果 | 有可量化增益 |

### B: 为 2.2 提供知识支持

| 步骤 | 任务 | 输入 | 输出 | 验收标准 |
|------|------|------|------|----------|
| B1 | 确认 ContextPacket 字段与 2.4 检索结果结构对齐 | 2.2 ContextPacket 定义 | 字段映射确认 | 无冗余/缺失 |
| B2 | 验证市场趋势、竞争情报类知识可被 2.2 消费 | OpportunityObject 查询 | 相关知识片段 | 可注入判断上下文 |
| B3 | 验证 2.4 不可用时 2.2 降级路径正常 | 模拟 2.4 超时 | 降级输出 | 无崩溃，有降级标注 |

### C: 为 2.3 提供知识支持

| 步骤 | 任务 | 输入 | 输出 | 验收标准 |
|------|------|------|------|----------|
| C1 | 确认行动设计相关知识（资源承诺、风险案例）可被检索 | ActionDesignRequest 关键词 | 相关文档 | 覆盖主要姿态类型 |
| C2 | 验证检索结果可注入 ActionDesigner 的 resource_commitment_logic 生成 | 检索结果 + 生成逻辑 | 增强后的承诺逻辑 | 质量优于纯规则 |

### D: 真实 LLM API 接入

| 步骤 | 任务 | 说明 |
|------|------|------|
| D1 | 替换模拟 /generate 为真实 Claude API 调用 | 使用 claude-sonnet-4-6 |
| D2 | 验证 /rag 端到端在真实 API 下的响应质量 | 对比模拟结果 |
| D3 | 设置每日调用上限，记录 API 成本 | 避免超支 |

---

## 三、增强任务（联调稳定后）

### 增强A：知识文档扩展至100条（P1）

- **当前**：43条，覆盖 game_design/market_trend/tech_innovation 三类
- **方案**：按联调反馈优先补充检索命中率低的类别
- **触发时机**：联调中发现特定类型查询无相关结果

### 增强B：混合检索（向量 + 关键词）（P2）

- **当前**：纯向量检索
- **方案**：引入 BM25 关键词检索，结果融合后重排序
- **触发时机**：纯向量检索对专有名词检索效果差

### 增强C：知识分类体系扩展（P2）

- **当前**：3类（game_design/market_trend/tech_innovation）
- **方案**：按真实查询分布新增 1-2 类
- **触发时机**：联调中下游模块查询类型明显超出当前分类

### 增强D：ContextPacket 协议实现（P1）✅ 进行中

**协议文档**：`phase2.4_implementation/docs/PHASE2_4_CONTEXT_PACKET_PROTOCOL.md` v1.0（2026-03-28 冻结）

**已完成**：
- `models.py` 新增 `ContextPacket / ContextRequest / ContextResponse` dataclass
  - `content_type` 枚举：`glossary / few_shot_example / constraint_rule / case_record / market_data / background`
  - `trust_level` 枚举：`high / medium / low`（基于 metadata.confidence 和来源评定）
  - `ContextRequest` 支持 `needed_content_types / caller / category_filter / min_trust_level`
- `retrieval.py` 新增 `Retriever.retrieve_context()` 方法
  - **分桶召回**（Bucketed Retrieval）：每种 `content_type` 独立配额，先过滤候选集再在其中做向量检索
  - 辅助函数：`_build_reason_for_match()`（模板化生成）、`_calc_trust_level()`（评定信任等级）
  - 冒烟验证：`content_type=None` 的文档正确被过滤，notes 说明命中为空的原因
- `app.py` 新增 `/api/v1/context` 路由，原接口不变（兼容策略）

**待完成**：
- [ ] **给 43 条文档补标 `content_type` 字段**（P0，当前全为 None，导致 retrieve_context 返回空）
  - 标注规则：每条文档只标一个主性质；`case_record` 必须含主体+动作+结果三要素
  - 重点补充：`case_record` 和 `market_data` 两类（当前严重不足，是 2.2/2.3 接入的前置障碍）
- [ ] Document dataclass 新增 `content_type` 可选字段（当前从 yaml 加载时字段不存在）
- [ ] 用真实数据端到端验证 `/api/v1/context` 接口

**intent routing（后续增强）**：
- 当前：调用方显式传 `needed_content_types`
- 后续：2.4 根据 `caller` + `query` 语义自动推断 `needed_content_types`，调用方无需手动指定
- 触发条件：分桶召回稳定后，联调反馈"每次指定类型太繁琐"时引入

---

## 四、待拍板事项

| 拍板项 | 建议 | 状态 |
|--------|------|------|
| 真实 LLM API 接入时机 | 联调前必须完成，避免模拟结果掩盖真实问题 | ☐ 待拍板 |
| 知识文档扩展目标（100条 or 按需） | 先联调，按命中率决定扩展优先级 | ☐ 待拍板 |
| 混合检索是否纳入本轮 | 推荐 MVP 联调阶段不引入，联调完成后评估 | ☐ 待拍板 |
| 分类体系是否本期扩展 | 保持3类至 MVP 联调验收完成 | ☐ 待拍板 |

---

**文档状态**：v1.0
**最后更新**：2026-03-16