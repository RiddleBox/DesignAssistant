"""
Phase 2.2 机会判断模块 - 验证案例集（v2，2026-03-28）

重构说明：
- 全部案例改为 decoded_intelligences: List[DecodedIntelligence] 多条输入
- 信号字段对齐 2.1 Schema：description / intensity_score / confidence_score / timeliness_score
- 每个案例至少 2 条来自不同 source_id 的 DecodedIntelligence，体现多源信号组合语义
- 主题换为游戏行业（贴近项目实际使用场景）
- 运行器（run_validation.py）不需要改动
"""

from schemas import OpportunityJudgmentRequest, ContextPacket


def _make_di(source_id, source_type, signals, summary=None):
    """构造 DecodedIntelligence dict（引擎内部用 _extract_enriched_signals 解析）"""
    return {
        "source_id": source_id,
        "source_type": source_type,
        "signals": signals,
        "summary": summary,
        "decoder_version": "v1.6",
        "processing_time_ms": 120,
        "warnings": None,
    }


def _make_sig(signal_id, signal_type, label, description, evidence_text,
              intensity_score, confidence_score, timeliness_score,
              entities=None, source_ref=""):
    """构造 Signal dict"""
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "signal_label": label,
        "description": description,
        "evidence_text": evidence_text,
        "entities": entities or [],
        "intensity_score": intensity_score,
        "confidence_score": confidence_score,
        "timeliness_score": timeliness_score,
        "source_ref": source_ref,
        "extracted_at": "2026-03-28T08:00:00",
        "metadata": None,
    }


# ============================================================
# 案例1：watch — 单一来源，单一信号，可信度低
# 场景：某博主报道某游戏引擎发布新版本，无官方确认
# 预期：信号孤立，来源为 news 且 confidence 低，输出 watch
# ============================================================
CASE_1_WATCH = {
    "case_id": "case_001_watch",
    "description": "单一信号，news 来源，confidence 偏低，无跨源印证",
    "expected_priority": "watch",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="news_001",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_001_tech",
                        signal_type="technical",
                        label="Unity 引擎新版本渲染管线升级",
                        description="Unity 据报道将在下一版本引入全新渲染管线，性能提升幅度尚不明确",
                        evidence_text="消息人士称 Unity 正在内测新渲染架构，具体细节未公开",
                        intensity_score=4,
                        confidence_score=3,
                        timeliness_score=6,
                        entities=["Unity Technologies"],
                    )
                ],
                summary="Unity 引擎升级传言，尚无官方证实",
            )
        ]
    ),
}


# ============================================================
# 案例2：watch — 空信号（证据不足）
# 场景：文章解码后未提取到有效信号（全为噪音）
# 预期：insufficient_evidence，输出 watch
# ============================================================
CASE_2_WATCH_INSUFFICIENT = {
    "case_id": "case_002_watch_insufficient",
    "description": "解码后无有效信号，证据不足",
    "expected_priority": "watch",
    "expected_status": "insufficient_evidence",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="news_002",
                source_type="news",
                signals=[],
                summary="文章为常规行业综述，未检测到有效信号",
            )
        ]
    ),
}


# ============================================================
# 案例3：research — 两条互补信号，来自不同来源
# 场景：NVIDIA 发布游戏专用 AI 推理芯片（technical）+
#       头部手游发行商公开寻求 AI NPC 解决方案合作（market）
# 预期：两条信号构成硬件侧供给 + 需求侧拉动的初步逻辑链，输出 research
# ============================================================
CASE_3_RESEARCH = {
    "case_id": "case_003_research",
    "description": "技术供给 + 市场需求双信号，跨两篇文章，初步逻辑链成立",
    "expected_priority": "research",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="news_003a",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_003_tech",
                        signal_type="technical",
                        label="NVIDIA 发布游戏 AI 推理专用 GPU 系列",
                        description="NVIDIA 官方发布面向游戏 AI 推理场景的专用 GPU 系列，推理算力较上代提升 3 倍，TDP 下降 20%",
                        evidence_text="NVIDIA officially announced the GeForce AI Series targeting real-time game AI inference workloads.",
                        intensity_score=7,
                        confidence_score=9,
                        timeliness_score=8,
                        entities=["NVIDIA", "GeForce AI Series"],
                    )
                ],
                summary="NVIDIA 官方公告：游戏 AI 推理专用 GPU 发布",
            ),
            _make_di(
                source_id="news_003b",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_003_market",
                        signal_type="market",
                        label="头部手游发行商公开寻求 AI NPC 推理方案合作",
                        description="多家头部手游发行商在 GDC 联合发布需求白皮书，明确寻求端侧 AI NPC 推理方案，预算窗口在 2026 Q3",
                        evidence_text="Several top mobile publishers jointly released a demand whitepaper at GDC seeking on-device AI NPC inference partners.",
                        intensity_score=6,
                        confidence_score=7,
                        timeliness_score=8,
                        entities=["GDC", "AI NPC"],
                    )
                ],
                summary="头部发行商集体需求信号：AI NPC 端侧推理",
            ),
        ]
    ),
}


