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

## 九、下一步工作

### 9.1 当前阶段主任务（MVP 验证与轻量升级）

1. **按升级版 benchmark 草案准备样本与标注表**：
   - 继续保留现有基础验收指标
   - 补入高价值变化 / 背景保留 / 噪音 / 边界样本观察字段
   - 形成首轮 baseline 的轻量增强版 benchmark

2. **完成首轮 baseline benchmark**：
   - 运行 benchmark
   - 计算准确率、召回率、Schema 合法率
   - 输出误报 / 漏报 / 边界样本分布与代表性案例复盘

3. **根据 benchmark 结果决定是否轻量升级 Prompt / few-shot**：
   - 若误报、边界不稳、命名漂移明显，再做一轮定向 Prompt 轻调
   - 优先补少量高价值 few-shot，而非立即扩成完整体系

### 9.2 后续增强（建议后置拍板）

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