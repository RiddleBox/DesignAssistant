# 样本收集模块（Sample Ingestion Module）设计方案

> **文档类型**：独立模块设计方案
> **创建日期**：2026-04-03
> **状态**：📝 设计完成，待实现
> **定位**：过渡模块（当前阶段 = knowledge-base 适配器）；面向未来 = 可独立运行的情报采集/存储系统
> **硬约束**：不改核心模块（phase2.1 / 2.2 / run_batch_real.py / 主链路任何文件）

---

## 0. 背景与定位

### 当前阶段目标（MVP）
让 `run_batch_real.py → 2.1 decoder` 持续获得真实样本输入。
第一阶段数据来源：`game-knowledge-base/00-Inbox/*.md`（已有 1000+ 条，每日自动追加）。

### 未来演进方向
本模块设计为**可扩展的独立情报采集/存储系统**，未来可以：
- 接入更多 Provider（RSS 直接订阅、API、自建爬虫、人工录入）
- 维护自己的持久化 Sample Store（不依赖 `incoming/` 目录）
- 支持独立运行，脱离 DesignAssistant 主项目

因此架构必须为"先当适配器，后当独立系统"留好扩展点。

---

## 1. 模块边界（codebuddy 硬约束）

| 允许 | 禁止 |
|------|------|
| 新增 `ingestion/` 模块目录 | 改 `phase2.1_implementation/` 任何文件 |
| 读取外部源，输出 JSON 到 `incoming/` | 改 `phase2.2_implementation/` 任何文件 |
| 新增 `ingestion/manifest/` 审计记录 | 改 `run_batch_real.py` |
| 新增 `ingestion/quarantine/` 失败隔离 | 改现有 `incoming/ → processed/` 状态流转逻辑 |
| 新增扩展字段（`ingestion_meta`） | 改变任何核心字段语义 |

---

## 2. 输出契约（兼容现有 2.1 输入）

输出到 `background/real_intel_samples/incoming/` 的 JSON 文件，**必须**包含：

```json
{
  "source_id": "incoming_123",
  "source_type": "news",
  "title": "string",
  "content": "string（事实摘要，不含人工判断）",
  "published_at": "2026-03-20T00:00:00Z",
  "source_name": "ChuApp",
  "source_url": "https://...",
  "language": "zh",
  "mode": "prompt_first"
}
```

**扩展字段**（可选，不影响核心链路）：
```json
{
  "ingestion_meta": {
    "provider": "knowledge_base_inbox",
    "origin_file": "00-Inbox/2026-04-03/[market] xxx.md",
    "signal_type_hint": "market",
    "crawler_batch_id": "kb-2026-04-03",
    "raw_tags": ["inbox", "market"],
    "editor_notes": "（用户在 '我的判断' 区域写的内容，若有）"
  }
}
```

**禁止**：把用户"我的判断"部分的内容混入 `content` 字段。

---

## 3. 架构设计：三层解耦

```
┌─────────────────────────────────────────────────────────┐
│              Sample Ingestion Module                     │
│                                                         │
│  ┌──────────────────┐                                   │
│  │  ProviderAdapter │  读取外部数据源，返回 RawRecord     │
│  │  (可插拔)        │  当前实现：KnowledgeBaseAdapter    │
│  │                  │  未来扩展：RSSAdapter / APIAdapter  │
│  └────────┬─────────┘                                   │
│           │ List[RawRecord]                              │
│  ┌────────▼─────────┐                                   │
│  │   Normalizer     │  字段映射 + 清洗 + 去重             │
│  │                  │  → List[NormalizedRecord]          │
│  └────────┬─────────┘                                   │
│           │ List[NormalizedRecord]                       │
│  ┌────────▼─────────┐                                   │
│  │    Exporter      │  Schema 校验 + 落盘 / quarantine   │
│  │                  │  → incoming/*.json + manifest      │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
          │
          ▼
background/real_intel_samples/incoming/
```

### 3.1 RawRecord（Provider 层内部结构，不对外暴露）

```python
@dataclass
class RawRecord:
    raw_title: str
    raw_content: str           # 摘要区（不含"我的判断"）
    raw_date: str              # 原始日期字符串，格式不保证
    raw_source: str            # frontmatter 里的 source 字段
    raw_url: str               # 从 md 正文解析的原文链接
    raw_signal_type: str       # frontmatter signal_type
    raw_tags: list[str]
    origin_file: str           # 相对路径，用于去重和审计
    editor_notes: str          # "我的判断"内容，若有
    language: str              # 推断：zh / en
```

