# Phase 2.2 机会判断模块设计方案

> **文档类型**：多角色讨论收敛产物
> **适用模块**：Phase 2.2 机会判断模块
> **产出方式**：基于 phase2_roles/phase2.2_roles.md 的多角色视角讨论
> **状态**：设计草案，待用户拍板
> **最后更新**：2026-03-16

---

## 一、设计目标与非目标

### 1.1 设计目标

Phase 2.2 的核心目标是建立**机会判断层 / 机会升级层**，具体包括：

1. **建立结构化机会对象**：把 2.1 的离散信号升级为可解释、可比较、可质疑的机会对象
2. **完成最小判断闭环**：机会组装 → 判断 → 分级 → 升级建议
3. **支撑 2.3 稳定消费**：提供稳定的输出契约，让 2.3 可以直接基于机会对象进行行动设计
4. **保持判断可解释性**：论点清晰、证据充分、假设显式、不确定性标注
5. **实现轻量验证**：通过 3-8 组真实案例验证判断闭环是否成立

### 1.2 非目标（明确不做）

为了保持 2.2 的边界清晰，以下内容**明确不在当前 MVP 范围内**：

1. ❌ **不做长篇报告生成器**：主产物是结构化对象，不是长篇分析报告
2. ❌ **不做复杂评分系统优先**：当前聚焦判断闭环，复杂权重评分作为后续增强
3. ❌ **不回卷重做信号识别**：信号识别是 2.1 的职责，2.2 只消费结构化信号
4. ❌ **不越级做行动方案**：行动设计是 2.3 的职责，2.2 只给出升级建议方向
5. ❌ **不在 MVP 前把多 Agent 作为硬前提**：多 Agent 作为 P1/P2 增强项

### 1.3 成功标准

Phase 2.2 MVP 成功的标准是：

- **功能层**：能稳定接收 2.1 输出，返回合法的 OpportunityObject
- **质量层**：机会对象具备可解释性、可追溯性和最小判断力
- **协作层**：2.3 可以基于 2.2 输出直接进入行动设计
- **验证层**：至少 1-2 个完整案例演示闭环成立

---

## 二、上下游边界

### 2.1 与 Phase 2.1 的关系

**输入依赖**：
- 2.2 直接消费 2.1 的 `DecodedIntelligence` 对象
- 2.2 依赖 2.1 提供的结构化信号列表（`signals`）
- 2.2 不回卷重做信号识别与准入判断

**边界约定**：
- ✅ 2.1 负责：把外部事实转化为结构化信号
- ✅ 2.2 负责：把结构化信号升级为机会对象
- ❌ 2.2 不负责：重新判断"这是不是一个信号"

**最小输入字段**（来自 2.1）：
```typescript
{
  decoded_intelligence: {
    intelligence_id: string,
    signals: Signal[],
    // ... 其他 2.1 输出字段
  }
}
```

### 2.2 与 Phase 2.4 的关系

**输入依赖**：
- 2.4 提供轻量证据包（context packet）作为**可选增强输入**
- 2.2 不强依赖 2.4，避免阻塞启动
- 2.4 的内容可补充到 supporting_evidence 或 counter_evidence

**边界约定**：
- ✅ 2.4 负责：提供方法论框架、相似案例、反例提醒、术语边界
- ✅ 2.2 负责：基于证据形成判断，不外包判断权给 2.4
- ❌ 2.2 不负责：替代 2.4 去做深度知识检索

**接入方式**：
```typescript
{
  context_packet?: {
    similar_cases?: string[],
    counter_examples?: string[],
    methodology_hints?: string[],
    // ... 其他 2.4 提供的增强信息
  }
}
```

### 2.3 与 Phase 2.3 的关系

**输出交付**：
- 2.2 输出 `OpportunityObject` 作为 2.3 的输入
- 2.2 提供 `priority_level` 用于分流
- 2.2 提供 `next_validation_questions` 指导 2.3 的行动设计

**边界约定**：
- ✅ 2.2 负责：输出机会对象、分级、升级建议方向
- ✅ 2.3 负责：基于机会对象设计具体行动方案、资源路径
- ❌ 2.2 不负责：直接给出"应该做什么、投入什么资源"

