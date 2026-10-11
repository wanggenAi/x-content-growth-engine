import json
import tempfile
import unittest
from pathlib import Path

from growth_engine.__main__ import connect
from growth_engine.editorial_gate import validate_candidate
from growth_engine.reader_model import (
    DIMENSIONS, VALUE_MODEL_VERSION, backtest, empty_profile, import_annotations, migrate_profile,
    profile_errors, ratios, reader_packet, review_profile, validate_comment, window_measurement,
    window_status,
)


def good_profile():
    p = empty_profile()
    p.update({key: "HIGH" for key in DIMENSIONS})
    p.update(model_version=VALUE_MODEL_VERSION, dominant_reader_value_route="SELF_RELEVANCE",
             reader_value_routes=[{"route": "SELF_RELEVANCE", "strength": "HIGH", "cue": "submission failed after preparation", "reader_thought": "Will mine fail too?"}],
             activation_mechanisms=["PERSONAL_EXPERIENCE"])
    p.update(concrete_stakes="time lost in an application", identity_trigger="applicants",
             why_reader_cares="Will my application fail too?", predicted_inner_response="Why did it fail?",
             share_recipient="a colleague applying", share_reason="avoid the same loss",
             social_currency="HIGH", opinion_activation="HIGH", opinion_space="HIGH",
             opinion_space_reason="different experiences can explain the outcome",
             utility="HIGH", future_usefulness="check the next application", concrete_resource="failure log",
             resource_value="HIGH", source_accessibility="HIGH", actionability="HIGH",
             curiosity="HIGH", information_gap="why the submission failed", narrative_progression="the error appears after submission",
             expectation_violation="HIGH",
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
    def test_low_self_relevance_high_curiosity_is_reviewable(self):
        p = good_profile()
        p.update(self_relevance="LOW", dominant_reader_value_route="CURIOSITY",
                 reader_value_routes=[{"route": "CURIOSITY", "strength": "HIGH", "cue": "an unfamiliar craft changes material under heat", "reader_thought": "How does that work?"}],
                 curiosity="HIGH", curiosity_types=["HIDDEN_PROCESS", "RARE_SKILL"],
                 information_gap="What process changes the material?", narrative_progression="the maker reveals the steps",
                 expectation_violation="HIGH", why_reader_cares="A rare process is worth understanding even without personal similarity.",
                 predicted_inner_response="原来是这样做出来的。", concrete_resource="recorded process notes")
        self.assertEqual(review_profile(p, "DWELL")["priority"], "REVIEW_FIRST")
        self.assertNotIn("self_relevance", review_profile(p, "DWELL")["reasons"])

    def test_action_routes_have_conditional_contracts(self):
        p = good_profile()
        self.assertTrue(validate_candidate({key: "reviewed" for key in __import__("growth_engine.editorial_gate", fromlist=["REQUIRED_FIELDS"]).REQUIRED_FIELDS} | {
            "source_refs": ["source"], "material_strength": "STRONG", "primary_action": "SHARE",
            "human_checked": True, "state": "EDITORIAL_REVIEW", "reader_model": p
        }).ready)
        for action, missing in (("SHARE", "share_recipient"), ("REPLY", "opinion_space"),
                                ("SAVE_RETURN", "concrete_resource"), ("CLICK_RESOURCE", "actionability"),
                                ("DWELL", "information_gap"), ("FOLLOW", "why_follow")):
            candidate = {key: "reviewed" for key in __import__("growth_engine.editorial_gate", fromlist=["REQUIRED_FIELDS"]).REQUIRED_FIELDS}
            candidate.update(source_refs=["source"], material_strength="STRONG", primary_action=action,
                             human_checked=True, state="EDITORIAL_REVIEW", reader_model=good_profile())
            candidate["reader_model"].pop(missing, None)
            self.assertFalse(validate_candidate(candidate).ready, action)

    def test_migration_preserves_legacy_without_inference(self):
        legacy = empty_profile()
        migrated = migrate_profile(legacy)
        self.assertEqual(migrated["model_version"], VALUE_MODEL_VERSION)
        self.assertEqual(migrated["reader_value_routes"], [])
        self.assertEqual(migrated["self_relevance"], "UNKNOWN")
        self.assertEqual(migrated["migration_note"], "Legacy signals preserved. Routes require explicit editorial review; no inferred strengths.")

    def test_window_tolerances_keep_actual_age_and_unknown(self):
        result = window_measurement("2026-10-01T00:00:00Z", "2026-10-02T00:45:00Z", "24h")
        self.assertEqual(result["window_class"], "NEAR_WINDOW")
        self.assertEqual(result["actual_post_age_minutes"], 1485.0)
        self.assertEqual(result["offset_from_target_minutes"], 45.0)
        self.assertEqual(window_measurement(None, None, "7d")["window_class"], "MISSING")

    def test_comment_prediction_match_is_recorded(self):
        row = {"comment_url": "https://x.com/example/status/456", "parent_post_url": "https://x.com/example/status/123",
               "observed_at_utc": "2026-10-08T02:00:00Z", "categories": ["CORRECTION", "EXPLANATION"],
               "evidence_ref": "synthetic", "coding_note": "synthetic test only", "body": "The real cause is different.", "agent_checked": True}
        prediction = {"experiment_id": "E1", "publication_url": row["parent_post_url"],
                      "preregistered_at_utc": "2026-10-07T00:00:00Z", "published_at_utc": "2026-10-07T01:00:00Z",
                      "activation_mechanisms": ["CORRECTION"]}
        self.assertEqual(validate_comment(row, prediction=prediction)["activation_prediction_match"]["status"], "MATCH")

    def test_stratified_sample_and_prospective_design_are_bounded(self):
        sample = json.loads(Path("data/reader_value_stratified_sample_2026-10-08.json").read_text())
        self.assertGreaterEqual(len(sample), 20)
        self.assertLessEqual(len(sample), 40)
        self.assertEqual({r["entity_kind"] for r in sample}, {"external", "own"})
        routes = {r["reader_model"]["dominant_reader_value_route"] for r in sample}
        self.assertTrue({"SELF_RELEVANCE", "CURIOSITY", "EPISTEMIC_REWARD", "UTILITY", "WONDER"} <= routes)
        self.assertTrue(all(r["reader_model"]["claim_status"] == "HYPOTHESIS" for r in sample))
        experiment = json.loads(Path("data/prospective_reader_value_experiment_2026-10-08.json").read_text())
        self.assertEqual(experiment["status"], "DESIGNED_NOT_SCHEDULED")
        self.assertEqual(len(experiment["cells"]), 12)
        self.assertEqual({c["hypothesis"] for c in experiment["cells"]}, {"H1", "H2", "H3"})

    def test_published_legacy_record_remains_auditable_but_new_v1_admission_fails(self):
        candidate = json.loads(Path("data/editorial_candidate_c355_2026-10-07.json").read_text())
        url = candidate["url"]
        self.assertTrue(validate_candidate(candidate).ready)
        self.assertEqual(candidate["url"], url)
        candidate["state"] = "EDITORIAL_REVIEW"
        self.assertFalse(validate_candidate(candidate).ready)
    def test_material_cannot_be_rescued_by_topic_strength(self):
        p = good_profile()
        p["material_strength"] = "LOW"
        result = review_profile(p)
        self.assertEqual(result["priority"], "LOWER_PRIORITY")
        self.assertIn("A_MATERIAL", result["reasons"])
        self.assertNotIn("score", result)

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

    def test_gate_blocks_missing_model_and_weak_reply_not_calm_wording(self):
        from growth_engine.editorial_gate import REQUIRED_FIELDS
        c = {key: "reviewed" for key in REQUIRED_FIELDS}
        c.update(source_refs=["source"], material_strength="STRONG", primary_action="REPLY",
                 human_checked=True, state="EDITORIAL_REVIEW", reader_model=good_profile())
        self.assertTrue(validate_candidate(c).ready)
        del c["reader_model"]
        self.assertFalse(validate_candidate(c).ready)
        c["reader_model"] = good_profile()
        c["reader_model"]["predicted_inner_response"] = "哦。"
        self.assertTrue(validate_candidate(c).ready)  # No dramatic-language test.
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
        late = {**obs, "observed_at_utc": "2026-10-02T02:01:00Z", "distribution_confidence": "UNKNOWN"}
        late_result = backtest([annotation()], [late], window="24h")
        self.assertEqual(late_result["n"], 0)
        self.assertEqual(late_result["rows"][0]["window_class"], "LATE_EXPLORATORY")
        self.assertEqual(late_result["rows"][0]["actual_post_age_minutes"], 1561.0)
        self.assertEqual(late_result["rows"][0]["distribution_confidence"], "UNKNOWN")
        self.assertEqual(late_result["rows"][0]["content_failure"], "UNKNOWN")

    def test_real_comments_require_parent_link_and_evidence(self):
        row = {"comment_url": "https://x.com/example/status/456", "parent_post_url": "https://x.com/example/status/123",
               "observed_at_utc": "2026-10-08T00:00:00Z", "categories": ["CORRECTION", "EXPLANATION"],
               "evidence_ref": "synthetic", "coding_note": "synthetic test only", "body": "The real cause is different.", "agent_checked": True}
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
