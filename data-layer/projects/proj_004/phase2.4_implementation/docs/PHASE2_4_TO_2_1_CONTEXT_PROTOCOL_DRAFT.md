# Phase 2.4 → Phase 2.1 上下文协议草案

**文档类型**: 跨模块协议草案  
**适用链路**: `Phase 2.4` 证据级上下文供应层 → `Phase 2.1` 情报解码模块  
**归档对象**: `proj_004 / phase2.4_implementation`  
**归档时间**: 2026-03-14  
**状态**: Draft v0.1（用于设计收口与联调准备）

---

## 一、文档目的

本文件用于把前面对 `2.4` 的第一性原理判断，进一步落成一份可讨论、可迭代、可用于联调的**跨模块协议草案**。

它不试图一步到位定义最终 API，而是先回答一个更关键的问题：

> 当 `2.1` 在做“非结构化文本 → 结构化信号”抽取时，`2.4` 到底应该给它什么，才能真正降低判断不确定性？

因此，本协议草案的重点不是“检索系统怎么实现”，而是：

- `2.1` 在什么时机需要 `2.4`
- `2.4` 应以什么最小单元交付证据
- 哪些字段是 `2.1` 真正可消费的
- 如何在低耦合前提下先建立稳定协作面

---

## 二、第一性原理下的协议定位

从第一性原理看，`2.4 -> 2.1` 的关系不应理解为：

- `2.4` 帮 `2.1` 回答问题
- `2.4` 替 `2.1` 做抽取
- `2.4` 直接产出结构化信号

更准确地说，应该理解为：

> **`2.4` 为 `2.1` 提供“与当前抽取任务相关、可信、可消费”的辅助证据包，帮助 `2.1` 更稳地完成字段判断与信号抽取。**

因此，这条链路的产品目标不是“让 `2.4` 更聪明”，而是：

> **让 `2.1` 在术语理解、边界判断、字段归类、few-shot 参考和证据约束上变得更稳定。**

---

## 三、`2.1` 真正需要 `2.4` 提供什么

结合 `2.1` 当前目标、边界和契约草案，`2.1` 需要的不是泛知识，而更像下面这几类上下文：

### 3.1 术语定义类

用于帮助 `2.1` 正确理解行业词、机制名词、组织形式或业务术语。

典型用途：

- 判断某个说法是否属于特定技术路线
- 识别某个业务术语在当前领域中的含义
- 降低由于术语歧义导致的误抽取

### 3.2 抽取样例类

用于帮助 `2.1` 在相似输入场景下参考高质量 few-shot 样例。

典型用途：

- 学习类似文本中哪些句子被抽成信号
- 学习某类信号通常如何命名和描述
- 学习证据片段与最终字段之间的映射方式

### 3.3 规则约束类

用于提示 `2.1` 在当前任务里有哪些字段边界、分类约束或判定规则。

典型用途：

- 避免把背景噪音误判成强信号
- 避免把 `market` 错分到 `capital`
- 约束 `signal_label` 与 `signal_type` 的搭配范围

### 3.4 边界反例类

用于帮助 `2.1` 识别“看起来像，但其实不该抽”的情况。

典型用途：

- 抑制模型脑补
- 减少弱相关句子的错误抽取
- 帮助评估信号强度和置信度的合理范围

### 3.5 背景补充类

用于在原文省略上下文时，提供必要背景知识帮助 `2.1` 理解材料。

典型用途：

- 原文默认读者已知某项目背景
- 某公告引用了既有事件但未展开说明
- 某报告中的缩写或概念需要外部解释

---

## 四、协议设计原则

### 4.1 `2.4` 提供证据，不提供最终信号结论

`2.4` 可以帮助 `2.1` 更好判断，但不应直接替代 `2.1` 输出 `Signal`。

原因很简单：

- `2.1` 才是结构化信号抽取的责任主体
- 如果 `2.4` 直接输出信号，会模糊模块边界
- 出现错误时也会更难定位是检索问题还是抽取问题