**最小交接字段**（给 2.3）：
```typescript
{
  opportunity_id: string,
  opportunity_thesis: string,
  priority_level: "watch" | "research" | "deep_dive" | "escalate",
  next_validation_questions: string[],
  related_signals: Signal[],
  // ... 其他字段
}
```

---

## 三、核心对象设计

### 3.1 OpportunityObject 最小字段集

基于机会判断负责人与结构化契约负责人的讨论，`OpportunityObject` 的最小字段集定义如下：

```typescript
interface OpportunityObject {
  // 基础标识
  opportunity_id: string;              // 机会对象唯一标识
  opportunity_title: string;           // 机会标题（简短描述）
  opportunity_thesis: string;          // 机会论点（核心判断）

  // 信号关联
  related_signals: Signal[];           // 关联的信号列表（来自 2.1）

  // 证据组织
  supporting_evidence: string[];       // 支持证据列表
  counter_evidence: string[];          // 反对证据列表
  key_assumptions: string[];           // 关键假设列表
  uncertainty_map: string[];           // 不确定性列表

  // 判断结果
  priority_level: "watch" | "research" | "deep_dive" | "escalate";

  // 升级建议
  next_validation_questions: string[]; // 下一步验证问题

  // 元数据
  judgment_version: string;            // 判断版本
  processing_time_ms: number;          // 处理耗时
}
```

### 3.2 输入契约：OpportunityJudgmentRequest

```typescript
interface OpportunityJudgmentRequest {
  // 必填：来自 2.1 的输入
  decoded_intelligence: DecodedIntelligence;

  // 可选：来自 2.4 的增强输入
  context_packet?: {
    similar_cases?: string[];
    counter_examples?: string[];
    methodology_hints?: string[];
    domain_constraints?: string[];
  };

  // 可选：判断配置
  judgment_config?: {
    min_confidence_threshold?: number;
    enable_counter_evidence_check?: boolean;
    max_processing_time_ms?: number;
  };
}
```

### 3.3 输出契约：OpportunityJudgmentResult

```typescript
interface OpportunityJudgmentResult {
  // 核心输出
  opportunity: OpportunityObject;

  // 判断状态
  status: "success" | "insufficient_evidence" | "error";

  // 诊断信息
  diagnostics?: {
    signal_count: number;
    evidence_completeness: number;
    boundary_warnings: string[];
  };

  // 错误信息（如果有）
  error?: {
    code: string;
    message: string;
  };
}
```

### 3.4 契约设计原则

**最小化原则**：
- 只包含 2.3 必需的字段，避免过度设计
- 扩展字段通过 `metadata` 预留，不污染核心契约

**可追溯原则**：
- `related_signals` 保持与 2.1 的追溯链路
- `judgment_version` 支持判断逻辑的版本管理

**可解释原则**：
- `opportunity_thesis` 必须是人类可读的论点
- `supporting_evidence` 和 `counter_evidence` 必须并列存在
- `key_assumptions` 和 `uncertainty_map` 显式化假设与不确定性

**边界清晰原则**：
- `suggested_actions` 只给方向，不给具体方案（避免越界到 2.3）
- `next_validation_questions` 指导 2.3 的行动设计，不替代 2.3

---

## 四、主流程设计

### 4.1 判断流程骨架

```
输入：OpportunityJudgmentRequest
  ↓
步骤 1：信号聚类与主题识别
  - 分析 related_signals 的类型分布
  - 识别信号之间的关联关系
  - 形成机会主题假设
  ↓
步骤 2：机会论点形成
  - 基于信号聚类形成核心论点
  - 检查论点是否可解释、可质疑
  - 生成 opportunity_thesis
  ↓
步骤 3：证据组织
  - 从 2.1 信号中提取支持证据
  - 从 2.4 context_packet 中补充证据
  - 识别反对证据与限制条件
  - 显式化关键假设
  ↓
步骤 4：不确定性评估
  - 识别证据不足的维度
  - 标注不确定性等级
  - 形成 uncertainty_map
  ↓
步骤 5：分级判断
  - 基于证据完整度、信号强度、不确定性进行分级
  - 输出 priority_level (watch/research/deep_dive/escalate)
  - 计算 confidence_score
  ↓
步骤 6：升级建议
  - 生成 next_validation_questions
  - 提出 suggested_actions 方向
  ↓
输出：OpportunityJudgmentResult
```

