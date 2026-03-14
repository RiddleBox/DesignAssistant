# Phase 2.1 情报解码模块

> **模块状态**: MVP 实现完成
> **版本**: v1.0
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

## 三、快速开始

### 3.1 安装依赖

```bash
pip install anthropic pydantic
```

### 3.2 设置 API Key

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 3.3 运行示例

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

## 四、设计特点

### 4.1 四类范式信号

- **technical**: 技术信号（引擎升级、跨平台发布、技术创新）
- **market**: 市场信号（市场趋势、用户需求、竞品动态）
- **team**: 团队信号（核心团队变动、关键人才加入）
- **capital**: 资本信号（融资、收购、投资）

### 4.2 三维评分体系

- **intensity_score**: 强度评分（1-10）
- **confidence_score**: 可信度评分（1-10）
- **timeliness_score**: 时效性评分（1-10）

### 4.3 Prompt-first 策略

- 使用 Claude Opus 4.6
- 6 个 few-shot 样例（4 类信号 + 1 边界例 + 1 负例）
- 温度设为 0 保证稳定性
- 轻量后处理（格式规范化、字段补全、去重）

### 4.4 错误处理

- LLM API 限流：重试 3 次，指数退避
- JSON 解析失败：记录 warning，返回空 signals
- Schema 校验失败：记录 warning，尝试修复或丢弃该信号

## 五、输出契约

### 5.1 Signal 结构

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

### 5.2 DecodedIntelligence 结构

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

## 六、验收标准

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| Schema 合法率 | 100% | ✅ 已实现 Pydantic 校验 |
| 准确率 | ≥ 80% | ⏳ 待 benchmark 测试 |
| 召回率 | ≥ 75% | ⏳ 待 benchmark 测试 |
| 单次处理耗时 | < 30s | ✅ 预计 6-11s |
| 输入源覆盖 | 至少 3 类 | ✅ 支持 news/report/announcement |

## 七、下一步工作

### 7.1 立即启动（评测与验收负责人视角）

1. **构建 benchmark**：
   - 收集 30 条样本（news 10 + report 10 + announcement 10）
   - 完成人工标注
   - 建立标注规范

2. **首轮测试**：
   - 运行 benchmark
   - 计算准确率、召回率、Schema 合法率
   - 出具验收报告

### 7.2 后续增强（可后置拍板）

- 规则 + LLM 混合链路（如果准确率/召回率不达标）
- 扩充信号类别（如果四类无法覆盖主要样本）
- 实体标准化与关系图谱（如果 2.2 明确提出强依赖）
- 2.4 上下文增强（待 2.4 真实能力稳定后）

## 八、相关文档

- 设计方案：[phase2.1_设计方案.md](../phase2_plan/phase2.1_设计方案.md)
- 角色定义：[phase2.1_roles.md](../phase2_plan/phase2_roles/phase2.1_roles.md)
- 启动文档：[phase2.1_启动与拍板.md](../phase2_plan/phase2.1_启动与拍板.md)

## 九、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-03-14 | MVP 初始版本，Prompt-first + 轻量后处理 |