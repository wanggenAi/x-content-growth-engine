"""Read-only official Telegram client. No joining, posting, or interactive login."""
from __future__ import annotations
import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .core import make_record, save_reports, save_public_status, validate_channel
from .settings import credentials
from .store import Store


def pdf_details(path: Path, max_pages: int = 0) -> tuple[str, int, str]:
    try:
        from pypdf import PdfReader
        doc = PdfReader(str(path))
        pages = doc.pages[:max_pages] if max_pages else doc.pages
        chunks = [page.extract_text() or '' for page in pages]
        text = '\n'.join(chunks)
        if not text.strip():
            return '', len(chunks), '扫描版/图片版 PDF 无可提取文字（未使用 OCR）'
        warning = '仅提取部分页面；不能称为完整阅读' if max_pages and len(doc.pages) > max_pages else ''
        return text, len(chunks), warning
    except Exception as exc:
        return '', 0, f'PDF 无法解析：{type(exc).__name__}'


def parse_date(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise argparse.ArgumentTypeError('日期需包含时区，例如 2026-10-01T00:00:00+08:00')
    return date.astimezone(timezone.utc)


async def retry(operation, attempts=3):
    from telethon.errors import FloodWaitError
    for attempt in range(attempts):
        try:
            return await operation()
        except FloodWaitError as exc:
            # Do not evade Telegram limits; preserve checkpoint and exit for later run.
            raise RuntimeError(f'Telegram 要求等待 {exc.seconds} 秒；本次停止，稍后再运行') from None
        except (OSError, asyncio.TimeoutError):
            if attempt + 1 == attempts:
                raise
            await asyncio.sleep(2 ** attempt)


async def download_pdf(client, msg, store, channel):
    key = str(msg.document.id)
    dest = store.file(key)
    if dest is None:
        folder = store.root / 'pdfs'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        dest = folder / f'{channel}-{key}.pdf'
        tmp = dest.with_suffix('.part')
        async def download():
            tmp.unlink(missing_ok=True)
            await client.download_media(msg, file=str(tmp))
            expected = getattr(msg.file, 'size', None)
            if not tmp.is_file() or (expected and tmp.stat().st_size != expected):
                raise OSError('incomplete download')
            tmp.replace(dest)
        await retry(download)
        store.remember_file(key, dest)
    return pdf_details(dest)


async def collect(args):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    api_id, api_hash, session = credentials(require_session=True)
    channel = validate_channel(args.channel)
    earliest = args.since or (datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None)
    store = Store()
    client = TelegramClient(StringSession(session), api_id, api_hash, receive_updates=False,
                            flood_sleep_threshold=0, request_retries=3)
    records, downloaded, failures = [], 0, 0
    cursor = store.cursor(channel) if args.incremental and not earliest and not args.until else 0
    newest = cursor
    try:
        # Context manager calls start(), which might prompt. Explicit connect never logs in.
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError('Telegram Session 无效；请在自己的电脑上重新授权')
        entity = await retry(lambda: client.get_entity(channel))
        if not getattr(entity, 'broadcast', False) or (getattr(entity, 'username', '') or '').lower() != channel.lower():
            raise RuntimeError('目标不是指定的公开频道；停止，防止采集私人聊天')
        # Oldest-first incremental iteration prevents losing a backlog larger than the batch.
        options = dict(limit=args.max_messages, min_id=cursor, reverse=bool(cursor))
        if args.until and not cursor:
            options['offset_date'] = args.until
        async for msg in client.iter_messages(entity, **options):
            if not msg or not msg.date:
                continue
            if earliest and msg.date < earliest:
                break
            if args.until and msg.date >= args.until:
                continue
            newest = max(newest, msg.id)
            if getattr(msg, 'action', None):
                continue
            file = getattr(msg, 'file', None)
            name, size, mime = (getattr(file, field, None) for field in ('name', 'size', 'mime_type'))
            pdf = bool(name and name.lower().endswith('.pdf')) or mime == 'application/pdf'
            if pdf and not name:
                name = f'document-{msg.id}.pdf'
            body, pages, error = '', 0, ''
            if args.download_pdfs and pdf and downloaded < args.pdf_limit:
                if size and size > args.pdf_max_mb * 1024 * 1024:
                    error = '超出 PDF 下载大小限制，已跳过'
                else:
                    try:
                        body, pages, error = await download_pdf(client, msg, store, channel)
                        downloaded += 1
                    except RuntimeError:
                        raise
                    except Exception as exc:
                        error = f'下载失败：{type(exc).__name__}'
                        failures += 1
            caption = msg.message or ''
            record = make_record(channel=channel, msg_id=msg.id, date=msg.date, caption=caption,
                                 filename=name, file_size=size, pdf_text=body, pdf_pages=pages, pdf_error=error)
            store.put(channel, record, body or caption)
            records.append(record)
        # Failed PDF jobs can be retried by rerunning the same interval; do not move frontier.
        if not failures and not earliest and not args.until:
            store.finish(channel, newest)
        save_reports(Path(args.output), channel, store.records(channel), pdf_mode=args.download_pdfs)
        if args.public_status:
            save_public_status(Path(args.public_status), channel, records, 'partial_failure' if failures else 'success')
        if failures:
            raise RuntimeError(f'{failures} 个附件下载失败；记录已保存，游标未推进')
        return records
    finally:
        await client.disconnect()
        store.close()


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--channel', default='shenduhaowen')
    p.add_argument('--days', type=int, default=0)
    p.add_argument('--since', type=parse_date)
    p.add_argument('--until', type=parse_date, help='不包含此时间')
    p.add_argument('--max-messages', type=int, default=200)
    p.add_argument('--incremental', action='store_true')
    p.add_argument('--download-pdfs', action='store_true')
    p.add_argument('--pdf-limit', type=int, default=10)
    p.add_argument('--pdf-max-mb', type=int, default=15)
    p.add_argument('--output', default='reports/telegram')
    p.add_argument('--public-status', help='只含统计的公开运行报告')
    a = p.parse_args()
    if not 1 <= a.max_messages <= 5000 or a.days < 0 or a.pdf_limit < 0 or a.pdf_max_mb < 1:
        p.error('无效的数量限制')
    if a.since and a.until and a.since >= a.until:
        p.error('since 必须早于 until')
    for value in (a.output, a.public_status):
        if value and Path.cwd().joinpath('reports').resolve() not in Path(value).resolve().parents:
            p.error('报告必须保存在 reports/ 内')
    try:
        records = asyncio.run(collect(a))
        print(f'成功：本轮 {len(records)} 条消息；私人报告 {a.output}/brief.md')
    except Exception as exc:
        # RPC exceptions may contain phone numbers or request details. Never echo them.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        p.exit(2, f'采集失败：{message}\n')

if __name__ == '__main__':
    main()
