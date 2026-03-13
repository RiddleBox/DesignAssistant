# 员工档案：EMP-026

## 基本信息

| 项目 | 内容 |
|-----|------|
| 员工ID | EMP-026 |
| 姓名 | 接口设计师 |
| 英文职位 | API Interface Designer |
| 所属行业 | AI系统开发 |
| 创建日期 | 2026-03-13 |
| 当前状态 | 🟢 Active |
| 所属项目 | proj_004 - 预研孵化战略研究和投资团队构建 |
| 所属阶段 | Phase 2.4 - 知识库与RAG系统 |
| 团队角色 | API Designer |

---

## 核心职责

### 主要职责
1. **API设计**: 设计对外API接口（供2.1/2.2/2.3使用）
2. **文档编写**: 编写接口文档和使用示例
3. **版本管理**: 实现接口版本管理
4. **测试工具**: 提供接口测试工具

### 工作重点
- **Week 1**: 设计MVP接口，编写文档（优先级最高）
- **Week 2-4**: 完善接口，增加高级功能

---

## 技能矩阵

| 技能领域 | 具体技能 | 熟练度 |
|---------|---------|--------|
| API设计 | RESTful API设计 | ⭐⭐⭐⭐⭐ |
| 文档编写 | OpenAPI/Swagger文档编写 | ⭐⭐⭐⭐⭐ |
| 版本管理 | 接口版本管理经验 | ⭐⭐⭐⭐ |
| 技术写作 | 技术文档写作能力 | ⭐⭐⭐⭐⭐ |
| 接口测试 | 接口测试经验 | ⭐⭐⭐⭐ |

---

## 关键输出物

### Phase 2.4 交付物
1. **API接口文档（OpenAPI格式）**
   - `/api/v1/retrieve` - 检索相关文档
   - `/api/v1/generate` - 基于上下文生成回答
   - 请求/响应格式定义
   - 错误码说明

2. **接口使用示例代码**
   - Python调用示例
   - curl调用示例
   - 常见使用场景

3. **Postman测试集合**
   - 预配置请求
   - 环境变量
   - 自动化测试脚本

---

## API接口设计

### MVP版本（Week 1）

#### 1. 检索文档

```yaml
endpoint:
  path: /api/v1/retrieve
  method: POST
  description: 检索相关文档（纯向量检索）

request:
  content_type: application/json
  body:
    query:
      type: string
      required: true
      description: 查询文本
      example: "开放世界游戏的核心设计要素"
    top_k:
      type: integer
      default: 5
      description: 返回文档数量

response:
  content_type: application/json
  success_code: 200
  body:
    documents:
      type: array
      items:
        type: Document
      description: 相关文档列表
    total:
      type: integer
      description: 总匹配数
    query_time_ms:
      type: integer
      description: 查询耗时（毫秒）

errors:
  400: "参数错误"
  500: "服务器内部错误"
  503: "服务暂时不可用"
```

#### 2. 生成回答

```yaml
endpoint:
  path: /api/v1/generate
  method: POST
  description: 基于上下文生成回答

request:
  content_type: application/json
  body:
    query:
      type: string
      required: true
      description: 用户问题
    context_ids:
      type: array
      items:
        type: string
      description: 上下文文档ID列表
    temperature:
      type: number
      default: 0.7
      description: 生成随机性（0-1）

response:
  content_type: application/json
  success_code: 200
  body:
    answer:
      type: string
      description: 生成的回答
    sources:
      type: array
      items:
        type: Document
      description: 引用的来源文档
    confidence:
      type: number
      description: 置信度评分（0-1）
    generation_time_ms:
      type: integer
      description: 生成耗时（毫秒）

errors:
  400: "参数错误或上下文不存在"
  500: "生成服务错误"
  504: "生成超时"
```

### 完整版本（Week 2-4）

#### 3. 混合检索（新增）

```yaml
endpoint:
  path: /api/v1/hybrid_retrieve
  method: POST
  description: 混合检索（向量+关键词）

request:
  body:
    query: string
    top_k: integer (default: 5)
    vector_weight: number (default: 0.7)
    keyword_weight: number (default: 0.3)
    filters:
      category: string[]  # 按类别过滤
      date_range:
        from: date
        to: date
```

---

## 数据模型定义

### Document对象