### 3.2 NormalizedRecord（Normalizer 输出，Exporter 消费）

```python
@dataclass
class NormalizedRecord:
    source_id: str             # 生成规则见下
    source_type: str           # signal_type → source_type 映射
    title: str
    content: str               # 只含事实摘要
    published_at: str          # ISO 8601
    source_name: str
    source_url: str
    language: str
    mode: str                  # 固定 "prompt_first"
    ingestion_meta: dict
```

---

## 4. 关键实现细节

### 4.1 source_id 生成规则

格式：`incoming_{YYYYMMDD}_{seq:03d}`
- 日期取 `published_at` 日期部分
- seq 在单次 batch 内递增（不跨 batch 累计）
- 不依赖文件名（文件名含特殊字符，不稳定）

### 4.2 source_type 映射

| Inbox 文件名前缀 / signal_type | → source_type |
|-------------------------------|---------------|
| capital                       | news          |
| market                        | news          |
| technical                     | news          |
| regulatory                    | news          |
| team                          | news          |
| 其他 / 未识别                  | news（默认）  |

> 备注：当前 2.1 decoder 的 source_type 语义是"数据类型"而非"领域"，统一用 `news` 是正确的。
> `signal_type_hint` 保留在 `ingestion_meta` 中，供未来 decoder 参考。

### 4.3 去重策略（三级）

```
一级（主键）：source_url（非空时优先）
二级（备用）：normalize(title) + date(YYYY-MM-DD) + source_name
三级（兜底）：正文前 200 字的 MD5
```

- **同文章重复导入** → 去重（写 manifest 记录 skipped）
- **同事件多源报道** → 保留（多源 corroboration 有价值）
  - 判定标准：source_url 不同 = 不同来源，即使标题相似也保留

去重状态持久化在：`ingestion/manifest/dedup_index.json`

### 4.4 日期解析

按优先级尝试：
1. frontmatter `date` 字段（格式 `YYYY-MM-DD`）
2. 文件名中的日期片段（`\d{4}-\d{2}-\d{2}`）
3. 父目录名（`00-Inbox/2026-04-03/`）
4. 兜底：采集时间（当前时间，标记 `inferred: true`）

统一输出 ISO 8601：`2026-04-03T00:00:00Z`

### 4.5 content 处理策略（A 方案）

按 codebuddy 建议，采用 A 方案：
- `content` = MD 文件中 `## 摘要` 区域的正文（纯事实，不含编辑意见）
- `## 我的判断` 区域内容 → `ingestion_meta.editor_notes`（若为空模板则留空）
- 不抓全文（避免污染 decoder 输入）
- 摘要区清理：去掉 Markdown 格式符，保留纯文本

### 4.6 失败隔离

解析失败的条目不静默丢弃，写入：
```
ingestion/quarantine/{run_id}_rejects.jsonl
```

每条 reject 记录：
```json
{
  "origin_file": "...",
  "reason": "missing_content | missing_url | invalid_date | ...",
  "raw_title": "...",
  "timestamp": "..."
}
```

---

## 5. CLI 接口

```bash
python -m ingestion.cli [--provider kb] [--date YYYY-MM-DD] [--mode dry-run|validate|export]

# 参数说明
--provider kb        # 当前唯一实现：knowledge_base_inbox
--date 2026-04-03    # 只处理指定日期的 Inbox（默认：昨天）
--date-range 2026-03-24:2026-04-03   # 批量历史导入
--mode dry-run       # 只打印会导入什么，不落盘
--mode validate      # 检查输入解析 + 输出 schema 合规，不落盘
--mode export        # 正式写入 incoming/（默认）
--limit N            # 单次最多导出 N 条（用于测试）
--force-reimport     # 跳过去重检查（危险，仅用于调试）
```

输出示例（dry-run）：
```
[DRY RUN] 2026-04-03: 84 files found
  → 72 parseable
  → 8 skipped (dedup: source_url match)
  → 4 quarantined (missing_content: 3, invalid_date: 1)
  → 60 would export to incoming/
```

---

## 6. 目录结构

```
data-layer/projects/proj_004/
└── ingestion/                          ← 新增模块（不改任何现有目录）
    ├── __init__.py
    ├── cli.py                          ← 入口
    ├── models.py                       ← RawRecord / NormalizedRecord dataclass
    ├── normalizer.py                   ← 字段映射、清洗、去重
    ├── exporter.py                     ← schema 校验、写 incoming/、写 manifest
    ├── providers/
    │   ├── __init__.py
    │   ├── base.py                     ← ProviderAdapter 抽象基类
    │   └── knowledge_base.py           ← KnowledgeBaseAdapter（当前唯一实现）
    ├── manifest/
    │   ├── dedup_index.json            ← 去重持久化索引（source_url/hash → source_id）
    │   └── runs/
    │       └── {run_id}.json           ← 每次运行的审计记录
    └── quarantine/
        └── {run_id}_rejects.jsonl      ← 解析失败隔离
```

