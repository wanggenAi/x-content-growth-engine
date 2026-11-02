"""One-time interactive, local-only Telegram authorization."""
import asyncio
import os
from .settings import PRIVATE_DIR, credentials

async def main() -> None:
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise SystemExit("先安装依赖：pip install -r telegram_research/requirements.txt") from exc
    api_id, api_hash, _ = credentials(require_session=False)
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_DIR / "session.txt"
    if path.exists():
        raise SystemExit("session.txt 已存在，不会覆盖现有登录。需要重新登录请先自行备份并移走该文件。")
    print("只在本机授权。不要把验证码、两步验证密码或生成的 session 发到聊天或上传 GitHub。")
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        await client.start()
        session = client.session.save()
        if not session:
            raise RuntimeError("无法生成 Telegram Session")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(session + "\n")
    print(f"本机授权完成：{path}（已按私密文件存储）")
    print("如要启用 GitHub 定时采集，仅将 session 值填入 GitHub Secrets 的 TG_STRING_SESSION，切勿提交到仓库。")

if __name__ == "__main__":
    asyncio.run(main())
