# PROJECT_CONTEXT.md — 项目一站式开工入口

> **文档类型**：项目状态总览 + 开工上下文
> **最后更新**：2026-03-28（2.2 完善阶段收尾，推进 2.3 联调回归）
> **当前阶段**：2.2 完善收尾，开始 2.3 联调回归
> **项目状态**：✅ 主链路联调完成，✅ 真实 LLM API 接入，✅ 报告输出层上线，✅ 2.1 两阶段筛选框架，✅ 2.2 多机会输出重构+字段完善，✅ 2.3 结构性缺口修复，⚠️ 2.4 RAG 本地模型路径异常（fallback 跳过，不阻塞主链路）

---

## 一、开工必读（新窗口接手 / 每次开工）

### 1.1 当前整体状态（一句话）

> Phase 2.1 / 2.2 / 2.3 / 2.4 / 2.5 的 MVP 均已完成并通过验证，**主链路联调（P0+P1-1~P1-4）已全部完成**。下一步可选：2.4 知识增强联调（P1-5/6/7）。

### 1.2 当前最高优先级（P0）

| # | 任务 | 阻塞方 | 状态 |
|---|------|--------|------|
| P0-1 | 接入真实 LLM API（2.1 + 2.4 当前为模拟服务） | 2.1、2.4 | ✅ 完成（2.1/2.2/2.3 已接入，2.4 待修） |
| P0-2 | 冻结 2.1→2.2 接口契约 | 整条主链路 | ✅ 完成 |
| P0-3 | 修复 2.4 RAG 本地模型路径 | 知识增强 | ⚠️ 待处理（当前 fallback 跳过，不阻塞主链路） |

### 1.3 联调优先级总览

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P1-1 | 2.1→2.2 接口联调 | ✅ 完成（3/3） |
| P1-2 | 2.2→2.3 接口联调 | ✅ 完成（3/3） |
| P1-3 | 2.3→2.5 接口联调 | ✅ 完成（2/2） |
| P1-4 | 端到端链路联调 | ✅ 完成（1/1，~6242ms） |
| P1-5 | 2.4→2.1/2.2/2.3 知识增强联调 | ✅ 完成（3/3，2026-03-22） |

> 详细优先级见：[phase2_综合联调优先级.md](data-layer/projects/proj_004/phase2_plan/phase2_综合联调优先级.md)

---

## 二、各模块核心定位与当前状态

### 2.1 情报解码（Phase 2.1）

**本质**：把全球游戏行业高熵、碎片化的外部信息，压缩为可进入战略判断流程的低歧义信号单元。不是资讯摘要，而是"变化感知→解码"的前端节点。

**MVP 边界**（已完成）：
- 输入：非结构化文本（新闻/报告/公告）
- 输出：DecodedIntelligence（Signal 列表 + 结构化字段）
- 方法：Prompt-first + 轻量后处理 + Schema 校验
- v1.5 benchmark（25条真实样本）：Precision=95.2% / Recall=87.0% / F1=90.9%

**2026-03-27 增强**：
- Prompt v1.6：五类信号判断框架统一（technical/team/capital 补充显式规则）
- 两阶段筛选：source_type 规则预筛（report 纯趋势 0ms 跳过）+ haiku 粗筛架构（待验证）
- 信号来源：当前依托 knowledge base 仓库每日订阅，后期独立 ingestion 层（已记录，待做）

**后置增强**：taxonomy 边界澄清、2.4 知识增强、并发批处理（100条/天目标）、ingestion 独立化

**遗留待办**：benchmark 对照实验（API 限流中）、haiku 粗筛验证、DecodedIntelligence 消费语义（2.2 推进时定）

**当前状态**：✅ MVP 完成 | ✅ LLM API 已接入 | ✅ P1-1 联调完成 | ✅ v1.6 noise boundary 增强完成

**关键文件**：
- 执行进展：[phase2.1_执行进展.md](data-layer/projects/proj_004/phase2_plan/phase2.1_执行进展.md)
- 联调计划：[phase2.1_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.1_联调与增强计划.md)
- 实现：[phase2.1_implementation/](data-layer/projects/proj_004/phase2.1_implementation/)

