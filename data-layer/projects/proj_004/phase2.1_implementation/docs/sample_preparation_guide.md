# Phase 2.1 样本准备指南

> **文档类型**：样本收集与准备操作指南
> **目标读者**：负责准备 benchmark 样本的人员
> **最后更新**：2026-03-14

---

## 一、为什么人工准备更好？

### 1.1 人工准备的优势

**质量可控**：
- ✅ 可以精确控制样本的信号类型分布
- ✅ 可以有意识地包含边界样本和负例
- ✅ 可以确保样本覆盖典型场景

**真实性强**：
- ✅ 基于真实游戏行业新闻，更有说服力
- ✅ 能够反映实际使用场景
- ✅ 避免合成样本的"过于理想化"问题

**标注准确**：
- ✅ 收集者对样本有深入理解
- ✅ 标注时更容易判断信号边界
- ✅ 减少标注歧义

### 1.2 合成样本的局限

**过于理想化**：
- ❌ 可能过度拟合 few-shot 样例
- ❌ 缺少真实文本的复杂性（如冗余信息、模糊表述）
- ❌ 难以覆盖边界情况

**泛化能力弱**：
- ❌ 系统在合成样本上表现好，不代表真实场景也好
- ❌ 可能遗漏真实场景中的常见错误模式

---

## 二、样本准备的内容要求

### 2.1 样本数量与分布（严格要求）

| 维度 | 要求 | 说明 |
|------|------|------|
| **总数量** | 30 条 | 不多不少，平衡代表性与效率 |
| **输入类型** | news 10 + report 10 + announcement 10 | 覆盖三类输入源 |
| **信号类型** | technical 8 + market 8 + team 7 + capital 7 | 四类信号均衡分布 |
| **样本质量** | 正例 24-26 + 边界 2-3 + 负例 1-2 | 测试系统的区分能力 |

### 2.2 样本内容要求

#### A. 正例样本（24-26 条）

**必须满足**：
- ✅ 包含明确的范式信号（technical/market/team/capital）
- ✅ 证据充分，不模糊
- ✅ 文本长度适中（100-500 字）
- ✅ 覆盖典型场景

**典型场景示例**：

**Technical 信号**：
- 引擎升级（Unity → UE5）
- 跨平台发布（PC → 主机/移动端）
- 新技术采用（光追、AI 生成内容）
- 技术创新（自研引擎、新工具链）

**Market 信号**：
- 品类趋势（Roguelike 增长、开放世界流行）
- 用户需求变化（多人联机需求上升）
- 竞品动态（竞品发布、市场份额变化）
- 市场数据（销量、增长率）

**Team 信号**：
- 核心人才加入（前 3A 制作人加入）
- 团队扩张（招聘规模、新工作室）
- 组织架构调整（新部门、合并）
- 关键人员离职

**Capital 信号**：
- 融资（种子轮、A/B/C 轮）
- 收购（被收购、收购其他公司）
- 投资（战略投资、财务投资）
- 财务数据（营收、利润）

#### B. 边界样本（2-3 条）

**特点**：
- ⚠️ 信号存在但模糊
- ⚠️ 证据不够充分
- ⚠️ 用于测试 confidence_score 的区分度

**示例**：
```
"市场传闻某公司正在洽谈新一轮融资，但官方尚未确认"
→ capital 信号，但 confidence_score 应该很低（2-3 分）

"游戏可能支持跨平台"
→ technical 信号，但不确定，confidence_score 较低

"据内部人士透露，团队正在扩张"
→ team 信号，但来源不可靠
```

#### C. 负例样本（1-2 条）

**特点**：
- ❌ 无范式信号
- ❌ 纯营销软文或无实质内容
- ❌ 用于测试是否会误报

**示例**：
```
"游戏画面精美，玩法有趣，深受玩家喜爱。敬请期待后续消息。"
→ 无信号

"这是一款值得期待的作品，我们将持续关注。"
→ 无信号
```

---

## 三、样本准备的形式要求

### 3.1 样本文件格式

**推荐格式**：JSON 文件

