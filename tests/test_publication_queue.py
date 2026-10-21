"""Real production gates plus cadence, idempotency and receipt regressions."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from growth_engine.hunt import production_dry_run
from growth_engine.publication_control import (
    new_queue, review_for_queue, slot_check, record_confirmation, record_failure, check_spacing,
)


class PublicationQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path('data/production_closure_v4_2026-10-21')
        feed = json.loads((root / 'source_packet.json').read_text())
        reviews = json.loads((root / 'editorial_reviews.json').read_text())
        reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
        cls.pipeline = production_dry_run(feed, reviews)['production_pipeline']

    def setUp(self):
        self.queue = new_queue()
        self.candidate = deepcopy(self.pipeline['candidate'])
        self.now = '2026-10-21T13:40:00+00:00'
        self.item = review_for_queue(self.queue, self.candidate, now=self.now,
                                    candidate_ref='checked.json', feedback=self.pipeline['feedback_24h'])
        self.candidates = {self.item['candidate_id']: self.candidate}

    def receipt(self, status='SCHEDULED'):
        return dict(status=status, provider='X', agent_checked=True, account='qiluo27808',
                    text_hash=self.item['text_hash'], observed_text=self.item['text'], observed_at=self.now,
                    evidence_ref='data/private/actual-observation', official_schedule_id='test-confirmation',
                    scheduled_for='2026-10-21T14:00:00+00:00',
                    post_url='https://x.com/qiluo27808/status/123', published_at=self.now)

    def test_real_gates_and_duplicate_or_stale_candidate(self):
        for change, error in [({}, 'DUPLICATE'), ({'competition_as_of': '2026-10-19T12:00:00Z'}, 'EXPIRED'),
                              ({'text': self.candidate['text'] + '!'}, 'hash'),
                              ({'source_fact_review': None}, 'editorial gate')]:
            with self.subTest(change=list(change)):
                candidate = {**self.candidate, **change}
                with self.assertRaisesRegex(ValueError, error):
                    review_for_queue(self.queue, candidate, now=self.now, candidate_ref='x',
                                     feedback=self.pipeline['feedback_24h'])

    def test_paused_slot_idempotent_no_catch_up_and_draft_stays_reviewed(self):
        slot = slot_check(self.queue, self.candidates, now=self.now,
                          control={'status': 'PAUSED', 'reason': 'TRANSPORT_BLOCKED'})
        again = slot_check(self.queue, {}, now='2026-10-21T13:59:59Z')
        self.assertEqual(slot, again)
        self.assertEqual(len(self.queue['slots']), 1)
        self.assertEqual(slot['reason'], 'TRANSPORT_BLOCKED')
        self.assertEqual(self.item['status'], 'REVIEWED')
        self.assertFalse(slot['external_action'])
        slot_check(self.queue, {}, now='2026-10-21T16:00:00Z')
        self.assertEqual(len(self.queue['slots']), 2)

    def test_active_switch_cannot_promote_dry_run_or_missing_transport(self):
        for control, reason in [({'status': 'ACTIVE'}, 'TRANSPORT'),
                                ({'status': 'ACTIVE', 'transport': {'verified': True}}, 'HISTORY')]:
            queue = deepcopy(self.queue)
            result = slot_check(queue, self.candidates, now=self.now, control=control)
            self.assertIn(reason, result['reason'])
        policy = {'status': 'ACTIVE', 'transport': {'verified': True},
                  'account_history': {'complete': True, 'checked_at': self.now, 'published_at': []}}
        result = slot_check(self.queue, self.candidates, now=self.now, control=policy)
        self.assertIn(result['reason'].split(':')[0], ('PUBLICATION_PAUSED', 'DRY_RUN_OR_PRODUCTION_HOLD'))

    def test_actual_and_reserved_times_require_twenty_minutes(self):
        self.queue['items'].append({'candidate_id': 'other', 'status': 'PUBLISHED', 'published_at': self.now})
        for target in ['2026-10-21T13:59:59Z', '2026-10-21T13:20:01Z']:
            with self.assertRaisesRegex(ValueError, 'INTERVAL'):
                check_spacing(self.queue, target)
        check_spacing(self.queue, '2026-10-21T14:00:00Z')
        self.queue['items'][-1] = {'candidate_id': 'other', 'status': 'SCHEDULED',
                                   'scheduled_for': '2026-10-21T14:20:00Z'}
        with self.assertRaisesRegex(ValueError, 'INTERVAL'):
            check_spacing(self.queue, '2026-10-21T14:01:00Z')

    def test_unknown_result_blocks_all_retries_until_actual_reconciliation(self):
        record_failure(self.queue, self.item['candidate_id'], now=self.now, reason='timeout; result unknown')
        result = slot_check(self.queue, self.candidates, now=self.now)
        self.assertIn('RECONCILE', result['reason'])
        self.assertEqual(self.item['status'], 'FAILED')
        record_confirmation(self.queue, self.item['candidate_id'], self.receipt('PUBLISHED'), now=self.now)
        self.assertEqual(self.item['status'], 'PUBLISHED')

    def test_local_plan_or_wrong_account_text_time_is_not_confirmation(self):
        for change in [{'agent_checked': False}, {'provider': 'LOCAL'}, {'account': 'other'},
                       {'text_hash': 'wrong'}, {'evidence_ref': ''}, {'official_schedule_id': None},
                       {'observed_at': '2026-10-21T14:00:00Z'},
                       {'scheduled_for': '2026-10-23T14:00:00Z'}]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    record_confirmation(self.queue, self.item['candidate_id'], {**self.receipt(), **change}, now=self.now)
                self.assertEqual(self.item['status'], 'REVIEWED')

    def test_scheduled_is_not_published_and_metrics_stay_unknown(self):
        record_confirmation(self.queue, self.item['candidate_id'], self.receipt(), now=self.now)
        self.assertEqual(self.item['status'], 'SCHEDULED')
        self.assertIsNone(self.item['post_url'])
        self.assertIsNone(self.item['feedback_24h']['published_at_utc'])
        receipt = self.receipt('PUBLISHED')
        receipt.update(observed_at='2026-10-21T14:00:00Z', published_at='2026-10-21T14:00:00Z')
        record_confirmation(self.queue, self.item['candidate_id'], receipt, now='2026-10-21T14:00:00Z')
        feedback = self.item['feedback_24h']
        self.assertIsNone(feedback['views'])
        self.assertIsNone(feedback['observed_at_utc'])
        self.assertFalse(feedback['learning_eligible'])
        self.assertEqual(feedback['due_at_utc'], '2026-10-22T14:00:00+00:00')

    def test_bad_post_url_and_spacing_or_daily_platform_cap(self):
        with self.assertRaisesRegex(ValueError, 'OWN_POST_URL'):
            record_confirmation(self.queue, self.item['candidate_id'],
                                {**self.receipt('PUBLISHED'), 'post_url': 'https://x.com.evil/qiluo27808/status/1'}, now=self.now)
        policy = {'status': 'ACTIVE', 'transport': {'verified': True}, 'account_history': {
            'complete': True, 'checked_at': self.now, 'published_at': ['2026-10-21T13:30:00Z']}}
        self.assertIn('INTERVAL', slot_check(deepcopy(self.queue), self.candidates, now=self.now, control=policy)['reason'])
        policy['account_history']['published_at'] = ['2026-10-21T01:00:00Z'] * 50
        self.assertIn('LIMIT_50', slot_check(self.queue, self.candidates, now=self.now, control=policy)['reason'])

    def test_reread_browser_boundary_correction_passes_the_same_full_pipeline(self):
        from scripts.validate_publication_launch import replay
        result = replay()
        self.assertEqual(result['final_status'], 'READY_CANDIDATE_DRY_RUN')
        candidate = result['production_pipeline']['candidate']
        self.assertIn('Chrome和Firefox已直接封锁相关中间证书', candidate['text'])
        self.assertNotIn('主流浏览器已阻断', candidate['text'])
        self.assertTrue(candidate['reader_model_integrity']['passed'])
        self.assertTrue(candidate['editorial_gate']['ready'])
        self.assertFalse(result['publication_allowed'])

    def test_stale_draft_does_not_hide_a_later_eligible_draft(self):
        stale = deepcopy(self.item)
        stale.update(candidate_id='stale', material_id='stale')
        self.queue['items'].insert(0, stale)
        self.candidates['stale'] = {**self.candidate, 'competition_as_of': '2026-10-18T00:00:00Z'}
        result = slot_check(self.queue, self.candidates, now=self.now,
                            control={'status': 'PAUSED', 'reason': 'NO_TRANSPORT'})
        self.assertEqual(stale['status'], 'SKIPPED')
        self.assertEqual(result['candidate_id'], self.item['candidate_id'])
        self.assertEqual(result['reason'], 'NO_TRANSPORT')

    def test_live_preflight_cannot_bypass_the_queue_by_changing_active_or_mode(self):
        from growth_engine.publication_preflight import pre_publish_assert
        candidate = {**self.candidate, 'publication_mode': 'USER_AUTHORIZED_OFFICIAL_CHANNEL'}
        with patch('growth_engine.publication_control.publication_control', return_value={
                'status': 'ACTIVE', 'minimum_interval_minutes': 20}):
            with self.assertRaisesRegex(ValueError, 'QUEUE_CONTEXT_REQUIRED'):
                pre_publish_assert(candidate, candidate['text'])
            with self.assertRaisesRegex(ValueError, 'NO_VERIFIED_COMPLIANT_TRANSPORT'):
                pre_publish_assert(candidate, candidate['text'], publication_queue=self.queue)

    def test_cli_checks_once_and_never_submits(self):
        with tempfile.TemporaryDirectory() as directory:
            queue_path = Path(directory) / 'queue.json'
            candidate_path = Path(directory) / 'candidate.json'
            queue_path.write_text(json.dumps(self.queue))
            candidate_path.write_text(json.dumps({'production_pipeline': self.pipeline}))
            command = [sys.executable, '-m', 'growth_engine', 'publication-queue',
                       str(queue_path), str(candidate_path)]
            for _ in range(2):
                run = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertFalse(result['external_action'])
                self.assertEqual(result['counts']['PUBLISHED'], 0)
                self.assertEqual(result['counts']['SCHEDULED'], 0)
            self.assertEqual(len(json.loads(queue_path.read_text())['slots']), 1)
