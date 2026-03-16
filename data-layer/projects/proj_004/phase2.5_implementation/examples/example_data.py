"""
Phase 2.5 Example Input Data

示例输入数据，用于测试系统复盘分析器。
"""

# 示例：真实链路运行记录
EXAMPLE_WORKFLOW_RUN_RECORD = {
    "run_id": "run_001",
    "start_time": "2026-03-16T10:00:00Z",
    "end_time": "2026-03-16T10:05:30Z",
    "processing_time_ms": 330000,
    "errors": [],
    "status": "completed"
}

# 示例：上游输出（2.1~2.4）
EXAMPLE_UPSTREAM_OUTPUTS = {
    "phase2_1": {
        "signals": [
            {
                "signal_id": "sig_001",
                "signal_type": "technology_breakthrough",
                "summary": "新型AI芯片架构突破",
                "source": "技术论文",
                "timestamp": "2026-03-15"
            },
            {
                "signal_id": "sig_002",
                "signal_type": "market_trend",
                "summary": "边缘计算市场快速增长",
                "source": "市场报告",
                "timestamp": "2026-03-14"
            }
        ],
        "signal_schema_validation": "passed",
        "benchmark_summary": "信号提取质量良好"
    },
    "phase2_2": {
        "opportunity_title": "布局边缘AI芯片生态",
        "opportunity_thesis": "随着边缘计算需求激增，新型AI芯片架构为构建差异化生态提供了技术窗口期。",
        "supporting_evidence": [
            "技术突破已验证可行性",
            "市场需求明确且增长快速",
            "现有竞争对手尚未形成垄断"
        ],
        "counter_evidence": [
            "技术成熟度仍需验证",
            "生态构建周期较长"
        ],
        "priority_level": "high",
        "uncertainty_map": {
            "technical_risk": "medium",
            "market_risk": "low",
            "execution_risk": "medium"
        }
    },
    "phase2_3": {
        "decision_posture": "pilot",
        "phased_plan": [
            {
                "phase": "Phase 1: 技术验证",
                "duration": "3个月",
                "key_actions": ["组建技术团队", "完成原型验证"],
                "milestones": ["原型完成", "性能达标"]
            },
            {
                "phase": "Phase 2: 生态试点",
                "duration": "6个月",
                "key_actions": ["选择试点场景", "建立合作伙伴"],
                "milestones": ["试点上线", "用户反馈收集"]
            }
        ],
        "go_no_go_criteria": {
            "go_conditions": ["原型性能达标", "试点场景验证成功"],
            "no_go_conditions": ["技术风险无法控制", "市场需求不足"]
        },
        "exit_conditions": ["技术路线失败", "竞争对手形成垄断"],
        "fallback_path": "转向技术授权模式"
    },
    "phase2_4": {
        "context_packet": {
            "similar_cases": ["案例A: 边缘计算芯片", "案例B: AI生态构建"],
            "risk_matrix": ["技术风险", "市场风险", "执行风险"],
            "best_practices": ["快速迭代", "生态优先"]
        },
        "retrieval_results": [
            {"doc_id": "doc_001", "relevance": 0.95},
            {"doc_id": "doc_002", "relevance": 0.88}
        ],
        "source_trace": ["知识库A", "知识库B"]
    }
}

# 示例：人工复核记录（可选）
EXAMPLE_REVIEW_NOTES = [
    {
        "reviewer": "human_reviewer_01",
        "timestamp": "2026-03-16T11:00:00Z",
        "observations": [
            "输出完整性良好",
            "机会判断论述清晰",
            "行动计划可执行"
        ],
        "confidence_level": "high",
        "major_concerns": []
    }
]

# 示例：完整请求对象
EXAMPLE_REQUEST_DATA = {
    "request_id": "req_001",
    "case_id": "case_001",
    "workflow_run_record": EXAMPLE_WORKFLOW_RUN_RECORD,
    "upstream_outputs": EXAMPLE_UPSTREAM_OUTPUTS,
    "review_notes": EXAMPLE_REVIEW_NOTES,
    "validation_mode": "mvp_single_case"
}