---

## 7. ProviderAdapter 抽象接口（扩展点）

```python
from abc import ABC, abstractmethod
from ingestion.models import RawRecord

class ProviderAdapter(ABC):
    """
    所有数据来源适配器的抽象基类。
    未来新增数据源只需实现此接口，不改其他任何代码。
    """

    @abstractmethod
    def fetch(self, **kwargs) -> list[RawRecord]:
        """
        拉取数据，返回 RawRecord 列表。
        kwargs 由各 Provider 自行定义（如 date、date_range、limit 等）。
        """
        ...

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Provider 唯一标识，写入 ingestion_meta.provider"""
        ...
```

**已规划的未来 Provider（不在本阶段实现）**：
- `RSSAdapter`：直接订阅 RSS feed，不依赖 knowledge-base
- `ManualAdapter`：读取人工整理的 CSV/Excel 并转换
- `APIAdapter`：对接第三方新闻 API（GamesIndustry、Gamasutra 等）
- `SampleStoreAdapter`：从未来的独立 Sample Store 中读取

---

## 8. KnowledgeBaseAdapter 实现要点

**输入**：`D:\AIproject\game-knowledge-base\00-Inbox\{date}\*.md`

**Frontmatter 字段映射**：
```
signal_type  → RawRecord.raw_signal_type
source       → RawRecord.raw_source
date         → RawRecord.raw_date
status       → （仅用于过滤：只处理 status=inbox 的文件）
tags         → RawRecord.raw_tags
```

**正文解析规则**：
```
# {title}           → raw_title
[原文链接](url)      → raw_url
## 摘要\n{text}     → raw_content（摘要正文）
## 我的判断\n{text} → editor_notes（人工判断，不进 content）
```

**语言推断**：
- 存在中文字符（\u4e00-\u9fff 占比 > 10%）→ `zh`
- 否则 → `en`

**配置（不硬编码路径）**：
```yaml
# ingestion/config.yaml
providers:
  knowledge_base:
    inbox_root: "D:/AIproject/game-knowledge-base/00-Inbox"
    # 未来改路径只改这里
```

---

## 9. Manifest 审计记录

每次运行产生一条 `manifest/runs/{run_id}.json`：
```json
{
  "run_id": "kb-20260403-143022",
  "provider": "knowledge_base_inbox",
  "mode": "export",
  "date_processed": "2026-04-03",
  "stats": {
    "scanned": 84,
    "parseable": 72,
    "dedup_skipped": 8,
    "quarantined": 4,
    "exported": 60
  },
  "exported_files": ["incoming_20260403_001.json", "..."],
  "quarantine_file": "quarantine/kb-20260403-143022_rejects.jsonl",
  "timestamp": "2026-04-03T14:30:22Z"
}
```

---

## 10. 未来演进路径（扩展备忘）

```
当前阶段（MVP）
  └── KnowledgeBaseAdapter → Normalizer → Exporter → incoming/*.json

阶段 2（独立采集）
  ├── 新增 RSSAdapter（直接订阅，脱离 knowledge-base）
  ├── 新增 ManualAdapter
  └── Exporter 继续输出到 incoming/（接口不变）

阶段 3（独立存储，完全解耦）
  ├── 新增 SampleStore（自己的持久化层，类似 SignalStore）
  ├── Exporter 支持双写：incoming/ + SampleStore
  └── run_batch_real.py 可选择从 SampleStore 读取（需主项目配合）
```

---

## 11. 拍板结论摘要

| 决策点 | 结论 |
|--------|------|
| 第一阶段数据来源 | `game-knowledge-base/00-Inbox/*.md` |
| content 内容策略 | 只放摘要区事实，不含人工判断 |
| source_type 映射 | 统一 `news`，signal_type 保留在 ingestion_meta |
| 去重主键 | source_url 优先，title+date+source 次之 |
| 多源报道处理 | 保留（不去重） |
| 状态机制 | 不自建 processed 机制，只维护 manifest 审计 |
| CLI 模式 | dry-run / validate / export 三档 |
| 路径配置 | config.yaml，不硬编码 |