```json
{
  "samples": [
    {
      "sample_id": "sample_001",
      "source_type": "news",
      "title": "某游戏工作室宣布技术升级",
      "content": "某知名独立游戏工作室今日宣布，其正在开发的新项目将从 Unity 引擎迁移到 Unreal Engine 5...",
      "published_at": "2026-03-14T10:00:00Z",
      "source_name": "游戏资讯网",
      "source_url": "https://example.com/news/001",
      "annotation": {
        "expected_signals": [
          {
            "signal_type": "technical",
            "signal_label": "引擎迁移至 UE5",
            "description": "项目从 Unity 迁移到 Unreal Engine 5",
            "intensity_score": 8,
            "confidence_score": 10,
            "timeliness_score": 9,
            "entities": ["Unity", "Unreal Engine 5", "Nanite", "Lumen"]
          }
        ]
      }
    }
  ]
}
```

### 3.2 必填字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sample_id` | string | ✅ | 样本唯一 ID，如 sample_001 |
| `source_type` | string | ✅ | news / report / announcement |
| `title` | string | ⚠️ | 标题（可选，但建议填写） |
| `content` | string | ✅ | 正文内容 |
| `published_at` | string | ⚠️ | 发布时间（影响 timeliness_score） |
| `source_name` | string | ⚠️ | 来源名称 |
| `source_url` | string | ⚠️ | 原文链接（如果是真实样本） |
| `annotation` | object | ✅ | 人工标注结果 |

### 3.3 标注字段说明

**annotation 结构**：
```json
{
  "expected_signals": [
    {
      "signal_type": "technical|market|team|capital",
      "signal_label": "信号标签",
      "description": "信号描述",
      "intensity_score": 1-10,
      "confidence_score": 1-10,
      "timeliness_score": 1-10,
      "entities": ["实体1", "实体2"]
    }
  ]
}
```

**注意**：
- `expected_signals` 是数组，一条样本可能包含多个信号
- 如果是负例，`expected_signals` 为空数组 `[]`

---

## 四、样本准备的实施步骤

### 步骤 1：确定样本来源（30 分钟）

**推荐来源**：

**游戏行业新闻网站**：
- GameLook（中文）
- 游戏葡萄（中文）
- VentureBeat（英文）
- GamesIndustry.biz（英文）

**行业报告**：
- Newzoo 游戏市场报告
- Sensor Tower 数据报告
- 伽马数据报告

**公司公告**：
- 游戏公司官网
- 投资机构公告
- 招聘网站（团队扩张信号）

**搜索关键词建议**：
- Technical: "引擎升级"、"UE5"、"跨平台"、"技术创新"
- Market: "市场趋势"、"品类增长"、"Roguelike"、"销量"
- Team: "加入"、"制作人"、"团队扩张"、"招聘"
- Capital: "融资"、"收购"、"投资"、"A 轮"

### 步骤 2：收集原始样本（2-3 小时）

**操作流程**：

1. **按信号类型收集**：
   - Technical: 收集 10-12 条候选
   - Market: 收集 10-12 条候选
   - Team: 收集 8-10 条候选
   - Capital: 收集 8-10 条候选

2. **按输入类型分类**：
   - 将收集的样本按 news/report/announcement 分类
   - 确保每类至少 10 条

3. **筛选与去重**：
   - 去除重复或过于相似的样本
   - 优先选择典型、清晰的样本

4. **补充边界样本和负例**：
   - 有意识地寻找 2-3 条模糊信号
   - 收集 1-2 条营销软文作为负例

### 步骤 3：文本预处理（1 小时）

**操作**：

1. **脱敏处理**（如果需要）：
   - 替换真实公司名为"某游戏工作室"
   - 替换真实人名为"某制作人"
   - 保留关键信息（如"前暴雪"、"UE5"）

2. **长度控制**：
   - 保留核心信息，去除冗余
   - 目标长度：100-500 字
   - 过长的报告可以截取关键段落

3. **格式统一**：
   - 去除多余空格、换行
   - 统一标点符号

### 步骤 4：人工标注（3-4 小时）

**操作流程**：

1. **先标注 5 条样本**：
   - 选择 5 条典型样本
   - 按照标注规范完成标注
   - 自我检查标注一致性

2. **标注剩余 25 条**：
   - 按照统一口径标注
   - 记录标注时间
   - 标记不确定的样本

