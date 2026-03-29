"""
app.py — DesignAssistant 链路观察面板
运行：streamlit run app.py
"""

import streamlit as st
import os
import sys
import glob
from datetime import datetime

# 路径
# 路径：dashboard/ → proj_004/ → projects/ → data-layer/ → DesignAssistant/
PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # proj_004/
DA_ROOT = os.path.normpath(os.path.join(PROJ_DIR, "..", "..", ".."))    # DesignAssistant/

INCOMING_DIR = os.path.normpath(os.path.join(DA_ROOT, "background", "real_intel_samples", "incoming"))
PROCESSED_DIR = os.path.normpath(os.path.join(DA_ROOT, "background", "real_intel_samples", "processed"))
REPORTS_DIR = os.path.join(PROJ_DIR, "reports")
ENV_PATH = os.path.join(PROJ_DIR, ".env")

sys.path.insert(0, PROJ_DIR)

# ── 页面基础配置 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="DesignAssistant 观察面板",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.step-header { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.3rem; }
.tag-llm { background: #1a7f3c; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem; }
.tag-fallback { background: #b45309; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem; }
.tag-noise { background: #6b7280; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem; }
.tag-signal { background: #1d4ed8; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.75rem; }
.finding-high { border-left: 3px solid #dc2626; padding-left: 8px; margin: 4px 0; }
.finding-medium { border-left: 3px solid #d97706; padding-left: 8px; margin: 4px 0; }
.finding-low { border-left: 3px solid #6b7280; padding-left: 8px; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)


# ── 辅助渲染函数（必须在主体之前定义）────────────────────────────
def _render_list(items: list):
    if not items:
        st.caption("（无数据）")
        return
    for item in items:
        if isinstance(item, dict):
            label = (item.get("summary") or item.get("description") or
                     item.get("text") or item.get("content") or str(item))[:200]
            remaining = {k: v for k, v in item.items()
                         if k not in ("summary","description","text","content") and v}
            if remaining:
                with st.expander(label):
                    for k, v in remaining.items():
                        st.caption(f"**{k}**: {str(v)[:300]}")
            else:
                st.markdown(f"- {label}")
        else:
            st.markdown(f"- {str(item)[:200]}")

import yaml as _yaml

# ── 读取 llm_config.yaml ─────────────────────────────────────────
LLM_CONFIG_PATH = os.path.join(PROJ_DIR, "llm_config.yaml")

def load_llm_config() -> dict:
    if os.path.exists(LLM_CONFIG_PATH):
        with open(LLM_CONFIG_PATH, encoding="utf-8") as f:
            return _yaml.safe_load(f) or {}
    return {}

def save_llm_config(cfg: dict):
    with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
        _yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def get_phase_model(cfg: dict, phase: str) -> str:
    return cfg.get("phases", {}).get(phase, {}).get("model") or cfg.get("default", {}).get("model", "claude-sonnet-4-6")

# ── 读取 .env ────────────────────────────────────────────────────
def load_env_defaults():
    defaults = {"api_key": "", "base_url": "https://api123.icu"}
    env_file = os.path.join(DA_ROOT, ".env")
    if os.path.exists(env_file):
        for line in open(env_file, encoding="utf-8"):
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                defaults["api_key"] = line.split("=", 1)[1].strip()
            elif line.startswith("ANTHROPIC_BASE_URL="):
                defaults["base_url"] = line.split("=", 1)[1].strip()
    return defaults

# ── 顶部：配置区 ─────────────────────────────────────────────────
st.title("🔬 DesignAssistant 链路观察面板")

defaults = load_env_defaults()
llm_cfg = load_llm_config()

with st.container(border=True):
    st.caption("**全局配置**")
    col1, col2 = st.columns([3, 3])
    with col1:
        api_key = st.text_input("API Key", value=defaults["api_key"], type="password",
                                 placeholder="ANTHROPIC_API_KEY")
    with col2:
        base_url = st.text_input("Base URL", value=defaults["base_url"])

    st.caption("**各模块模型配置**（修改后点「保存配置」写入 llm_config.yaml）")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        m21 = st.text_input("2.1 情报解码", value=get_phase_model(llm_cfg, "2.1"), key="m21")
    with mc2:
        m22 = st.text_input("2.2 机会判断", value=get_phase_model(llm_cfg, "2.2"), key="m22")
    with mc3:
        m23 = st.text_input("2.3 行动设计", value=get_phase_model(llm_cfg, "2.3"), key="m23")
    with mc4:
        m25 = st.text_input("2.5 复盘归因", value=get_phase_model(llm_cfg, "2.5"), key="m25")

    save_col, stat_col = st.columns([1, 4])
    with save_col:
        if st.button("💾 保存配置", use_container_width=True):
            # 只更新 model 字段，其余字段（base_url/max_tokens 等）保持原值
            for phase, new_model in [("2.1", m21), ("2.2", m22), ("2.3", m23), ("2.5", m25)]:
                if "phases" not in llm_cfg:
                    llm_cfg["phases"] = {}
                if phase not in llm_cfg["phases"]:
                    llm_cfg["phases"][phase] = {}
                llm_cfg["phases"][phase]["model"] = new_model
            save_llm_config(llm_cfg)
            st.success("已保存到 llm_config.yaml")
    with stat_col:
        incoming_count = len(glob.glob(os.path.join(INCOMING_DIR, "*.json")))
        st.metric("incoming/ 样本数", incoming_count, label_visibility="visible")

# ── incoming 样本预览 ────────────────────────────────────────────
with st.expander(f"📁 incoming/ 目录（{incoming_count} 个文件）", expanded=incoming_count > 0):
    if incoming_count == 0:
        st.info("incoming/ 为空，请先将样本 JSON 文件放入该目录")
        st.code(os.path.normpath(INCOMING_DIR))
    else:
        files = sorted(glob.glob(os.path.join(INCOMING_DIR, "*.json")))
        for f in files:
            st.text(f"  • {os.path.basename(f)}")

# ── 运行按钮 ─────────────────────────────────────────────────────
run_col, _ = st.columns([1, 4])
with run_col:
    run_btn = st.button("▶ 开始运行", type="primary", disabled=(incoming_count == 0), use_container_width=True)

st.divider()

# ── 主内容区 ─────────────────────────────────────────────────────
# 用 session_state 存储上次运行结果，允许刷新后仍可查看
if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "running" not in st.session_state:
    st.session_state.running = False

# ── 运行逻辑 ────────────────────────────────────────────────────
if run_btn:
    st.session_state.running = True
    st.session_state.run_result = {
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "step_21": None, "step_22": None, "step_23": None,
        "step_24_packets": [], "step_25": None,
        "report_path": None, "total_ms": None,
        "logs": [], "errors": [],
    }

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from pipeline_runner import run_pipeline

    # 进度占位符
    progress_bar = st.progress(0, text="初始化…")
    log_area = st.empty()

    STEP_WEIGHTS = {"2.1": 0.2, "2.2": 0.4, "2.3": 0.6, "2.4": 0.5, "2.5": 0.85}

    for event in run_pipeline(api_key, base_url):
        etype = event["type"]
        step = event.get("step")
        msg = event.get("message", "")
        data = event.get("data", {})

        # 日志
        st.session_state.run_result["logs"].append(f"[{etype}][{step or '-'}] {msg}")
        log_area.caption(" | ".join(st.session_state.run_result["logs"][-3:]))

        if etype == "step_start" and step in STEP_WEIGHTS:
            progress_bar.progress(max(0.05, STEP_WEIGHTS[step] - 0.15), text=f"{step} 进行中…")

        elif etype == "step_done":
            completed_steps.add(step)
            progress_bar.progress(STEP_WEIGHTS.get(step, 0.5), text=f"{step} 完成 ✓")

            if step == "2.1":
                st.session_state.run_result["step_21"] = data
            elif step == "2.2":
                st.session_state.run_result["step_22"] = data
                st.session_state.run_result["step_24_packets"] = data.get("rag_packets", [])
            elif step == "2.3":
                st.session_state.run_result["step_23"] = data
            elif step == "2.5":
                st.session_state.run_result["step_25"] = data
                # 2.5 查的 RAG 证据回填到 2.4 展示区（2.2 阶段不单独查 RAG）
                if data.get("rag_packets"):
                    st.session_state.run_result["step_24_packets"] = data["rag_packets"]

        elif etype == "error":
            st.session_state.run_result["errors"].append({"step": step, "message": msg, "detail": data.get("traceback", "")})
            progress_bar.progress(1.0, text=f"❌ {step} 出错")

        elif etype == "pipeline_done":
            st.session_state.run_result["total_ms"] = data.get("total_ms")
            st.session_state.run_result["report_path"] = data.get("report_path")
            progress_bar.progress(1.0, text=f"✅ 全链路完成，耗时 {data.get('total_ms',0)//1000}s")

    st.session_state.running = False
    st.rerun()

# ── 展示上次运行结果 ─────────────────────────────────────────────
result = st.session_state.run_result
if result is None:
    st.info("点击「▶ 开始运行」启动链路分析。首次运行请确保 incoming/ 目录中有样本文件。")
else:
    st.caption(f"运行时间：{result['started_at']}  |  总耗时：{(result.get('total_ms') or 0)//1000}s")

    # 错误提示
    for err in result.get("errors", []):
        with st.expander(f"❌ {err['step']} 出错：{err['message']}", expanded=True):
            st.code(err.get("detail", ""), language="text")

    # ── 2.1 ─────────────────────────────────────────────────────
    d21 = result.get("step_21")
    with st.container(border=True):
        st.markdown("### 📥 Phase 2.1 — 情报解码")
        if d21 is None:
            st.caption("尚未运行")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("输入样本", len(d21.get("samples", [])))
            c2.metric("提取信号", d21.get("signal_total", 0))
            c3.metric("噪音样本", d21.get("noise_count", 0))

            for s in d21.get("samples", []):
                is_noise = s.get("is_noise", False)
                tag = "🔇 噪音" if is_noise else f"✅ {s.get('signal_count',0)} 个信号"
                with st.expander(f"{'🔇' if is_noise else '📄'} {s['source_id']}  —  {tag}", expanded=not is_noise):
                    if is_noise:
                        st.caption("未提取到有效信号（噪音样本）")
                    else:
                        for sig in s.get("signals", []):
                            sig_type = sig.get("signal_type", "?")
                            sig_label = sig.get("signal_label", sig.get("description", "")[:60])
                            intensity = sig.get("intensity_score", sig.get("intensity", "?"))
                            confidence = sig.get("confidence_score", sig.get("confidence", "?"))
                            st.markdown(f"**[{sig_type}]** {sig_label}")
                            ci, co = st.columns(2)
                            ci.caption(f"强度: {intensity}")
                            co.caption(f"置信: {confidence}")
                            if sig.get("evidence_text"):
                                st.caption(f"原文片段：{sig['evidence_text'][:200]}…")

    # ── 2.2 ─────────────────────────────────────────────────────
    d22 = result.get("step_22")
    with st.container(border=True):
        st.markdown("### 🔍 Phase 2.2 — 机会判断")
        if d22 is None:
            st.caption("尚未运行")
        else:
            opp = d22.get("opportunity", {})
            llm_tag = "✅ LLM生成" if opp.get("llm_used") else "⚠️ 规则引擎 fallback"
            st.markdown(f"**{opp.get('title','（无标题）')}**  &nbsp; `{opp.get('priority_level','')}` &nbsp; {llm_tag}",
                        unsafe_allow_html=True)
            if opp.get("thesis"):
                st.caption(opp["thesis"][:300] + ("…" if len(opp.get("thesis","")) > 300 else ""))

            tabs = st.tabs(["支持证据", "反对证据", "关键假设", "为什么是现在", "下一步验证", "不确定性", "2.4证据包"])

            with tabs[0]:
                _render_list(opp.get("supporting_evidence", []))
            with tabs[1]:
                _render_list(opp.get("counter_evidence", []))
            with tabs[2]:
                _render_list(opp.get("key_assumptions", []))
            with tabs[3]:
                st.write(opp.get("why_now") or "（未填写）")
            with tabs[4]:
                _render_list(opp.get("next_validation_questions", []))
            with tabs[5]:
                _render_list(opp.get("uncertainty_map", []))
            with tabs[6]:
                packets = result.get("step_24_packets", []) or d22.get("rag_packets", [])
                if not packets:
                    st.caption("本次未命中 2.4 证据包（RAG fallback 或无匹配）")
                else:
                    for p in packets:
                        with st.expander(f"[{p.get('content_type','?')}] {p.get('source_title','?')}  score={p.get('score',0):.3f}"):
                            st.caption(f"来源：{p.get('source_id')}  |  可信度：{p.get('trust_level')}")
                            st.write(p.get("excerpt", ""))
                            st.caption(f"命中原因：{p.get('reason_for_match','')}")

            if opp.get("warnings"):
                for w in opp["warnings"]:
                    st.warning(w)

    # ── 2.3 ─────────────────────────────────────────────────────
    d23 = result.get("step_23")
    with st.container(border=True):
        st.markdown("### 🎯 Phase 2.3 — 行动设计")
        if d23 is None:
            st.caption("尚未运行")
        else:
            act = d23.get("action", {})
            llm_tag = "✅ LLM三路辩论" if act.get("llm_used") else "⚠️ 规则引擎 fallback"
            st.markdown(f"**行动姿态：`{act.get('posture','')}`**  &nbsp; {llm_tag}", unsafe_allow_html=True)
            if act.get("why"):
                st.caption(act["why"][:200])

            tabs = st.tabs(["辩论过程", "分阶段计划", "主要风险", "退出条件"])

            with tabs[0]:
                debate = act.get("debate_summary", {})
                if not debate:
                    st.caption("LLM 未跑通，无辩论记录")
                else:
                    st.markdown("**🦅 鹰派（激进）**")
                    st.write(debate.get("hawk_position", ""))
                    st.markdown("**🕊️ 鸽派（保守）**")
                    st.write(debate.get("dove_position", ""))
                    st.markdown("**⚖️ 仲裁结论**")
                    st.write(debate.get("arbitrator_verdict", ""))
                    st.caption(f"共识程度：{debate.get('consensus_level','')}")
            with tabs[1]:
                _render_list(act.get("phases", []))
            with tabs[2]:
                _render_list(act.get("top_risks", []))
            with tabs[3]:
                _render_list(act.get("exit_conditions", []))

    # ── 2.5 ─────────────────────────────────────────────────────
    d25 = result.get("step_25")
    with st.container(border=True):
        st.markdown("### 🔄 Phase 2.5 — 复盘归因")
        if d25 is None:
            st.caption("尚未运行")
        else:
            retro = d25.get("retrospective", {})
            if retro.get("workflow_summary"):
                st.caption(retro["workflow_summary"][:200])

            findings = retro.get("critical_findings", [])
            causes = retro.get("suspected_root_causes", [])
            priorities = retro.get("phase3_priorities", [])

            c1, c2, c3 = st.columns(3)
            c1.metric("关键发现", len(findings))
            c2.metric("根因归因", len(causes))
            c3.metric("Phase3 优先项", len(priorities))

            tabs = st.tabs(["关键发现", "根因归因", "Phase3 优先项"])
            with tabs[0]:
                for f in findings:
                    sev = f.get("severity", "").lower()
                    css = f"finding-{sev}" if sev in ("high","medium","low") else "finding-low"
                    st.markdown(
                        f'<div class="{css}"><b>[{sev.upper()}][{f.get("layer","")}]</b> {f.get("summary","")}</div>',
                        unsafe_allow_html=True
                    )
                    if f.get("evidence") or f.get("impact"):
                        with st.expander("详情"):
                            if f.get("evidence"):
                                st.caption(f"证据：{f['evidence']}")
                            if f.get("impact"):
                                st.caption(f"影响：{f['impact']}")
            with tabs[1]:
                _render_list(causes)
            with tabs[2]:
                _render_list(priorities)

    # ── 报告入口 ─────────────────────────────────────────────────
    report_path = result.get("report_path")
    if report_path and os.path.exists(report_path):
        with st.container(border=True):
            st.markdown("### 📄 报告输出")
            st.success(f"报告已生成：`{os.path.basename(report_path)}`")
            with open(report_path, encoding="utf-8") as f:
                st.download_button("⬇ 下载报告", f.read(), file_name=os.path.basename(report_path), mime="text/markdown")
            with st.expander("预览报告内容"):
                content = open(report_path, encoding="utf-8").read()
                st.markdown(content[:3000] + ("\n\n…（报告过长，已截断，请下载查看完整内容）" if len(content) > 3000 else ""))


# ── 辅助渲染函数 ─────────────────────────────────────────────────
def _render_list(items: list):
    if not items:
        st.caption("（无数据）")
        return
    for item in items:
        if isinstance(item, dict):
            # 优先展示 summary / description / text 字段
            label = (item.get("summary") or item.get("description") or
                     item.get("text") or item.get("content") or str(item))[:200]
            remaining = {k: v for k, v in item.items()
                         if k not in ("summary","description","text","content") and v}
            if remaining:
                with st.expander(label):
                    for k, v in remaining.items():
                        st.caption(f"**{k}**: {str(v)[:300]}")
            else:
                st.markdown(f"- {label}")
        else:
            st.markdown(f"- {str(item)[:200]}")
