# Design Assistant - AI驱动的设计协作系统

## 📋 项目简介

Design Assistant 是一个基于AI的设计协作系统，通过8个专业化的Skill模块，为设计团队提供全方位的项目管理、任务协调、资产管理和知识共享支持。

## 🎯 核心功能

### 8大核心Skill模块

1. **SKILL0 - 协调器 (Coordinator)**
   - 统一入口和任务分发
   - 智能路由到专业Skill

2. **SKILL1 - 团队协调 (Team Coordinator)**
   - 员工信息管理
   - 团队资源协调

3. **SKILL2 - 项目协作 (Project Collaboration)**
   - 项目创建与管理
   - 跨团队协作支持

4. **SKILL3 - 任务管理 (Task Management)**
   - 任务创建、分配、追踪
   - 里程碑管理

5. **SKILL4 - 资产管理 (Asset Management)**
   - 设计资产存储与检索
   - 版本控制

6. **SKILL5 - 工作日志分析 (Work Log Analytics)**
   - 工作记录追踪
   - 数据分析与洞察

7. **SKILL6 - 知识共享 (Knowledge Sharing)**
   - 知识库管理
   - 最佳实践分享

8. **SKILL7 - 团队模板 (Team Templates)**
   - 模板库管理
   - 快速项目启动

9. **SKILL8 - 团队顾问 (Team Advisor)**
   - 项目总结与分析
   - 智能建议与优化

## 🚀 快速开始

### 零依赖部署

本系统采用"零依赖"设计，只需8个Markdown Skill文件即可运行：

```bash
# 最小部署（仅需Skill文件）
SKILL0_COORDINATOR.md
SKILL_V2.md
SKILL2_PROJECT_COLLABORATION.md
SKILL3_TASK_MANAGEMENT.md
SKILL4_ASSET_MANAGEMENT.md
SKILL5_WORK_LOG_ANALYTICS.md
SKILL6_KNOWLEDGE_SHARING.md
SKILL7_TEAM_TEMPLATES.md
SKILL8_TEAM_ADVISOR.md
```

### 完整部署（含数据持久化）

如需数据持久化功能，可选择部署data-layer：

```bash
# 克隆仓库
git clone [your-repo-url]

# 进入目录
cd DesignAssistant

# 初始化数据层（可选）
python data-layer/auto_init.py
```

## 📁 项目结构

```
DesignAssistant/
├── SKILL*.md                    # 8个核心Skill文件
├── data-layer/                  # 数据持久化层（可选）
│   ├── employees/              # 员工数据
│   ├── projects/               # 项目数据
│   ├── tasks/                  # 任务数据
│   ├── assets/                 # 资产数据
│   ├── logs/                   # 工作日志
│   └── *.py                    # Python工具脚本
├── .codebuddy/                 # 开发计划文档
└── *.md                        # 各类文档
```

## 📖 文档

- [部署指南](DEPLOYMENT_GUIDE.md)
- [迁移指南](MIGRATION_GUIDE.md)
- [零依赖部署](ZERO_DEPENDENCY_DEPLOYMENT.md)
- [实施进度](IMPLEMENTATION_PROGRESS.md)
- [项目总结](PROJECT_FINAL_SUMMARY.md)

## 🎮 示例项目

- [POE2巴别塔设计](POE2_BABEL_TOWER_DESIGN.md) - 游戏设计案例
- [教程：游戏设计示例](TUTORIAL_GAME_DESIGN_EXAMPLE.md)

## 🔧 技术特点

- **零依赖设计**：核心功能仅需Markdown文件
- **模块化架构**：8个独立Skill，职责清晰
- **可选持久化**：支持数据层扩展
- **AI驱动**：基于大语言模型的智能协作
- **易于迁移**：复制Skill文件即可部署

## 📊 开发阶段

- ✅ Phase 1: 核心Skill开发
- ✅ Phase 2: 数据层集成
- ✅ Phase 3: 功能增强
- ✅ Phase 4: 测试与优化
- ✅ Phase 5: 文档完善

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

[MIT License](LICENSE)

## 📮 联系方式

如有问题或建议，欢迎通过Issue联系。

---

**注意**：本项目为AI辅助设计协作系统，需要配合支持Markdown Prompt的AI系统使用。
