# Skill 1 跨Skill接口文档

本文档定义了Skill 1（数字员工招募与管理）提供给其他Skill调用的接口。

## 接口列表

### 1. 更新员工所属项目

**接口名称**：`update_employee_projects`

**调用者**：Skill 2（团队项目协作）

**功能描述**：当员工被分配到项目或从项目移除时，更新员工的项目列表。

**参数**：
- `employee_id` (string): 员工ID，格式为 `emp_XXX`
- `project_id` (string): 项目ID，格式为 `proj_XXX`
- `operation` (string): 操作类型，可选值：
  - `"add"`: 将员工添加到项目
  - `"remove"`: 从项目移除员工

**返回值**：无

**示例代码**：

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

**数据变更**：
- 更新 `data-layer/employees/roster.json` 中对应员工的 `projects` 字段
- 记录变更日志到 `data-layer/logs/work_logs.json`

**注意事项**：
- 如果员工ID不存在，操作将被忽略
- 添加操作会检查项目ID是否已存在，避免重复添加
- 移除操作会检查项目ID是否存在，避免重复移除

---

### 2. 查询员工技能标签

**接口名称**：`query_employees_by_skills`

**调用者**：Skill 2（团队项目协作）

**功能描述**：根据技能关键词查询匹配的员工列表，用于项目成员匹配。

**参数**：
- `skill_keywords` (List[string]): 技能关键词列表，如 `["需求分析", "产品规划"]`

**返回值**：
- `List[Dict]`: 匹配的员工列表，每个员工包含完整的员工信息

**示例代码**：

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 查找具有"需求分析"或"产品规划"技能的员工
matched_employees = employee_access.query_employees_by_skills(['需求分析', '产品规划'])

for employee in matched_employees:
    print(f"- {employee['name']} ({employee['position']}): {', '.join(employee['skills'])}")
```

**匹配规则**：
- 使用模糊匹配，不区分大小写
- 只要员工的任一技能标签包含任一关键词，即视为匹配
- 返回所有匹配的员工，不限制数量

**返回示例**：

```json
[
  {
    "id": "emp_001",
    "name": "张三",
    "industry": "互联网",
    "position": "产品经理",
    "createdAt": "2026-02-12T10:00:00Z",
    "workspacePath": "~/Documents/digital_employees/张三",
    "status": "active",
    "projects": ["proj_001"],
    "skills": ["需求分析", "用户研究", "Axure", "产品规划"]
  }
]
```

---

### 3. 更新员工技能树

**接口名称**：`update_employee_skill_tree`

**调用者**：Skill 3（任务管理）、Skill 5（日志分析）

**功能描述**：当员工完成任务时，根据任务类型和质量增加相关技能经验值。

**状态**：⚠️ 待实现（P2功能）

**参数**：
- `employee_id` (string): 员工ID
- `skill_name` (string): 技能名称
- `exp_increment` (int): 经验值增量

**返回值**：无

**预期行为**：
- 读取员工档案中的技能树数据
- 增加指定技能的经验值
- 如果经验值达到阈值，升级技能等级
- 更新员工档案文件

**示例代码**（待实现）：

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 员工完成需求分析任务，增加"需求分析"技能经验值
employee_access.update_employee_skill_tree(
    employee_id='emp_001',
    skill_name='需求分析',
    exp_increment=10
)
```

---

### 4. 读取员工档案

**接口名称**：`get_employee_profile`

**调用者**：所有Skill

**功能描述**：读取员工的完整档案信息，包括基本信息、参与项目、技能树、协作记录等。

**状态**：⚠️ 待实现

**参数**：
- `employee_id` (string): 员工ID

**返回值**：
- `Dict`: 员工档案数据，包含：
  - 基本信息（从roster.json读取）
  - 档案详情（从员工档案.md解析）
  - 工作空间路径

**示例代码**（待实现）：

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 读取员工档案
profile = employee_access.get_employee_profile('emp_001')

print(f"员工姓名: {profile['name']}")
print(f"岗位: {profile['position']}")
print(f"参与项目: {', '.join(profile['projects'])}")
print(f"技能标签: {', '.join(profile['skills'])}")
```

**返回示例**（待实现）：

```json
{
  "id": "emp_001",
  "name": "张三",
  "industry": "互联网",
  "position": "产品经理",
  "createdAt": "2026-02-12T10:00:00Z",
  "workspacePath": "~/Documents/digital_employees/张三",
  "status": "active",
  "projects": ["proj_001"],
  "skills": ["需求分析", "用户研究", "Axure", "产品规划"],
  "profile": {
    "responsibilities": ["..."],
    "workflow": ["..."],
    "outputs": ["..."]
  }
}
```

---

## 接口调用流程

### 场景1：Skill 2 创建项目并分配成员

```python
from data_access import ProjectDataAccess, EmployeeDataAccess

