"""Reader/fact evidence cannot be replaced by an author's self-PASS."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.content_review import reader_review_packet, review_content
from growth_engine.human_voice import stable_hash
from growth_engine.hunt import production_dry_run
from tests.test_human_style_production import candidate


class FinalChineseReaderTests(unittest.TestCase):
    def test_legacy_structural_pass_is_not_content_acceptance(self):
        c = candidate(); del c['content_review']['final_reader_review']
        report = review_content(c, c['material_pool'][0])
        self.assertTrue(report['passed'])  # historical evidence remains readable
        self.assertFalse(report['quality_ready'])
        self.assertNotEqual(prepare_candidate(c)['state'], 'READY_FOR_MANUAL_PUBLISH')

    def test_rejected_private_key_grammar_cannot_be_self_scored_back_to_ready(self):
        for text in ['有把私钥竟然是4。', '私钥竟然是4。']:
            c = candidate(text)  # even a fabricated all-PASS review must fail
            self.assertIn('CONTENT_USER_REJECTED_CHINESE_PRIVATE_KEY',
                          review_content(c, c['material_pool'][0])['final_reader']['reasons'])
            self.assertFalse(prepare_candidate(c)['editorial_gate']['ready'])

    def test_language_background_and_seven_questions_are_real_vetoes(self):
        changes = [lambda f: f['sentences'].pop(),
                   lambda f: f['sentences'][0].update(issues=['主谓搭配不自然']),
                   lambda f: f['sentences'][0].update(background_cost='EXCESSIVE'),
                   lambda f: f['checks']['new_information'].update(decision='HOLD'),
                   lambda f: f['checks']['natural_voice'].update(decision='HOLD'),
                   lambda f: f['variety'].update(decision='HOLD'),
                   lambda f: f.update(author_scores_used=True),
                   lambda f: f.update(stage='AUTHOR'),
                   lambda f: f.update(checks=['malformed']),
                   lambda f: f['sentences'].append('not a review'),
                   lambda f: f.update(reviewed_at='not-a-time')]
        for change in changes:
            c = candidate(); change(c['content_review']['final_reader_review'])
            self.assertFalse(prepare_candidate(c)['editorial_gate']['ready'])

    def test_facts_first_and_exact_final_pass_binding(self):
        for part in ['unresolved', 'date', 'text', 'claims', 'memory', 'source']:
            c = candidate(); m = c['material_pool'][0]; r = c['content_review']
            if part == 'unresolved': r['fact_review']['unresolved'] = ['重要因果尚未核实']
            elif part == 'date': r['fact_review']['reviewed_at'] = '2026-10-15T00:00:00Z'
            elif part == 'text': c['text'] = '一个朋友给我发来一张500元账单。'; r['text_hash'] = stable_hash(c['text'])
            elif part == 'claims': r['claims'][0]['reason'] = '更改事实解释，必须重新复核语义和因果边界。'
            elif part == 'memory': c['publication_memory'].append({'text': '另一个历史选题'})
            else: m['source']['event_time'] = '2026-10-10T00:00:00Z'
            self.assertFalse(prepare_candidate(c)['editorial_gate']['ready'], part)

    def test_final_input_omits_writer_score_and_recommendations(self):
        c = candidate(); c.update(writing_quality=100, recommended_variant='A')
        c['content_review']['reader_value'] = {'stop_reason': '作者自称极有传播价值'}
        c['material_pool'][0]['source']['evidence_text'] = '作者推荐语不能进入最终正文复核输入'
        packet = reader_review_packet(c, c['material_pool'][0])
        self.assertNotIn('writing_quality', packet)
        self.assertNotIn('recommended_variant', packet)
        self.assertNotIn('reader_value', packet)
        self.assertNotIn('evidence_text', packet['source'])
        self.assertIn('claims', packet)
        self.assertIn('publication_memory', packet)

    def test_fresh_real_materials_five_posts_two_content_passes_zero_queue_ready(self):
        root = Path('data/chinese_reader_quality_2026-10-22')
        feed = json.loads((root/'source_packet.json').read_text())
        reviews = json.loads((root/'editorial_reviews.json').read_text())
        reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
        run = production_dry_run(feed, reviews)
        drafts = [v for t in run['topics'] for v in t['variants']]
        self.assertEqual(len(reviews['records']), 10)
        self.assertEqual(len(drafts), 5)
        self.assertEqual(sum(v['content_quality_status'] == 'READY' for v in drafts), 2)
        self.assertTrue(all(v['human_style_passed'] for v in drafts))
        self.assertEqual(run['ranking']['candidate_count'], 102)
        self.assertIn('HUNT_INCOMPLETE_DEEP_REVIEW', run['ranking']['pool_reasons'])
        self.assertIsNone(run['recommended_top1'])
        self.assertFalse(run['production_pipeline']['prepublish']['passed'])
        self.assertFalse(run['publication_allowed'])
        for v in drafts:
            self.assertEqual(v['text'], v['after'])
            self.assertEqual(v['content_review_result']['final_reader']['audience_validation'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
