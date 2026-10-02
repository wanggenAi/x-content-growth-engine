import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from growth_engine.__main__ import SCHEMA, connect, import_csv, import_file, validate
from growth_engine.phase2 import import_pairs, import_queries, import_research_review, quality_report, research_packet


BASE = {
    "url": "https://x.com/example/status/12345", "author_handle": "example",
    "posted_date": "2026-09-01", "topic": "AI", "excerpt": "A short excerpt",
    "cohort": "unclassified", "observed_at": "2026-09-29T00:00:00Z",
    "source_url": "https://x.com/example/status/12345", "method": "public_search_index",
    "discovery_query": "example AI", "evidence_note": "Index result", "views": 100,
}


class Phase2Tests(unittest.TestCase):
    def test_legacy_migration_preserves_observation_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "old.db"
            with closing(sqlite3.connect(path)) as old:
                old.executescript(SCHEMA)
                old.execute("INSERT INTO x_posts VALUES (?,?,?,?,?,?,?,?,?)", (
                    "12345", BASE["url"], "example", "2026-09-01", "AI", "excerpt", "unclassified",
                    BASE["observed_at"], BASE["observed_at"]))
                old.execute("""INSERT INTO x_observations
                    (post_id,observed_at,source_url,method,discovery_query,evidence_note,views)
                    VALUES (?,?,?,?,?,?,?)""", ("12345", BASE["observed_at"], BASE["source_url"],
                                                   "public_search_index", "example AI", "Index result", 100))
                old.commit()
            for _ in range(2):
                with closing(connect(path)) as db:
                    self.assertEqual(quality_report(db)["discovered_posts"], 1)
                    self.assertEqual(db.execute("SELECT count(*) FROM x_observations").fetchone()[0], 1)
                    self.assertEqual(db.execute("SELECT metric_source FROM x_observations").fetchone()[0], "SEARCH_INDEX")
                    self.assertEqual(db.execute("SELECT views_precision FROM x_observations").fetchone()[0], "EXACT_DISPLAYED")

    def test_conflicting_same_timestamp_source_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / "batch.json"
            source.write_text(json.dumps([BASE, {**BASE, "views": 120, "evidence_note": "Conflicting index value"}]))
            with closing(connect(path / "db.sqlite3")) as db:
                self.assertEqual(import_file(db, source), (1, 2))
                self.assertEqual(quality_report(db)["conflicting_observation_groups"], 1)
                self.assertEqual(import_file(db, source), (0, 0))

    def test_manual_confirmation_requires_evidence_and_index_cannot_confirm(self):
        with self.assertRaises(ValueError):
            validate({**BASE, "verification_status": "ORIGINAL_CONFIRMED", "evidence_ref": "x"})
        with self.assertRaises(ValueError):
            validate({**BASE, "method": "manual_user_record", "verification_status": "ORIGINAL_CONFIRMED"})
        with self.assertRaises(ValueError):
            validate({**BASE, "metric_as_of": "2026-09-30T00:00:00Z"})

    def test_manual_recheck_upgrades_existing_candidate_without_losing_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / "batch.json"
            source.write_text(json.dumps([BASE, {**BASE, "method": "manual_user_record",
                "observed_at": "2026-09-30T00:00:00Z", "evidence_ref": "private-screenshot",
                "evidence_note": "Human checked context", "verification_status": "ORIGINAL_CONFIRMED",
                "human_checked": True, "post_type": "ORIGINAL", "promotion_status": "NONE_OBSERVED",
                "metric_source": "USER_SCREENSHOT", "metric_as_of": "2026-09-30T00:00:00Z"}]))
            with closing(connect(path / "db.sqlite3")) as db:
                self.assertEqual(import_file(db, source), (1, 2))
                self.assertEqual(db.execute("SELECT verification_status,post_type,promotion_status FROM x_posts").fetchone(),
                                 ("ORIGINAL_CONFIRMED", "ORIGINAL", "NONE_OBSERVED"))
                self.assertEqual(quality_report(db)["posts_with_dated_metrics"], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM x_observations").fetchone()[0], 2)

    def test_csv_batch_is_atomic_and_retain_metric_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = path / "batch.csv"
            header = "url,author_handle,topic,excerpt,observed_at,source_url,evidence_note,evidence_ref,verification_status,metric_source,metric_as_of,views,human_checked\n"
            row = "https://x.com/example/status/12345,example,AI,Observed,2026-09-29T00:00:00Z,https://x.com/example/status/12345,Manual note,private-screenshot-1,ORIGINAL_CONFIRMED,USER_SCREENSHOT,2026-09-29T00:00:00Z,100,true\n"
            source.write_text(header + row + row.replace("100,true\n", "bad,true\n"))
            with closing(connect(path / "db.sqlite3")) as db:
                with self.assertRaises(ValueError):
                    import_csv(db, source)
                self.assertEqual(quality_report(db)["discovered_posts"], 0)
                source.write_text(header + row)
                self.assertEqual(import_csv(db, source), (1, 1))
                self.assertEqual(quality_report(db)["posts_with_dated_metrics"], 1)

    def test_query_log_review_and_pair_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sample = path / "sample.json"
            sample.write_text(json.dumps([BASE]))
            queries = path / "queries.json"
            queries.write_text(json.dumps([{
                "id": "q1", "channel": "public_search", "query_text": "example AI",
                "executed_at": BASE["observed_at"], "visible_results": 1, "candidate_urls": 1,
                "admitted": 1, "duplicates": 0, "rejected": 0, "metric_candidates": 1,
                "result_post_ids": ["12345"], "permission_status": "ALLOWED_PUBLIC_SEARCH",
                "evidence_ref": "local-query-record", "failure_reason": None,
            }]))
            with closing(connect(path / "db.sqlite3")) as db:
                import_file(db, sample)
                self.assertEqual(import_queries(db, queries), 1)
                self.assertEqual(import_queries(db, queries), 0)
                invalid_batch = json.loads(queries.read_text())
                invalid_batch[0]["id"] = "q2"
                invalid_batch.append({**invalid_batch[0], "id": "q3", "candidate_urls": 2})
                queries.write_text(json.dumps(invalid_batch))
                with self.assertRaises(ValueError):
                    import_queries(db, queries)
                self.assertEqual(quality_report(db)["query_runs"], 1)
                review = path / "review.json"
                entry = {"id": "h1", "question": "Does this pattern replicate?", "hypothesis": "Possible pattern",
                         "limitations": "One indexed post", "reviewer_note": "Human checked scope",
                         "evidence_post_ids": ["12345"], "counterexample_post_ids": [], "human_reviewed": True,
                         "status": "HYPOTHESIS"}
                review.write_text(json.dumps([entry]))
                self.assertEqual(import_research_review(db, review), 1)
                self.assertEqual(import_research_review(db, review), 1)
                self.assertEqual(len(research_packet(db)["hypotheses"]), 2)
                self.assertEqual(research_packet(db)["analysis_ready_post_ids"], [])
                review.write_text(json.dumps([{**entry, "status": "REPLICATED"}]))
                with self.assertRaises(ValueError):
                    import_research_review(db, review)
                pair = path / "pair.json"
                pair.write_text(json.dumps([{"id": "p1", "candidate_post_id": "12345",
                    "control_post_id": "12345", "matching_basis": "same author", "differences": "none", "status": "READY"}]))
                with self.assertRaises(ValueError):
                    import_pairs(db, pair)


if __name__ == "__main__":
    unittest.main()
