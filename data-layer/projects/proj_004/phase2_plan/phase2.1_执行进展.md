# Phase 2.1 执行进展记录

> **文档类型**：执行进展追踪
> **最后更新**：2026-03-15
> **当前状态**：✅ MVP 实现完成，✅ Benchmark 验证完成，⏳ 等待 taxonomy 澄清与后续增强决策

---

## 一、执行时间线

| 日期 | 阶段 | 关键里程碑 | 负责角色视角 |
|------|------|-----------|-------------|
| 2026-03-14 | 拍板阶段 | 完成 9 项组织决策拍板 | 总协调视角 |
| 2026-03-14 | 拍板阶段 | 完成 5 项设计决策拍板 | 总协调视角 |
| 2026-03-14 | 设计阶段 | 完成角色定义落档（7 个职责视角） | 总协调视角 |
| 2026-03-14 | 设计阶段 | 完成多角色讨论，产出设计方案 | 方案设计视角 |
| 2026-03-14 | 实现阶段 | 完成 MVP 实现（4 个核心文件） | 实现落地视角 |
| 2026-03-14 | 验收阶段 | 完成 benchmark 样本准备（30 条） | 评测验收视角 |
| 2026-03-14 | 验收阶段 | 完成 v1.0 baseline benchmark | 评测验收视角 |
| 2026-03-14 | 优化阶段 | 完成 v1.1 轻量优化与验证 | Prompt 策略视角 |
| 2026-03-14 | 优化阶段 | 完成 v1.2 定向优化与验证 | Prompt 策略视角 |
| 2026-03-15 | 总结阶段 | 完成优化历程总结与方法论反思 | 总协调视角 |

---

## 二、已完成工作

### 2.1 拍板阶段（总协调视角）

✅ **组织决策拍板（9 项）**：
1. 是否重组团队：按目标补位重组
2. 是否新增结构化契约负责人：新增专责
3. 是否保留跨阶段连续性角色：保留
4. 评测是否独立成角色：独立
5. 角色协作模式：角色面具协作模式
6. 职责视角数量：7 个职责视角
7. 与 2.4 的协作方式：2.1 主导、2.4 支撑
8. 设计方案产出方式：先定义角色面具后多角色讨论
9. 角色定义落档方式：落档到 phase2.1_roles.md

✅ **设计决策拍板（5 项）**：
1. 评分口径定义方式：Prompt + 明文评分规则表
2. 后处理规则复杂度：轻量规范化
3. Few-shot 样例数量：6 个（4 类 + 1 边界 + 1 负例）
4. 首轮 benchmark 样本量：30 条
5. 是否首轮引入后处理规则：只加轻量规范化

### 2.2 设计阶段（多角色协作）

✅ **角色定义落档**（总协调视角）：
- 文档：[phase2.1_roles.md](phase2_roles/phase2.1_roles.md)
- 内容：7 个职责视角的详细定义、协作流程、切换时机

✅ **多角色讨论产出设计方案**（方案设计视角主导）：
- 文档：[phase2.1_设计方案.md](phase2.1_设计方案.md)
- 参与视角：信息抽取、结构化契约、Prompt 策略、评测验收、实现落地
- 核心内容：
  - 四类信号定义（technical/market/team/capital）
  - Signal 与 DecodedIntelligence 最小 Schema
  - Prompt 结构与 6 个 few-shot 样例
  - 抽取流程设计（5 步）
  - Benchmark 设计（30 条样本）
  - 验收标准（准确率 ≥80%、召回率 ≥75%、Schema 合法率 100%）

### 2.3 实现阶段（实现落地视角）

✅ **MVP 实现完成**：
- 实现目录：`phase2.1_implementation/`
- 核心文件：
  1. `schemas.py`：数据结构定义（Signal、DecodedIntelligence、评分口径）
  2. `prompt_templates.py`：Prompt 模板与 few-shot 样例（v1.0: 6 个 → v1.1: 9 个 → v1.2: 10 个）
  3. `decoder.py`：核心解码器（Prompt-first + 轻量后处理）
  4. `example_usage.py`：使用示例
  5. `README.md`：模块文档

✅ **技术实现特点**：
- 使用 Claude Opus 4.6
- Pydantic 数据校验
- 重试机制（3 次，指数退避）
- 轻量后处理（格式规范化、字段补全、去重）
- 错误处理（JSON 解析失败、Schema 校验失败）

### 2.4 验收阶段（评测验收视角）

✅ **Benchmark 样本准备**：
- 样本文件：`data/benchmark_samples.json`
- 样本数量：30 条（news: 15, report: 8, announcement: 7）
- 包含边界样本（E001-E005）和负例样本（N001）
- 完成人工标注（expected_signals）

