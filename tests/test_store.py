import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from growth_engine.__main__ import connect, import_file, import_materials, report, validate, validate_material


BASE = {
    "url": "https://x.com/example/status/12345",
    "author_handle": "example",
    "posted_date": "2026-09-01",
    "topic": "AI",
    "excerpt": "A short research excerpt",
    "cohort": "ordinary_candidate",
    "observed_at": "2026-09-29T00:00:00Z",
    "source_url": "https://x.com/example/status/12345",
    "method": "public_search_index",
    "discovery_query": "site:x.com/example/status/ AI",
    "evidence_note": "Index result",
    "views": None,
}


class StoreTests(unittest.TestCase):
    def test_validation_rejects_false_precision_and_missing_provenance(self):
        for changes in ({"views": -1}, {"views": "100"}, {"source_url": ""}, {"observed_at": "2026-09-29"}, {"url": "https://other.site/example/status/12345"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate({**BASE, **changes})

    def test_idempotent_import_and_unknown_is_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            seed = path / "seed.json"
            seed.write_text(json.dumps([BASE]), encoding="utf-8")
            with connect(path / "research.sqlite3") as db:
                self.assertEqual(import_file(db, seed), (1, 1))
                self.assertEqual(import_file(db, seed), (0, 0))
                self.assertEqual(report(db)["unknown_views"], 1)
                self.assertEqual(db.execute("SELECT views FROM x_observations").fetchone(), (None,))
                self.assertEqual(db.execute("SELECT count(*) FROM materials").fetchone(), (0,))

    def test_invalid_batch_does_not_partially_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            seed = path / "seed.json"
            seed.write_text(json.dumps([BASE, {**BASE, "source_url": ""}]), encoding="utf-8")
            with connect(path / "research.sqlite3") as db:
                with self.assertRaises(ValueError):
                    import_file(db, seed)
                self.assertEqual(report(db)["x_posts"], 0)

    def test_formula_status_is_constrained(self):
        with tempfile.TemporaryDirectory() as directory:
            with connect(Path(directory) / "research.sqlite3") as db:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("INSERT INTO formula_hypotheses VALUES ('F1','claim','text','MATURE','2026-09-29')")

    def test_older_observation_does_not_move_checkpoint_backwards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            seed = path / "seed.json"
            with connect(path / "research.sqlite3") as db:
                seed.write_text(json.dumps([BASE]), encoding="utf-8")
                import_file(db, seed)
                seed.write_text(json.dumps([{**BASE, "observed_at": "2026-09-28T00:00:00Z"}]), encoding="utf-8")
                self.assertEqual(import_file(db, seed), (0, 1))
                self.assertEqual(db.execute("SELECT last_seen_at FROM x_posts").fetchone()[0], BASE["observed_at"])

    def test_materials_are_separate_deduplicated_and_reddit_blocked(self):
        material = {
            "source_url": "https://github.com/example/project",
            "discovery_url": "https://news.ycombinator.com/item?id=123",
            "source_kind": "github_project",
            "published_at": "2026-09-28",
            "discovered_at": "2026-09-29T00:00:00Z",
            "observation": "Short original summary",
            "verification_status": "SOURCE_CHECKED",
            "content_direction": "Test a concrete use case",
            "region": "global",
            "rights_note": "Link only",
            "review_after": "2026-10-29",
        }
        with self.assertRaises(ValueError):
            validate_material({**material, "source_url": "https://www.reddit.com/r/test"})
        with self.assertRaises(ValueError):
            validate_material({**material, "source_url": "https://old.reddit.com/r/test"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            seed = path / "materials.json"
            seed.write_text(json.dumps([material]), encoding="utf-8")
            with connect(path / "research.sqlite3") as db:
                self.assertEqual(import_materials(db, seed), 1)
                self.assertEqual(import_materials(db, seed), 0)
                self.assertEqual(report(db)["materials"], 1)
                self.assertEqual(report(db)["x_posts"], 0)


if __name__ == "__main__":
    unittest.main()
