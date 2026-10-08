"""Small local CLI for durable research observations."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, date, timezone
from pathlib import Path
from urllib.parse import urlparse

from .editorial_gate import validate_candidate
from . import reader_model
from .phase2 import (import_annotations, import_pairs, import_queries, import_research_review, insert_observation, migrate,
                     packet_markdown, quality_report, research_packet)

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
  content_direction TEXT,
  discovery_url TEXT,
  source_kind TEXT,
  published_at TEXT,
  region TEXT,
  rights_note TEXT,
  review_after TEXT
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
CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  input_path TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  added_items INTEGER NOT NULL,
  added_observations INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('SUCCESS','FAILED')),
  error TEXT,
  retries INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    columns = {row[1] for row in db.execute("PRAGMA table_info(materials)")}
    for name in ("discovery_url", "source_kind", "published_at", "region", "rights_note", "review_after"):
        if name not in columns:
            db.execute(f"ALTER TABLE materials ADD COLUMN {name} TEXT")
    migrate(db)
    reader_model.migrate(db)
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
    if item.get("verification_status", "DISCOVERED") not in {"DISCOVERED", "ORIGINAL_CONFIRMED"}:
        raise ValueError("invalid verification status")
    if item.get("verification_status") == "ORIGINAL_CONFIRMED" and item["method"] == "public_search_index":
        raise ValueError("search index cannot confirm the original page")
    if item.get("verification_status") == "ORIGINAL_CONFIRMED" and item["method"] == "manual_user_record" and item.get("human_checked") is not True:
        raise ValueError("manual original confirmation requires human_checked=true")
    if item.get("post_type", "UNKNOWN") not in {"UNKNOWN", "ORIGINAL", "REPLY", "QUOTE", "REPOST", "ARTICLE"}:
        raise ValueError("invalid post type")
    if item.get("promotion_status", "UNKNOWN") not in {"UNKNOWN", "NONE_OBSERVED", "SUSPECTED", "DISCLOSED"}:
        raise ValueError("invalid promotion status")
    if item.get("metric_source", "UNKNOWN") not in {"UNKNOWN", "SEARCH_INDEX", "PUBLIC_X_PAGE", "USER_SCREENSHOT", "USER_NOTE"}:
        raise ValueError("invalid metric source")
    if item.get("views_precision") not in {None, "UNKNOWN", "APPROXIMATE", "EXACT_DISPLAYED"}:
        raise ValueError("invalid views precision")
    if item.get("views_precision") == "EXACT_DISPLAYED" and item.get("views") is None:
        raise ValueError("exact views precision needs a view count")
    if item.get("metric_as_of"):
        metric_at = datetime.fromisoformat(item["metric_as_of"].replace("Z", "+00:00"))
        if metric_at.utcoffset() is None or metric_at.utcoffset().total_seconds() != 0:
            raise ValueError("metric_as_of must be UTC")
    if item.get("metric_source") == "SEARCH_INDEX" and item.get("metric_as_of"):
        raise ValueError("search index cannot establish metric timestamp")
    if item.get("verification_status") == "ORIGINAL_CONFIRMED" and not item.get("evidence_ref"):
        raise ValueError("confirmed original requires evidence_ref")
    observed = datetime.fromisoformat(item["observed_at"].replace("Z", "+00:00"))
    if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
        raise ValueError("observed_at must be UTC")
    if item.get("metric_as_of") and metric_at > observed:
        raise ValueError("metric_as_of cannot be later than observed_at")
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
    canonical_path = f"i/web/status/{match.group(1)}" if handle == "i" else f"{handle}/status/{match.group(1)}"
    return {**item, "post_id": match.group(1), "url": f"https://x.com/{canonical_path}"}


def import_file(db: sqlite3.Connection, path: Path) -> tuple[int, int]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("input must be a JSON array")
    validated = [validate(record) for record in records]
    before_posts = db.execute("SELECT count(*) FROM x_posts").fetchone()[0]
    before_observations = db.execute("SELECT count(*) FROM x_observations").fetchone()[0]
    with db:
        for row in validated:
            insert_observation(db, row)
    posts = db.execute("SELECT count(*) FROM x_posts").fetchone()[0] - before_posts
    observations = db.execute("SELECT count(*) FROM x_observations").fetchone()[0] - before_observations
    return posts, observations


def import_csv(db: sqlite3.Connection, path: Path) -> tuple[int, int]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("CSV has no observations")
    prepared = []
    for row in rows:
        cleaned = {key: value.strip() if isinstance(value, str) else value for key, value in row.items() if key}
        for metric in METRICS:
            cleaned[metric] = int(cleaned[metric]) if cleaned.get(metric) else None
        cleaned["cohort"] = cleaned.get("cohort") or "unclassified"
        cleaned["method"] = cleaned.get("method") or "manual_user_record"
        cleaned["discovery_query"] = cleaned.get("discovery_query") or "user supplied batch"
        cleaned["verification_status"] = cleaned.get("verification_status") or "DISCOVERED"
        cleaned["metric_source"] = cleaned.get("metric_source") or "UNKNOWN"
        cleaned["views_precision"] = cleaned.get("views_precision") or None
        cleaned["human_checked"] = cleaned.get("human_checked", "").lower() == "true"
        cleaned["source_url"] = cleaned.get("source_url") or cleaned.get("url")
        cleaned["posted_date"] = cleaned.get("posted_date") or None
        cleaned["metric_as_of"] = cleaned.get("metric_as_of") or None
        prepared.append(validate(cleaned))
    before_posts = db.execute("SELECT count(*) FROM x_posts").fetchone()[0]
    before_observations = db.execute("SELECT count(*) FROM x_observations").fetchone()[0]
    with db:
        for row in prepared:
            insert_observation(db, row)
    return (db.execute("SELECT count(*) FROM x_posts").fetchone()[0] - before_posts,
            db.execute("SELECT count(*) FROM x_observations").fetchone()[0] - before_observations)


def validate_material(item: dict) -> dict:
    required = ("source_url", "discovery_url", "source_kind", "discovered_at", "observation", "verification_status", "content_direction", "region", "rights_note", "review_after")
    missing = [key for key in required if not isinstance(item.get(key), str) or not item[key].strip()]
    if missing:
        raise ValueError(f"missing/empty material fields: {', '.join(missing)}")
    for field in ("source_url", "discovery_url"):
        parsed = urlparse(item[field])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"{field} must be an HTTPS URL")
        host = parsed.hostname.lower()
        if host == "redd.it" or host == "reddit.com" or host.endswith(".reddit.com"):
            raise ValueError("Reddit material import requires a separate rights decision")
    if item["verification_status"] not in {"UNVERIFIED", "SOURCE_CHECKED", "INDEPENDENTLY_CORROBORATED"}:
        raise ValueError("invalid material verification status")
    observed = datetime.fromisoformat(item["discovered_at"].replace("Z", "+00:00"))
    if observed.utcoffset() is None or observed.utcoffset().total_seconds() != 0:
        raise ValueError("discovered_at must be UTC")
    if item.get("published_at"):
        date.fromisoformat(item["published_at"])
    date.fromisoformat(item["review_after"])
    if len(item["observation"]) > 300:
        raise ValueError("material observation must be a short original summary")
    return item


def import_materials(db: sqlite3.Connection, path: Path) -> int:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("input must be a JSON array")
    validated = [validate_material(record) for record in records]
    before = db.execute("SELECT count(*) FROM materials").fetchone()[0]
    with db:
        for row in validated:
            db.execute("""INSERT OR IGNORE INTO materials
                (source_url,discovered_at,observation,verification_status,content_direction,discovery_url,source_kind,published_at,region,rights_note,review_after)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(row.get(key) for key in ("source_url", "discovered_at", "observation", "verification_status", "content_direction", "discovery_url", "source_kind", "published_at", "region", "rights_note", "review_after")))
    return db.execute("SELECT count(*) FROM materials").fetchone()[0] - before


