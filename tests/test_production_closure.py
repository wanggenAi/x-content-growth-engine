"""Exercise the real source-bound packet through every existing gate."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from growth_engine.hunt import production_dry_run
from growth_engine.publication_preflight import pre_publish_assert
from growth_engine.reader_model import METRICS, text_hash


ROOT = Path("data/production_closure_v4_2026-10-21")


def inputs():
    feed = json.loads((ROOT / "source_packet.json").read_text())
    reviews = json.loads((ROOT / "editorial_reviews.json").read_text())
    reviews["publication_memory"] = json.loads(Path(reviews["publication_memory_ref"]).read_text())["publication_memory"]
    return feed, reviews


class ProductionClosureTests(unittest.TestCase):
    def test_historical_self_pass_cannot_grant_new_content_readiness(self):
        feed, reviews = inputs()
        result = production_dry_run(feed, reviews)
        self.assertNotEqual(result["final_status"], "READY_CANDIDATE_DRY_RUN")
        ranking = result["ranking"]
        self.assertGreaterEqual(ranking["candidate_count"], 30)
        self.assertGreaterEqual(ranking["reviewed_source_count"], 20)
        self.assertGreaterEqual(ranking["under48h_count"], 10)
        self.assertGreaterEqual(ranking["source_family_count"], 4)
        closure = result["production_pipeline"]
        candidate = closure["candidate"]
        self.assertEqual(ranking["selected_material_ids"], [candidate["material_id"]])
        self.assertTrue(candidate["reader_model_integrity"]["passed"])
        self.assertFalse(candidate["editorial_gate"]["ready"])
        self.assertFalse(closure["prepublish"]["passed"])
        self.assertEqual(candidate["text"], candidate["authored_text"])
        for variant in result["top1_previews"]:
            self.assertEqual(variant["authoring"]["method"], "SUPPLIED_AUTHOR_REVISION")
            self.assertEqual(variant["text"], variant["after"])
        self.assertFalse(candidate["human_checked"])
        self.assertEqual(candidate["publication_review_exception"], "USER_AUTHORIZED_AGENT_REVIEW")
        self.assertFalse(result["publication_allowed"])
        self.assertIn("CONTENT_FINAL_READER_REVIEW_REQUIRED", candidate["content_review_result"]["reasons"])
        with self.assertRaisesRegex(ValueError, 'not READY'):
            pre_publish_assert(candidate, candidate['text'], dry_run=True)
        feedback = closure["feedback_24h"]
        self.assertEqual(feedback["publication_text_digest"], text_hash(candidate["text"]))
        self.assertEqual(feedback["window_class"], "MISSING")
        self.assertEqual(feedback["metrics_status"], "UNKNOWN")
        self.assertIsNone(feedback["published_at_utc"])
        self.assertIsNone(feedback["observed_at_utc"])
        self.assertTrue(all(feedback[key] is None for key in METRICS))
        self.assertFalse(feedback["learning_eligible"])

    def test_missing_or_changed_editor_evidence_cannot_complete_the_loop(self):
        feed, original = inputs()
        for change in ("missing_packet", "other_material", "other_variant", "text", "reader_model",
                       "source_fact_review", "review_waiver", "authorization", "semantic_context", "source", "rejected"):
            with self.subTest(change=change):
                current_feed, reviews = deepcopy(feed), deepcopy(original)
                packet = reviews["production_candidate"]
                if change == "missing_packet": reviews.pop("production_candidate")
                elif change == "other_material": packet["material_id"] = "not-the-winner"
                elif change == "other_variant": packet["variant_id"] = "C"
                elif change == "text": packet["text"] = "unreviewed prose"
                elif change == "reader_model": packet.pop("reader_model")
                elif change == "source_fact_review": packet.pop("source_fact_review")
                elif change == "review_waiver": packet.pop("publication_review_exception")
                elif change == "authorization": packet["user_authorized"] = False
                elif change == "semantic_context": packet["payload"] = "changed without reader review"
                else:
                    material = next(m for m in current_feed["materials"] if m["material_id"] == packet["material_id"])
                    if change == "source": material["source_evidence"][0]["excerpt"] = "Changed evidence"
                    else: material["user_content_verdict"] = "REJECT"
                result = production_dry_run(current_feed, reviews)
                self.assertFalse(result["production_pipeline"]["prepublish"]["passed"])
                self.assertNotEqual(result["final_status"], "READY_CANDIDATE_DRY_RUN")
                self.assertFalse(result["publication_allowed"])

    def test_cli_resolves_existing_memory_reference_and_exports_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            completed = subprocess.run([
                sys.executable, "-m", "growth_engine", "validate-hunt",
                str(ROOT / "source_packet.json"), str(ROOT / "editorial_reviews.json"),
                "--output", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text())
            self.assertFalse(result["production_pipeline"]["prepublish"]["passed"])
            self.assertIn("正式候选审核结果", output.with_suffix(".md").read_text())


if __name__ == "__main__":
    unittest.main()
