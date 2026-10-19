import json
from copy import deepcopy
from pathlib import Path
import unittest

from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.content_review import review_content, review_variant_set
from growth_engine.discovery import parse_rss
from growth_engine.editorial_gate import validate_candidate
from growth_engine.human_voice import stable_hash
from growth_engine.hunt import production_dry_run
from growth_engine.viral_admission import score_material
from growth_engine.x_native_style import review_x_native_style
from tests.test_human_style_production import candidate
from tests.topic_helpers import AS_OF, material


class ContentReviewTests(unittest.TestCase):
    def test_style_and_topic_pass_cannot_replace_missing_text_review(self):
        c = candidate(); c.pop('content_review')
        p = prepare_candidate(c)
        self.assertTrue(p['human_style_result']['passed'])
        self.assertTrue(p['viral_admission']['admitted'])
        self.assertFalse(p['editorial_gate']['ready'])
        self.assertNotEqual(p['state'], 'READY_FOR_MANUAL_PUBLISH')
        # A caller cannot bypass the assembly function by setting READY.
        p['state'] = 'READY_FOR_MANUAL_PUBLISH'
        self.assertFalse(validate_candidate(p).ready)

    def test_editor_rejection_survives_all_high_scores_and_renamed_ids(self):
        c = candidate()
        c['content_review'].update(decision='REJECT', failure_reasons=['只有金额，没有值得读完的增量'])
        p = prepare_candidate(c)
        self.assertTrue(p['human_style_result']['passed'])
        self.assertIn('CONTENT_EDITOR_HOLD', p['editorial_gate']['reasons'])
        c['candidate_id'] = 'anything-else'
        self.assertNotEqual(prepare_candidate(c)['state'], 'READY_FOR_MANUAL_PUBLISH')

    def test_user_rejection_overrides_an_editor_pass(self):
        c = candidate(); c['user_content_verdict'] = 'REJECT'
        self.assertIn('CONTENT_USER_REJECTED', prepare_candidate(c)['editorial_gate']['reasons'])

    def test_draft_derived_locks_do_not_certify_source_truth(self):
        c = candidate()
        c['material_pool'][0]['source_evidence'][0]['excerpt'] = '实际原文只有一张账单，没有金额。'
        c['content_review']['source_hash'] = stable_hash(c['material_pool'][0]['source_evidence'])
        result = review_content(c, c['material_pool'][0])
        self.assertFalse(result['passed'])
        self.assertTrue(any('CONTENT_UNSUPPORTED_SENTENCE' in r for r in result['reasons']))

    def test_review_invalidated_by_one_word_source_or_memory_change(self):
        for changed in ['text', 'source', 'memory']:
            c = candidate(); m = c['material_pool'][0]
            if changed == 'text': c['text'] += '实际还有100元。'
            elif changed == 'source': m['source_evidence'][0]['excerpt'] += '更正。'
            else: c['publication_memory'].append({'text':'一条旧帖'})
            self.assertFalse(review_content(c, m)['passed'], changed)

    def test_unmapped_number_is_not_hidden_by_supported_verdict(self):
        c = candidate(); m = c['material_pool'][0]
        m['source_evidence'][0]['excerpt'] = '朋友给我发来一张100元账单。'
        c['content_review']['source_hash'] = stable_hash(m['source_evidence'])
        c['content_review']['claims'][0]['source_span'] = m['source_evidence'][0]['excerpt']
        self.assertIn('CONTENT_UNSOURCED_NUMBER:500', review_content(c, m)['reasons'])

    def test_duplicate_event_beats_a_positive_novelty_annotation(self):
        c = candidate(); m = c['material_pool'][0]
        c['publication_memory'] = [{'event_id':m['event_id']}]
        c['content_review']['novelty']['memory_hash'] = stable_hash(c['publication_memory'])
        self.assertIn('CONTENT_ALREADY_PUBLISHED', review_content(c,m)['reasons'])

    def test_tracking_parameters_cannot_hide_a_published_source(self):
        c = candidate(); m = c['material_pool'][0]
        c['publication_memory'] = [{'source_url':m['source']['url']+'?utm_source=old'}]
        c['content_review']['novelty']['memory_hash'] = stable_hash(c['publication_memory'])
        self.assertIn('CONTENT_ALREADY_PUBLISHED', review_content(c,m)['reasons'])

    def test_details_late_in_body_cannot_inflate_first_screen(self):
        short = '最近有一件值得关注的事。'
        long = short+'朋友收到500元账单，老板却拿走1000元，还发来一份合同。'
        self.assertEqual(review_x_native_style(short)['dimensions']['first_screen_stopping_power'],
                         review_x_native_style(long)['dimensions']['first_screen_stopping_power'])

    def test_comment_keywords_are_not_counted_twice_as_topic_evidence(self):
        self.assertEqual(score_material(material(),as_of=AS_OF)['viral_bonus']['human_nature_dilemma_bonus'],0)

    def test_repost_time_never_resets_known_event_age(self):
        m = material(); m['source']['event_time'] = '2026-09-16T00:00:00Z'
        self.assertEqual(score_material(m,as_of=AS_OF)['freshness'], 'OLDER_THAN_48H')
        c = candidate(); m = c['material_pool'][0]
        m['source'].update(event_time_status='EVERGREEN_REDISCOVERY',event_time='2026-09-16T00:00:00Z',
                           rediscovery_reason='旧事中付款流程依然值得复查，但须对读者标明原始日期。')
        self.assertIn('CONTENT_OLD_EVENT_DATE_HIDDEN', review_content(c,m)['reasons'])

    def test_cosmetic_variants_rejected_even_with_distinct_labels(self):
        vs = [{'id':i,'mode':mode,'text':'朋友给我发来一张500元账单。'+tail,
               'structure_reason':'先给具体账单然后呈现双方约定的关系。'}
              for i,mode,tail in [('A','STORY','散场才收到。'),('B','CONTRAST','散场后收到。'),('C','DISCUSSION','散场才看见。')]]
        self.assertFalse(review_variant_set(vs)['passed'])

    def test_c390_and_delivery_legacy_scores_no_longer_mean_recommended(self):
        old = json.loads(Path('data/editorial_candidate_c390_2026-10-16.json').read_text())
        self.assertTrue(old['editorial_gate']['ready'])  # immutable incident evidence
        old['candidate_id'] = 'renamed-negative'
        self.assertFalse(review_content(old, {})['passed'])
        result = production_dry_run(
            json.loads(Path('data/viral_feed/2026-10-17/1256.json').read_text()),
            json.loads(Path('data/viral_hunt_deep_reviews_2026-10-17.json').read_text()))
        self.assertTrue(all(v['human_style_passed'] for v in result['top1_previews']))
        self.assertIsNone(result['recommended_top1'])
        self.assertTrue(all(not v['content_review_result']['passed'] for v in result['top1_previews']))

    def test_rss_image_credit_does_not_hide_actual_story(self):
        rss = '''<rss xmlns:content="urn:content"><channel><item><title>一场婚礼</title>
        <link>https://example.com/story</link><content:encoded>Photograph: example</content:encoded>
        <description>新郎和新娘不请司仪，把预算留给婚宴，让宾客到场后直接开饭。</description></item></channel></rss>'''
        self.assertIn('预算留给婚宴',parse_rss(rss,'https://example.com/rss',AS_OF)[0]['text'])

    def test_live_source_packet_replays_all_three_topics_and_nine_drafts(self):
        root = Path('data/content_quality_2026-10-19')
        result = production_dry_run(json.loads((root/'source_packet.json').read_text()),
                                    json.loads((root/'editorial_reviews.json').read_text()))
        self.assertGreaterEqual(result['ranking']['reviewed_source_count'], 20)
        self.assertIsNotNone(result['recommended_top1'])
        drafted = [t for t in result['topics'] if t['variants']]
        self.assertEqual(len(drafted), 3)
        for topic in drafted:
            self.assertTrue(topic['variant_set_review']['passed'])
            self.assertTrue(all(v['content_review_result']['passed'] and v['human_style_passed'] for v in topic['variants']))
        self.assertFalse(result['publication_allowed'])


if __name__ == '__main__': unittest.main()
