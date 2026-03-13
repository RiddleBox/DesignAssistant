# RAG系统 API 接口文档

## 概述

本文档描述 RAG（Retrieval-Augmented Generation）系统的三个核心 API 接口：
1. `/retrieve` - 文档检索接口
2. `/generate` - 回答生成接口
3. `/rag` - 完整 RAG 流程接口

**版本**: v1.0 (Phase 2.4 MVP)
**基础URL**: `http://localhost:8000/api/v1`

---

## 1. 文档检索接口

### `POST /retrieve`

根据用户查询检索相关文档。

#### 请求参数

```json
{
  "query": "如何设计游戏的付费系统？",
  "top_k": 5
}
```

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| query | string | 是 | 用户查询文本，最大1000字符 | - |
| top_k | integer | 否 | 返回文档数量，范围1-20 | 5 |

#### 响应示例

```json
{
  "documents": [
    {
      "id": "kb_035",
      "title": "游戏付费模式对比分析",
      "content": "游戏付费模式的对比分析：\n\n主要付费模式：\n1. 免费游戏（F2P）...",
      "category": "market_trend",
      "tags": ["付费模式", "商业模式", "F2P", "买断制"],
      "metadata": {
        "source": "游戏商业模式分析2024",
        "confidence": 0.88,
        "last_updated": "2024-02-18"
      },
      "score": 0.8523
    },
    {
      "id": "kb_005",
      "title": "免费游戏（F2P）经济系统设计",
      "content": "免费游戏经济系统的设计原则和最佳实践...",
      "category": "game_design",
      "tags": ["F2P", "经济系统", "货币设计", "商业化"],
      "metadata": {
        "source": "F2P游戏设计指南2024",
        "confidence": 0.90,
        "last_updated": "2024-01-10"
      },
      "score": 0.7891
    }
  ],
  "total": 2,
  "query_time_ms": 45
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| documents | array | 检索到的文档列表 |
| documents[].id | string | 文档唯一ID |
| documents[].title | string | 文档标题 |
| documents[].content | string | 文档内容 |
| documents[].category | string | 文档分类 |
| documents[].tags | array | 文档标签 |
| documents[].metadata | object | 文档元数据 |
| documents[].score | float | 相似度分数（0-1） |
| total | integer | 返回文档总数 |
| query_time_ms | integer | 检索耗时（毫秒） |

#### 错误响应

```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "查询文本不能为空"
  }
}
```

**错误码**：
- `INVALID_QUERY` - 查询参数无效
- `QUERY_TOO_LONG` - 查询文本过长
- `INVALID_TOP_K` - top_k 参数超出范围
- `INTERNAL_ERROR` - 服务器内部错误

---

## 2. 回答生成接口

### `POST /generate`

基于检索到的文档生成回答。

#### 请求参数

```json
{
  "query": "如何设计游戏的付费系统？",
  "context_ids": ["kb_035", "kb_005", "kb_038"],
  "temperature": 0.7
}
```

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| query | string | 是 | 用户查询文本，最大1000字符 | - |
| context_ids | array | 是 | 上下文文档ID列表，最多10个 | - |
| temperature | float | 否 | 生成随机性，范围0-1 | 0.7 |

#### 响应示例

```json
{
  "answer": "游戏付费系统的设计需要考虑以下几个关键方面：\n\n1. 付费模式选择[1]：\n   - F2P（免费游戏）：适合移动游戏和网游，通过IAP和广告变现\n   - 买断制：适合主机和PC单机游戏\n   - 订阅制：适合MMO和云游戏\n\n2. 经济系统设计[2]：\n   - 多层货币结构：硬货币（付费）+ 软货币（游戏内获得）\n   - 合理的货币获取和消耗平衡\n   - 避免Pay-to-Win，保证公平性\n\n3. 运营活动配合[3]：\n   - 限时礼包和折扣活动\n   - 首充双倍等激励机制\n   - 月卡和通行证系统\n\n建议根据游戏类型、目标用户和平台特性选择合适的付费模式。",
  "sources": [
    {
      "id": "kb_035",
      "title": "游戏付费模式对比分析",
      "score": 0.8523
    },
    {
      "id": "kb_005",
      "title": "免费游戏（F2P）经济系统设计",
      "score": 0.7891
    },
    {
      "id": "kb_038",
      "title": "游戏运营活动设计",
      "score": 0.7234
    }
  ],
  "confidence": 0.85,
  "generation_time_ms": 2340
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| answer | string | 生成的回答 |
| sources | array | 引用的来源文档 |
| sources[].id | string | 文档ID |
| sources[].title | string | 文档标题 |
| sources[].score | float | 相似度分数 |
| confidence | float | 回答置信度（0-1） |
| generation_time_ms | integer | 生成耗时（毫秒） |

#### 错误响应

```json
{
  "error": {
    "code": "INVALID_CONTEXT",
    "message": "上下文文档ID不能为空"
  }
}
```

**错误码**：
- `INVALID_QUERY` - 查询参数无效
- `INVALID_CONTEXT` - 上下文参数无效
- `CONTEXT_NOT_FOUND` - 文档ID不存在
- `GENERATION_FAILED` - 生成失败
- `INTERNAL_ERROR` - 服务器内部错误

---

## 3. 完整 RAG 流程接口

### `POST /rag`

一站式 RAG 接口，自动完成检索和生成。

#### 请求参数

```json
{
  "query": "如何设计游戏的付费系统？",
  "top_k": 5,
  "temperature": 0.7
}
```

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| query | string | 是 | 用户查询文本，最大1000字符 | - |
| top_k | integer | 否 | 检索文档数量，范围1-20 | 5 |
| temperature | float | 否 | 生成随机性，范围0-1 | 0.7 |

#### 响应示例

```json
{
  "query": "如何设计游戏的付费系统？",
  "answer": "游戏付费系统的设计需要考虑以下几个关键方面：\n\n1. 付费模式选择[1]：...",
  "sources": [
    {
      "id": "kb_035",
      "title": "游戏付费模式对比分析",
      "content": "游戏付费模式的对比分析：...",
      "category": "market_trend",
      "tags": ["付费模式", "商业模式", "F2P", "买断制"],
      "metadata": {
        "source": "游戏商业模式分析2024",
        "confidence": 0.88,
        "last_updated": "2024-02-18"
      },
      "score": 0.8523
    }
  ],
  "confidence": 0.85,
  "retrieval_time_ms": 45,
  "generation_time_ms": 2340,
  "total_time_ms": 2385
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| query | string | 用户查询 |
| answer | string | 生成的回答 |
| sources | array | 引用的来源文档（完整信息） |
| confidence | float | 回答置信度（0-1） |
| retrieval_time_ms | integer | 检索耗时（毫秒） |
| generation_time_ms | integer | 生成耗时（毫秒） |
| total_time_ms | integer | 总耗时（毫秒） |

#### 错误响应

```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "查询文本不能为空"
  }
}
```

**错误码**：
- `INVALID_QUERY` - 查询参数无效
- `NO_RESULTS` - 未检索到相关文档
- `GENERATION_FAILED` - 生成失败
- `INTERNAL_ERROR` - 服务器内部错误

---

## 通用说明

### 认证

当前 MVP 版本暂不需要认证。生产环境建议添加 API Key 认证：

```
Authorization: Bearer YOUR_API_KEY
```

### 限流

建议限流策略：
- 每个 IP：100 请求/分钟
- 每个 API Key：1000 请求/分钟

### 响应格式

所有接口统一返回 JSON 格式，Content-Type 为 `application/json`。

### HTTP 状态码

- `200 OK` - 请求成功
- `400 Bad Request` - 请求参数错误
- `404 Not Found` - 资源不存在
- `429 Too Many Requests` - 请求过于频繁
- `500 Internal Server Error` - 服务器内部错误

### 性能指标

**目标延迟**（P95）：
- `/retrieve`: < 100ms
- `/generate`: < 3000ms
- `/rag`: < 3500ms

---

## 使用示例

### Python

```python
import requests

# 1. 检索文档
response = requests.post(
    "http://localhost:8000/api/v1/retrieve",
    json={
        "query": "如何设计游戏的付费系统？",
        "top_k": 5
    }
)
result = response.json()
print(f"检索到 {result['total']} 条文档")

# 2. 完整 RAG
response = requests.post(
    "http://localhost:8000/api/v1/rag",
    json={
        "query": "如何设计游戏的付费系统？",
        "top_k": 5,
        "temperature": 0.7
    }
)
result = response.json()
print(f"回答: {result['answer']}")
print(f"置信度: {result['confidence']}")
```

### cURL

```bash
# 检索文档
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何设计游戏的付费系统？",
    "top_k": 5
  }'

# 完整 RAG
curl -X POST http://localhost:8000/api/v1/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何设计游戏的付费系统？",
    "top_k": 5,
    "temperature": 0.7
  }'
```

---

## 更新日志

### v1.0 (2025-03-13)
- 初始版本
- 实现三个核心接口：retrieve、generate、rag
- 支持 40 条知识文档
- 向量维度：2048（智谱 embedding-3）

---

## 联系方式

如有问题或建议，请联系：
- 项目负责人：EMP-022（RAG架构师）
- 邮箱：[项目邮箱]