---

### 2.2 机会判断（Phase 2.2）

**本质**：帮助组织更早、更稳、更可解释地识别哪些变化值得被升级为下一步行动。不是评估报告生成器，而是"机会判断层 / 机会升级层"。

**MVP 边界**（已完成）：
- 输入：`List[DecodedIntelligence]`（多条，来自 2.1）+ 可选 ContextPacket（来自 2.4）
- 输出：OpportunityObject（12字段，含 priority_level: watch/research/deep_dive/escalate）
- 方法：Prompt-first v2（LLM 自主信号组合+逻辑链推导）+ 规则引擎 fallback
- 2.1 打分（intensity/confidence/timeliness）完整传入，作为 LLM 信号权重判断依据

**2026-03-28 重构（消费语义拍板）**：
- 输入从单条改为多条 `decoded_intelligences: List[DecodedIntelligence]`
- 由 2.2 自主决定哪些信号可以组合成机会（不依赖调用方预分组）
- Prompt-first v2 落地：完整暴露打分+source_type，LLM 做跨文章信号逻辑链组合
- uncertainty_map 格式约定：`[类型] 描述：影响说明`（5种类型枚举）
- 冒烟验证通过：2条跨来源信号（technical+capital）→ 输出逻辑链完整的 OpportunityObject
- **Bug 修复（2026-03-28）**：规则引擎 fallback 中 `intensity` 字段名改为 `intensity_score`（兼容写法），修复 priority 分级 avg_intensity 始终为 0 的问题

**遗留待办**：

| # | 项目 | 优先级 | 状态 | 备注 |
|---|------|--------|------|------|
| 1 | **LLM 完整验证（7/7 全 LLM 路径）** | P1 | ⏳ 后续完善事项 | api123.icu 持续抖动，已验证 case_001/002/003/004 LLM 路径正确；005/006/007 因 API 随机空响应未完成；等稳定窗口重跑 |
| 2 | **2.2→2.3 联调回归** | P1 | ⏳ 进行中 | 本轮推进；opportunities 列表输出、next_validation_questions 语义修正后，确认 2.3 消费逻辑未受影响 |
| 3 | **EvidenceValidator 可信度加权** | P2 | ⏳ 待讨论 | 已实现可追溯性（source_ref 覆盖率占 completeness 20%）；可信度加权挂起——问题：2.1 已打 confidence_score，2.2 再基于 source_type 降权是否双重惩罚？等 2.1 打分机制稳定后讨论 |
| 4 | v1 流程残留清理 | P2 | ⏳ 待做 | judgment_pipeline_v1 + validators v1 标记 deprecated，下次整理时移除 |
| 5 | judgment_config 预留字段实现 | P2 | ⏳ 待做 | min_confidence_threshold 等字段有定义无实现 |

**⚠️ 已移出 P1 的项目（附降级理由，避免误判优先级）**：

- **轻量评分框架**（change_significance / capture_feasibility / timing_window / evidence_strength）：
  原列为 P1，但从未正式拍板（见 phase2.2_待拍板决策清单.md §6.3 状态=☐ 待拍板）。
  2.2 的 first principle 是"机会判断层，主产物是结构化对象+priority_level"，评分是辅助表达而非判断骨架（拍板结论 §5.2）。
  消费方不清晰——2.3 消费 priority_level 做分流，不消费这 4 个维度；人工阅读由 opportunity_thesis 承担。
  **降为 P2 条件性后置**，触发条件：2.3 明确反馈"priority_level 不足以支撑行动设计，需要辅助维度"时再做。

- **简版自然语言摘要**：
  与 opportunity_thesis（已是 2-4 句可读论点）定位重叠，差异未被定义。
  **从优先级列表删除**，等有人明确提出"thesis 不够用"再讨论。

**当前状态**：✅ MVP 完成 | ✅ 消费语义拍板 | ✅ Prompt-first v2 + 多机会输出重构 | ✅ EvidenceValidator 可追溯性 | ⏳ LLM 完整验证（后续完善）| ⏳ 2.3 联调回归（进行中）

