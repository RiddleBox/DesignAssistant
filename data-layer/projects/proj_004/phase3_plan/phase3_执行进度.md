# Phase 3 执行进度

> **文档类型**：执行进度跟踪文档
> **适用模块**：Phase 3 真实数据管道 + 螺旋质量迭代
> **状态**：执行中（Iteration 4 已完成主体，Iteration 5 待规划）
> **最后更新**：2026-03-29

---

## 一、Phase 3 定位

Phase 2 证明的是「链路能跑通」。Phase 3 要证明的是「链路能处理真实数据并支撑实际决策」。

**核心目标**：
> 以螺旋迭代方式，逐步将系统从「能运行的 MVP」推进到「处理真实信息、输出可信判断」的可演示状态。

**工程约定**：
- 不新建 3.1~3.5 实现文件夹，所有代码增量继续在 `phase2.1~2.5_implementation/` 中演进
- Phase 3 文档仅存放在 `phase3_plan/` 中
- 每轮迭代由 2.5 复盘驱动下一轮优先修复方向

---

## 二、螺旋迭代计划

### Iteration 1 — 真实数据管道跑通

**目标**：用真实样本跑通完整链路，识别首批质量问题

**输入**：`background/real_intel_samples/` 中的样本（当前 11 条信号样本 + 3 条噪音样本）

**主要工作**：
- [x] 建立 `incoming/` → `processed/` 文件夹约定（详见设计方案）
- [x] 编写批量运行脚本（从 JSON 读取 → batch 2.1 解码 → 聚合信号池 → 2.2 → 2.3 → 2.5 复盘）
- [x] 首轮运行，观察真实数据下的提取质量
- [x] 2.5 输出首轮复盘对象，识别主要问题

**首轮运行结果（2026-03-25）**：
- 输入样本：14 条（11 信号样本 + 3 噪音样本）
- 2.1 输出：10 条样本提取到信号，4 条样本为 0 信号，合计 18 个信号
- 2.2 输出：成功生成机会判断，priority_level = `deep_dive`
- 2.3 输出：成功生成行动姿态，decision_posture = `pilot`
- 2.5 输出：成功生成复盘对象，critical_findings = 1，phase3_priorities = 1

**首轮暴露问题**：
- `noise_001` 被误提取为 capital 信号，说明财报套话抑制仍需加强
- `real_001` 调用超时，说明代理/API 稳定性或超时策略需优化
- `real_010` 出现 `regulatory` 兼容性错误，说明 2.2/2.3 与 2.1 v1.3 新类型的联调仍有缺口

**验收标准**：
- 管道端到端跑通，无崩溃
- 2.5 能输出合法的 `SystemRetrospectiveObject`
- 噪音样本（noise_001~003）应触发 0 信号或低置信输出

**状态**：进行中（14 条干净样本基线已验证通过，待扩样进入下一轮）

---

### Iteration 2 — 信号质量提升

**目标**：根据 Iteration 1 的 2.5 复盘结果，定向修复质量问题

**主要工作**（由 Iteration 1 复盘驱动，以下为预期方向）：
- [x] 2.1 Prompt/few-shot 定向修复（基于真实数据暴露的误报/漏报）
- [x] 扩展到 37 条真实样本（含 7 条噪音，33 条信号样本）
- [x] 再跑完整链路 → 再 2.5 复盘
- [x] 扩样后暴露新噪音误报 → 二次修复（prompt v1.5）

**当前修复结果（2026-03-25）**：
- 已修复 `real_010` 的 `regulatory` 类型 KeyError（decoder summary 映射缺失）
- 已通过新增 few-shot 负例压制 `noise_001` 财报套话误报（复测为 0 信号）
- 已将代理调用超时从单值改为 `(30, 180)`，降低批跑时的偶发读超时风险
- 已完成一次修复后复跑验证：核心问题均未再次出现