# ============================================================
# 案例4：research — 两条信号 + 2.4 证据包
# 场景：Epic 宣布 UE5 大规模优化（technical）+
#       主机平台销量增长报告（market）+ 2.4 注入相似案例
# 预期：信号组合 + 外部知识印证，输出 research
# ============================================================
CASE_4_RESEARCH_WITH_CONTEXT = {
    "case_id": "case_004_research_with_context",
    "description": "UE5 技术升级 + 平台销量增长，2.4 注入相似案例",
    "expected_priority": "research",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="announcement_004a",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_004_tech",
                        signal_type="technical",
                        label="UE5 Nanite 支持移动端正式发布",
                        description="Epic 官方宣布 UE5.4 正式将 Nanite 虚拟几何体技术扩展到移动端，适配主流 Android 旗舰机型",
                        evidence_text="Epic Games announced UE5.4 with full Nanite support for mobile, targeting flagship Android devices.",
                        intensity_score=8,
                        confidence_score=9,
                        timeliness_score=9,
                        entities=["Epic Games", "UE5", "Nanite"],
                    )
                ],
                summary="Epic 官方：UE5.4 Nanite 移动端正式落地",
            ),
            _make_di(
                source_id="report_004b",
                source_type="report",
                signals=[
                    _make_sig(
                        signal_id="sig_004_market",
                        signal_type="market",
                        label="主机端手游市场规模预测上调 35%",
                        description="IDC 最新报告将 2026-2028 年主机端手游市场规模预测上调 35%，驱动因素为旗舰机性能跃升",
                        evidence_text="IDC revised 2026-2028 mobile gaming market forecast upward by 35%, citing flagship hardware leap.",
                        intensity_score=6,
                        confidence_score=7,
                        timeliness_score=7,
                        entities=["IDC"],
                    )
                ],
                summary="IDC 报告：主机端手游市场上调预测",
            ),
        ],
        context_packet=ContextPacket(
            similar_cases=[
                "UE4 移动端落地后，《堡垒之夜》Mobile 在 18 个月内成为旗舰机标配体验",
                "Unity HDRP 2020 年移动端落地，带动中重度手游画质竞赛",
            ],
            counter_examples=[
                "UE3 移动端迁移因适配成本高，中小团队放弃比例超 60%",
            ],
            methodology_hints=[
                "技术落地时效性窗口：旗舰机普及率达 30% 前是最佳跟进期",
            ]
        ),
    ),
}