3. **标注检查**：
   - 检查信号类型分布是否符合要求
   - 检查评分是否合理
   - 检查是否包含边界样本和负例

### 步骤 5：整理成 JSON 文件（30 分钟）

**操作**：

1. **创建 JSON 文件**：
   - 文件名：`benchmark_samples.json`
   - 位置：`phase2.1_implementation/data/`

2. **填充数据**：
   - 按照格式要求填充每条样本
   - 确保 JSON 格式正确

3. **验证**：
   - 使用 JSON 校验工具检查格式
   - 确认样本数量和分布

---

## 五、质量检查清单

### 5.1 数量检查

- [ ] 总数量：30 条
- [ ] news: 10 条
- [ ] report: 10 条
- [ ] announcement: 10 条
- [ ] technical 信号: 8 个
- [ ] market 信号: 8 个
- [ ] team 信号: 7 个
- [ ] capital 信号: 7 个
- [ ] 边界样本: 2-3 条
- [ ] 负例样本: 1-2 条

### 5.2 质量检查

- [ ] 所有样本都有明确的 sample_id
- [ ] 所有样本都有 content 字段
- [ ] 所有样本都有 annotation 字段
- [ ] 正例样本的信号清晰、证据充分
- [ ] 边界样本的模糊性明确
- [ ] 负例样本确实无信号
- [ ] 评分符合评分口径
- [ ] 样本长度适中（100-500 字）

### 5.3 多样性检查

- [ ] 样本覆盖不同的表述方式
- [ ] 样本不与 few-shot 样例过于相似
- [ ] 样本覆盖典型场景
- [ ] 样本包含不同的信号强度（弱/中/强）

---

## 六、常见问题

### Q1：如果找不到足够的真实样本怎么办？

**A**：可以采用混合方式
- 优先收集真实样本（目标 70%，即 21 条）
- 补充合成样本（30%，即 9 条）
- 合成样本应基于真实场景，避免过于理想化

### Q2：如何判断一条样本是否合适？

**A**：满足以下条件即可
- ✅ 信号明确（或明确无信号）
- ✅ 证据充分
- ✅ 长度适中
- ✅ 不与 few-shot 样例雷同

### Q3：标注时如何确定评分？

**A**：严格按照评分口径
- 参考 `schemas.py` 中的 `SCORING_CRITERIA`
- 参考标注规范中的示例
- 如果不确定，标记为"待讨论"

### Q4：是否需要包含多信号样本？

**A**：可以包含，但不强制
- MVP 阶段优先测试单信号样本
- 如果有合适的多信号样本，可以包含 1-2 条
- 标注时需要标记所有信号

### Q5：样本的时效性如何处理？

**A**：
- 优先使用近期样本（<6 个月）
- 如果使用旧样本，需要在 `published_at` 字段标明
- timeliness_score 应基于发布时间判断

---

## 七、样本准备模板

### 7.1 JSON 模板

```json
{
  "samples": [
    {
      "sample_id": "sample_001",
      "source_type": "news",
      "title": "标题",
      "content": "正文内容...",
      "published_at": "2026-03-14T10:00:00Z",
      "source_name": "来源名称",
      "source_url": "https://example.com",
      "annotation": {
        "expected_signals": [
          {
            "signal_type": "technical",
            "signal_label": "信号标签",
            "description": "信号描述",
            "intensity_score": 8,
            "confidence_score": 10,
            "timeliness_score": 9,
            "entities": ["实体1", "实体2"]
          }
        ]
      }
    }
  ]
}
```

### 7.2 Excel 模板（可选）

如果更习惯使用 Excel，可以先用 Excel 整理，再转换为 JSON：

| sample_id | source_type | title | content | signal_type | signal_label | intensity | confidence | timeliness |
|-----------|-------------|-------|---------|-------------|--------------|-----------|------------|------------|
| sample_001 | news | ... | ... | technical | UE5 升级 | 8 | 10 | 9 |

---

## 八、相关文档

- Benchmark 验收指南：[benchmark_validation_guide.md](benchmark_validation_guide.md)
- 标注规范：[annotation_guidelines.md](annotation_guidelines.md)
- 评分口径：[../schemas.py](../schemas.py) 中的 `SCORING_CRITERIA`