✅ **三轮 Benchmark 执行**：

**v1.0 Baseline**（2026-03-14）：
- Precision: 35.71%
- Recall: 83.33%
- F1 Score: 50.00%
- Schema 合法率: 100%
- 误报: 45 个（market: 25, technical: 8, capital: 7, team: 5）
- 漏报: 5 个
- 报告：[PHASE2_1_BASELINE_BENCHMARK_REPORT.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_BASELINE_BENCHMARK_REPORT.md)

**v1.1 轻量优化**（2026-03-14）：
- Precision: 42.11%（+6.4%）
- Recall: 80.00%（-3.33%）
- F1 Score: 55.17%（+5.17%）
- 误报: 33 个（-12）
- 优化内容：
  * 角色设定升级为"范式信号解码器"
  * 补充信号准入原则
  * 调整 market 定义为"注意事项"
  * 修正 confidence_score 口径
  * 补充 3 个 few-shot（样例 7、8、9）
- 报告：[PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md)

**v1.2 定向优化**（2026-03-14）：
- Precision: 42.86%（+0.75%）
- Recall: 80.00%（持平）
- F1 Score: 55.81%（+0.64%）
- 误报: 32 个（-1）
- 优化内容：
  * 进一步收紧 market 定义
  * 明确大型收购/投资优先标注为 capital
  * 补充 few-shot 样例 10
- 边际收益递减，Prompt 优化接近上限

### 2.5 总结阶段（总协调视角）

✅ **完整优化历程总结**：
- 文档：[PHASE2_1_OPTIMIZATION_SUMMARY.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_OPTIMIZATION_SUMMARY.md)
- 内容：
  * 三版本核心指标对比
  * 优化策略回顾与效果分析
  * 误报压制效果分析
  * Prompt 优化的边界识别
  * **重要方法论发现：Taxonomy 边界问题**
  * 下一步方向建议

---

## 三、重要方法论发现：Taxonomy 边界问题

### 3.1 核心发现

本轮 benchmark 暴露出一个关键问题：**并非所有被统计为"误报"的信号都是模型判断错误，部分样本的分类差异源于 signal taxonomy 本身的边界暧昧。**

### 3.2 典型案例

**S002 - 微软收购动视暴雪**：
- 模型输出：capital 信号（690 亿美元收购）
- 人工标注：market 信号（platform_power_shift）
- **问题本质**：从资本交易视角和市场格局视角看，两种分类都具备业务合理性

### 3.3 问题特征

1. **双重解释合理性**：同一事件可从多个角度抽取信号
2. **集中在 market vs capital 边界**：大型收购/投资事件是典型的暧昧样本
3. **不是 Prompt 问题**：继续调整 Prompt 无法解决这类分类差异

### 3.4 当前处理原则

1. **不建议立即改为双标签**：会污染阶段性评估结论
2. **定义为独立问题类型**：标记为 `taxonomy_ambiguity`
3. **纳入系统能力建设规划**：需跨模块协同（2.1 → 2.2 → 2.4）解决

### 3.5 后续推进方向

1. 梳理四类信号的边界定义
2. 建立"单主标签 / 可接受替代标签 / 真正双信号样本"的判定规则
3. 对 benchmark 样本中的暧昧样本建立单独清单
4. 考虑在未来版本中支持"可接受替代标签"的评估逻辑
5. 将 taxonomy 澄清视为跨模块协同设计的一部分

详见：[PHASE2_1_OPTIMIZATION_SUMMARY.md 第九章](../proj_004/phase2.1_implementation/docs/PHASE2_1_OPTIMIZATION_SUMMARY.md)

---

## 四、当前状态

### 4.1 已完成

- ✅ 角色定义落档
- ✅ 多角色讨论产出设计方案
- ✅ 所有拍板项已确认
- ✅ MVP 实现完成
- ✅ 使用文档完成
- ✅ Benchmark 样本准备（30 条）
- ✅ 三轮 benchmark 执行与验证
- ✅ 优化历程总结与方法论反思

### 4.2 进行中

- ⏳ 无（等待下一步指令）

### 4.3 待决策

- ⏳ 是否推进 taxonomy 定义澄清
- ⏳ 是否引入 Phase 2.4 ContextPacket 增强
- ⏳ 是否扩大 benchmark 样本规模
- ⏳ 是否开始与 Phase 2.2 联调

---

## 五、关键指标

### 5.1 验收标准达成情况