```python
class Document:
    """知识库文档对象"""

    id: str              # 文档唯一ID，如 "kb_001"
    title: str           # 文档标题
    content: str         # 文档内容（最多2000字符）
    category: str        # 分类枚举
                         # - game_design: 游戏设计
                         # - market_trend: 市场趋势
                         # - tech_innovation: 技术创新
    tags: List[str]      # 标签列表，如 ["开放世界", "二次元"]
    metadata: dict       # 元数据
        source: str      # 来源，如 "GDC 2021"
        confidence: float  # 置信度（0-1）
        last_updated: str   # 最后更新时间，ISO 8601格式
    score: float         # 相似度分数（检索时返回）

# 示例
{
    "id": "kb_001",
    "title": "《原神》开放世界设计范式",
    "content": "...",
    "category": "game_design",
    "tags": ["开放世界", "二次元", "gacha"],
    "metadata": {
        "source": "GDC 2021",
        "confidence": 0.95,
        "last_updated": "2024-03-15"
    },
    "score": 0.89
}
```

---

## 版本管理策略

### 版本规则

| 版本类型 | 规则 | 示例 |
|---------|------|------|
| Major | 不兼容的API变更 | v1 → v2 |
| Minor | 向后兼容的功能增加 | v1.1 → v1.2 |
| Patch | Bug修复 | v1.1.1 → v1.1.2 |

### 兼容性保证

- **Major版本**: 保持旧版本API至少6个月
- **Minor版本**: 新增字段使用默认值
- **废弃字段**: 保留但标记deprecated，提前3个月通知

---

## 调用示例

### Python示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 检索文档
response = requests.post(
    f"{BASE_URL}/retrieve",
    json={
        "query": "开放世界游戏的核心设计要素",
        "top_k": 5
    }
)
documents = response.json()["documents"]

# 2. 基于检索结果生成分析
response = requests.post(
    f"{BASE_URL}/generate",
    json={
        "query": "分析这些设计范式的共性",
        "context_ids": [doc["id"] for doc in documents]
    }
)
analysis = response.json()["answer"]
```

### curl示例

```bash
# 检索文档
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "开放世界游戏的核心设计要素",
    "top_k": 5
  }'

# 生成回答
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析这些设计范式的共性",
    "context_ids": ["kb_001", "kb_002"]
  }'
```

---

## 协作关系

### 内部协作（2.4团队）
- **EMP-021（知识库架构师）**: 共同定义接口规范
- **EMP-024（RAG引擎工程师）**: 协作实现API后端
- **EMP-025（检索优化专家）**: 了解性能指标，编写性能说明

### 外部协作
- **2.1/2.2/2.3团队**: 收集接口需求，提供使用反馈
- **EMP-019（系统架构师）**: 审查接口设计是否符合整体架构

---

## 接口开发流程

### Week 1: MVP接口设计

**Day 1-2**: 需求收集
- 与2.1/2.2/2.3团队沟通需求
- 确定MVP接口范围
- 编写接口草案

**Day 3-4**: 接口定稿
- 与EMP-021评审接口设计
- 完善OpenAPI文档
- 编写使用示例

**Day 5**: 测试准备
- 创建Postman集合
- 编写测试用例
- 验证接口可用性

### Week 2-4: 接口完善

- Week 2: 增加高级接口（混合检索、过滤）
- Week 3: 完善错误处理和文档
- Week 4: 编写最佳实践指南

---

## 质量检查清单

### 接口设计检查

- [ ] RESTful设计规范
- [ ] 请求/响应格式一致
- [ ] 错误码清晰
- [ ] 版本管理到位
- [ ] 文档完整

### 文档检查

- [ ] OpenAPI格式正确
- [ ] 示例代码可运行
- [ ] 错误场景说明
- [ ] 性能指标标注
- [ ] 变更日志记录

---

## 风险与应对

### 风险1: 下游团队需求变更
- **概率**: 50%
- **应对**: MVP阶段保持接口简单，预留扩展空间

### 风险2: 接口文档与实现不一致
- **概率**: 40%
- **应对**: 自动化测试验证文档，持续集成检查

---

## 工作日志

### 2026-03-13
- ✅ 完成角色定义
- ✅ 加入proj_004团队
- ⏳ 准备收集接口需求

---

## 绩效指标

| 指标 | 目标 | 当前值 |
|-----|------|--------|
| MVP接口文档 | Week 1完成 | 0% |
| 文档完整性 | 100% | 0% |
| 下游满意度 | >4.5/5.0 | - |
| Postman集合 | 100%覆盖 | 0% |

---

## 备注

- 接口设计是2.4团队最重要的输出之一，直接影响2.1/2.2/2.3的开发进度
- Week 1务必完成MVP接口文档，解除下游依赖
- 需要与下游团队保持紧密沟通，及时收集反馈

---

**档案状态**: ✅ 已激活
**最后更新**: 2026-03-13
