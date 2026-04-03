# Phase 2.2 Step A 优化设计方案

> **文档类型**：2.2 内部迭代设计方案
> **创建日期**：2026-04-01
> **状态**：✅ 主干已实现，✅ 理想化样本评测已收口（`auto / llm` 8/8），⏳ 指标基线沉淀与真实样本扩展中
> **范围**：纯 2.2 内部改造（step_a_cluster.py + judgment_engine.py），不改变任何对外接口
> **关联文档**：`phase2.2_signal_store_设计方案_v2.md`（本方案是其 Step A 部分的增强迭代）

---

## 一、背景与问题定义

### 1.1 现有 Step A 的核心缺陷

当前 Step A（`step_a_cluster.py`）的职责是：对批内信号做一次 LLM 调用，输出`signal_groups`（可直接组合的信号组）和孤立信号。

已识别三个核心问题：

**问题 1：硬分组污染 Step C 的判断前提**

Step A 的分组结果直接成为 Step C 的"硬隔离子集"：每个 group 独立送入 `judge()`，Step C 在被隔离的子集内工作，完全看不到组外的信号。

问题本质：Step A（haiku 级、上下文有限）做了本应由 Step C（sonnet 级、完整推理）做的决定，且一旦分错，Step C 无法纠正。

```python
# 当前行为：硬隔离
for group in step_a_result.signal_groups:
    result = self.judge(self._build_group_request(request, group))
    # Step C 只能看到 group 内的信号
```

**问题 2：跨域机会被系统性漏掉**

游戏行业典型机会的逻辑链往往是跨域的（监管信号 + 资本信号 + 市场信号），而当前 Step A 的 LLM 在信息不足时退化为语义相似分组，导致跨域互补信号被拆散，分别进入不同 group 或孤立信号流程。

估算：游戏行业情报场景中，约 60-70% 的可操作机会涉及跨域信号组合，当前方案存在系统性漏判风险。

**问题 3：小批次下 Step A 的分组反而降低精度**

信号数量 ≤ 15 条时，Step A 的分组假设对 Step C 的干扰大于帮助，全量送 Step C 成本可控且精度更高。

> **注：问题 3 已修复**（commit `7193ef6`，2026-04-01）：≤ 15 条信号跳过 Step A，直接全量送 Step C。

### 1.2 本方案的解决目标

1. 消除硬分组对 Step C 的判断前提污染（核心）
2. 保留跨域信号在同一 Step C 上下文中被发现关联的可能
3. 在 2.1 结构化字段（Step 3，中期规划）落地前，用 Prompt 工程改进 LLM 的逻辑互补判断质量

---

## 二、方案设计

### 2.1 核心思路：Step A 从"硬分组器"降级为"软标注器"

**改变 Step A 的输出结构**：从 `signal_groups`（硬性分组） → `logical_scenarios`（软性场景建议）

| 维度 | 当前（signal_groups） | 目标（logical_scenarios） |
|------|----------------------|--------------------------|
| Step A 输出什么 | "这几条信号是一组" | "这几条信号可能有逻辑关联，建议 Step C 重点验证" |
| Step C 接收什么 | 被隔离的信号子集，无法引用组外信号 | 全量信号 + 场景建议标注，可自由引用所有信号 |
| Step A 分错时 | Step C 被迫在错误前提下判断 | Step C 可忽略建议，独立发现真实关联 |
| 跨域机会 | 被拆散，无法在同一 Step C 中被发现 | 保留在全量信号池中，Step C 可自由发现 |

### 2.2 Step A 新输出结构

```python
class LogicalScenario:
    scenario_id: str              # "s1", "s2", ...
    primary_signal_ids: List[str] # 核心相关信号（2-4条）
    context_signal_ids: List[str] # 建议关注但非核心的信号（0-3条）
    reasoning: str                # 一句话：为什么认为这些信号有逻辑关联
    opportunity_direction: str    # 一句话：指向的可能机会方向

class StepAResult:
    logical_scenarios: List[LogicalScenario]  # 替换原 signal_groups
    isolated_signals: List[dict]              # 无法归入任何场景的孤立信号（含角色标注）
    role_annotations: Dict[str, dict]         # 不变
    fallback_used: bool                       # 不变
```

### 2.3 Step C 的变化：从"接收子集"到"接收全量 + 场景建议"

**中等批次（16-50 条）的 Step C 调用变化**：

```python
# 旧行为：每个 group 单独调用，硬隔离
for group in step_a_result.signal_groups:
    result = self.judge(self._build_group_request(request, group))

# 当前实现：全量信号只调用一次，logical_scenarios 作为软建议注入
scenario_request = self._build_scenario_request(
    original_request=request,
    all_signals=enriched_signals,
    logical_scenarios=step_a_result.logical_scenarios,
)
result = self.judge(scenario_request)
```

**当前拍板结论**：
- `Step C` **一次调用看到全量信号**
- `logical_scenarios` 只是 prompt 级建议，不是硬隔离子集
- 这样既保留了跨 scenario 发现机会的能力，也避免了把全量信号重复传给多个 `Step C` 调用带来的 token / 时延放大

**Step C 的 prompt 增加场景建议前缀**（由 `_build_scenario_request` 注入）：

```
[初步分析建议]
根据初步信号分析，以下信号可能在逻辑上相关：
- 核心信号：{primary_signal_ids} → 可能指向：{opportunity_direction}
- 建议关注：{context_signal_ids}
- 初步推断依据：{reasoning}

以上为参考建议，你可以基于所有信号独立判断，不必局限于上述组合。
如果发现其他更有价值的信号关联，优先以你的完整分析为准。

[全量信号]
...（所有信号）...
```

### 2.4 长尾兜底：高强度孤立信号强制扫描

