import json
import tempfile
import unittest
from pathlib import Path

from growth_engine.__main__ import connect
from growth_engine.editorial_gate import validate_candidate
from growth_engine.reader_model import (
    DIMENSIONS, backtest, empty_profile, import_annotations, profile_errors,
    ratios, reader_packet, review_profile, validate_comment, window_status,
)


def good_profile():
    p = empty_profile()
    p.update({key: "HIGH" for key in DIMENSIONS})
    p.update(concrete_stakes="time lost in an application", identity_trigger="applicants",
             why_reader_cares="Will my application fail too?", predicted_inner_response="Why did it fail?",
             share_recipient="a colleague applying", share_reason="avoid the same loss",
             opinion_space_reason="different experiences can explain the outcome",
             attention_mechanism="expected completion vs visible failure",
             psychological_accounts=[{"account": "CONTROL", "stake": "time", "cue": "submit failed",
                                      "reader_thought": "Can I fix it?"}],
             evidence_strength="FULL_RECORDED_TEXT", novelty_status="CHECKED",
             acceptable_editorial_mechanism="ACCEPTABLE_WITH_SOURCE_CHECK",
             rationale={key: "concrete evidence reviewed" for key in DIMENSIONS})
    return p


def annotation():
    return {"entity_id": "C-test", "entity_kind": "own", "version": 1,
            "annotated_at_utc": "2026-10-08T00:00:00Z", "annotator": "test",
            "source_digest": "test-digest", "annotation_note": "synthetic test only",
            "source_refs": ["synthetic"], "post_url": "https://x.com/example/status/123",
            "publication_text_digest": "test-body", "published_at_utc": "2026-10-01T00:00:00Z",
            "reader_model": good_profile()}


