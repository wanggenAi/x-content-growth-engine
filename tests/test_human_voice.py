import json
import unittest
from pathlib import Path

from growth_engine.ai_flavor_gate import analyze_ai_flavor
from growth_engine.editorial_gate import validate_candidate
from growth_engine.fact_preservation import HOLD_FACT_DRIFT, check_fact_preservation
from growth_engine.human_voice import humanize_text, run_human_voice_pipeline
from growth_engine.x_native_style import review_comment_impulse, review_x_native_style


class AIFlavorGateTests(unittest.TestCase):
    def test_structural_templates_are_reported(self):
        report = analyze_ai_flavor(
            "不是价格的问题，而是边界的问题。真正的问题是大家都忽略了尊严。\n"
            "更值得关注的是选择权。换句话说，这背后反映的是价值。"
        )
        self.assertTrue({"balanced_contrast", "abstract_conclusion"}.issubset(report.matched_patterns))
        self.assertGreaterEqual(report.score, 25)

    def test_rhetorical_question_and_fact_to_value_chain_block(self):
        report = analyze_ai_flavor("工牌只记8小时，凭什么让人相信它公平？")
        self.assertTrue(report.blocked)
        self.assertIn("fact_to_value_question", report.matched_patterns)
        self.assertEqual(report.sentence_stats["question_count"], 1)

    def test_uniform_explanation_and_forced_humanization_are_signals(self):
        report = analyze_ai_flavor(
            "因为大家都很在意，所以这说明问题很复杂。\n"
            "因为规则需要调整，所以这意味着边界需要重建。\n"
            "因为讨论还在继续，所以这说明答案并不简单。\n"
            "因为每个人都有选择，所以这意味着价值需要平衡。"
        )
        self.assertIn("uniform_sentence_length", report.matched_patterns)
        forced = analyze_ai_flavor("卧槽兄弟们哈哈哈，这也太离谱了吧！！！")
        self.assertTrue(forced.blocked)
        self.assertIn("forced_humanization", forced.matched_patterns)

    def test_natural_short_text_and_direct_quote_are_not_penalized(self):
        self.assertFalse(analyze_ai_flavor("给别人送蛋糕的骑手，多要了一盒蜡烛。").blocked)
        report = analyze_ai_flavor("他说：“一会儿回去我就把蜡烛插在我的面条上。”")
        self.assertFalse(report.blocked)


class FactPreservationTests(unittest.TestCase):
    def setUp(self):
        self.before = "临沂一位69岁的环卫工说：凌晨5点开始扫地，6点才能打卡。"
        self.locks = {"people": ["69岁"], "times": ["凌晨5点", "6点"]}

    def test_number_name_date_and_quote_changes_hold(self):
        for after in (
            "临沂一位70岁的环卫工说：凌晨5点开始扫地，6点才能打卡。",
            "临沂一位69岁的环卫工说：凌晨6点开始扫地，6点才能打卡。",
            "临沂一位69岁的环卫工说：凌晨5点开始扫地，6点才能打卡。因此考勤制度证明了它是公平的。",
        ):
            report = check_fact_preservation(self.before, after, self.locks)
            self.assertEqual(report["status"], HOLD_FACT_DRIFT)

    def test_safe_synonym_rewrite_passes(self):
        after = "临沂一位69岁的环卫工说：凌晨5点已经扫地，6点才可以打卡。"
        report = check_fact_preservation(self.before, after, self.locks)
        self.assertTrue(report["passed"], report)

    def test_date_and_direct_quote_changes_hold(self):
        before = "2026年2月，他说：“我凌晨5点开始扫地。”"
        locks = {"date": "2026年2月", "quote": "“我凌晨5点开始扫地。”"}
        changed_date = check_fact_preservation(before, "2026年3月，他说：“我凌晨5点开始扫地。”", locks)
        changed_quote = check_fact_preservation(before, "2026年2月，他说：“我凌晨6点开始扫地。”", locks)
        self.assertEqual(changed_date["status"], HOLD_FACT_DRIFT)
        self.assertEqual(changed_quote["status"], HOLD_FACT_DRIFT)


