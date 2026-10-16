import json
import unittest
from pathlib import Path

from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.editorial_gate import validate_candidate
from growth_engine.fact_preservation import HOLD_FACT_DRIFT, check_fact_preservation
from growth_engine.human_voice import HUMAN_STYLE_VERSION, stable_hash
from growth_engine.human_voice import run_human_style_pipeline
from growth_engine.x_native_style import review_comment_impulse, review_x_native_style
from growth_engine.publication_preflight import pre_publish_assert
from tests.topic_helpers import bind_candidate


def candidate(text="朋友给我发来一张500元账单。", action="SHARE"):
    return bind_candidate({
        "candidate_id": "B-PIPELINE", "research_version": "research-v1",
        "publication_version": "public-v1", "subject_value": "具体账单冲突",
        "information_gap": "谁承担这笔钱", "payload": "500元账单",
        "primary_action": action, "primary_action_reader": "有过聚餐分账的人",
        "novelty_check": "未见重复", "audit_language_separation": "事实与观点分开",
        "follow_reason": "后续观察关系边界", "material_strength": "STRONG",
        "source_refs": ["https://example.com/source"],
        "fact_check_status": "SOURCE_CHECKED", "human_checked": True,
        "state": "DRAFT",
        "text": text, "locked_facts": {"amount": "500元"},
    })


class HumanStyleProductionTests(unittest.TestCase):
    def test_candidate_entry_runs_pipeline_and_emits_hash_bound_v2(self):
        prepared = prepare_candidate(candidate())
        self.assertEqual(prepared["state"], "READY_FOR_MANUAL_PUBLISH")
        contract = prepared["human_style"]
        self.assertEqual(contract["version"], HUMAN_STYLE_VERSION)
        self.assertEqual(contract["output_text_hash"], stable_hash(prepared["text"]))
        self.assertTrue(prepared["editorial_gate"]["ready"])

    def test_authorized_agent_review_waiver_keeps_human_checked_false(self):
        item = candidate()
        item["human_checked"] = False
        item["agent_checked"] = True
        item["user_authorized"] = True
        item["publication_review_exception"] = "USER_AUTHORIZED_AGENT_REVIEW"
        prepared = prepare_candidate(item)
        self.assertEqual(prepared["state"], "READY_FOR_MANUAL_PUBLISH")
        self.assertIs(prepared["human_checked"], False)

    def test_pre_publish_assert_binds_exact_text_and_hash(self):
        prepared = prepare_candidate(candidate())
        result = pre_publish_assert(prepared, prepared["text"], dry_run=True)
        self.assertTrue(result["passed"])
        with self.assertRaises(ValueError):
            pre_publish_assert(prepared, prepared["text"] + " 改过了")

    def test_editing_text_invalidates_previous_contract(self):
        prepared = prepare_candidate(candidate())
        prepared["text"] += " 后来他又补了一句。"
        result = validate_candidate(prepared)
        self.assertFalse(result.ready)
        self.assertTrue(any("output_text_hash" in reason for reason in result.reasons))

    def test_forged_pass_contract_is_recomputed_and_rejected(self):
        prepared = prepare_candidate(candidate())
        prepared["human_style"]["ai_flavor_score_after"] = 99
        result = validate_candidate(prepared)
        self.assertFalse(result.ready)
        self.assertTrue(any("AI flavor" in reason or "deterministic engine output" in reason for reason in result.reasons))

    def test_fact_drift_is_hold(self):
        report = check_fact_preservation("朋友给我发来一张500元账单。", "朋友给我发来一张800元账单。", {"amount": "500元"})
        self.assertEqual(report["status"], HOLD_FACT_DRIFT)

    def test_ai_micro_essay_does_not_reach_ready(self):
        prepared = prepare_candidate(candidate(
            "事实发生了。公平是社会的重要价值。我们应该关注边界。值得我们思考。",
            "REPLY",
        ))
        self.assertNotEqual(prepared["state"], "READY_FOR_MANUAL_PUBLISH")

    def test_fake_reply_does_not_reach_ready(self):
        prepared = prepare_candidate(candidate(
            "老板少发了员工三个月工资。你觉得合理吗？",
            "REPLY",
        ))
        self.assertNotEqual(prepared["state"], "READY_FOR_MANUAL_PUBLISH")

    def test_fake_reply_and_real_branch(self):
        fake = review_comment_impulse("老板少发了员工三个月工资。你觉得合理吗？", "REPLY")
        self.assertFalse(fake["passed"])
        real = review_comment_impulse("同事每个月工资比我高5000。我们做一样的工作。他入职比我早两年。", "REPLY")
        self.assertTrue(real["passed"], real)
        self.assertGreaterEqual(len(real["possible_reply_branches"]), 2)

    def test_scene_is_structural_without_historical_words(self):
        text = "谈恋爱三年，男朋友一次都没发过她的照片。他的爸妈和朋友都知道她。"
        native = review_x_native_style(text, "REPLY")
        self.assertTrue(native["passed"], native)
        self.assertTrue(review_comment_impulse(text, "REPLY")["passed"])

    def test_synthetic_blind_fixtures_cannot_enter_production(self):
        fixture = json.loads(Path("data/human_style_blindset_v1.json").read_text())[0]
        with self.assertRaises(ValueError):
            prepare_candidate(fixture)

    def test_blindset_has_required_balance_and_is_audit_only(self):
        fixtures = json.loads(Path("data/human_style_blindset_v1.json").read_text())
        self.assertGreaterEqual(len(fixtures), 30)
        labels = [item["expected"]["decision"] for item in fixtures]
        self.assertGreaterEqual(labels.count("SHOULD_PASS_REWRITE"), 10)
        self.assertGreaterEqual(labels.count("SHOULD_PASS_AS_IS"), 8)
        self.assertGreaterEqual(labels.count("SHOULD_FAIL_AI_STYLE"), 6)
        self.assertGreaterEqual(labels.count("SHOULD_FAIL_COMMENT_IMPULSE"), 6)
        self.assertTrue(all(item["fixture_type"] == "SYNTHETIC_TEST_FIXTURE" for item in fixtures))

    def test_blindset_replay_reports_expected_pass_fail(self):
        fixtures = json.loads(Path("data/human_style_blindset_v1.json").read_text())
        expected_pass = sum(item["expected"]["decision"] in {"SHOULD_PASS_REWRITE", "SHOULD_PASS_AS_IS"} for item in fixtures)
        actual_pass = 0
        mismatches = []
        for item in fixtures:
            report = run_human_style_pipeline({
                "draft_text": item["draft"],
                "locked_facts": {},
                "primary_action": item.get("primary_action", "REPLY"),
            })
            passed = bool(report["passed"])
            actual_pass += passed
            expected = item["expected"]["decision"] in {"SHOULD_PASS_REWRITE", "SHOULD_PASS_AS_IS"}
            if passed != expected:
                mismatches.append(item["id"])
        self.assertEqual((len(fixtures), expected_pass, actual_pass, mismatches), (32, 20, 20, []))


if __name__ == "__main__":
    unittest.main()
