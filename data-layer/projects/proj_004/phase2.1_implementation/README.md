# Phase 2.1 情报解码模块

> **模块状态**: MVP 实现完成
> **版本**: v1.1
> **最后更新**: 2026-03-14

## 一、模块概述

Phase 2.1 情报解码模块负责将非结构化信息（新闻、报告、公告）转化为可追溯、可评分、可被下游稳定消费的结构化范式信号。

## 二、核心文件

| 文件 | 说明 |
|------|------|
| `schemas.py` | 数据结构定义（Signal、DecodedIntelligence、评分口径） |
| `prompt_templates.py` | Prompt 模板与 few-shot 样例集（6 个样例） |
| `decoder.py` | 核心解码器实现（Prompt-first + 轻量后处理） |
| `example_usage.py` | 使用示例 |
| `data/benchmark_samples.json` | `2.1 benchmark` 正式样本文件（唯一真相源；按正式 JSON 结构维护样本与人工标注） |
| `docs/SAMPLE_POOL_SCHEMA_NOTES.md` | benchmark 样本文件说明、字段口径与人工标注工作流说明 |

## 三、文档目录

| 文档 | 说明 |
|------|------|
| `docs/annotation_guidelines.md` | 标注规范 |
| `docs/sample_preparation_guide.md` | 样本准备指南 |
| `docs/benchmark_validation_guide.md` | Benchmark 验收指南 |
| `docs/PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md` | `2.1` 第一性原理、岗位本质与服务对象对齐文档 |
| `docs/PHASE2_1_CONTEXT_PACKET_CONSUMPTION_DESIGN_DRAFT.md` | `2.1` 消费 `2.4 ContextPacket` 的设计草案 |
| `docs/PHASE2_1_BENCHMARK_UPGRADE_DRAFT.md` | `2.1` benchmark 口径升级草案 |
| `docs/PHASE2_1_PROMPT_AND_FEWSHOT_OPTIMIZATION_DRAFT.md` | `2.1` Prompt 角色设定与 few-shot 优化草案 |
| `docs/PHASE2_1_MVP_SCOPE_AND_ITERATION_ALIGNMENT.md` | `2.1 MVP` 范围与后续迭代边界对齐文档 |

## 四、快速开始

### 4.1 安装依赖

```bash
pip install anthropic pydantic
```

### 4.2 设置 API Key

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 4.3 运行示例

```python
from decoder import IntelligenceDecoder
from schemas import IntelligenceDecodeRequest, SourceType

# 初始化解码器
decoder = IntelligenceDecoder(api_key="your-api-key")

# 构建请求
request = IntelligenceDecodeRequest(
    source_id="news_001",
    source_type=SourceType.NEWS,
    content="某游戏工作室宣布完成 A 轮融资 500 万美元..."
)

# 解码
result = decoder.decode(request)

# 查看结果
print(f"检测到 {len(result.signals)} 个信号")
for signal in result.signals:
    print(f"- {signal.signal_type.value}: {signal.signal_label}")
```

## 五、设计特点

### 5.1 四类范式信号

- **technical**: 技术信号（引擎升级、跨平台发布、技术创新）
- **market**: 市场信号（市场趋势、用户需求、竞品动态）
- **team**: 团队信号（核心团队变动、关键人才加入）
- **capital**: 资本信号（融资、收购、投资）

### 5.2 三维评分体系

- **intensity_score**: 强度评分（1-10）
- **confidence_score**: 可信度评分（1-10）
- **timeliness_score**: 时效性评分（1-10）

### 5.3 Prompt-first 策略

- 使用 Claude Opus 4.6
- 6 个 few-shot 样例（4 类信号 + 1 边界例 + 1 负例）
- 温度设为 0 保证稳定性
- 轻量后处理（格式规范化、字段补全、去重）
- `retrieval_context` 作为未来 `2.4` 上下文增强入口，当前保持低耦合可选接入

### 5.4 错误处理

- LLM API 限流：重试 3 次，指数退避
- JSON 解析失败：记录 warning，返回空 signals
- Schema 校验失败：记录 warning，尝试修复或丢弃该信号

## 六、输出契约

### 6.1 Signal 结构

