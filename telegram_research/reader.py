"""Read-only Telegram user-client collector; no joining, posting or forwarding."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .core import make_record, save_reports, validate_channel
from .settings import credentials

def pdf_details(path: Path, max_pages: int = 15) -> tuple[str, int, str]:
    try:
        from pypdf import PdfReader
        doc = PdfReader(str(path))
        pages = 0
        chunks: list[str] = []
        for page in doc.pages[:max_pages]:
            pages += 1
            chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)[:30000]
        if not text.strip():
            return "", pages, "扫描版/图片版 PDF 无可提取文字（未使用 OCR）"
        return text, pages, ""
    except Exception as exc:
        return "", 0, f"PDF 无法解析：{type(exc).__name__}"

async def collect(args: argparse.Namespace) -> list[dict]:
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise RuntimeError("缺少 Telethon；pip install -r telegram_research/requirements.txt") from exc
    api_id, api_hash, session = credentials(require_session=True)
    channel = validate_channel(args.channel)
    if args.max_messages < 1 or args.max_messages > 5000 or args.days < 0:
        raise ValueError("max-messages 应为 1-5000，days 不得为负数")
    earliest = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None
    records = []
    downloaded = 0
    async with TelegramClient(StringSession(session), api_id, api_hash,
                              receive_updates=False) as client:
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram Session 无效；请在自己的电脑上重新授权")
        entity = await client.get_entity(channel)
        async for msg in client.iter_messages(entity, limit=args.max_messages):
            if not msg or not msg.date:
                continue
            if earliest and msg.date < earliest:
                break
            media_file = getattr(msg, "file", None)
            name = getattr(media_file, "name", None)
            size = getattr(media_file, "size", None)
            mime = getattr(media_file, "mime_type", None)
            pdf = bool(name and name.lower().endswith(".pdf")) or mime == "application/pdf"
            if pdf and not name:
                name = f"document-{msg.id}.pdf"
            text, pages, error = "", 0, ""
            if args.download_pdfs and pdf and downloaded < args.pdf_limit:
                if size and size > args.pdf_max_mb * 1024 * 1024:
                    error = "超出 PDF 下载大小限制，已跳过"
                else:
                    dest_dir = Path("data/telegram/pdfs")
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / f"{channel}-{msg.id}.pdf"
                    try:
                        if not dest.is_file():
                            await client.download_media(msg, file=str(dest))
                        if dest.is_file():
                            text, pages, error = pdf_details(dest)
                            downloaded += 1
                        else:
                            error = "下载未生成文件"
                    except Exception as exc:
                        error = f"下载失败：{type(exc).__name__}"
            records.append(make_record(channel=channel, msg_id=msg.id, date=msg.date,
                                       caption=msg.message or "", filename=name, file_size=size,
                                       pdf_text=text, pdf_pages=pages, pdf_error=error))
    return records

def main() -> None:
    parser = argparse.ArgumentParser(description="只读 Telegram 研究：采集频道消息和 PDF 索引")
    parser.add_argument("--channel", default="shenduhaowen", help="公开频道用户名")
    parser.add_argument("--days", type=int, default=7, help="采集最近 N 天；0=不按日期筛选")
    parser.add_argument("--max-messages", type=int, default=200, help="最多读取消息数（上限 5000）")
    parser.add_argument("--download-pdfs", action="store_true", help="仅在本地保存 PDF，提取可选文字")
    parser.add_argument("--pdf-limit", type=int, default=10, help="最多下载 PDF 份数")
    parser.add_argument("--pdf-max-mb", type=int, default=15, help="每份 PDF 上限 MB")
    parser.add_argument("--output", default="reports/telegram", help="仅写入被忽略的报告目录")
    args = parser.parse_args()
    if args.pdf_limit < 0 or args.pdf_max_mb < 1:
        parser.error("PDF 上限参数无效")
    dest = Path(args.output).resolve()
    if not (dest == (Path.cwd() / "reports").resolve() or (Path.cwd() / "reports").resolve() in dest.parents):
        parser.error("输出目录必须在 reports/ 下，以防无意提交到公开仓库")
    try:
        records = asyncio.run(collect(args))
        save_reports(dest, validate_channel(args.channel), records, pdf_mode=args.download_pdfs)
        print(f"完成：{len(records)} 条消息；报告：{dest / 'brief.md'}；未发布到 X。")
    except (RuntimeError, ValueError, OSError) as exc:
        parser.exit(2, f"采集失败：{exc}\n")

if __name__ == "__main__":
    main()
