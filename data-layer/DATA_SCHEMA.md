# 数据层格式规范

本文档定义了数字员工协作系统的共享数据层格式规范。

## 目录结构

```
data-layer/
├── employees/          # 员工数据(Skill 1维护)
│   ├── roster.json    # 花名册
│   └── {id}/          # 员工工作空间
├── projects/           # 项目数据(Skill 2维护)
│   ├── index.json     # 项目索引
│   └── {project_id}/  # 项目工作空间
├── tasks/             # 任务数据(Skill 3维护)
│   ├── board.json     # 任务看板
│   └── milestones.json # 里程碑
├── assets/            # 资产数据(Skill 4维护)
│   ├── metadata.json  # 资产元数据
│   └── knowledge/     # 知识库
└── logs/              # 日志数据(Skill 5维护)
    ├── work_logs.json # 工作日志
    └── analytics/     # 分析报告
```

## 数据访问规则

- 每个Skill可以**读取**其他Skill的数据
- 每个Skill只能**写入**自己负责的数据
- 所有数据变更必须记录到日志系统

---

## 1. 员工数据 (employees/)

### 1.1 roster.json - 花名册

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "employees": [
    {
      "id": "emp_001",
      "name": "张三",
      "industry": "互联网",
      "position": "产品经理",
      "createdAt": "2026-02-12T10:00:00Z",
      "workspacePath": "~/Documents/digital_employees/张三",
      "status": "active",
      "projects": [],
      "skills": ["需求分析", "用户研究", "Axure", "产品规划"]
    }
  ],
  "statistics": {
    "total": 1,
    "active": 1,
    "inactive": 0
  }
}
```

**字段说明**：
- `id`: 员工唯一标识符，格式为 `emp_` + 3位数字
- `name`: 员工名称
- `industry`: 所属行业
- `position`: 岗位名称
- `createdAt`: 创建时间（ISO 8601格式）
- `workspacePath`: 工作空间路径
- `status`: 状态（active/inactive）
- `projects`: 参与的项目ID列表（由Skill 2维护）
- `skills`: 技能标签数组（根据岗位自动生成）

### 1.2 员工工作空间目录结构

```
employees/{id}/
├── system_prompt.md        # 系统提示词
├── 员工档案.md              # 员工档案
├── 工作日志/                # 工作日志
├── 知识库/                  # 个人知识库
├── 产出物/                  # 工作产出
├── 协作记录/                # 协作历史（Skill 5维护）
└── 项目引用/                # 项目引用配置（Skill 2维护）
```

---

## 2. 项目数据 (projects/)

### 2.1 index.json - 项目索引

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "projects": [
    {
      "id": "proj_001",
      "name": "电商App MVP",
      "description": "电商应用最小可行产品开发",
      "createdAt": "2026-02-12T10:00:00Z",
      "status": "active",
      "members": ["emp_001", "emp_002"],
      "workspacePath": "data-layer/projects/proj_001"
    }
  ],
  "statistics": {
    "total": 1,
    "active": 1,
    "completed": 0,
    "archived": 0
  }
}
```

**字段说明**：
- `id`: 项目唯一标识符，格式为 `proj_` + 3位数字
- `name`: 项目名称
- `description`: 项目描述
- `createdAt`: 创建时间
- `status`: 状态（active/completed/archived）
- `members`: 成员员工ID列表
- `workspacePath`: 项目工作空间路径

### 2.2 项目工作空间目录结构

```
projects/{project_id}/
├── project.json           # 项目配置文件
├── shared/                # 共享资源区
│   ├── docs/             # 文档
│   ├── code/             # 代码
│   ├── design/           # 设计
│   ├── config/           # 配置
│   └── other/            # 其他
├── members/               # 成员目录
│   └── {employee_id}.json # 成员配置
└── README.md             # 项目说明
```

### 2.3 project.json - 项目配置

```json
{
  "id": "proj_001",
  "name": "电商App MVP",
  "description": "电商应用最小可行产品开发",
  "createdAt": "2026-02-12T10:00:00Z",
  "updatedAt": "2026-02-12T10:00:00Z",
  "status": "active",
  "members": [
    {
      "employeeId": "emp_001",
      "role": "产品经理",
      "permission": "admin",
      "joinedAt": "2026-02-12T10:00:00Z"
    }
  ],
  "sharedResources": {
    "docs": "shared/docs",
    "code": "shared/code",
    "design": "shared/design",
    "config": "shared/config",
    "other": "shared/other"
  },
  "milestones": []
}
```

**字段说明**：
- `permission`: 权限级别（admin/write/read）
- `role`: 在项目中的角色
- `sharedResources`: 共享资源路径配置

---

## 3. 任务数据 (tasks/)

