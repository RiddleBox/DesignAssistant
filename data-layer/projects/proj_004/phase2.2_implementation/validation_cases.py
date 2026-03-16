"""
Phase 2.2 机会判断模块 - 验证案例集

包含3-8组真实案例，覆盖watch/research/deep_dive/escalate四个级别
"""

from schemas import OpportunityJudgmentRequest, ContextPacket


# ============================================================
# 案例1：watch级别 - 单一技术信号
# ============================================================
CASE_1_WATCH = {
    "case_id": "case_001_watch",
    "description": "单一技术信号，无市场验证",
    "expected_priority": "watch",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_001",
            "signals": [
                {
                    "signal_id": "sig_tech_001",
                    "signal_type": "technical",
                    "signal_summary": "某AI芯片公司发布7nm制程新品",
                    "intensity": 6,
                    "confidence": 7,
                    "source": "公司官网新闻"
                }
            ]
        }
    )
}


# ============================================================
# 案例2：watch级别 - 证据不足
# ============================================================
CASE_2_WATCH_INSUFFICIENT = {
    "case_id": "case_002_watch_insufficient",
    "description": "信号质量低，证据不足",
    "expected_priority": "watch",
    "expected_status": "insufficient_evidence",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_002",
            "signals": []
        }
    )
}


# ============================================================
# 案例3：research级别 - 技术+市场双信号
# ============================================================
CASE_3_RESEARCH = {
    "case_id": "case_003_research",
    "description": "技术+市场双信号，有初步证据",
    "expected_priority": "research",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_003",
            "signals": [
                {
                    "signal_id": "sig_tech_002",
                    "signal_type": "technical",
                    "signal_summary": "公司A发布固态电池技术突破，能量密度提升40%",
                    "intensity": 7,
                    "confidence": 8,
                    "source": "技术论文"
                },
                {
                    "signal_id": "sig_market_001",
                    "signal_type": "market",
                    "signal_summary": "电动车市场对高能量密度电池需求强烈",
                    "intensity": 6,
                    "confidence": 7,
                    "source": "市场报告"
                }
            ]
        }
    )
}


# ============================================================
# 案例4：research级别 - 带2.4证据包
# ============================================================
CASE_4_RESEARCH_WITH_CONTEXT = {
    "case_id": "case_004_research_with_context",
    "description": "技术信号+2.4证据包增强",
    "expected_priority": "research",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_004",
            "signals": [
                {
                    "signal_id": "sig_tech_003",
                    "signal_type": "technical",
                    "signal_summary": "量子计算公司B实现100量子比特稳定运行",
                    "intensity": 8,
                    "confidence": 7,
                    "source": "学术期刊"
                },
                {
                    "signal_id": "sig_team_001",
                    "signal_type": "team",
                    "signal_summary": "公司B招聘量子算法专家10人",
                    "intensity": 5,
                    "confidence": 6,
                    "source": "招聘网站"
                }
            ]
        },
        context_packet=ContextPacket(
            similar_cases=[
                "IBM量子计算商业化案例：从研究到云服务",
                "Google量子优势实验成功案例"
            ],
            counter_examples=[
                "D-Wave量子计算早期商业化遇阻案例"
            ],
            methodology_hints=[
                "量子计算商业化需要关注：算法成熟度、硬件稳定性、应用场景"
            ]
        )
    )
}


# ============================================================
# 案例5：deep_dive级别 - 多维度信号聚类
# ============================================================
CASE_5_DEEP_DIVE = {
    "case_id": "case_005_deep_dive",
    "description": "技术+市场+团队+资本多维度信号",
    "expected_priority": "deep_dive",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_005",
            "signals": [
                {
                    "signal_id": "sig_tech_004",
                    "signal_type": "technical",
                    "signal_summary": "公司C的AIGC模型在多个benchmark超越GPT-4",
                    "intensity": 9,
                    "confidence": 8,
                    "source": "技术评测"
                },
                {
                    "signal_id": "sig_market_002",
                    "signal_type": "market",
                    "signal_summary": "AIGC市场规模预计3年内增长10倍",
                    "intensity": 8,
                    "confidence": 7,
                    "source": "Gartner报告"
                },
                {
                    "signal_id": "sig_team_002",
                    "signal_type": "team",
                    "signal_summary": "公司C核心团队来自OpenAI和Google Brain",
                    "intensity": 7,
                    "confidence": 9,
                    "source": "公司官网"
                },
                {
                    "signal_id": "sig_capital_001",
                    "signal_type": "capital",
                    "signal_summary": "公司C完成2亿美元B轮融资，红杉领投",
                    "intensity": 8,
                    "confidence": 9,
                    "source": "融资公告"
                }
            ]
        },
        context_packet=ContextPacket(
            similar_cases=[
                "OpenAI从研究机构到商业巨头的转型路径",
                "Anthropic快速崛起案例"
            ],
            counter_examples=[
                "多家AIGC创业公司因同质化竞争失败"
            ]
        )
    )
}


