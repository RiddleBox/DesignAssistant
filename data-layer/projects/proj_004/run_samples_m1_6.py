"""
M1-M6 样本批量运行：多文档 → 多信号聚合 → 2.2 → 2.3 → 2.5

运行流程（标准多文档模式）：
  1. 2.1 ×6：逐篇解码，各自提取 signals
  2. 合并所有 signals 为统一信号池
  3. 2.2 ×1：基于多源信号做整体机会判断
  4. 2.3 ×1：行动设计
  5. 2.5 ×1：整合复盘

运行方式: python run_samples_m1_6.py
需要: 在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 LLM 信息
"""

import os
import sys
import time
import importlib.util
from dataclasses import asdict

BASE = os.path.dirname(os.path.abspath(__file__))
LLM_CONFIG_PATH = os.path.join(BASE, "llm_config.py")

def _load_env_file(path):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))

def load_module(name, path, dep_modules=None):
    if dep_modules:
        for dep_name, dep_mod in dep_modules.items():
            sys.modules[dep_name] = dep_mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    if dep_modules:
        for dep_name in dep_modules:
            if dep_name != name:
                sys.modules.pop(dep_name, None)
    return mod


def load_llm_config(phase: str) -> dict:
    spec = importlib.util.spec_from_file_location("llm_config", LLM_CONFIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["llm_config"] = mod
    spec.loader.exec_module(mod)
    return mod.get_llm_config(phase)

# 2.1
m21_schemas = load_module('schemas_21', os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
m21_prompts = load_module('prompt_templates',
    os.path.join(BASE, 'phase2.1_implementation', 'prompt_templates.py'),
    dep_modules={'schemas': m21_schemas})
decoder_mod = load_module('decoder',
    os.path.join(BASE, 'phase2.1_implementation', 'decoder.py'),
    dep_modules={'schemas': m21_schemas, 'prompt_templates': m21_prompts})
IntelligenceDecoder       = decoder_mod.IntelligenceDecoder
IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest
SourceType                = m21_schemas.SourceType

# 2.2
m22_schemas = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))
m22_validators = load_module('validators',
    os.path.join(BASE, 'phase2.2_implementation', 'validators.py'),
    dep_modules={'schemas': m22_schemas})
judgment_mod = load_module('judgment_engine',
    os.path.join(BASE, 'phase2.2_implementation', 'judgment_engine.py'),
    dep_modules={'schemas': m22_schemas, 'validators': m22_validators})
JudgmentEngine             = judgment_mod.JudgmentEngine
OpportunityJudgmentRequest = m22_schemas.OpportunityJudgmentRequest

# 2.3
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OppObj23, ActionDesignRequest
from action_designer import ActionDesigner

# 2.5
impl25_dir = os.path.join(BASE, 'phase2.5_implementation')
sys.path.insert(0, impl25_dir)
from schemas import SystemRetrospectiveRequest
from core import SystemRetrospectiveAnalyzer


# ── 样本定义 ─────────────────────────────────────────────────────────────────
# 每条使用原文 Summary 字段作为输入文本
SAMPLES = [
    {
        "id": "M1",
        "source_type": SourceType.REPORT,
        "text": (
            "Unity Muse 在 2024 年完成了向 Unity 6 的原生集成，重点更新了 Texture（PBR 材质生成）"
            "和 Behavior（自然语言驱动行为树）。Sentis 则进化为支持 DirectML 的跨平台推理库，"
            "允许 AI 模型在不依赖云端的情况下于玩家本地设备运行。"
            "新模型生成的纹理贴图具有更高的细节和色彩一致性，生成的高度图默认为 16 位，"
            "确保符合专业生产标准。"
        ),
    },
    {
        "id": "M2",
        "source_type": SourceType.NEWS,
        "text": (
            "UE5.7 强化了 PCG（程序化内容生成）框架，并新增了实验性的 AI Assistant，"
            "旨在通过编辑器内交互引导开发者完成复杂工作流。"
            "Epic 在 UE5.7 中正式引入了'In-editor AI Assistant'，"
            "标志着头部引擎开始尝试'对话式驱动'研发。"
        ),
    },
    {
        "id": "M3",
        "source_type": SourceType.REPORT,
        "text": (
            "2026 年初调研显示，开发者对生成式 AI 的采纳率从 2025 年的 36% 略降至 29%。"
            "尽管 87% 的开发者在某些环节使用 AI Agent，但对成本削减的乐观态度正在下降。"
            "27% 的受访者在 2025 年上半年看好 GenAI 的成本削减能力，"
            "到 2026 年初这一比例降至 21%。"
        ),
    },
    {
        "id": "M4",
        "source_type": SourceType.NEWS,
        "text": (
            "NVIDIA ACE 现已商用，支持在 RTX PC 或云端运行 Audio2Face、Riva ASR 等微服务。"
            "完美世界等公司已开始将其整合进生产流。"
            "NVIDIA ACE 是一套针对设备端推理与图形协同优化的技术套件，"
            "实时 AI 推理正成为游戏运行环境（Runtime）的一部分。"
        ),
    },
    {
        "id": "M5",
        "source_type": SourceType.NEWS,
        "text": (
            "Embark 展示了 AI/ML 在实际项目中的工业化使用方式："
            "通过机器学习驱动部分敌人的动态 locomotion 与物理反馈，"
            "通过 TTS 扩展高重复、长尾语音内容的生产覆盖范围。"
            "AI 的应用已超出静态资产生成，开始进入动态行为与内容生产的部分关键环节。"
        ),
    },
    {
        "id": "M6",
        "source_type": SourceType.REPORT,
        "text": (
            "美国版权局报告强调，AI 生成内容的可版权性取决于人类'创造性控制'的程度。"
            "若 AI 主导生成，该部分内容可能无法获得版权保护。"
            "纯 AI 生成资产面临严重的知识产权（IP）资产化风险，"
            "这是大厂在替换核心资产管线时保持谨慎的主要原因之一。"
        ),
    },
]


