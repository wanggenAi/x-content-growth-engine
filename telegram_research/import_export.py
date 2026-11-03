"""Import an official, single-channel Telegram Desktop JSON export locally."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from .core import make_record, save_reports, validate_channel
from .reader import pdf_details
from .store import Store


def text_value(value):
    if isinstance(value, str):
        return value
    return ''.join(v if isinstance(v, str) else v.get('text', '') for v in value or [])


def import_export(source, channel, store, since=None, until=None):
    source = Path(source).resolve()
    data = json.loads(source.read_text(encoding='utf-8'))
    if data.get('type') != 'public_channel' or not isinstance(data.get('messages'), list):
        raise ValueError('只接受单个公开频道的官方 JSON 导出；不导入私人聊天或整个账号导出')
    count = 0
    for msg in data['messages']:
        if msg.get('type') != 'message':
            continue
        date = datetime.fromtimestamp(int(msg['date_unixtime']), timezone.utc)
        if (since and date < since) or (until and date >= until):
            continue
        caption = text_value(msg.get('text', ''))
        relative = msg.get('file', '')
        name = msg.get('file_name') or (Path(relative).name if relative and not relative.startswith('(') else None)
        body, pages, error = '', 0, ''
        if name and name.lower().endswith('.pdf'):
            attachment = (source.parent / relative).resolve() if relative else None
            if attachment and source.parent in attachment.parents and attachment.is_file():
                body, pages, error = pdf_details(attachment)
            else:
                error = '附件未导出或路径不安全；未读取正文'
        record = make_record(channel=channel, msg_id=int(msg['id']), date=date, caption=caption,
                             filename=name, file_size=msg.get('file_size'), pdf_text=body,
                             pdf_pages=pages, pdf_error=error)
        record['source'] = 'official_desktop_export'
        store.put(channel, record, body or caption)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--channel', default='shenduhaowen', help='请确认导出确为该公开频道；导出 JSON 不一定含用户名')
    args = parser.parse_args()
    channel = validate_channel(args.channel)
    store = Store()
    try:
        count = import_export(args.source, channel, store)
        save_reports(Path('reports/telegram'), channel, store.records(channel), pdf_mode=True)
        print(f'导入消息 {count}；报告 reports/telegram/brief.md；仅本地保存')
    finally:
        store.close()

if __name__ == '__main__':
    main()