```json
{
  "signal_id": "sig_001",
  "signal_type": "technical|market|team|capital",
  "signal_label": "UE5 升级",
  "description": "项目从 UE4 升级到 UE5",
  "evidence_text": "官方公告：我们很高兴宣布...",
  "entities": ["Unreal Engine 5", "Nanite"],
  "intensity_score": 8,
  "confidence_score": 10,
  "timeliness_score": 9,
  "source_ref": "news_001",
  "extracted_at": "2026-03-14T10:00:00Z"
}
```

### 6.2 DecodedIntelligence 结构

```json
{
  "source_id": "news_001",
  "source_type": "news",
  "signals": [...],
  "summary": "检测到 1 个范式信号：技术信号 1 个",
  "decoder_version": "v1.0",
  "processing_time_ms": 6500,
  "warnings": []
}
```

## 七、如何理解这个模块

如果只从工程上看，`2.1` 是一个“结构化信号抽取模块”；但如果从真实岗位本质看，它更准确的定义是：

> **一个面向战略研究、项目孵化与生态投资的“范式信号解码层”。**

它的重点不是“把文本抽成 JSON”本身，而是把高熵外部情报压缩成后续工作流可以稳定消费的低歧义信号单元。

如果你希望理解这层更深的定位，建议先阅读：

- [PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md)
- [PHASE2_1_CONTEXT_PACKET_CONSUMPTION_DESIGN_DRAFT.md](f:\AIProjects\DesignAssistant\data-layer\projects\proj_004\phase2.1_implementation\docs\PHASE2_1_CONTEXT_PACKET_CONSUMPTION_DESIGN_DRAFT.md)

## 八、验收标准

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| Schema 合法率 | 100% | ✅ 已实现 Pydantic 校验 |
| 准确率 | ≥ 80% | ⏳ 待 benchmark 测试 |
| 召回率 | ≥ 75% | ⏳ 待 benchmark 测试 |
| 单次处理耗时 | < 30s | ✅ 预计 6-11s |
| 输入源覆盖 | 至少 3 类 | ✅ 支持 news/report/announcement |

## 九、Benchmark 结果与方法论边界

### 9.1 首轮 Benchmark 完成情况

**执行状态**: ✅ 已完��三轮 benchmark（v1.0 → v1.1 → v1.2）

**核心指标**（v1.2 当前版本）:
- Precision: 42.86%（相比 baseline 提升 7.15%）
- Recall: 80.00%（保持稳定）
- F1 Score: 55.81%（相比 baseline 提升 5.81%）
- Schema 合法率: 100%
- 误报数量: 32 个（相比 baseline 减少 28.9%）

**优化历程**:
- v1.0 → v1.1: Precision +6.4%，成功压制 market 误报（25 → 12）
- v1.1 → v1.2: Precision +0.75%，边际收益递减

**详细报告**:
- [PHASE2_1_BASELINE_BENCHMARK_REPORT.md](docs/PHASE2_1_BASELINE_BENCHMARK_REPORT.md) - v1.0 baseline 分析
- [PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md](docs/PHASE2_1_V1.0_VS_V1.1_COMPARISON_REPORT.md) - 首轮优化对比
- [PHASE2_1_OPTIMIZATION_SUMMARY.md](docs/PHASE2_1_OPTIMIZATION_SUMMARY.md) - 完整优化历程总结

### 9.2 重要方法论发现：Taxonomy 边界问题

**本轮 benchmark 暴露出的关键问题**：

并非所有被统计为"误报"的信号都是模型判断错误。部分样本的分类差异源于 **signal taxonomy 本身的边界暧昧**，尤其集中在 `market` 与 `capital` 的区分上。

**典型案例**：
- 微软收购动视暴雪（S002）
  - 从资本交易视角：690 亿美元收购 → `capital` 信号合理
  - 从市场格局视角：改变游戏行业平台竞争态势 → `market` 信号合理
  - **两种解释都具备业务合理性**

**问题本质**：
- 这不是 Prompt 错误，而是 taxonomy 歧义
- 同一事件可从多个角度抽取信号，但当前标注只给出单一标签
- 继续调整 Prompt 无法解决这类分类差异

**当前阶段处理原则**：

