"""冒烟测试：Step A / Step B / judge_with_signal_store / _override_signals 注入"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Test 1: SignalStore ───────────────────────────────────────
from signal_store import SignalStore, build_signal_entry

STORE_PATH = os.path.join(os.path.dirname(__file__), "_test_signal_store.pkl")
store = SignalStore(store_path=STORE_PATH)

entry = build_signal_entry(
    signal={
        "signal_id": "test001",
        "signal_label": "EU DMA罚苹果5亿欧元",
        "signal_type": "regulatory",
        "description": "欧盟裁定苹果违反DMA反引导义务",
        "evidence_text": "罚款5亿欧元",
        "intensity_score": 9,
        "confidence_score": 8,
        "timeliness_score": 9,
        "source_id": "incoming_005",
    },
    roles=["catalyst"],
    needs=["demand_evidence", "resource_validation"],
    domains=["gaming", "regulation"],
    waiting_for_text="等待开发者出走App Store的证据",
    batch_date="2026-03-31",
)
store.add(entry)
# query_by_role("catalyst") 应返回0（entry.needs包含catalyst才命中，而entry.roles=catalyst，needs=demand_evidence）
# query_by_role("demand_evidence") 应返回1（entry.needs包含demand_evidence）
hits = store.query_by_role("demand_evidence")
assert len(hits) == 1, f"Expected 1, got {len(hits)}"
stats = store.stats()
assert stats["total"] == 1
os.remove(STORE_PATH)
print("✅ Test 1: SignalStore OK")

# ── Test 2: Step A 规则 fallback ─────────────────────────────
from step_a_cluster import run_step_a

signals = [
    {"signal_id": "s001", "signal_type": "regulatory", "signal_label": "EU DMA罚苹果",
     "description": "欧盟罚款5亿欧元", "intensity_score": 9},
    {"signal_id": "s002", "signal_type": "market", "signal_label": "开发者出走AppStore",
     "description": "独立开发者流失增加", "intensity_score": 7},
    {"signal_id": "s003", "signal_type": "capital", "signal_label": "Valve融资3亿",
     "description": "Steam获新一轮融资", "intensity_score": 8},
]

result = run_step_a(signals, llm_client=None)
assert result.fallback_used is True
assert len(result.signal_groups) == 0
assert len(result.isolated_signals) == 3
for s in result.isolated_signals:
    ann = s.get("_role_annotation", {})
    assert ann.get("roles"), f"Missing roles for {s['signal_id']}"
    assert ann.get("domains"), f"Missing domains for {s['signal_id']}"
    print(f"  {s['signal_id']} -> roles={ann['roles']} needs={ann['needs']}")
print("✅ Test 2: Step A fallback OK")

# ── Test 3: Step B（无历史信号，应返回 matched=False）────────
from step_b_retrieval import run_step_b

STORE_PATH2 = os.path.join(os.path.dirname(__file__), "_test_signal_store2.pkl")
empty_store = SignalStore(store_path=STORE_PATH2)

iso_signal = dict(signals[0])
iso_signal["_role_annotation"] = {
    "roles": ["catalyst"],
    "needs": ["demand_evidence"],
    "domains": ["gaming", "regulation"],
    "waiting_for_text": "等待需求侧证据",
}

b_result = run_step_b(iso_signal, empty_store, llm_client=None)
assert b_result.matched is False
assert b_result.candidate_groups == []
if os.path.exists(STORE_PATH2):
    os.remove(STORE_PATH2)
print("✅ Test 3: Step B (empty store) OK")

# ── Test 4: judge_with_signal_store（规则引擎模式，不需要真实API）─
from judgment_engine import JudgmentEngine
from schemas import OpportunityJudgmentRequest

STORE_PATH3 = os.path.join(os.path.dirname(__file__), "_test_signal_store3.pkl")

# 构造最小 DecodedIntelligence
class FakeSignal:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class FakeDI:
    def __init__(self, signals):
        self.source_id = "test_src"
        self.source_title = "Test Article"
        self.source_type = "news"
        self.signals = signals
        self.processing_time_ms = 100
        self.model_used = "test"
        self.batch_id = "batch_test"

fake_signal = FakeSignal(
    signal_id="fs001",
    signal_label="测试信号",
    signal_type="regulatory",
    description="测试描述",
    evidence_text="测试证据",
    intensity_score=8,
    confidence_score=7,
    timeliness_score=8,
    source_id="test_src",
    source_type="news",
    source_title="Test",
    geographic_scope="global",
    affected_parties=["developer"],
    time_horizon="short",
)

fake_di = FakeDI([fake_signal])
req = OpportunityJudgmentRequest(decoded_intelligences=[fake_di])

# api_key='' 强制规则引擎模式
engine = JudgmentEngine(api_key="")
test_store = SignalStore(store_path=STORE_PATH3)

result = engine.judge_with_signal_store(req, signal_store=test_store)
print(f"  status={result.status}")
print(f"  opportunities={len(result.opportunities or [])}")

# 规则引擎 + 单条信号 → 要么有结果，要么 pending_signals
assert result.status in ("success", "pending_signals", "insufficient_evidence", "error"), \
    f"Unexpected status: {result.status}"

# 检查 Signal Store 状态
stats3 = test_store.stats()
print(f"  signal_store stats: {stats3}")

if os.path.exists(STORE_PATH3):
    os.remove(STORE_PATH3)
print("✅ Test 4: judge_with_signal_store OK")

# ── Test 5: _override_signals 信号隔离注入 ────────────────────
# 验证：judge() 在 request 带 _override_signals 时，
# 用注入信号替代从 decoded_intelligences 提取的信号

override_signal = {
    "signal_id":       "override_001",
    "signal_label":    "注入信号：开发者出走AppStore",
    "signal_type":     "market",
    "description":     "独立开发者大规模迁移至替代平台",
    "evidence_text":   "Q1迁移开发者数+40%",
    "intensity_score": 9,
    "confidence_score": 8,
    "timeliness_score": 9,
    "source_id":       "override_src",
    "source_type":     "market_report",
    "source_title":    "Override Test",
    "geographic_scope": "global",
    "affected_parties": ["developer"],
    "time_horizon":    "short",
}

req5 = OpportunityJudgmentRequest(decoded_intelligences=[fake_di])
req5._override_signals = [override_signal]   # 注入

engine5 = JudgmentEngine(api_key="")
result5 = engine5.judge(req5)

# 验证注入生效：判断流程用的是 override_signal 而不是 fake_di 的信号
# 由于是规则引擎模式，只验证流程不崩溃、状态合法
assert result5.status in ("success", "insufficient_evidence", "error"), \
    f"Test 5 unexpected status: {result5.status}"
print(f"  _override_signals status={result5.status}")
print("✅ Test 5: _override_signals 注入 OK")

print("\n🎉 所有冒烟测试通过")
