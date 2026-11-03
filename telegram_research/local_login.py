"""One-time loopback-only login UI. No credentials, codes or account names logged."""
import asyncio
import html
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from .settings import PRIVATE_DIR, credentials

class Login:
    def __init__(self):
        self.phase = 'credentials'
        self.error = ''
        self.client = None
        self.phone = None
        self.code_hash = None
        self.lock = threading.Lock()
        if (PRIVATE_DIR / 'session.txt').exists():
            self.phase = 'done'
        else:
            try:
                credentials(require_session=False)
                self.phase = 'phone'
            except RuntimeError:
                pass

    async def submit(self, values):
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import SessionPasswordNeededError
        try:
            self.error = ''
            if self.phase == 'credentials':
                api_id, api_hash = values.get('api_id', ''), values.get('api_hash', '')
                if not api_id.isdigit() or len(api_hash) != 32 or any(c not in '0123456789abcdefABCDEF' for c in api_hash):
                    raise ValueError('invalid format')
                PRIVATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd = os.open(PRIVATE_DIR / 'credentials.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as f:
                    f.write(f'TG_API_ID={api_id}\nTG_API_HASH={api_hash}\n')
                self.phase = 'phone'
            elif self.phase == 'phone':
                api_id, api_hash, _ = credentials(require_session=False)
                if self.client is None:
                    self.client = TelegramClient(StringSession(), api_id, api_hash, receive_updates=False, flood_sleep_threshold=0)
                    await self.client.connect()
                self.phone = values.get('phone', '').strip()
                result = await self.client.send_code_request(self.phone)
                self.code_hash = result.phone_code_hash
                self.phase = 'code'
            elif self.phase == 'code':
                try:
                    await self.client.sign_in(phone=self.phone, code=values.get('code', '').strip(), phone_code_hash=self.code_hash)
                except SessionPasswordNeededError:
                    self.phase = 'password'
                    return
                await self.finish()
            elif self.phase == 'password':
                await self.client.sign_in(password=values.get('password', ''))
                await self.finish()
        except Exception as exc:
            self.error = type(exc).__name__  # Never include exception text or request parameters.

    async def finish(self):
        if not await self.client.is_user_authorized():
            raise RuntimeError('not authorized')
        fd = os.open(PRIVATE_DIR / 'session.txt', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(self.client.session.save() + '\n')
        await self.client.disconnect()
        self.phone = self.code_hash = None
        self.phase = 'done'

    def page(self, token):
        fields = {
            'credentials': [('api_id', 'API ID'), ('api_hash', 'API Hash')],
            'phone': [('phone', '手机号（含国家区号）')],
            'code': [('code', 'Telegram 登录验证码')],
            'password': [('password', 'Telegram 两步验证密码')],
            'done': [],
        }[self.phase]
        inputs = ''.join(f'<label>{label}<input name="{name}" type="password" autocomplete="off" required></label>' for name, label in fields)
        form = f'<form method="post"><input type="hidden" name="csrf" value="{token}">{inputs}<button>继续</button></form>' if fields else '<p>本机授权已保存。可以关闭此页，由 Codex 继续采集。</p>'
        return ('<!doctype html><html lang="zh"><meta charset="utf-8"><title>本机 Telegram 授权</title>'
                '<meta name="viewport" content="width=device-width"><style>body{font:18px system-ui;max-width:600px;margin:60px auto;padding:24px}label{display:block;margin:24px 0}input{display:block;width:100%;padding:12px;box-sizing:border-box}button{padding:12px 24px}</style>'
                '<h1>本机 Telegram 授权</h1><p>输入仅交给这台电脑上的官方 Telethon 客户端。请直接在本页输入，不发到聊天。</p>'
                f'<p>{html.escape(self.error)}</p>{form}</html>').encode()


def main():
    os.umask(0o077)
    login, token = Login(), secrets.token_urlsafe(32)
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if not self.valid_host() or self.path != '/':
                self.send_error(403)
                return
            body = login.page(token)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            expected_origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.path != '/' or self.headers.get('Origin') != expected_origin:
                self.send_error(403)
                return
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size < 8192:
                self.send_error(400)
                return
            values = {k: v[0] for k, v in parse_qs(self.rfile.read(size).decode()).items()}
            if not secrets.compare_digest(values.pop('csrf', ''), token):
                self.send_error(403)
                return
            with login.lock:
                asyncio.run_coroutine_threadsafe(login.submit(values), loop).result(timeout=90)
            self.send_response(303)
            self.send_header('Location', '/')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    print(f'Local login ready: http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        loop.stop()

if __name__ == '__main__':
    main()
