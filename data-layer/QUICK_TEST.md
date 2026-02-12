# 快速测试指令

## 一键测试（推荐）

```bash
cd f:\AIProjects\DesignAssistant
python data-layer\test_phase1.py
```

**预期结果**：所有测试通过，显示"🎉 All tests passed!"

---

## 分步测试

### 1. 测试数据层结构

```bash
# 检查目录是否存在
ls data-layer\
ls data-layer\employees\
ls data-layer\projects\
ls data-layer\tasks\
ls data-layer\assets\
ls data-layer\logs\
```

### 2. 测试JSON文件

```bash
# 查看员工花名册
cat data-layer\employees\roster.json

# 查看项目索引
cat data-layer\projects\index.json

# 查看任务看板
cat data-layer\tasks\board.json

# 查看工作日志
cat data-layer\logs\work_logs.json
```

### 3. 测试数据访问类

```python
# 创建测试文件 quick_test.py
from data_access import EmployeeDataAccess

employee_access = EmployeeDataAccess()
roster = employee_access.get_roster()
print(f"员工总数: {roster['statistics']['total']}")
```

运行：
```bash
python quick_test.py
```

### 4. 测试一致性校验

```bash
python data-layer\consistency_validator.py
```

**预期结果**：显示"✓ All consistency checks passed!"或列出发现的问题

---

## 测试数据清理

如果需要清理测试数据，重新初始化：

```python
# 创建 cleanup.py
import json
from pathlib import Path

files = {
    'data-layer/employees/roster.json': {
        'version': '1.0.0',
        'lastUpdated': '2026-02-12T10:37:00Z',
        'employees': [],
        'statistics': {'total': 0, 'active': 0, 'inactive': 0}
    },
    'data-layer/projects/index.json': {
        'version': '1.0.0',
        'lastUpdated': '2026-02-12T10:37:00Z',
        'projects': [],
        'statistics': {'total': 0, 'active': 0, 'completed': 0, 'archived': 0}
    },
    'data-layer/tasks/board.json': {
        'version': '1.0.0',
        'lastUpdated': '2026-02-12T10:37:00Z',
        'tasks': [],
        'statistics': {'total': 0, 'todo': 0, 'inProgress': 0, 'completed': 0, 'blocked': 0}
    },
    'data-layer/assets/metadata.json': {
        'version': '1.0.0',
        'lastUpdated': '2026-02-12T10:37:00Z',
        'assets': [],
        'statistics': {'total': 0, 'byType': {}}
    },
    'data-layer/logs/work_logs.json': {
        'version': '1.0.0',
        'lastUpdated': '2026-02-12T10:37:00Z',
        'logs': []
    }
}

for file_path, data in files.items():
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 测试数据已清理")
```

运行：
```bash
python cleanup.py
```

---

## 常用检查命令

```bash
# 查看文件数量
ls data-layer\employees\ | Measure-Object
ls data-layer\projects\ | Measure-Object

# 查看JSON文件大小
ls data-layer\employees\roster.json
ls data-layer\projects\index.json

# 查看最近修改时间
ls data-layer\employees\roster.json | Select-Object LastWriteTime
```

---

## 快速验证清单

- [ ] 运行 `python data-layer\test_phase1.py`
- [ ] 检查是否显示"All tests passed"
- [ ] 查看测试报告 `data-layer\TEST_REPORT.md`
- [ ] 运行一致性校验 `python data-layer\consistency_validator.py`
- [ ] 查看工作日志 `cat data-layer\logs\work_logs.json`

---

*最后更新：2026-02-12*