### 4.2 交付最小必要证据，而不是整篇文档

`2.1` 最需要的是可直接消费的**证据片段**，而不是一堆完整文档。

因此，本协议草案的核心交付单元应是：

> **`ContextPacket`**

而不是传统意义上的文档对象。

### 4.3 用途必须显式标注

`2.1` 不应再去猜：

- 这段内容是术语说明还是 few-shot
- 这是硬约束还是弱参考
- 这是正例还是反例

因此，协议里必须有显式用途字段。

### 4.4 保持低耦合接入

考虑到 `2.4` 当前真实能力仍在演进，`2.1` 不应把该协议作为启动硬阻塞。

因此设计上应满足：

- `retrieval_context` 可以为空
- `2.1` 在无增强上下文时仍可运行
- `2.4` 的增强接入是“增益型输入”，不是“强制型前置依赖”

### 4.5 协议必须可评测

每次 `2.4` 输出给 `2.1` 的上下文，都应该能被回看和分析：

- 给了什么
- 为什么给
- 最后有没有帮助 `2.1`

否则后续无法做联合优化。

---

## 五、推荐的最小交付单元：`ContextPacket`

### 5.1 一句话定义

> **`ContextPacket` 是 `2.4` 提供给 `2.1` 的最小证据级上下文单元，用于表达“这段信息是什么、为什么命中、建议如何被使用”。**

### 5.2 推荐字段

| 字段 | 类型 | 必填 | 含义 | 备注 |
|------|------|------|------|------|
| `packet_id` | `string` | Y | 上下文包唯一ID | 用于日志追踪 |
| `source_id` | `string` | Y | 来源知识条目ID | 对应 `2.4` 知识资产 |
| `source_type` | `string` | Y | 来源类型 | 如 `glossary / few_shot / rule / background / case` |
| `title` | `string` | N | 来源标题 | 便于人工排查 |
| `excerpt` | `string` | Y | 实际交付的证据片段 | 不建议直接给全文 |
| `excerpt_span` | `object` | N | 片段位置 | 如段落号、字符区间 |
| `use_as` | `string` | Y | 建议用途 | 如 `glossary / few_shot / constraint / boundary_case / background` |
| `topic` | `string` | N | 主题标签 | 便于粗粒度分类 |
| `tags` | `string[]` | N | 细粒度标签 | 支持术语、信号类型、场景等 |
| `reason_for_match` | `string` | Y | 命中原因 | 必须说明和当前任务的关系 |
| `applicable_to` | `string[]` | N | 适用字段或场景 | 如 `signal_type`, `signal_label`, `confidence_score` |
| `trust_level` | `string` | N | 信任等级 | 如 `high / medium / low` |
| `freshness` | `string` | N | 时效性标记 | 如 `recent / reference / historical` |
| `score` | `number` | N | 检索支持分数 | 仅作为支持信号，不等于事实置信度 |
| `metadata` | `object` | N | 扩展元数据 | 预留兼容 |

### 5.3 推荐 JSON 示例

```json
{
  "packet_id": "ctx_001",
  "source_id": "kb_glossary_017",
  "source_type": "glossary",
  "title": "跨平台发行术语定义",
  "excerpt": "跨平台发行通常指同一游戏产品面向多个平台同步或分阶段上线，并以平台覆盖能力作为市场扩张信号之一。",
  "excerpt_span": {
    "section": "definition",
    "char_start": 0,
    "char_end": 52
  },
  "use_as": "glossary",
  "topic": "distribution_strategy",
  "tags": ["market", "publishing", "cross-platform"],
  "reason_for_match": "原文中出现‘多平台同步上线’表述，可能影响 `signal_type` 与 `signal_label` 判断，需要术语定义帮助消歧。",
  "applicable_to": ["signal_type", "signal_label", "description"],
  "trust_level": "high",
  "freshness": "reference",
  "score": 0.87,
  "metadata": {
    "last_updated": "2026-03-10",
    "knowledge_role": "term_definition"
  }
}
```

