# PROJECT_CONTEXT.md — 项目一站式开工入口

> **文档类型**：项目状态总览 + 开工上下文
> **最后更新**：2026-03-22
> **当前阶段**：Phase 2 主链路联调全部完成（P0+P1-1~P1-4）
> **项目状态**：✅ 主链路联调完成，待评估 P1-5/6/7 知识增强联调

---

## 一、开工必读（新窗口接手 / 每次开工）

### 1.1 当前整体状态（一句话）

> Phase 2.1 / 2.2 / 2.3 / 2.4 / 2.5 的 MVP 均已完成并通过验证，**主链路联调（P0+P1-1~P1-4）已全部完成**。下一步可选：2.4 知识增强联调（P1-5/6/7）。

### 1.2 当前最高优先级（P0）

| # | 任务 | 阻塞方 | 状态 |
|---|------|--------|------|
| P0-1 | 接入真实 LLM API（2.1 + 2.4 当前为模拟服务） | 2.1、2.4 | ✅ 完成 |
| P0-2 | 冻结 2.1→2.2 接口契约 | 整条主链路 | ✅ 完成 |

### 1.3 联调优先级总览

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P1-1 | 2.1→2.2 接口联调 | ✅ 完成（3/3） |
| P1-2 | 2.2→2.3 接口联调 | ✅ 完成（3/3） |
| P1-3 | 2.3→2.5 接口联调 | ✅ 完成（2/2） |
| P1-4 | 端到端链路联调 | ✅ 完成（1/1，~6242ms） |
| P1-5 | 2.4→2.1/2.2/2.3 知识增强联调 | ☐ 未启动（可选，可并行） |

> 详细优先级见：[phase2_综合联调优先级.md](data-layer/projects/proj_004/phase2_plan/phase2_综合联调优先级.md)

---

## 二、各模块核心定位与当前状态

### 2.1 情报解码（Phase 2.1）

**本质**：把全球游戏行业高熵、碎片化的外部信息，压缩为可进入战略判断流程的低歧义信号单元。不是资讯摘要，而是"变化感知→解码"的前端节点。

**MVP 边界**（已完成）：
- 输入：非结构化文本（新闻/报告/公告）
- 输出：DecodedIntelligence（Signal 列表 + 结构化字段）
- 方法：Prompt-first + 轻量后处理 + Schema 校验
- 已完成：v1.2 benchmark（准确率达标），30条样本

**后置增强**：taxonomy 边界澄清、2.4 知识增强、多信号聚合优化

**当前状态**：✅ MVP 完成 | ✅ LLM API 已接入 | ✅ P1-1 联调完成

**关键文件**：
- 执行进展：[phase2.1_执行进展.md](data-layer/projects/proj_004/phase2_plan/phase2.1_执行进展.md)
- 联调计划：[phase2.1_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.1_联调与增强计划.md)
- 实现：[phase2.1_implementation/](data-layer/projects/proj_004/phase2.1_implementation/)

---

### 2.2 机会判断（Phase 2.2）

**本质**：帮助组织更早、更稳、更可解释地识别哪些变化值得被升级为下一步行动。不是评估报告生成器，而是"机会判断层 / 机会升级层"。

**MVP 边界**（已完成）：
- 输入：DecodedIntelligence（来自 2.1）+ 可选 ContextPacket（来自 2.4）
- 输出：OpportunityObject（12字段，含 priority_level: watch/research/deep_dive/escalate）
- 方法：规则引擎（6步判断流程）+ 4个边界检查点
- 已完成：7/7 验收案例通过

**后置增强**：多 Agent 辩论、复杂评分体系、完整评估报告

**当前状态**：✅ MVP 完成 | ✅ 验收通过 | ✅ P1-1/P1-2 联调完成

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

**当前状态**：✅ MVP 完成 | ✅ 验收通过 | ✅ P1-2/P1-3 联调完成

**关键文件**：
- 执行进展：[phase2.3_执行进展.md](data-layer/projects/proj_004/phase2_plan/phase2.3_执行进展.md)
- 联调计划：[phase2.3_联调与增强计划.md](data-layer/projects/proj_004/phase2_plan/phase2.3_联调与增强计划.md)
- 实现：[phase2.3_implementation/](data-layer/projects/proj_004/phase2.3_implementation/)

