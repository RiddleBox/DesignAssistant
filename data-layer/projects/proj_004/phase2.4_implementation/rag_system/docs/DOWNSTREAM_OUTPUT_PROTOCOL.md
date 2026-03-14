# Phase 2.4 对下游输出协议规范

**文档类型**: 接口协议规范
**版本**: v1.0
**创建日期**: 2026-03-14
**适用范围**: Phase 2.4 → Phase 2.1/2.2/2.3

---

## 一、协议概述

### 1.1 目的

定义 Phase 2.4 RAG 系统对下游模块（Phase 2.1 情报解码、Phase 2.2 机会评估、Phase 2.3 决策建议）的标准输出格式，确保接口稳定性和数据一致性。

### 1.2 核心原则

1. **向后兼容**: 新增字段不破坏现有接口
2. **结构化输出**: 使用固定的 JSON 格式
3. **错误透明**: 明确的错误码和错误信息
4. **性能可观测**: 包含性能指标和追踪信息

---

## 二、核心接口

### 2.1 检索接口 (Retrieve)

**端点**: `POST /api/v1/retrieve`

**请求格式**:
```json
{
  "query": "用户查询文本",
  "top_k": 5,
  "filters": {
    "category": ["game_design", "market_trend"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

**响应格式**:
```json
{
  "status": "success",
  "data": {
    "query": "用户查询文本",
    "documents": [
      {
        "id": "kb_001",
        "title": "文档标题",
        "content": "文档内容...",
        "category": "game_design",
        "tags": ["标签1", "标签2"],
        "score": 0.8567,
        "metadata": {
          "source": "来源",
          "confidence": 0.9,
          "last_updated": "2024-03-01"
        }
      }
    ],
    "total_results": 5,
    "retrieval_time_ms": 25
  },
  "request_id": "req_20260314_001",
  "timestamp": "2026-03-14T10:30:00Z"
}
```

**字段说明**:
- `status`: 请求状态 (`success` | `error`)
- `documents`: 检索到的文档列表，按相似度降序排列
- `score`: 相似度分数 (0-1)，越高越相关
- `retrieval_time_ms`: 检索耗时（毫秒）
- `request_id`: 请求追踪ID

---

### 2.2 生成接口 (Generate)

**端点**: `POST /api/v1/generate`

**请求格式**:
```json
{
  "query": "用户问题",
  "context_docs": [
    {
      "id": "kb_001",
      "title": "文档标题",
      "content": "文档内容..."
    }
  ],
  "temperature": 0.7
}
```

**响应格式**:
```json
{
  "status": "success",
  "data": {
    "query": "用户问题",
    "answer": "生成的回答内容...",
    "confidence": 0.85,
    "sources": [
      {
        "id": "kb_001",
        "title": "文档标题",
        "relevance": "high"
      }
    ],
    "generation_time_ms": 5200
  },
  "request_id": "req_20260314_002",
  "timestamp": "2026-03-14T10:30:05Z"
}
```

**字段说明**:
- `answer`: 生成的回答文本
- `confidence`: 置信度 (0-1)，基于引用数量计算
- `sources`: 引用的文档来源
- `generation_time_ms`: 生成耗时（毫秒）

---

### 2.3 完整RAG接口 (RAG)

**端点**: `POST /api/v1/rag`

**请求格式**:
```json
{
  "query": "用户问题",
  "top_k": 5,
  "temperature": 0.7,
  "filters": {
    "category": ["game_design"]
  }
}
```

**响应格式**:
```json
{
  "status": "success",
  "data": {
    "query": "用户问题",
    "answer": "生成的回答内容...",
    "confidence": 0.85,
    "retrieved_docs": [
      {
        "id": "kb_001",
        "title": "文档标题",
        "content": "文档内容...",
        "category": "game_design",
        "tags": ["标签1", "标签2"],
        "score": 0.8567,
        "metadata": {
          "source": "来源",
          "confidence": 0.9,
          "last_updated": "2024-03-01"
        }
      }
    ],
    "sources": [
      {
        "id": "kb_001",
        "title": "文档标题",
        "relevance": "high"
      }
    ],
    "metrics": {
      "retrieval_time_ms": 25,
      "generation_time_ms": 5200,
      "total_time_ms": 5225
    }
  },
  "request_id": "req_20260314_003",
  "timestamp": "2026-03-14T10:30:05Z"
}
```

**字段说明**:
- `retrieved_docs`: 检索到的原始文档
- `sources`: 生成时引用的文档
- `metrics`: 性能指标

---

## 三、错误处理

### 3.1 错误响应格式

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_QUERY",
    "message": "查询文本不能为空",
    "details": {
      "field": "query",
      "constraint": "non-empty"
    }
  },
  "request_id": "req_20260314_004",
  "timestamp": "2026-03-14T10:30:00Z"
}
```

### 3.2 错误码定义

| 错误码 | HTTP状态码 | 说明 | 处理建议 |
|--------|-----------|------|---------|
| `INVALID_QUERY` | 400 | 查询参数无效 | 检查请求参数 |
| `EMPTY_RESULTS` | 200 | 检索无结果 | 正常情况，返回空列表 |
| `GENERATION_FAILED` | 500 | 生成失败 | 重试或降级处理 |
| `INDEX_NOT_FOUND` | 503 | 索引未加载 | 等待系统初始化 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 | 降低请求频率 |
| `INTERNAL_ERROR` | 500 | 内部错误 | 联系技术支持 |