# ============================================================
# 案例6：deep_dive级别 - 有反对证据的复杂场景
# ============================================================
CASE_6_DEEP_DIVE_WITH_COUNTER = {
    "case_id": "case_006_deep_dive_counter",
    "description": "强信号但存在明显反对证据",
    "expected_priority": "deep_dive",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_006",
            "signals": [
                {
                    "signal_id": "sig_tech_005",
                    "signal_type": "technical",
                    "signal_summary": "公司D发布自动驾驶L4级别系统",
                    "intensity": 8,
                    "confidence": 7,
                    "source": "产品发布会"
                },
                {
                    "signal_id": "sig_market_003",
                    "signal_type": "market",
                    "signal_summary": "自动驾驶市场需求旺盛，多家车企寻求合作",
                    "intensity": 7,
                    "confidence": 7,
                    "source": "行业报告"
                },
                {
                    "signal_id": "sig_team_003",
                    "signal_type": "team",
                    "signal_summary": "公司D团队规模扩张至500人",
                    "intensity": 6,
                    "confidence": 8,
                    "source": "公司年报"
                }
            ]
        },
        context_packet=ContextPacket(
            similar_cases=[
                "Waymo自动驾驶商业化进展"
            ],
            counter_examples=[
                "Uber自动驾驶事故导致项目暂停",
                "多家自动驾驶公司因法规限制推迟商业化"
            ],
            domain_constraints=[
                "自动驾驶面临严格的安全法规",
                "L4级别商业化需要大量路测数据"
            ]
        )
    )
}


# ============================================================
# 案例7：escalate级别 - 时效性紧迫
# ============================================================
CASE_7_ESCALATE = {
    "case_id": "case_007_escalate",
    "description": "强信号+高时效性+竞争压力",
    "expected_priority": "escalate",
    "request": OpportunityJudgmentRequest(
        decoded_intelligence={
            "intelligence_id": "intel_case_007",
            "signals": [
                {
                    "signal_id": "sig_tech_006",
                    "signal_type": "technical",
                    "signal_summary": "公司E发布革命性芯片架构，性能提升5倍",
                    "intensity": 10,
                    "confidence": 9,
                    "source": "技术白皮书"
                },
                {
                    "signal_id": "sig_market_004",
                    "signal_type": "market",
                    "signal_summary": "多家头部客户已签署采购意向，总额超10亿美元",
                    "intensity": 9,
                    "confidence": 8,
                    "source": "商业合同"
                },
                {
                    "signal_id": "sig_capital_002",
                    "signal_type": "capital",
                    "signal_summary": "竞争对手F同时宣布类似技术，抢占市场窗口期",
                    "intensity": 9,
                    "confidence": 8,
                    "source": "竞品发布会"
                },
                {
                    "signal_id": "sig_team_004",
                    "signal_type": "team",
                    "signal_summary": "公司E核心技术团队稳定，已申请50+专利",
                    "intensity": 8,
                    "confidence": 9,
                    "source": "专利数据库"
                },
                {
                    "signal_id": "sig_market_005",
                    "signal_type": "market",
                    "signal_summary": "行业分析师预测该技术将重塑芯片市场格局",
                    "intensity": 9,
                    "confidence": 7,
                    "source": "分析师报告"
                }
            ]
        },
        context_packet=ContextPacket(
            similar_cases=[
                "NVIDIA CUDA架构改变GPU市场格局",
                "Apple M系列芯片颠覆PC市场"
            ],
            methodology_hints=[
                "技术突破+市场窗口期+竞争压力 = 需要快速决策"
            ]
        )
    )
}


# ============================================================
# 案例集合
# ============================================================
VALIDATION_CASES = [
    CASE_1_WATCH,
    CASE_2_WATCH_INSUFFICIENT,
    CASE_3_RESEARCH,
    CASE_4_RESEARCH_WITH_CONTEXT,
    CASE_5_DEEP_DIVE,
    CASE_6_DEEP_DIVE_WITH_COUNTER,
    CASE_7_ESCALATE
]


def get_case_by_id(case_id: str):
    """根据case_id获取案例"""
    for case in VALIDATION_CASES:
        if case["case_id"] == case_id:
            return case
    return None


def get_cases_by_priority(priority: str):
    """根据预期优先级获取案例"""
    return [case for case in VALIDATION_CASES if case.get("expected_priority") == priority]
