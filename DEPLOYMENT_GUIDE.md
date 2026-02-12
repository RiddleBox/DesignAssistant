# 数字员工协作系统 - 部署指南

本文档说明如何在不同机器上部署和使用数字员工协作系统。

---

## 🎯 部署方案对比

### 方案A：完整部署（推荐用于生产环境）

**携带文件**：
- ✅ 所有SKILL文件（SKILL_V2.md等）
- ✅ 完整的 `data-layer/` 目录（包含所有数据）
- ✅ 所有Python脚本（data_access.py等）

**优点**：
- 开箱即用，无需初始化
- 保留所有历史数据
- 适合团队协作和数据迁移

**适用场景**：
- 从一台机器迁移到另一台机器
- 团队成员之间共享数据
- 需要保留所有历史记录

---

### 方案B：轻量部署（推荐用于新环境）

**携带文件**：
- ✅ 所有SKILL文件（SKILL_V2.md等）
- ✅ `data-layer/auto_init.py`（自动初始化脚本）
- ✅ `data-layer/data_access.py`（数据访问类）
- ✅ `data-layer/consistency_validator.py`（一致性校验）
- ✅ `data-layer/DATA_SCHEMA.md`（数据格式规范）

**优点**：
- 文件少，便于携带
- 适合版本控制（Git）
- 自动创建干净的数据层

**适用场景**：
- 首次部署到新机器
- 开发测试环境
- 不需要历史数据的场景

---

## 📦 方案B：轻量部署详细步骤

### 第一步：准备文件

创建项目目录并复制以下文件：

```
DesignAssistant/
├── SKILL_V2.md                          # Skill 1
├── data-layer/
│   ├── auto_init.py                     # 自动初始化脚本
│   ├── data_access.py                   # 数据访问类
│   ├── consistency_validator.py         # 一致性校验
│   └── DATA_SCHEMA.md                   # 数据格式规范
```

**文件大小**：约 50KB（5个文件）

---

### 第二步：首次运行

#### 选项1：自动初始化（推荐）

直接使用SKILL，系统会自动检测并初始化：

```bash
# 直接调用SKILL 1
# 系统会自动检测数据层不存在，并运行初始化脚本
```

SKILL会自动执行：
```bash
python data-layer/auto_init.py
```

**预期输出**：
```
============================================================
🚀 Data Layer Auto-Initialization
============================================================
📍 Base path: f:\AIProjects\DesignAssistant\data-layer

📁 Creating directory structure...
   ✅ Created: employees/
   ✅ Created: projects/
   ✅ Created: tasks/
   ✅ Created: assets/
   ✅ Created: logs/
   ...

📄 Creating JSON files...
   ✅ Created: employees/roster.json
   ✅ Created: projects/index.json
   ...

============================================================
✅ Initialization Complete!
============================================================
📁 Directories created: 10
📄 JSON files created: 6
📖 README created: Yes

🎉 Data layer is ready to use!
```

#### 选项2：手动初始化

如果需要提前初始化：

```bash
cd f:\AIProjects\DesignAssistant
python data-layer\auto_init.py
```

**强制重新初始化**（清空所有数据）：
```bash
python data-layer\auto_init.py --force
```

---

### 第三步：验证部署

运行测试脚本验证环境：

```bash
# 如果携带了测试脚本
python data-layer\test_phase1.py

# 或者手动验证
python data-layer\consistency_validator.py
```

---

## 🔄 数据迁移场景

### 场景1：从机器A迁移到机器B（保留数据）

**步骤**：

1. **在机器A上打包**：
   ```bash
   # 打包整个项目目录
   tar -czf digital-employee-system.tar.gz DesignAssistant/
   ```

2. **传输到机器B**：
   - 使用U盘、网盘、Git等方式传输

3. **在机器B上解压**：
   ```bash
   tar -xzf digital-employee-system.tar.gz
   cd DesignAssistant
   ```

4. **验证数据**：
   ```bash
   python data-layer\consistency_validator.py
   ```

**结果**：所有员工、项目、任务数据完整保留

---

### 场景2：在新机器上从零开始

**步骤**：

1. **只复制核心文件**（约50KB）：
   - SKILL文件
   - auto_init.py
   - data_access.py
   - consistency_validator.py
   - DATA_SCHEMA.md

2. **首次运行时自动初始化**：
   - 调用任何SKILL
   - 系统自动创建数据层

3. **开始使用**：
   - 招聘新员工
   - 创建新项目

**结果**：干净的新环境，无历史数据

---

### 场景3：团队协作（共享数据）

**方案A：使用Git**

```bash
# 在机器A上
git init
git add .
git commit -m "Initial commit"
git push origin main

# 在机器B上
git clone <repository-url>
cd DesignAssistant
```

**方案B：使用共享文件夹**