class ReaderModelTests(unittest.TestCase):
    def test_material_cannot_be_rescued_by_topic_strength(self):
        p = good_profile()
        p["material_strength"] = "LOW"
        result = review_profile(p)
        self.assertEqual(result["priority"], "LOWER_PRIORITY")
        self.assertIn("A_MATERIAL", result["reasons"])
        self.assertIsNone(result["score"])

    def test_unknown_summary_and_risky_attention_are_not_production_evidence(self):
        self.assertEqual(review_profile(empty_profile())["priority"], "HOLD_NEEDS_ANNOTATION")
        p = good_profile()
        p.update(evidence_strength="STRUCTURE_SUMMARY_ONLY", acceptable_editorial_mechanism="RESEARCH_ONLY")
        self.assertIn("NEEDS_FULL_MATERIAL", review_profile(p)["reasons"])
        self.assertIn("ATTENTION_NOT_EDITORIALLY_ACCEPTABLE", review_profile(p)["reasons"])
        p["claim_status"] = "VERIFIED_ON_OWN_ACCOUNT"
        self.assertTrue(profile_errors(p))

    def test_distance_is_not_a_monotonic_score(self):
        p = good_profile()
        p["self_relevance_distance"].update(occupation="FAR", bridge="investment or aspiration")
        self.assertEqual(review_profile(p)["priority"], "REVIEW_FIRST")

    def test_gate_blocks_missing_model_and_passive_inner_response(self):
        from growth_engine.editorial_gate import REQUIRED_FIELDS
        c = {key: "reviewed" for key in REQUIRED_FIELDS}
        c.update(source_refs=["source"], material_strength="STRONG", primary_action="REPLY",
                 human_checked=True, state="EDITORIAL_REVIEW", reader_model=good_profile())
        self.assertTrue(validate_candidate(c).ready)
        del c["reader_model"]
        self.assertFalse(validate_candidate(c).ready)
        c["reader_model"] = good_profile()
        c["reader_model"]["predicted_inner_response"] = "哦。"
        self.assertIn("PASSIVE_INNER_RESPONSE", validate_candidate(c).reasons)
        c["reader_model"] = good_profile()
        c["reader_model"]["opinion_activation"] = "LOW"
        self.assertFalse(validate_candidate(c).ready)
        c.update(state="RESEARCH_ONLY", reader_model=good_profile())
        self.assertFalse(validate_candidate(c).ready)

    def test_append_only_import_idempotence_conflict_and_atomicity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            db = connect(Path(directory) / "db.sqlite3")
            self.addCleanup(db.close)
            first = annotation()
            path.write_text(json.dumps([first]))
            self.assertEqual(import_annotations(db, path), 1)
            self.assertEqual(import_annotations(db, path), 0)
            new = {**first, "entity_id": "C-new"}
            conflict = {**first, "annotation_note": "changed without revision"}
            path.write_text(json.dumps([new, conflict]))
            with self.assertRaises(ValueError):
                import_annotations(db, path)
            self.assertEqual(len(reader_packet(db)), 1)
            revised = {**conflict, "version": 2}
            path.write_text(json.dumps([revised]))
            self.assertEqual(import_annotations(db, path), 1)
            self.assertEqual(reader_packet(db, "own")[0]["version"], 2)

    def test_rates_do_not_collapse_metrics_or_missing_denominators(self):
        self.assertEqual(ratios({"views": 10, "replies": 2, "likes": 0})["replies_per_views"], .2)
        self.assertEqual(ratios({"views": 10, "likes": 0})["likes_per_views"], 0)
        self.assertIsNone(ratios({"views": 0, "replies": 0})["replies_per_views"])
        self.assertIsNone(ratios({"views": 10})["replies_per_views"])
        self.assertIsNone(ratios({"views": 10, "replies": 2})["replies_per_impressions"])

    def test_past_due_is_missing_not_backfilled(self):
        self.assertEqual(window_status("2026-10-07T13:19:00Z", "2026-10-08T00:00:00Z", "1h"), "DUE_MISSING")
        self.assertEqual(window_status("2026-10-07T13:19:00Z", "2026-10-08T00:00:00Z", "24h"), "PENDING_WINDOW")

    def test_strict_backtest_requires_window_human_evidence_and_text_version(self):
        obs = {"entity_id": "C-test", "post_url": annotation()["post_url"], "views": 100,
               "replies": 0, "reposts": None, "human_reviewed": False,
               "published_at_utc": "2026-10-01T00:00:00Z", "observed_at_utc": "2026-10-02T00:00:00Z",
               "evidence_ref": "synthetic", "source_kind": "USER_NOTE", "window": "24h",
               "publication_text_digest": "test-body"}
        self.assertEqual(backtest([annotation()], [obs], window="24h")["n"], 0)
        obs["human_reviewed"] = True
        result = backtest([annotation()], [obs], window="24h")
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["rows"][0]["rates"]["replies_per_views"], 0)
        self.assertIsNone(result["rows"][0]["rates"]["reposts_per_views"])
        for change in [{"observed_at_utc": "2026-10-02T06:00:00Z"}, {"publication_text_digest": "old-version"},
                       {"source_kind": "SEARCH_INDEX"}, {"evidence_ref": None},
                       {"published_at_utc": "2026-10-01T03:00:00Z"},
                       {"post_url": "https://x.com/example/status/999"}]:
            self.assertEqual(backtest([annotation()], [{**obs, **change}], window="24h")["n"], 0)
        self.assertFalse(result["verified_on_own_account"])
        self.assertEqual(result["formula_promotions"], 0)

    def test_real_comments_require_parent_link_and_evidence(self):
        row = {"comment_url": "https://x.com/example/status/456", "parent_post_url": "https://x.com/example/status/123",
               "observed_at_utc": "2026-10-08T00:00:00Z", "categories": ["CORRECTION", "EXPLANATION"],
               "evidence_ref": "synthetic", "coding_note": "synthetic test only", "agent_checked": True}
        self.assertFalse(validate_comment(row)["learning_eligible"])
        for change in [{"categories": ["MADE_UP"]}, {"evidence_ref": None}, {"parent_post_url": "missing"}]:
            with self.assertRaises(ValueError):
                validate_comment({**row, **change})

    def test_rebuild_does_not_change_original_evidence(self):
        from scripts.build_reader_recode import build, OUTPUT
        stored = json.loads(OUTPUT.read_text())
        self.assertEqual(build(), stored)
        self.assertEqual(len({r["post_url"] for r in stored if r["entity_kind"] == "own"}),
                         sum(r["entity_kind"] == "own" for r in stored))
        self.assertEqual(len({(r["entity_kind"], r["entity_id"]) for r in stored}), len(stored))
        self.assertTrue(all(r["reader_model"]["claim_status"] == "HYPOTHESIS" for r in stored))
        unknown = [r for r in stored if r["annotation_state"] == "NEEDS_REVIEW"]
        self.assertTrue(all(r["reader_model"]["predicted_inner_response"] is None for r in unknown))


if __name__ == "__main__":
    unittest.main()