**关键文件**：
- 执行进展：[phase2.2_执行进展.md](data-layer/projects/proj_004/phase2_plan/phase2.2_执行进展.md)
- 联调计划：[phase2.2_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.2_联调与增强计划.md)
- 实现：[phase2.2_implementation/](data-layer/projects/proj_004/phase2.2_implementation/)

---

### 2.3 行动设计（Phase 2.3）

**本质**：把 2.2 的机会判断，转化为组织可分阶段承诺、可动态调整、可必要时及时止损的行动结构。不是决策建议写作模块，而是"行动设计层 / 资源承诺层"。

**MVP 边界**（已完成）：
- 输入：OpportunityObject（来自 2.2）
- 输出：ActionDesignResult（姿态 + 分阶段计划 + Go/No-Go + 退出条件 + 资源承诺逻辑）
- 姿态类型：watch / validate / pilot / escalate / hold / stop
- 方法：规则引擎（基于 priority_level + key_assumptions 数量）
- 已完成：3/3 验收案例通过

**后置增强**：资源估算差异化、风险分析深化、Prompt 模式迁移

**当前状态**：✅ MVP 完成 | ✅ 验收通过 | ✅ P1-2/P1-3/P1-4 联调完成 | ✅ LLM 三路辩论已上线 | ✅ 联调回归通过（2026-03-28）| ✅ why_now/next_vq 消费 | ✅ LLM 路径稳定跑通 | ✅ 验证案例集更新（5/5 PASS）| ✅ P3-A debate_summary 透传 | ✅ global_summary 实现

**遗留待办**：

| # | 项目 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | 细粒度资源模型 / 长篇建议模板 / 多 Agent 辩论深化 / 2.4 深度集成 | P2 | 触发条件满足时启动 |

**关键文件**：
- 执行进展：[phase2.3_执行进展.md](data-layer/projects/proj_004/phase2_plan/phase2.3_执行进展.md)
- 联调计划：[phase2.3_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.3_联调与增强计划.md)
- 实现：[phase2.3_implementation/](data-layer/projects/proj_004/phase2.3_implementation/)

---

### 2.4 知识库与 RAG（Phase 2.4）

**本质**：为 2.1/2.2/2.3 提供历史经验、行业知识、外部证据的结构化支撑，是整条链路的"证据基础层"。定位为**证据级上下文供应层**，目标是降低下游决策的不确定性，而非问答系统。

**MVP 边界**（已完成骨架）：
- 知识文档：43条（game_design / market_trend / tech_innovation）
- 接口：/retrieve / /generate / /rag（Flask API）
- 索引：vector_index.faiss + vector_meta.pkl 已构建（all-MiniLM-L6-v2，384维，真实 embedding）
- 已完成：本地闭环联调验证通过（P1-5/P1-6/P1-7，2026-03-22）

**⚠️ 关键设计拍板（2026-03-28）**：
- **交付单元升级**：输出从 `Document[]` 升级为 `ContextPacket[]`（含 `content_type / excerpt / reason_for_match / trust_level`）
- **`content_type` 而非 `use_as`**：2.4 描述内容性质（是什么），怎么用由 2.1/2.2/2.3 各自决定
- **content_type 枚举**：`glossary / few_shot_example / constraint_rule / case_record / market_data / background`
- **当前知识库缺口**：`case_record` 和 `market_data` 严重不足，是 2.2/2.3 接入的前置障碍
- **协议文档**：[PHASE2_4_CONTEXT_PACKET_PROTOCOL.md](data-layer/projects/proj_004/phase2.4_implementation/docs/PHASE2_4_CONTEXT_PACKET_PROTOCOL.md)（v1.0 已冻结）