对于强度 ≥ 7 且未被任何 scenario 覆盖的孤立信号，额外发起一次 Step C 兜底判断：

```python
# 兜底扫描：intensity ≥ 7 的孤立信号，即使没有 scenario 覆盖，也单独送 Step C
HIGH_INTENSITY_THRESHOLD = 7
for iso_signal in step_a_result.isolated_signals:
    intensity = iso_signal.get("intensity_score") or iso_signal.get("intensity", 0)
    if intensity >= HIGH_INTENSITY_THRESHOLD:
        # 单独送 Step C，让 Step C 判断是否单独成立或是否能与其他信号组合
        fallback_request = self._build_group_request(request, [iso_signal])
        result = self.judge(fallback_request)
        # ...
```

> 注：intensity < 7 的孤立信号仍走原有 Step B → Signal Store 路径，不变。

### 2.5 Prompt 增强：few-shot 逻辑互补案例

在 Step A 的 prompt 中增加 3-5 个游戏行业典型"逻辑互补组合"案例，引导 LLM 避免退化为语义相似分组：

```
## 逻辑互补案例参考（用于理解什么是"逻辑互补"而非"语义相似"）

【案例1 - 监管倒逼整合机会】
- 催化剂：EU DMA 罚款苹果（监管域）→ 平台分发成本上升
- 资源验证：某大厂宣布 3 亿并购资金（资本域）→ 资源充足
- 市场确认：独立开发者出走 App Store 数量创新高（市场域）→ 需求出现
- ✅ 这三条信号跨域但逻辑互补：外部压力 + 资源到位 + 市场需求

【案例2 - AI 降低独立游戏门槛】
- 技术信号：生成式 AI 代码工具成本骤降 80%（技术域）
- 市场信号：Steam 独立游戏月活创新高（市场域）
- ✅ 跨域互补：供给侧成本下降 + 需求侧市场验证

【反例 - 语义相似但非逻辑互补】
- 信号A：腾讯游戏新作发布（游戏域）
- 信号B：网易游戏新作发布（游戏域）
- ❌ 这两条语义相似（都是游戏新作）但不构成逻辑链，不应分为一组
```

---

## 三、不改变的内容

以下内容**不受本方案影响**：

| 模块 | 说明 |
|------|------|
| 小批次快速路径（≤ 15 条） | 已实现，跳过 Step A，直接全量送 Step C |
| Step B（孤立信号跨批次检索） | 完全不变，孤立信号仍走 L1-L4 漏斗 |
| Signal Store 读写接口 | 完全不变 |
| 2.1 → 2.2 输入接口 | 完全不变 |
| 2.2 → 2.3 输出接口 | 完全不变 |
| 规则 fallback 逻辑 | 保留，LLM 失败时所有信号视为孤立信号 |
| 第八章预计算组合索引 | 不受影响，触发条件（Store > 200 条）不变 |
| 第九章假设驱动（Top-down） | 不受影响，v2.0 规划不变 |

---

## 四、分级策略汇总

本方案实现后，完整的批次处理分级如下：

| 批次规模 | 策略 | 实现状态 |
|----------|------|----------|
| ≤ 15 条 | 跳过 Step A，全量直送 Step C | ✅ 已实现（commit `7193ef6`） |
| 16-50 条 | Step A 输出 logical_scenarios（软建议），Step C 接收全量信号 + 场景建议 | ✅ 主干已实现，理想化样本 `auto / llm` 已确认 8/8 通过 |
| 50+ 条 | 待定：logical_scenarios 基础上 + 假说驱动（依赖 Step 3 结构化字段） | 🔮 未来规划 |

---

## 五、实施计划

### 阶段 1：Step A 输出结构改造（step_a_cluster.py）

**任务**：
1. 新增 `LogicalScenario` 数据类
2. `_parse_step_a_response` 输出 `logical_scenarios` 替代 `signal_groups`
3. 更新 `StepAResult` 字段
4. 更新 prompt，加入 few-shot 逻辑互补案例

**验收**：`StepAResult.logical_scenarios` 有输出，每个 scenario 含 `reasoning` 和 `opportunity_direction`

---

### 阶段 2：judgment_engine.py 调用逻辑改造

**任务**：
1. 新增 `_build_scenario_request`（全量信号 + 场景建议注入）
2. 将 `for group in step_a_result.signal_groups` 改为 `for scenario in step_a_result.logical_scenarios`
3. 加入高强度孤立信号兜底扫描逻辑（intensity ≥ 7）

**验收**：
- Step C 每次调用能看到全量信号
- 场景建议以 prompt 前缀形式传入，Step C 可自由突破
- 高强度孤立信号不会因为无 scenario 而直接进入 Step B

---

### 阶段 3：评测与收口

**当前结论**：
1. 已使用 `run_step_a_idealized_eval.py` 完成理想化样本评测闭环：`rules` baseline 为 8/8 PASS，`auto` 模式运行于 `runtime_mode=llm`
2. `auto / llm` 首轮全量结果为 7/8，随后针对 4 个失败 case 完成 prompt 收口与解析兜底修复，并逐个复跑确认全部 PASS；当前 8 个理想化样本已确认 8/8 通过
3. 评测结论已同步回执行进展文档，当前设计文档也已更新到同一结论

**下一步任务**：
1. 沉淀 `logical_scenarios` 命中率、跨域互补召回率、语义相似误场景率、Step C 最终有效机会产出率
2. 补第二层真实样本评测集，与理想化样本分层管理，避免混用
3. 继续明确 `isolated_signals` 的实现语义说明
4. 再决定是否推进候选集收敛策略（如 Anchor-based Window）

---

## 六、待拍板事项