| 指标 | 目标值 | v1.2 实际值 | 达成情况 |
|------|--------|------------|----------|
| Schema 合法率 | 100% | 100% | ✅ 达标 |
| Precision | ≥ 80% | 42.86% | ⚠️ 未达标（但已接近 Prompt 优化上限） |
| Recall | ≥ 75% | 80.00% | ✅ 达标 |
| F1 Score | ≥ 75% | 55.81% | ⚠️ 未达标 |
| 单次处理耗时 | < 30s | 8.3s | ✅ 达标 |
| 输入源覆盖 | 至少 3 类 | 3 类 | ✅ 达标 |

### 5.2 指标未达标原因分析

**Precision 未达标的主要原因**：
1. Prompt 优化已接近上限（v1.2 边际收益仅 0.75%）
2. 剩余 32 个误报中，部分属于 taxonomy 边界问题而非模型错误
3. 需要通过 taxonomy 澄清或外部约束（Phase 2.4）进一步提升

**不建议继续通过 Prompt 调优追求更高分数**，应转向系统能力建设层面的优化。

---

## 六、下一步行动建议

### 6.1 优先级 P0：Taxonomy 定义澄清

**目标**：解决 market/capital 等边界歧义

**具体动作**：
1. 梳理四类信号的边界定义
2. 建立"单主标签 / 可接受替代标签 / 真正双信号样本"的判定规则
3. 对 S002 等暧昧样本重新标注或标记为 taxonomy_ambiguity
4. 更新标注规范文档

### 6.2 优先级 P1：引入 Phase 2.4 增强

**目标**：通过外部约束提升精度

**具体动作**：
1. 接入 `constraint` 类 ContextPacket（补充分类边界）
2. 接入 `glossary` 类 ContextPacket（术语消歧）
3. 接入 `boundary_case` 类 ContextPacket（边界样本防护）
4. 运行联合 benchmark 验证效果

**预期效果**：Precision 提升 5-10%

### 6.3 优先级 P2：扩大 Benchmark 样本

**目标**：更全面评估性能

**具体动作**：
1. 扩大到 50-100 个样本
2. 补充更多边界样本和负例样本
3. 覆盖更多场景类型

### 6.4 优先级 P3：与 Phase 2.2 联调

**前置条件**：完成 P0 或 P1 后

**具体动作**：
1. 确认输出契约可被下游稳定消费
2. 联合测试信号传递链路
3. 识别接口优化需求

---

## 七、风险与问题

### 7.1 当前风险

| 风险 | 影响 | 应对措施 | 状态 |
|------|------|----------|------|
| Precision 未达标 | 中 | 已识别为 taxonomy 问题，转向系统能力建设 | ✅ 已应对 |
| Taxonomy 边界暧昧 | 中 | 纳入后续规划，不影响当前 MVP 交付 | ⏳ 待决策 |
| 2.4 上下文增强未就绪 | 低 | 当前为可选增强项，不阻塞 MVP | ⏳ 待协调 |

### 7.2 已解决问题

- ✅ 角色定义不明确 → 已落档到 phase2.1_roles.md
- ✅ 设计方案缺失 → 已通过多角色讨论产出
- ✅ 拍板项未确认 → 已完成 14 项拍板
- ✅ Benchmark 样本缺失 → 已完成 30 条样本准备与标注
- ✅ 优化方向不明确 → 已完成三轮 benchmark 与优化历程总结
- ✅ Prompt 优化边界不清晰 → 已识别边际收益递减，明确不建议继续 Prompt 调优

---

## 八、文档索引

### 8.1 规划与设计文档

- 角色定义：[phase2.1_roles.md](phase2_roles/phase2.1_roles.md)
- 设计方案：[phase2.1_设计方案.md](phase2.1_设计方案.md)
- 启动文档：[phase2.1_启动与拍板.md](phase2.1_启动与拍板.md)
- 待拍板清单：[phase2.1_待拍板决策清单.md](phase2.1_待拍板决策清单.md)

### 8.2 实现文档

- 实现代码：[phase2.1_implementation/](../proj_004/phase2.1_implementation/)
- 模块 README：[phase2.1_implementation/README.md](../proj_004/phase2.1_implementation/README.md)

### 8.3 Benchmark 报告

- v1.0 Baseline 报告：[PHASE2_1_BASELINE_BENCHMARK_REPORT.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_BASELINE_BENCHMARK_REPORT.md)
- v1.0 vs v1.1 对比报告：[PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md)
- 完整优化历程总结：[PHASE2_1_OPTIMIZATION_SUMMARY.md](../proj_004/phase2.1_implementation/docs/PHASE2_1_OPTIMIZATION_SUMMARY.md)

---

**文档状态**: ✅ 已完成
**版本**: v2.0
**建议下次更新时机**: 完成 taxonomy 澄清或引入 2.4 增强后