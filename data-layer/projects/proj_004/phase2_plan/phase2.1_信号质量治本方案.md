# Phase 2.1 信号质量治本方案设计

> **文档类型**：设计方案
> **状态**：⏳ 待拍板
> **提出日期**：2026-04-01
> **作者**：助理
> **关联模块**：phase2.1_implementation/decoder.py、prompt_templates.py

---

## 一、问题描述

### 1.1 现状

2.1 解码器由 LLM 自由生成信号字段（`signal_type`、`intensity_score`、`confidence_score`、`timeliness_score`），`_post_process()` 仅做 JSON 解析和格式规范化，**不做任何语义校验**。

```
原文 → LLM prompt → JSON 输出 → _post_process()（解析/去重）→ DecodedIntelligence
```

### 1.2 核心问题

**打分虚高，无语义锚点**

- LLM 自由打分没有后验约束，容易虚高
- 今日验证（2026-04-01）观察到：intensity 3-4 分的信号，2.2 LLM 仍能判断成机会，说明打分失去了区分意义
- 典型表现：传言类信号打出 6-7 分，官方公告类信号也是 6-7 分，区分度为零

**signal_type 分类随意**

- Step B 跨批次检索靠 `signal_type` 互补来匹配历史伙伴
- 如果 `signal_type` 打错（如把 `capital` 打成 `market`），跨批次检索漏掉或误匹配

**没有"打分理由"字段**

- 无法验证 LLM 为什么给这个分
- Prompt 编辑器（后续功能）无从调试

### 1.3 问题边界（不在本方案范围内）

- 2.1 Prompt few-shot 本身的质量（已经是 v1.6，不动）
- 2.2 LLM 判断逻辑过于宽松（是独立问题，后续 Prompt 编辑器功能处理）
- 2.1 召回率（不做收紧，只做标准化）

---

## 二、治本方向

在 2.1 的 `_post_process()` 后，增加一层**后验结构化校验与标准化**（`_normalize_signals()`），核心做三件事：

| 目标 | 手段 | 改动范围 |
|------|------|---------|
| signal_type 强枚举校验 | 白名单检查，不在枚举内的拒绝或归类 | decoder.py |
| 打分加锚点约束 | 规则约束（见下），不符合的截断/调整 | decoder.py |
| 新增 score_rationale 字段 | 要求 LLM 在 JSON 中输出打分理由（可选字段） | prompt_templates.py + decoder.py |

---

## 三、方案详情

### 3.1 signal_type 强枚举校验

**规则**：
```
允许值：technical / market / team / capital / regulatory
若 LLM 输出不在白名单 → 记录 warning，该信号丢弃（不进入后续）
```

**理由**：signal_type 是 Step B 匹配的 key，错误值比空值危害更大（会导致误匹配）。

---

### 3.2 打分锚点约束（规则层截断）

打分约束基于"证据类型"，规则如下：

#### intensity_score 约束

| 条件 | 约束 |
|------|------|
| `confidence_score ≤ 3`（传言/推断） | `intensity_score` 上限截断为 5 |
| `evidence_text` 字段为空或 < 20 字 | `intensity_score` 上限截断为 4 |
| `confidence_score ≤ 5` 且 `intensity_score ≥ 8` | `intensity_score` 截断为 7，记录 warning |

**设计意图**：阻止"传言打高 intensity"（如"据悉苹果正在研究..."`intensity=8`），让 intensity 和 confidence 之间有结构性约束。

#### confidence_score 约束

在 `_post_process` 已有的语义之外，加以下规则校验（不自动改分，只记 warning）：

| 条件 | 处理 |
|------|------|
| `evidence_text` 含 "据悉"/"传言"/"可能"/"或将"/"预计" 等措辞 | 若 `confidence_score ≥ 7`，记录 warning（提示 LLM 可能虚高） |
| `evidence_text` 含 "官方"/"正式"/"宣布"/"公告" 等措辞 | 若 `confidence_score ≤ 4`，记录 warning（提示 LLM 可能虚低） |

**注**：confidence_score 约束只记 warning，不自动改分——因为有时 LLM 有合理理由给低分（如官方公告但信息量极小），不宜强制覆盖。

#### timeliness_score 约束

暂不加规则约束，timeliness 是相对时间判断，规则难以表达。后续 Prompt 编辑器功能中可让用户手动调整。

---

### 3.3 新增 score_rationale 字段（可选）

在 prompt schema 中新增可选字段 `score_rationale`：

```json
{
  "signal_id": "...",
  "signal_type": "...",
  ...
  "intensity_score": 7,
  "confidence_score": 8,
  "score_rationale": "官方公告，金额明确（500万），属于已完成事件；intensity偏高因为涉及头部基金领投"
}
```

- 字段为**可选**：LLM 不输出时不报错，`_post_process` 中 `setdefault("score_rationale", "")` 兜底
- 主要价值：为 Prompt 编辑器（P3 功能）提供可视化调试入口
- 不影响任何现有评分逻辑，纯增量字段

---

## 四、实现方案

### 4.1 改动文件