| 拍板项 | 建议 | 状态 |
|--------|------|------|
| 16-50 条批次时，Step C 是否对每个 scenario 独立调用，还是全量信号只调用一次（传入所有 scenarios 作为建议）？ | **已拍板：全量信号只调用一次**，所有 `logical_scenarios` 一并作为建议注入；理由：保留跨 scenario 关联发现能力，同时避免重复传输全量信号造成 token / 时延放大 | ✅ 已拍板 |
| 高强度孤立信号兜底阈值 intensity ≥ 7 是否合适？ | 当前实现已采用 `intensity >= 7`，待后续真实跑批结果再校准 | ✅ 暂定实施 |

---

## 七、执行进展

| 日期 | 阶段 | 关键进展 |
|------|------|----------|
| 2026-04-01 | 设计阶段 | 设计方案完成，参考 Kimi/Deepseek/Gemini 三方建议综合优化 |
| 2026-04-01 | 实现阶段 | 小批次快速路径（≤ 15 条）已实现，commit `7193ef6` |
| 2026-04-01 | 实现阶段 | Step A v2 主干已落地：`logical_scenarios` 替代 `signal_groups`，`Step C` 改为接收“全量信号 + 场景建议” |
| 2026-04-01 | 验证阶段 | 理想化评测样本文件已创建：`step_a_idealized_eval_samples_not_real_data.py`（明确标注非真实数据） |
| 2026-04-01 | 验证阶段 | 理想化评测 runner 已实现：`run_step_a_idealized_eval.py`，`rules` baseline 8/8 PASS |
| 2026-04-01 | 收口阶段 | 理想化样本 `auto / llm` 评测完成一轮收口：首轮全量结果 7/8，随后针对 4 个失败 case 完成 prompt 收口与解析兜底修复，并逐个复跑确认全部 PASS；当前 8 个理想化样本已确认 8/8 通过 |
| 2026-04-02 | 实现阶段 | `Relation Graph v1` 第一版骨架已落地：`Step A` 可产出 `RelationEdge / ScenarioCandidate / exploration_scenarios / emerging_links`，`Signal Store` 已支持 `EmergingLink / ScenarioMemory` 持久化与 `Step B` 跨批次唤醒 |

---

## 八、Relation Graph v1 设计回写与后续演进

> **定位**：本节已从“实现前设计稿”更新为“v1 骨架落地后的设计回写 + 后续演进说明”，用于解释当前实现边界与下一步增强方向。
> **当前状态**：✅ `Relation Graph v1` 第一版骨架已完成，当前实现已接入 `Step A → Signal Store → Step B` 主链路；后续重点转向 `logic_frame` 质量提升、阈值校准与真实样本验证。

### 8.1 模块边界（重新拍稳）

- **`2.2` 的职责**：高召回地发现、保留并组织可能长成机会的信号关系结构。
- **`2.3` 的职责**：判断机会成熟度、行动姿态、资源承诺与 Go/No-Go。
- **明确不做**：`2.2` 不给出“现在是否值得下注”的成熟度结论；这部分属于 `2.3`。

换句话说，`2.2` 只回答：
- 这些信号之间有没有值得保留的逻辑关系？
- 它们更像哪一种候选机会路径？
- 当前缺哪些拼图，后续应该等待什么信号补位？

### 8.2 核心原则

1. **从“猜关系”改成“算关系”**：优先使用 `logic_frame.what_changed / change_direction / affects`、角色标注、领域标签和时间顺序做结构化判断，而不是只读短文本猜语义相似。
2. **保留弱结构，不抢做成熟度判断**：允许“关系成立但仍不完整”的候选结构进入观察层，避免系统只保留成熟机会。
3. **先高召回，再做收敛**：Step A 先尽量保留真实的潜在关系，再通过候选集收敛控制 Step C 上下文成本。
4. **跨批次可生长**：当批次没长成机会的关系，不应直接消失，而应以可激活的中间态沉淀到 Signal Store。

### 8.3 内部数据结构（仅限 2.2 内部，不改变对外接口）

```python
class RelationEdge:
    edge_id: str
    left_signal_id: str
    right_signal_id: str
    edge_type: str          # reinforcing / complementary / constraint_release /
                            # demand_validation / resource_enablement / contradictory
    strength_band: str      # strong / emerging / weak
    gate_passed: bool
    bucket_scores: Dict[str, float]
    synergy_bonus: float
    concentration_penalty: float
    final_score: float
    reasoning: str

class ScenarioCandidate:
    candidate_id: str
    anchor_signal_ids: List[str]
    member_signal_ids: List[str]
    covered_roles: List[str]
    missing_slots: List[str]
    shared_affects: List[str]
    state: str              # seed / emerging / developing / ready_for_step_c
    promotion_score: float
    option_value_score: float
    reasoning_path: str
    activated_by: Optional[str]
    last_activated_at: str
```

**说明**：
- `RelationEdge` 和 `ScenarioCandidate` 是 `2.2` 内部对象，不改变 `2.1 → 2.2` 或 `2.2 → 2.3` 的正式接口。
- `logical_scenarios` 仍然是 Step A 对 Step C 的显式输出；`RelationEdge` / `ScenarioCandidate` 是其内部生成依据与后续沉淀对象。
- `promotion_score` 用于决定“现在是否值得送 Step C”，`option_value_score` 用于决定“即使现在不送 Step C，是否值得继续保留等待补槽”。两者不能混为一个总分。

### 8.4 边类型（v1 先收口为 6 类）

| 边类型 | 含义 | 示例 |
|--------|------|------|
| `reinforcing` | 同一变化被多源强化 | 两条信号都在强化“分发限制收紧” |
| `complementary` | 不同变化互补构成机会链 | 监管变化 + 资本到位 |
| `constraint_release` | 原有约束被削弱，新路径开始可行 | 平台封闭性下降 + 替代渠道松动 |
| `demand_validation` | 需求侧行为开始响应 | 开发者迁移、用户使用偏好变化 |
| `resource_enablement` | 资源/能力/供给条件开始具备 | 工具降本、资金流入、人才流动 |
| `contradictory` | 对机会链形成反证或冲突 | 利好信号出现，但执行门槛同步抬升 |

