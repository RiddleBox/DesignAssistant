"""
unit_tests_phase22.py — Phase 2.2 Signal Store 编排逻辑单元测试

覆盖范围：
  T01 - build_signal_entry: signal_type 枚举 → 纯字符串
  T02 - SignalStore: add / query_pending / stats 基本读写
  T03 - SignalStore: contributed 信号不出现在 query_pending
  T04 - Step A: 无 LLM 时 fallback 保证信号不丢失
  T05 - Step B: 孤立信号命中历史 pending 信号（跨批次匹配核心路径）
  T06 - Step B: 无历史伙伴时 matched=False
  T07 - Step B: query_pending 是 Step B 跨批次的前提条件
  T08 - judge_with_signal_store: signal_store=None 必须报错
  T09 - judge_with_signal_store: 全批成功后 contributed 信号写入 store

运行：
  cd D:\\AIproject\\DesignAssistant\\data-layer\\projects\\proj_004
  python unit_tests_phase22.py
"""

import sys
import os
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

# ── 路径设置 ──────────────────────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_impl = os.path.join(_here, "phase2.2_implementation")
if _impl not in sys.path:
    sys.path.insert(0, _impl)

from signal_store import SignalStore, SignalEntry, build_signal_entry, OpportunityStore


# ── 工具函数 ──────────────────────────────────────────────────────────────────
def _make_signal(sid="s001", stype="capital", label="测试信号"):
    return {
        "signal_id": sid,
        "signal_label": label,
        "signal_type": stype,
        "description": "测试描述",
        "evidence_text": "测试证据",
        "intensity_score": 7,
        "confidence_score": 8,
        "timeliness_score": 7,
        "source_id": f"src_{sid}",
    }


def _make_entry(sid="s001", stype="capital", label="测试信号", status="pending"):
    e = build_signal_entry(
        signal=_make_signal(sid, stype, label),
        roles=["catalyst"],
        needs=["resource_validation"],
        domains=["gaming"],
        waiting_for_text="等待配对信号",
        batch_date="2026-03-31",
    )
    e.status = status
    return e


class TmpStoreMixin:
    """
    为每个测试用例提供独立的临时目录，避免 pkl 互相污染。
    通过 monkey-patch SignalStore.__init__ 重定向 store_path。
    """
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._pkl = os.path.join(self._tmpdir, "signal_store.pkl")
        self._orig_init = SignalStore.__init__
        _pkl = self._pkl

        def patched_init(self_store):
            self_store.store_path = _pkl
            self_store._store = {}
            self_store._load()

        SignalStore.__init__ = patched_init

    def tearDown(self):
        SignalStore.__init__ = self._orig_init
        shutil.rmtree(self._tmpdir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# T01: build_signal_entry signal_type 枚举安全性
# ─────────────────────────────────────────────────────────────────────────────
class TestBuildSignalEntryEnumSafety(unittest.TestCase):
    """
    signal_type 写入 SignalEntry 时必须是纯字符串。
    2.1 decoder 输出的是 SignalType 枚举，直接存入 pkl 会引用
    动态加载的模块 (schemas_21.SignalType)，导致反序列化失败。
    """

    def test_plain_string_passthrough(self):
        e = build_signal_entry(
            signal=_make_signal(stype="regulatory"),
            roles=["catalyst"], needs=[], domains=["gaming"],
            waiting_for_text="", batch_date="2026-03-31",
        )
        self.assertEqual(e.signal_type, "regulatory")
        self.assertIsInstance(e.signal_type, str)

    def test_enum_with_value_attr(self):
        """模拟 2.1 decoder 产出的枚举：有 .value 属性"""
        class FakeEnum:
            value = "capital"
            def __str__(self): return "SignalType.capital"

        e = build_signal_entry(
            signal=_make_signal(stype=FakeEnum()),
            roles=["catalyst"], needs=[], domains=["gaming"],
            waiting_for_text="", batch_date="2026-03-31",
        )
        self.assertEqual(e.signal_type, "capital")
        self.assertIsInstance(e.signal_type, str)

    def test_enum_repr_fallback(self):
        """无 .value 属性的枚举 repr：SignalType.TEAM → team"""
        class FakeEnumNoValue:
            def __str__(self): return "SignalType.TEAM"

        e = build_signal_entry(
            signal=_make_signal(stype=FakeEnumNoValue()),
            roles=[], needs=[], domains=[],
            waiting_for_text="", batch_date="2026-03-31",
        )
        self.assertEqual(e.signal_type, "team")
        self.assertIsInstance(e.signal_type, str)


# ─────────────────────────────────────────────────────────────────────────────
# T02: SignalStore 基本读写
# ─────────────────────────────────────────────────────────────────────────────
class TestSignalStoreBasic(TmpStoreMixin, unittest.TestCase):

    def test_add_and_query_pending(self):
        store = SignalStore()
        e = _make_entry("s001", status="pending")
        store.add(e)

        pending = store.query_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].signal_id, e.signal_id)

    def test_add_batch(self):
        store = SignalStore()
        entries = [_make_entry(f"s{i:03d}", status="pending") for i in range(3)]
        store.add_batch(entries)
        self.assertEqual(store.stats()["total"], 3)

    def test_update_status(self):
        store = SignalStore()
        e = _make_entry("s001", status="pending")
        store.add(e)
        store.update_status(e.signal_id, "matched", "opp_abc")

        updated = store._store[e.signal_id]
        self.assertEqual(updated.status, "matched")
        self.assertEqual(updated.matched_opportunity_id, "opp_abc")

    def test_persistence_across_instances(self):
        """写入后重新加载（同一 pkl 路径），数据应持久化"""
        store1 = SignalStore()
        e = _make_entry("s001", status="pending")
        store1.add(e)

        store2 = SignalStore()
        self.assertEqual(store2.stats()["total"], 1)
        self.assertEqual(store2._store[e.signal_id].signal_label, e.signal_label)