project_access = ProjectDataAccess()
employee_access = EmployeeDataAccess()

# 1. 创建项目
new_project = {
    'name': '电商App MVP',
    'description': '电商应用最小可行产品开发',
    'createdAt': '2026-02-12T10:00:00Z',
    'status': 'active',
    'members': ['emp_001', 'emp_002'],
    'workspacePath': 'data-layer/projects/proj_001'
}
project_access.add_project(new_project)
project_id = new_project['id']  # 自动生成的ID

# 2. 更新员工的项目列表（调用Skill 1接口）
for employee_id in ['emp_001', 'emp_002']:
    employee_access.update_employee_projects(
        employee_id=employee_id,
        project_id=project_id,
        operation='add'
    )
```

### 场景2：Skill 2 根据技能匹配项目成员

```python
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()

# 1. 查询具有特定技能的员工
required_skills = ['需求分析', '产品规划']
matched_employees = employee_access.query_employees_by_skills(required_skills)

# 2. 展示匹配结果给用户选择
print("以下员工具备所需技能：")
for employee in matched_employees:
    print(f"- {employee['name']} ({employee['position']})")
    print(f"  技能: {', '.join(employee['skills'])}")
    print(f"  当前项目: {', '.join(employee['projects']) if employee['projects'] else '无'}")
```

### 场景3：Skill 3 任务完成后更新技能树（待实现）

```python
from data_access import TaskDataAccess, EmployeeDataAccess

task_access = TaskDataAccess()
employee_access = EmployeeDataAccess()

# 1. 更新任务状态
task_id = 'task_001'
# ... 更新任务状态为completed

# 2. 获取任务信息
task_board = task_access.get_task_board()
task = next(t for t in task_board['tasks'] if t['id'] == task_id)

# 3. 根据任务类型增加技能经验值（调用Skill 1接口）
if '需求' in task['tags']:
    employee_access.update_employee_skill_tree(
        employee_id=task['assignee'],
        skill_name='需求分析',
        exp_increment=10
    )
```

---

## 数据一致性保证

### 员工-项目双向同步

当Skill 2调用 `update_employee_projects` 接口时：

1. **Skill 2的职责**：
   - 更新项目的 `members` 列表
   - 在项目工作空间创建成员配置文件

2. **Skill 1的职责**（通过接口）：
   - 更新员工的 `projects` 列表
   - 在员工工作空间的 `项目引用/` 目录创建项目引用配置

3. **一致性校验**：
   - 定期运行 `consistency_validator.py` 检查员工-项目一致性
   - 如果发现不一致，生成警告报告

### 接口调用日志

所有接口调用都会记录到 `data-layer/logs/work_logs.json`：

```json
{
  "id": "log_001",
  "timestamp": "2026-02-12T10:00:00Z",
  "action": "employee_projects_updated",
  "details": {
    "employeeId": "emp_001",
    "projectId": "proj_001",
    "operation": "add"
  }
}
```

---

## 接口实现状态

| 接口名称 | 状态 | 优先级 | 预计实现阶段 |
|---------|------|--------|-------------|
| update_employee_projects | ✅ 已实现 | P0 | 阶段一 |
| query_employees_by_skills | ✅ 已实现 | P0 | 阶段一 |
| update_employee_skill_tree | ⚠️ 待实现 | P2 | 阶段六 |
| get_employee_profile | ⚠️ 待实现 | P1 | 阶段二 |

---

## 测试用例

### 测试1：更新员工所属项目

```python
def test_update_employee_projects():
    from data_access import EmployeeDataAccess
    
    employee_access = EmployeeDataAccess()
    
    # 添加员工到项目
    employee_access.update_employee_projects('emp_001', 'proj_001', 'add')
    
    # 验证
    roster = employee_access.get_roster()
    employee = next(e for e in roster['employees'] if e['id'] == 'emp_001')
    assert 'proj_001' in employee['projects']
    
    # 从项目移除员工
    employee_access.update_employee_projects('emp_001', 'proj_001', 'remove')
    
    # 验证
    roster = employee_access.get_roster()
    employee = next(e for e in roster['employees'] if e['id'] == 'emp_001')
    assert 'proj_001' not in employee['projects']
```

### 测试2：查询员工技能标签

```python
def test_query_employees_by_skills():
    from data_access import EmployeeDataAccess
    
    employee_access = EmployeeDataAccess()
    
    # 查询具有"需求分析"技能的员工
    matched = employee_access.query_employees_by_skills(['需求分析'])
    
    # 验证
    assert len(matched) > 0
    for employee in matched:
        assert any('需求分析' in skill for skill in employee['skills'])
```

---

*最后更新：2026-02-12*
