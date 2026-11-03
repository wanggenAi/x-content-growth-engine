"""Private durable state. Never upload this database or bodies as artifacts."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path

class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get('TG_STATE_DIR', 'data/telegram'))
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.root / 'index.sqlite3')
        self.db.execute('CREATE TABLE IF NOT EXISTS posts(channel TEXT, id INTEGER, record TEXT, digest TEXT, PRIMARY KEY(channel,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS cursors(channel TEXT PRIMARY KEY, id INTEGER)')
        self.db.execute('CREATE TABLE IF NOT EXISTS files(key TEXT PRIMARY KEY, path TEXT)')
        self.db.commit()
    def cursor(self, channel):
        row = self.db.execute('SELECT id FROM cursors WHERE channel=?', (channel,)).fetchone()
        return row[0] if row else 0
    def finish(self, channel, msg_id):
        with self.db:
            self.db.execute('INSERT INTO cursors VALUES(?,?) ON CONFLICT(channel) DO UPDATE SET id=max(id,excluded.id)', (channel, msg_id))
    def put(self, channel, record, body=''):
        digest = hashlib.sha256(body.encode()).hexdigest() if body.strip() else ''
        record['content_sha256'] = digest
        if body:
            folder = self.root / 'bodies' / channel
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            tmp = folder / f"{record['id']}.tmp"
            tmp.write_text(body, encoding='utf-8')
            tmp.replace(folder / f"{record['id']}.txt")
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO posts VALUES(?,?,?,?)', (channel, record['id'], json.dumps(record, ensure_ascii=False), digest))
    def records(self, channel):
        records = [json.loads(r[0]) for r in self.db.execute('SELECT record FROM posts WHERE channel=? ORDER BY id DESC', (channel,))]
        seen = {}
        for r in records:
            digest = r.get('content_sha256')
            r['duplicate_of'] = seen.get(digest) if digest else None
            if digest:
                seen.setdefault(digest, r['id'])
        return records
    def file(self, key):
        row = self.db.execute('SELECT path FROM files WHERE key=?', (str(key),)).fetchone()
        return Path(row[0]) if row and Path(row[0]).is_file() else None
    def remember_file(self, key, path):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO files VALUES(?,?)', (str(key), str(Path(path).resolve())))
    def close(self):
        self.db.close()