**待完成**（按优先级）：
1. ~~实现 `POST /api/v1/context` 接口（ContextRequest → ContextResponse）~~ ✅ 完成（2026-03-29，`retrieve_context()` 已联调）
2. ~~给 43 条现有文档补标 `content_type` 字段~~ ✅ 完成（62 条文档全部已标注）
3. **知识库内容来源模块**（新增，2026-03-29 拍板）：需要独立的可信内容搜索模块，专门负责发现和录入知识库条目，不依赖手动维护；触发时机：知识库扩充工作量超过手动可维护边界时
4. 补充 `case_record` / `market_data` 类型知识文档（当前 case_record=16, market_data=10, constraint_rule=2, few_shot_example=2，background 占比过高=32）
5. 检索精度增强（见下方独立说明，2026-03-29 讨论）
6. 2.4 → 2.1/2.2/2.3 增益联合验证（最终验收终点）

**检索精度增强路线**（2026-03-29 讨论，按触发时机排序）：

| 技术 | 触发时机 | 前置条件 | 备注 |
|------|---------|---------|------|
| **category_filter**（2026-03-29 拍板加入计划） | 同一 `content_type` 开始跨多个领域，且下游反馈召回了不相关领域的案例 | 知识库规模扩大至包含多个垂直领域；`tags` 质量问题先修复（当前 content_type 值混入 tags） | 字段已在 `ContextRequest` 中预留，届时只需在 `retrieve_context()` 加一层候选过滤；当前 content_type 分桶已间接覆盖该需求，规模未到触发点前不实现 |
| **混合检索（BM25 + 向量）** | 发现专有名词（公司名/产品名）向量召回效果差 | 向量检索主路径稳定 | — |
| **Scoping / Query Routing / Query Transformation** | 多模块接入后，query 与知识子集出现系统性错配 | 2.1/2.2/2.3 均已接入 2.4 | 入口层技术，由 `caller` + query 语义驱动 |
| **重排序（Rerank）** | 分桶召回稳定后，top-k 排序质量成为瓶颈 | 分桶召回已稳定运行一段时间，有下游增益数据作为基线 | 定位为 `retrieve_context()` 内部可插拔层，不改外部接口 |

> **设计原则**：以上均为增益型增强，不是前置阻塞。先保证"稳定召回"，再追求"精准排序"。tags 质量问题（当前 content_type 值混入 tags）需在 category_filter 实现前修复，否则 tags 也不适合作为过滤维度。

**当前状态**：✅ 骨架完成 | ✅ 真实 Embedding 接入（all-MiniLM-L6-v2）| ✅ P1-5/P1-6/P1-7 联调完成 | ✅ ContextPacket 协议冻结（v1.0）| ⚠️ 真实 LLM e2e 待验证（api123.icu 波动）

**关键文件**：
- 协议规范：[PHASE2_4_CONTEXT_PACKET_PROTOCOL.md](data-layer/projects/proj_004/phase2.4_implementation/docs/PHASE2_4_CONTEXT_PACKET_PROTOCOL.md)
- 第一性原理：[PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md](data-layer/projects/proj_004/phase2.4_implementation/docs/PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md)
- 进展：[phase2.4_进展与待拍板事项.md](data-layer/projects/proj_004/phase2_plan/phase2.4_进展与待拍板事项.md)
- 联调计划：[phase2.4_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.4_联调与增强计划.md)
- 实现：[phase2.4_implementation/](data-layer/projects/proj_004/phase2.4_implementation/)

---

### 2.5 整合验证与复盘（Phase 2.5）

**本质**：把 2.1~2.4 的局部能力压入真实工作流，验证系统级有效性，识别关键失真点，沉淀为阶段3优化依据。不是收尾材料整理，而是"现实校验层 / 闭环学习层"。

**MVP 边界**（已完成）：
- 输入：来自 2.1~2.4 的中间对象和最终输出
- 输出：结构化系统复盘对象 + 阶段3优先级判断
- 已完成：OutputChecker / ProblemAttributor / PriorityCloser / SystemRetrospectiveAnalyzer
- 已完成：示例验证通过

**当前状态**：✅ MVP 完成 | ✅ P1-3/P1-4 联调完成（端到端链路跑通）

**关键文件**：
- 执行进度：[phase2.5_执行进度.md](data-layer/projects/proj_004/phase2_plan/phase2.5_执行进度.md)
- 实现：[phase2.5_implementation/](data-layer/projects/proj_004/phase2.5_implementation/)

