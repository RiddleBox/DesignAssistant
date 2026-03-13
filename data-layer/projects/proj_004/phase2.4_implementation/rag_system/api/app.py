"""
API接口模块
提供RESTful API服务
"""

import time
from typing import List, Optional
from flask import Flask, request, jsonify

from core.models import RetrieveRequest, RetrieveResponse, GenerateRequest, GenerateResponse, Document
from core.retrieval import get_retriever
from core.generation import get_generation_service

app = Flask(__name__)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })


@app.route('/api/v1/retrieve', methods=['POST'])
def retrieve():
    """
    检索相关文档

    Request Body:
        {
            "query": "查询文本",
            "top_k": 5  // 可选，默认5
        }

    Response:
        {
            "documents": [...],
            "total": 5,
            "query_time_ms": 123
        }
    """
    try:
        data = request.get_json()

        # 解析请求
        req = RetrieveRequest(
            query=data.get('query', ''),
            top_k=data.get('top_k', 5)
        )

        # 验证请求
        is_valid, error_msg = req.validate()
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # 执行检索
        retriever = get_retriever()
        documents, query_time = retriever.retrieve(req.query, req.top_k)

        # 构建响应
        response = RetrieveResponse(
            documents=documents,
            total=len(documents),
            query_time_ms=query_time
        )

        return jsonify(response.to_dict())

    except Exception as e:
        app.logger.error(f"检索失败: {e}")
        return jsonify({"error": f"检索服务错误: {str(e)}"}), 500


@app.route('/api/v1/generate', methods=['POST'])
def generate():
    """
    基于上下文生成回答

    Request Body:
        {
            "query": "用户问题",
            "context_ids": ["kb_001", "kb_002"],  // 上下文文档ID列表
            "temperature": 0.7  // 可选，默认0.7
        }

    Response:
        {
            "answer": "生成的回答...",
            "sources": [...],
            "confidence": 0.85,
            "generation_time_ms": 2345
        }
    """
    try:
        data = request.get_json()

        # 解析请求
        req = GenerateRequest(
            query=data.get('query', ''),
            context_ids=data.get('context_ids', []),
            temperature=data.get('temperature', 0.7)
        )

        # 验证请求
        is_valid, error_msg = req.validate()
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # 获取上下文文档
        retriever = get_retriever()
        vector_store = retriever.vector_store

        context_docs = []
        for doc_id in req.context_ids:
            if doc_id in vector_store.documents:
                context_docs.append(vector_store.documents[doc_id])
            else:
                return jsonify({"error": f"文档ID不存在: {doc_id}"}), 400

        if len(context_docs) == 0:
            return jsonify({"error": "未找到有效的上下文文档"}), 400

        # 执行生成
        gen_service = get_generation_service()
        answer, confidence, gen_time = gen_service.generate_with_confidence(
            req.query, context_docs, req.temperature
        )

        # 构建响应
        response = GenerateResponse(
            answer=answer,
            sources=context_docs,
            confidence=confidence,
            generation_time_ms=int(gen_time * 1000)
        )

        return jsonify(response.to_dict())

    except Exception as e:
        app.logger.error(f"生成失败: {e}")
        return jsonify({"error": f"生成服务错误: {str(e)}"}), 500


@app.route('/api/v1/rag', methods=['POST'])
def rag():
    """
    完整RAG流程（检索+生成）

    Request Body:
        {
            "query": "用户问题",
            "top_k": 5,  // 可选，默认5
            "temperature": 0.7  // 可选，默认0.7
        }

    Response:
        {
            "query": "用户问题",
            "retrieved_docs": [...],
            "answer": "生成的回答...",
            "sources": [...],
            "confidence": 0.85,
            "retrieval_time_ms": 123,
            "generation_time_ms": 2345,
            "total_time_ms": 2468
        }
    """
    try:
        data = request.get_json()

        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        temperature = data.get('temperature', 0.7)

        if not query:
            return jsonify({"error": "查询文本不能为空"}), 400

        # 执行完整RAG流程
        from core.generation import RAGChain

        rag_chain = RAGChain(
            retriever=get_retriever(),
            generation_service=get_generation_service()
        )

        result = rag_chain.run(query, top_k=top_k, temperature=temperature)

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"RAG失败: {e}")
        return jsonify({"error": f"RAG服务错误: {str(e)}"}), 500


@app.route('/api/v1/documents/<doc_id>', methods=['GET'])
def get_document(doc_id: str):
    """获取单个文档详情"""
    try:
        retriever = get_retriever()
        vector_store = retriever.vector_store

        if doc_id not in vector_store.documents:
            return jsonify({"error": f"文档不存在: {doc_id}"}), 404

        doc = vector_store.documents[doc_id]
        return jsonify(doc.to_dict(include_score=False))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/documents', methods=['GET'])
def list_documents():
    """获取文档列表"""
    try:
        retriever = get_retriever()
        vector_store = retriever.vector_store

        documents = [doc.to_dict(include_score=False) for doc in vector_store.documents.values()]

        return jsonify({
            "total": len(documents),
            "documents": documents
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "接口不存在"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "服务器内部错误"}), 500


def create_app(openai_key: str, claude_key: str, index_path: str, meta_path: str):
    """
    创建并配置Flask应用

    Args:
        openai_key: OpenAI API Key
        claude_key: Claude API Key
        index_path: 向量索引路径
        meta_path: 元数据路径
    """
    from core.retrieval import init_retriever
    from core.generation import init_generation_service

    # 初始化检索器
    init_retriever(openai_key, index_path, meta_path)

    # 初始化生成服务
    init_generation_service(claude_key)

    return app


if __name__ == '__main__':
    import os

    # 从环境变量读取API Key
    openai_key = os.getenv('OPENAI_API_KEY', '')
    claude_key = os.getenv('CLAUDE_API_KEY', '')

    if not openai_key or not claude_key:
        print("❌ 请设置OPENAI_API_KEY和CLAUDE_API_KEY环境变量")
        exit(1)

    # 创建应用
    app = create_app(
        openai_key=openai_key,
        claude_key=claude_key,
        index_path='data/vector_index.faiss',
        meta_path='data/vector_meta.pkl'
    )

    # 启动服务
    app.run(host='0.0.0.0', port=8000, debug=True)