**修复后复跑说明（2026-03-25）**：
- 本次复跑输入为 28 条，不是 14 条；原因是 `processed/` 中同时存在原始归档文件和上一轮重名追加副本，回灌到 `incoming/` 时被一并复制
- 该次复跑主要用于验证修复是否生效，不作为最终质量统计基线
- 复跑验证结果：`noise_001` 两份样本均为 0 信号，`real_010` 两份样本均成功提取 `regulatory`，`real_001` 未再出现超时

**干净基线复跑结果（2026-03-25）**：
- 已清理 `processed/` 与 `incoming/` 中的重复归档副本，恢复为 14 条标准样本集
- 输入样本：14 条（11 信号样本 + 3 噪音样本）
- 2.1 输出：11 条样本提取到信号，3 条样本为 0 信号，合计 21 个信号
- 噪音抑制：`noise_001~003` 全部为 0 信号
- `real_010` 成功提取 `regulatory` 信号，兼容性问题已确认修复
- 2.2 / 2.3 / 2.5 全链路运行成功

**状态**：⚠️ 修复已实施，但验证不充分

**验证缺口**：
- 噪音抑制验证仅覆盖 noise_001~003 共 3 条样本，样本量严重不足，无法确认是否真正达到噪音抑制状态
- few-shot 修复在"见过"的样本上通过，未在外部未见过的噪音样本上验证泛化能力
- 结论：修复生效是局部的，噪音抑制的稳定性结论需要扩充样本后重新验证

---

### Iteration 3 — 规模化 + RAG 接入

**目标**：obsidian 知识库内容入库 2.4 RAG，验证 51 条量级全链路，架构改造 RAG 为按需检索

**主要工作**：
- [x] obsidian 内容格式化 → 2.4 RAG 索引建立（40 条文档，FAISS IndexFlatIP，dim=768）
- [x] 2.4 → 2.2 联调架构改造：RAG 由 2.2 在形成判断主题后按需发起查询（非预取）
- [x] 51 条量级批量运行验证（RAG 正常检索，全链路无崩溃）
- [x] 2.2 LLM 判断模式上线：补写 `_call_llm` + `_llm_judge`，修复 `'JudgmentEngine' object has no attribute '_llm_judge'` bug（2026-03-27）
- [x] record 模式验证 LLM 路径：priority_level=research，supporting/counter 各 6 条，$0.1225/次（2026-03-27）
- [x] phase3_执行进度.md 更新完整 Iteration 3 状态

**架构决策记录（2026-03-26）**：
- RAG 查询由 2.2 在 Step2（论点形成）后发起，而非在 2.2 执行前预取
- 查询内容为 2.2 已识别的 theme + thesis，语义精度高于原始信号文本
- 2.4 文档类别（game_design/market_trend/tech_innovation）与 2.1 信号类型（market/technical/capital/team/regulatory）维度不同，不建议强行对齐；2.2 应使用纯语义查询跨类别检索

**验收结果（2026-03-27）**：
- 输入样本：3 条（2 信号样本 + 1 噪音样本，record 模式验证）
- 2.1 输出：3 条信号，噪音正确过滤 0 信号
- 2.2 LLM 路径：priority_level=research，supporting 6 条，counter 6 条，$0.1225
- 2.4 RAG：命中 3 条相关文档，按需查询架构稳定
- 全链路：无崩溃，无 fallback 错误

**状态**：⚠️ 主体实现，验证不足

**验证缺口**：
- LLM 路径（2.2/2.3）稳定性依赖 api123.icu 状态，当前随机出现 fallback，同一样本两次跑结果不同
- 51 条量级的验证是在 record/replay 模式下完成的，不是全部走真实 LLM 路径
- RAG 命中质量未建立基线（命中条数 ≠ 命中质量）

---

### Iteration 4 — 2.1 精度提升 + 链路质量全面升级

**目标**：提升 2.1 信号提取 Precision，LLM 判断路径全面接入，2.5 LLM 深层归因能力建立

**状态**：✅ 已完成（2026-03-27 ~ 2026-03-29）

