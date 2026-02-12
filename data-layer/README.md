# 数据层使用指南

本目录包含数字员工协作系统的共享数据层，为多个Skill提供统一的数据存储和访问接口。

## 目录结构

```
data-layer/
├── DATA_SCHEMA.md              # 数据格式规范文档
├── data_access.py              # 数据访问基础类
├── consistency_validator.py    # 数据一致性校验工具
├── README.md                   # 本文件
├── employees/                  # 员工数据(Skill 1维护)
│   ├── roster.json            # 花名册
│   └── {id}/                  # 员工工作空间
├── projects/                   # 项目数据(Skill 2维护)
│   ├── index.json             # 项目索引
│   └── {project_id}/          # 项目工作空间
├── tasks/                      # 任务数据(Skill 3维护)
│   ├── board.json             # 任务看板
│   └── milestones.json        # 里程碑
├── assets/                     # 资产数据(Skill 4维护)
│   ├── metadata.json          # 资产元数据
│   └── knowledge/             # 知识库
│       ├── technical/         # 技术方案
│       ├── business/          # 业务规范
│       ├── trends/            # 行业趋势
│       └── practices/         # 最佳实践
└── logs/                       # 日志数据(Skill 5维护)
    ├── work_logs.json         # 工作日志
    └── analytics/             # 分析报告
```

## 数据访问规则

1. **读取权限**：每个Skill可以读取其他Skill的数据
2. **写入权限**：每个Skill只能写入自己负责的数据域
3. **日志记录**：所有数据变更必须记录到日志系统

## 使用示例

### 1. 读取员工花名册（任何Skill都可以）

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()
roster = employee_access.get_roster()

print(f"员工总数: {roster['statistics']['total']}")
for employee in roster['employees']:
    print(f"- {employee['name']} ({employee['position']})")
```

### 2. 添加新员工（仅Skill 1）

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

new_employee = {
    'name': '张三',
    'industry': '互联网',
    'position': '产品经理',
    'createdAt': '2026-02-12T10:00:00Z',
    'workspacePath': '~/Documents/digital_employees/张三',
    'status': 'active',
    'projects': [],
    'skills': ['需求分析', '用户研究', 'Axure', '产品规划']
}

employee_access.add_employee(new_employee)
print(f"员工 {new_employee['name']} 已添加")
```

### 3. 更新员工所属项目（Skill 2调用Skill 1接口）

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 将员工添加到项目
employee_access.update_employee_projects(
    employee_id='emp_001',
    project_id='proj_001',
    operation='add'
)

# 从项目移除员工
employee_access.update_employee_projects(
    employee_id='emp_001',
    project_id='proj_001',
    operation='remove'
)
```

### 4. 查询具有特定技能的员工（Skill 2调用Skill 1接口）

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 查找具有"需求分析"或"产品规划"技能的员工
matched_employees = employee_access.query_employees_by_skills(['需求分析', '产品规划'])

for employee in matched_employees:
    print(f"- {employee['name']}: {', '.join(employee['skills'])}")
```

### 5. 添加新项目（仅Skill 2）

```python
from data_access import ProjectDataAccess

project_access = ProjectDataAccess()

new_project = {
    'name': '电商App MVP',
    'description': '电商应用最小可行产品开发',
    'createdAt': '2026-02-12T10:00:00Z',
    'status': 'active',
    'members': ['emp_001', 'emp_002'],
    'workspacePath': 'data-layer/projects/proj_001'
}

project_access.add_project(new_project)
print(f"项目 {new_project['name']} 已创建")
```

### 6. 添加新任务（仅Skill 3）

```python
from data_access import TaskDataAccess

task_access = TaskDataAccess()

new_task = {
    'projectId': 'proj_001',
    'name': '需求分析',
    'description': '完成产品需求文档',
    'assignee': 'emp_001',
    'status': 'todo',
    'priority': 'high',
    'dependencies': [],
    'createdAt': '2026-02-12T10:00:00Z',
    'updatedAt': '2026-02-12T10:00:00Z',
    'dueDate': '2026-02-20T00:00:00Z',
    'tags': ['需求', '文档']
}

task_access.add_task(new_task)
print(f"任务 {new_task['name']} 已创建")
```