---

## 六、`2.4 -> 2.1` 请求草案

为了贴合 `2.1` 的真实消费方式，建议不要让 `2.1` 只传一个自然语言问题，而是传一个更接近“抽取任务上下文”的请求对象。

### 6.1 推荐请求对象：`DecodeContextRequest`

| 字段 | 类型 | 必填 | 含义 | 备注 |
|------|------|------|------|------|
| `request_id` | `string` | Y | 请求唯一ID | 用于联调日志 |
| `source_id` | `string` | Y | 当前待解码原文ID | 与 `2.1` 输入对齐 |
| `source_type` | `string` | Y | 原始信息类型 | `news / report / announcement` |
| `title` | `string` | N | 原始标题 | 可帮助检索 |
| `content` | `string` | Y | 原始正文 | 核心检索依据 |
| `decode_goal` | `string` | Y | 当前解码目标 | 建议固定为“提取结构化范式信号” |
| `candidate_signal_types` | `string[]` | N | 候选信号分类 | 如 `technical / market / team / capital` |
| `needed_context_types` | `string[]` | N | 希望优先提供的上下文类型 | 如 `glossary / few_shot / constraint` |
| `focus_fields` | `string[]` | N | 当前重点辅助字段 | 如 `signal_type`, `confidence_score` |
| `top_k` | `integer` | N | 上下文包数量上限 | 建议默认 `5` |
| `mode` | `string` | N | 检索模式 | 如 `assist_decode` |

### 6.2 请求示例

```json
{
  "request_id": "decode_ctx_req_001",
  "source_id": "news_20260314_001",
  "source_type": "news",
  "title": "某厂商宣布核心团队扩张并启动新一代引擎研发",
  "content": "某游戏厂商今日宣布将在上海新增研发团队，并面向下一代渲染技术加大投入……",
  "decode_goal": "提取结构化范式信号",
  "candidate_signal_types": ["technical", "team", "market", "capital"],
  "needed_context_types": ["glossary", "few_shot", "constraint"],
  "focus_fields": ["signal_type", "signal_label", "confidence_score"],
  "top_k": 5,
  "mode": "assist_decode"
}
```

---

## 七、`2.4 -> 2.1` 响应草案

### 7.1 推荐响应对象：`DecodeContextResponse`

| 字段 | 类型 | 必填 | 含义 | 备注 |
|------|------|------|------|------|
| `request_id` | `string` | Y | 原样回传请求ID | 用于链路追踪 |
| `context_packets` | `ContextPacket[]` | Y | 上下文包列表 | 可为空数组 |
| `query_summary` | `string` | N | 本次检索意图摘要 | 便于调试 |
| `retrieval_notes` | `string[]` | N | 检索备注 | 如“未命中 few-shot，仅命中 glossary” |
| `retrieval_time_ms` | `integer` | Y | 检索耗时 | |
| `version` | `string` | Y | 协议/检索版本 | 便于回归对比 |

### 7.2 响应示例

```json
{
  "request_id": "decode_ctx_req_001",
  "context_packets": [
    {
      "packet_id": "ctx_001",
      "source_id": "kb_glossary_017",
      "source_type": "glossary",
      "title": "跨平台发行术语定义",
      "excerpt": "跨平台发行通常指同一游戏产品面向多个平台同步或分阶段上线，并以平台覆盖能力作为市场扩张信号之一。",
      "use_as": "glossary",
      "tags": ["market", "publishing", "cross-platform"],
      "reason_for_match": "原文出现多平台上线表述，可能影响 `signal_type` 判定。",
      "applicable_to": ["signal_type", "signal_label"],
      "trust_level": "high",
      "score": 0.87
    },
    {
      "packet_id": "ctx_002",
      "source_id": "kb_case_021",
      "source_type": "few_shot",
      "title": "团队扩张信号抽取样例",
      "excerpt": "当文本明确提到新增研发团队、招聘扩张、组织搭建时，可优先判为 `team` 类信号。",
      "use_as": "few_shot",
      "tags": ["team", "hiring", "organization"],
      "reason_for_match": "原文包含研发团队扩张描述，与历史高质量样例相似。",
      "applicable_to": ["signal_type", "description", "confidence_score"],
      "trust_level": "high",
      "score": 0.82
    }
  ],
  "query_summary": "围绕团队扩张与技术投入，为结构化信号抽取提供术语定义与样例辅助。",
  "retrieval_notes": ["命中 1 条 glossary，1 条 few_shot，未命中 boundary_case"],
  "retrieval_time_ms": 68,
  "version": "draft_v0.1"
}
```

