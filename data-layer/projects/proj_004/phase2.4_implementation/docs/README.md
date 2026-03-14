# Phase 2.4 文档目录说明

**目录用途**: Phase 2.4 模块级文档中心
**维护人**: EMP-021（知识库架构师）
**最后更新**: 2026-03-14

---

## 目录结构

```
phase2.4_implementation/
├── docs/                           # 模块级文档（本目录）
│   ├── README.md                   # 本文档
│   ├── PHASE2_4_ACCEPTANCE_ASSESSMENT.md # Phase 2.4 验收评估归档
│   ├── PHASE2_4_PRIORITY_AND_REAL_CAPABILITY_QA.md # 优先级拍板与真实能力问答归档
│   ├── PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md # 第一性原理与设计指导
│   ├── PHASE2_4_PRODUCT_OPTIMIZATION_RISK_REVIEW.md # 当前 RAG pipeline 的产品优化风险复盘
│   ├── PHASE2_4_TECHNICAL_VALIDITY_VS_PRODUCT_RISK_MATRIX.md # 技术合理性 / 产品风险对照表
│   ├── PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md # 2.4 → 2.1 上下文协议草案
│   ├── PHASE2_4_TO_2_1_OPTIMIZATION_BACKLOG_DRAFT.md # 2.4 → 2.1 优化 Backlog 草案
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
1. **PHASE2_4_ACCEPTANCE_ASSESSMENT.md** - Phase 2.4 验收评估归档
   - 内容：当前交付验收结论、模块级分析、风险边界、后续执行指令
   - 受众：项目管理者、模块负责人、下游协作团队
   - 状态：✅ 已完成（归档版 v1.0）

2. **PHASE2_4_PRIORITY_AND_REAL_CAPABILITY_QA.md** - 优先级拍板与真实能力问答归档
   - 内容：当前阶段主副线执行策略、A/B 分工边界、真实 embedding 与真实 LLM 的概念解释、验收口径说明
   - 受众：项目管理者、Phase 2.4 持续实现团队、Phase 2.1 并行团队
   - 状态：✅ 已完成（归档版 v1.0）

3. **PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md** - 第一性原理与设计指导
   - 内容：从第一性原理定义 `2.4` 的本质、规划问题、设计原则、实现优先级与优化评审口径
   - 受众：Phase 2.4 持续实现团队、Phase 2.1/2.2/2.3 下游模块、项目管理者
   - 状态：✅ 已完成（参考版 v1.0）

4. **PHASE2_4_PRODUCT_OPTIMIZATION_RISK_REVIEW.md** - 当前 RAG pipeline 的产品优化风险复盘
   - 内容：系统化归档“问题 2”的完整回答，聚焦当前真实 RAG pipeline 在哪些方面技术上成立、但产品上仍可能未对齐目标
   - 受众：Phase 2.4 持续实现团队、项目管理者、后续参与复盘与优化的角色
   - 状态：✅ 已完成（参考版 v1.0）

5. **PHASE2_4_TECHNICAL_VALIDITY_VS_PRODUCT_RISK_MATRIX.md** - 技术合理性 / 产品风险对照表
   - 内容：按知识组织、召回、排序、协议、生成、评测、日志、下游适配等层次，对比“为什么当前方案技术上合理”与“为什么它产品上未必最优”
   - 受众：Phase 2.4 持续实现团队、设计评审参与者、项目管理者、Phase 2.1/2.2/2.3 协作方
   - 状态：✅ 已完成（评审版 v1.0）

6. **PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md** - `2.4 → 2.1` 上下文协议草案
   - 内容：定义 `2.4` 应如何以 `ContextPacket` 形式向 `2.1` 交付可解释、可追溯、带用途标记的证据级上下文
   - 受众：Phase 2.4 持续实现团队、Phase 2.1 结构化契约/实现/评测角色、项目管理者
   - 状态：✅ 已完成（Draft v0.1）

7. **PHASE2_4_TO_2_1_OPTIMIZATION_BACKLOG_DRAFT.md** - `2.4 → 2.1` 优化 Backlog 草案
   - 内容：将前述第一性原理判断转成面向执行的 `P0 / P1 / P2` 优化项，便于后续排期、评审和协同推进
   - 受众：Phase 2.4 持续实现团队、Phase 2.1 设计/实现/评测角色、项目管理者
   - 状态：✅ 已完成（Draft v0.1）

8. **SYSTEM_EVOLUTION_ROADMAP.md** - 系统演进路线图
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
2. `PHASE2_4_ACCEPTANCE_ASSESSMENT.md`（了解当前验收判断与真实边界）
3. `PHASE2_4_PRIORITY_AND_REAL_CAPABILITY_QA.md`（了解当前主副线策略与真实能力口径）
4. `PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md`（理解 `2.4` 的第一性原理、设计原则与优化判断标准）
5. `PHASE2_4_PRODUCT_OPTIMIZATION_RISK_REVIEW.md`（理解当前真实 RAG pipeline 的产品优化风险与结构性偏差）
6. `PHASE2_4_TECHNICAL_VALIDITY_VS_PRODUCT_RISK_MATRIX.md`（用于系统化把握“技术成立”和“产品最优”之间的差距）
7. `PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md`（理解 `2.4` 面向 `2.1` 的具体交付协议草案）
8. `PHASE2_4_TO_2_1_OPTIMIZATION_BACKLOG_DRAFT.md`（理解 `2.4 -> 2.1` 的执行优先级与优化 backlog）
9. `SYSTEM_EVOLUTION_ROADMAP.md`（了解系统全貌和演进方向）
10. `rag_system/docs/API_DOCUMENTATION.md`（了解接口规范）
11. `rag_system/docs/SYSTEM_VALIDATION_REPORT.md`（了解当前状态）

### 下游模块接入

**必读文档**:
1. `rag_system/docs/API_DOCUMENTATION.md` - 接口规范
2. `SYSTEM_EVOLUTION_ROADMAP.md` 第七节 - 下游接入指南
3. `PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md` - 理解 `2.4` 的产品定位与上下文供应职责
4. `PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md` - 理解 `2.4 -> 2.1` 的上下文交付草案

### 系统优化

**参考文档**:
1. `rag_system/docs/benchmark_report.json` - 当前性能基线
2. `SYSTEM_EVOLUTION_ROADMAP.md` 第三~五节 - 优化方向
3. `PHASE2_4_FIRST_PRINCIPLES_AND_DESIGN_GUIDANCE.md` - 第一性原理、设计原则与优化评审口径
4. `PHASE2_4_PRODUCT_OPTIMIZATION_RISK_REVIEW.md` - 当前 pipeline 的产品层风险复盘
5. `PHASE2_4_TECHNICAL_VALIDITY_VS_PRODUCT_RISK_MATRIX.md` - 技术合理性 / 产品风险对照分析
6. `PHASE2_4_TO_2_1_CONTEXT_PROTOCOL_DRAFT.md` - `2.4 -> 2.1` 协议草案
7. `PHASE2_4_TO_2_1_OPTIMIZATION_BACKLOG_DRAFT.md` - `2.4 -> 2.1` backlog 草案
8. `SYSTEM_EVOLUTION_ROADMAP.md` 第六节 - 技术债务管理

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
**版本**: v1.2
**下次更新**: 当增加新文档或调整目录结构时
