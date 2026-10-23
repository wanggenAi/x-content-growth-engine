"""Regressions for the first-person, non-viral content lane."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from growth_engine.field_notes import MODE, blank_template, evaluate_note


def note():
    return {
        "mode": MODE, "note_id": "sample-001", "observed_at": "2026-10-23T09:03:00+08:00",
        "kind": "PERSONAL", "origin": "USER_DIRECT",
        "raw_observation": "我今天想通了一件事情。",
        "draft_text": "今天想记录一点东西。没有结论，也没关系。",
        "source_urls": [], "commercial_intent": "NONE",
        "review": {"author_approved": True, "facts_and_uncertainty_checked": True,
                   "privacy_checked": True, "no_invented_experience": True,
                   "no_manipulative_pressure": True},
    }


class FieldNotesTests(unittest.TestCase):
    def test_ordinary_content_ready_without_hook_cta_or_top1(self):
        result = evaluate_note(note())
        self.assertTrue(result["ready_for_manual_publish"])
        self.assertFalse(result["external_action"])
        self.assertFalse(result["automatic_x_submission"])

    def test_draft_and_origin_are_not_invented_by_ai(self):
        for change, reason in (
            ({"origin": "EDITOR_INFERRED"}, "USER_ORIGINAL_INPUT_REQUIRED"),
            ({"raw_observation": ""}, "RAW_OBSERVATION_REQUIRED"),
            ({"draft_text": ""}, "DRAFT_REQUIRED"),
            ({"fixture_type": "EXAMPLE_ONLY"}, "EXAMPLE_CANNOT_PUBLISH"),
        ):
            with self.subTest(change=change):
                self.assertIn(reason, evaluate_note({**note(), **change})["reasons"])

    def test_review_must_be_explicit(self):
        for key in ("author_approved", "facts_and_uncertainty_checked", "privacy_checked",
                    "no_invented_experience", "no_manipulative_pressure"):
            n = note()
            n["review"][key] = False
            self.assertIn("AUTHOR_REVIEW_REQUIRED:" + key, evaluate_note(n)["reasons"])

    def test_public_event_requires_credible_link_field(self):
        n = note()
        n["kind"] = "PUBLIC_EVENT"
        self.assertIn("PUBLIC_EVENT_SOURCE_REQUIRED", evaluate_note(n)["reasons"])
        n["source_urls"] = ["https://example.org/news"]
        self.assertTrue(evaluate_note(n)["ready_for_manual_publish"])
        n["source_urls"] = ["javascript:bad"]
        self.assertFalse(evaluate_note(n)["ready_for_manual_publish"])

    def test_conversation_privacy_and_commercial_disclosure(self):
        n = note()
        n["kind"] = "CONVERSATION"
        self.assertIn("CONVERSATION_PRIVACY_REVIEW_REQUIRED", evaluate_note(n)["reasons"])
        n["review"]["conversation_privacy_handled"] = True
        self.assertTrue(evaluate_note(n)["ready_for_manual_publish"])
        n["commercial_intent"] = "AFFILIATE"
        self.assertIn("COMMERCIAL_DISCLOSURE_REQUIRED", evaluate_note(n)["reasons"])
        n["commercial_disclosure"] = "含推广合作"
        self.assertTrue(evaluate_note(n)["ready_for_manual_publish"])

    def test_invalid_timestamp_and_blank_template_hold(self):
        n = note()
        n["observed_at"] = "2026-10-23T09:03:00"
        self.assertIn("TIMEZONE_AWARE_OBSERVATION_TIME_REQUIRED", evaluate_note(n)["reasons"])
        self.assertFalse(evaluate_note(blank_template())["ready_for_manual_publish"])

    def test_cli_only_checks_and_previews(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "note.json"
            n = note()
            path.write_text(json.dumps(n, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "growth_engine.field_notes", "check",
                                     str(path), "--require-ready"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["external_action"])
            view = subprocess.run([sys.executable, "-m", "growth_engine.field_notes",
                                   "preview", str(path)], text=True, capture_output=True)
            self.assertEqual(view.stdout.strip(), n["draft_text"])
            n["review"]["author_approved"] = False
            path.write_text(json.dumps(n, ensure_ascii=False), encoding="utf-8")
            failed = subprocess.run([sys.executable, "-m", "growth_engine.field_notes",
                                     "check", str(path), "--require-ready"], text=True, capture_output=True)
            self.assertEqual(failed.returncode, 1)