### 8.5 评分口径：评分是“分流机制”，不是“单点淘汰机制”

**设计原因**：如果只是把不同维度直接相加，会出现“少数维度极强、但整体结构失衡”的组合压过“多个维度都有迹象、形成合力”的组合；更严重的是，会把“结构还不完整、但很值得等待后续补槽”的早期高价值机会错误挡在外面。这不符合“尽量早、尽量快发现潜在机会”的目标。

#### A. 先拍板总原则

- `gate` 只拦**假关系**，不拦**早关系**。
- `concentration_penalty` 只负责**降级排序**，不直接判死。
- 分数主要用于**决定去向**，而不是直接做“高分留下 / 低分淘汰”。
- `2.2` 的目标不是选出“最成熟的机会”，而是把真实关系组织成“可验证的候选机会路径”。

#### B. 关系边的基础评分 `bucket_scores`

`RelationEdge` 仍保留统一的 `bucket_scores`：
- `relation_validity`：结构上是否真有逻辑连接
- `complementarity`：是否是不同拼图而非重复表述
- `object_convergence`：是否共同作用于同一对象群体
- `temporal_coherence`：是否符合真实世界演进顺序
- `independent_corroboration`：是否来自相互独立的观察面（作为加分项）

可保留一个内部 `final_score` 作为边强度的汇总参考，但它**不直接决定是否淘汰**，只为后续局部子图组装提供排序信号。

#### C. 宽松门槛 `gate_pass`

至少满足以下之一即可视为 `gate_passed=True`：
- `affects` 有明显收敛（共同作用于同一类对象）
- 角色明显互补（如 `catalyst + demand_evidence`）
- 时序关系合理（不像反因果）
- 不是纯语义相似（仅“都在说 AI / 融资 / 新游发布”不算）

**关键约束**：`gate_pass` 的设计目标是过滤明显无关系的噪声，而不是过滤“结构还不完整的萌芽关系”。

#### D. 从单一总分改为双分系统

对 `ScenarioCandidate`，不再只保留一个总分，而是拆成两个分流分数：

```python
promotion_score     # 决定是否值得现在送 Step C
option_value_score  # 决定是否值得继续保留在 Signal Store 等待补槽
```

- `promotion_score` 关注：当前结构是否已经足以形成“可验证假说”
- `option_value_score` 关注：即使当前不完整，是否仍具有明显的跨批次生长价值

#### E. 双阈值而不是一条线

建议冻结两条阈值：

```python
T_store   # 超过它就值得保留到 Scenario Memory / Signal Store
T_step_c  # 超过它才值得送 Step C 验证
```

推荐口径：
- `promotion_score >= T_step_c` → 送 Step C
- `promotion_score < T_step_c` 但 `option_value_score >= T_store` → 写入 `scenario_candidates` / `emerging_links`
- 两者都低，且 `gate_passed=False` → 视为噪声，不进入主候选

#### F. 协同加分与集中惩罚的真实职责

- `synergy_bonus`：只在多个关键桶同时过线时加分，鼓励“多维度共同成形”的候选结构
- `concentration_penalty`：当高分只集中在 1-2 个桶、其余关键桶明显偏弱时，降低其**优先级**，避免单点极强信号长期压制更均衡的组合

**重要补充**：`concentration_penalty` 只能把候选从“优先送 Step C”降级为“先留在 Store 观察”，不能直接把真实萌芽机会判成噪声。

#### G. 探索通道（本轮新增拍板）

为了避免系统只偏好“看起来更完整”的组合，每批保留少量**探索通道**名额：

- 主通道：高 `promotion_score`、当前更适合送 Step C 的候选
- 探索通道：`promotion_score` 未过主线，但 `option_value_score` 很高、且具有明显新颖性 / 补槽价值 / 跨域价值的候选

这样可以保证：
- 系统不会被“高分但保守”的组合完全占满
- 早期高期权价值的关系结构仍有机会上升到 Step C 验证

#### H. v1 的工程化分流建议（便于实现而非最终拍死阈值）

为避免在实现时又退回“一个总分决定生死”，建议直接冻结为**先分流、再排序**的执行顺序：

1. **先判真假关系**：`gate_passed=False` 才进入噪声池；`gate_passed=True` 一律继续看去向
2. **再判是否值得保留**：`option_value_score >= T_store` 即可进入 Store 生长层
3. **最后判是否值得当前送 Step C**：`promotion_score >= T_step_c` 才进入主通道
4. **探索通道兜底**：即使 `promotion_score < T_step_c`，但若 `option_value_score` 很高且具有明显新颖性，则仍保留少量上送名额

建议的工程初值（供实现期 A/B 校准，不视为永久阈值）：

```python
T_store = 0.45
T_step_c = 0.68
EXPLORATION_LANE_MAX = 2
EXPLORATION_LANE_RATIO = 0.2
```

推荐解释：
- `T_store` 故意设置得较低，保证“真关系但结构未闭环”的候选能活下来
- `T_step_c` 只要求达到“可验证假说”门槛，不要求达到“成熟下注”门槛
- `EXPLORATION_LANE_MAX` 用于防止探索候选过多，反过来淹没主通道
- `EXPLORATION_LANE_RATIO` 用于在批次规模变大时保持探索通道占比稳定

**探索通道的建议排序键**：

```python
exploration_priority = (
    option_value_score * 0.5
    + novelty_score * 0.2
    + gap_fill_value * 0.2
    + cross_domain_bonus * 0.1
)
```