# ── Step 1: 2.1 逐篇解码，收集所有 signals ──────────────────────────────────
def run_step1(llm_config_21: dict) -> list:
    decoder = IntelligenceDecoder(
        api_key=llm_config_21.get("api_key", ""),
        model=llm_config_21.get("model", "claude-opus-4-6"),
        provider=llm_config_21.get("provider", "anthropic"),
        base_url=llm_config_21.get("base_url", ""),
    )
    all_signals = []
    decode_results = []

    print(f"\n{'='*60}")
    print("Step 1: 2.1 情报解码（逐篇）")
    print(f"{'='*60}")

    for s in SAMPLES:
        req = IntelligenceDecodeRequest(
            source_id=s["id"],
            source_type=s["source_type"],
            content=s["text"],
        )
        print(f"\n  [{s['id']}] 解码中...")
        result = decoder.decode(req)
        sig_count = len(result.signals)
        print(f"  [{s['id']}] 提取信号 {sig_count} 个，耗时 {result.processing_time_ms}ms")
        for sig in result.signals:
            print(f"    - [{sig.signal_type.value}] {sig.signal_label} (强度={sig.intensity_score})")
            all_signals.append(sig.model_dump())
        decode_results.append(result)

    print(f"\n  >>> 信号池合计: {len(all_signals)} 个信号（来自 {len(SAMPLES)} 篇文档）")
    return all_signals, decode_results


# ── Step 2: 2.2 基于合并信号池做整体机会判断 ─────────────────────────────────
def run_step2(all_signals: list) -> object:
    print(f"\n{'='*60}")
    print("Step 2: 2.2 机会判断（多源信号聚合）")
    print(f"{'='*60}")

    merged_intelligence = {
        "source_id": "M1-M6_batch",
        "signals": all_signals,
        "summary": f"来自 {len(SAMPLES)} 篇文档的信号聚合，共 {len(all_signals)} 个信号",
        "decoder_version": "v1.2",
        "processing_time_ms": 0,
        "warnings": [],
    }

    engine = JudgmentEngine()
    req = OpportunityJudgmentRequest(decoded_intelligence=merged_intelligence)
    t0 = time.time()
    result = engine.judge(req)
    elapsed = int((time.time() - t0) * 1000)

    opp = result.opportunity
    print(f"  status:          {result.status}")
    print(f"  priority_level:  {opp.priority_level}")
    print(f"  opportunity:     {opp.opportunity_title}")
    print(f"  thesis:          {opp.opportunity_thesis[:80]}...")
    print(f"  supporting:      {len(opp.supporting_evidence)} 条")
    print(f"  counter:         {len(opp.counter_evidence)} 条")
    print(f"  key_assumptions: {len(opp.key_assumptions)} 条")
    print(f"  耗时:            {elapsed}ms")
    return result