def validate_feedback(item: dict) -> dict:
    for field in ("url", "published_at", "observed_at", "evidence_note"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(f"missing/empty feedback field: {field}")
    if item.get("human_reviewed") is not True:
        raise ValueError("own post must be human reviewed and manually published")
    url = urlparse(item["url"])
    match = POST_RE.fullmatch(url.path)
    if url.scheme != "https" or url.hostname not in {"x.com", "twitter.com"} or not match:
        raise ValueError("feedback URL must be an X status URL")
    timestamps = {}
    for field in ("published_at", "observed_at"):
        timestamp = datetime.fromisoformat(item[field].replace("Z", "+00:00"))
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError(f"{field} must be UTC")
        timestamps[field] = timestamp
    if timestamps["observed_at"] < timestamps["published_at"]:
        raise ValueError("feedback observation precedes publication")
    for metric in ("impressions", "likes", "replies", "reposts", "profile_visits", "new_follows"):
        value = item.get(metric)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{metric} must be a nonnegative integer or null")
    return {**item, "post_id": match.group(1)}


def import_feedback(db: sqlite3.Connection, path: Path) -> tuple[int, int]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("input must be a JSON array")
    validated = [validate_feedback(record) for record in records]
    before_posts = db.execute("SELECT count(*) FROM own_posts").fetchone()[0]
    before_metrics = db.execute("SELECT count(*) FROM own_post_observations").fetchone()[0]
    with db:
        for row in validated:
            db.execute("INSERT OR IGNORE INTO own_posts (post_id,url,published_at,review_status) VALUES (?,?,?,'PUBLISHED')",
                       (row["post_id"], row["url"], row["published_at"]))
            db.execute("""INSERT OR IGNORE INTO own_post_observations
                (post_id,observed_at,impressions,likes,replies,reposts,profile_visits,new_follows,evidence_note)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (row["post_id"], row["observed_at"], *(row.get(key) for key in ("impressions", "likes", "replies", "reposts", "profile_visits", "new_follows")), row["evidence_note"]))
    return (db.execute("SELECT count(*) FROM own_posts").fetchone()[0] - before_posts,
            db.execute("SELECT count(*) FROM own_post_observations").fetchone()[0] - before_metrics)


def packet(db: sqlite3.Connection) -> str:
    stats = report(db)
    lines = [
        "# X 内容研究任务包（探索阶段）",
        "",
        f"真实原帖链接：{stats['x_posts']}；高传播候选：{stats['high_candidates']}；普通候选：{stats['ordinary_candidates']}；作者：{stats['authors']}。",
        "全部 X 指标来自有滞后的公开搜索索引；当前没有经过验证的传播公式。请仅提出待证伪研究问题，不生成确定性增长承诺。",
        "",
        "## 素材线索（与 X 样本分离）",
    ]
    for url, observation, status, direction in db.execute("SELECT source_url,observation,verification_status,content_direction FROM materials ORDER BY discovered_at DESC, id DESC"):
        lines.extend((f"- 来源：{url}", f"  - 已知：{observation}（{status}）", f"  - 可研究方向：{direction}", "  - 创作前须独立核实主张、时效、语境和使用权。"))
    lines.extend(("", "## 交接要求", "", "区分事实、作者自述和推断；给出反例或证据缺口。不得翻译搬运原帖、虚构个人经历或自动发布。人工审核后才进入发布环节。"))
    return "\n".join(lines)


def logged_import(db: sqlite3.Connection, kind: str, path: Path) -> tuple[int, int]:
    started = datetime.now(timezone.utc).isoformat()
    try:
        if kind == "x":
            added_items, added_observations = import_file(db, path)
        elif kind == "materials":
            added_items, added_observations = import_materials(db, path), 0
        else:
            added_items, added_observations = import_feedback(db, path)
        status, error = "SUCCESS", None
    except (OSError, ValueError, sqlite3.Error) as exc:
        added_items, added_observations = 0, 0
        status, error = "FAILED", str(exc)[:500]
    db.execute("""INSERT INTO ingest_runs
        (kind,input_path,started_at,finished_at,added_items,added_observations,status,error,retries)
        VALUES (?,?,?,?,?,?,?,?,0)""",
        (kind, str(path), started, datetime.now(timezone.utc).isoformat(), added_items, added_observations, status, error))
    db.commit()
    if error:
        raise ValueError(error)
    return added_items, added_observations


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
        "materials": db.execute("SELECT count(*) FROM materials").fetchone()[0],
        "materials_needing_review": db.execute("SELECT count(*) FROM materials WHERE review_after <= ?", (datetime.now(timezone.utc).date().isoformat(),)).fetchone()[0],
        "own_posts": db.execute("SELECT count(*) FROM own_posts").fetchone()[0],
        "own_post_observations": db.execute("SELECT count(*) FROM own_post_observations").fetchone()[0],
        "ingest_runs": db.execute("SELECT count(*) FROM ingest_runs").fetchone()[0],
        "failed_ingest_runs": db.execute("SELECT count(*) FROM ingest_runs WHERE status='FAILED'").fetchone()[0],
        "indexed_metric_observations": db.execute("SELECT count(*) FROM x_observations WHERE method='public_search_index' AND views IS NOT NULL").fetchone()[0],
        "direct_metric_observations": db.execute("SELECT count(*) FROM x_observations WHERE method='direct_public_page' AND views IS NOT NULL").fetchone()[0],
        "quality": quality_report(db),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local X research evidence store")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    importer = sub.add_parser("import")
    importer.add_argument("file", type=Path)
    csv_importer = sub.add_parser("import-csv")
    csv_importer.add_argument("file", type=Path)
    material_importer = sub.add_parser("import-materials")
    material_importer.add_argument("file", type=Path)
    feedback_importer = sub.add_parser("import-feedback")
    feedback_importer.add_argument("file", type=Path)
    query_importer = sub.add_parser("import-queries")
    query_importer.add_argument("file", type=Path)
    review_importer = sub.add_parser("import-review")
    review_importer.add_argument("file", type=Path)
    annotation_importer = sub.add_parser("import-annotations")
    annotation_importer.add_argument("file", type=Path)
    pair_importer = sub.add_parser("import-pairs")
    pair_importer.add_argument("file", type=Path)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--port", type=int, default=8765)
    packet_parser = sub.add_parser("research-packet")
    packet_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    sub.add_parser("report")
    sub.add_parser("audit")
    gate_parser = sub.add_parser("editorial-gate")
    gate_parser.add_argument("file", type=Path)
    reader_importer = sub.add_parser("import-reader-annotations")
    reader_importer.add_argument("file", type=Path)
    reader_parser = sub.add_parser("reader-packet")
    reader_parser.add_argument("--kind", choices=("external", "own", "material", "candidate"))
    reader_parser.add_argument("--model-version", choices=(reader_model.MODEL_VERSION, reader_model.VALUE_MODEL_VERSION))
    reviewer = sub.add_parser("reader-review")
    reviewer.add_argument("file", type=Path)
    tester = sub.add_parser("reader-backtest")
    tester.add_argument("annotations", type=Path)
    tester.add_argument("feedback", type=Path)
    tester.add_argument("--window", choices=tuple(reader_model.WINDOWS))
    tester.add_argument("--output", required=True, type=Path)
    comments = sub.add_parser("reader-comments")
    comments.add_argument("file", type=Path)
    comments.add_argument("--experiment", type=Path)
    comments.add_argument("--output", required=True, type=Path)
    sub.add_parser("packet")
    args = parser.parse_args()
    if args.command in {"reader-review", "reader-backtest", "reader-comments"}:
        try:
            if args.command == "reader-backtest":
                # Account metrics must never be written to a public artifact.
                private_root = Path("data/private").resolve()
                if not args.output.resolve().is_relative_to(private_root):
                    raise ValueError("backtest output must be under ignored data/private/")
                annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
                for row in annotations:
                    reader_model.validate_annotation(row)
                result = reader_model.backtest(annotations, json.loads(args.feedback.read_text(encoding="utf-8")), window=args.window)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps({"n": result["n"], "learning_eligible": result["learning_eligible_observations"], "output": str(args.output)}))
            else:
                records = json.loads(args.file.read_text(encoding="utf-8"))
                if not isinstance(records, list):
                    raise ValueError("reader input must be an array")
                if args.command == "reader-comments":
                    if not args.output.resolve().is_relative_to(Path("data/private").resolve()):
                        raise ValueError("raw comments output must stay under ignored data/private/")
                    prediction = json.loads(args.experiment.read_text(encoding="utf-8")) if args.experiment else None
                    result = [reader_model.validate_comment(row, prediction=prediction) for row in records]
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps({"comments_saved": len(result), "output": str(args.output)}))
                else:
                    result = [{"entity_id": r.get("entity_id", r.get("candidate_id")),
                               "review": reader_model.review_profile(r.get("reader_model"), r.get("primary_action", r.get("review_primary_action")))} for r in records]
                    print(json.dumps(result, ensure_ascii=False, indent=2))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            parser.exit(1, f"reader review failed: {exc}\n")
        return
    if args.command == "editorial-gate":
        try:
            records = json.loads(args.file.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise ValueError("editorial gate input must be a JSON array")
            results = []
            for record in records:
                result = validate_candidate(record)
                results.append({"candidate_id": record.get("candidate_id"), "ready": result.ready, "state": result.state, "reasons": list(result.reasons),
                                "reader_review": reader_model.review_profile(record.get("reader_model"), record.get("primary_action"))})
            print(json.dumps(results, ensure_ascii=False, indent=2))
            if any(not item["ready"] for item in results):
                raise SystemExit(1)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.exit(1, f"editorial gate failed: {exc}\n")
        return
    if args.command == "capture":
        from .capture import serve
        serve(args.db, args.port)
        return
    with closing(connect(args.db)) as db:
        if args.command == "init":
            print(f"initialized {args.db}")
        elif args.command == "import-reader-annotations":
            try:
                added = reader_model.import_annotations(db, args.file)
            except (OSError, ValueError, sqlite3.Error) as exc:
                parser.exit(1, f"reader import failed: {exc}\n")
            print(json.dumps({"added_reader_annotations": added}))
        elif args.command == "reader-packet":
            records = reader_model.reader_packet(db, args.kind)
            if args.model_version:
                records = [r for r in records if r["reader_model"]["model_version"] == args.model_version]
            print(json.dumps(records, ensure_ascii=False, indent=2))
        elif args.command == "import":
            try:
                posts, observations = logged_import(db, "x", args.file)
            except ValueError as exc:
                parser.exit(1, f"import failed: {exc}\n")
            print(json.dumps({"new_posts": posts, "new_observations": observations}, ensure_ascii=False))
        elif args.command == "import-csv":
            try:
                posts, observations = import_csv(db, args.file)
            except (OSError, ValueError, sqlite3.Error) as exc:
                parser.exit(1, f"CSV import failed: {exc}\n")
            print(json.dumps({"new_posts": posts, "new_observations": observations}, ensure_ascii=False))
        elif args.command == "import-materials":
            try:
                materials, _ = logged_import(db, "materials", args.file)
            except ValueError as exc:
                parser.exit(1, f"import failed: {exc}\n")
            print(json.dumps({"new_materials": materials}, ensure_ascii=False))
        elif args.command == "import-feedback":
            try:
                posts, observations = logged_import(db, "feedback", args.file)
            except ValueError as exc:
                parser.exit(1, f"import failed: {exc}\n")
            print(json.dumps({"new_own_posts": posts, "new_feedback_observations": observations}, ensure_ascii=False))
        elif args.command == "import-queries":
            try:
                added = import_queries(db, args.file)
            except (OSError, ValueError, sqlite3.Error) as exc:
                parser.exit(1, f"query import failed: {exc}\n")
            print(json.dumps({"new_query_runs": added}))
        elif args.command == "import-review":
            try:
                added = import_research_review(db, args.file)
            except (OSError, ValueError, sqlite3.Error) as exc:
                parser.exit(1, f"review import failed: {exc}\n")
            print(json.dumps({"reviewed_hypotheses": added}))
        elif args.command in {"import-annotations", "import-pairs"}:
            try:
                added = (import_annotations if args.command == "import-annotations" else import_pairs)(db, args.file)
            except (OSError, ValueError, sqlite3.Error) as exc:
                parser.exit(1, f"research import failed: {exc}\n")
            print(json.dumps({"added_records": added}))
        elif args.command == "research-packet":
            research = research_packet(db)
            reader_annotations = reader_model.reader_packet(db)
            research["reader_model_annotations"] = reader_annotations
            print(json.dumps(research, ensure_ascii=False, indent=2) if args.format == "json" else
                  packet_markdown(research) + f"\n\n读者模型派生标注：{len(reader_annotations)}条；使用 reader-packet 导出完整字段。全部为HYPOTHESIS，不覆盖原证据或原有研究结论。")
        elif args.command == "packet":
            print(packet(db))
        elif args.command == "report":
            print(json.dumps(report(db), ensure_ascii=False, indent=2))
        else:
            stats = report(db)
            issues = []
            if stats["x_posts"] < 450:
                issues.append("Below exploratory collection targets; no formula validation")
            if stats["indexed_metric_observations"] and not stats["direct_metric_observations"]:
                issues.append("All available X view counts come from stale search-index snapshots")
            if stats["unknown_followers"]:
                issues.append("Author follower counts unknown; reach cannot be normalized")
            if stats["ordinary_candidates"] == 0:
                issues.append("No ordinary-post controls")
            print(json.dumps({"stats": stats, "issues": issues}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
