"""Small local CLI for durable research observations."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_DB = Path("data/research.sqlite3")
POST_RE = re.compile(r"^/(?:[A-Za-z0-9_]+|i/web)/status/(\d+)/?$")
METRICS = ("views", "likes", "reposts", "quotes", "replies", "followers")
COHORTS = {"high_candidate", "ordinary_candidate", "unclassified"}
METHODS = {"public_search_index", "direct_public_page", "manual_user_record"}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS x_posts (
  post_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  author_handle TEXT NOT NULL,
  posted_date TEXT,
  topic TEXT NOT NULL,
  excerpt TEXT NOT NULL,
  cohort TEXT NOT NULL CHECK(cohort IN ('high_candidate','ordinary_candidate','unclassified')),
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS x_observations (
  id INTEGER PRIMARY KEY,
  post_id TEXT NOT NULL REFERENCES x_posts(post_id),
  observed_at TEXT NOT NULL,
  source_url TEXT NOT NULL,
  method TEXT NOT NULL,
  discovery_query TEXT NOT NULL,
  evidence_note TEXT NOT NULL,
  views INTEGER, likes INTEGER, reposts INTEGER, quotes INTEGER, replies INTEGER, followers INTEGER,
  UNIQUE(post_id, observed_at, source_url)
);
CREATE TABLE IF NOT EXISTS materials (
  id INTEGER PRIMARY KEY,
  source_url TEXT NOT NULL UNIQUE,
  discovered_at TEXT NOT NULL,
  observation TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
  content_direction TEXT
);
CREATE TABLE IF NOT EXISTS formula_hypotheses (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  definition TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('HYPOTHESIS','REPLICATED','EXPERIMENT_SUPPORTED','REJECTED','REVIEW_REQUIRED')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS formula_history (
  id INTEGER PRIMARY KEY,
  formula_id TEXT NOT NULL REFERENCES formula_hypotheses(id),
  changed_at TEXT NOT NULL,
  old_status TEXT,
  new_status TEXT NOT NULL,
  rationale TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS own_posts (
  post_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  published_at TEXT NOT NULL,
  review_status TEXT NOT NULL CHECK(review_status IN ('APPROVED','PUBLISHED')),
  source_material_id INTEGER REFERENCES materials(id),
  formula_id TEXT REFERENCES formula_hypotheses(id)
);
CREATE TABLE IF NOT EXISTS own_post_observations (
  id INTEGER PRIMARY KEY,
  post_id TEXT NOT NULL REFERENCES own_posts(post_id),
  observed_at TEXT NOT NULL,
  impressions INTEGER, likes INTEGER, replies INTEGER, reposts INTEGER,
  profile_visits INTEGER, new_follows INTEGER,
  evidence_note TEXT NOT NULL,
  UNIQUE(post_id, observed_at)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    return db


def validate(item: dict) -> dict:
    required = ("url", "author_handle", "topic", "excerpt", "cohort", "observed_at", "source_url", "method", "discovery_query", "evidence_note")
    missing = [key for key in required if not isinstance(item.get(key), str) or not item[key].strip()]
    if missing:
        raise ValueError(f"missing/empty fields: {', '.join(missing)}")
    url = urlparse(item["url"])
    match = POST_RE.fullmatch(url.path)
    if url.scheme != "https" or url.hostname not in {"x.com", "twitter.com"} or not match:
        raise ValueError("url must be a canonical X/Twitter status URL")
    source = urlparse(item["source_url"])
    if source.scheme != "https" or not source.hostname:
        raise ValueError("source_url must be an HTTPS evidence URL")
    if item["cohort"] not in COHORTS or item["method"] not in METHODS:
        raise ValueError("invalid cohort or method")
    observed = datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
    if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
        raise ValueError("observed_at must be UTC")
    if item.get("posted_date") is not None:
        datetime.strptime(item["posted_date"], "%Y-%m-%d")
    handle = url.path.split("/")[1]
    if handle != "i" and handle.lower() != item["author_handle"].lstrip("@").lower():
        raise ValueError("author_handle does not match post URL")
    if len(item["excerpt"]) > 180:
        raise ValueError("excerpt exceeds 180 characters")
    for metric in METRICS:
        value = item.get(metric)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{metric} must be a nonnegative integer or null")
    return {**item, "post_id": match.group(1), "url": f"https://x.com/{handle}/status/{match.group(1)}"}


def import_file(db: sqlite3.Connection, path: Path) -> tuple[int, int]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("input must be a JSON array")
    validated = [validate(record) for record in records]
    before_posts = db.execute("SELECT count(*) FROM x_posts").fetchone()[0]
    before_observations = db.execute("SELECT count(*) FROM x_observations").fetchone()[0]
    with db:
        for row in validated:
            db.execute("""INSERT INTO x_posts VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(post_id) DO UPDATE SET last_seen_at=max(x_posts.last_seen_at, excluded.last_seen_at)""",
                (row["post_id"], row["url"], row["author_handle"], row.get("posted_date"), row["topic"], row["excerpt"], row["cohort"], row["observed_at"], row["observed_at"]))
            db.execute("""INSERT OR IGNORE INTO x_observations
                (post_id,observed_at,source_url,method,discovery_query,evidence_note,views,likes,reposts,quotes,replies,followers)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (row["post_id"], row["observed_at"], row["source_url"], row["method"], row["discovery_query"], row["evidence_note"], *(row.get(key) for key in METRICS)))
    posts = db.execute("SELECT count(*) FROM x_posts").fetchone()[0] - before_posts
    observations = db.execute("SELECT count(*) FROM x_observations").fetchone()[0] - before_observations
    return posts, observations