class XNativeAndCommentTests(unittest.TestCase):
    def test_mini_essay_and_conclusion_fail(self):
        essay = "事实发生了。公平是社会的重要价值。我们应该关注边界。值得我们思考。"
        self.assertFalse(review_x_native_style(essay)["passed"])
        self.assertFalse(review_x_native_style("所以这才是我们真正应该思考的问题。\n")["passed"])

    def test_scene_and_natural_pause_pass(self):
        text = "给别人送蛋糕的骑手，找老板多要了一盒蜡烛。\n\n‘一会儿回去我就把蜡烛插在我的面条上。’"
        self.assertTrue(review_x_native_style(text)["passed"])

    def test_comment_impulse_distinguishes_consensus_and_tradeoff(self):
        consensus = "人干了快10小时，工牌只记8小时。凭什么让人相信它公平？"
        self.assertFalse(review_comment_impulse(consensus, "REPLY")["passed"])
        dilemma = "公司临时让大家住学校宿舍救急。学生不同意，但游客也确实没地方住。"
        result = review_comment_impulse(dilemma, "REPLY")
        self.assertTrue(result["real_tradeoff"])
        self.assertTrue(result["passed"])
        self.assertFalse(review_comment_impulse("你怎么看？", "REPLY")["passed"])
        self.assertTrue(review_comment_impulse("一个骑手快过生日了，只想要一盒蜡烛。", "SHARE")["passed"])


class HumanVoicePipelineTests(unittest.TestCase):
    def test_pipeline_preserves_quote_and_returns_contract(self):
        request = {
            "draft_text": "更值得关注的是：他说‘一会儿回去我就把蜡烛插在我的面条上。’",
            "locked_facts": {"quote": "‘一会儿回去我就把蜡烛插在我的面条上。’"},
            "primary_action": "SHARE",
        }
        result = run_human_voice_pipeline(request)
        self.assertEqual(result["human_voice"]["version"], "HUMAN_STYLE_V2")
        self.assertEqual(result["human_voice"]["fact_preservation"], "PASS")
        self.assertEqual(result["human_voice"]["comment_impulse"], "NOT_APPLICABLE")
        self.assertIn("一会儿回去我就把蜡烛插在我的面条上", result["rewritten_text"])

    def test_ready_requires_contract_but_legacy_published_is_readable(self):
        candidate = {
            "candidate_id": "C-test", "research_version": "r", "publication_version": "p",
            "subject_value": "具体损失", "payload": "一个数字", "primary_action": "SHARE",
            "novelty_check": "checked", "audit_language_separation": "kept", "material_strength": "STRONG",
            "source_refs": ["https://example.com/source"], "fact_check_status": "SOURCE_CHECKED",
            "human_checked": True, "state": "READY_FOR_MANUAL_PUBLISH",
            "reader_model": {"model_version": "READER_MODEL_V2", "material_strength": "HIGH", "novelty_status": "CHECKED",
                             "subject_value": "x", "information_gap": "x", "reader_self_insertion": "x",
                             "primary_action": "SHARE", "follow_reason": "x", "evidence_refs": ["x"]},
        }
        self.assertFalse(validate_candidate(candidate).ready)
        legacy = json.loads(Path("data/editorial_candidate_c355_2026-10-07.json").read_text())
        self.assertTrue(validate_candidate(legacy).ready)

    def test_historical_replay_contract(self):
        for cid in ("c387", "c388", "c389"):
            path = next(Path("data").glob(f"editorial_candidate_{cid}_*.json"))
            candidate = json.loads(path.read_text())
            result = run_human_voice_pipeline({
                "draft_text": candidate["text"],
                "locked_facts": {"urls": [value for value in candidate["source_refs"]
                                            if isinstance(value, str) and value.startswith("http")]},
                "primary_action": candidate["primary_action"],
            })
            self.assertEqual(result["fact_preservation_report"]["status"], "PASS")
            if cid == "c387":
                self.assertFalse(review_x_native_style(candidate["text"])["passed"])
                self.assertIn("removed_author_verdict_or_mechanical_question", result["changes"])
                self.assertEqual(result["x_native_style_report"]["status"], "PASS")
            elif cid == "c388":
                self.assertTrue(result["ai_flavor_report_before"]["blocked"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["comment_impulse_report"]["status"], "FAIL")
            else:
                self.assertFalse(result["ai_flavor_report"]["blocked"])
                self.assertEqual(result["x_native_style_report"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