# ─────────────────────────────────────────────────────────────────────────────
# T03: contributed 信号不参与 query_pending
# ─────────────────────────────────────────────────────────────────────────────
class TestQueryPendingExcludesContributed(TmpStoreMixin, unittest.TestCase):
    """
    设计约束：contributed 信号已参与成功机会，不应再被 Step B 检索到。
    query_pending 只返回 pending 状态的信号。
    """

    def test_contributed_not_in_query_pending(self):
        store = SignalStore()
        pending     = _make_entry("sp",  status="pending")
        contributed = _make_entry("sc",  status="contributed")
        store.add_batch([pending, contributed])

        pending_ids = {e.signal_id for e in store.query_pending()}
        self.assertIn(pending.signal_id, pending_ids)
        self.assertNotIn(contributed.signal_id, pending_ids,
                         "contributed 信号不应出现在 query_pending 结果中")

    def test_stats_counts_all_statuses(self):
        store = SignalStore()
        store.add_batch([
            _make_entry("s1", status="pending"),
            _make_entry("s2", status="contributed"),
            _make_entry("s3", status="contributed"),
        ])
        stats = store.stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["by_status"].get("pending", 0), 1)
        self.assertEqual(stats["by_status"].get("contributed", 0), 2)


# ─────────────────────────────────────────────────────────────────────────────
# T04: Step A 信号完整性（无 LLM fallback）
# ─────────────────────────────────────────────────────────────────────────────
class TestStepASignalIntegrity(unittest.TestCase):
    """
    设计约束：Step A 不应丢失任何输入信号。
    无论 LLM 是否可用，signal_groups + isolated_signals 的信号总数
    必须等于输入信号总数。
    """

    def test_no_signal_loss_with_rule_fallback(self):
        """llm_client=None → 规则 fallback，信号不丢失"""
        from step_a_cluster import run_step_a

        signals = [
            _make_signal("s001", "capital", "信号A"),
            _make_signal("s002", "team",    "信号B"),
            _make_signal("s003", "capital", "信号C"),
        ]
        result = run_step_a(signals, llm_client=None, model="mock")
        total_out = len(result.isolated_signals) + sum(len(g) for g in result.signal_groups)
        self.assertEqual(total_out, len(signals),
                         f"Step A 输出 {total_out} 条，输入 {len(signals)} 条，存在信号丢失")

    def test_single_signal_not_lost(self):
        """单条信号 fallback 后也应被完整保留"""
        from step_a_cluster import run_step_a

        signals = [_make_signal("s001", "capital", "Nacon 破产")]
        result = run_step_a(signals, llm_client=None, model="mock")
        total_out = len(result.isolated_signals) + sum(len(g) for g in result.signal_groups)
        self.assertEqual(total_out, 1)


