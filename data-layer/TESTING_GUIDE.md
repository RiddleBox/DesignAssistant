# 阶段一测试指南

本文档提供了测试阶段一实现成果的完整指南。

## 测试内容

阶段一实现了以下功能，需要逐一验证：

### 1. 数据层基础设施
- ✅ 目录结构完整性
- ✅ JSON文件格式正确性
- ✅ 数据访问类功能
- ✅ 数据一致性校验

### 2. 跨Skill接口
- ✅ 更新员工所属项目
- ✅ 查询员工技能标签
- ✅ 日志记录功能

### 3. 数据操作
- ✅ 添加员工
- ✅ 添加项目
- ✅ 添加任务
- ✅ 添加资产

---

## 测试方法

### 方法一：自动化测试（推荐）

运行自动化测试脚本，一键验证所有功能：

```bash
# 进入项目目录
cd f:\AIProjects\DesignAssistant

# 运行测试脚本
python data-layer/test_phase1.py
```

**预期输出**：
```
============================================================
Phase 1 Testing Suite
============================================================

=== Test 1: Directory Structure ===
✅ PASS - Directory exists: employees
✅ PASS - Directory exists: projects
✅ PASS - Directory exists: tasks
...

=== Test 2: JSON Files ===
✅ PASS - JSON file valid: roster.json
✅ PASS - JSON file valid: index.json
...

============================================================
Test Summary
============================================================
Total tests: 20+
✅ Passed: 20+
❌ Failed: 0
Success rate: 100.0%

🎉 All tests passed! Phase 1 implementation is working correctly.
```

---

### 方法二：手动测试

如果自动化测试失败或需要深入验证，可以手动测试各个功能。

#### 测试1：验证目录结构

```bash
# 检查数据层目录是否存在
ls data-layer/

# 预期输出：
# employees/  projects/  tasks/  assets/  logs/
# DATA_SCHEMA.md  data_access.py  consistency_validator.py  README.md
```

#### 测试2：验证JSON文件

```bash
# 查看员工花名册
cat data-layer/employees/roster.json

# 预期输出：包含version、lastUpdated、employees、statistics字段
```

#### 测试3：测试数据访问类

创建测试脚本 `manual_test.py`：

```python
from data_access import EmployeeDataAccess

# 创建数据访问对象
employee_access = EmployeeDataAccess()

# 读取花名册
roster = employee_access.get_roster()
print(f"员工总数: {roster['statistics']['total']}")

# 添加测试员工
test_employee = {
    'name': '测试员工',
    'industry': '互联网',
    'position': '产品经理',
    'createdAt': '2026-02-12T10:00:00Z',
    'workspacePath': '~/Documents/digital_employees/测试员工',
    'status': 'active',
    'projects': [],
    'skills': ['需求分析', '产品规划']
}

employee_access.add_employee(test_employee)
print(f"员工已添加，ID: {test_employee['id']}")

# 再次读取花名册
roster = employee_access.get_roster()
print(f"员工总数: {roster['statistics']['total']}")
```

运行：
```bash
python manual_test.py
```

#### 测试4：测试跨Skill接口

```python
from data_access import EmployeeDataAccess, ProjectDataAccess

employee_access = EmployeeDataAccess()
project_access = ProjectDataAccess()

# 添加项目
test_project = {
    'name': '测试项目',
    'description': '测试项目描述',
    'createdAt': '2026-02-12T10:00:00Z',
    'status': 'active',
    'members': ['emp_001'],
    'workspacePath': 'data-layer/projects/proj_001'
}
project_access.add_project(test_project)
print(f"项目已添加，ID: {test_project['id']}")

# 更新员工所属项目
employee_access.update_employee_projects('emp_001', test_project['id'], 'add')
print("员工已添加到项目")

# 查询员工
roster = employee_access.get_roster()
employee = next(e for e in roster['employees'] if e['id'] == 'emp_001')
print(f"员工项目列表: {employee['projects']}")

# 查询具有特定技能的员工
matched = employee_access.query_employees_by_skills(['需求分析'])
print(f"找到 {len(matched)} 位员工具有'需求分析'技能")
```

#### 测试5：测试一致性校验

```bash
# 运行一致性校验工具
python data-layer/consistency_validator.py

# 预期输出：
# ✓ All consistency checks passed!
# 或者列出发现的问题
```

---

## 测试检查清单

使用以下清单逐项验证：

### 数据层结构
- [ ] `data-layer/` 目录存在
- [ ] `employees/` 目录存在
- [ ] `projects/` 目录存在
- [ ] `tasks/` 目录存在
- [ ] `assets/` 目录存在
- [ ] `logs/` 目录存在
- [ ] `assets/knowledge/technical/` 目录存在
- [ ] `assets/knowledge/business/` 目录存在
- [ ] `assets/knowledge/trends/` 目录存在
- [ ] `assets/knowledge/practices/` 目录存在

### JSON文件
- [ ] `roster.json` 存在且格式正确
- [ ] `index.json` 存在且格式正确
- [ ] `board.json` 存在且格式正确
- [ ] `milestones.json` 存在且格式正确
- [ ] `metadata.json` 存在且格式正确
- [ ] `work_logs.json` 存在且格式正确