### 3.1 board.json - 任务看板

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "tasks": [
    {
      "id": "task_001",
      "projectId": "proj_001",
      "name": "需求分析",
      "description": "完成产品需求文档",
      "assignee": "emp_001",
      "status": "todo",
      "priority": "high",
      "dependencies": [],
      "createdAt": "2026-02-12T10:00:00Z",
      "updatedAt": "2026-02-12T10:00:00Z",
      "dueDate": "2026-02-20T00:00:00Z",
      "tags": ["需求", "文档"]
    }
  ],
  "statistics": {
    "total": 1,
    "todo": 1,
    "inProgress": 0,
    "completed": 0,
    "blocked": 0
  }
}
```

**字段说明**：
- `id`: 任务唯一标识符，格式为 `task_` + 3位数字
- `projectId`: 所属项目ID
- `assignee`: 负责人员工ID
- `status`: 状态（todo/inProgress/completed/blocked）
- `priority`: 优先级（low/medium/high/urgent）
- `dependencies`: 依赖的任务ID列表
- `tags`: 标签数组

### 3.2 milestones.json - 里程碑

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "milestones": [
    {
      "id": "mile_001",
      "projectId": "proj_001",
      "name": "MVP版本",
      "description": "完成最小可行产品",
      "dueDate": "2026-03-01T00:00:00Z",
      "status": "active",
      "tasks": ["task_001", "task_002"],
      "progress": 0,
      "createdAt": "2026-02-12T10:00:00Z"
    }
  ]
}
```

**字段说明**：
- `id`: 里程碑唯一标识符，格式为 `mile_` + 3位数字
- `progress`: 进度百分比（0-100）
- `tasks`: 关联的任务ID列表

---

## 4. 资产数据 (assets/)

### 4.1 metadata.json - 资产元数据

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "assets": [
    {
      "id": "asset_001",
      "projectId": "proj_001",
      "name": "产品需求文档.md",
      "type": "document",
      "category": "docs",
      "path": "projects/proj_001/shared/docs/产品需求文档.md",
      "creator": "emp_001",
      "createdAt": "2026-02-12T10:00:00Z",
      "updatedAt": "2026-02-12T10:00:00Z",
      "version": "1.0.0",
      "description": "电商App产品需求文档",
      "tags": ["需求", "文档"],
      "references": [],
      "changeLog": [
        {
          "version": "1.0.0",
          "date": "2026-02-12T10:00:00Z",
          "author": "emp_001",
          "changes": "初始版本"
        }
      ]
    }
  ],
  "statistics": {
    "total": 1,
    "byType": {
      "document": 1,
      "code": 0,
      "design": 0,
      "config": 0,
      "other": 0
    }
  }
}
```

**字段说明**：
- `id`: 资产唯一标识符，格式为 `asset_` + 3位数字
- `type`: 资产类型（document/code/design/config/other）
- `category`: 分类（docs/code/design/config/other）
- `references`: 被引用的资产ID列表
- `changeLog`: 变更日志数组

### 4.2 知识库目录结构

```
assets/knowledge/
├── technical/          # 技术方案
├── business/           # 业务规范
├── trends/             # 行业趋势
└── practices/          # 最佳实践
```

---

## 5. 日志数据 (logs/)

### 5.1 work_logs.json - 工作日志

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-02-12T10:00:00Z",
  "logs": [
    {
      "id": "log_001",
      "employeeId": "emp_001",
      "projectId": "proj_001",
      "taskId": "task_001",
      "timestamp": "2026-02-12T10:00:00Z",
      "action": "task_started",
      "description": "开始需求分析任务",
      "duration": 0,
      "outputs": [],
      "issues": []
    }
  ]
}
```

**字段说明**：
- `id`: 日志唯一标识符，格式为 `log_` + 3位数字
- `action`: 操作类型（task_started/task_completed/asset_created等）
- `duration`: 耗时（分钟）
- `outputs`: 产出物列表
- `issues`: 遇到的问题列表

---

## 数据一致性校验

系统应定期执行以下校验：

1. **员工-项目一致性**：
   - 员工的 `projects` 字段与项目的 `members` 字段保持同步
   
2. **任务-项目一致性**：
   - 任务的 `projectId` 必须存在于项目索引中
   - 任务的 `assignee` 必须是项目成员
   
3. **资产-项目一致性**：
   - 资产的 `projectId` 必须存在于项目索引中
   - 资产的 `creator` 必须是项目成员
   
4. **引用完整性**：
   - 资产的 `references` 中的ID必须存在
   - 任务的 `dependencies` 中的ID必须存在

---

## 版本控制

所有JSON文件都包含 `version` 字段，遵循语义化版本规范（Semantic Versioning）：
- 主版本号：不兼容的API修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

当前版本：**1.0.0**

---

*最后更新：2026-02-12*
