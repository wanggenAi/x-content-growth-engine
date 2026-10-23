"""Offline handoff gates: never publish unapproved conversations or duplicate posts."""
import json
import tempfile
import unittest
from pathlib import Path

from growth_engine.handoff import text_hash, verify_ready, verify_receipt, scan_outbox


def packet():
    text = "今天路上看到一件事，突然发现我也会羡慕别人。"
    return {
        "schema": "LIVING_RECORD_X_HANDOFF_V1",
        "post_id": "20261023-personal-reflection", "status": "READY_FOR_CODEX",
        "platform": "X", "account": "qiluo27808", "scope": "ORIGINAL_POST",
        "origin": "CHATGPT_USER_CONVERSATION",
        "created_at": "2026-10-23T09:30:00+08:00",
        "text": text, "content_sha256": text_hash(text),
        "claim_type": "PERSONAL_REFLECTION", "source_urls": [],
        "review": {
            "user_explicitly_requested_publication": True,
            "final_text_approved": True, "author_voice_checked": True,
            "privacy_checked": True, "no_invented_first_person": True,
            "facts_and_uncertainty_checked": True, "no_manipulative_pressure": True,
        },
    }


def receipt(p):
    return {
        "post_id": p["post_id"], "content_sha256": p["content_sha256"],
        "account": "qiluo27808", "provider": "X",
        "url": "https://x.com/qiluo27808/status/1234567890123456789",
        "observed_exact_text": True, "verified_at": "2026-10-23T10:00:00+08:00",
    }


class HandoffTests(unittest.TestCase):
    def test_prepared_message_has_no_external_action(self):
        r = verify_ready(packet(), filename="20261023-personal-reflection.json")
        self.assertTrue(r["valid"], r["errors"])
        self.assertFalse(r["publication_triggered"])
        self.assertFalse(r["external_action"])

    def test_denies_chat_without_explicit_post_request(self):
        p = packet()
        p["review"]["user_explicitly_requested_publication"] = False
        self.assertIn("MISSING_AUTHOR_ATTESTATION:user_explicitly_requested_publication",
                      verify_ready(p)["errors"])

    def test_legacy_unattended_publisher_hold_does_not_revoke_explicit_handoff(self):
        p = packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ready").mkdir()
            (root / "state").mkdir()
            (root / "state" / "publisher.json").write_text(json.dumps({
                "status": "PAUSED", "reason": "NO_VERIFIED_COMPLIANT_TRANSPORT",
                "x_api_available": False,
            }))
            file = root / "ready" / (p["post_id"] + ".json")
            file.write_text(json.dumps(p))
            self.assertEqual(len(scan_outbox(root)["ready"]), 1)
            p["review"]["user_explicitly_requested_publication"] = False
            file.write_text(json.dumps(p))
            self.assertTrue(scan_outbox(root)["blocked"])

    def test_rejects_edited_text_wrong_user_and_private_transcript(self):
        for change in (
            {"text": packet()["text"] + "！"},
            {"account": "someone_else"},
            {"raw_conversation": ["secret"]},
        ):
            p = {**packet(), **change}
            self.assertFalse(verify_ready(p)["valid"])

    def test_news_claim_needs_a_source(self):
        p = packet()
        p["claim_type"] = "PUBLIC_FACTS"
        self.assertFalse(verify_ready(p)["valid"])
        p["source_urls"] = ["https://example.com/news"]
        self.assertTrue(verify_ready(p)["valid"])

    def test_receipt_needs_live_url_and_exact_text(self):
        p = packet()
        self.assertTrue(verify_receipt(p, receipt(p))["valid"])
        r = receipt(p)
        r["observed_exact_text"] = False
        self.assertFalse(verify_receipt(p, r)["valid"])
        r = receipt(p)
        r["url"] = "https://x.com.evil/qiluo27808/status/123"
        self.assertFalse(verify_receipt(p, r)["valid"])

    def test_scan_holds_bad_files_and_never_auto_publishes(self):
        p = packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ready").mkdir()
            (root / "receipts").mkdir()
            file = root / "ready" / (p["post_id"] + ".json")
            file.write_text(json.dumps(p), encoding="utf-8")
            q = scan_outbox(root)
            self.assertEqual(len(q["ready"]), 1)
            self.assertEqual(q["validation_scope"], "LOCAL_HANDOFF_INTEGRITY_ONLY")
            self.assertFalse(q["publication_triggered"])
            (root / "receipts" / file.name).write_text(json.dumps(receipt(p)), encoding="utf-8")
            q = scan_outbox(root)
            self.assertEqual(len(q["completed"]), 1)
            self.assertEqual(q["ready"], [])
            (root / "ready" / "bad.json").write_text("{bad", encoding="utf-8")
            self.assertTrue(scan_outbox(root)["blocked"])


if __name__ == "__main__":
    unittest.main()

class LongformHandoffTests(unittest.TestCase):
    """Long discussions cannot be silently truncated or falsely reported published."""

    def _longform(self):
        p = packet()
        p["post_id"] = "20261023-approved-longform"
        p["scope"] = "LONGFORM_OR_THREAD"
        p["text"] = "第一件具体的事。\n\n第二件具体的事。\n\n最后我还不知道答案。"
        p["thread_parts"] = ["第一件具体的事。", "第二件具体的事。", "最后我还不知道答案。"]
        p["content_sha256"] = text_hash(p["text"])
        return p

    def test_every_paragraph_must_be_preserved(self):
        p = self._longform()
        self.assertTrue(verify_ready(p)["valid"], verify_ready(p)["errors"])
        p["thread_parts"][1] = "一句话总结"
        self.assertIn("THREAD_TEXT_MISMATCH", verify_ready(p)["errors"])

    def test_oversized_part_denied(self):
        p = self._longform()
        p["thread_parts"] = ["长" * 131, "结束。"]
        p["text"] = "\n\n".join(p["thread_parts"])
        p["content_sha256"] = text_hash(p["text"])
        self.assertIn("THREAD_PART_TOO_LONG_OR_EMPTY", verify_ready(p)["errors"])

    def test_long_post_requires_exact_observed_text(self):
        p = self._longform()
        r = receipt(p)
        r["publish_mode"] = "LONG_POST"
        self.assertFalse(verify_receipt(p, r)["valid"])
        r["observed_text"] = p["text"]
        self.assertTrue(verify_receipt(p, r)["valid"])

    def test_thread_requires_all_real_urls_and_text(self):
        p = self._longform()
        r = receipt(p)
        r["publish_mode"] = "THREAD"
        r["observed_parts"] = [
            {"url": r["url"], "observed_text": "第一件具体的事。"},
            {"url": "https://x.com/qiluo27808/status/1234567890123456790", "observed_text": "第二件具体的事。"},
            {"url": "https://x.com/qiluo27808/status/1234567890123456791", "observed_text": "最后我还不知道答案。"},
        ]
        self.assertTrue(verify_receipt(p, r)["valid"])
        r["observed_parts"][2]["observed_text"] = "随便替换了"
        self.assertFalse(verify_receipt(p, r)["valid"])