### Python模块
- [ ] `data_access.py` 可以正常导入
- [ ] `consistency_validator.py` 可以正常导入
- [ ] `EmployeeDataAccess` 类可以实例化
- [ ] `ProjectDataAccess` 类可以实例化
- [ ] `TaskDataAccess` 类可以实例化
- [ ] `AssetDataAccess` 类可以实例化

### 数据操作
- [ ] 可以添加员工
- [ ] 可以添加项目
- [ ] 可以添加任务
- [ ] 可以添加资产
- [ ] 统计数据自动更新
- [ ] 日志自动记录

### 跨Skill接口
- [ ] `update_employee_projects` 可以添加项目
- [ ] `update_employee_projects` 可以移除项目
- [ ] `query_employees_by_skills` 可以查询员工
- [ ] 接口调用会记录日志

### 一致性校验
- [ ] 可以运行一致性校验
- [ ] 可以检测员工-项目不一致
- [ ] 可以检测任务-项目不一致
- [ ] 可以检测资产-项目不一致
- [ ] 可以检测引用完整性问题

### 文档
- [ ] `DATA_SCHEMA.md` 存在且内容完整
- [ ] `README.md` 存在且内容完整
- [ ] `SKILL1_API.md` 存在且内容完整
- [ ] `SKILL_V2.md` 存在且内容完整

---

## 常见问题排查

### 问题1：ImportError: No module named 'data_access'

**原因**：Python找不到模块

**解决方案**：
```bash
# 确保在正确的目录下运行
cd f:\AIProjects\DesignAssistant

# 或者设置PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;f:\AIProjects\DesignAssistant\data-layer
```

### 问题2：FileNotFoundError: roster.json not found

**原因**：JSON文件不存在或路径错误

**解决方案**：
```bash
# 检查文件是否存在
ls data-layer/employees/roster.json

# 如果不存在，重新创建
# 参考 DATA_SCHEMA.md 中的格式
```

### 问题3：JSONDecodeError: Invalid JSON

**原因**：JSON文件格式错误

**解决方案**：
```bash
# 使用JSON验证工具检查
python -m json.tool data-layer/employees/roster.json

# 或者重新初始化文件
```

### 问题4：一致性校验失败

**原因**：数据不一致

**解决方案**：
1. 查看校验报告，了解具体问题
2. 根据报告修复数据
3. 重新运行校验

---

## 测试数据清理

测试完成后，如果需要清理测试数据：

```bash
# 备份当前数据（可选）
cp -r data-layer data-layer-backup

# 重新初始化JSON文件
# 将所有JSON文件的数据数组清空，保留结构
```

或者运行清理脚本：

```python
from data_access import EmployeeDataAccess, ProjectDataAccess, TaskDataAccess, AssetDataAccess

# 清空所有数据
employee_access = EmployeeDataAccess()
project_access = ProjectDataAccess()
task_access = TaskDataAccess()
asset_access = AssetDataAccess()

# 重置花名册
employee_access.write_json(employee_access.config.ROSTER_FILE, {
    'version': '1.0.0',
    'lastUpdated': '2026-02-12T10:00:00Z',
    'employees': [],
    'statistics': {'total': 0, 'active': 0, 'inactive': 0}
})

# 重置项目索引
project_access.write_json(project_access.config.PROJECT_INDEX_FILE, {
    'version': '1.0.0',
    'lastUpdated': '2026-02-12T10:00:00Z',
    'projects': [],
    'statistics': {'total': 0, 'active': 0, 'completed': 0, 'archived': 0}
})

# 重置任务看板
task_access.write_json(task_access.config.TASK_BOARD_FILE, {
    'version': '1.0.0',
    'lastUpdated': '2026-02-12T10:00:00Z',
    'tasks': [],
    'statistics': {'total': 0, 'todo': 0, 'inProgress': 0, 'completed': 0, 'blocked': 0}
})

# 重置资产元数据
asset_access.write_json(asset_access.config.ASSET_METADATA_FILE, {
    'version': '1.0.0',
    'lastUpdated': '2026-02-12T10:00:00Z',
    'assets': [],
    'statistics': {'total': 0, 'byType': {}}
})

print("测试数据已清理")
```

---

## 测试报告模板

测试完成后，可以使用以下模板记录测试结果：

```markdown
# 阶段一测试报告

**测试日期**：YYYY-MM-DD
**测试人员**：XXX
**测试环境**：Windows/Linux/Mac

## 测试结果

- 总测试项：XX
- 通过：XX
- 失败：XX
- 成功率：XX%

## 详细结果

### 数据层结构
- [x] 目录结构完整
- [x] JSON文件格式正确

### 数据操作
- [x] 添加员工成功
- [x] 添加项目成功
- [x] 添加任务成功
- [x] 添加资产成功

### 跨Skill接口
- [x] 更新员工项目成功
- [x] 查询员工技能成功

### 一致性校验
- [x] 校验工具运行正常
- [x] 无数据不一致问题

## 发现的问题

1. 问题描述
   - 严重程度：高/中/低
   - 复现步骤：...
   - 预期结果：...
   - 实际结果：...

## 建议

1. ...
2. ...

## 结论

阶段一实现 [通过/未通过] 测试，[可以/不可以] 进入下一阶段。
```

---

*最后更新：2026-02-12*