- 将整个项目目录放在共享网络驱动器
- 团队成员直接访问共享目录

**方案C：使用云同步**

- 使用OneDrive、Dropbox等云同步服务
- 自动同步所有文件

---

## 📋 最小文件清单

### 核心文件（必需）

| 文件 | 大小 | 说明 |
|------|------|------|
| SKILL_V2.md | ~14KB | Skill 1定义 |
| data-layer/auto_init.py | ~8KB | 自动初始化脚本 |
| data-layer/data_access.py | ~12KB | 数据访问类 |
| data-layer/consistency_validator.py | ~10KB | 一致性校验 |
| data-layer/DATA_SCHEMA.md | ~6KB | 数据格式规范 |

**总计**：约 50KB（5个文件）

### 可选文件（推荐）

| 文件 | 大小 | 说明 |
|------|------|------|
| data-layer/test_phase1.py | ~10KB | 测试脚本 |
| data-layer/TESTING_GUIDE.md | ~8KB | 测试指南 |
| data-layer/README.md | ~2KB | 使用说明 |
| data-layer/SKILL1_API.md | ~6KB | 接口文档 |

**总计**：约 76KB（9个文件）

---

## 🚀 快速部署命令

### Windows

```powershell
# 创建项目目录
mkdir f:\AIProjects\DesignAssistant
cd f:\AIProjects\DesignAssistant

# 复制核心文件（假设从U盘复制）
copy E:\digital-employee\*.* .

# 自动初始化
python data-layer\auto_init.py

# 验证
python data-layer\consistency_validator.py
```

### Linux/Mac

```bash
# 创建项目目录
mkdir -p ~/Projects/DesignAssistant
cd ~/Projects/DesignAssistant

# 复制核心文件
cp -r /path/to/source/* .

# 自动初始化
python3 data-layer/auto_init.py

# 验证
python3 data-layer/consistency_validator.py
```

---

## 🔧 常见问题

### Q1：初始化失败怎么办？

**原因**：可能是权限问题或路径不存在

**解决方案**：
```bash
# 检查当前目录
pwd

# 检查权限
ls -la

# 手动创建目录
mkdir -p data-layer

# 重新运行初始化
python data-layer/auto_init.py --force
```

---

### Q2：如何清空所有数据重新开始？

**方案A：使用强制初始化**
```bash
python data-layer/auto_init.py --force
```

**方案B：手动删除数据层**
```bash
# 删除数据层目录
rm -rf data-layer/employees data-layer/projects data-layer/tasks data-layer/assets data-layer/logs

# 重新初始化
python data-layer/auto_init.py
```

---

### Q3：如何备份数据？

**方案A：完整备份**
```bash
# 备份整个项目
tar -czf backup-$(date +%Y%m%d).tar.gz DesignAssistant/
```

**方案B：只备份数据层**
```bash
# 只备份数据
tar -czf data-backup-$(date +%Y%m%d).tar.gz data-layer/
```

**方案C：使用Git**
```bash
git add .
git commit -m "Backup: $(date +%Y-%m-%d)"
git push
```

---

### Q4：如何在多台机器间同步？

**推荐方案**：使用Git

```bash
# 机器A：提交更改
git add .
git commit -m "Update employee data"
git push

# 机器B：拉取更新
git pull
```

**注意**：如果多人同时修改，可能产生冲突，需要手动解决。

---

## 📊 部署方案选择指南

| 场景 | 推荐方案 | 携带文件 | 初始化方式 |
|------|---------|---------|-----------|
| 首次部署 | 方案B | 核心文件（50KB） | 自动初始化 |
| 数据迁移 | 方案A | 完整目录 | 无需初始化 |
| 团队协作 | Git | 完整目录 | Git clone |
| 开发测试 | 方案B | 核心文件 | 自动初始化 |
| 生产环境 | 方案A | 完整目录 | 无需初始化 |

---

## ✅ 部署检查清单

部署完成后，使用以下清单验证：

- [ ] 核心文件已复制
- [ ] 数据层已初始化（目录和JSON文件存在）
- [ ] 一致性校验通过
- [ ] 可以正常调用SKILL
- [ ] 可以创建新员工
- [ ] 可以创建新项目

---

## 🎉 总结

### 方案B（轻量部署）的优势

1. **极简部署**：只需5个文件（50KB）
2. **自动初始化**：首次运行自动创建数据层
3. **版本控制友好**：适合Git管理
4. **跨平台**：Windows/Linux/Mac通用
5. **可靠性高**：标准化的初始化流程

### 推荐实践

- ✅ **开发环境**：使用方案B（轻量部署）
- ✅ **生产环境**：使用方案A（完整部署）
- ✅ **团队协作**：使用Git + 方案A
- ✅ **个人使用**：使用方案B + 定期备份

---

*最后更新：2026-02-12*