# ============================================================
# 案例5：deep_dive — 四维信号聚合，逻辑链完整
# 场景：AI 游戏开发工具链爆发
#   - 某 AI 代码生成工具宣布游戏专用版本（technical）
#   - 独立游戏开发者调研显示 AI 工具采用率同比翻倍（market）
#   - 头部游戏引擎公司挖角 AI 研究团队（team）
#   - 顶级 VC 密集投资 AI 游戏开发工具赛道（capital）
# 预期：四维高强度信号，逻辑链清晰，输出 deep_dive
# ============================================================
CASE_5_DEEP_DIVE = {
    "case_id": "case_005_deep_dive",
    "description": "AI 游戏开发工具链：技术+市场+团队+资本四维信号聚合",
    "expected_priority": "escalate",
    "note": "四维信号强度均在 7-8，LLM 判定平台级竞争启动+资本密集下注达到 escalate 标准；原预期 deep_dive 偏保守",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="announcement_005a",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_005_tech",
                        signal_type="technical",
                        label="Cursor 发布 Game Dev Edition，深度集成游戏引擎 API",
                        description="Cursor 正式发布 Game Dev Edition，内置 UE5/Unity API 理解能力，可生成可运行蓝图和 C# 脚本",
                        evidence_text="Cursor announced Game Dev Edition with native UE5/Unity integration, generating runnable Blueprints and C# scripts.",
                        intensity_score=8,
                        confidence_score=9,
                        timeliness_score=9,
                        entities=["Cursor", "UE5", "Unity"],
                    )
                ],
                summary="Cursor 游戏开发专版正式发布",
            ),
            _make_di(
                source_id="report_005b",
                source_type="report",
                signals=[
                    _make_sig(
                        signal_id="sig_005_market",
                        signal_type="market",
                        label="独立游戏开发者 AI 工具采用率同比翻倍",
                        description="GDC 2026 年度调研：独立开发者中 AI 辅助编码工具使用率从 22% 升至 47%，付费意愿显著增强",
                        evidence_text="GDC 2026 State of the Game Industry: AI coding tool adoption among indie devs doubled from 22% to 47%.",
                        intensity_score=7,
                        confidence_score=8,
                        timeliness_score=8,
                        entities=["GDC"],
                    )
                ],
                summary="GDC 2026 调研：AI 工具采用率翻倍",
            ),
            _make_di(
                source_id="news_005c",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_005_team",
                        signal_type="team",
                        label="Unity 挖角 OpenAI 游戏 AI 研究团队核心成员",
                        description="Unity 确认从 OpenAI 游戏 AI 研究组挖走 3 名核心研究员，组建内部 AI 工具链团队",
                        evidence_text="Unity confirmed hiring 3 key researchers from OpenAI's gaming AI group to form an in-house AI toolchain team.",
                        intensity_score=7,
                        confidence_score=8,
                        timeliness_score=7,
                        entities=["Unity", "OpenAI"],
                    )
                ],
                summary="Unity 从 OpenAI 挖角游戏 AI 研究团队",
            ),
            _make_di(
                source_id="news_005d",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_005_capital",
                        signal_type="capital",
                        label="a16z 领投 AI 游戏工具赛道，本季度累计投资超 8 亿美元",
                        description="a16z 本季度在 AI 游戏开发工具赛道密集出手，累计投资额超 8 亿美元，覆盖资产生成、代码生成、NPC AI 三个方向",
                        evidence_text="a16z led multiple deals in AI game dev tools this quarter, totaling over $800M across asset generation, code gen, and NPC AI.",
                        intensity_score=8,
                        confidence_score=7,
                        timeliness_score=9,
                        entities=["a16z"],
                    )
                ],
                summary="a16z 密集投资 AI 游戏工具赛道",
            ),
        ],
        context_packet=ContextPacket(
            similar_cases=[
                "2008-2010 年 Unity 崛起：工具民主化引发独立游戏爆发，长尾市场规模翻 5 倍",
                "GitHub Copilot 落地后，SaaS 赛道人均代码产出提升 40%，工具链公司估值重估",
            ],
            counter_examples=[
                "早期 AI 美术工具因质量不稳定被头部工作室拒绝采用，市场渗透率长期停滞",
            ],
        ),
    ),
}