---

## 四、数据模型

### 4.1 Document 模型

```python
{
  "id": str,              # 文档唯一标识，格式: kb_XXX
  "title": str,           # 文档标题
  "content": str,         # 文档内容（完整文本）
  "category": str,        # 分类: game_design | market_trend | tech_innovation
  "tags": List[str],      # 标签列表
  "score": float,         # 相似度分数 (0-1)，仅检索时有效
  "metadata": {
    "source": str,        # 来源
    "confidence": float,  # 置信度 (0-1)
    "last_updated": str   # 最后更新时间 (ISO 8601)
  }
}
```

### 4.2 Source 模型

```python
{
  "id": str,              # 文档ID
  "title": str,           # 文档标题
  "relevance": str        # 相关性: high | medium | low
}
```

### 4.3 Metrics 模型

```python
{
  "retrieval_time_ms": int,    # 检索耗时（毫秒）
  "generation_time_ms": int,   # 生成耗时（毫秒）
  "total_time_ms": int         # 总耗时（毫秒）
}
```

---

## 五、性能保证

### 5.1 延迟目标

| 接口 | P50 | P95 | P99 |
|------|-----|-----|-----|
| Retrieve | < 50ms | < 300ms | < 500ms |
| Generate | < 3000ms | < 10000ms | < 15000ms |
| RAG | < 3500ms | < 10500ms | < 20000ms |

### 5.2 可用性目标

- **可用性**: 99.9%
- **错误率**: < 1%
- **超时时间**: 30秒

---

## 六、使用示例

### 6.1 Python 客户端示例

```python
import requests

# RAG 查询
response = requests.post(
    "http://localhost:8000/api/v1/rag",
    json={
        "query": "游戏设计中如何提升玩家留存率？",
        "top_k": 5,
        "temperature": 0.7
    }
)

if response.status_code == 200:
    data = response.json()
    if data["status"] == "success":
        print(f"Answer: {data['data']['answer']}")
        print(f"Confidence: {data['data']['confidence']}")
        print(f"Sources: {len(data['data']['sources'])}")
    else:
        print(f"Error: {data['error']['message']}")
```

### 6.2 JavaScript 客户端示例

```javascript
const response = await fetch('http://localhost:8000/api/v1/rag', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: '游戏设计中如何提升玩家留存率？',
    top_k: 5,
    temperature: 0.7
  })
});

const data = await response.json();
if (data.status === 'success') {
  console.log('Answer:', data.data.answer);
  console.log('Confidence:', data.data.confidence);
}
```

---

## 七、版本演进

### 7.1 当前版本 (v1.0)

- ✅ 基础检索、生成、RAG接口
- ✅ 固定输出格式
- ✅ 错误处理机制
- ✅ 性能指标

### 7.2 未来版本 (v1.1+)

**计划增强**:
- 结构化输出（key_points, evidence, caveats）
- 流式响应（SSE）
- 批量查询接口
- 缓存控制（Cache-Control）
- 元数据过滤增强

**兼容性承诺**:
- v1.x 系列保持向后兼容
- 新增字段不影响现有字段
- 废弃字段提前通知（至少1个版本）

---

## 八、下游接入指南

### 8.1 Phase 2.1 (情报解码)

**推荐接口**: `POST /api/v1/retrieve`

**使用场景**:
- 检索行业术语定义
- 查找信号分类标准
- 获取市场趋势数据

**示例**:
```python
response = requests.post("/api/v1/retrieve", json={
    "query": "游戏行业的关键信号类型",
    "top_k": 5,
    "filters": {"category": ["market_trend"]}
})
```

### 8.2 Phase 2.2 (机会评估)

**推荐接口**: `POST /api/v1/rag`

**使用场景**:
- 获取评估框架
- 查找相似案例
- 生成评估建议

**示例**:
```python
response = requests.post("/api/v1/rag", json={
    "query": "如何评估一个新游戏项目的投资价值？",
    "top_k": 10,
    "temperature": 0.7
})
```

### 8.3 Phase 2.3 (决策建议)

**推荐接口**: `POST /api/v1/rag`

**使用场景**:
- 获取决策模型
- 查找资源分配标准
- 生成决策建议

**示例**:
```python
response = requests.post("/api/v1/rag", json={
    "query": "游戏项目的资源分配模型",
    "top_k": 5,
    "filters": {"category": ["game_design", "market_trend"]}
})
```

---

## 九、测试与验证

### 9.1 测试数据

测试日志位置: `docs/real_rag_test_log.json`

包含3组真实测试样例：
1. 游戏设计中如何提升玩家留存率？
2. Battle Royale游戏的核心设计要素有哪些？
3. 独立游戏开发面临的主要挑战是什么？

### 9.2 验证清单

下游模块接入前请验证：
- [ ] 能正常解析响应JSON
- [ ] 能处理错误响应
- [ ] 能处理空结果
- [ ] 能处理超时情况
- [ ] 能记录request_id用于追踪

---

**文档状态**: ✅ 已完成
**版本**: v1.0
**下次更新**: 当接口有变更时
**负责人**: EMP-026（接口设计师）