| 文件 | 改动内容 |
|------|---------|
| `decoder.py` | 新增 `_normalize_signals()` 方法，在 `_post_process()` 之后调用 |
| `prompt_templates.py` | schema 中新增 `score_rationale` 可选字段，PROMPT_VERSION → v1.7 |

**不改动**：`schemas.py`（Signal schema 新增 `score_rationale: Optional[str]` 字段）、2.2/2.3 下游（纯增量，无 breaking change）

### 4.2 decoder.py 改动位置

```python
# _post_process 末尾，return unique_signals 之前调用
unique_signals = self._normalize_signals(unique_signals, warnings)
return unique_signals
```

`_normalize_signals` 逻辑：
```python
def _normalize_signals(self, signals, warnings):
    VALID_TYPES = {"technical", "market", "team", "capital", "regulatory"}
    result = []
    for sig in signals:
        # 1. signal_type 强校验
        if sig.get("signal_type") not in VALID_TYPES:
            warnings.append(f"[normalize] 非法 signal_type={sig.get('signal_type')}，丢弃信号 {sig.get('signal_id')}")
            continue

        # 2. intensity / confidence 联动约束（截断，不丢弃）
        confidence = sig.get("confidence_score", 5)
        intensity  = sig.get("intensity_score", 5)
        evidence   = sig.get("evidence_text", "")

        if confidence <= 3 and intensity > 5:
            warnings.append(f"[normalize] {sig.get('signal_id')}: confidence≤3 但 intensity={intensity}，截断至5")
            sig["intensity_score"] = 5

        if len(evidence) < 20 and intensity > 4:
            warnings.append(f"[normalize] {sig.get('signal_id')}: evidence_text 过短，intensity 截断至4")
            sig["intensity_score"] = 4

        if confidence <= 5 and intensity >= 8:
            warnings.append(f"[normalize] {sig.get('signal_id')}: confidence≤5 但 intensity≥8，截断至7")
            sig["intensity_score"] = 7

        # 3. confidence 措辞一致性 warning（不改分）
        UNCERTAIN_WORDS = ["据悉", "传言", "可能", "或将", "预计", "据报道", "消息称"]
        CERTAIN_WORDS   = ["官方", "正式", "宣布", "公告", "确认", "发布"]
        for word in UNCERTAIN_WORDS:
            if word in evidence and confidence >= 7:
                warnings.append(f"[normalize] {sig.get('signal_id')}: evidence含'{word}'但 confidence={confidence}，请核查")
        for word in CERTAIN_WORDS:
            if word in evidence and confidence <= 4:
                warnings.append(f"[normalize] {sig.get('signal_id')}: evidence含'{word}'但 confidence={confidence}，请核查")

        # 4. score_rationale 兜底
        sig.setdefault("score_rationale", "")
        result.append(sig)
    return result
```

### 4.3 prompt_templates.py 改动

schema 段新增可选字段（在 `timeliness_score` 之后）：
```json
"score_rationale": "string（可选）：简述打分理由，例如'官方公告+具体金额，intensity偏高因头部机构背书'"
```

PROMPT_VERSION 从 `v1.6` 升级到 `v1.7`，PROMPT_CHANGELOG 新增 v1.7 记录。

---

## 五、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| intensity 截断导致本来合理的高分信号被压低 | 中 | 中 | 截断规则加 warning 日志，可通过 dashboard 观察；后续 Prompt 编辑器可调整阈值 |
| score_rationale 字段 LLM 不输出（输出空） | 高 | 低 | `setdefault("score_rationale", "")` 兜底，不影响任何下游逻辑 |
| _normalize 改分后与 LLM 原始意图冲突 | 低 | 低 | 所有改分操作都记 warning，可追溯；调试时对比 warning 日志 |
| 2.1 通过率（has_signal 为 True 的比例）下降 | 低 | 低 | normalize 只做 intensity 截断，不做信号丢弃（除非 signal_type 非法），通过率不受影响 |

---

## 六、验收标准

| 验收项 | 方法 |
|--------|------|
| signal_type 非法值被丢弃并记 warning | 构造一条 `signal_type: "policy"` 的信号，验证被过滤 |
| confidence≤3 + intensity>5 → 截断为5 | 构造对应测试用例，验证 normalize 后 intensity=5 |
| evidence_text<20字 + intensity>4 → 截断为4 | 构造测试用例 |
| score_rationale 字段存在（LLM 不输出时为空字符串） | 跑现有冒烟测试，验证字段存在 |
| 现有 2.1 冒烟/benchmark 通过率不下降 | 跑现有测试集，对比改动前后 |

---

## 七、待拍板事项

| # | 拍板项 | 建议 |
|---|--------|------|
| 1 | intensity 截断阈值是否合适（confidence≤3 → intensity 上限5）| 建议先用此阈值跑一轮，按 warning 日志反馈调整 |
| 2 | score_rationale 字段是否加入 prompt schema（token 增加约10-20%）| 建议加，为 Prompt 编辑器打基础；可在 llm_config.yaml 中设开关 |
| 3 | 本方案是否影响现有 benchmark 精度（需重跑验证）| 建议实现后跑完整 benchmark 对比，不跑完不合入主分支 |

---

**文档状态**：v1.0 草稿，待拍板
**最后更新**：2026-04-01