### 4.2 分级口径

| 分级 | 触发条件 | 典型特征 | 建议方向 |
|------|----------|----------|----------|
| **watch** | 信号弱、证据不足、不确定性高 | 单一信号、缺少交叉验证 | 持续观察，等待更多信号 |
| **research** | 信号中等、有初步证据、不确定性中等 | 2-3 个相关信号、有部分支持证据 | 启动轻量研究，补充证据 |
| **deep_dive** | 信号强、证据较充分、不确定性可控 | 多信号聚类、支持/反对证据完整 | 深度分析，形成完整判断 |
| **escalate** | 信号极强、证据充分、时效性紧迫 | 多维度信号、高置信度、需快速决策 | 升级到决策层，准备行动 |

### 4.3 边界检查点

在流程中设置以下边界检查点：

**检查点 1：信号来源检查**
- ✅ 确认信号来自 2.1 的 DecodedIntelligence
- ❌ 拒绝未经 2.1 处理的原始输入

**检查点 2：判断层级检查**
- ✅ 确认当前是机会级判断，不是信号级准入判断
- ❌ 避免回卷重做 2.1 的信号识别工作

**检查点 3：输出边界检查**
- ✅ 确认输出是机会对象，不是行动方案
- ❌ 避免越级给出具体资源投入建议

**检查点 4：证据完整性检查**
- ✅ 确认支持证据与反对证据并列存在
- ❌ 避免只有支持证据的过度自信判断

### 4.4 错误处理策略

| 错误类型 | 处理方式 | 返回状态 |
|----------|----------|----------|
| **信号不足** | 返回 insufficient_evidence，建议等待更多信号 | status: "insufficient_evidence" |
| **证据冲突** | 降低 confidence_score，增加 uncertainty_map 条目 | status: "success" (但置信度低) |
| **超时** | 返回部分结果，标注 diagnostics.boundary_warnings | status: "success" (带警告) |
| **输入格式错误** | 返回 error，提供具体错误信息 | status: "error" |

---

## 五、证据与不确定性组织

### 5.1 证据组织原则

**并列原则**：
- 支持证据（supporting_evidence）与反对证据（counter_evidence）必须并列存在
- 不允许只有支持证据而没有反对证据的判断对象
- 如果确实没有反对证据，必须显式说明"未发现明显反对证据"

**可追溯原则**：
- 每条证据必须能追溯到具体来源（2.1 信号或 2.4 证据包）
- 证据格式：`"[来源] 具体证据内容"`
- 示例：`"[Signal-tech-001] 公司发布新技术专利申请"`

**分层原则**：
- 一级证据：直接支持/反对机会论点的核心证据
- 二级证据：间接相关的背景信息
- 当前 MVP 只处理一级证据，二级证据放入 metadata

### 5.2 假设显式化

**关键假设（key_assumptions）组织方式**：

每个假设应包含：
1. 假设内容
2. 假设的重要性等级（critical / important / minor）
3. 假设的可验证性

示例：
```typescript
key_assumptions: [
  "假设：该技术在未来 6 个月内能完成商业化验证 [重要性: critical, 可验证: 可通过后续跟踪验证]",
  "假设：市场对该技术存在真实需求 [重要性: critical, 可验证: 需要市场调研]",
  "假设：竞争对手尚未布局类似技术 [重要性: important, 可验证: 可通过专利检索验证]"
]
```

### 5.3 不确定性映射

**不确定性维度**：

| 维度 | 说明 | 典型场景 |
|------|------|----------|
| **evidence_completeness** | 证据完整度 | 信号数量不足、缺少关键证据 |
| **signal_reliability** | 信号可靠性 | 信号来源不明确、信号质量存疑 |
| **timing_uncertainty** | 时间不确定性 | 事件发生时间不明确、时效性难判断 |
| **impact_uncertainty** | 影响不确定性 | 机会影响范围难以评估 |
| **competitive_landscape** | 竞争格局不确定性 | 竞争对手动态不明确 |