# ── Step 3: 2.3 行动设计 ───────────────────────────────────────────────────
def run_step3(judgment_result) -> object:
    print(f"\n{'='*60}")
    print("Step 3: 2.3 行动设计")
    print(f"{'='*60}")

    opp22 = judgment_result.opportunity
    opp23 = OppObj23(
        opportunity_title=opp22.opportunity_title,
        opportunity_thesis=opp22.opportunity_thesis,
        priority_level=opp22.priority_level,
        key_assumptions=opp22.key_assumptions,
        supporting_evidence=opp22.supporting_evidence,
        counter_evidence=opp22.counter_evidence,
        uncertainty_map={u: "不确定" for u in opp22.uncertainty_map},
    )

    designer = ActionDesigner()
    req = ActionDesignRequest(request_id="M1_M6_batch_001", opportunity_object=opp23)
    result = designer.design_action(req)
    ad = result.action_decision

    print(f"  posture:          {ad.decision_posture}")
    print(f"  why:              {ad.why_this_posture[:80]}...")
    print(f"  phases:           {len(ad.phased_plan)} 个阶段")
    for i, ph in enumerate(ad.phased_plan, 1):
        print(f"    阶段{i}: {ph.stage} — {ph.objective[:50]}")
    print(f"  top_risks:        {len(ad.top_risks)} 条")
    print(f"  resource_logic:   {ad.resource_commitment_logic[:80]}...")
    return result


# ── Step 4: 2.5 整合复盘 ──────────────────────────────────────────────────
def run_step4(judgment_result, action_result, decode_results) -> object:
    print(f"\n{'='*60}")
    print("Step 4: 2.5 整合复盘")
    print(f"{'='*60}")

    opp = judgment_result.opportunity
    ad  = action_result.action_decision

    req = SystemRetrospectiveRequest(
        request_id="M1_M6_retro_001",
        case_id="M1-M6_batch",
        workflow_run_record={
            "run_id": "M1_M6_batch_001",
            "case_description": "M1-M6 六篇文档批量运行，验证多信号聚合标准流程",
            "modules_executed": ["2.1", "2.2", "2.3"],
            "signal_count": sum(len(r.signals) for r in decode_results),
            "opportunity_title": opp.opportunity_title,
            "decision_posture": ad.decision_posture,
        },
        upstream_outputs={
            "phase_2_1": {
                "source_ids": [s["id"] for s in SAMPLES],
                "total_signals": sum(len(r.signals) for r in decode_results),
                "signals_sample": [r.signals[0].model_dump() for r in decode_results if r.signals],
            },
            "phase_2_2": opp.model_dump(),
            "phase_2_3": {
                "decision_posture": ad.decision_posture,
                "why_this_posture": ad.why_this_posture,
                "phases": len(ad.phased_plan),
                "resource_commitment_logic": ad.resource_commitment_logic,
            },
        },
    )

    analyzer = SystemRetrospectiveAnalyzer()
    result = analyzer.analyze(req)
    retro = result.retrospective

    print(f"  workflow_summary:    {retro.workflow_summary[:80]}...")
    print(f"  critical_findings:  {len(retro.critical_findings)} 条")
    for f in retro.critical_findings[:3]:
        print(f"    - [{f.severity.value}] {f.summary[:60]}")
    print(f"  root_causes:        {len(retro.suspected_root_causes)} 条")
    print(f"  phase3_priorities:  {len(retro.phase3_priorities)} 条")
    for p in retro.phase3_priorities[:3]:
        print(f"    - [order={p.suggested_order}] {p.title[:60]}")
    return result


# ── 主入口 ─────────────────────────────────────────────────────────────────
def main():
    llm_config_21 = load_llm_config("2.1")
    if not llm_config_21.get("api_key"):
        print("ERROR: 未找到 phase 2.1 的 LLM API key")
        print("请在 llm_config.local.yaml 或环境变量中配置 phase 2.1 的 api_key")
        sys.exit(1)
    print(f"2.1 model: {llm_config_21.get('model', 'claude-opus-4-6')}")
    print(f"2.1 provider: {llm_config_21.get('provider', 'anthropic')}")

    t_total = time.time()

    all_signals, decode_results = run_step1(llm_config_21)
    judgment_result = run_step2(all_signals)
    action_result   = run_step3(judgment_result)
    retro_result    = run_step4(judgment_result, action_result, decode_results)

    total_ms = int((time.time() - t_total) * 1000)
    print(f"\n{'#'*60}")
    print(f"M1-M6 批量运行完成，总耗时 {total_ms}ms")
    print(f"  信号池:      {len(all_signals)} 个")
    print(f"  机会判断:    {judgment_result.opportunity.priority_level} / {judgment_result.opportunity.opportunity_title}")
    print(f"  行动姿态:    {action_result.action_decision.decision_posture}")
    print(f"  复盘完成:    findings={len(retro_result.retrospective.critical_findings)}, phase3_priorities={len(retro_result.retrospective.phase3_priorities)}")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