---

## 三、模块间接口关系

### 3.1 标准运作流程（多文档 → 多信号聚合 → 单次判断）

```
外部输入文档批次（新闻/报告/公告，N 篇）
    ↓ 逐篇解码
[2.1 情报解码 ×N] → DecodedIntelligence × N（各含 signals 列表）
    ↓ 合并所有 signals 为统一信号池
[2.2 机会判断 ×1] → OpportunityObject（基于多源信号，priority: watch/research/deep_dive/escalate）
    ↓
[2.3 行动设计 ×1] → ActionDesignResult（posture: watch/validate/pilot/escalate/hold/stop）
    ↓
[2.5 整合验证 ×1] → SystemRetrospectiveObject + Phase3 优先级

[2.4 知识库] ──→ 可选注入 2.1 / 2.2 / 2.3 任意节点
```

**关键设计意图**（来自 2.2 First Principles 文档第 15.1 节）：
> 2.2 的本质是把「多个 2.1 信号」组织成「一个机会候选对象」，而不是逐条点评单篇文档。
> 信号聚合发生在 2.1 → 2.2 的边界：将 N 篇文档产生的 signals 合并后整体送入 2.2 判断。
> 2.3 拿到的是「多源信号驱动的机会判断」，而不是单篇文本的孤立判断。

### 3.2 联调 MVP 简化模式（单文档验证接口契约）

```
单篇文本 → [2.1] → [2.2] → [2.3] → [2.5]
```

> 用于接口联调和回归测试。不代表生产运行模式。

**关键接口约定（联调前必须完成拍板）**：

| # | 约定 | 建议 | 状态 |
|---|------|------|------|
| 1 | LLM API 模型选型 | claude-sonnet-4-6 via api123.icu 中转 | ✅ 已拍板（2026-03-27 实跑确认） |
| 2 | priority_level 到姿态映射规则维护方 | 2.2 定义，2.3 跟随 | ✅ 已拍板（LLM 模式下 2.2 直接输出，2.3 读取） |
| 3 | key_assumptions >=3 触发 validate 阈值是否沿用 | LLM 模式下不强制阈值，规则引擎仅作 fallback | ✅ 已拍板（2.2/2.3 切换为 LLM 判断后规则退居备用） |
| 4 | 2.4 知识增强在 MVP 联调是否必须集成 | 可选，不阻塞主链路 | ✅ 已拍板（RAG 路径报错自动 fallback 跳过，主链路正常） |
| 5 | 知识检索失败时统一降级策略 | 降级为纯 LLM 判断，不报错 | ✅ 已拍板（实跑验证通过） |
| 6 | ActionDesignResult 是否增加 confidence_score | 本轮不增加 | ✅ 已拍板（models.py 未定义，实际输出亦无此字段） |
| 7 | 知识文档扩展目标 | 按命中率决定，不盲目扩展 | ⚠️ 待定（2.4 RAG 修复后，依据真实命中率数据再定） |

---

## 四、Phase 3 入场条件

> Phase 3 不是时间驱动的，而是条件驱动的。以下条件全部满足后才进入 Phase 3。

### 必须满足（全部 ✅ 才可入场）

| # | 条件 | 验收标准 | 当前状态 |
|---|------|----------|----------|
| 1 | 主链路联调通过 | 2.1→2.2→2.3→2.5 端到端跑通 ≥2 个真实案例，各节点无 schema 报错 | ✅ 完成（37条真实样本批量跑通，2026-03-27） |
| 2 | 各模块 LLM API 接入真实服务 | 2.1 / 2.4 替换模拟服务，输出结果可信 | ✅ 2.1/2.2/2.3 已接入（api123.icu）⚠️ 2.4 RAG 本地模型路径异常，知识增强 fallback 跳过 |
| 3 | 接口契约全部冻结 | 2.1→2.2 / 2.2→2.3 / 2.3→2.5 接口契约文档已落档并双方确认 | ✅ 完成（各模块联调计划文档已落档） |
| 4 | 2.5 整合验证完成 | SystemRetrospectiveObject 产出，含问题归因与 Phase 3 优先级建议 | ✅ 完成（critical_findings 正常输出，2026-03-27 修复误报） |
| 5 | 联调前 7 项拍板事项全部确认 | 见第三节接口约定表，全部从「待拍板」变为「已拍板」 | ⚠️ 6/7 已拍板，第7项（知识文档扩展目标）待 2.4 RAG 修复后确认 |