**不确定性等级**：
- **low**：不确定性可控，不影响核心判断
- **medium**：存在不确定性，但可通过后续验证降低
- **high**：不确定性严重，可能影响判断有效性

### 5.4 2.4 证据包的使用方式

**使用原则**：
- 2.4 提供的内容是**增强输入**，不是判断依据的唯一来源
- 2.4 的 similar_cases 用于补充 supporting_evidence
- 2.4 的 counter_examples 用于补充 counter_evidence
- 2.4 的 methodology_hints 用于指导判断方法，不直接作为证据
- 2.4 的 domain_constraints 用于补充 uncertainty_map

**边界约定**：
- ✅ 2.2 基于 2.4 提供的证据形成判断
- ❌ 2.2 不把判断权外包给 2.4
- ❌ 2.2 不因为 2.4 未提供证据就拒绝判断

### 5.5 证据不足的处理

当证据不足时，2.2 应：

1. **返回 insufficient_evidence 状态**
2. **在 diagnostics 中说明缺少哪些关键证据**
3. **在 next_validation_questions 中提出补充证据的方向**
4. **不强行给出低质量判断**

示例：
```typescript
{
  status: "insufficient_evidence",
  diagnostics: {
    signal_count: 1,
    evidence_completeness: 0.3,
    boundary_warnings: [
      "仅有单一技术信号，缺少市场验证信号",
      "缺少竞争对手动态信息"
    ]
  },
  opportunity: {
    // ... 部分字段
    next_validation_questions: [
      "该技术是否有市场需求验证？",
      "竞争对手是否有类似布局？"
    ]
  }
}
```

---

## 六、MVP 验证方案

### 6.1 验证目标

验证 Phase 2.2 的最小判断闭环是否成立，具体包括：

1. **对象稳定性**：OpportunityObject 是否符合 Schema 定义
2. **判断可解释性**：机会论点是否清晰、证据是否充分
3. **分级合理性**：priority_level 是否与证据强度匹配
4. **下游可消费性**：2.3 是否能基于输出进行行动设计

### 6.2 验证方式

**轻量案例验证**（不是完整 benchmark）：

- **案例数量**：3-8 组真实案例
- **案例覆盖**：
  - 至少 1 个 watch 级别案例
  - 至少 1 个 research 级别案例
  - 至少 1 个 deep_dive 级别案例
  - 可选 1 个 escalate 级别案例
- **验证维度**：
  - Schema 合法率：100%
  - 论点可解释性：人工评审
  - 证据完整性：支持/反对证据并列
  - 分级一致性：与人工判断对比

### 6.3 验收检查表

| 检查项 | 检查标准 | 通过条件 |
|--------|----------|----------|
| **Schema 合法性** | 输出符合 OpportunityObject 定义 | 100% 合法 |
| **论点清晰度** | opportunity_thesis 人类可读、可质疑 | 人工评审通过 |
| **证据并列** | supporting_evidence 和 counter_evidence 同时存在 | 100% 并列 |
| **假设显式化** | key_assumptions 不为空且合理 | 100% 显式 |
| **不确定性标注** | uncertainty_map 覆盖关键不确定性 | 人工评审通过 |
| **分级合理性** | priority_level 与证据强度匹配 | 80% 一致 |
| **边界遵守** | 不回卷到 2.1、不越界到 2.3 | 100% 遵守 |
| **下游可消费** | 2.3 能基于输出进行行动设计 | 人工评审通过 |

### 6.4 验证案例示例

**案例 1：watch 级别**
- 输入：单一技术信号，无市场验证
- 预期输出：priority_level = "watch"，next_validation_questions 提示需要更多信号

**案例 2：research 级别**
- 输入：2-3 个相关信号（技术 + 市场），有初步证据
- 预期输出：priority_level = "research"，建议启动轻量研究

**案例 3：deep_dive 级别**
- 输入：多信号聚类（技术 + 市场 + 团队），证据较充分
- 预期输出：priority_level = "deep_dive"，建议深度分析