其中：
- `novelty_score`：避免总是把“熟悉结构”送入探索通道
- `gap_fill_value`：优先让能补历史半成品关键缺口的候选被看到
- `cross_domain_bonus`：鼓励真正可能产生范式转移的跨域结构

**重要约束**：探索通道不是“低质量候选回收站”，而是“高期权价值候选的受控上送机制”。

### 8.6 Step A 新处理流（v1）

```text
输入：当批次全部信号（优先消费 2.1 的 logic_frame）
  ↓
A1. 生成候选边（批内两两轻量连边）
  ↓
A2. 宽 gate 过滤明显噪声边，保留 strong / emerging / weak 的内部排序
  ↓
A3. 围绕 strong / emerging edges 组装局部子图
  ↓
A4. 为子图计算 promotion_score / option_value_score
  ↓
A5. 按分流规则输出：
    - logical_scenarios：promotion_score ≥ T_step_c 的可验证假说
    - exploration_lane：promotion_score 未达主线，但 option_value_score 很高的探索候选
    - scenario_candidates / emerging_links：当前不完整但值得保留的关系痕迹
    - weak_noise：仅语义相似或无真实结构的噪声
  ↓
A6. logical_scenarios + exploration_lane → Step C
    scenario_candidates / emerging_links → Signal Store
```

### 8.7 `logical_scenarios` 的生成规则与 2.2 → 2.3 边界

`logical_scenarios` 不再理解为“分组结果”，而理解为“当前最值得让 Step C 验证的候选机会路径”。

建议保留以下约束：
- 每个 scenario 只保留 `2-5` 条核心信号，避免过度膨胀
- 优先保留跨域互补，不追求批内一次闭环
- 允许存在 `missing_slots`，只要结构上已经出现真实生长方向
- 同一信号可以出现在多个 scenario 中，只要扮演不同逻辑角色
- 进入 `logical_scenarios` 的标准是“已形成**可验证假说**”，不是“已经证明值得投入资源”

**与 `2.3` 的边界**：
- `RelationEdge` / `ScenarioCandidate` / `logical_scenarios` 都仍属于 `2.2` 的关系组织层
- 只有当 `Step C` 基于这些候选输出了正式 `OpportunityObject` 后，才进入 `2.3`
- `2.3` 接收的是“机会假说对象”，不是“关系边”或“半成品图”

### 8.8 与 Signal Store 的衔接

`Relation Graph v1` 不应只在当次批处理中临时存在。对后续真正有价值的，不是保存所有 pairwise 边，而是保存高价值关系痕迹：

- `emerging_links`：关系成立但尚不足以组成完整场景的边
- `scenario_candidates`：已经形成局部子图、但还未准备送 Step C 的候选场景
- `missing_slots`：当前还缺的关键拼图
- `anchor_traces`：高价值锚点曾经拉出的局部关系线索

这些对象的持久化设计放在 [phase2.2_signal_store_设计方案_v2.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2_plan\phase2.2_signal_store_设计方案_v2.md) 中统一承接。

### 8.9 可执行落地顺序（建议）

1. **前置条件**：`2.1 logic_frame` 覆盖率和字段稳定性达到可用门槛
2. **第一步**：在 `step_a_cluster.py` 内部增加 `RelationEdge` 生成与分桶逻辑
3. **第二步**：将 `logical_scenarios` 改为由局部子图组装得出，而不是直接依赖 LLM 分组
4. **第三步**：把 `emerging_links / missing_slots` 写入 Signal Store
5. **第四步**：在 `judgment_engine.py` 中保留当前“全量信号 + 场景建议”接口不变，仅替换场景来源

### 8.10 文件级工程拆解（落档，供实现前审阅）

#### A. `schemas.py`

新增或扩展以下内部数据结构：
- `RelationEdge`
- `EmergingLink`
- `ScenarioCandidate`
- `StepAResult` 的内部扩展字段：`exploration_lane` / `emerging_links` / `scenario_candidates`

建议约束：
- 对外接口仍保持 `logical_scenarios` 为主
- `exploration_lane` 只作为 `2.2` 内部编排对象，不直接暴露给 `2.3`

#### B. `step_a_cluster.py`

建议拆出以下函数：
- `_build_candidate_edges()`：批内两两连边
- `_score_edge_buckets()`：计算 `bucket_scores`
- `_classify_edge_strength()`：生成 `strong / emerging / weak`
- `_assemble_scenario_candidates()`：从局部子图组装候选场景
- `_compute_promotion_score()`：计算当前是否值得送 Step C
- `_compute_option_value_score()`：计算是否值得进入 Store 生长层
- `_select_exploration_lane()`：选出高期权价值的少量探索候选
- `_build_logical_scenarios_from_candidates()`：生成最终 `logical_scenarios`

#### C. `judgment_engine.py`

建议改造点：
- 保持当前“全量信号 + 场景建议”主接口不变
- 主通道接收 `logical_scenarios`
- 探索通道接收少量 `exploration_lane` 候选，与主通道一起送 Step C
- 仍保留高强度孤立信号兜底，防止未入图但强度很高的信号被系统漏掉

#### D. `signal_store.py`

建议新增：
- `save_emerging_links()`
- `save_scenario_candidates()`
- `find_candidates_by_missing_slots()`
- `find_matching_emerging_links()`
- `update_candidate_state()`

核心目标：让 `Relation Graph v1` 产出的中间态能被 Step B 真正消费，而不是只停留在批内内存对象。

#### E. `step_b_retrieval.py`

建议扩成三类检索入口：
- `retrieve_from_pending_signals()`
- `retrieve_from_emerging_links()`
- `retrieve_from_scenario_candidates()`

同时保留一个可选辅助入口：
- `retrieve_rag_support_for_candidate()`

职责边界：
- 前三者负责“关系召回”
- 最后一个只负责在候选关系已成形后补充支持/反向证据，不替代关系召回本身