### 7. 添加新资产（仅Skill 4）

```python
from data_access import AssetDataAccess

asset_access = AssetDataAccess()

new_asset = {
    'projectId': 'proj_001',
    'name': '产品需求文档.md',
    'type': 'document',
    'category': 'docs',
    'path': 'projects/proj_001/shared/docs/产品需求文档.md',
    'creator': 'emp_001',
    'createdAt': '2026-02-12T10:00:00Z',
    'updatedAt': '2026-02-12T10:00:00Z',
    'version': '1.0.0',
    'description': '电商App产品需求文档',
    'tags': ['需求', '文档'],
    'references': [],
    'changeLog': [
        {
            'version': '1.0.0',
            'date': '2026-02-12T10:00:00Z',
            'author': 'emp_001',
            'changes': '初始版本'
        }
    ]
}

asset_access.add_asset(new_asset)
print(f"资产 {new_asset['name']} 已添加")
```

### 8. 运行数据一致性校验

```python
from consistency_validator import ConsistencyValidator

validator = ConsistencyValidator()
is_valid, issues = validator.validate_all()

if is_valid:
    print("✓ 所有一致性检查通过！")
else:
    print(validator.get_report())
```

或者直接运行命令行工具：

```bash
python consistency_validator.py
```

## 数据格式规范

详细的数据格式规范请参阅 [DATA_SCHEMA.md](DATA_SCHEMA.md)。

## 跨Skill接口

### Skill 1 (员工管理) 提供的接口

- `update_employee_projects(employee_id, project_id, operation)` - 更新员工所属项目
- `query_employees_by_skills(skill_keywords)` - 查询具有特定技能的员工
- `update_employee_skill_tree(employee_id, skill_name, exp_increment)` - 更新员工技能树（待实现）
- `get_employee_profile(employee_id)` - 读取员工档案（待实现）

### Skill 2 (项目协作) 提供的接口

- `add_project_member(project_id, employee_id, role, permission)` - 添加项目成员（待实现）
- `remove_project_member(project_id, employee_id)` - 移除项目成员（待实现）
- `get_project_details(project_id)` - 获取项目详情（待实现）

### Skill 3 (任务管理) 提供的接口

- `create_task(task_data)` - 创建任务（待实现）
- `update_task_status(task_id, status)` - 更新任务状态（待实现）
- `check_task_dependencies(task_id)` - 检查任务依赖（待实现）

### Skill 4 (资产管理) 提供的接口

- `save_asset(asset_data)` - 保存资产（待实现）
- `search_assets(query)` - 搜索资产（待实现）
- `get_asset_references(asset_id)` - 获取资产引用（待实现）

### Skill 5 (日志分析) 提供的接口

- `log_work(log_data)` - 记录工作日志（待实现）
- `generate_report(start_date, end_date)` - 生成复盘报告（待实现）

## 注意事项

1. **时间格式**：所有时间字段使用ISO 8601格式（`YYYY-MM-DDTHH:MM:SSZ`）
2. **ID生成**：ID格式为 `{类型}_{3位数字}`，如 `emp_001`、`proj_001`
3. **版本控制**：所有JSON文件包含 `version` 字段，遵循语义化版本规范
4. **数据一致性**：定期运行 `consistency_validator.py` 检查数据一致性
5. **备份**：重要操作前建议备份整个 `data-layer` 目录

## 开发建议

1. **新增Skill时**：
   - 在 `data_access.py` 中添加对应的数据访问类
   - 在 `DATA_SCHEMA.md` 中定义数据格式
   - 在 `consistency_validator.py` 中添加相关校验逻辑

2. **修改数据结构时**：
   - 更新 `version` 字段
   - 在 `DATA_SCHEMA.md` 中记录变更
   - 确保向后兼容或提供迁移脚本

3. **调试时**：
   - 使用 `consistency_validator.py` 检查数据一致性
   - 查看 `logs/work_logs.json` 了解数据变更历史

---

*最后更新：2026-02-12*