### 6.5 失败模式识别

在验证过程中，需要识别以下失败模式：

| 失败模式 | 表现 | 处理方式 |
|----------|------|----------|
| **过度自信** | 只有支持证据，无反对证据 | 强制要求反对证据 |
| **判断越界** | 输出具体行动方案 | 边界检查拦截 |
| **证据不足强判** | 证据不足但仍给出高置信度判断 | 降低置信度或返回 insufficient_evidence |
| **假设隐藏** | 关键假设未显式化 | 人工评审识别并补充 |

### 6.6 验收结论口径

- **可推进**：通过所有必需检查项，可进入 2.3 联调
- **需返工**：未通过关键检查项，需修正后重新验证
- **需拍板**：存在设计分歧，需用户决策

---

## 七、设计取舍说明

### 7.1 核心取舍决策

#### 取舍 1：对象化 vs 报告化

**选择**：优先对象化，报告作为后续增强

**理由**：
- ✅ 对象化支持 2.3 稳定消费，报告化难以程序化处理
- ✅ 对象化便于版本管理和追溯，报告化难以比较
- ✅ 对象化是 MVP 核心目标，报告化是展示增强

**代价**：
- ❌ 初期对用户展示不够直观
- ❌ 需要额外的可视化层（可作为 P1 增强）

#### 取舍 2：简单分级 vs 复杂评分

**选择**：采用 4 级分级（watch/research/deep_dive/escalate），不做复杂评分系统

**理由**：
- ✅ 4 级分级足够支持 2.3 的分流需求
- ✅ 简单分级更易解释和调试
- ✅ 复杂评分系统需要大量标注数据和调优

**代价**：
- ❌ 无法提供精细化的优先级排序
- ❌ 同级别内的机会无法进一步区分

**后续增强路径**：
- P1：在 4 级分级基础上增加 confidence_score 作为辅助排序
- P2：引入多维度评分体系

#### 取舍 3：Prompt-first vs 规则引擎

**选择**：MVP 采用 Prompt-first，规则作为后处理补充

**理由**：
- ✅ Prompt-first 快速启动，无需大量规则设计
- ✅ LLM 能处理复杂的证据组织和论点形成
- ✅ 规则引擎适合后续优化和边界加固

**代价**：
- ❌ Prompt 稳定性需要迭代验证
- ❌ 边界情况可能需要规则兜底

**实施方式**：
- 核心判断逻辑：Prompt-first
- Schema 校验：规则引擎
- 边界检查：规则引擎

#### 取舍 4：强依赖 2.4 vs 可选增强

**选择**：2.4 作为可选增强输入，不强依赖

**理由**：
- ✅ 避免 2.4 阻塞 2.2 启动
- ✅ 2.2 可基于 2.1 信号独立完成最小判断
- ✅ 2.4 作为增强输入提升判断质量

**代价**：
- ❌ 无 2.4 输入时，判断质量可能较低
- ❌ 需要设计降级策略

**降级策略**：
- 无 2.4 输入时，仅基于 2.1 信号形成判断
- 在 uncertainty_map 中标注"缺少外部证据验证"
- 降低 confidence_score

#### 取舍 5：单 Agent 角色面具 vs 多 Agent 协作

**选择**：MVP 采用单 Agent 角色面具协作，多 Agent 作为 P1/P2 增强

**理由**：
- ✅ 单 Agent 上下文天然共享，适合设计收敛
- ✅ 角色面具足够支持多视角讨论
- ✅ 多 Agent 增加系统复杂度，不是 MVP 必需

**代价**：
- ❌ 无法展示多 Agent 协作能力
- ❌ 角色面具切换不如多 Agent 直观

**后续增强路径**：
- P1：在关键判断节点引入多 Agent 辩论
- P2：完整多 Agent 编排系统

### 7.2 边界取舍

#### 边界 1：与 2.1 的边界

**明确不做**：
- ❌ 不回卷重做信号识别
- ❌ 不质疑 2.1 的信号准入判断
- ❌ 不修改 2.1 的 Signal Schema

