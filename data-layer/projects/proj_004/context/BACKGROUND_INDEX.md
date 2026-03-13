## 本地背景入口说明

该目录是 `proj_004` 的**本地接手入口层**，作用不是复制整个 `background/`，而是为后续 AI / 人工接手者提供一套就近可读的索引。

需要明确区分三层材料：

- **当前状态层**：优先阅读 [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md)
- **工程规范层**：系统阅读 [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md)
- **历史追溯层**：按需回查 `background/`、`background/thoughts/` 与 `data-layer/knowledge/team/`

---

## 一、推荐阅读顺序

### 1. 快速接手（5~15 分钟）

按以下顺序阅读：

1. [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md)
2. [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md)
3. [SOURCE_MAP.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/context/SOURCE_MAP.md)
4. `phase2_plan/` 中与当前子阶段对应的目标说明和角色文档

适用场景：

- 刚切换窗口
- 新 AI 临时接手
- 需要先判断当前优先级，而不是追溯完整历史

### 2. 完整恢复背景（20~40 分钟）

在“快速接手”基础上继续阅读：

1. `background/thoughts/项目需求澄清.txt`
2. `background/thoughts/2-1-交付标准.txt`
3. `background/thoughts/4- 阶段 1：计划设计（按阶段步骤角色交付形成可执行计划）.txt`
4. `data-layer/knowledge/team/岗位能力与流程规划.md`
5. `data-layer/knowledge/team/招聘团队工作流程.md`
6. `phase1_outputs/` 中核心正式产物
7. `phase2_plan/` 中当前子阶段相关正式产物

适用场景：

- 需要理解“为什么这样设计”
- 需要恢复项目方法论与阶段衔接
- 准备继续推进阶段 2 执行

### 3. 原始追溯（仅按需）

如果仍然无法解释某个设计、命名或阶段决策，再回查：

- `background/3f36dc20-708d-4d2c-85c8-97d28ebe909a.jsonl`
- `background/d54f3dfa-0860-4a0a-a2e3-7975376f6e5e.jsonl`
- `background/abe6c61a-31e3-4ea1-9bda-83250dfe2565.jsonl`

不建议从头顺读 `.jsonl`，而应先按关键词定位，例如：

- `proj_004`
- `阶段1`
- `阶段2`
- `招聘团队`
- `phase2.4`
- 具体文件名

---

## 二、三类信息源各自负责回答什么问题

### 1. `PROJECT_CONTEXT.md`

主要回答：

- 现在做到哪一步了？
- 当前阶段是什么？
- 近期下一步做什么？
- 哪些团队和模块已经明确？

### 2. `工程背景手册.md`

主要回答：

- 为什么要做 `proj_004`？
- 项目目标、方法论和阶段划分是什么？
- 工程规范、验收标准和接手规则是什么？
- Claude 历史材料该如何使用？

### 3. `background/` 与 `background/thoughts/`

主要回答：

- 最初的需求原话是什么？
- 阶段 0 / 阶段 1 的判断是怎样一步步形成的？
- 某些被简化掉的设计动机和中间推理是什么？

### 4. `data-layer/knowledge/team/`

主要回答：

- 递归式团队构建方法是如何定义的？
- 阶段团队、招聘团队、角色包和执行工作流应如何组织？
- 后续团队扩展时应复用哪些方法论文档？

---

## 三、接手时的判断原则

### 1. 当信息不一致时

优先级按以下顺序判断：

1. [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md) 中的**当前状态**
2. [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md) 中的**背景与规范**
3. `phase1_outputs/`、`phase2_plan/` 中的**正式交付物**
4. `background/thoughts/` 中的**阶段摘要**
5. `background/*.jsonl` 中的**原始会话**

### 2. 当不知道先看什么时

默认只做三步：

1. 看 [PROJECT_CONTEXT.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/PROJECT_CONTEXT.md)
2. 看 [工程背景手册.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/工程背景手册.md)
3. 看 [SOURCE_MAP.md](f:/AIProjects/DesignAssistant/data-layer/projects/proj_004/context/SOURCE_MAP.md)

这三步通常足够恢复 80% 以上的有效背景。

---

## 四、本目录的维护原则

- **不复制原始资料**：`background/` 继续保留在仓库根部作为原始资料层
- **只做索引与映射**：本目录负责告诉接手者“去哪里看什么”
- **优先保持轻量**：仅补充入口、映射、关键词和阅读路径
- **避免双份真相**：不要在这里维护另一套与正式文档竞争的背景结论

---

## 五、建议的后续扩展

如果后续接手频率变高，可以继续在本目录下补充：

- `selected_raw_refs.md`：记录高价值原始会话片段的关键词和定位建议
- `handoff_checklist.md`：形成接手核对清单
- `phase2_current_focus.md`：记录阶段 2 当前真正推进中的子任务

当前阶段下，本目录只需要先承担“就近入口”的职责即可。