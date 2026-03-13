## 资料映射表

该文件用于把 `proj_004` 中常见的接手问题，映射到最应该优先阅读的资料位置，减少在大量文档之间来回查找的成本。

---

## 一、问题 -> 首选资料

| 想回答的问题 | 首选资料 | 备用资料 |
|---|---|---|
| 项目现在进行到哪里？ | [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md) | `phase2_plan/` 当前子阶段文档 |
| 这个项目为什么存在？ | [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“项目定位 / 背景来源 / 项目目标”章节 | `background/thoughts/项目需求澄清.txt` |
| 项目要证明什么能力？ | [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“项目目标与成功定义”章节 | `background/预研孵化战略研究和投资（游戏向）全职.txt` |
| 为什么采用递归式团队构建？ | [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“项目方法论”章节 | `data-layer/knowledge/team/岗位能力与流程规划.md` |
| 阶段 1 已经沉淀了什么？ | `phase1_outputs/` 与 [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“阶段1已沉淀的工程标准”章节 | `background/thoughts/4- 阶段 1：计划设计（按阶段步骤角色交付形成可执行计划）.txt` |
| 阶段 2 为什么这样拆分？ | `phase2_plan/阶段2团队构建方案.md` | `phase2_plan/子阶段依赖关系与并行策略.md` |
| 当前应该先做哪件事？ | [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md) 的“下一步行动”章节 | `phase2_plan/阶段2时间表.md` |
| 统一规范和搭建纪律是什么？ | [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“继续推进时必须遵守的搭建规范 / 统一规范”章节 | `phase1_outputs/acceptance_criteria/` |
| Claude 的历史判断在哪里看？ | [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 的“Claude 历史会话与摘要索引”章节 | `background/thoughts/` 与 `background/*.jsonl` |
| 需要追溯原始聊天过程怎么办？ | `background/*.jsonl` | 先看 `background/thoughts/` 再回查 |

---

## 二、目录职责映射

| 目录 / 文件 | 职责 | 使用方式 |
|---|---|---|
| [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md) | 当前状态总入口 | 接手第一读物 |
| [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) | 背景、规范、方法论总入口 | 接手第二读物 |
| `context/BACKGROUND_INDEX.md` | 本地入口说明与阅读顺序 | 接手第三读物 |
| `context/SOURCE_MAP.md` | 问题到资料的快速映射 | 遇到具体问题时查询 |
| `phase1_outputs/` | 阶段 1 正式交付物 | 查看已沉淀标准 |
| `phase2_plan/` | 阶段 2 正式规划 | 查看当前实施蓝图 |
| `data-layer/knowledge/team/` | 团队构建方法论文档 | 理解递归团队模型 |
| `background/thoughts/` | 历史结论摘要 | 快速补背景 |
| `background/*.jsonl` | 原始会话与完整追溯源 | 按关键词定点回查 |

---

## 三、当前阶段的最短定位路径

如果当前接手者只想知道“此刻该做什么”，请使用以下最短路径：

1. 阅读 [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md)
2. 确认当前子阶段与下一步动作
3. 打开 `phase2_plan/` 中对应子阶段的目标说明与角色文档
4. 仅在不理解设计依据时，再回到 [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md)

---

## 四、当前阶段的完整定位路径

如果当前接手者需要在没有口头交接的情况下恢复完整上下文，请使用以下路径：

1. [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md)
2. [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md)
3. [BACKGROUND_INDEX.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/context/BACKGROUND_INDEX.md)
4. `background/thoughts/` 中与需求澄清、交付标准、阶段 0 / 阶段 1 相关的文件
5. `data-layer/knowledge/team/` 中的团队方法论文档
6. `phase1_outputs/` 与 `phase2_plan/` 中的正式产物
7. 最后按需定位 `background/*.jsonl`

---

## 五、关键词建议

若需要在原始会话或历史材料中搜索，请优先使用以下关键词：

- `proj_004`
- `阶段0`
- `阶段1`
- `阶段2`
- `招聘团队`
- `递归`
- `phase2.4`
- `系统架构设计`
- `阶段2团队构建方案`
- `工程背景手册`

这些关键词通常足够帮助接手者从历史材料中快速命中相关上下文。