"""Small dual-track queue. Python never clicks X; an agent owns the UI lease.

All mutable state and candidate research stay ignored locally. A lease holds the
same OS flock across separate Computer Use calls. No lease timeout can authorize
a second submit: abandoned in-flight attempts become UNKNOWN on recovery.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import fcntl
import json
from pathlib import Path
import re
import sqlite3
import sys
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from .handoff import ACCOUNT, verify_ready, verify_receipt, text_hash

UTC = timezone.utc
SHANGHAI = timezone(timedelta(hours=8))
DB = "state/publication.sqlite3"


def now():
    return datetime.now(UTC)


def stamp(t=None):
    return (t or now()).astimezone(SHANGHAI).isoformat()


def instant(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timezone required")
    return d.astimezone(UTC)


def canonical_text(s):
    s = re.sub(r"https?://\S+", "", unicodedata.normalize("NFKC", s).lower())
    return re.sub(r"[^\w\u4e00-\u9fff]", "", s)


def event_url(s):
    p = urlsplit(s)
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", ""))


def connect(path=DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=5, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.executescript('''
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=FULL;
    CREATE TABLE IF NOT EXISTS posts(
      id TEXT PRIMARY KEY, track TEXT NOT NULL, hash TEXT NOT NULL,
      event_key TEXT, normalized TEXT NOT NULL, payload TEXT NOT NULL,
      scheduled_at TEXT NOT NULL, created_at TEXT NOT NULL,
      status TEXT NOT NULL, actual_at TEXT, url TEXT, reason TEXT,
      evidence TEXT, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS runs(
      slot TEXT PRIMARY KEY, observed_at TEXT NOT NULL, status TEXT, reason TEXT);
    CREATE TABLE IF NOT EXISTS audit(
      seq INTEGER PRIMARY KEY, at TEXT, id TEXT, action TEXT, detail TEXT);
    ''')
    return c


@contextmanager
def transaction(c):
    c.execute("BEGIN IMMEDIATE")
    try:
        yield
        c.commit()
    except BaseException:
        c.rollback()
        raise


def audit(c, post_id, action, detail=""):
    c.execute("INSERT INTO audit(at,id,action,detail) VALUES(?,?,?,?)",
              (stamp(), post_id, action, detail))


def duplicate(c, p):
    normalized = canonical_text(p["text"])
    urls = {event_url(s) for s in p.get("source_urls", [])}
    for row in c.execute("SELECT * FROM posts"):
        if row["id"] == p["post_id"]:
            return "SAME_ID" if row["hash"] == p["content_sha256"] else "IMMUTABLE_ID_CHANGED"
        old = json.loads(row["payload"])
        if row["hash"] == p["content_sha256"]:
            return "EXACT_TEXT:" + row["id"]
        if p.get("event_key") and row["event_key"] == p["event_key"]:
            return "SAME_EVENT:" + row["id"]
        if urls & {event_url(s) for s in old.get("source_urls", [])}:
            return "SAME_SOURCE_EVENT:" + row["id"]
        if normalized and row["normalized"] and SequenceMatcher(
                None, normalized, row["normalized"], autojunk=False).ratio() >= .86:
            return "SIMILAR_TEXT:" + row["id"]
    return None


def enqueue(c, p, *, at=None, receipt=None):
    report = verify_ready(p)
    if not report["valid"]:
        return {"status": "REJECTED", "errors": report["errors"]}
    at = at or now()
    if receipt is not None and not verify_receipt(p, receipt)["valid"]:
        return {"status": "REJECTED", "errors": ["INVALID_EXISTING_RECEIPT"]}
    if p.get("track", "B") == "A" and instant(p["expires_at"]) <= at and receipt is None:
        return {"status": "EXPIRED"}
    with transaction(c):
        reason = duplicate(c, p)
        if reason:
            audit(c, p["post_id"], "DUPLICATE", reason)
            return {"status": "UNCHANGED" if reason == "SAME_ID" else "DUPLICATE", "reason": reason}
        scheduled = stamp(instant(p.get("scheduled_at") or p["created_at"]))
        status = "PUBLISHED" if receipt else "QUEUED"
        c.execute("INSERT INTO posts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            p["post_id"], p.get("track", "B"), p["content_sha256"], p.get("event_key"),
            canonical_text(p["text"]), json.dumps(p, ensure_ascii=False), scheduled,
            p["created_at"], status, receipt.get("published_at", receipt["verified_at"]) if receipt else None,
            receipt["url"] if receipt else None, None,
            json.dumps(receipt, ensure_ascii=False) if receipt else None, stamp(at)))
        audit(c, p["post_id"], status)
    return {"id": p["post_id"], "status": status}


def ingest(c, root="outbox", *, at=None):
    root = Path(root)
    results = []
    for row in c.execute("SELECT id,hash FROM posts WHERE status='QUEUED'").fetchall():
        source = root / 'ready' / (row['id'] + '.json')
        try:
            p = json.loads(source.read_text())
            valid = (verify_ready(p, filename=source.name)['valid']
                     and p['content_sha256'] == row['hash']
                     and not (root / 'rejected' / source.name).exists())
        except (OSError, ValueError):
            valid = False
        if not valid:
            c.execute("UPDATE posts SET status='BLOCKED',reason='REVOKED_REMOVED_OR_CHANGED',updated_at=? WHERE id=?", (stamp(at), row['id']))
            audit(c, row['id'], 'BLOCKED', 'REVOKED_REMOVED_OR_CHANGED')
    for file in sorted((root / "ready").glob("*.json")):
        try:
            p = json.loads(file.read_text())
            review = verify_ready(p, filename=file.name)
            if not review["valid"]:
                results.append({"file": str(file), "status": "REJECTED", "errors": review["errors"]})
                continue
            # Rejected/revoked IDs are a permanent denylist, not queue candidates.
            if (root / "rejected" / file.name).exists():
                raise ValueError("REVOKED_ID")
            rf = root / "receipts" / file.name
            receipt = json.loads(rf.read_text()) if rf.exists() else None
            results.append(enqueue(c, p, at=at, receipt=receipt))
        except (OSError, ValueError) as exc:
            results.append({"file": str(file), "status": "REJECTED", "reason": str(exc)[:180]})
    return results


@contextmanager
def browser_lock(db=DB):
    lock = Path(db).resolve().parent / "browser.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("BROWSER_BUSY") from None
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class Executor:
    """Used only while browser_lock is held, including across UI tool calls."""
    def __init__(self, c, pause_file="state/PAUSE"):
        self.c, self.pause_file = c, Path(pause_file)
        with transaction(c):
            for row in c.execute("SELECT id FROM posts WHERE status='IN_FLIGHT'").fetchall():
                c.execute("UPDATE posts SET status='UNKNOWN',reason=?,updated_at=? WHERE id=?",
                          ("EXECUTOR_INTERRUPTED_CHECK_RECENT_POSTS", stamp(), row["id"]))
                audit(c, row["id"], "UNKNOWN", "lease interrupted")

    def next(self, *, at=None):
        at = at or now()
        if self.pause_file.exists():
            return {"status": "PAUSED"}
        pending = self.c.execute("SELECT id FROM posts WHERE status='IN_FLIGHT' LIMIT 1").fetchone()
        if pending:
            return {"status": "SUBMISSION_PENDING", "id": pending['id']}
        unknown = self.c.execute("SELECT id,payload FROM posts WHERE status='UNKNOWN' ORDER BY scheduled_at LIMIT 1").fetchone()
        if unknown:
            return {"status": "RECONCILE_ONLY", "id": unknown["id"], "payload": json.loads(unknown["payload"])}
        rows = self.c.execute("SELECT * FROM posts WHERE status='QUEUED' ORDER BY scheduled_at,created_at,id").fetchall()
        for row in rows:
            p = json.loads(row["payload"])
            if row["track"] == "A" and instant(p["expires_at"]) <= at:
                self.c.execute("UPDATE posts SET status='EXPIRED',reason='MISSED_NO_CATCHUP',updated_at=? WHERE id=?", (stamp(at), row["id"]))
                audit(self.c, row["id"], "EXPIRED")
                continue
            if instant(row["scheduled_at"]) <= at:
                if row['track'] == 'A':
                    start = at.astimezone(SHANGHAI).replace(minute=at.minute // 20 * 20, second=0, microsecond=0)
                    previous = self.c.execute("SELECT actual_at FROM posts WHERE track='A' AND status='PUBLISHED'").fetchall()
                    if any(r['actual_at'] and start <= instant(r['actual_at']) < start + timedelta(minutes=20) for r in previous):
                        continue
                return {"status": "READY", "id": row["id"], "payload": p}
        return {"status": "EMPTY"}

    def begin(self, post_id, *, at=None):
        candidate = self.next(at=at)
        if candidate.get("id") != post_id or candidate["status"] != "READY":
            raise ValueError("NOT_NEXT_READY_OR_UNKNOWN_REQUIRES_RECONCILIATION")
        self.c.execute("UPDATE posts SET status='IN_FLIGHT',updated_at=? WHERE id=?", (stamp(at), post_id))
        audit(self.c, post_id, "IN_FLIGHT", "persisted BEFORE the only publish click")
        return {"status": "IN_FLIGHT", "id": post_id}

    def result(self, post_id, status, *, reason=None, receipt=None, observed_text=None):
        row = self.c.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not row or row["status"] not in {"IN_FLIGHT", "UNKNOWN", "QUEUED"}:
            raise ValueError("INVALID_RESULT_TRANSITION")
        if status not in {"PUBLISHED", "UNKNOWN", "BLOCKED", "CANCELLED"}:
            raise ValueError("INVALID_RESULT_STATUS")
        p = json.loads(row["payload"])
        if status == "PUBLISHED":
            if (row["status"] == "QUEUED" or observed_text != p["text"]
                    or not verify_receipt(p, receipt)["valid"]
                    or not receipt.get("published_at") or not instant(receipt["published_at"])):
                raise ValueError("INDEPENDENT_PAGE_EXACT_TEXT_AND_TIME_REQUIRED")
            used = self.c.execute("SELECT id FROM posts WHERE url=? AND id!=?", (receipt["url"], post_id)).fetchone()
            if used:
                raise ValueError("STATUS_URL_ALREADY_USED")
        elif not reason:
            raise ValueError("CONCRETE_REASON_REQUIRED")
        if row["status"] in {"UNKNOWN", "IN_FLIGHT"} and status in {"BLOCKED", "CANCELLED"}:
            raise ValueError("UNCERTAIN_SUBMISSION_CANNOT_BE_CLEARED_WITHOUT_VERIFICATION")
        self.c.execute("UPDATE posts SET status=?,reason=?,url=?,actual_at=?,evidence=?,updated_at=? WHERE id=?", (
            status, reason, receipt["url"] if receipt else None,
            receipt["published_at"] if receipt else None,
            json.dumps(receipt, ensure_ascii=False) if receipt else None, stamp(), post_id))
        audit(self.c, post_id, status, reason or receipt["url"])
        if status == 'BLOCKED' and reason.split(':', 1)[0] in {
            'LOGIN_REQUIRED', 'CAPTCHA', 'ACCOUNT_RESTRICTED', 'WRONG_ACCOUNT', 'COMPUTER_USE_UNAVAILABLE'
        }:
            self.pause_file.write_text(reason + '\n')
        return {"status": status, "id": post_id}


def cycle(c, *, at=None, reason="agent started"):
    """Only current Shanghai 20-minute slot; missed slots recorded, never replayed."""
    at = (at or now()).astimezone(SHANGHAI)
    slot = at.replace(minute=at.minute // 20 * 20, second=0, microsecond=0)
    with transaction(c):
        last = c.execute("SELECT slot FROM runs ORDER BY slot DESC LIMIT 1").fetchone()
        if last:
            gap = int((slot - instant(last["slot"]).astimezone(SHANGHAI)).total_seconds() // 1200) - 1
            if gap > 0:
                audit(c, None, "MISSED_CYCLES", json.dumps({"count": gap, "after": last["slot"], "resume": stamp(slot)}))
        c.execute("UPDATE runs SET status='INCOMPLETE',reason='INTERRUPTED_NO_CATCHUP' WHERE status='STARTED' AND slot!=?", (stamp(slot),))
        cur = c.execute("INSERT OR IGNORE INTO runs VALUES(?,?,?,?)", (stamp(slot), stamp(at), "STARTED", reason))
    return {"slot": stamp(slot), "new_cycle": cur.rowcount == 1, "next_at": stamp(slot + timedelta(minutes=20))}


def finish_cycle(c, slot, status, reason):
    if status not in {'PUBLISHED', 'NO_QUALIFIED', 'BLOCKED'} or not reason:
        raise ValueError('CYCLE_RESULT_AND_REASON_REQUIRED')
    changed = c.execute('UPDATE runs SET status=?,reason=? WHERE slot=? AND status=\'STARTED\'',
                        (status, reason, stamp(instant(slot))))
    if changed.rowcount != 1:
        raise ValueError('CYCLE_NOT_STARTED_OR_ALREADY_FINISHED')
    return {'slot': slot, 'status': status}


def run_lease(c, db, pause_file):
    with browser_lock(db):
        ex = Executor(c, pause_file)
        print(json.dumps({"lease": "ACQUIRED", "next": ex.next()}, ensure_ascii=False), flush=True)
        try:
            for line in sys.stdin:
                try:
                    cmd = json.loads(line)
                    op = cmd.pop("op")
                    if op == "release":
                        break
                    if op == "next":
                        result = ex.next()
                    elif op == "begin":
                        result = ex.begin(**cmd)
                    elif op == "result":
                        result = ex.result(**cmd)
                    elif op == "verify-receipt":
                        receipt = json.loads(Path(cmd['path']).read_text())
                        result = ex.result(receipt['post_id'], 'PUBLISHED',
                                           receipt=receipt, observed_text=receipt.get('observed_text'))
                    else:
                        raise ValueError("UNKNOWN_OPERATION")
                    print(json.dumps(result, ensure_ascii=False), flush=True)
                except (ValueError, TypeError, KeyError) as exc:
                    print(json.dumps({"error": str(exc)}), flush=True)
        finally:
            # Any exception, EOF, or explicit release preserves uncertainty.
            c.execute("UPDATE posts SET status='UNKNOWN',reason='LEASE_ENDED_WITHOUT_VERIFICATION',updated_at=? WHERE status='IN_FLIGHT'", (stamp(),))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=DB)
    sub = p.add_subparsers(dest="op", required=True)
    i = sub.add_parser("ingest"); i.add_argument("--root", default="outbox")
    e = sub.add_parser("enqueue"); e.add_argument("file")
    sub.add_parser("status")
    sub.add_parser("cycle")
    r = sub.add_parser('cycle-result')
    r.add_argument('--slot', required=True)
    r.add_argument('--status', choices=['PUBLISHED', 'NO_QUALIFIED', 'BLOCKED'], required=True)
    r.add_argument('--reason', required=True)
    sub.add_parser("pause")
    sub.add_parser("resume")
    sub.add_parser("executor")
    args = p.parse_args(argv)
    c = connect(args.db)
    pause_file = Path(args.db).parent / "PAUSE"
    try:
        if args.op == "ingest":
            result = ingest(c, args.root)
        elif args.op == "enqueue":
            result = enqueue(c, json.loads(Path(args.file).read_text()))
        elif args.op == "cycle":
            result = cycle(c)
        elif args.op == 'cycle-result':
            result = finish_cycle(c, args.slot, args.status, args.reason)
        elif args.op == "status":
            result = {"paused": pause_file.exists(), "posts": [dict(r) for r in c.execute("SELECT id,track,status,scheduled_at,actual_at,url,reason FROM posts ORDER BY created_at")]}
        elif args.op in {"pause", "resume"}:
            if args.op == "pause":
                pause_file.touch()
            else:
                pause_file.unlink(missing_ok=True)
            result = {"paused": pause_file.exists()}
        else:
            run_lease(c, args.db, pause_file)
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        c.close()


if __name__ == "__main__":
    main()