**说明**：原 Iter 4 规划（2026-03-26）只预期"2.1 v1.6 + Precision 测量 + replay 缓存"，实际推进过程中各模块质量问题集中爆发并完成修复，范围远超原计划。replay 缓存暂缓——当前真实 API 链路稳定，replay 的迫切性下降，后续视需要补做。

**主要工作**：

**2.1 情报解码**：
- [x] prompt 升级至 v1.5/v1.6：market 类误报抑制、5类信号判断框架统一（technical/team/capital 补充显式规则）
- [x] Precision 测量体系建立（25 条真实样本基准集）
- [x] 验证结果：Precision=95.2% / Recall=87.0% / F1=90.9%，远超原目标 ≥60%
- [x] 两阶段筛选架构：source_type 规则预筛（report 纯趋势类 0ms 跳过）

**2.2 机会判断**：
- [x] 消费语义重构：输入从单条改为 `decoded_intelligences: List[DecodedIntelligence]`，2.2 自主决定信号组合
- [x] Prompt-first v2（`_llm_judge_v2`）：完整暴露打分 + source_type，LLM 自主组合逻辑链
- [x] `uncertainty_map` 格式约定：`[类型] 描述：影响说明`（5 种类型枚举）
- [x] 规则引擎 fallback 修复：`intensity` 字段名 bug（→ `intensity_score`），avg_intensity 始终为 0 导致 priority 分级偏低
- [x] 验证案例集 v2 重写（7 个游戏行业主题案例，多条 DI 输入）

**2.3 行动设计**：
- [x] 轻量版多 Agent 辩论：鹰派 + 鸽派 + 仲裁者三轮调用
- [x] 结构性缺口修复：`PhaseResources` 加 `resource_rationale`，`TopRisk` 加 `blocks_stage`，新增 `DebateSummary` dataclass
- [x] `debate_summary` 字段透传到报告层
- [x] `why_now` / `next_validation_questions` 字段接入报告

**2.4 知识库 RAG**：
- [x] ContextPacket v1.0 协议冻结（content_type 枚举 6 种，ContextRequest / ContextResponse 字段定义）
- [x] 四层文档结构确立（industry / category / content_type / tags 正交）
- [x] MetadataFilter 重构（三维弹性过滤：industry / category / min_trust_level，替代旧 category_filter）
- [x] 向量索引重建（vector_meta 含 industry/content_type/category 字段，384 维 MiniLM-L6-v2）
- [x] 62 条文档全部标注 industry: gaming
- [x] 2.2 真实接入验证：8 条证据包命中，4 种 content_type 分桶全部成功

**2.5 整合复盘**：
- [x] 真实链路端到端打通：upstream_outputs 来自真实 2.1→2.2→2.3→2.4 运行
- [x] 新增 `llm_attributor.py`（主归因路径），`ProblemAttributor` 降为规则 fallback
- [x] LLM 归因验证：findings=5，全部为准确的语义层发现（RAG 失效 / counter_evidence 无关 / why_now 空 / 信号丢弃 / exit_conditions=0）
- [x] 关键工程修复 4 项：流式请求绕过中转截断、JSON 兼容前缀解析、prompt 体积压缩、信号字段名对齐
- [x] 报告结构重构（输出检查 / 关键发现 / 根因归因 / Phase3优先项四块分离）
- [x] `processing_time_ms` 接入真实耗时，`errors` 字段自动收集 2.2/2.3 fallback 信息

**Iter 4 复盘结论**：
- 链路质量全面提升，LLM 判断路径已在 2.2/2.3/2.5 三个模块稳定运行
- 2.5 LLM 归因能力已从"规则发现表面问题"升级为"语义层发现系统性问题"
- 当前主要瓶颈：API 中转（api123.icu）偶发截断/限流，2.2/2.3 LLM 路径随机 fallback 到规则引擎

**状态**：⚠️ 主体实现，质量指标存在水分