**明确要做**：
- ✅ 消费 2.1 的结构化信号
- ✅ 基于信号形成机会对象
- ✅ 在 diagnostics 中反馈信号质量问题（供 2.1 参考）

#### 边界 2：与 2.3 的边界

**明确不做**：
- ❌ 不给出具体行动方案
- ❌ 不设计资源投入计划
- ❌ 不做决策级输出

**明确要做**：
- ✅ 给出升级建议方向（suggested_actions）
- ✅ 提出验证问题（next_validation_questions）
- ✅ 提供分级结果（priority_level）

#### 边界 3：与 2.4 的边界

**明确不做**：
- ❌ 不替代 2.4 做深度知识检索
- ❌ 不把判断权外包给 2.4
- ❌ 不强依赖 2.4 才能工作

**明确要做**：
- ✅ 消费 2.4 的证据包作为增强输入
- ✅ 基于 2.4 提供的证据形成判断
- ✅ 在证据不足时，在 next_validation_questions 中提示需要 2.4 补充

---

## 八、待拍板事项

### 8.1 核心设计决策（必须拍板）

#### 决策 1：OpportunityObject 字段集是否确认

**当前方案**：采用第三节定义的最小字段集

**需要确认**：
- 字段集是否完整，是否缺少关键字段
- 字段命名是否合理
- 是否需要调整字段结构

**影响范围**：影响 2.3 的消费契约、实现复杂度

**推荐**：先冻结最小字段集，后续通过 metadata 扩展

**✅ 拍板结论**（2026-03-16）：
- **已确认**：采用精简版最小字段集
- **调整内容**：
  - 移除 `signal_cluster_summary`（非必需）
  - 移除 `confidence_score`（P1 阶段再引入）
  - 移除 `suggested_actions`（避免与 2.3 越界）
  - 移除 `created_at`（非核心字段）
  - 移除 `metadata`（当前不需要扩展）
  - 简化 `uncertainty_map` 为 `string[]`（降低复杂度）
- **最终字段集**：opportunity_id, opportunity_title, opportunity_thesis, related_signals, supporting_evidence, counter_evidence, key_assumptions, uncertainty_map, priority_level, next_validation_questions, judgment_version, processing_time_ms
- **状态**：✅ 已冻结，可启动实现

---

#### 决策 2：分级口径是否确认

**当前方案**：4 级分级（watch/research/deep_dive/escalate）

**需要确认**：
- 4 级是否足够，是否需要更细粒度
- 分级触发条件是否合理
- 是否需要增加数值型评分

**影响范围**：影响 2.3 的分流逻辑、验证标准

**推荐**：先采用 4 级分级，P1 阶段再考虑增加 confidence_score 辅助排序

**✅ 拍板结论**（2026-03-16）：
- **已确认**：采用 4 级分级（watch/research/deep_dive/escalate）
- **分级触发条件**：按照第四节 4.2 定义的口径执行
- **数值型评分**：P1 阶段再引入，当前不做
- **状态**：✅ 已冻结，可启动实现

---

#### 决策 3：2.4 依赖方式是否确认

**当前方案**：2.4 作为可选增强输入，不强依赖

**需要确认**：
- 是否接受无 2.4 输入时的降级判断
- 降级策略是否合理
- 是否需要调整为强依赖

**影响范围**：影响 2.2 启动时机、2.4 开发优先级

**推荐**：保持可选增强，避免阻塞 2.2 启动

**降级策略说明**：
当 2.4 未提供 `context_packet` 时，2.2 采取以下策略：
1. 仅基于 2.1 信号形成判断，从 `related_signals` 中提取支持证据
2. 在 `uncertainty_map` 中显式标注："缺少外部证据验证，判断仅基于内部信号"
3. 在 `next_validation_questions` 中提示需要补充外部证据
4. `priority_level` 可能更保守（倾向于 watch/research）
5. 不会因为缺少 2.4 就拒绝判断，仍然输出 `OpportunityObject`

**✅ 拍板结论**（2026-03-16）：
- **已确认**：2.4 作为可选增强输入，不强依赖
- **降级策略**：已明确，按照上述 5 点策略执行
- **启动时机**：2.2 可独立启动，不等待 2.4
- **状态**：✅ 已冻结，可启动实现

