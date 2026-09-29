"""Phase-two schema upgrades and evidence quality rules."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone


OBSERVATION_FIELDS = (
    "post_id", "observed_at", "source_url", "method", "discovery_query",
    "evidence_note", "views", "likes", "reposts", "quotes", "replies", "followers",
    "metric_as_of", "evidence_ref", "metric_source", "context_note", "views_precision",
)


def views_precision(record: dict) -> str:
    if record.get("views_precision"):
        return record["views_precision"]
    if record.get("views") is None:
        return "UNKNOWN"
    return "APPROXIMATE" if "rounded" in record.get("evidence_note", "").lower() else "EXACT_DISPLAYED"


def fingerprint(record: dict) -> str:
    payload = {key: record.get(key) for key in OBSERVATION_FIELDS}
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def migrate(db: sqlite3.Connection) -> None:
    post_columns = {row[1] for row in db.execute("PRAGMA table_info(x_posts)")}
    additions = {
        "verification_status": "TEXT NOT NULL DEFAULT 'DISCOVERED'",
        "post_type": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        "promotion_status": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        "media_type": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
        "cohort_basis": "TEXT",
        "audience": "TEXT",
        "context_note": "TEXT",
        "fact_check_status": "TEXT NOT NULL DEFAULT 'UNVERIFIED'",
    }
    with db:
        for name, definition in additions.items():
            if name not in post_columns:
                db.execute(f"ALTER TABLE x_posts ADD COLUMN {name} {definition}")

    observation_columns = {row[1] for row in db.execute("PRAGMA table_info(x_observations)")}
    if "fingerprint" not in observation_columns:
        old_rows = list(db.execute("SELECT * FROM x_observations ORDER BY id"))
        names = [row[1] for row in db.execute("PRAGMA table_info(x_observations)")]
        with db:
            db.execute("ALTER TABLE x_observations RENAME TO x_observations_legacy")
            db.execute("""CREATE TABLE x_observations (
                id INTEGER PRIMARY KEY,
                post_id TEXT NOT NULL REFERENCES x_posts(post_id),
                observed_at TEXT NOT NULL,
                source_url TEXT NOT NULL,
                method TEXT NOT NULL,
                discovery_query TEXT NOT NULL,
                evidence_note TEXT NOT NULL,
                views INTEGER, likes INTEGER, reposts INTEGER, quotes INTEGER, replies INTEGER, followers INTEGER,
                metric_as_of TEXT,
                evidence_ref TEXT NOT NULL,
                metric_source TEXT NOT NULL,
                context_note TEXT,
                views_precision TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE
            )""")
            for values in old_rows:
                old = dict(zip(names, values))
                source = "SEARCH_INDEX" if old["method"] == "public_search_index" else "UNKNOWN"
                record = {**old, "metric_as_of": None, "evidence_ref": old["source_url"],
                          "metric_source": source, "context_note": None}
                record["views_precision"] = views_precision(record)
                columns = ("id",) + OBSERVATION_FIELDS + ("fingerprint",)
                db.execute(
                    f"INSERT INTO x_observations ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                    (old["id"], *(record.get(key) for key in OBSERVATION_FIELDS), fingerprint(record)),
                )
            db.execute("DROP TABLE x_observations_legacy")
            db.execute("""UPDATE x_posts SET verification_status='ORIGINAL_CONFIRMED'
                WHERE post_id IN (SELECT post_id FROM x_observations WHERE method='direct_public_page')""")

    observation_columns = {row[1] for row in db.execute("PRAGMA table_info(x_observations)")}
    if "views_precision" not in observation_columns:
        with db:
            db.execute("ALTER TABLE x_observations ADD COLUMN views_precision TEXT NOT NULL DEFAULT 'UNKNOWN'")
            for values in db.execute("SELECT * FROM x_observations").fetchall():
                names = [row[1] for row in db.execute("PRAGMA table_info(x_observations)")]
                record = dict(zip(names, values))
                record["views_precision"] = views_precision({**record, "views_precision": None})
                db.execute("UPDATE x_observations SET views_precision=?,fingerprint=? WHERE id=?",
                           (record["views_precision"], fingerprint(record), record["id"]))

    db.executescript("""
    CREATE TABLE IF NOT EXISTS discovery_queries (
      id TEXT PRIMARY KEY,
      channel TEXT NOT NULL,
      query_text TEXT NOT NULL,
      executed_at TEXT NOT NULL,
      duration_seconds REAL,
      visible_results INTEGER NOT NULL,
      candidate_urls INTEGER NOT NULL,
      admitted INTEGER NOT NULL,
      duplicates INTEGER NOT NULL,
      rejected INTEGER NOT NULL,
      metric_candidates INTEGER NOT NULL,
      result_post_ids TEXT NOT NULL,
      permission_status TEXT NOT NULL,
      failure_reason TEXT,
      evidence_ref TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS comparison_pairs (
      id TEXT PRIMARY KEY,
      candidate_post_id TEXT NOT NULL REFERENCES x_posts(post_id),
      control_post_id TEXT NOT NULL REFERENCES x_posts(post_id),
      matching_basis TEXT NOT NULL,
      differences TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('EXPLORATORY','READY','REJECTED')),
      created_at TEXT NOT NULL,
      UNIQUE(candidate_post_id, control_post_id)
    );
    CREATE TABLE IF NOT EXISTS research_annotations (
      id INTEGER PRIMARY KEY,
      post_id TEXT NOT NULL REFERENCES x_posts(post_id),
      version INTEGER NOT NULL,
      labeled_at TEXT NOT NULL,
      researcher TEXT NOT NULL,
      audience TEXT,
      opening_motive TEXT,
      expectation_relation TEXT,
      narrative_structure TEXT,
      concrete_evidence TEXT,
      practical_value TEXT,
      emotion TEXT,
      discussion_motive TEXT,
      confounders TEXT,
      counterexample_note TEXT,
      uncertainty TEXT,
      UNIQUE(post_id, version)
    );
    CREATE TABLE IF NOT EXISTS research_reviews (
      id TEXT PRIMARY KEY,
      imported_at TEXT NOT NULL,
      question TEXT NOT NULL,
      hypothesis TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status='HYPOTHESIS'),
      evidence_post_ids TEXT NOT NULL,
      counterexample_post_ids TEXT NOT NULL,
      limitations TEXT NOT NULL,
      reviewer_note TEXT NOT NULL,
      version INTEGER NOT NULL
    );
    PRAGMA user_version = 3;
    """)


def insert_observation(db: sqlite3.Connection, row: dict) -> tuple[int, int]:
    existing = db.execute("SELECT 1 FROM x_posts WHERE post_id=?", (row["post_id"],)).fetchone()
    db.execute("""INSERT INTO x_posts
        (post_id,url,author_handle,posted_date,topic,excerpt,cohort,first_seen_at,last_seen_at,
         verification_status,post_type,promotion_status,media_type,cohort_basis,audience,context_note,fact_check_status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(post_id) DO UPDATE SET
          last_seen_at=max(x_posts.last_seen_at,excluded.last_seen_at),
          verification_status=CASE WHEN excluded.verification_status='ORIGINAL_CONFIRMED'
            THEN 'ORIGINAL_CONFIRMED' ELSE x_posts.verification_status END,
          excerpt=CASE WHEN x_posts.excerpt='' THEN excluded.excerpt ELSE x_posts.excerpt END,
          topic=CASE WHEN x_posts.topic='UNCLASSIFIED' THEN excluded.topic ELSE x_posts.topic END,
          posted_date=coalesce(x_posts.posted_date,excluded.posted_date),
          post_type=CASE WHEN excluded.post_type!='UNKNOWN' THEN excluded.post_type ELSE x_posts.post_type END,
          promotion_status=CASE WHEN excluded.promotion_status!='UNKNOWN' THEN excluded.promotion_status ELSE x_posts.promotion_status END,
          media_type=CASE WHEN excluded.media_type!='UNKNOWN' THEN excluded.media_type ELSE x_posts.media_type END,
          cohort=CASE WHEN excluded.cohort_basis IS NOT NULL AND excluded.cohort!='unclassified'
            THEN excluded.cohort ELSE x_posts.cohort END,
          cohort_basis=coalesce(excluded.cohort_basis,x_posts.cohort_basis),
          audience=coalesce(excluded.audience,x_posts.audience),
          context_note=coalesce(excluded.context_note,x_posts.context_note),
          fact_check_status=CASE WHEN excluded.fact_check_status!='UNVERIFIED'
            THEN excluded.fact_check_status ELSE x_posts.fact_check_status END""",
        (row["post_id"], row["url"], row["author_handle"], row.get("posted_date"),
         row.get("topic", "UNCLASSIFIED"), row.get("excerpt", ""), row.get("cohort", "unclassified"),
         row["observed_at"], row["observed_at"], row.get("verification_status", "DISCOVERED"),
         row.get("post_type", "UNKNOWN"), row.get("promotion_status", "UNKNOWN"),
         row.get("media_type", "UNKNOWN"), row.get("cohort_basis"), row.get("audience"),
         row.get("context_note"), row.get("fact_check_status", "UNVERIFIED")))
    metric_source = row.get("metric_source") or ("SEARCH_INDEX" if row["method"] == "public_search_index" else "UNKNOWN")
    observation = {**row, "metric_as_of": row.get("metric_as_of"),
                   "evidence_ref": row.get("evidence_ref") or row["source_url"],
                   "metric_source": metric_source, "context_note": row.get("context_note"),
                   "views_precision": views_precision(row)}
    digest = fingerprint(observation)
    cursor = db.execute(
        f"INSERT OR IGNORE INTO x_observations ({','.join(OBSERVATION_FIELDS)},fingerprint) "
        f"VALUES ({','.join('?' for _ in range(len(OBSERVATION_FIELDS) + 1))})",
        (*(observation.get(key) for key in OBSERVATION_FIELDS), digest),
    )
    return (0 if existing else 1, cursor.rowcount)


def quality_report(db: sqlite3.Connection) -> dict:
    count = lambda sql: db.execute(sql).fetchone()[0]
    return {
        "discovered_posts": count("SELECT count(*) FROM x_posts"),
        "original_confirmed": count("SELECT count(*) FROM x_posts WHERE verification_status='ORIGINAL_CONFIRMED'"),
        "posts_with_any_views": count("SELECT count(DISTINCT post_id) FROM x_observations WHERE views IS NOT NULL"),
        "posts_with_exact_index_views": count("SELECT count(DISTINCT post_id) FROM x_observations WHERE metric_source='SEARCH_INDEX' AND views IS NOT NULL AND views_precision='EXACT_DISPLAYED'"),
        "posts_with_approximate_index_views": count("SELECT count(DISTINCT post_id) FROM x_observations WHERE metric_source='SEARCH_INDEX' AND views IS NOT NULL AND views_precision='APPROXIMATE'"),
        "posts_with_dated_metrics": count("SELECT count(DISTINCT post_id) FROM x_observations WHERE views IS NOT NULL AND metric_as_of IS NOT NULL AND metric_source IN ('PUBLIC_X_PAGE','USER_SCREENSHOT')"),
        "provisional_high": count("SELECT count(*) FROM x_posts WHERE cohort='high_candidate'"),
        "provisional_ordinary": count("SELECT count(*) FROM x_posts WHERE cohort='ordinary_candidate'"),
        "cohorts_with_relative_basis": count("SELECT count(*) FROM x_posts WHERE cohort!='unclassified' AND cohort_basis IS NOT NULL"),
        "exploratory_pairs": count("SELECT count(*) FROM comparison_pairs WHERE status='EXPLORATORY'"),
        "ready_pairs": count("SELECT count(*) FROM comparison_pairs WHERE status='READY'"),
        "conflicting_observation_groups": count("""SELECT count(*) FROM (
            SELECT post_id, observed_at, source_url FROM x_observations
            GROUP BY post_id, observed_at, source_url HAVING count(*) > 1)"""),
        "query_runs": count("SELECT count(*) FROM discovery_queries"),
        "annotations": count("SELECT count(*) FROM research_annotations"),
        "reviewed_hypotheses": count("SELECT count(*) FROM research_reviews"),
    }


def record_query(db: sqlite3.Connection, row: dict) -> bool:
    counts = ("visible_results", "candidate_urls", "admitted", "duplicates", "rejected", "metric_candidates")
    if any(type(row.get(key)) is not int or row[key] < 0 for key in counts):
        raise ValueError("query counts must be nonnegative integers")
    if row["admitted"] + row["duplicates"] + row["rejected"] != row["candidate_urls"]:
        raise ValueError("query disposition counts must sum to candidate URLs")
    if row["candidate_urls"] > row["visible_results"]:
        raise ValueError("candidate URLs cannot exceed visible results")
    if row["permission_status"] not in {"ALLOWED_PUBLIC_SEARCH", "MANUAL_ONLY", "BLOCKED"}:
        raise ValueError("invalid permission status")
    if not isinstance(row["result_post_ids"], list) or len(set(row["result_post_ids"])) != len(row["result_post_ids"]):
        raise ValueError("result_post_ids must be a unique list")
    columns = ("id", "channel", "query_text", "executed_at", "duration_seconds", *counts,
               "result_post_ids", "permission_status", "failure_reason", "evidence_ref")
    values = {**row, "result_post_ids": json.dumps(row["result_post_ids"])}
    cursor = db.execute(
        f"INSERT OR IGNORE INTO discovery_queries ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        tuple(values.get(key) for key in columns),
    )
    return bool(cursor.rowcount)


def import_queries(db: sqlite3.Connection, path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("query input must be a JSON array")
    required = ("id", "channel", "query_text", "executed_at", "evidence_ref", "permission_status")
    for row in rows:
        if any(not isinstance(row.get(key), str) or not row[key] for key in required):
            raise ValueError("query record missing provenance")
    with db:
        return sum(record_query(db, row) for row in rows)


def import_research_review(db: sqlite3.Connection, path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("review input must be a JSON array")
    for row in rows:
        if row.get("human_reviewed") is not True or row.get("status") != "HYPOTHESIS":
            raise ValueError("research claims require human review and HYPOTHESIS status")
        if not all(isinstance(row.get(key), str) and row[key].strip() for key in
                   ("id", "question", "hypothesis", "limitations", "reviewer_note")):
            raise ValueError("review lacks question, evidence limits, or rationale")
        for key in ("evidence_post_ids", "counterexample_post_ids"):
            if not isinstance(row.get(key), list):
                raise ValueError(f"{key} must be a list")
        for post_id in row["evidence_post_ids"] + row["counterexample_post_ids"]:
            if not db.execute("SELECT 1 FROM x_posts WHERE post_id=?", (post_id,)).fetchone():
                raise ValueError(f"unknown evidence post: {post_id}")
    with db:
        added = 0
        for row in rows:
            prefix = f"{row['id']}:v"
            version = db.execute("SELECT coalesce(max(version),0)+1 FROM research_reviews WHERE substr(id,1,?)=?",
                                 (len(prefix), prefix)).fetchone()[0]
            review_id = f"{row['id']}:v{version}"
            db.execute("""INSERT INTO research_reviews
                (id,imported_at,question,hypothesis,status,evidence_post_ids,counterexample_post_ids,limitations,reviewer_note,version)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (review_id, datetime.now(timezone.utc).isoformat(), row["question"], row["hypothesis"],
                 "HYPOTHESIS", json.dumps(row["evidence_post_ids"]), json.dumps(row["counterexample_post_ids"]),
                 row["limitations"], row["reviewer_note"], version))
            added += 1
    return added