### 可选但建议完成（不阻塞入场）

| # | 条件 | 说明 |
|---|------|------|
| 6 | P2 增强项中至少完成 1 项 | 验证增强路径可行，为 Phase 3 提供参考 |
| 7 | 2.4 知识文档命中率基线已建立 | 为 Phase 3 知识库扩展提供数据依据 |

### 入场时必须产出

进入 Phase 3 前，需产出以下交接材料：
1. Phase 2 整体复盘报告（由 2.5 驱动）
2. Phase 3 优先级建议清单（来自 2.5 的 SystemRetrospectiveObject）
3. 各模块已知技术债务清单（来自各模块执行进展文件）

---

## 五、工作流规范（每次开工/收工必须遵守）

详见：[phase2_统一工作流规范.md](data-layer/projects/proj_004/phase2_plan/phase2_统一工作流规范.md)

**开工 5 步**：读本文档 -> 读综合优先级 -> 读涉及模块执行进展 -> 读涉及模块联调计划 -> 确认无阻塞拍板项

**收工 4 步**：更新执行进展文件 -> 标记联调计划已完成步骤 -> 更新综合优先级状态 -> 如有里程碑更新本文档

---

## 五、项目背景资料入口

| 类型 | 文件 |
|------|------|
| 工程背景手册 | [工程背景手册.md](data-layer/projects/proj_004/工程背景手册.md) |
| 背景索引 | [context/BACKGROUND_INDEX.md](data-layer/projects/proj_004/context/BACKGROUND_INDEX.md) |
| 资料来源地图 | [context/SOURCE_MAP.md](data-layer/projects/proj_004/context/SOURCE_MAP.md) |
| 阶段2依赖关系 | [phase2_plan/子阶段依赖关系与并行策略.md](data-layer/projects/proj_004/phase2_plan/子阶段依赖关系与并行策略.md) |
| 综合联调优先级 | [phase2_plan/phase2_综合联调优先级.md](data-layer/projects/proj_004/phase2_plan/phase2_综合联调优先级.md) |

---

## 六、正式版模型选型方案

> 当前中转 API（api123.icu）为临时方案，正式版替代选项如下：

| 方案 | 模型 | 适用场景 | 说明 |
|------|------|----------|------|
| **官方 Anthropic** | claude-sonnet-4-x | 正式生产 | 直接换 `ANTHROPIC_API_KEY` + 去掉 `ANTHROPIC_BASE_URL` 即可，代码已支持 |
| **OpenAI 兼容接口** | gpt-4o / gpt-4.1 | 如需换厂商 | decoder 里 requests 路径已写成通用结构，换 base_url 即可 |
| **腾讯混元** | hunyuan-turbos / pro | 内网/合规优先 | 需加一层适配器把 OpenAI format → 混元格式，改动约 30 行 |
| **本地部署** | Qwen2.5-72B / DeepSeek-R1 | 离线/低成本 | 通过 Ollama/vLLM 起 OpenAI 兼容服务，换 base_url 即可 |

**迁移步骤（官方 Anthropic）**：
1. 删除 `.env` 里的 `ANTHROPIC_BASE_URL`
2. 替换 `ANTHROPIC_API_KEY` 为官方 key
3. 无需改代码，decoder 会自动走官方 SDK 路径

---

## 七、各模块迭代路线图（正式版完善计划）

> 基于各模块 MVP_SCOPE 文档与 FIRST_PRINCIPLES 文档整理。当前 MVP 已完成，以下为通往正式版的增强路径。

---

### 7.1 Phase 2.1 情报解码

**当前状态**：v1.5 prompt 已上线，Precision 测量体系建立，5类信号 taxonomy 稳定