**验证缺口**：
- **Precision 95.2% 有水分**：测试集与 few-shot 训练集高度重叠（测的是"见过"的样本），不代表真实泛化能力
- **噪音抑制结论继承 Iter 2 的不充分验证**：噪音样本量仍然偏少
- 上述两个质量数字在 Iter 5 需要用**外部未见过的样本**重测才能作为可信基准
- replay 缓存机制未实现（暂缓，见 Iter 4 遗留说明）

---

### Iteration 5 — 建立可信质量基准 + 2.5 驱动修复闭环

**目标**：用外部未见样本重建质量数字，让 2.5 复盘基于可信数据驱动下一步修复方向

**状态**：待开始

**核心前提（Iter 4 复盘识别）**：

当前所有质量数字都有不同程度的水分：

| 指标 | 当前值 | 问题 |
|------|--------|------|
| 2.1 Precision | 95.2% | 测试集与 few-shot 样本高度重叠，不代表泛化能力 |
| 噪音抑制率 | noise_001~003 全抑制 | 仅 3 条噪音样本，样本量严重不足 |
| LLM 路径命中率 | 未测量 | api123.icu 随机 fallback，无法统计 |
| RAG 命中质量 | 未测量 | 命中条数有统计，但命中是否有效未评估 |

**规划方向**（等确认优先级后细化）：

1. **扩充外部测试样本**（最优先）
   - 补充 20+ 条 few-shot 未覆盖的真实外部样本（信号类 + 噪音类各约一半）
   - 噪音样本需覆盖多种噪音形态：财报套话、纯公告、非游戏行业、低信息量内容等
   - 样本来源：openclaw 采集的新批次，或手工构造典型边界案例

2. **重跑质量基准**
   - 在新样本集上重测 Precision / Recall / 噪音抑制率
   - 建立可信的质量基线（"脱离 few-shot 的真实精度"）

3. **换正式 API**
   - 根治 2.2/2.3 随机 fallback 根因
   - 换完后重跑同批样本，得到 LLM 路径真实命中率

4. **2.5 跨轮次归因**
   - 积累 10+ 次真实链路运行记录
   - 让 2.5 对比多次结果，识别持续性系统性问题 vs 偶发问题

5. **background 文档重分类评估**
   - 62 条文档中 32 条 content_type=background，2.2 不请求此类型
   - RAG 实际有效文档只有 30/62，评估重分类后能否提升命中质量

---

## 二.五、模块待完善计划

> 以下为各模块识别出的待完善项，按优先级排序，将在后续 Iteration 中逐步推进。

### 2.1 情报解码模块

**短期（下一 Iteration）**：
- [ ] 加强 market 类误报抑制：销量/收入数字类事件，只在明确超出同类历史记录、或原文指出预期被颠覆时提取为 market 信号
- [ ] 新增范式边界 few-shot：区分「销量里程碑（背景信息）」vs「范式突破验证（市场信号）」
- [ ] prompt 升级至 v1.6，Precision 目标 ≥ 60%

**中期（后续 Iteration）**：
- [ ] 与 2.4 知识库联调，用历史基线上下文辅助判断信号强度
- [ ] benchmark 升级：引入信号价值密度、噪音抑制率指标（参考 PHASE2_1_BENCHMARK_UPGRADE_DRAFT.md）

### 2.2 机会判断模块

**短期**：
- [x] RAG 按需查询架构（2026-03-26 完成）
- [x] LLM 判断模式：`_call_llm` + `_llm_judge` 实现并验证（2026-03-27 完成）
- [x] 修复 LLM 响应中文引号导致 JSON 解析失败 bug（2026-03-27）

**中期**：
- [ ] 实现多信号范式合成能力：多个中低强度信号 + 2.4 知识 → 识别范式突破机会
- [ ] 多 Agent 辩论作为可选优化手段（参考 PHASE2_2_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md）

### 2.3 行动设计模块

