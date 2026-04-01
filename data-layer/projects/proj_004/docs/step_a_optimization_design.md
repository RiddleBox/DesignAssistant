# Phase 2.2 Step A 优化设计方案

> **文档类型**：2.2 内部迭代设计方案
> **创建日期**：2026-04-01
> **状态**：📝 设计完成，待实现
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
# 当前：每个 group 单独调用，硬隔离
for group in step_a_result.signal_groups:
    result = self.judge(self._build_group_request(request, group))

# 目标：全量信号 + 场景建议注入 prompt，Step C 自主判断
for scenario in step_a_result.logical_scenarios:
    scenario_request = self._build_scenario_request(
        request=request,
        all_signals=enriched_signals,   # 全量信号
        scenario=scenario,              # 软建议（仅供参考）
    )
    result = self.judge(scenario_request)
```

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
| 16-50 条 | Step A 输出 logical_scenarios（软建议），Step C 接收全量信号 + 场景建议 | 📋 本方案目标 |
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

### 阶段 3：单元测试更新

**任务**：
1. 更新 `unit_tests_phase22.py` 中涉及 `signal_groups` 的断言
2. 新增测试：Step A fallback 时 `logical_scenarios` 为空、孤立信号完整

---

## 六、待拍板事项

| 拍板项 | 建议 | 状态 |
|--------|------|------|
| 16-50 条批次时，Step C 是否对每个 scenario 独立调用，还是全量信号只调用一次（传入所有 scenarios 作为建议）？ | 建议每个 scenario 独立调用，结果去重合并；全量一次调用 context 太长，质量下降 | ⏳ 待拍板 |
| 高强度孤立信号兜底阈值 intensity ≥ 7 是否合适？ | 7 对应"较强信号"，可根据实际跑批结果调整 | ⏳ 待拍板 |

---

## 七、执行进展

| 日期 | 阶段 | 关键进展 |
|------|------|----------|
| 2026-04-01 | 设计阶段 | 设计方案完成，参考 Kimi/Deepseek/Gemini 三方建议综合优化 |
| 2026-04-01 | 实现阶段（预置）| 小批次快速路径（≤ 15 条）已实现，commit `7193ef6` |

---

*文档维护：实现完成后更新第七节执行进展，并在 phase2.2_执行进展.md 同步里程碑。设计有重大变更时创建新版本文档。*