### 8.11 实现顺序建议（避免一次性做重）

- **Phase 1**：冻结 schema、枚举、阈值与探索通道名额
- **Phase 2**：打通批内 `RelationEdge → ScenarioCandidate → logical_scenarios`
- **Phase 3**：接通 `emerging_links / scenario_candidates` 持久化
- **Phase 4**：实现 Step B 的历史关系唤醒
- **Phase 5**：最后补上候选形成后的 RAG 支撑检索

这样可以确保：
- 先把“关系结构发现”做对
- 再把“跨批次生长”做通
- 最后再把“知识支撑补强”做稳

---

## 九、后续增强路线图（供后续迭代对齐）

### 9.1 增强版（v1.1）：跨批次场景生长

**目标**：让机会不只在单批次里被发现，而能跨批次逐步长出来。

**重点能力**：
- `scenario_candidates` 持久化
- 新信号优先做“补槽”而不是“全局重算”
- 场景状态机：`seed → emerging → developing → ready_for_step_c`
- 差异化时效策略：监管 / 平台规则类信号寿命更长，市场热点类寿命更短

**预期收益**：支持 `3-4` 条跨批次信号稳定生长，并开始覆盖一部分 `5-6` 条长链机会。

### 9.2 增强版（v2.0）：Anchor-based Window + 关系索引联动

**目标**：在 50+ 条批次中降低 Step C 上下文压力，同时不切断跨域链条。

**重点能力**：
- 以高价值锚点（不是只看强度，还要看结构杠杆）拉取 `8-15` 条候选集
- `Anchor-based Window` 与 `RelationEdge / ScenarioCandidate` 联动，而不是退回语义近邻
- 预计算组合索引从“角色缺口匹配”升级到“关系痕迹 / 缺口补位”索引

**预期收益**：中大批次下显著降低上下文成本，同时保留跨场景发现能力。

### 9.3 高级版（v3.0）：长链弱信号发现

**目标**：让系统更稳定地发现“6 条以上、跨更长时间、单条都不够强”的长链机会结构。

**重点能力**：
- 两跳 / 多跳关系桥接
- dormant scenario 重新激活
- Bottom-up 关系图与 Top-down 假设驱动融合
- 更强的图索引与观察报告机制

**预期收益**：从“能保留早期萌芽结构”升级到“更稳定发现长周期弱信号组合机会”。

### 9.4 本轮拍板后的实现顺序建议

- **当前主线**：继续沉淀 `Step A v2` 真实样本指标，并推进 `2.1 logic_frame` 稳定
- **已完成骨架**：`Relation Graph v1`
- **随后增强**：补 `Scenario Memory` 的更完整生长与治理策略
- **规模触发后**：再实现 `Anchor-based Window` 和预计算关系索引

---

## 十、Relation Graph v1 Schema / 接口冻结稿（实现前对齐版）

> **目的**：把前文的设计原则与当前实现骨架对齐，冻结第一版字段和函数边界，降低后续实现阶段的反复摇摆。
> **对齐范围**：`schemas.py`、`step_a_cluster.py`、`judgment_engine.py`

### 10.1 与当前实现的对齐结论

基于当前实现代码，建议保持以下原则不变：

- **不修改 `2.2 → 2.3` 对外正式输出**：`OpportunityObject` / `OpportunityJudgmentResult` 保持不变
- **不让 `RelationEdge / ScenarioCandidate` 直接进入 `schemas.py` 的正式对外 schema**
- **先作为 `2.2` 内部对象存在**，由 `step_a_cluster.py` 生成、由 `judgment_engine.py` 消费
- `logical_scenarios` 仍然是 `Step A → Step C` 的显式桥接对象

换句话说：
- `schemas.py` 维持对下游稳定
- `step_a_cluster.py` 引入内部图结构
- `judgment_engine.py` 继续通过 `_scenario_hints` 接收软建议

### 10.2 内部对象冻结（v1）

建议在 `step_a_cluster.py` 所在层冻结以下内部对象：

```python
class RelationEdge:
    edge_id: str
    left_signal_id: str
    right_signal_id: str
    edge_type: Literal[
        "reinforcing",
        "complementary",
        "constraint_release",
        "demand_validation",
        "resource_enablement",
        "contradictory",
    ]
    strength_band: Literal["strong", "emerging", "weak"]
    gate_passed: bool
    bucket_scores: Dict[str, float]
    synergy_bonus: float
    concentration_penalty: float
    final_score: float
    reasoning: str
```

```python
class ScenarioCandidate:
    candidate_id: str
    anchor_signal_ids: List[str]
    member_signal_ids: List[str]
    covered_roles: List[str]
    missing_slots: List[str]
    shared_affects: List[str]
    state: Literal["seed", "emerging", "developing", "ready_for_step_c"]
    promotion_score: float
    option_value_score: float
    novelty_score: float
    gap_fill_value: float
    cross_domain_bonus: float
    reasoning_path: str
    activated_by: Optional[str]
    last_activated_at: Optional[str]
```

### 10.3 `LogicalScenario` 扩展冻结建议

当前 [step_a_cluster.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\step_a_cluster.py) 中的 `LogicalScenario` 已可工作。为兼容 `Relation Graph v1`，建议只做**最小扩展**：

```python
class LogicalScenario:
    scenario_id: str
    primary_signal_ids: List[str]
    context_signal_ids: List[str]
    reasoning: str
    opportunity_direction: str
    reasoning_path: Optional[str] = None
    missing_slots: Optional[List[str]] = None
    scenario_score: Optional[float] = None
    lane: Optional[Literal["primary", "exploration"]] = None
```

冻结原则：
- `reasoning_path`：给 Step C 一个更显式的“为什么把这些信号放在一起”
- `missing_slots`：让 Step C 知道当前仍缺什么，但**不要求它完成成熟度判断**
- `scenario_score`：仅用于内部排序与调试，不改变 Step C 的判断边界
- `lane`：用于标识该 scenario 来自主通道还是探索通道