**短期**：
- [x] LLM 判断模式：`_call_llm` + `_llm_design` 实现并验证，规则引擎 fallback（2026-03-27 完成）
- [x] 修复 llm_client.py 路径深度错误（2026-03-27）
- [x] 轻量版多 Agent 辩论：鹰派 + 鸽派 + 仲裁者三轮调用，避免单次 LLM 确认偏误（2026-03-27 完成）

**中期**：
- [ ] Go/No-Go 门槛结构化（当前行动姿态判断为规则驱动，缺乏退出条件设计）
- [ ] 分阶段承诺设计（watch/pilot/build/pass 各阶段的资源承诺结构）
- [ ] 多 Agent 辩论完整版：多轮对话迭代，Agent 之间有反驳回合，模拟真实决策辩论（轻量版完成后推进）

### 2.4 知识库模块

**中期**：
- [ ] 扩充行业范式假设类文档（历史基线、市场预期、品类天花板），供 2.2 范式合成使用
- [ ] 知识类别扩展（加入 business_model/studio_management）
- [ ] 文档数量从 40 条扩充至 100 条

---

## 三、样本库状态

| 位置 | 用途 | 当前数量 |
|------|------|----------|
| `background/real_intel_samples/incoming/` | openclaw 定期投放新样本 | 51 条（测试运行时回填） |
| `background/real_intel_samples/processed/` | 已处理样本归档 | 51 条 |
| `background/real_intel_samples/` (根目录) | 当前手动样本 | 51 条（含噪音样本）|

**样本覆盖类型**：market × 多 / capital × 多 / technical × 多 / team × 多 / regulatory × 多 / 噪音 × 多（共 51 条）

---

## 四、风险与问题跟踪

### 4.1 当前风险

| 风险项 | 严重度 | 状态 | 应对措施 |
|--------|--------|------|----------|
| openclaw 采集格式与 IntelligenceDecodeRequest 不完全一致 | 低 | 已确认格式兼容，零转换成本 | 持续监控新批次格式 |
| 真实数据噪音比例未知 | 中 | 已完成 14 条干净样本基线验证：3 条噪音全部被压制 | 下一步扩展到 20-30 条样本，观察是否仍稳定 |
| API 调用成本（100条规模） | 低 | 当前 14 条基线已稳定跑通，未再出现超时 | 扩样时继续观察代理稳定性与耗时曲线 |

### 4.2 已解决问题

| 问题 | 解决方案 | 解决时间 |
|------|----------|----------|
| Phase 3 是否需要重走 Phase 2 完整治理流程 | 不需要：目标对齐→轻量设计决策→实现→验证，不需要待拍板清单/团队重组/角色面具 | 2026-03-24 |
| 是否新建 3.1~3.5 实现文件夹 | 不建：代码增量继续在 phase2.x_implementation/ 中演进 | 2026-03-24 |
| 是否在 2.1 前人工筛选噪音 | 不筛：全量输入是 2.1 的正确姿势，噪音抑制是其核心职责 | 2026-03-24 |
| 样本管道「已处理」状态如何持久化 | incoming/processed 文件夹约定 + 2.5 复盘结果记录信号提取结论 | 2026-03-24 |
| `regulatory` 新信号类型导致 decoder summary KeyError | 在 2.1 `decoder.py` 中补齐 `regulatory` 类型映射，并用 `dict.get` 避免未来新增类型再次触发 KeyError | 2026-03-25 |
| 标准财报套话被误提取为 capital 信号 | 在 2.1 `prompt_templates.py` 中新增 few-shot 负例（季报套话 → 0 信号）并升级到 v1.4 | 2026-03-25 |

---

## 五、参考文档

- [phase3_设计方案.md](phase3_设计方案.md)
- [phase2.5_执行进度.md](../phase2_plan/phase2.5_执行进度.md)（Phase 2 收口状态）
- [PHASE2_1_MVP_SCOPE_AND_ITERATION_ALIGNMENT.md](../phase2.1_implementation/docs/PHASE2_1_MVP_SCOPE_AND_ITERATION_ALIGNMENT.md)

---

**文档状态**：执行中
**版本**：v0.3
**最后更新**：2026-03-26
