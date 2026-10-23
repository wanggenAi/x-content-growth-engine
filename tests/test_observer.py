from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import tempfile
import unittest
from growth_engine.observer import build_digest, parse_rss, person_action, save_note, select

NOW = datetime(2026, 10, 23, 1, tzinfo=timezone.utc)
FEED = {"id":"people","name":"普通人","query":"民事"}
XML = """<rss><channel>
<item><title>女子回应街头纠纷 - 媒体甲</title><link>https://news.google.com/rss/articles/a</link><pubDate>Fri, 23 Oct 2026 00:30:00 GMT</pubDate><source>媒体甲</source></item>
<item><title>马斯克宣布新计划 - 媒体乙</title><link>https://news.google.com/rss/articles/b</link><pubDate>Fri, 23 Oct 2026 00:29:00 GMT</pubDate><source>媒体乙</source></item>
<item><title>宏观经济趋势观点</title><link>https://news.google.com/rss/articles/c</link><pubDate>Fri, 23 Oct 2026 00:28:00 GMT</pubDate></item>
</channel></rss>""".encode("utf-8")

class ObserverTests(unittest.TestCase):
    def test_person_action_and_provenance(self):
        items = parse_rss(XML, FEED, at=NOW)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["source"], "媒体甲")
        self.assertEqual(items[0]["verification"], "UNVERIFIED_RSS_LEAD")
        self.assertTrue(person_action(items[0]))
        self.assertFalse(person_action(items[2]))
    def test_limit_age_seen(self):
        items = parse_rss(XML, FEED, at=NOW)
        self.assertEqual(len(select(items, {}, at=NOW)), 2)
        self.assertEqual(len(select(items, {items[0]["key"]:NOW}, at=NOW)), 1)
        self.assertEqual(select(items, {}, at=NOW + timedelta(days=4)), [])
    def test_hourly_memory_and_no_publishing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/"config.json").write_text(json.dumps({"feeds":[FEED],"max_items_per_hour":5,"max_age_hours":48,"cooldown_hours":72}))
            args = (p/"config.json", p/"reports", p/"seen.json")
            run = lambda: build_digest(*args, at=NOW, fetcher=lambda _:XML)
            one = run()
            self.assertEqual(one["count"], 2)
            self.assertIn("可以只看、不评论", one["markdown"])
            self.assertFalse(json.loads((p/"reports"/"latest.json").read_text())["automatic_x_submission"])
            self.assertEqual(run()["count"], 0)
    def test_private_note_verbatim(self):
        with tempfile.TemporaryDirectory() as d:
            file=save_note("今天心里有点嫉妒。","personal",d,at=NOW)
            self.assertIn("今天心里有点嫉妒。",Path(file).read_text())
            with self.assertRaises(ValueError):
                save_note(" ","personal",d)

if __name__=="__main__":
    unittest.main()
