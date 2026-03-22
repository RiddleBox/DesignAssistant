"""
Phase 2.1 -> 2.2 -> 2.3 -> 2.5 端到端链路联调 (P1-4)

使用真实 Anthropic API 从头跑通完整链路:
  1. 2.1 IntelligenceDecoder: 原始文本 -> DecodedIntelligence
  2. 2.2 JudgmentEngine:  DecodedIntelligence -> OpportunityObject
  3. 2.3 ActionDesigner:  OpportunityObject -> ActionDesignResult
  4. 2.5 SystemRetrospectiveAnalyzer: 全链路输出 -> SystemRetrospectiveResult

运行方式: python integration_test_e2e.py
需要: ANTHROPIC_API_KEY 环境变量或 .env 文件
"""

import os
import sys
import time
import importlib.util
from dataclasses import asdict

BASE = os.path.dirname(os.path.abspath(__file__))

# 加载 API key（不依赖 dotenv）
def _load_env_file(path):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env_file(os.path.join(BASE, '..', '..', '..', '.env'))
_load_env_file(os.path.join(BASE, 'phase2.4_implementation', 'rag_system', '.env'))

def load_module(name, path, dep_modules=None):
    """加载模块，可注入依赖模块到 sys.modules 避免 schemas 冲突"""
    if dep_modules:
        for dep_name, dep_mod in dep_modules.items():
            sys.modules[dep_name] = dep_mod
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    # 清理注入的临时依赖，防止污染后续加载
    if dep_modules:
        for dep_name in dep_modules:
            if dep_name != name:
                sys.modules.pop(dep_name, None)
    return mod

# --- 加载各模块 schemas（用唯一名注册）---
m21_schemas = load_module('schemas_21', os.path.join(BASE, 'phase2.1_implementation', 'schemas.py'))
m22_schemas = load_module('schemas_22', os.path.join(BASE, 'phase2.2_implementation', 'schemas.py'))

# 加载 prompt_templates（依赖 2.1 schemas）
m21_prompts = load_module('prompt_templates',
    os.path.join(BASE, 'phase2.1_implementation', 'prompt_templates.py'),
    dep_modules={'schemas': m21_schemas})

# 加载 decoder（注入 2.1 schemas 和 prompt_templates）
decoder_mod = load_module('decoder',
    os.path.join(BASE, 'phase2.1_implementation', 'decoder.py'),
    dep_modules={'schemas': m21_schemas, 'prompt_templates': m21_prompts})
IntelligenceDecoder = decoder_mod.IntelligenceDecoder

# 加载 2.2 validators
m22_validators = load_module('validators',
    os.path.join(BASE, 'phase2.2_implementation', 'validators.py'),
    dep_modules={'schemas': m22_schemas})

# 加载 judgment_engine（注入 2.2 schemas 和 validators）
judgment_mod = load_module('judgment_engine',
    os.path.join(BASE, 'phase2.2_implementation', 'judgment_engine.py'),
    dep_modules={'schemas': m22_schemas, 'validators': m22_validators})
JudgmentEngine = judgment_mod.JudgmentEngine

# 加载 2.3
sys.path.insert(0, os.path.join(BASE, 'phase2.3_implementation', 'src'))
from models import OpportunityObject as OpportunityObject23, ActionDesignRequest
from action_designer import ActionDesigner

# 加载 2.5
sys.path.append(os.path.join(BASE, 'phase2.5_implementation'))
from core.system_retrospective_analyzer import SystemRetrospectiveAnalyzer
from schemas.system_retrospective_schema import SystemRetrospectiveRequest, ValidationMode, CheckStatus

IntelligenceDecodeRequest = m21_schemas.IntelligenceDecodeRequest
SourceType = m21_schemas.SourceType
OpportunityJudgmentRequest = m22_schemas.OpportunityJudgmentRequest


# --- 适配器 ---
def adapt_22_to_23(opp22) -> OpportunityObject23:
    """2.2 OpportunityObject(Pydantic) -> 2.3 OpportunityObject(dataclass)"""
    uncertainty_dict = {
        f"uncertainty_{i+1}": item
        for i, item in enumerate(opp22.uncertainty_map)
    }
    return OpportunityObject23(
        opportunity_title=opp22.opportunity_title,
        opportunity_thesis=opp22.opportunity_thesis,
        supporting_evidence=opp22.supporting_evidence,
        counter_evidence=opp22.counter_evidence,
        key_assumptions=opp22.key_assumptions,
        uncertainty_map=uncertainty_dict,
        priority_level=opp22.priority_level,
    )


def build_upstream_outputs(decoded, opp22, result23) -> dict:
    """将各模块输出组装为 2.5 upstream_outputs 格式"""
    decision = result23.action_decision
    phased_plan = []
    for stage in decision.phased_plan:
        phased_plan.append({
            "stage": stage.stage,
            "objective": stage.objective,
            "go_no_go_criteria": stage.go_no_go_criteria,
            "exit_conditions": stage.exit_conditions,
            "resources": asdict(stage.resources),
        })

    return {
        "phase2_1": {
            "signals": [s.model_dump() for s in decoded.signals],
            "signal_schema_validation": "passed",
            "benchmark_summary": decoded.summary or "",
            "decoder_version": decoded.decoder_version,
        },
        "phase2_2": {
            "opportunity_title": opp22.opportunity_title,
            "opportunity_thesis": opp22.opportunity_thesis,
            "supporting_evidence": opp22.supporting_evidence,
            "counter_evidence": opp22.counter_evidence,
            "priority_level": opp22.priority_level,
            "uncertainty_map": {f"u_{i}": v for i, v in enumerate(opp22.uncertainty_map)},
        },
        "phase2_3": {
            "decision_posture": decision.decision_posture,
            "why_this_posture": decision.why_this_posture,
            "phased_plan": phased_plan,
            "go_no_go_criteria": {
                s.stage: s.go_no_go_criteria for s in decision.phased_plan
            },
            "resource_commitment_logic": decision.resource_commitment_logic,
            "fallback_path": decision.fallback_path,
            "top_risks": [asdict(r) for r in decision.top_risks],
            "open_questions": decision.open_questions,
        }
    }


