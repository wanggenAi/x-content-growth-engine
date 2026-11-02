import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from telegram_research.core import validate_channel, classify, make_record, build_brief, save_reports
from telegram_research.reader import pdf_details

class TelegramResearchTests(unittest.TestCase):
    def test_channel_valid(self):
        self.assertEqual(validate_channel("@shenduhaowen"), "shenduhaowen")
        self.assertEqual(validate_channel("https://t.me/shenduhaowen"), "shenduhaowen")
        with self.assertRaises(ValueError):
            validate_channel("../secrets")

    def test_scoring_is_explicitly_heuristic(self):
        labels, score = classify("东南亚出海供应链客户合作机会")
        self.assertIn("跨境B2B", labels)
        self.assertGreater(score, 0)
        self.assertEqual(classify("完全无关")[-1], 0)

    def test_report_does_not_publish_pdf_text(self):
        secret_pdf_text = "This must not show up in reports 大模型供应链"
        record = make_record(channel="shenduhaowen", msg_id=123, date=datetime.now(timezone.utc),
                             caption="共享 PDF", filename="report.pdf", file_size=100,
                             pdf_text=secret_pdf_text, pdf_pages=2)
        self.assertTrue(record["pdf_read"])
        self.assertEqual(record["link"], "https://t.me/shenduhaowen/123")
        with TemporaryDirectory() as folder:
            save_reports(Path(folder), "shenduhaowen", [record], pdf_mode=True)
            self.assertNotIn(secret_pdf_text, (Path(folder) / "brief.md").read_text())
            self.assertNotIn(secret_pdf_text, (Path(folder) / "posts.json").read_text())

    def test_empty_report_and_extract_failure(self):
        brief = build_brief("shenduhaowen", [], datetime.now(timezone.utc), pdf_mode=False)
        self.assertIn("没有检索到", brief)
        with TemporaryDirectory() as folder:
            content, pages, err = pdf_details(Path(folder) / "not-there.pdf")
            self.assertEqual(content, "")
            self.assertTrue(err)

if __name__ == '__main__':
    unittest.main()
