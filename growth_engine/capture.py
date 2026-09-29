"""Local, manual-only X research capture form."""

from __future__ import annotations

import html
import secrets
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


FORM = """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>X 原帖研究录入</title><style>
body{font:15px/1.5 system-ui,sans-serif;color:#17212b;background:#f6f8f8;margin:0}main{max-width:760px;margin:32px auto;padding:0 20px}
h1{font-size:23px}h2{font-size:17px;margin-top:28px}label{display:block;margin:13px 0 4px;font-weight:600}input,textarea,select{box-sizing:border-box;width:100%;padding:9px;border:1px solid #abb8bc;border-radius:4px;background:white;font:inherit}textarea{min-height:80px}button{background:#087b65;color:white;border:0;border-radius:4px;padding:11px 17px;margin:18px 0;font:inherit;cursor:pointer}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.check{display:flex;gap:9px;align-items:center;font-weight:400}.check input{width:auto}.message{padding:10px;border-left:4px solid #087b65;background:#e9f5ef}small{color:#42515b}@media(max-width:600px){.row{display:block}main{margin:14px auto}}
</style><main><h1>X 原帖研究录入</h1>{message}<form method="post" action="/capture">
<input type="hidden" name="token" value="{token}"><label>原帖链接</label><input name="url" type="url" required placeholder="https://x.com/author/status/123">
<div class="row"><div><label>话题</label><input name="topic" required></div><div><label>发帖日期</label><input name="posted_date" type="date"></div></div>
<label>简短原文摘录（最多 180 字）</label><textarea name="excerpt" maxlength="180" required></textarea>
<h2>观察证据</h2><label>证据出处</label><input name="evidence_ref" required placeholder="原帖链接或本机截图引用"><small>截图及个人账号数据留在本机，不上传公开仓库。</small>
<label>观察笔记</label><textarea name="evidence_note" required placeholder="看到的上下文、评论关注点、限制或失败原因"></textarea>
<div class="row"><div><label>浏览量</label><input name="views" type="number" min="0"></div><div><label>点赞</label><input name="likes" type="number" min="0"></div></div>
<div class="row"><div><label>转发</label><input name="reposts" type="number" min="0"></div><div><label>回复</label><input name="replies" type="number" min="0"></div></div>
<div class="row"><div><label>指标出处</label><select name="metric_source"><option value="USER_NOTE">仅研究笔记</option><option value="PUBLIC_X_PAGE">当时 X 页面</option><option value="USER_SCREENSHOT">用户截图</option></select></div><div><label>指标所属时间（UTC）</label><input name="metric_as_of" placeholder="留空表示此刻；历史截图须填写 ISO 时间"></div></div>
<div class="row"><div><label>帖子形式</label><select name="post_type"><option>UNKNOWN</option><option>ORIGINAL</option><option>REPLY</option><option>QUOTE</option><option>REPOST</option><option>ARTICLE</option></select></div><div><label>商业推广</label><select name="promotion_status"><option>UNKNOWN</option><option>NONE_OBSERVED</option><option>SUSPECTED</option><option>DISCLOSED</option></select></div></div>
<label class="check"><input type="checkbox" name="original_checked" value="yes" required>我已在 X 正常界面亲自核对原帖，且有权记录此观察</label>
<button type="submit">保存观察</button></form></main></html>"""


def make_handler(db_path: Path):
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404)
                return
            self.render(200, "")

        def do_POST(self):
            if self.path != "/capture" or self.headers.get("Origin") not in {None, f"http://127.0.0.1:{self.server.server_port}"}:
                self.send_error(403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384:
                self.send_error(413)
                return
            fields = {key: values[0] for key, values in parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}
            if fields.get("token") != token or fields.get("original_checked") != "yes":
                self.send_error(403)
                return
            try:
                from .__main__ import connect, validate
                parsed = urlparse(fields["url"])
                handle = parsed.path.split("/")[1]
                now = datetime.now(timezone.utc).isoformat()
                row = {
                    "url": fields["url"], "author_handle": handle if handle != "i" else "unknown",
                    "posted_date": fields.get("posted_date") or None, "topic": fields["topic"],
                    "excerpt": fields["excerpt"], "cohort": "unclassified", "observed_at": now,
                    "source_url": fields["url"], "method": "manual_user_record", "discovery_query": "manual X interface",
                    "evidence_note": fields["evidence_note"], "evidence_ref": fields["evidence_ref"],
                    "verification_status": "ORIGINAL_CONFIRMED", "metric_source": fields["metric_source"],
                    "human_checked": True,
                    "metric_as_of": (fields.get("metric_as_of") or now) if fields.get("views") else None,
                    "post_type": fields["post_type"], "promotion_status": fields["promotion_status"],
                }
                for metric in ("views", "likes", "reposts", "replies"):
                    row[metric] = int(fields[metric]) if fields.get(metric) else None
                row = validate(row)
                with closing(connect(db_path)) as db, db:
                    from .phase2 import insert_observation
                    insert_observation(db, row)
                self.render(200, "<div class='message'>已保存原帖观察。可继续录入下一条。</div>")
            except (ValueError, KeyError) as exc:
                self.render(400, f"<div class='message'>保存失败：{html.escape(str(exc))}</div>")

        def render(self, status: int, message: str):
            body = FORM.replace("{message}", message).replace("{token}", token).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(db_path: Path, port: int):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(db_path))
    print(f"Manual capture: http://127.0.0.1:{server.server_port}/", flush=True)
    server.serve_forever()
