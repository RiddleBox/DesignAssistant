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
            self_store._emerging_links = {}
            self_store._scenario_memories = {}
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
        L1 命中到历史伙伴，但若只是补到部分结构、尚未形成机会，则应保留为 store-for-later。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        nacon = self._make_nacon_entry()
        store.add(nacon)

        new_signal = self._make_new_signal()

        mock_l4.return_value = [[nacon]]

        result = run_step_b(
            isolated_signal=new_signal,
            signal_store=store,
            llm_client=MagicMock(),
            model="mock",
        )

        self.assertFalse(result.matched,
                         "未形成机会闭环时不应返回 matched=True")
        self.assertEqual(len(result.candidate_groups), 0,
                         "只有 Step-C-ready 候选才应进入 candidate_groups")
        self.assertGreaterEqual(len(result.store_candidate_groups), 1,
                                "应保留 store-for-later 候选供后续成长")
        latent_ids = [e.signal_id for g in result.store_candidate_groups for e in g]
        self.assertIn(nacon.signal_id, latent_ids,
                      "历史信号应出现在 store_candidate_groups 中")

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
        L4 返回空 → fallback_used=True，把 Step-C-ready 候选作为结果返回
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        nacon = self._make_nacon_entry()
        helper = build_signal_entry(
            signal=_make_signal("helper_001", "market", "历史需求信号"),
            roles=["demand_evidence"],
            needs=["resource_validation"],
            domains=["gaming"],
            waiting_for_text="等待资源验证",
            batch_date="2026-03-31",
        )
        helper.status = "pending"
        store.add(nacon)
        store.add(helper)

        store.save_scenario_memories([
            {
                "scenario_id": "scenario_fallback_1",
                "anchor_signal_ids": [nacon.original_signal_id],
                "member_signal_ids": [nacon.original_signal_id, helper.original_signal_id],
                "covered_roles": ["catalyst", "demand_evidence"],
                "missing_slots": ["execution_risk"],
                "shared_affects": ["gaming"],
                "state": "developing",
                "promotion_score": 0.8,
                "option_value_score": 0.75,
                "novelty_score": 0.4,
                "gap_fill_value": 0.8,
                "cross_domain_bonus": 0.1,
                "reasoning_path": "已有催化剂和需求，等待执行风险补槽形成机会",
            }
        ], batch_date="2026-03-31")

        new_signal = self._make_new_signal()
        mock_l4.return_value = []  # L4 无法确认

        result = run_step_b(
            isolated_signal=new_signal,
            signal_store=store,
            llm_client=MagicMock(),
            model="mock",
        )

        self.assertTrue(result.fallback_used,
                        "L4 无确认时应使用 fallback")
        self.assertTrue(result.matched,
                        "存在 Step-C-ready 候选时 fallback 路径 matched 应为 True")
        self.assertGreaterEqual(len(result.ready_candidate_groups), 1)

    def test_step_b_prefers_scenario_memory_over_raw_signal(self):
        """
        若同时命中 ScenarioMemory 与普通历史信号，应优先保留 ScenarioMemory 产物，
        但只有形成机会时才 matched=True。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        raw_partner = self._make_nacon_entry()
        store.add(raw_partner)

        helper = build_signal_entry(
            signal=_make_signal("helper_001", "market", "用户需求升温"),
            roles=["demand_evidence"],
            needs=["resource_validation"],
            domains=["gaming"],
            waiting_for_text="等待资源验证",
            batch_date="2026-03-31",
        )
        helper.status = "pending"
        store.add(helper)

        store.save_scenario_memories([
            {
                "scenario_id": "scenario_test_1",
                "anchor_signal_ids": [raw_partner.original_signal_id],
                "member_signal_ids": [raw_partner.original_signal_id, helper.original_signal_id],
                "covered_roles": ["catalyst", "demand_evidence"],
                "missing_slots": ["execution_risk"],
                "shared_affects": ["gaming"],
                "state": "developing",
                "promotion_score": 0.66,
                "option_value_score": 0.78,
                "novelty_score": 0.4,
                "gap_fill_value": 0.67,
                "cross_domain_bonus": 0.1,
                "reasoning_path": "已有催化剂与需求证据，等待执行风险补槽",
            }
        ], batch_date="2026-03-31")

        result = run_step_b(
            isolated_signal=self._make_new_signal(),
            signal_store=store,
            llm_client=None,
            model="mock",
        )

        self.assertFalse(result.matched)
        self.assertGreater(len(result.matched_scenarios), 0,
                           "应优先命中 ScenarioMemory")
        self.assertEqual(result.matched_scenarios[0].scenario_id, "scenario_test_1")
        self.assertGreaterEqual(len(result.store_candidate_groups[0]), 2,
                                "优先返回的场景候选应展开为场景中的历史信号集合")

    def test_step_b_exposes_step_c_ready_and_store_for_later(self):
        """
        Step B 应显式暴露真正进入 Step C 的候选，以及只保留待后续成长的候选。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()

        strong_partner = self._make_nacon_entry()
        store.add(strong_partner)

        demand_partner = build_signal_entry(
            signal=_make_signal("demand_001", "market", "需求已经出现"),
            roles=["demand_evidence"],
            needs=["resource_validation"],
            domains=["gaming"],
            waiting_for_text="等待资源验证",
            batch_date="2026-03-31",
        )
        demand_partner.status = "pending"
        store.add(demand_partner)

        weak_partner = build_signal_entry(
            signal=_make_signal("weak_001", "market", "外围社区关注"),
            roles=["timing_signal"],
            needs=["execution_risk"],
            domains=["gaming"],
            waiting_for_text="等待催化剂或风险信号",
            batch_date="2026-03-31",
        )
        weak_partner.status = "pending"
        weak_partner.intensity_score = 5
        store.add(weak_partner)

        store.save_scenario_memories([
            {
                "scenario_id": "scenario_route_test",
                "anchor_signal_ids": [strong_partner.original_signal_id],
                "member_signal_ids": [strong_partner.original_signal_id, demand_partner.original_signal_id],
                "covered_roles": ["catalyst", "demand_evidence"],
                "missing_slots": ["execution_risk"],
                "shared_affects": ["gaming"],
                "state": "developing",
                "promotion_score": 0.8,
                "option_value_score": 0.72,
                "novelty_score": 0.4,
                "gap_fill_value": 0.8,
                "cross_domain_bonus": 0.1,
                "reasoning_path": "已有催化剂和需求，当前执行风险可把逻辑补成机会",
            }
        ], batch_date="2026-03-31")

        result = run_step_b(
            isolated_signal=self._make_new_signal(),
            signal_store=store,
            llm_client=None,
            model="mock",
        )

        self.assertTrue(result.matched)
        self.assertGreater(len(result.candidate_group_infos), 0,
                           "应暴露 candidate_group_infos 供上层查看上送结果")
        self.assertGreaterEqual(len(result.ready_candidate_groups), 1,
                                "应暴露 ready_candidate_groups")
        self.assertGreaterEqual(len(result.store_candidate_groups), 1,
                                "应暴露 store_candidate_groups")
        routes = {info.route for info in result.candidate_group_infos + result.latent_candidate_group_infos}
        self.assertIn("step_c_ready", routes)
        self.assertIn("store_for_later", routes)

    def test_single_signal_pair_should_not_auto_escalate_to_step_c(self):
        """
        单条历史 signal 即使很强，只要还只是补到最小关系、不足以形成机会，也不应直接进入 Step C。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        demand_only = build_signal_entry(
            signal=_make_signal("hist_sig_only_001", "market", "强需求信号"),
            roles=["demand_evidence"],
            needs=["catalyst"],
            domains=["gaming"],
            waiting_for_text="等待催化剂",
            batch_date="2026-03-31",
        )
        demand_only.status = "pending"
        demand_only.intensity_score = 9
        store.add(demand_only)

        isolated = _make_signal("iso_sig_only_001", "regulatory", "新催化剂")
        isolated["_role_annotation"] = {
            "roles": ["catalyst"],
            "needs": ["demand_evidence"],
            "domains": ["gaming"],
            "waiting_for_text": "等待需求信号",
        }

        result = run_step_b(
            isolated_signal=isolated,
            signal_store=store,
            llm_client=None,
            model="mock",
        )

        self.assertFalse(result.matched,
                         "仅形成 signal pair 时不应自动视为已成机会")
        self.assertEqual(len(result.ready_candidate_groups), 0)
        self.assertGreaterEqual(len(result.store_candidate_groups), 1)
        self.assertEqual(result.latent_candidate_group_infos[0].source_kind, "signal_entry")
        self.assertEqual(result.latent_candidate_group_infos[0].route, "store_for_later")

    def test_emerging_link_should_not_auto_escalate_without_opportunity_loop(self):
        """
        emerging_link 形成关系本身不等于机会；没有补成机会闭环时只能保留待后续成长。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()

        hist_market = build_signal_entry(
            signal=_make_signal("hist_link_market_001", "market", "需求信号"),
            roles=["demand_evidence"],
            needs=["resource_validation"],
            domains=["gaming", "ai"],
            waiting_for_text="等待资源验证",
            batch_date="2026-03-31",
        )
        hist_team = build_signal_entry(
            signal=_make_signal("hist_link_team_001", "team", "团队准备"),
            roles=["timing_signal"],
            needs=["demand_evidence"],
            domains=["ai"],
            waiting_for_text="等待更明确需求",
            batch_date="2026-03-31",
        )
        hist_market.status = "pending"
        hist_team.status = "pending"
        store.add_batch([hist_market, hist_team])

        store.save_emerging_links([
            {
                "link_id": "link_boundary_001",
                "signal_ids": [hist_market.original_signal_id, hist_team.original_signal_id],
                "edge_type": "complementary",
                "strength_band": "emerging",
                "gate_passed": True,
                "final_score": 0.58,
                "reasoning": "关系存在但未闭环",
                "shared_affects": ["ai workflow"],
            }
        ], batch_date="2026-03-31")

        isolated = _make_signal("iso_link_boundary_001", "technical", "部署摩擦上升")
        isolated["_role_annotation"] = {
            "roles": ["execution_risk"],
            "needs": ["demand_evidence"],
            "domains": ["gaming", "ai"],
            "waiting_for_text": "等待商业意义更明确的配对",
        }

        result = run_step_b(
            isolated_signal=isolated,
            signal_store=store,
            llm_client=None,
            model="mock",
        )

        self.assertFalse(result.matched)
        self.assertEqual(len(result.ready_candidate_groups), 0)
        self.assertGreaterEqual(len(result.store_candidate_groups), 1)
        latent = result.latent_candidate_group_infos[0]
        self.assertEqual(latent.source_kind, "emerging_link")
        self.assertEqual(latent.route, "store_for_later")

    def test_scenario_memory_can_escalate_when_core_loop_is_closed(self):
        """
        只有当 scenario memory 被补成最小机会闭环时，才应该真正进入 Step C。
        """
        from step_b_retrieval import run_step_b

        store = SignalStore()
        catalyst = self._make_nacon_entry()
        demand = build_signal_entry(
            signal=_make_signal("hist_scn_demand_001", "market", "需求明确出现"),
            roles=["demand_evidence"],
            needs=["resource_validation"],
            domains=["gaming"],
            waiting_for_text="等待资源验证",
            batch_date="2026-03-31",
        )
        catalyst.status = "pending"
        demand.status = "pending"
        store.add_batch([catalyst, demand])

        store.save_scenario_memories([
            {
                "scenario_id": "scenario_closed_loop_001",
                "anchor_signal_ids": [catalyst.original_signal_id],
                "member_signal_ids": [catalyst.original_signal_id, demand.original_signal_id],
                "covered_roles": ["catalyst", "demand_evidence"],
                "missing_slots": ["execution_risk"],
                "shared_affects": ["gaming"],
                "state": "developing",
                "promotion_score": 0.82,
                "option_value_score": 0.76,
                "novelty_score": 0.5,
                "gap_fill_value": 0.82,
                "cross_domain_bonus": 0.1,
                "reasoning_path": "催化剂和需求已具备，只等执行风险补槽形成最小机会逻辑",
            }
        ], batch_date="2026-03-31")

        result = run_step_b(
            isolated_signal=self._make_new_signal(),
            signal_store=store,
            llm_client=None,
            model="mock",
        )

        self.assertTrue(result.matched)
        self.assertGreaterEqual(len(result.ready_candidate_groups), 1)
        self.assertEqual(result.candidate_group_infos[0].source_kind, "scenario_memory")
        self.assertEqual(result.candidate_group_infos[0].route, "step_c_ready")


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

    def test_step_b_exploration_route_hint_reaches_step_c(self):
        """
        Step B v1.2：探索通道候选进入 Step C 时，应把 route-aware hint 注入子请求。
        """
        from judgment_engine import JudgmentEngine
        from schemas import OpportunityJudgmentRequest, OpportunityJudgmentResult
        from step_b_retrieval import StepBResult, CandidateGroupInfo
        from step_a_cluster import StepAResult

        iso_signal = _make_signal("iso_001", "capital", "孤立信号")
        iso_signal["_role_annotation"] = {
            "roles": ["execution_risk"],
            "needs": ["catalyst"],
            "domains": ["gaming"],
            "waiting_for_text": "等待催化剂",
        }
        partner = _make_entry("hist_001", "market", "历史伙伴")

        candidate_info = CandidateGroupInfo(
            group_id="scenario::explore_1",
            entries=[partner],
            source_kind="scenario_memory",
            rank_score=0.64,
            route="store_for_later",
            route_reason="retain high option value scenario",
            slot_fill_count=1,
            core_role_coverage=2,
        )
        step_b_result = StepBResult(
            candidate_groups=[[partner]],
            current_signal_id="iso_001",
            matched=True,
            fallback_used=True,
            candidate_group_infos=[candidate_info],
        )

        mock_step_a = StepAResult.__new__(StepAResult)
        mock_step_a.signal_groups = []
        mock_step_a.isolated_signals = [iso_signal]
        mock_step_a.role_annotations = {}
        mock_step_a.fallback_used = False
        mock_step_a.logical_scenarios = []
        mock_step_a.exploration_scenarios = []
        mock_step_a.emerging_links = []
        mock_step_a.scenario_candidates = []

        captured_hints = []

        def fake_judge(self_engine, request_obj):
            captured_hints.extend(getattr(request_obj, "_scenario_hints", []) or [])
            return OpportunityJudgmentResult(
                opportunities=[],
                status="insufficient_evidence",
                diagnostics=None,
            )

        large_batch_signals = [iso_signal] + [
            _make_signal(f"pad_{i:03d}", "capital", f"填充信号{i:03d}")
            for i in range(15)
        ]

        import step_a_cluster, step_b_retrieval, golden_pattern
        with patch.object(step_a_cluster, "run_step_a", return_value=mock_step_a):
            with patch.object(step_b_retrieval, "run_step_b", return_value=step_b_result):
                with patch.object(JudgmentEngine, "judge", fake_judge):
                    with patch.object(JudgmentEngine, "_extract_enriched_signals", return_value=large_batch_signals):
                        engine = JudgmentEngine(api_key="")
                        store = SignalStore()
                        req = OpportunityJudgmentRequest(decoded_intelligences=[])
                        result = engine.judge_with_signal_store(req, signal_store=store)

        self.assertEqual(len(captured_hints), 1)
        self.assertIn("scenario::explore_1", captured_hints[0])
        self.assertIn("store_for_later", captured_hints[0])
        self.assertIn("排序分=0.64", captured_hints[0])

    def test_step_b_diagnostics_exposes_summary_and_trace(self):
        """
        Step B v1.3：最终 diagnostics 应暴露 step_b_summary 和 step_b_trace，
        便于评估主/探索通道的真实收益。
        """
        from judgment_engine import JudgmentEngine
        from schemas import OpportunityJudgmentRequest, OpportunityJudgmentResult
        from step_b_retrieval import StepBResult, CandidateGroupInfo
        from step_a_cluster import StepAResult

        iso_signal = _make_signal("iso_diag_001", "capital", "诊断孤立信号")
        iso_signal["_role_annotation"] = {
            "roles": ["execution_risk"],
            "needs": ["catalyst"],
            "domains": ["gaming"],
            "waiting_for_text": "等待催化剂",
        }
        primary_partner = _make_entry("hist_diag_001", "market", "主通道伙伴")
        exploration_partner = _make_entry("hist_diag_002", "team", "探索通道伙伴")

        primary_info = CandidateGroupInfo(
            group_id="scenario::diag_primary",
            entries=[primary_partner],
            source_kind="scenario_memory",
            rank_score=0.81,
            route="step_c_ready",
            route_reason="fills scenario missing slot",
            slot_fill_count=1,
            core_role_coverage=2,
        )
        exploration_info = CandidateGroupInfo(
            group_id="link::diag_explore",
            entries=[exploration_partner],
            source_kind="emerging_link",
            rank_score=0.58,
            route="store_for_later",
            route_reason="retain promising emerging relation",
            slot_fill_count=0,
            core_role_coverage=1,
        )
        step_b_result = StepBResult(
            candidate_groups=[[primary_partner]],
            current_signal_id="iso_diag_001",
            matched=True,
            fallback_used=True,
            candidate_group_infos=[primary_info],
            latent_candidate_group_infos=[exploration_info],
        )

        mock_step_a = StepAResult.__new__(StepAResult)
        mock_step_a.signal_groups = []
        mock_step_a.isolated_signals = [iso_signal]
        mock_step_a.role_annotations = {}
        mock_step_a.fallback_used = False
        mock_step_a.logical_scenarios = []
        mock_step_a.exploration_scenarios = []
        mock_step_a.emerging_links = []
        mock_step_a.scenario_candidates = []

        def fake_judge(self_engine, request_obj):
            hints = getattr(request_obj, "_scenario_hints", []) or []
            if hints and "diag_primary" in hints[0]:
                opp = self._make_mock_opportunity()
                opp.opportunity_id = "opp_diag_001"
                opp.opportunity_title = "主通道机会"
                return OpportunityJudgmentResult(
                    opportunities=[opp],
                    status="success",
                    diagnostics=None,
                )
            return OpportunityJudgmentResult(
                opportunities=[],
                status="insufficient_evidence",
                diagnostics=None,
            )

        large_batch_signals = [iso_signal] + [
            _make_signal(f"diag_pad_{i:03d}", "capital", f"诊断填充信号{i:03d}")
            for i in range(15)
        ]

        import step_a_cluster, step_b_retrieval
        with patch.object(step_a_cluster, "run_step_a", return_value=mock_step_a):
            with patch.object(step_b_retrieval, "run_step_b", return_value=step_b_result):
                with patch.object(JudgmentEngine, "judge", fake_judge):
                    with patch.object(JudgmentEngine, "_extract_enriched_signals", return_value=large_batch_signals):
                        engine = JudgmentEngine(api_key="")
                        store = SignalStore()
                        req = OpportunityJudgmentRequest(decoded_intelligences=[])
                        result = engine.judge_with_signal_store(req, signal_store=store)

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.diagnostics)
        self.assertIsNotNone(result.diagnostics.step_b_summary)
        self.assertIsNotNone(result.diagnostics.step_b_trace)
        self.assertEqual(result.diagnostics.step_b_summary["matched_signal_count"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["step_c_ready_group_count"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["store_for_later_group_count"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["step_c_attempt_count"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["step_c_success_count"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["route_success_counts"]["step_c_ready"], 1)
        self.assertEqual(result.diagnostics.step_b_summary["route_success_counts"]["store_for_later"], 0)
        self.assertEqual(len(result.diagnostics.step_b_trace), 1)
        trace = result.diagnostics.step_b_trace[0]
        self.assertTrue(trace["matched"])
        self.assertTrue(trace["produced_opportunity"])
        self.assertEqual(trace["candidate_count"], 1)
        self.assertEqual(len(trace["candidate_attempts"]), 1)
        self.assertEqual(trace["candidate_attempts"][0]["group_id"], "scenario::diag_primary")
        self.assertEqual(trace["candidate_attempts"][0]["opportunity_count"], 1)


class TestStepBIdealizedEvalRunner(unittest.TestCase):
    def test_step_b_idealized_eval_runner_case_passes(self):
        from run_step_b_idealized_eval import StepBIdealizedEvalRunner

        runner = StepBIdealizedEvalRunner(case_id="step_b_scenario_primary_001", json_output=True)
        result = runner._run_case(runner._get_target_cases()[0])

        self.assertTrue(result["validation"]["passed"])
        self.assertTrue(result["execution"]["matched"])
        self.assertGreaterEqual(result["execution"]["step_c_ready_group_count"], 1)
        self.assertEqual(result["execution"]["top_route"], "step_c_ready")
        self.assertEqual(result["execution"]["top_source_kind"], "scenario_memory")
        self.assertIsNotNone(result["execution"]["top_rank_score"])
        self.assertIsNotNone(result["execution"]["step_c_ready_avg_rank_score"])
        self.assertGreaterEqual(result["execution"]["store_for_later_group_count"], 1)

    def test_step_b_idealized_eval_runner_store_for_later_case(self):
        from run_step_b_idealized_eval import StepBIdealizedEvalRunner

        runner = StepBIdealizedEvalRunner(case_id="step_b_signal_store_for_later_001", json_output=True)
        result = runner._run_case(runner._get_target_cases()[0])

        self.assertTrue(result["validation"]["passed"])
        self.assertFalse(result["execution"]["matched"])
        self.assertEqual(result["execution"]["step_c_ready_group_count"], 0)
        self.assertGreaterEqual(result["execution"]["store_for_later_group_count"], 1)
        self.assertEqual(result["execution"]["top_route"], "store_for_later")

    def test_step_b_idealized_eval_runner_json_report_has_diff_friendly_metrics(self):
        from run_step_b_idealized_eval import StepBIdealizedEvalRunner

        runner = StepBIdealizedEvalRunner(json_output=True)
        runner.results = [runner._run_case(case) for case in runner._get_target_cases()]
        report = runner._build_json_report()
        aggregate = report["aggregate"]

        self.assertIn("top1_route_counts", aggregate)
        self.assertIn("top1_source_kind_counts", aggregate)
        self.assertIn("top1_rank_score_avg", aggregate)
        self.assertIn("candidate_rank_score_avg", aggregate)
        self.assertIn("case_overview", aggregate)
        self.assertIn("generated_at", report)
        self.assertEqual(report["case_scope"], "all_cases")
        self.assertEqual(len(aggregate["case_overview"]), len(runner.results))
        self.assertEqual(aggregate["top1_route_counts"]["step_c_ready"], 2)
        self.assertEqual(aggregate["top1_route_counts"]["store_for_later"], 2)
        self.assertEqual(aggregate["top1_route_counts"]["none"], 1)
        self.assertEqual(aggregate["top1_source_kind_counts"]["scenario_memory"], 2)
        self.assertEqual(aggregate["top1_source_kind_counts"]["emerging_link"], 1)
        self.assertEqual(aggregate["top1_source_kind_counts"]["signal_entry"], 1)
        self.assertEqual(aggregate["top1_source_kind_counts"]["none"], 1)

    def test_step_b_idealized_eval_runner_scenario_can_beat_strong_signal(self):
        from run_step_b_idealized_eval import StepBIdealizedEvalRunner

        runner = StepBIdealizedEvalRunner(case_id="step_b_scenario_beats_strong_signal_001", json_output=True)
        result = runner._run_case(runner._get_target_cases()[0])
        execution = result["execution"]

        self.assertTrue(result["validation"]["passed"])
        self.assertEqual(execution["top_route"], "step_c_ready")
        self.assertEqual(execution["top_source_kind"], "scenario_memory")
        self.assertTrue((execution["top_group_id"] or "").startswith("scenario::"))
        self.assertGreaterEqual(execution["step_c_ready_group_count"], 1)
        self.assertGreaterEqual(execution["matched_scenario_count"], 1)
        self.assertIn("signal_entry", {item["source_kind"] for item in execution["candidates"]})

    def test_step_b_idealized_eval_runner_can_save_report_snapshot(self):
        import json
        from run_step_b_idealized_eval import StepBIdealizedEvalRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = StepBIdealizedEvalRunner(json_output=True, save_report=True, report_dir=tmpdir)
            runner.results = [runner._run_case(case) for case in runner._get_target_cases()]
            report = runner._build_json_report()
            saved_path = runner._write_report(report)

            self.assertTrue(os.path.exists(saved_path))
            self.assertTrue(saved_path.endswith(".json"))

            with open(saved_path, "r", encoding="utf-8") as f:
                saved_report = json.load(f)

            self.assertIn("aggregate", saved_report)
            self.assertIn("generated_at", saved_report)
            self.assertEqual(saved_report["case_scope"], "all_cases")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.2 Signal Store 单元测试")
    print("=" * 60)
    unittest.main(verbosity=2)