1. **不建议立即改为双标签**
   - 双标签会提高样本要求，可能把"可接受的标签歧义"误转化为"模型漏报"
   - 会污染阶段性评估结论，使 Precision/Recall 指标失去可比性

2. **定义为独立问题类型**
   - 标记为 `taxonomy_ambiguity` 或 `annotation_boundary_issue`
   - 在 benchmark 报告中单独列出，不计入 Prompt 优化的评估范围
   - 作为后续优化的重要方向

3. **纳入系统能力建设规划**
   - 这属于系统能力建设的一部分，而非单次 Prompt 调优即可解决
   - 需要跨模块协同（2.1 → 2.2 → 2.4）共同解决

**后续推进方向**（详见 [PHASE2_1_OPTIMIZATION_SUMMARY.md](docs/PHASE2_1_OPTIMIZATION_SUMMARY.md) 第九章）：
1. 梳理 `market` / `capital` / `team` / `technical` 的边界定义
2. 建立"单主标签 / 可接受替代标签 / 真正双信号样本"的判定规则
3. 对 benchmark 样本中的暧昧样本建立单独清单
4. 考虑在未来版本中支持"可接受替代标签"的评估逻辑
5. 将 taxonomy 澄清视为 `2.1 → 2.2 → 2.4` 协同设计的一部分

### 9.3 Prompt 优化的边界

**已确认的结论**：
- Prompt 优化已接近上限（v1.2 边际收益仅 0.75%）
- 剩余 32 个误报中，部分属于标注边界问题而非模型错误
- 不建议继续通过 Prompt 调优追求更高分数

**下一步重点**（优先级排序）：
1. **P0**: 澄清 taxonomy 定义，解决 market/capital 等边界歧义
2. **P1**: 引入 Phase 2.4 ContextPacket 增强，通过外部约束提升精度
3. **P2**: 扩大 benchmark 样本至 50-100 个，更全面评估性能

### 9.4 后续增强（建议后置拍板）

- 规则 + LLM 混合链路（如果准确率/召回率不达标）
- 扩充信号类别（如果四类无法覆盖主要样本）
- 实体标准化与关系图谱（如果 `2.2` 明确提出强依赖）
- few-shot 资产体系系统化维护（待首轮 benchmark 形成清晰错误画像后推进）
- `2.4` 上下文增强（待 `ContextPacket` 协议与联合 benchmark 路径收口后接入）
- Prompt 角色设定进一步向“战略研究 / 孵化 / 投资导向的范式信号解码器”收口

## 十、建议阅读顺序

1. 本 README
2. `docs/PHASE2_1_FIRST_PRINCIPLES_AND_ROLE_ESSENCE.md`
3. `docs/PHASE2_1_CONTEXT_PACKET_CONSUMPTION_DESIGN_DRAFT.md`
4. `docs/PHASE2_1_BENCHMARK_UPGRADE_DRAFT.md`
5. `docs/PHASE2_1_PROMPT_AND_FEWSHOT_OPTIMIZATION_DRAFT.md`
6. `docs/PHASE2_1_MVP_SCOPE_AND_ITERATION_ALIGNMENT.md`
7. `docs/annotation_guidelines.md`
8. `docs/sample_preparation_guide.md`
9. `docs/benchmark_validation_guide.md`
10. `schemas.py`
11. `prompt_templates.py`
12. `decoder.py`

## 十一、相关文档

- 设计方案：[phase2.1_设计方案.md](../phase2_plan/phase2.1_设计方案.md)
- 角色定义：[phase2.1_roles.md](../phase2_plan/phase2_roles/phase2.1_roles.md)
- 启动文档：[phase2.1_启动与拍板.md](../phase2_plan/phase2.1_启动与拍板.md)
- `2.4` 第一性原理文档：[PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md](../phase2.4_implementation/docs/PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md)
- `2.4 -> 2.1` 协议草案：[PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md](../phase2.4_implementation/docs/PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md)

## 十二、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.1 | 2026-03-14 | 补充 `2.1` 第一性原理文档、`ContextPacket` 消费设计草案与阅读路径 |
| v1.0 | 2026-03-14 | MVP 初始版本，Prompt-first + 轻量后处理 |