# ============================================================
# 案例6：deep_dive — 强信号但有明显反证
# 场景：云游戏平台复苏信号
#   - 微软 xCloud 宣布延迟低于 20ms 新架构（technical）
#   - 5G 覆盖率报告显示游戏级低延迟网络覆盖达 40%（market）
#   - 谷歌 Stadia 失败案例（反证）+ 用户付费习惯迁移难（counter）
# 预期：信号有一定强度但存在系统性反证，输出 deep_dive（保守端）
# ============================================================
CASE_6_DEEP_DIVE_WITH_COUNTER = {
    "case_id": "case_006_deep_dive_counter",
    "description": "云游戏平台复苏：技术突破 + 网络覆盖改善，但 Stadia 反证显著",
    "expected_priority": "deep_dive",
    "note": "LLM 模式预期 deep_dive（有明显反证但信号强度仍高）；规则引擎因 3 信号含反证方向可能保守降级为 research，属合理边界行为",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="announcement_006a",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_006_tech",
                        signal_type="technical",
                        label="微软 xCloud 新架构延迟降至 18ms",
                        description="微软官方宣布 xCloud 2.0 架构，通过边缘节点下沉将平均延迟降至 18ms，覆盖北美 / 欧洲主要城市",
                        evidence_text="Microsoft announced xCloud 2.0 with average latency of 18ms via edge node deployment in North America and Europe.",
                        intensity_score=8,
                        confidence_score=9,
                        timeliness_score=8,
                        entities=["Microsoft", "xCloud"],
                    )
                ],
                summary="微软 xCloud 2.0：延迟突破 20ms 门槛",
            ),
            _make_di(
                source_id="report_006b",
                source_type="report",
                signals=[
                    _make_sig(
                        signal_id="sig_006_market",
                        signal_type="market",
                        label="全球 5G 游戏级低延迟覆盖率达 40%",
                        description="Ericsson 报告：全球 5G 网络中达到云游戏可用标准（延迟 <25ms）的覆盖率已达 40%，预计 2027 年超 70%",
                        evidence_text="Ericsson report: 40% of global 5G networks now meet cloud gaming latency requirements (<25ms), expected 70% by 2027.",
                        intensity_score=7,
                        confidence_score=8,
                        timeliness_score=7,
                        entities=["Ericsson", "5G"],
                    )
                ],
                summary="Ericsson：5G 游戏级覆盖率达 40%",
            ),
            _make_di(
                source_id="report_006c",
                source_type="report",
                signals=[
                    _make_sig(
                        signal_id="sig_006_market2",
                        signal_type="market",
                        label="云游戏付费用户渗透率持续低迷，3 年增长不足 5%",
                        description="Newzoo 报告：云游戏付费用户渗透率从 2023 年 4.2% 仅增至 2025 年 6.8%，付费习惯迁移难度超预期",
                        evidence_text="Newzoo: cloud gaming paid user penetration grew from 4.2% in 2023 to only 6.8% in 2025, far below early projections.",
                        intensity_score=7,
                        confidence_score=8,
                        timeliness_score=7,
                        entities=["Newzoo"],
                    )
                ],
                summary="Newzoo：云游戏付费渗透率低迷",
            ),
        ],
        context_packet=ContextPacket(
            similar_cases=[
                "Netflix 云游戏 2022 年入场后，依托会员基数实现差异化破局",
            ],
            counter_examples=[
                "谷歌 Stadia 2021 年关闭：技术过硬但商业模式失败，用户不愿为串流支付溢价",
                "GeForce NOW 多年运营后仍为小众服务，付费留存率不足 30%",
            ],
            domain_constraints=[
                "云游戏商业成功依赖用户付费心智迁移，与网络技术成熟度解耦",
            ]
        ),
    ),
}