# ─────────────────────────────────────────────────────────────────────────────
# T05: Step B 跨批次匹配 — 找到历史伙伴（核心场景）
# ─────────────────────────────────────────────────────────────────────────────
class TestStepBCrossBatchMatch(TmpStoreMixin, unittest.TestCase):
    """
    跨批次匹配完整路径：
      batch1 写入 pending 信号 → batch2 来孤立信号 → Step B L1 命中 →
      L4 LLM 确认（mock）→ matched=True，candidate_groups 非空

    L1 命中条件：新信号的 roles 与历史信号的 needs 存在交集。
    这里构造：新信号 roles=["execution_risk"]，历史信号 needs=["execution_risk"]
    """

    def _make_nacon_entry(self):
        """batch1 遗留的 Nacon 破产 pending 信号"""
        e = build_signal_entry(
            signal=_make_signal("nacon_001", "capital", "Nacon 破产"),
            roles=["catalyst"],
            needs=["execution_risk"],   # 等待有执行风险补全的信号
            domains=["gaming"],
            waiting_for_text="等待工作室资产重组信号",
            batch_date="2026-03-31",
        )
        e.status = "pending"
        return e

    def _make_new_signal(self):
        """batch2 的新信号：来自法国工作室资产出售"""
        s = _make_signal("new_fr_001", "capital", "法国工作室资产出售")
        s["_role_annotation"] = {
            "roles": ["execution_risk"],   # 与 Nacon needs 匹配
            "needs": ["catalyst"],
            "domains": ["gaming"],
            "waiting_for_text": "",
        }
        return s

    @patch("step_b_retrieval._l4_llm_confirm")
    def test_step_b_finds_historical_partner(self, mock_l4):
        """
        L1 命中 + mock L4 确认 → matched=True，candidate_groups 包含历史信号
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        nacon = self._make_nacon_entry()
        store.add(nacon)

        new_signal = self._make_new_signal()

        # mock L4：确认可以组合
        mock_l4.return_value = [[nacon]]

        result = run_step_b(
            isolated_signal=new_signal,
            signal_store=store,
            llm_client=MagicMock(),   # 非 None，才会走 L4
            model="mock",
        )

        self.assertTrue(result.matched,
                        "Step B 应识别历史伙伴，returned matched=False")
        self.assertGreater(len(result.candidate_groups), 0,
                           "candidate_groups 应非空")
        all_ids = [e.signal_id for g in result.candidate_groups for e in g]
        self.assertIn(nacon.signal_id, all_ids,
                      "历史信号应出现在 candidate_groups 中")

    @patch("step_b_retrieval._l4_llm_confirm")
    def test_step_b_no_l1_hit_returns_false(self, mock_l4):
        """
        L1 无命中（空 store）→ matched=False，不调用 L4
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()  # 空 store

        new_signal = self._make_new_signal()
        result = run_step_b(
            isolated_signal=new_signal,
            signal_store=store,
            llm_client=MagicMock(),
            model="mock",
        )

        self.assertFalse(result.matched)
        self.assertEqual(len(result.candidate_groups), 0)
        mock_l4.assert_not_called()  # L1 无命中时不应调 L4

    @patch("step_b_retrieval._l4_llm_confirm")
    def test_step_b_l4_returns_empty_uses_fallback(self, mock_l4):
        """
        L4 返回空 → fallback_used=True，把 L2 候选作为单组返回
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        nacon = self._make_nacon_entry()
        store.add(nacon)

        new_signal = self._make_new_signal()
        mock_l4.return_value = []  # L4 无法确认

        result = run_step_b(
            isolated_signal=new_signal,
            signal_store=store,
            llm_client=MagicMock(),
            model="mock",
        )

        # L4 无确认但 L2 有候选 → fallback=True，matched=True（让 Step C 判断）
        self.assertTrue(result.fallback_used,
                        "L4 无确认时应使用 fallback")
        self.assertTrue(result.matched,
                        "L2 有候选时 fallback 路径 matched 应为 True")


# ─────────────────────────────────────────────────────────────────────────────
# T06: query_pending 是 Step B 跨批次检索的前提
# ─────────────────────────────────────────────────────────────────────────────
class TestQueryPendingForStepB(TmpStoreMixin, unittest.TestCase):

    def test_pending_signal_retrievable_after_persist(self):
        """
        batch1 写入 pending 信号并持久化后，
        新 SignalStore 实例也能通过 query_pending 取到它，
        这是 Step B 跨批次检索的前提。
        """
        store1 = SignalStore()
        nacon = _make_entry("nacon_001", "capital", "Nacon 破产", status="pending")
        store1.add(nacon)

        # 模拟新批次：新建 store 实例重新加载
        store2 = SignalStore()
        pending = store2.query_pending()
        pending_ids = [e.signal_id for e in pending]

        self.assertIn(nacon.signal_id, pending_ids,
                      "batch1 写入的 pending 信号应能在新 store 实例中被 query_pending 检索到")


# ─────────────────────────────────────────────────────────────────────────────
# T07: judge_with_signal_store 接口契约
# ─────────────────────────────────────────────────────────────────────────────
class TestJudgeWithSignalStoreContract(unittest.TestCase):

    def test_signal_store_none_raises_value_error(self):
        """
        signal_store=None 必须抛出 ValueError。
        设计原因：内部 importlib 动态创建的 SignalStore 与外部 sys.path
        加载的类名不同，pickle 会反序列化失败，必须由调用方统一创建。
        """
        from judgment_engine import JudgmentEngine
        from schemas import OpportunityJudgmentRequest

        engine = JudgmentEngine(api_key="")  # 规则引擎模式
        req = OpportunityJudgmentRequest(decoded_intelligences=[])

        with self.assertRaises(ValueError,
                               msg="signal_store=None 时必须抛出 ValueError"):
            engine.judge_with_signal_store(req, signal_store=None)


# ─────────────────────────────────────────────────────────────────────────────
# T08: 全批成功后 contributed 信号写入 Signal Store（端到端 mock）
# ─────────────────────────────────────────────────────────────────────────────
class TestContributedWrittenOnSuccess(TmpStoreMixin, unittest.TestCase):

    def _make_mock_opportunity(self):
        """构造符合 OpportunityObject schema 的最小 mock 对象"""
        from schemas import OpportunityObject
        return OpportunityObject(
            opportunity_id="opp_test_001",
            opportunity_title="测试机会",
            opportunity_thesis="这是测试论点",
            priority_level="deep_dive",
            supporting_evidence=["证据1", "证据2"],
            counter_evidence=[],
            key_assumptions=["假设1"],
            uncertainty_map=["主要不确定因素：政策落地时间"],
            validation_questions=[],
            next_validation_questions=["验证问题1"],
            related_signals=[],
            why_now="现在是合适时机",
            action_recommendation="建议行动",
            judgment_version="v2.0-llm",
            processing_time_ms=1000,
        )

    def test_contributed_written_when_judge_succeeds(self):
        """
        当 judge() 成功产出机会时，参与信号应以 contributed 状态写入 Signal Store。

        mock 策略：
        - patch JudgmentEngine.judge() 直接返回成功结果，跳过真实 LLM
        - patch JudgmentEngine._extract_enriched_signals 返回带角色标注的信号
        - patch step_a_cluster 模块让 run_step_a 返回预定义分组
        - 验证 judgment_engine 的 Signal Store 写入逻辑
        """
        from judgment_engine import JudgmentEngine
        from schemas import OpportunityJudgmentRequest, OpportunityJudgmentResult

        opp = self._make_mock_opportunity()
        mock_result = OpportunityJudgmentResult(
            opportunities=[opp],
            status="success",
            diagnostics=None,
        )

        signal_dict = _make_signal("s001", "capital", "测试信号")
        signal_dict["_role_annotation"] = {
            "roles": ["catalyst"],
            "needs": ["resource_validation"],
            "domains": ["gaming"],
            "waiting_for_text": "等待配对",
        }

        from step_a_cluster import StepAResult
        mock_step_a = StepAResult.__new__(StepAResult)
        mock_step_a.signal_groups = [[signal_dict]]
        mock_step_a.isolated_signals = []
        mock_step_a.role_annotations = {}
        mock_step_a.fallback_used = False

        # patch judge()：控制 Step C 输出
        # patch _extract_enriched_signals：让信号池为预定义信号
        # patch sys.modules['step_a_cluster'].run_step_a：拦截函数体内的 from import
        import sys as _sys
        import step_a_cluster as _sa_mod
        original_run_step_a = _sa_mod.run_step_a
        _sa_mod.run_step_a = lambda *a, **kw: mock_step_a
        _sys.modules["step_a_cluster"].run_step_a = _sa_mod.run_step_a

        import golden_pattern as _gp_mod
        original_gp = _gp_mod.maybe_write_golden_pattern
        _gp_mod.maybe_write_golden_pattern = lambda *a, **kw: None
        _sys.modules["golden_pattern"].maybe_write_golden_pattern = _gp_mod.maybe_write_golden_pattern

        try:
            with patch.object(JudgmentEngine, "judge", return_value=mock_result):
                with patch.object(JudgmentEngine, "_extract_enriched_signals",
                                  return_value=[signal_dict]):
                    engine = JudgmentEngine(api_key="")
                    store = SignalStore()
                    req = OpportunityJudgmentRequest(decoded_intelligences=[])
                    result = engine.judge_with_signal_store(req, signal_store=store)
        finally:
            _sa_mod.run_step_a = original_run_step_a
            _sys.modules["step_a_cluster"].run_step_a = original_run_step_a
            _gp_mod.maybe_write_golden_pattern = original_gp
            _sys.modules["golden_pattern"].maybe_write_golden_pattern = original_gp

        self.assertEqual(result.status, "success")
        stats = store.stats()
        self.assertGreater(stats["total"], 0,
                           "成功产出机会后，Signal Store 应有信号被写入")
        self.assertGreater(stats["by_status"].get("contributed", 0), 0,
                           "参与成功机会的信号应为 contributed 状态")

    def test_pending_written_when_no_opportunity(self):
        """
        当批次无孤立信号且全组判断失败（opportunities 为空）时，
        参与信号应以 pending 或不写入（根据当前实现：孤立信号才写 pending）。
        本测试验证：不产出机会时 contributed 信号为 0。
        """
        from judgment_engine import JudgmentEngine
        from schemas import OpportunityJudgmentRequest, OpportunityJudgmentResult

        mock_result = OpportunityJudgmentResult(
            opportunities=[],
            status="insufficient_evidence",
            diagnostics=None,
        )

        with patch.object(JudgmentEngine, "judge", return_value=mock_result):
            engine = JudgmentEngine(api_key="")

            signal_dict = _make_signal("s001", "capital", "测试信号")
            signal_dict["_role_annotation"] = {
                "roles": ["catalyst"], "needs": [], "domains": ["gaming"],
                "waiting_for_text": "",
            }

            import step_a_cluster, golden_pattern
            from step_a_cluster import StepAResult
            mock_step_a = StepAResult.__new__(StepAResult)
            mock_step_a.signal_groups = [[signal_dict]]
            mock_step_a.isolated_signals = []
            mock_step_a.role_annotations = {}
            mock_step_a.fallback_used = False

            with patch.object(step_a_cluster, "run_step_a", return_value=mock_step_a):
                with patch.object(golden_pattern, "maybe_write_golden_pattern"):
                    store = SignalStore()
                    req = OpportunityJudgmentRequest(decoded_intelligences=[])
                    req._override_signals = [signal_dict]

                    engine.judge_with_signal_store(req, signal_store=store)

        self.assertEqual(store.stats().get("by_status", {}).get("contributed", 0), 0,
                         "未产出机会时不应有 contributed 信号")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.2 Signal Store 单元测试")
    print("=" * 60)
    unittest.main(verbosity=2)