---

## 八、`2.1` 如何消费这些上下文

建议 `2.1` 不是把 `context_packets` 当作自由文本拼接，而是按用途装配到解码 prompt 或后处理流程中。

### 8.1 推荐消费方式

- `use_as = glossary`
  - 用于术语解释与分类消歧
- `use_as = few_shot`
  - 用于参考信号命名、字段描述与证据映射样式
- `use_as = constraint`
  - 用于约束分类边界与评分口径
- `use_as = boundary_case`
  - 用于抑制误判与脑补
- `use_as = background`
  - 用于补足理解上下文，但优先级低于前四类

### 8.2 推荐装配顺序

```text
约束类 > 术语类 > few-shot 类 > 边界反例类 > 背景类
```

原因是：

- 先确保不越界、不误解
- 再帮助分类与命名
- 最后才补充背景

这样更符合 `2.1` 作为结构化抽取模块的目标。

---

## 九、MVP 阶段建议采用的低耦合版本

考虑到当前 `2.4` 真实 API 仍更偏向传统 `/retrieve` / `/rag` 形态，MVP 阶段建议先采用一层**协议映射**，而不是立即重做底层系统。

### 9.1 MVP 建议路线

- 底层仍允许 `2.4` 使用现有检索能力
- 在 `2.4` 与 `2.1` 之间增加轻量“上下文组装层”
- 由该层把传统检索结果转换成 `ContextPacket[]`
- `2.1` 仅消费转换后的协议，不直接依赖底层文档对象结构

### 9.2 这样做的好处

- 不阻塞当前 `2.4` MVP 能力继续复用
- 不要求 `2.1` 适配传统文档级输出
- 后续 `2.4` 升级召回和排序策略时，`2.1` 接口可保持更稳定

---

## 十、联合评测建议

这份协议是否有效，不应只看“能返回上下文”，而要看：

### 10.1 模块内评测

- `context_packets` 是否字段完整
- `use_as` 标注是否稳定
- `reason_for_match` 是否有可解释性
- `top_k` 控制是否合理

### 10.2 联合评测

与 `2.1` 联合验证以下问题：

- 接入 `ContextPacket` 后，`signal_type` 准确率是否提升
- `signal_label` 的一致性是否提升
- `confidence_score` 的评分漂移是否下降
- 术语误判是否减少
- 无效上下文是否反而干扰了抽取

只有这一层成立，协议才算真正有效。

---

## 十一、当前阶段的结论

如果用一句话总结这份协议草案的核心思想，可以写成：

> **`2.4 -> 2.1` 不是“把检索结果交给解码模块”，而是“把可解释、可追溯、带用途标记的证据包交给解码模块”。**

因此，后续若要继续收口和迭代，建议围绕以下四个问题推进：

1. `ContextPacket` 的字段是否足够支撑 `2.1` 消费
2. `use_as` 分类是否足够清晰稳定
3. `2.1` 是否真正按用途消费而不是重新拼成散文本
4. 协议是否已经可以支持联合 benchmark 和误差分析

---

**文档状态**: ✅ 已完成  
**版本**: v0.1 Draft  
**建议下次更新时机**: 当 `2.4` 的真实输出协议、`2.1` 的字段冻结方案或联合 benchmark 口径发生变化时