### 10.4 `StepAResult` 扩展冻结建议

当前 `StepAResult` 已包含：
- `logical_scenarios`
- `isolated_signals`
- `role_annotations`
- `fallback_used`

建议扩为：

```python
class StepAResult:
    logical_scenarios: List[LogicalScenario]
    exploration_scenarios: List[LogicalScenario]
    isolated_signals: List[dict]
    role_annotations: Dict[str, dict]
    emerging_links: List[dict]
    scenario_candidates: List[dict]
    fallback_used: bool
```

字段职责：
- `logical_scenarios`：主通道，优先送 Step C
- `exploration_scenarios`：探索通道，少量上送 Step C
- `emerging_links`：关系成立但不足成场景，供持久化
- `scenario_candidates`：局部子图已成形但当前不送 Step C，供跨批次生长

### 10.5 `step_a_cluster.py` 函数边界冻结建议

建议后续实现时按以下函数边界拆分：

```python
def _build_candidate_edges(signals: List[dict]) -> List[RelationEdge]: ...
def _score_edge_buckets(left: dict, right: dict) -> Dict[str, float]: ...
def _infer_edge_type(left: dict, right: dict) -> str: ...
def _classify_edge_strength(edge: RelationEdge) -> str: ...
def _assemble_scenario_candidates(edges: List[RelationEdge], signals: List[dict]) -> List[ScenarioCandidate]: ...
def _compute_promotion_score(candidate: ScenarioCandidate) -> float: ...
def _compute_option_value_score(candidate: ScenarioCandidate) -> float: ...
def _select_primary_scenarios(candidates: List[ScenarioCandidate]) -> List[LogicalScenario]: ...
def _select_exploration_scenarios(candidates: List[ScenarioCandidate]) -> List[LogicalScenario]: ...
def _extract_emerging_links(edges: List[RelationEdge]) -> List[dict]: ...
```

约束建议：
- **LLM 仅保留在弱结构补充环节**，不要再让它重新承担“先硬分组再交给 Step C”的职责
- 如果 `logic_frame` 缺失，允许回退到当前 prompt 路径；但当 `logic_frame` 可用时，优先结构化计算

### 10.6 `judgment_engine.py` 接口冻结建议

当前 [judgment_engine.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\judgment_engine.py) 中的 `_build_scenario_request()` 已有 `_scenario_hints` 注入机制，这一点建议继续沿用。

建议冻结为以下行为：

- `Step C` **仍只做一次全量判断**
- `_scenario_hints` 同时接收：
  - `logical_scenarios`
  - `exploration_scenarios`
- prompt 中显式标识：
  - 哪些是主通道候选
  - 哪些是探索通道候选
- `judgment_engine.py` **不消费 `RelationEdge` 原始对象**，只消费整理后的 `LogicalScenario`

推荐注入格式：

```text
[主通道候选]
- ...

[探索通道候选]
- ...
```

这样可以保证：
- Step C 知道哪些候选是高确定性主线
- 也知道有少量高期权价值候选值得额外留意
- 但仍保持“对全量信号自主判断”的边界

### 10.7 本轮冻结结论

本轮不建议直接改动 `schemas.py` 的对外正式 schema，而建议冻结为：

- **内部新增**：`RelationEdge` / `ScenarioCandidate`
- **内部扩展**：`LogicalScenario` / `StepAResult`
- **接口复用**：`judgment_engine.py` 继续使用 `_scenario_hints`
- **对外保持稳定**：`OpportunityObject` / `OpportunityJudgmentResult` 不变

这会是 `Relation Graph v1` 最稳、且与当前工程最兼容的切入方式。

---

## 十一、Relation Graph v1 实现前任务清单

> **目标**：把当前冻结稿拆成可以直接开工的工程任务，优先保证最小可运行链路，而不是一步到位做完整高级版。

### 11.1 先解释一句：为什么说“Step A → Step C 的桥接仍然用 `LogicalScenario`”

这里的意思是：

- `RelationEdge`、`ScenarioCandidate`、`EmergingLink`、`ScenarioMemory` 这些对象，虽然在 `2.2` 内部很重要，但它们属于**底层关系组织层**
- `Step C` 不应该直接消费这些底层对象
- `Step C` 应该继续只接收一种已经整理好的“上层候选表达”——也就是 `LogicalScenario`

换成工程语言：

```text
Signal / Edge / Candidate / Memory
        ↓ 内部计算与筛选
   LogicalScenario
        ↓ _scenario_hints
      Step C
```

这样做的原因是：
- **对 Step C 最稳定**：它不需要理解图结构细节
- **对迭代最友好**：后面你可以继续改 `RelationEdge` 打分、`ScenarioCandidate` 组装方式，但只要 `LogicalScenario` 结构基本稳定，Step C 不用跟着频繁改
- **符合当前代码现实**：现在 `judgment_engine.py` 已经是通过 `_scenario_hints` 注入 `logical_scenarios` 给 Step C 的

所以这里的“桥接仍然用 `LogicalScenario`”，本质上就是：

- **底层对象留给 Step A / Step B / Signal Store 内部使用**
- **对 Step C 暴露的仍然是整理后的场景建议对象**

### 11.2 开发顺序总原则

建议按以下顺序推进：

1. **先补内部对象与数据流**
2. **再让 Step A 能产出主通道 / 探索通道 scenario**
3. **再把关系痕迹持久化到 Signal Store**
4. **最后再升级 Step B 做历史唤醒**

也就是说：
- **先做批内关系图**
- **再做跨批次生长**
- 不建议一开始就同时把 Step A、Step B、Store、RAG 全部重构