ANNOTATION_FIELDS = ("audience", "opening_motive", "expectation_relation", "narrative_structure",
                     "concrete_evidence", "practical_value", "emotion", "discussion_motive",
                     "confounders", "counterexample_note", "uncertainty")


def import_annotations(db: sqlite3.Connection, path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("annotation input must be a JSON array")
    for row in rows:
        if row.get("human_reviewed") is not True or not row.get("researcher"):
            raise ValueError("annotation requires researcher and human review")
        if not db.execute("SELECT 1 FROM x_posts WHERE post_id=?", (row.get("post_id"),)).fetchone():
            raise ValueError("annotation references unknown post")
        if any(value is not None and not isinstance(value, str) for value in (row.get(k) for k in ANNOTATION_FIELDS)):
            raise ValueError("annotation fields must be text")
    with db:
        for row in rows:
            version = db.execute("SELECT coalesce(max(version),0)+1 FROM research_annotations WHERE post_id=?", (row["post_id"],)).fetchone()[0]
            db.execute(
                f"INSERT INTO research_annotations (post_id,version,labeled_at,researcher,{','.join(ANNOTATION_FIELDS)}) "
                f"VALUES ({','.join('?' for _ in range(4 + len(ANNOTATION_FIELDS)))})",
                (row["post_id"], version, datetime.now(timezone.utc).isoformat(), row["researcher"],
                 *(row.get(k) for k in ANNOTATION_FIELDS)),
            )
    return len(rows)


def import_pairs(db: sqlite3.Connection, path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("pair input must be a JSON array")
    for row in rows:
        if row.get("status") not in {"EXPLORATORY", "READY", "REJECTED"}:
            raise ValueError("invalid pair status")
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in
                   ("id", "candidate_post_id", "control_post_id", "matching_basis", "differences")):
            raise ValueError("pair lacks identifiers or comparison rationale")
        if row["candidate_post_id"] == row["control_post_id"]:
            raise ValueError("self comparison is invalid")
        posts = db.execute("""SELECT post_id,verification_status,cohort_basis FROM x_posts
            WHERE post_id IN (?,?)""", (row["candidate_post_id"], row["control_post_id"])).fetchall()
        if len(posts) != 2:
            raise ValueError("pair references unknown post")
        if row["status"] == "READY":
            if any(status != "ORIGINAL_CONFIRMED" or not basis for _, status, basis in posts):
                raise ValueError("ready pair requires verified originals and relative baselines")
            for post_id, _, _ in posts:
                if not db.execute("""SELECT 1 FROM x_observations WHERE post_id=? AND views IS NOT NULL
                    AND metric_as_of IS NOT NULL AND metric_source IN ('PUBLIC_X_PAGE','USER_SCREENSHOT')""", (post_id,)).fetchone():
                    raise ValueError("ready pair requires dated non-index view evidence for both posts")
    with db:
        for row in rows:
            db.execute("""INSERT INTO comparison_pairs
                (id,candidate_post_id,control_post_id,matching_basis,differences,status,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (row["id"], row["candidate_post_id"], row["control_post_id"], row["matching_basis"],
                 row["differences"], row["status"], datetime.now(timezone.utc).isoformat()))
    return len(rows)


def research_packet(db: sqlite3.Connection) -> dict:
    posts = []
    for post in db.execute("""SELECT post_id,url,author_handle,posted_date,topic,excerpt,cohort,
        verification_status,post_type,promotion_status,media_type,cohort_basis,context_note
        FROM x_posts ORDER BY first_seen_at,post_id"""):
        keys = ("post_id", "url", "author", "posted_date", "topic", "excerpt", "cohort",
                "verification_status", "post_type", "promotion_status", "media_type", "cohort_basis", "context_note")
        item = dict(zip(keys, post))
        item["observations"] = [dict(zip(
            ("observed_at", "metric_as_of", "views", "views_precision", "likes", "reposts", "quotes", "replies", "followers",
             "method", "metric_source", "source_url", "evidence_ref", "evidence_note"), row)) for row in db.execute(
                """SELECT observed_at,metric_as_of,views,views_precision,likes,reposts,quotes,replies,followers,
                method,metric_source,source_url,evidence_ref,evidence_note FROM x_observations
                WHERE post_id=? ORDER BY observed_at""", (item["post_id"],))]
        posts.append(item)
    pairs = [dict(zip(("candidate", "control", "matching_basis", "differences", "status"), row))
             for row in db.execute("SELECT candidate_post_id,control_post_id,matching_basis,differences,status FROM comparison_pairs")]
    annotations = [dict(zip(("post_id", "version", "audience", "opening_motive", "expectation_relation",
                             "narrative_structure", "concrete_evidence", "practical_value", "emotion",
                             "discussion_motive", "confounders", "counterexample_note", "uncertainty"), row))
                   for row in db.execute("""SELECT post_id,version,audience,opening_motive,expectation_relation,
                       narrative_structure,concrete_evidence,practical_value,emotion,discussion_motive,confounders,
                       counterexample_note,uncertainty FROM research_annotations ORDER BY post_id,version""")]
    reviews = [dict(zip(("id", "question", "hypothesis", "status", "evidence_post_ids",
                         "counterexample_post_ids", "limitations", "reviewer_note"), row))
               for row in db.execute("""SELECT id,question,hypothesis,status,evidence_post_ids,
                   counterexample_post_ids,limitations,reviewer_note FROM research_reviews ORDER BY imported_at""")]
    return {
        "question": "哪些结构差异与简中 X 原帖传播表现有关，且在控制作者、主题、形式和观察时间后仍可复现？",
        "quality": quality_report(db), "analysis_ready_post_ids": sorted({post_id for pair in pairs if pair["status"] == "READY"
                                                                      for post_id in (pair["candidate"], pair["control"])}),
        "posts": posts, "comparison_pairs": pairs,
        "annotations": annotations, "hypotheses": reviews,
        "limitations": ["搜索索引指标属于未定时的历史快照", "候选标签并非相对基线分类",
                        "无 READY 对照对时不得做传播机制效果判断", "需保留独立作者及时间留出样本"],
        "instruction": "区分观察、作者自述与推断；寻找反例，只输出待验证假设。人工审核后才可导入。",
    }


def packet_markdown(packet: dict) -> str:
    lines = ["# X 传播机制研究任务包", "", "## 研究问题", packet["question"], "",
             "## 数据质量", "", f"```json\n{json.dumps(packet['quality'], ensure_ascii=False, indent=2)}\n```", "",
             "## 候选链接与证据（不等于可分析样本）", "",
             f"可分析帖子 ID：{', '.join(packet['analysis_ready_post_ids']) or '无'}", ""]
    for post in packet["posts"]:
        lines += [f"### {post['author']} · {post['post_id']}", post["url"],
                  f"主题：{post['topic']}；发布时间：{post['posted_date'] or '未知'}；状态：{post['verification_status']}；候选类：{post['cohort']}；相对基线：{post['cohort_basis'] or '无'}。",
                  f"摘录：{post['excerpt']}"]
        for obs in post["observations"]:
            displayed = ('约 ' if obs['views_precision'] == 'APPROXIMATE' else '') + (str(obs['views']) if obs['views'] is not None else '未知')
            lines.append(f"- 观察 {obs['observed_at']}；指标所属 {obs['metric_as_of'] or '未知'}；浏览 {displayed}；来源 {obs['metric_source']}；证据 {obs['evidence_ref']}；备注 {obs['evidence_note']}")
        lines.append("")
    lines += ["## 对照关系", ""]
    lines += [f"- {p['candidate']} / {p['control']}：{p['status']}；依据 {p['matching_basis']}；差异 {p['differences']}" for p in packet["comparison_pairs"]] or ["暂无合格对照关系。"]
    lines += ["", "## 结构标注与反例", ""]
    lines += [f"- {a['post_id']} v{a['version']}：开头 {a['opening_motive'] or '未标注'}；结构 {a['narrative_structure'] or '未标注'}；反例 {a['counterexample_note'] or '未标注'}；不确定性 {a['uncertainty'] or '未标注'}" for a in packet["annotations"]] or ["暂无完成的结构标注。"]
    lines += ["", "## 待验证假设", ""]
    lines += [f"- {h['hypothesis']}；限制 {h['limitations']}" for h in packet["hypotheses"]] or ["暂无经人工审核的假设。"]
    lines += ["", "## 局限与交接要求", ""] + [f"- {v}" for v in packet["limitations"]]
    lines += ["", packet["instruction"]]
    return "\n".join(lines) + "\n"