---

#### 决策 4：验证方案是否确认

**当前方案**：3-8 组轻量案例验证

**需要确认**：
- 案例数量是否足够
- 验收标准是否合理
- 是否需要更完整的 benchmark

**影响范围**：影响验收时机、质量基线

**推荐**：先采用轻量验证，P1 阶段再建立完整 benchmark

---

### 8.2 实现路径决策（本周最好拍板）

#### 决策 5：Prompt 策略

**当前方案**：Prompt-first + 规则后处理

**需要确认**：
- 是否接受 Prompt-first 的稳定性风险
- 规则后处理的范围
- Prompt 迭代机制

**影响范围**：影响实现复杂度、调试难度

**推荐**：采用 Prompt-first，规则仅用于 Schema 校验和边界检查

---

#### 决策 6：实现优先级

**当前方案**：先实现核心判断流程，再补充边界检查和错误处理

**需要确认**：
- 实现顺序是否合理
- 是否需要调整优先级

**影响范围**：影响开发节奏、验证时机

**推荐**：
1. 先实现 OpportunityObject Schema 和校验
2. 再实现核心判断流程（步骤 1-6）
3. 最后补充边界检查和错误处理

---

### 8.3 后续增强决策（可延后拍板）

#### 决策 7：多 Agent 引入时机

**当前方案**：P1/P2 阶段引入

**需要确认**：
- 是否需要提前到 MVP
- 引入范围（全流程 vs 关键节点）

**影响范围**：影响系统复杂度、展示效果

**推荐**：保持 P1/P2 引入，MVP 聚焦判断闭环

---

#### 决策 8：复杂评分系统

**当前方案**：P2 阶段引入

**需要确认**：
- 是否需要提前规划评分维度
- 评分系统与分级的关系

**影响范围**：影响后续扩展性

**推荐**：P2 引入，当前保持简单分级

---

### 8.4 拍板优先级

| 优先级 | 决策项 | 拍板时机 | 阻塞影响 |
|--------|--------|----------|----------|
| **P0** | 决策 1：OpportunityObject 字段集 | 立即 | 阻塞实现启动 |
| **P0** | 决策 2：分级口径 | 立即 | 阻塞实现启动 |
| **P0** | 决策 3：2.4 依赖方式 | 立即 | 影响启动时机 |
| **P1** | 决策 4：验证方案 | 本周 | 影响验收标准 |
| **P1** | 决策 5：Prompt 策略 | 本周 | 影响实现路径 |
| **P1** | 决策 6：实现优先级 | 本周 | 影响开发节奏 |
| **P2** | 决策 7：多 Agent 引入时机 | 可延后 | 不阻塞 MVP |
| **P2** | 决策 8：复杂评分系统 | 可延后 | 不阻塞 MVP |

---

## 九、后续步骤

### 9.1 拍板后的执行路径

**✅ P0 决策已完成拍板**（2026-03-16）

1. ✅ **用户拍板 P0 决策**（决策 1-3）- 已完成
2. ✅ **冻结核心契约**：OpportunityObject Schema 已冻结
3. ⏭️ **启动实现**：按照第四节主流程设计开始实现
4. ⏭️ **轻量验证**：按照第六节验证方案进行案例验证
5. ⏭️ **验收判断**：基于验收检查表判断是否可进入 2.3 联调

**下一步行动**：
- 立即启动实现：实现 OpportunityObject Schema 和校验逻辑
- 实现核心判断流程（步骤 1-6）
- 准备 3-8 组轻量验证案例

### 9.2 文档更新机制

- 拍板结果回写到本文档 ✅ 已完成
- 实现过程中的调整记录到执行轨文档
- 验证结果记录到验收报告

---

**文档状态**：✅ 设计方案已完成，P0 决策已拍板，核心契约已冻结
**版本**：v1.0（2026-03-16 拍板版）
**产出方式**：基于 phase2_roles/phase2.2_roles.md 的多角色面具讨论收敛
**下一步**：启动实现，按照冻结的契约和流程设计开始开发