| 优先级 | 增强项 | 说明 |
|--------|--------|------|
| P1 | **benchmark 扩展指标** | 在现有准确率/召回率基础上补入：信号价值密度、噪音抑制率、边界样本稳定性、下游可消费性四项观察维度 |
| P1 | **Prompt 角色设定轻调** | 若 benchmark 暴露明显误报/边界不稳，做一轮 wording 收口 + 边界约束补强，不整体重写 |
| P2 | **定向 few-shot 补强** | 基于 benchmark 错误类型画像，补 2-4 条高针对性 few-shot（边界样本/反例/命名标准） |
| P2 | **2.4 → 2.1 动态上下文增强** | 接入 2.4 的 context_packet：术语定义、判定边界、历史高质量案例作为 retrieval_context；接口已预留，等 2.4 RAG 修好后联调 |
| P3 | **few-shot 资产体系** | 样例类型全面重构 + 维护规则 + 错误类型映射体系 + Prompt 版本化管理；建立在 benchmark 反馈上 |
| P3 | **多信号聚合优化** | 同一文本产出多个信号时的去重、权重、置信度汇总规则 |

---

### 7.2 Phase 2.2 机会判断

**当前状态**：LLM 判断模式已上线（替代规则引擎），12字段机会对象稳定输出

| 优先级 | 增强项 | 说明 |
|--------|--------|------|
| P1 | **轻量评分框架** | 补充 `change_significance / capture_feasibility / timing_window / evidence_strength` 四项评分维度，作为辅助表达，有解释有证据 |
| P1 | **简版自然语言摘要** | 结构化对象基础上派生可读摘要，服务于人工验证与协作沟通 |
| P2 | **多 Agent 辩论增强（P3-A）** | `debate_summary` 透传（hawk/dove/arbitrator），已有代码骨架，~30 分钟；详见 phase2.3_联调与增强计划.md P3-A 节 |
| P2 | **历史案例对比** | 接入 2.4 知识库的相似案例，支持"为什么这次选 deep_dive 而不是 research"的可追溯解释 |
| P3 | **完整可配置评分体系** | 维度权重配置、评分版本管理、评分校准与案例回放；建立在轻量评分验证之后 |
| P3 | **姿态变更追踪** | 同一机会在不同时间点重新评估时记录姿态变化轨迹 |

---

### 7.3 Phase 2.3 行动设计

**当前状态**：LLM 三路辩论已上线，6种行动姿态稳定输出，分阶段计划/风险/退出条件完整

| 优先级 | 增强项 | 说明 |
|--------|--------|------|
| P1 | **debate_summary 透传（P3-A）** | `ActionDecisionObject` 增加 `debate_summary` 字段，从 LLM 输出取出透传；报告层已预留展示位，~30 分钟改动 |
| P1 | **资源估算规则细化** | 当前只有粗粒度资源表达；补充阶段级人力/预算/时间带宽的轻量规则，不做精算系统 |
| P2 | **辩论轮次深化（P3-B）** | 鹰/鸽加入"回应对方论点"的第二轮，仲裁看完整来回后判断；token 消耗约增加 50%；有明确质量瓶颈时再做 |
| P2 | **场景化路径模板库** | 验证型/试点型/升级型三类基本路径模板；避免完全从零生成动作结构 |
| P3 | **辩论历史沉淀复用（P3-C）** | 把每次辩论的鹰/鸽/仲裁观点存入 2.4 知识库；下次遇到相似机会时 RAG 检索历史辩论作参考；2.4 RAG 稳定后做 |
| P3 | **多 Agent 行动设计编排** | 路径推进/风险约束/资源现实性多角色视角；行动骨架稳定后再引入 |

---

### 7.4 Phase 2.4 知识库与 RAG

**当前状态**：骨架完成（40条知识文档，FAISS 向量索引），本地 BERT 模型路径报错导致 fallback，知识增强实际未生效

