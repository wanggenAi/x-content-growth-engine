import asyncio
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock
from pypdf import PdfWriter
from telegram_research.core import make_record, save_public_status
from telegram_research.import_export import import_export
from telegram_research.reader import download_pdf, pdf_details, parse_date
from telegram_research.store import Store
from types import SimpleNamespace

class StateTests(unittest.TestCase):
    def test_restart_dedup_and_frontier(self):
        with TemporaryDirectory() as d:
            s = Store(d)
            for i in (1, 2, 2):
                r = make_record(channel='shenduhaowen', msg_id=i, date=datetime.now(timezone.utc), caption='title', filename=None, file_size=None)
                s.put('shenduhaowen', r, 'same actual text')
            self.assertEqual(s.cursor('shenduhaowen'), 0)
            s.finish('shenduhaowen', 2)
            s.close()
            s = Store(d)
            self.assertEqual(len(s.records('shenduhaowen')), 2)
            self.assertEqual(s.records('shenduhaowen')[1]['duplicate_of'], 2)
            self.assertEqual(s.cursor('shenduhaowen'), 2)
            s.close()

    def test_import_rejects_private_and_traversal(self):
        with TemporaryDirectory() as d:
            p = Path(d) / 'result.json'
            s = Store(Path(d) / 'state')
            p.write_text(json.dumps({'type':'personal_chat','messages':[]}))
            with self.assertRaises(ValueError):
                import_export(p, 'shenduhaowen', s)
            p.write_text(json.dumps({'type':'public_channel', 'messages':[{'type':'message','id':7,'date_unixtime':1,'text':[{'text':'Title'}], 'file':'../secret.pdf'}]}))
            self.assertEqual(import_export(p, 'shenduhaowen', s), 1)
            r = s.records('shenduhaowen')[0]
            self.assertFalse(r['pdf_read'])
            self.assertIn('路径', r['pdf_error'])
            self.assertIsNone(r['analysis']['core_views'])
            s.close()

    def test_scan_pdf_and_partial_download_not_reused(self):
        with TemporaryDirectory() as d:
            p = Path(d) / 'blank.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with p.open('wb') as f:
                writer.write(f)
            text, pages, error = pdf_details(p)
            self.assertEqual((text, pages), ('', 1))
            self.assertIn('扫描', error)
            s = Store(Path(d) / 'state')
            msg = SimpleNamespace(document=SimpleNamespace(id=42), file=SimpleNamespace(size=p.stat().st_size))
            async def copy(message, file):
                Path(file).write_bytes(p.read_bytes())
            client = SimpleNamespace(download_media=AsyncMock(side_effect=copy))
            asyncio.run(download_pdf(client, msg, s, 'shenduhaowen'))
            asyncio.run(download_pdf(client, msg, s, 'shenduhaowen'))
            self.assertEqual(client.download_media.await_count, 1)
            self.assertTrue(s.file('42'))
            s.close()

    def test_public_output_excludes_untrusted_text(self):
        with TemporaryDirectory() as d:
            p = Path(d) / 'status.md'
            save_public_status(p, 'shenduhaowen', [{'pdf':True,'pdf_read':False,'title':'PRIVATE','caption':'PRIVATE'}])
            self.assertNotIn('PRIVATE', p.read_text())
            self.assertIn('PDF files: 1', p.read_text())
        with self.assertRaises(Exception):
            parse_date('2026-01-01')
