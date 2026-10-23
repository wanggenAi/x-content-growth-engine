import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from growth_engine.handoff import REVIEW_FLAGS, text_hash, verify_ready
from growth_engine.pipeline import connect, enqueue, ingest, Executor, browser_lock, cycle, finish_cycle
from growth_engine.discovery import collect, TelegramPreview

AT = datetime(2026, 10, 23, 12, 1, tzinfo=timezone.utc)


def post(suffix='one', track='B', text='今天走了另一条路，发现那家旧书店还开着。'):
    p = {'schema':'LIVING_RECORD_X_HANDOFF_V1', 'post_id':'20261023-'+suffix,
         'track':track, 'status':'READY_FOR_CODEX', 'allow_publication':True,
         'platform':'X','account':'qiluo27808','scope':'ORIGINAL_POST',
         'origin':'CHATGPT_USER_CONVERSATION', 'created_at':AT.isoformat(),
         'text':text,'content_sha256':text_hash(text),'claim_type':'PERSONAL_REFLECTION',
         'source_urls':[], 'review':dict.fromkeys(REVIEW_FLAGS, True),
         'approved_content_sha256':text_hash(text)}
    if track == 'A':
        p.update(origin='PUBLIC_SOURCE_DISCOVERY', claim_type='PUBLIC_FACTS',
                 source_urls=['https://example.org/event'],event_key='event-one',
                 event_at=AT.isoformat(),expires_at=(AT+timedelta(minutes=19)).isoformat(),
                 editorial={'reviewed_at':AT.isoformat(),'reviewed_sha256':text_hash(text),
                            'candidates_considered':['first','second'],'selection_reason':'verified details',
                            'fact_checks':[{'claim':'details','source':'https://example.org/event'}]})
        for f in ('final_text_approved','author_voice_checked','user_explicitly_requested_publication'):
            del p['review'][f]
        p['review'].update(standing_publication_authorized=True,editorial_checked=True)
    return p