# ============================================================
# 案例7：escalate — 多维高强度信号聚合 + 时效窗口紧迫
# 场景：AI 生成游戏资产颠覆传统美术管线
#   - Adobe 宣布 Substance 3D AI 一键生成 PBR 材质达到 AAA 水准（technical, 官方公告）
#   - EA 公开宣布裁撤传统美术岗，转向 AI 生成管线（team, 新闻）
#   - 独立研究报告：AI 美术工具可降低 AAA 资产制作成本 60%（market, 报告）
#   - Epic 宣布 Fab 平台集成 AI 生成资产，竞争对手快速跟进（capital/market, 公告）
#   - 传统美术外包龙头 Virtuos 股价单周下跌 18%（capital, 新闻）
# 预期：5 条跨维度高强度信号，时效窗口紧迫，输出 escalate
# ============================================================
CASE_7_ESCALATE = {
    "case_id": "case_007_escalate",
    "description": "AI 生成美术资产颠覆传统管线：五维信号聚合，时效窗口紧迫",
    "expected_priority": "escalate",
    "request": OpportunityJudgmentRequest(
        decoded_intelligences=[
            _make_di(
                source_id="announcement_007a",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_007_tech",
                        signal_type="technical",
                        label="Adobe Substance 3D AI 一键生成 AAA 级 PBR 材质",
                        description="Adobe 官方发布 Substance 3D AI 2.0，一键生成的 PBR 材质在盲测中与人工制作达到同等水准，已集成 UE5/Unity",
                        evidence_text="Adobe announced Substance 3D AI 2.0 achieving AAA-quality PBR material generation matching manual work in blind tests.",
                        intensity_score=9,
                        confidence_score=9,
                        timeliness_score=9,
                        entities=["Adobe", "Substance 3D", "UE5", "Unity"],
                    )
                ],
                summary="Adobe 官方：AI 生成材质达到 AAA 水准",
            ),
            _make_di(
                source_id="news_007b",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_007_team",
                        signal_type="team",
                        label="EA 宣布裁撤传统美术岗，全面转向 AI 生成管线",
                        description="EA 公开宣布将在 18 个月内将传统环境美术岗位缩减 40%，转向 AI 生成资产管线，节省成本用于 AI 工具链建设",
                        evidence_text="EA announced a 40% reduction in traditional environment art roles over 18 months, pivoting to AI-generated asset pipelines.",
                        intensity_score=9,
                        confidence_score=8,
                        timeliness_score=9,
                        entities=["EA"],
                    )
                ],
                summary="EA 裁撤传统美术岗，AI 管线全面转型",
            ),
            _make_di(
                source_id="report_007c",
                source_type="report",
                signals=[
                    _make_sig(
                        signal_id="sig_007_market",
                        signal_type="market",
                        label="AI 美术工具降低 AAA 资产制作成本 60%",
                        description="麦肯锡游戏行业报告：AI 生成美术工具已可将 AAA 游戏资产制作成本降低 60%，中型工作室已具备可行性",
                        evidence_text="McKinsey gaming report: AI art tools reduce AAA asset production costs by 60%, now viable for mid-size studios.",
                        intensity_score=8,
                        confidence_score=8,
                        timeliness_score=8,
                        entities=["McKinsey"],
                    )
                ],
                summary="麦肯锡报告：AI 美术降本 60%，中型工作室可行",
            ),
            _make_di(
                source_id="announcement_007d",
                source_type="announcement",
                signals=[
                    _make_sig(
                        signal_id="sig_007_market2",
                        signal_type="market",
                        label="Epic Fab 集成 AI 生成资产，Unity 宣布跟进",
                        description="Epic 官宣 Fab 资产商店集成 AI 生成资产标准认证体系，Unity Asset Store 同周宣布跟进，平台级竞争已启动",
                        evidence_text="Epic announced AI-generated asset certification on Fab; Unity Asset Store announced a similar initiative the same week.",
                        intensity_score=8,
                        confidence_score=9,
                        timeliness_score=10,
                        entities=["Epic", "Fab", "Unity Asset Store"],
                    )
                ],
                summary="Epic & Unity 同周宣布 AI 资产平台标准，竞争窗口开启",
            ),
            _make_di(
                source_id="news_007e",
                source_type="news",
                signals=[
                    _make_sig(
                        signal_id="sig_007_capital",
                        signal_type="capital",
                        label="传统美术外包龙头 Virtuos 股价单周下跌 18%",
                        description="Virtuos 受 EA 转型新闻影响股价单周下跌 18%，市场开始重新定价传统外包模式的长期价值",
                        evidence_text="Virtuos shares dropped 18% in a week following EA's AI pivot announcement, signaling market repricing of traditional outsourcing.",
                        intensity_score=8,
                        confidence_score=7,
                        timeliness_score=9,
                        entities=["Virtuos"],
                    )
                ],
                summary="Virtuos 股价暴跌：市场开始重定价传统外包",
            ),
        ],
        context_packet=ContextPacket(
            similar_cases=[
                "摄影技术冲击传统插画市场（1990s）：技术成熟后 3 年内传统外包单价下跌 50%",
                "AI 配音工具 2023 年落地后，欧美配音行业人均接单量下降 35%",
            ],
            counter_examples=[
                "AI 美术工具在东亚二次元风格上仍存在明显质量差距，传统美术在细分风格上有护城河",
            ],
            methodology_hints=[
                "技术颠覆窗口判断：头部玩家公开转型是关键信号，通常领先中小工作室跟进 12-18 个月",
            ]
        ),
    ),
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
    CASE_7_ESCALATE,
]


def get_case_by_id(case_id: str):
    """根据 case_id 获取案例"""
    for case in VALIDATION_CASES:
        if case["case_id"] == case_id:
            return case
    return None


def get_cases_by_priority(priority: str):
    """根据预期优先级获取案例"""
    return [case for case in VALIDATION_CASES if case.get("expected_priority") == priority]