---

### 2.4 知识库与 RAG（Phase 2.4）

**本质**：为 2.1/2.2/2.3 提供历史经验、行业知识、外部证据的结构化支撑，是整条链路的"证据基础层"。非主链路必要节点，但显著提升各模块输出质量。

**MVP 边界**（已完成骨架）：
- 知识文档：40条（game_design / market_trend / tech_innovation）
- 接口：/retrieve / /generate / /rag（Flask API）
- 索引：vector_index.faiss + vector_meta.pkl 已构建
- 已完成：本地闭环联调验证通过

**待完成**：真实 LLM API 接入（当前为模拟服务）、与下游模块联调

**后置增强**：混合检索、文档扩展至100条、分类体系扩展

**当前状态**：✅ 骨架完成 | ⚠️ LLM API 为模拟服务 | ☐ 与下游联调未启动

**关键文件**：
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

```
外部输入（新闻/报告）
    ↓
[2.1 情报解码] → DecodedIntelligence
    ↓
[2.2 机会判断] → OpportunityObject (priority: watch/research/deep_dive/escalate)
    ↓
[2.3 行动设计] → ActionDesignResult (posture: watch/validate/pilot/escalate/hold/stop)
    ↓
[2.5 整合验证] → SystemRetrospectiveObject + Phase3 优先级

[2.4 知识库] ──→ 可选注入 2.1 / 2.2 / 2.3 任意节点
```

**关键接口约定（联调前必须完成拍板）**：

| # | 约定 | 建议 | 状态 |
|---|------|------|------|
| 1 | LLM API 模型选型 | claude-sonnet-4-6 | 待拍板 |
| 2 | priority_level 到姿态映射规则维护方 | 2.2 定义，2.3 跟随 | 待拍板 |
| 3 | key_assumptions >=3 触发 validate 阈值是否沿用 | 沿用，联调后调整 | 待拍板 |
| 4 | 2.4 知识增强在 MVP 联调是否必须集成 | 可选，不阻塞主链路 | 待拍板 |
| 5 | 知识检索失败时统一降级策略 | 降级为纯规则，有降级标注 | 待拍板 |
| 6 | ActionDesignResult 是否增加 confidence_score | 本轮不增加 | 待拍板 |
| 7 | 知识文档扩展目标 | 按命中率决定，不盲目扩展 | 待拍板 |

---

## 四、Phase 3 入场条件

> Phase 3 不是时间驱动的，而是条件驱动的。以下条件全部满足后才进入 Phase 3。

### 必须满足（全部 ✅ 才可入场）

| # | 条件 | 验收标准 | 当前状态 |
|---|------|----------|----------|
| 1 | 主链路联调通过 | 2.1→2.2→2.3→2.5 端到端跑通 ≥2 个真实案例，各节点无 schema 报错 | ☐ 未完成 |
| 2 | 各模块 LLM API 接入真实服务 | 2.1 / 2.4 替换模拟服务，输出结果可信 | ☐ 未完成 |
| 3 | 接口契约全部冻结 | 2.1→2.2 / 2.2→2.3 / 2.3→2.5 接口契约文档已落档并双方确认 | ☐ 未完成 |
| 4 | 2.5 整合验证完成 | SystemRetrospectiveObject 产出，含问题归因与 Phase 3 优先级建议 | ☐ 未完成 |
| 5 | 联调前 7 项拍板事项全部确认 | 见第三节接口约定表，全部从「待拍板」变为「已拍板」 | ☐ 未完成 |

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

## 六、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-03-13 | 初始创建，记录 Phase 2.4 开发状态 |
| 2026-03-16 | 全面重写：纳入 2.1~2.5 各模块核心定位、MVP 边界、接口约定、工作流规范 |
| 2026-03-22 | 更新联调状态：P0+P1-1~P1-4 全部完成，主链路端到端跑通 |

---

**文档维护说明**：
- 每次收工如有重要里程碑，更新第一节的 P0/P1 状态表和第六节更新日志
- 各模块核心定位与 MVP 边界为稳定内容，不频繁修改
- 详细进度以各模块执行进展文件为准，本文档只做状态摘要