def receipt(p):
    return {'post_id':p['post_id'],'content_sha256':p['content_sha256'],'account':'qiluo27808',
            'provider':'X','url':'https://x.com/qiluo27808/status/1234567890123456789',
            'observed_exact_text':True,'verified_at':AT.isoformat(),'published_at':AT.isoformat()}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/'queue.sqlite3'
        self.c=connect(self.db)
        self.ex=Executor(self.c,Path(self.tmp.name)/'PAUSE')
    def tearDown(self):
        self.c.close(); self.tmp.cleanup()
    def test_two_tracks_ordered_and_scheduled(self):
        a=post('news','A'); b=post('note',text='路过菜市场，摊主把剩下的花送给了买菜的人。')
        b['scheduled_at']=(AT+timedelta(minutes=10)).isoformat()
        self.assertEqual(enqueue(self.c,a,at=AT)['status'],'QUEUED')
        self.assertEqual(enqueue(self.c,b,at=AT)['status'],'QUEUED')
        self.assertEqual(self.ex.next(at=AT)['id'],a['post_id'])
        self.ex.begin(a['post_id'],at=AT)
        self.ex.result(a['post_id'],'PUBLISHED',receipt=receipt(a),observed_text=a['text'])
        self.assertEqual(self.ex.next(at=AT)['status'],'EMPTY')
        self.assertEqual(self.ex.next(at=AT+timedelta(minutes=10))['id'],b['post_id'])
    def test_id_event_exact_and_fuzzy_duplicates_survive_restart(self):
        a=post('news','A'); enqueue(self.c,a,at=AT)
        for name,changes in [('exact',{}),('event',{'text':'另一种完全不同的描述'})]:
            p=copy.deepcopy(a); p['post_id']='20261023-'+name; p.update(changes)
            p['content_sha256']=text_hash(p['text']);p['editorial']['reviewed_sha256']=p['content_sha256']
            self.assertEqual(enqueue(self.c,p,at=AT)['status'],'DUPLICATE')
        self.c.close();self.c=connect(self.db)
        b=post('near',text=a['text']+'。')
        self.assertEqual(enqueue(self.c,b,at=AT)['status'],'DUPLICATE')
        changed=copy.deepcopy(a);changed['text']='改稿';changed['content_sha256']=text_hash('改稿');changed['editorial']['reviewed_sha256']=changed['content_sha256']
        self.assertEqual(enqueue(self.c,changed,at=AT)['reason'],'IMMUTABLE_ID_CHANGED')
    def test_draft_false_permission_and_changed_approval_never_queue(self):
        p=post();p['status']='DRAFT';p['allow_publication']=False
        self.assertEqual(enqueue(self.c,p,at=AT)['status'],'REJECTED')
        p=post();p['text']+='改了';p['content_sha256']=text_hash(p['text'])
        self.assertFalse(verify_ready(p)['valid'])
    def test_unknown_blocks_both_tracks_and_cannot_be_blindly_retried(self):
        a=post('news','A');b=post('note',text='路口那棵树又开花了。')
        enqueue(self.c,a,at=AT);enqueue(self.c,b,at=AT)
        self.ex.begin(a['post_id'],at=AT)
        self.ex=Executor(self.c,Path(self.tmp.name)/'PAUSE')
        self.assertEqual(self.ex.next(at=AT)['status'],'RECONCILE_ONLY')
        with self.assertRaises(ValueError):self.ex.begin(a['post_id'],at=AT)
        with self.assertRaises(ValueError):self.ex.result(a['post_id'],'BLOCKED',reason='timeout')
        with self.assertRaises(ValueError):self.ex.result(a['post_id'],'PUBLISHED',receipt=receipt(a),observed_text='wrong')
        self.ex.result(a['post_id'],'PUBLISHED',receipt=receipt(a),observed_text=a['text'])
        self.assertEqual(self.ex.next(at=AT)['id'],b['post_id'])
    def test_browser_lock_excludes_another_process(self):
        script='from growth_engine.pipeline import browser_lock\nimport sys\ntry:\n with browser_lock(sys.argv[1]): pass\nexcept RuntimeError:\n sys.exit(7)'
        with browser_lock(self.db):
            r=subprocess.run([sys.executable,'-c',script,str(self.db)],capture_output=True)
            self.assertEqual(r.returncode,7,r.stderr)
        self.assertEqual(subprocess.run([sys.executable,'-c',script,str(self.db)],capture_output=True).returncode,0)
    def test_pending_submit_and_account_block_pause_other_track(self):
        a=post('news','A');b=post('note',text='路口的店铺换了一位老板。')
        enqueue(self.c,a,at=AT);enqueue(self.c,b,at=AT)
        self.ex.begin(a['post_id'],at=AT)
        self.assertEqual(self.ex.next(at=AT)['status'],'SUBMISSION_PENDING')
        self.ex.result(a['post_id'],'PUBLISHED',receipt=receipt(a),observed_text=a['text'])
        self.ex.result(b['post_id'],'BLOCKED',reason='LOGIN_REQUIRED:visible sign in page')
        self.assertTrue(self.ex.pause_file.exists())
        self.assertEqual(self.ex.next(at=AT)['status'],'PAUSED')
    def test_cycle_completion_and_known_date_without_invented_time(self):
        p=post('news','A');p['event_at']='2026-10-22';p['event_time_precision']='date'
        p['editorial']['event_date_note']='Court order on October 22; precise time unknown.'
        self.assertTrue(verify_ready(p)['valid'])
        p['event_at']='2026-13-32'
        self.assertFalse(verify_ready(p)['valid'])
        run=cycle(self.c,at=AT)
        self.assertEqual(finish_cycle(self.c,run['slot'],'NO_QUALIFIED','sources unavailable')['status'],'NO_QUALIFIED')
        with self.assertRaises(ValueError):finish_cycle(self.c,run['slot'],'PUBLISHED','already closed')
    def test_pause_expiry_no_catchup_and_missed_cycle_audit(self):
        a=post('news','A');enqueue(self.c,a,at=AT)
        self.assertEqual(self.ex.next(at=AT+timedelta(minutes=21))['status'],'EMPTY')
        self.assertEqual(self.c.execute('select status from posts').fetchone()[0],'EXPIRED')
        first=cycle(self.c,at=AT)
        self.assertTrue(first['new_cycle']);self.assertFalse(cycle(self.c,at=AT)['new_cycle'])
        cycle(self.c,at=AT+timedelta(hours=3))
        self.assertEqual(self.c.execute("select count(*) from audit where action='MISSED_CYCLES'").fetchone()[0],1)
        self.ex.pause_file.touch();self.assertEqual(self.ex.next(at=AT)['status'],'PAUSED')
    def test_ingest_receipt_and_revoked_input(self):
        root=Path(self.tmp.name)/'outbox';(root/'ready').mkdir(parents=True);(root/'receipts').mkdir()
        p=post();f=root/'ready'/(p['post_id']+'.json');f.write_text(json.dumps(p))
        self.assertEqual(ingest(self.c,root,at=AT)[0]['status'],'QUEUED')
        p['allow_publication']=False;f.write_text(json.dumps(p));ingest(self.c,root,at=AT)
        self.assertEqual(self.c.execute('select status from posts').fetchone()[0],'BLOCKED')
    def test_telegram_parser_and_access_failure_are_explicit(self):
        feed={'id':'tg','name':'test'};p=TelegramPreview(feed,AT)
        p.feed('<div class="tgme_widget_message" data-post="test/12"><div class="tgme_widget_message_text">一个具体的人<br>做了一件事</div><time datetime="2026-10-23T12:00:00+00:00"></time></div>')
        self.assertEqual(len(p.items),1);self.assertIn('做了一件事',p.items[0]['title'])
        config=Path(self.tmp.name)/'sources.json';config.write_text(json.dumps({'feeds':[dict(feed,url='https://example.org/rss')]}))
        def fail(url):raise TimeoutError('offline')
        r=collect(config,Path(self.tmp.name)/'reports',at=AT,fetcher=fail)
        self.assertEqual(r['count'],0);self.assertEqual(r['sources'][0]['status'],'ACCESS_FAILED')


if __name__=='__main__':unittest.main()
