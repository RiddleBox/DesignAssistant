# Phase 2.4 文档目录说明

**目录用途**: Phase 2.4 模块级文档中心
**维护人**: EMP-021（知识库架构师）
**最后更新**: 2026-03-13

---

## 目录结构

```
phase2.4_implementation/
├── docs/                           # 模块级文档（本目录）
│   ├── README.md                   # 本文档
│   └── SYSTEM_EVOLUTION_ROADMAP.md # 系统演进路线图
│
└── rag_system/                     # RAG 系统实现
    ├── docs/                       # RAG 系统技术文档
    │   ├── API_DOCUMENTATION.md           # API 接口文档
    │   ├── SYSTEM_VALIDATION_REPORT.md    # 系统验证报告
    │   ├── benchmark_report.json          # 性能基线数据
    │   ├── rag_pipeline_validation.md     # RAG 流程验证
    │   └── vector_index_validation.md     # 向量索引验证
    │
    ├── core/                       # 核心代码
    ├── api/                        # API 接口
    ├── data/                       # 数据和索引
    └── tests/                      # 测试脚本
```

---

## 文档分类

### 一、模块级文档（本目录）

**用途**: 跨子系统的规划、架构和治理文档

**当前文档**:
1. **SYSTEM_EVOLUTION_ROADMAP.md** - 系统演进路线图
   - 编写人：EMP-021（知识库架构师）
   - 内容：MVP → 增强版 → 完整版的演进路径
   - 受众：所有团队成员 + 下游模块（2.1/2.2/2.3）
   - 更新频率：每个版本发布后

**未来可能增加**:
- `ARCHITECTURE_OVERVIEW.md` - 整体架构说明（如有多个子系统）
- `INTEGRATION_GUIDE.md` - 跨子系统集成指南
- `PHASE2.4_WORKLOG.md` - 模块级工作日志

---

### 二、RAG 系统技术文档（rag_system/docs/）

**用途**: RAG 系统的实现细节、接口规范和验证报告

**当前文档**:

#### 2.1 接口与规范
- **API_DOCUMENTATION.md** - API 接口文档
  - 编写人：EMP-026（接口设计师）
  - 内容：三个核心 API 的请求/响应规范
  - 受众：下游模块开发者
  - 状态：✅ 已冻结（v1.0）

#### 2.2 验证与测试
- **SYSTEM_VALIDATION_REPORT.md** - 系统验证报告
  - 编写人：EMP-021 + 全体团队
  - 内容：功能验证、性能基线、验收结论
  - 受众：项目管理者 + 质量保证
  - 状态：✅ 已完成（MVP v1.0）

- **benchmark_report.json** - 性能基线数据
  - 生成人：EMP-025（检索优化专家）
  - 内容：检索/RAG 性能指标（JSON 格式）
  - 受众：性能优化团队
  - 状态：✅ 已建立（MVP v1.0）

- **rag_pipeline_validation.md** - RAG 流程验证
  - 内容：端到端流程测试记录
  - 状态：✅ 已完成

- **vector_index_validation.md** - 向量索引验证
  - 内容：索引构建和加载测试记录
  - 状态：✅ 已完成

---

## 文档使用指南

### 新成员入职

**阅读顺序**:
1. 本 README（了解文档结构）
2. `SYSTEM_EVOLUTION_ROADMAP.md`（了解系统全貌和演进方向）
3. `rag_system/docs/API_DOCUMENTATION.md`（了解接口规范）
4. `rag_system/docs/SYSTEM_VALIDATION_REPORT.md`（了解当前状态）

### 下游模块接入

**必读文档**:
1. `rag_system/docs/API_DOCUMENTATION.md` - 接口规范
2. `SYSTEM_EVOLUTION_ROADMAP.md` 第七节 - 下游接入指南

### 系统优化

**参考文档**:
1. `rag_system/docs/benchmark_report.json` - 当前性能基线
2. `SYSTEM_EVOLUTION_ROADMAP.md` 第三~五节 - 优化方向
3. `SYSTEM_EVOLUTION_ROADMAP.md` 第六节 - 技术债务管理

---

## 文档维护规范

### 新增文档

**模块级文档**（本目录）:
- 跨子系统的规划、架构、治理文档
- 命名格式：`大写_下划线.md`（如 `INTEGRATION_GUIDE.md`）
- 需在本 README 中更新索引

**RAG 系统文档**（rag_system/docs/）:
- RAG 系统的实现细节、接口、测试文档
- 命名格式：`大写_下划线.md` 或 `小写_下划线.json`
- 需在 rag_system/docs/ 中维护独立索引（如需要）

### 更新文档

**更新频率**:
- 接口文档：版本变更时更新
- 验证报告：每次验证后更新
- 演进路线图：每个版本发布后更新
- 性能基线：每次 benchmark 后更新

**更新责任人**:
- 模块级文档：EMP-021（知识库架构师）
- 接口文档：EMP-026（接口设计师）
- 验证报告：EMP-021 + 全体团队
- 性能基线：EMP-025（检索优化专家）

---

## 文档状态标记

使用以下标记表示文档状态：

- ✅ **已完成** - 文档已完成且经过审核
- 🔄 **进行中** - 文档正在编写或更新
- ⏳ **待编写** - 计划编写但尚未开始
- ⚠️ **需更新** - 文档已过时，需要更新
- 🔒 **已冻结** - 文档已冻结，不再变更（如接口规范）

---

## 常见问题

### Q1: 为什么有两个 docs 目录？

**A**:
- `phase2.4_implementation/docs/`：模块级文档，跨子系统的规划和架构
- `rag_system/docs/`：RAG 系统的技术文档，实现细节和接口规范

当前 Phase 2.4 只有 RAG 系统一个子系统，所以大部分文档在 `rag_system/docs/`。未来如果增加其他子系统（如知识图谱、推荐系统），模块级文档会放在顶层 `docs/`。

### Q2: 我应该把新文档放在哪里？

**A**:
- **跨子系统的规划/架构文档** → `phase2.4_implementation/docs/`
- **RAG 系统的实现/接口/测试文档** → `rag_system/docs/`
- **不确定？** → 问 EMP-021（知识库架构师）

### Q3: 如何找到某个主题的文档？

**A**: 使用本 README 的文档分类索引，或直接搜索文件名。

---

## 联系人

- **文档架构**: EMP-021（知识库架构师）
- **接口文档**: EMP-026（接口设计师）
- **性能文档**: EMP-025（检索优化专家）

---

**文档状态**: ✅ 已完成
**版本**: v1.0
**下次更新**: 当增加新文档或调整目录结构时
