# Phase 2.2 联调与增强计划

> **文档类型**：联调与增强执行计划
> **当前状态**：✅ MVP 完成，✅ 验收通过，⏳ 等待联调
> **最后更新**：2026-03-16

---

## 一、模块现状摘要

| 项目 | 状态 |
|------|------|
| MVP 实现 | ✅ 完成（schemas + validators + judgment_engine） |
| 验收测试 | ✅ 7/7 通过 |
| 与 2.1 上游联调 | ☐ 未启动 |
| 与 2.3 下游联调 | ☐ 未启动 |
| 2.4 知识增强 | ⏳ 可选，未启动 |

---

## 二、联调任务（优先执行）

### A: 与 2.1 上游联调

| 步骤 | 任务 | 输入 | 输出 | 验收标准 |
|------|------|------|------|----------|
| A1 | 确认 DecodedIntelligence 字段到 JudgmentEngine 输入的映射 | 2.1 真实输出样例 | 字段映射确认文档 | 无缺失必填字段 |
| A2 | 用 2.1 输出驱动 JudgmentEngine 跑通 2 个案例 | DecodedIntelligence 实例 | OpportunityObject | 优先级判断合理 |
| A3 | 验证信号不足时 BoundaryValidator 正确拦截 | 低质量输入 | 错误/降级输出 | 有明确错误信息 |
| A4 | 冻结上游接口契约 | 联调结果 | 契约文档 | 双方确认 |

### B: 与 2.3 下游联调

| 步骤 | 任务 | 输入 | 输出 | 验收标准 |
|------|------|------|------|----------|
| B1 | 确认 OpportunityObject 到 ActionDesignRequest 的字段映射 | 2.2 schemas.py + 2.3 models.py | 映射表 | 无歧义 |
| B2 | 用 2.2 真实输出驱动 2.3 ActionDesigner 跑通 2 个案例 | OpportunityObject 实例 | ActionDesignResult | 无 schema 报错 |
| B3 | 验证优先级到姿态映射一致性（deep_dive→pilot, research→validate 等） | 各优先级案例 | 对应姿态 | 映射规则一致 |
| B4 | 冻结下游接口契约 | 联调结果 | 契约文档 | 双方确认 |

### C: 与 2.4 知识增强联调（可选）

| 步骤 | 任务 | 说明 |
|------|------|------|
| C1 | 确认 2.4 RAG 检索结果可作为 ContextPacket 注入 JudgmentEngine | 调用样例验证 |
| C2 | 对比有/无 2.4 支持时 evidence_ratio 计算差值 | 评估增强价值 |
| C3 | 验证 2.4 不可用时降级路径正常工作 | 降级验证 |

---

## 三、增强任务（联调稳定后）

### 增强A：优先级分级阈值精调（P1）

- **问题**：watch/research/deep_dive/escalate 阈值基于规则，边界案例判断稳定性待验证
- **方案**：引入联调真实案例反馈，微调 signal_count + evidence_ratio 阈值组合
- **触发时机**：端到端联调中出现优先级判断与预期不符

### 增强B：证据完整度算法优化（P2）

- **问题**：当前证据完整度权重固定（支持30% + 反对30% + 假设20% + 不确定性20%）
- **方案**：根据真实案例反馈调整权重，或引入动态权重
- **触发时机**：2.3 反馈姿态判断依据不充分

### 增强C：escalate 级别判断增强（P1）

- **问题**：escalate 条件较严苛（signal_count≥5 + avg_intensity≥8 + 竞争关键词），真实案例覆盖率待验证
- **方案**：补充 escalate 真实案例，调整条件组合
- **触发时机**：端到端测试中 escalate 案例判断不准确

---

## 四、待拍板事项

| 拍板项 | 建议 | 状态 |
|--------|------|------|
| priority_level 到 2.3 姿态的映射规则是否共同维护一份 | 建议在 2.2 侧定义，2.3 跟随 | ☐ 待拍板 |
| 2.4 知识增强是否纳入本轮联调 | 推荐可选，不阻塞主链路 | ☐ 待拍板 |
| escalate 阈值是否在联调前调整 | 先联调验证，按真实案例调整 | ☐ 待拍板 |

---

**文档状态**：v1.0
**最后更新**：2026-03-16

---

## 五、Step A 优化增强任务（2026-04-01 新增）

### 背景

Step A 优化方案设计完成，详见 docs/step_a_optimization_design.md。
核心变化：signal_groups（硬分组）→ logical_scenarios（软场景建议），Step C 接收全量信号。

### 实施任务

| 步骤 | 任务 | 文件 | 验收标准 |
|------|------|------|----------|
| SA1 | step_a_cluster.py：新增 LogicalScenario 数据类，改造输出结构 | step_a_cluster.py | StepAResult.logical_scenarios 有正确输出 |
| SA2 | step_a_cluster.py：Prompt 增加 few-shot 逻辑互补案例（3-5个） | step_a_cluster.py | LLM 输出跨域组合概率提升 |
| SA3 | judgment_engine.py：新增 _build_scenario_request，全量信号 + 场景建议注入 | judgment_engine.py | Step C 每次调用可见全量信号 |
| SA4 | judgment_engine.py：高强度孤立信号兜底扫描（intensity ≥ 7） | judgment_engine.py | 强信号不因无 scenario 而直接进 Step B |
| SA5 | unit_tests_phase22.py：更新涉及 signal_groups 的断言 | unit_tests_phase22.py | 原有测试全部通过 |

### 待拍板事项（实施前确认）

| 拍板项 | 建议 | 状态 |
|--------|------|------|
| 16-50 条批次：每个 scenario 独立调用 Step C，还是全量信号一次调用（传入所有 scenarios 作建议）？ | 建议每个 scenario 独立调用后去重合并 | ⏳ 待拍板 |
| 高强度孤立信号兜底阈值：intensity ≥ 7 是否合适？ | 先用 7，跑批后按实际结果调整 | ⏳ 待拍板 |

**文档状态**：v1.1
**最后更新**：2026-04-01
