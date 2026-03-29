# Phase 2.4 进展与待拍板事项

> **文档类型**：模块进展文档
> **适用模块**：`Phase 2.4` 知识库与 RAG 系统
> **状态**：维护+按需增强阶段
> **最后更新**：2026-03-29

---

## 一、当前状态一句话

> Phase 2.4 主体工作已完成，已进入"维护 + 按需增强"状态。后续迭代随下游模块需求驱动，不作为独立大版本推进。

---

## 二、已完成事项（截至 2026-03-29）

### 2.1 核心能力

| 项目 | 完成时间 | 说明 |
|------|----------|------|
| RAG 系统骨架（API + 检索 + 生成） | 2026-03-13 | `/retrieve` `/generate` `/rag` `/health` `/documents` |
| 知识库文档 62 条（kb_001~kb_062） | 2026-03-28 | 全部标注 content_type，tags 干净 |
| 真实 Embedding 接入（MiniLM-L6-v2，384维） | 2026-03-22 | 本地 BERT 路径废弃，MiniLM 为正式方案 |
| FAISS 向量索引构建 | 2026-03-22 | vector_index_local.faiss + vector_meta_local.pkl |
| ContextPacket 协议冻结（v1.0） | 2026-03-28 | 见 PHASE2_4_CONTEXT_PACKET_PROTOCOL.md |
| `retrieve_context()` 分桶召回实现 | 2026-03-28 | 按 content_type 分桶，trust_level 过滤 |
| P1-5/P1-6/P1-7 联调完成（2.4→2.1/2.2/2.3） | 2026-03-22 | 接口契约验证通过 |
| 2.2 真实接入 ContextPacket | 2026-03-29 | run_batch_real.py 联调验证，8 条证据包命中，4 种 content_type |

### 2.2 本轮（2026-03-29）完成

| 项目 | 说明 |
|------|------|
| tags 质量修复 | 清除 kb_044~062 中混入的 content_type 枚举值；fix_tags.py 作为质检脚本保留 |
| 四层文档结构建立 | industry / category / content_type / tags 四层正交，语义无重叠 |
| industry 字段添加 | 62 条文档全部加 `industry: gaming`，为跨行业扩展预留结构 |
| MetadataFilter 重构 | ContextRequest 的 `category_filter` + `min_trust_level` 合并为 `MetadataFilter` dataclass |
| category 边界定义 | market_trend 明确包含"市场数据 + 行业事件"，写入 CATEGORY_VALUES 注释 |
| INDUSTRY_VALUES / CATEGORY_VALUES 枚举 | 加入 models.py，后续录入有校验依据 |
| 检索精度增强路线记录 | category_filter / 混合检索 / Scoping / Rerank 触发时机写入 PROJECT_CONTEXT |

---

## 三、文档结构规范（当前范本）

```yaml
id: kb_xxx
title: "..."
industry: gaming          # 行业标识；当前唯一值：gaming
category: market_trend    # 主题域：game_design / market_trend / tech_innovation
content_type: case_record # 内容性质：见 CONTENT_TYPE_VALUES 枚举
tags: ["公司名", "产品名", "地区", "技术名词"]  # 细粒度实体标签，不含 content_type/category/industry 值
metadata:
  source: "..."
  confidence: 0.90
  last_updated: "YYYY-MM-DD"
content: |
  ...
```

**字段边界（必须遵守）**：
- `content_type`：只用枚举值，**不放进 tags**
- `category`：只用枚举值，**不放进 tags**
- `industry`：只用枚举值，**不放进 tags**
- `tags`：只放实体类标签（公司/产品/地区/玩法类型/技术名词等）

**录入质检**：新文档录入后运行 `fix_tags.py`，输出"共修复 0 个文件"为合格。

---

## 四、知识库当前状态

| 维度 | 数值 |
|------|------|
| 文档总数 | 62 条 |
| 向量维度 | 384（MiniLM-L6-v2） |
| industry 分布 | gaming: 62 |
| category 分布 | market_trend: 28 / game_design: 19 / tech_innovation: 15 |
| content_type 分布 | background: 32 / case_record: 16 / market_data: 10 / few_shot_example: 2 / constraint_rule: 2 |

**已知缺口**：`constraint_rule` 和 `few_shot_example` 各 2 条，`background` 占比过高（52%）。对 2.2/2.3 判断质量影响最直接的 `case_record + market_data` 合计 26 条。

---

## 五、待完成事项（按触发时机排序）

| 项目 | 触发时机 | 优先级 |
|------|---------|--------|
| 知识库内容来源模块 | 知识库扩充工作量超过手动可维护边界 | 后续规划 |
| 补充 case_record / market_data 文档 | 下游反馈证据包命中质量不足 | 按需 |
| category_filter 实现 | 知识库扩展至多个垂直行业且下游反馈跨行业噪音 | 结构已预留，未触发不实现 |
| 混合检索（BM25 + 向量） | 发现专有名词向量召回效果差 | 未触发 |
| Scoping / Query Routing / Query Transformation | 多模块接入后 query 与知识子集出现系统性错配 | 未触发 |
| Rerank（可插拔层） | 分桶召回稳定后 top-k 排序成为瓶颈 | 未触发 |
| 增益联合验证（2.4 → 2.1/2.2/2.3） | 下游模块迭代稳定后 | 最终验收终点 |

---

## 六、关键设计拍板记录

| 时间 | 决策 |
|------|------|
| 2026-03-28 | ContextPacket v1.0 协议冻结；`content_type` 替代 `use_as`（描述内容性质，不预判用途） |
| 2026-03-28 | content_type 枚举：glossary / few_shot_example / constraint_rule / case_record / market_data / background |
| 2026-03-28 | Embedding 方案：MiniLM-L6-v2（384维），本地 BERT 路径废弃 |
| 2026-03-29 | 四层文档结构（industry / category / content_type / tags）正式确立 |
| 2026-03-29 | MetadataFilter 替代 category_filter：按维度弹性过滤，不绑定特定层 |
| 2026-03-29 | category_filter 触发条件：跨行业扩展后，当前不实现 |
| 2026-03-29 | 知识库内容来源模块：列入后续规划，独立模块，不依赖手动维护 |

---

## 七、关键文件索引

| 文件 | 用途 |
|------|------|
| `PHASE2_4_CONTEXT_PACKET_PROTOCOL.md` | ContextPacket v1.0 协议规范（已冻结） |
| `PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md` | 第一性原理与设计指导（长期有效） |
| `PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md` | ⚠️ 已废弃旧草案，不作为设计依据 |
| `rag_system/core/models.py` | 数据模型定义（含所有枚举常量） |
| `rag_system/core/retrieval.py` | 检索核心，含 `retrieve_context()` 分桶召回 |
| `rag_system/fix_tags.py` | tags 质检脚本 |
| `rag_system/add_industry_field.py` | 批量添加 industry 字段脚本 |
| `rag_system/data/documents/` | 62 条知识文档（yaml） |