### 11.3 第一阶段：最小可运行版（建议优先完成）

#### A. [step_a_cluster.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\step_a_cluster.py)

- 新增内部对象：
  - `RelationEdge`
  - `ScenarioCandidate`
- 新增内部函数：
  - `_build_candidate_edges()`
  - `_score_edge_buckets()`
  - `_infer_edge_type()`
  - `_classify_edge_strength()`
  - `_assemble_scenario_candidates()`
  - `_select_primary_scenarios()`
  - `_select_exploration_scenarios()`
- 扩展 `LogicalScenario`：
  - `reasoning_path`
  - `missing_slots`
  - `scenario_score`
  - `lane`
- 扩展 `StepAResult`：
  - `exploration_scenarios`
  - `emerging_links`
  - `scenario_candidates`
- 调整 `run_step_a()` 主流程：
  - 优先结构化生成 edge
  - edge 组装 candidate
  - candidate 分流成 primary / exploration
  - fallback 仍保留

**完成标准**：
- 不改 Step C 的情况下，`run_step_a()` 已能输出：
  - `logical_scenarios`
  - `exploration_scenarios`
  - `emerging_links`
  - `scenario_candidates`

#### B. [judgment_engine.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\judgment_engine.py)

- 扩展 `_build_scenario_request()`
- 将 `exploration_scenarios` 一并注入 `_scenario_hints`
- prompt 中区分：
  - 主通道候选
  - 探索通道候选
- 保持 Step C 仍然只做一次全量判断

**完成标准**：
- Step C 能看到两类 scenario hint
- `RelationEdge` / `ScenarioCandidate` 不直接进入 Step C prompt

### 11.4 第二阶段：关系持久化版（建立跨批次基础）

#### C. [signal_store.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\signal_store.py)

- 新增持久化对象：
  - `EmergingLink`
  - `ScenarioMemory`
- 最小扩展 `SignalEntry`：
  - `last_activated_at`
  - `activation_count`
  - `linked_scenario_ids`
  - `linked_edge_ids`
- 为 `SignalStore` 增加接口：
  - `save_emerging_links()`
  - `save_scenario_memories()`
  - `query_matching_links()`
  - `query_matching_scenarios()`
  - `update_scenario_state()`
  - `mark_link_promoted()`

**完成标准**：
- Step A 产出的 `emerging_links` / `scenario_candidates` 能被持久化
- 新信号进入后，系统有地方记录“过去形成过哪些半成品关系”

### 11.5 第三阶段：历史关系唤醒版

#### D. [step_b_retrieval.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\step_b_retrieval.py)

- 保留现有 `L1 → L2 → L4` 主骨架
- 新增并行召回路径：
  - `_retrieve_pending_signal_candidates()`
  - `_retrieve_emerging_link_candidates()`
  - `_retrieve_scenario_memory_candidates()`
- 新增统一排序：
  - `_merge_and_rank_candidates()`
- 新增候选补强入口：
  - `_maybe_fetch_rag_support()`

**完成标准**：
- 新孤立信号不只会查历史 `pending signal`
- 还会查：
  - 已存在的关系痕迹
  - 已存在的半成品 scenario
- 命中后可重新上送 Step C

### 11.6 第四阶段：Schema 与观测补齐

#### E. [schemas.py](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.2_implementation\schemas.py)

这一阶段**不建议大改正式对外 schema**，只建议做两件事：

- 如有必要，给内部调试结果预留 `diagnostics` 扩展位
- 不把 `RelationEdge` / `ScenarioCandidate` / `EmergingLink` / `ScenarioMemory` 放进正式对外输出

**完成标准**：
- `2.2 → 2.3` 接口保持稳定
- 调试信息可逐步增强，但不污染正式输出

### 11.7 每个阶段的验收测试建议

#### 第一阶段验收
- 输入 10-20 条有 `logic_frame` 的信号
- 验证 Step A 是否能稳定输出：
  - 主通道 scenario
  - 探索通道 scenario
  - 若干 emerging link
- 验证 Step C 是否仍能正常产出机会结果

#### 第二阶段验收
- 连续跑两批不同时间的信号
- 验证第一批形成的 `emerging_links` 和 `scenario_candidates` 是否被写入 store
- 验证对象状态是否可查询、可更新

#### 第三阶段验收
- 先写入历史弱结构候选
- 再输入一条补位信号
- 验证 Step B 是否能成功唤醒旧 candidate / old link
- 验证唤醒后的候选是否被送入 Step C

### 11.8 推荐的实际开工顺序

如果按最小风险推进，我建议真实编码顺序就是：

1. `step_a_cluster.py`
2. `judgment_engine.py`
3. `signal_store.py`
4. `step_b_retrieval.py`
5. `schemas.py`（只做最小必要补位）

原因很简单：
- Step A 先把“批内关系图”跑起来
- Judgment Engine 先把“主通道 / 探索通道”接进去
- Store 再接住这些半成品
- Step B 最后再消费这些新对象做跨批次唤醒

这条路径最符合“先做轻、先跑通、再长出来”的实现原则。

### 11.9 本轮任务清单结论

本轮编码已完成以下三项目标：

- **目标1**：Step A 已能产出 `RelationEdge → ScenarioCandidate → LogicalScenario`
- **目标2**：Step C 已能同时接收主通道 + 探索通道 hint
- **目标3**：Signal Store 已能存 `EmergingLink / ScenarioMemory`

这意味着 `Relation Graph v1` 已经落地第一版骨架；下一步重点不再是“是否开工”，而是继续做 `logic_frame` 质量提升、阈值/排序校准，以及 `Step B` 跨批次唤醒效果验证。

---

*文档维护：`Relation Graph v1` 第一版骨架已完成并已同步本节执行进展；后续若出现字段边界或分流语义的重大变化，再创建新版本文档。*