| 优先级 | 增强项 | 说明 |
|--------|--------|------|
| **P0** | **修复本地 BERT 模型路径** | 路径含中文/特殊字符，HuggingFace 拒绝识别；改用在线拉取或换用短路径；当前主链路 fallback 跳过，不阻塞但知识增强无效 |
| P1 | **混合检索（向量 + 关键词）** | 当前只有向量搜索；BM25 或关键词检索作补充，提升精确命中率 |
| P1 | **上下文包结构化输出** | 当前 RAG 返回纯文本；改为结构化 context_packet（source_type/excerpt/content_type/trust_level 等），对齐 FIRST_PRINCIPLES 设计 |
| P1 | **2.4 → 2.1/2.2/2.3 真实联调** | BERT 路径修好后，与三个下游模块做真实数据联调，建立命中率基线（第7项拍板事项的前置条件） |
| P2 | **知识文档扩展至 100 条** | 依据真实命中率数据决定扩展方向；不盲目扩展 |
| P2 | **增益可验证机制** | 对比接入 2.4 前后下游模块输出质量变化（2.1 准确率/2.2 论点完整度/2.3 假设覆盖度） |
| P2 | **文档版本管理** | 知识文档的更新/废弃/版本追踪机制 |
| P3 | **动态知识更新** | 新信号自动触发知识库更新评估；长期运行场景下保持知识库新鲜度 |
| P3 | **跨模块证据追踪** | 同一知识片段被 2.1/2.2/2.3 分别引用时的来源统一追踪 |

---

### 7.5 Phase 2.5 整合验证与复盘

**当前状态**：OutputChecker/ProblemAttributor/PriorityCloser 已上线，upstream_outputs 字段修复，critical_findings 正常输出

| 优先级 | 增强项 | 说明 |
|--------|--------|------|
| P1 | **真实案例积累** | 持续跑真实 incoming 样本，积累 20+ 次运行记录；让 2.5 的复盘从"单次验证"变成"趋势分析" |
| P1 | **复盘报告纵向对比** | 跨多次运行对比 posture 分布/信号密度/findings 数量变化；识别系统质量趋势 |
| P2 | **多 Agent 质量审查层** | 在 2.5 引入独立的质量审查 Agent，对 2.1~2.3 输出做对抗性验证；这是多 Agent 在整个链路中最自然的落点 |
| P2 | **自动化归因增强** | 当前 ProblemAttributor 规则较简单；引入 LLM 做更深层的根因分析 |
| P3 | **质量指标看板** | 系统级质量数据可视化；需积累足够运行数据后再做 |
| P3 | **大规模案例池机制** | 100+ 案例的管理、检索、回放机制；配合 2.4 知识库扩展 |

---

## 八、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-03-13 | 初始创建，记录 Phase 2.4 开发状态 |
| 2026-03-16 | 全面重写：纳入 2.1~2.5 各模块核心定位、MVP 边界、接口约定、工作流规范 |
| 2026-03-22 | 更新联调状态：P0+P1-1~P1-4 全部完成，主链路端到端跑通 |
| 2026-03-27 | 接入真实 LLM API（api123.icu 中转），2.1 v1.5 prompt + Precision 测量体系，2.2/2.3 LLM 判断上线，报告输出层（report_writer.py）上线，2.5 upstream_outputs 字段修正，2.1 per-sample 容错，2.3 多 agent 完善路线写入规划文档 |
| 2026-03-28（凌晨） | 2.2 消费语义重构：多条输入+Prompt-first v2（_llm_judge_v2），2.1 打分全透传，冒烟验证通过 |
| 2026-03-28 | 修复 2.2 规则引擎 fallback 中 intensity 字段名 bug（avg_intensity 始终为 0 导致 priority 分级偏低） |
| 2026-03-28（晚） | 2.4 ContextPacket 协议 v1.0 冻结：content_type 枚举（glossary/few_shot_example/constraint_rule/case_record/market_data/background）、ContextRequest/ContextResponse 字段定义、三模块消费场景差异确认、兼容策略（新增 /context 接口，原接口不变） |

---

**文档维护说明**：
- 每次收工如有重要里程碑，更新第一节的 P0/P1 状态表和第六节更新日志
- 各模块核心定位与 MVP 边界为稳定内容，不频繁修改
- 详细进度以各模块执行进展文件为准，本文档只做状态摘要

