import json
from copy import deepcopy
from pathlib import Path
import unittest

from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.content_review import review_content, review_variant_set
from growth_engine.discovery import parse_rss
from growth_engine.editorial_gate import validate_candidate
from growth_engine.human_voice import stable_hash
from growth_engine.hunt import apply_deep_review_records, production_dry_run
from growth_engine.viral_admission import score_material, validate_deep_review
from growth_engine.x_native_style import review_x_native_style
from tests.test_human_style_production import candidate
from tests.topic_helpers import AS_OF, material


class ContentReviewTests(unittest.TestCase):
    def test_english_conflict_evidence_still_needs_grounded_editor_review(self):
        m = material()
        proof = 'Drivers disputed claims their horses are mistreated.'
        m['source']['evidence_text'] += '\n' + proof
        m['review']['conflict'].update(rating=2, evidence=proof,
                                      reason='车夫与支持禁令者存在双方利益冲突，需要保留两方的真实立场。')
        self.assertNotIn('UNSUPPORTED_DIMENSION_EVIDENCE:conflict', validate_deep_review(m)['reasons'])
        m['review']['conflict']['evidence'] = 'Drivers discussed their work.'
        m['source']['evidence_text'] += '\nDrivers discussed their work.'
        self.assertIn('UNSUPPORTED_DIMENSION_EVIDENCE:conflict', validate_deep_review(m)['reasons'])
        m['review']['conflict']['evidence'] = 'Other people opposed the plan.'
        self.assertIn('MISSING_GROUNDED_REVIEW:conflict', validate_deep_review(m)['reasons'])

    def test_final_live_competition_keeps_veto_and_checks_authored_held_story(self):
        root = Path('data/content_competition_v4_final_2026-10-21')
        feed = json.loads((root/'source_packet.json').read_text())
        reviews = json.loads((root/'editorial_reviews.json').read_text())
        reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
        result = production_dry_run(feed, reviews); ranking = result['ranking']
        self.assertGreaterEqual(ranking['candidate_count'], 30)
        self.assertGreaterEqual(ranking['reviewed_source_count'], 20)
        self.assertGreaterEqual(ranking['under48h_count'], 10)
        self.assertGreaterEqual(ranking['source_family_count'], 4)
        self.assertEqual(ranking['selected_material_ids'], ['D04e89731e0e8c0f1'])
        rows = {r['material_id']:r for r in ranking['rows']}
        self.assertFalse(rows['D22b51d2ff51d406b']['admitted'])
        self.assertIn('TOPIC_EDITOR_HOLD', rows['D22b51d2ff51d406b']['reasons'])
        self.assertGreater(rows['Daabc79abe7faa361']['editorial_topic_score'],
                           rows['D91aa25fe640f5a3e']['editorial_topic_score'])
        self.assertFalse(rows['Daabc79abe7faa361']['admitted'])
        variants = [v for t in result['topics'] for v in t['variants']]
        self.assertEqual(len(variants), 12)
        self.assertTrue(all(v['human_style_passed'] and v['content_review_result']['passed'] for v in variants))
        self.assertFalse(result['publication_allowed'])
        # The packet policy cannot be bypassed by omitting a variant flag.
        first = reviews['records'][0]['previews'][0]
        first.pop('opening_comparison_required', None)
        del first['content_review']['opening']['alternatives']
        changed = production_dry_run(feed, reviews)
        variant = next(t for t in changed['topics'] if t['material_id'] == reviews['records'][0]['material_id'])['variants'][0]
        self.assertIn('CONTENT_OPENING_COMPARISON_REQUIRED', variant['content_review_result']['reasons'])

    def test_new_opening_comparison_is_source_bound_and_not_cosmetic(self):
        c = candidate(); m = c['material_pool'][0]
        c['opening_comparison_required'] = True
        self.assertIn('CONTENT_OPENING_COMPARISON_REQUIRED', review_content(c, m)['reasons'])
        opening = c['content_review']['opening']
        proof = m['source_evidence'][0]['excerpt']
        opening.update(alternatives=[
            {'text':c['text'].split('。')[0], 'approach':'RESULT_FIRST',
             'reader_reason':'首句直接展示付款动作和具体账单，让读者不用先猜发生什么。', 'source_span':proof},
            {'text':'一顿饭吃完，请客约定还算不算数。', 'approach':'AGREEMENT_FIRST',
             'reader_reason':'从约定切入可以理解分歧，但把具体金额延后，理解成本更高。', 'source_span':proof}],
            selection_reason='保留账单动作在前；约定开头需要再读一句才知道实际代价。')
        self.assertTrue(review_content(c, m)['passed'], review_content(c, m)['reasons'])
        for field, value in [('source_span','完全不在原文中的虚构证据。'),
                             ('text',opening['alternatives'][0]['text']+'啊'),
                             ('approach','RESULT_FIRST')]:
            changed = deepcopy(c); changed['content_review']['opening']['alternatives'][1][field] = value
            self.assertIn('CONTENT_OPENING_COMPARISON_REQUIRED', review_content(changed, m)['reasons'])

    def test_v4_reader_questions_gate_topic_selection_before_writing(self):
        root = Path('data/content_competition_v4_2026-10-20')
        feed = json.loads((root/'source_packet.json').read_text())
        reviews = json.loads((root/'editorial_reviews.json').read_text())
        mid = reviews['records'][0]['material_id']
        m = next(m for m in apply_deep_review_records(feed['materials'], reviews)
                 if m['material_id'] == mid)
        self.assertTrue(validate_deep_review(m)['passed'])
        del reviews['records'][0]['reader_value']['distinct_angle']
        m = next(m for m in apply_deep_review_records(feed['materials'], reviews)
                 if m['material_id'] == mid)
        self.assertIn('CONTENT_READER_VALUE_REQUIRED:distinct_angle', validate_deep_review(m)['reasons'])
        reviews['strategy_version'] = 'V4'
        del reviews['records'][0]['reader_value']
        m = next(m for m in apply_deep_review_records(feed['materials'], reviews)
                 if m['material_id'] == mid)
        self.assertEqual(len([r for r in validate_deep_review(m)['reasons']
                              if r.startswith('CONTENT_READER_VALUE_REQUIRED:')]), 4)

    def test_v4_reader_value_is_required_without_changing_legacy_contracts(self):
        c = candidate(); m = c['material_pool'][0]
        self.assertTrue(review_content(c, m)['passed'])
        c['strategy_version'] = 'V4'
        self.assertIn('CONTENT_V4_REVIEW_REQUIRED', review_content(c, m)['reasons'])
        c['content_review']['version'] = 'CONTENT_REVIEW_V4'
        self.assertEqual(sum(r.startswith('CONTENT_READER_VALUE_REQUIRED:')
                             for r in review_content(c, m)['reasons']), 4)

    def test_v4_live_source_competition_all_fifteen_and_no_production_admission(self):
        root = Path('data/content_competition_v4_2026-10-20')
        feed = json.loads((root/'source_packet.json').read_text())
        reviews = json.loads((root/'editorial_reviews.json').read_text())
        # Reuse full existing public history; no second copy or synthetic memory.
        reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
        self.assertEqual(stable_hash(reviews['publication_memory']), reviews['publication_memory_hash'])
        result = production_dry_run(feed, reviews)
        self.assertEqual(result['ranking']['candidate_count'], 10)
        self.assertEqual(result['ranking']['reviewed_source_count'], 10)
        self.assertEqual(len(result['topics']), 5)
        for topic in result['topics']:
            self.assertTrue(topic['variant_set_review']['passed'])
            self.assertEqual(len(topic['variants']), 3)
            for v in topic['variants']:
                self.assertTrue(v['human_style_passed'], v['fact_preservation_report'])
                self.assertTrue(v['content_review_result']['passed'], v['content_review_result'])
                self.assertFalse(v['publication_allowed'])
        self.assertFalse(result['ranking']['competition_passed'])  # existing raw30/review20/families4 kept
        self.assertIsNone(result['recommended_top1'])
        self.assertFalse(result['publication_allowed'])
        selected = result['topics'][0]['variants'][0]
        material = next(m for m in feed['materials'] if m['material_id'] == result['topics'][0]['material_id'])
        changed = {**selected, 'text': selected['after']+'另有9999元奖金。',
                   'publication_memory': reviews['publication_memory']}
        self.assertFalse(review_content(changed, material)['passed'])

    def test_v4_and_legacy_variant_protocols_cannot_be_mixed(self):
        variants = [{'id': i, 'mode': mode, 'strategy_version': 'V4', 'text': text,
                     'structure_reason': '用不同叙事切口说明同一件事的实际动作与取舍。'}
                    for i, mode, text in [('A', 'DIRECT', '客人把账单退了回去。'),
                                          ('B', 'PERSONAL', '这顿饭看得我有点糊涂。朋友原来没买单。'),
                                          ('C', 'HUMAN_CONTRAST', '散场以后才知道谁付钱。老板还在门口等着。')]]
        self.assertTrue(review_variant_set(variants)['passed'])
        variants[0].pop('strategy_version')
        self.assertIn('VARIANT_STRATEGY_VERSION_MISMATCH', review_variant_set(variants)['reasons'])

    def test_v4_followthrough_preserves_authored_text_and_source_bound_holds(self):
        root = Path('data/content_competition_v4_2026-10-21')
        feed = json.loads((root/'source_packet.json').read_text())
        reviews = json.loads((root/'editorial_reviews.json').read_text())
        reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
        result = production_dry_run(feed, reviews)
        self.assertEqual(result['ranking']['candidate_count'], 10)
        self.assertEqual(sum(len(t['variants']) for t in result['topics']), 15)
        for topic in result['topics']:
            self.assertTrue(topic['variant_set_review']['passed'])
            for v in topic['variants']:
                self.assertEqual(v['text'], v['after'])
                self.assertTrue(v['content_review_result']['passed'], v['content_review_result'])
                self.assertTrue(v['human_style_passed'], v['fact_preservation_report'])
        self.assertFalse(result['ranking']['competition_passed'])
        self.assertIsNone(result['recommended_top1'])
        self.assertFalse(result['publication_allowed'])
        # Explicitly rejected user feedback survives a high-scoring new review.
        m = deepcopy(feed['materials'][0]); m['user_content_verdict'] = 'REJECT'
        c = {**reviews['records'][0]['previews'][0], 'publication_memory': reviews['publication_memory']}
        self.assertIn('CONTENT_USER_REJECTED', review_content(c, m)['reasons'])

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
        self.assertIsNone(result['recommended_top1'])  # historical structural PASS is not final Chinese acceptance
        drafted = [t for t in result['topics'] if t['variants']]
        self.assertEqual(len(drafted), 3)
        for topic in drafted:
            self.assertTrue(topic['variant_set_review']['passed'])
            self.assertTrue(all(v['content_review_result']['passed'] and v['human_style_passed'] for v in topic['variants']))
        self.assertFalse(result['publication_allowed'])


if __name__ == '__main__': unittest.main()