def report(db: sqlite3.Connection) -> dict:
    cohorts = dict(db.execute("SELECT cohort, count(*) FROM x_posts GROUP BY cohort"))
    methods = dict(db.execute("SELECT method, count(*) FROM x_observations GROUP BY method"))
    total = db.execute("SELECT count(*) FROM x_posts").fetchone()[0]
    return {
        "x_posts": total,
        "high_candidates": cohorts.get("high_candidate", 0),
        "ordinary_candidates": cohorts.get("ordinary_candidate", 0),
        "authors": db.execute("SELECT count(DISTINCT lower(author_handle)) FROM x_posts").fetchone()[0],
        "observations": db.execute("SELECT count(*) FROM x_observations").fetchone()[0],
        "methods": methods,
        "unknown_views": db.execute("SELECT count(*) FROM x_observations WHERE views IS NULL").fetchone()[0],
        "unknown_followers": db.execute("SELECT count(*) FROM x_observations WHERE followers IS NULL").fetchone()[0],
        "same_author_both_cohorts": [row[0] for row in db.execute("SELECT author_handle FROM x_posts GROUP BY lower(author_handle) HAVING count(DISTINCT cohort)>1")],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local X research evidence store")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    importer = sub.add_parser("import")
    importer.add_argument("file", type=Path)
    sub.add_parser("report")
    sub.add_parser("audit")
    args = parser.parse_args()
    with connect(args.db) as db:
        if args.command == "init":
            print(f"initialized {args.db}")
        elif args.command == "import":
            posts, observations = import_file(db, args.file)
            print(json.dumps({"new_posts": posts, "new_observations": observations}, ensure_ascii=False))
        elif args.command == "report":
            print(json.dumps(report(db), ensure_ascii=False, indent=2))
        else:
            stats = report(db)
            issues = []
            if stats["x_posts"] < 450:
                issues.append("Below exploratory collection targets; no formula validation")
            if len(stats["methods"]) == 1 and "public_search_index" in stats["methods"]:
                issues.append("Single discovery channel with search-index selection bias")
            if stats["unknown_followers"]:
                issues.append("Author follower counts unknown; reach cannot be normalized")
            if stats["ordinary_candidates"] == 0:
                issues.append("No ordinary-post controls")
            print(json.dumps({"stats": stats, "issues": issues}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