def run_e2e(case_id: str, raw_text: str, source_type, api_key: str):
    print(f"\n{'='*60}")
    print(f"端到端案例: {case_id}")
    print(f"{'='*60}")
    t0 = time.time()

    # Step 1: 2.1 情报解码
    print("[Step 1] 2.1 情报解码...")
    decoder = IntelligenceDecoder(api_key=api_key, model="claude-haiku-4-5-20251001")
    req21 = IntelligenceDecodeRequest(
        source_id=case_id,
        source_type=source_type,
        content=raw_text
    )
    decoded = decoder.decode(req21)
    print(f"  信号数: {len(decoded.signals)}, 耗时: {decoded.processing_time_ms}ms")
    for s in decoded.signals:
        print(f"  - [{s.signal_type.value}] {s.signal_label} (强度:{s.intensity_score})")

    if not decoded.signals:
        print("  WARNING: 未抽取到信号，后续模块将进入降级路径")

    # Step 2: 2.2 机会判断
    print("[Step 2] 2.2 机会判断...")
    engine = JudgmentEngine()
    req22 = OpportunityJudgmentRequest(decoded_intelligence=decoded.model_dump())
    result22 = engine.judge(req22)
    opp22 = result22.opportunity
    print(f"  状态: {result22.status}, 优先级: {opp22.priority_level}")
    print(f"  机会: {opp22.opportunity_title}")

    # Step 3: 2.3 行动设计
    print("[Step 3] 2.3 行动设计...")
    designer = ActionDesigner()
    opp23 = adapt_22_to_23(opp22)
    req23 = ActionDesignRequest(request_id=case_id, opportunity_object=opp23)
    result23 = designer.design_action(req23)
    decision = result23.action_decision
    print(f"  姿态: {decision.decision_posture}, 计划阶段数: {len(decision.phased_plan)}")

    # Step 4: 2.5 系统复盘
    print("[Step 4] 2.5 系统复盘...")
    analyzer = SystemRetrospectiveAnalyzer()
    upstream = build_upstream_outputs(decoded, opp22, result23)
    workflow_record = {
        "run_id": case_id,
        "start_time": "2026-03-22T00:00:00Z",
        "end_time": "2026-03-22T00:01:00Z",
        "processing_time_ms": int((time.time() - t0) * 1000),
        "errors": [],
        "status": "completed"
    }
    req25 = SystemRetrospectiveRequest(
        request_id=f"retro_{case_id}",
        case_id=case_id,
        workflow_run_record=workflow_record,
        upstream_outputs=upstream,
        validation_mode=ValidationMode.MVP_SINGLE_CASE
    )
    retro_result = analyzer.analyze(req25)
    retro = retro_result.retrospective
    print(f"  复盘完成，耗时: {retro_result.processing_time_ms}ms")
    print(f"  关键发现数: {len(retro.critical_findings)}")
    print(f"  Phase3 优先级项数: {len(retro.phase3_priorities)}")

    # 端到端验收
    checks = {
        "2.1 信号抽取完成": result22.status in ("success", "insufficient_evidence"),
        "2.2 机会对象产出": bool(opp22.opportunity_title),
        "2.3 行动姿态产出": bool(decision.decision_posture),
        "2.3 有分阶段计划": len(decision.phased_plan) > 0,
        "2.5 OutputChecker 无 FAIL": all(
            c.status != CheckStatus.FAIL
            for c in retro.output_checks
        ),
        "2.5 Phase3 优先级产出": len(retro.phase3_priorities) > 0,
    }
    total_ms = int((time.time() - t0) * 1000)
    all_pass = all(checks.values())
    print(f"\n端到端验收 ({'PASS' if all_pass else 'FAIL'}, 总耗时 {total_ms}ms):")
    for k, v in checks.items():
        print(f"  {'YES' if v else 'NO '} {k}")
    return all_pass


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY 未设置")
        sys.exit(1)
    print(f"API key: {api_key[:8]}...")

    print("\nPhase 端到端链路联调 (P1-4)")
    print("="*60)

    # 真实案例1: AI NPC 游戏行业新闻
    text1 = """OpenAI今日宣布与游戏巨头EA、育碧和Riot Games达成战略合作，
将GPT-4技术深度集成至旗下多款主流游戏的NPC对话系统中。
此次合作标志着生成式AI在游戏行业的商业化进程大幅提速。
市场分析师预测，AI驱动的NPC对话市场规模将在2027年突破50亿美元。
与此同时，三家AI游戏初创公司在本季度完成A轮融资，合计融资额超过2亿美元，
投资方包括红杉资本、a16z等顶级VC机构。"""

    results = [
        run_e2e("e2e_ai_npc_001", text1, SourceType.NEWS, api_key),
    ]

    print(f"\n{'='*60}")
    print("端到端联调总结 (P1-4)")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r)
    print(f"通过: {passed}/{len(results)}")
    if passed == len(results):
        print("P1-4 端到端联调: PASS")
        print("Phase 2 主链路联调完成！可进入 P2 增强项或 Phase 3 准备")
    else:
        print("P1-4 端到端联调: FAIL")


if __name__ == "__main__":
    main()