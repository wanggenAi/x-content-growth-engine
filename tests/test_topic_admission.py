import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import patch

from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.editorial_gate import validate_candidate
from growth_engine.human_voice import stable_hash
from growth_engine.reader_model import reader_context, reader_model_semantic_integrity
from growth_engine.publication_preflight import pre_publish_assert
from growth_engine.viral_admission import PREVIEW_MODE, PRODUCTION_MODE, rank_materials, score_material, candidate_admission, material_hash
from tests.topic_helpers import AS_OF, WEIGHTS, bind_candidate, material, grounded_profile
from tests.test_human_style_production import candidate
from tests.test_reader_model import good_profile


class SemanticIntegrityTests(unittest.TestCase):
    def test_c390_contaminated_profile_fails_without_editing_history(self):
        original = json.loads(Path('data/editorial_candidate_c390_2026-10-16.json').read_text())
        c = deepcopy(original)
        c['state'] = 'READY_FOR_MANUAL_PUBLISH'
        report = reader_model_semantic_integrity(c)
        self.assertFalse(report['passed'])
        self.assertIn('FAIL_READER_MODEL_TOPIC_MISMATCH', report['status'])
        self.assertTrue(any('FAIL_UNSUPPORTED_READER_HIGH_SCORE' in r for r in report['reasons']))
        self.assertEqual(original['reader_model']['identity_trigger'], 'applicants')

    def test_technology_with_relationship_annotation_fails(self):
        c = candidate()
        c.update(text='OpenAI发布AI模型，软件平台提供代码工具。', topic='technology', payload='模型代码软件')
        c['reader_model']['why_reader_cares'] = '婚姻里的丈夫把妻子的存款转走'
        report = reader_model_semantic_integrity(c)
        self.assertTrue(any('TOPIC_MISMATCH' in r for r in report['reasons']))

    def test_grounded_work_profile_passes_and_text_edit_expires_it(self):
        c = candidate()
        c.update(text='老板给员工补发500元工资，工作账单写清楚。', topic='work', payload='500元工资')
        p = grounded_profile(c)
        p['reader_value_routes'][0].update(cue='老板给员工补发500元工资', reader_thought='补发工资的账单算清了吗')
        p['predicted_inner_response']='员工拿到补发工资了吗'
        p['share_recipient']='一起工作的同事'
        p['share_reason']='同事可以核对工作后的工资记录'
        p['why_reader_cares'] = '员工工作后的工资有没有兑现'
        p['concrete_stakes'] = '老板给员工的500元工资'
        for field, proof in p['semantic_binding']['field_evidence'].items():
            proof.update(quote='500元工资', value_hash=stable_hash(p[field]))
        c['reader_model'] = p
        self.assertTrue(reader_model_semantic_integrity(c)['passed'])
        c['text'] += '改动事实'
        self.assertIn('FAIL_READER_MODEL_STALE_CONTEXT', reader_model_semantic_integrity(c)['reasons'])

    def test_context_includes_source_payload_subject_topic_and_action(self):
        c = candidate()
        for key, value in [('subject_value','另一主题'),('payload','不同事实'),('source_refs',['https://example.com/other']),('topic','other'),('primary_action','REPLY')]:
            with self.subTest(key=key):
                changed = deepcopy(c); changed[key] = value
                self.assertIn('FAIL_READER_MODEL_STALE_CONTEXT', reader_model_semantic_integrity(changed)['reasons'])

    def test_generic_high_evidence_and_copied_value_are_refused(self):
        c = candidate()
        c['reader_model']['rationale'] = {'material_strength':'concrete evidence reviewed'}
        self.assertTrue(any('UNSUPPORTED_READER_HIGH_SCORE' in r for r in reader_model_semantic_integrity(c)['reasons']))
        c = candidate(); c['reader_model']['social_currency'] = 'HIGH'
        self.assertTrue(any('UNSUPPORTED_READER_HIGH_SCORE:social_currency' in r for r in reader_model_semantic_integrity(c)['reasons']))

    def test_production_modules_never_import_test_fixtures(self):
        for root in ('growth_engine','scripts'):
            for path in Path(root).glob('*.py'):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        self.assertFalse((node.module or '').startswith(('tests','test_')), path)
                    if isinstance(node, ast.Import):
                        self.assertTrue(all(not alias.name.startswith(('tests','test_')) for alias in node.names),path)


class TopicCompetitionTests(unittest.TestCase):
    def pool(self):
        return [material('m'+str(i), 1) for i in range(29)] + [material('winner',4)]

    def test_ranking_only_admits_production_winner(self):
        pool = self.pool()
        pool[0] = material('first', 3)  # Individually passes; still must lose.
        self.assertTrue(score_material(pool[0],as_of=AS_OF)['admitted'])
        report = rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(report['selected_material_id'],'winner')
        self.assertEqual(report['selected_material_ids'], ['winner'])
        reversed_report = rank_materials(list(reversed(pool)),as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(reversed_report['selected_material_id'], 'winner')

    def test_missing_pool_and_hand_filled_rank_cannot_reach_ready(self):
        c = candidate(); c.pop('material_pool'); c['competition_report']={'candidate_count':20,'rank':1,'ranking_margin':99}
        p = prepare_candidate(c)
        self.assertNotEqual(p['state'],'READY_FOR_MANUAL_PUBLISH')
        self.assertNotIn('human_style',p)  # Weak materials never enter rewriting.

    def test_duplicate_event_or_url_alias_does_not_fill_pool(self):
        pool=self.pool()
        pool[1]['event_id']=pool[0]['event_id']
        report=rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(report['candidate_count'],29)
        self.assertTrue(report['duplicate_clusters'])
        self.assertFalse(report['competition_passed'])
        self.assertIn('HUNT_INCOMPLETE_RAW_POOL',report['pool_reasons'])
        pool=self.pool();pool[0]['source']['url']='https://cn.v2ex.com/t/123'
        pool[1]['source']['url']='https://v2ex.com/t/123?x=2'
        self.assertTrue(rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)['duplicates'])

    def test_duplicated_dimension_reason_and_evidence_invalidate_deep_review(self):
        for field, expected in [('reason','DUPLICATED_DIMENSION_REASON'),('evidence','DUPLICATED_DIMENSION_EVIDENCE')]:
            m=material()
            repeated=m['review']['raw_material_strength'][field]
            for key in list(WEIGHTS)[:4]: m['review'][key][field]=repeated
            report=score_material(m,as_of=AS_OF)
            self.assertIn(expected,report['reasons'])
            self.assertIsNone(report['editorial_topic_score'])

    def test_fifty_rows_from_one_source_family_fail_production_diversity(self):
        pool=[material('telegram'+str(i),4 if i==49 else 1) for i in range(50)]
        for row in pool: row['source']['family']='TELEGRAM'
        report=rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertFalse(report['competition_passed'])
        self.assertEqual(report['source_family_count'],1)
        self.assertIn('HUNT_INCOMPLETE_SOURCE_DIVERSITY',report['pool_reasons'])

    def test_plain_amount_does_not_receive_hard_evidence_bonus(self):
        report=score_material(material(),as_of=AS_OF)
        self.assertEqual(report['viral_bonus']['hard_evidence_bonus'],0)

    def test_top2_cannot_forge_candidate_admission(self):
        c=candidate(); report=rank_materials(c['material_pool'],as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        runner_up=report['top3'][1]['material_id']; m=next(x for x in c['material_pool'] if x['material_id']==runner_up)
        c.update(material_id=runner_up,material_hash=material_hash(m),text=m['text'],draft_text_before_human_style=m['text'],source_refs=[m['source']['url']])
        admission=candidate_admission(c)
        self.assertFalse(admission['admitted'])
        self.assertIn('NOT_PRODUCTION_WINNER',admission['reasons'])

    def test_source_quality_never_adds_interest(self):
        low=material('boring',1);low['source']['confidence']='OFFICIAL_PRIMARY'
        same=deepcopy(low);same['source']['confidence']='SELF_REPORT'
        self.assertEqual(score_material(low,as_of=AS_OF)['topic_strength'],score_material(same,as_of=AS_OF)['topic_strength'])
        report=rank_materials([low]+self.pool(),as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(report['selected_material_id'],'winner')

    def test_distant_background_penalty_not_currency_regex(self):
        near=material(); far=deepcopy(near)
        far['review']['audience_distance']['value']='FAR'
        far['review']['background_cost']['value']='HIGH'
        self.assertGreater(score_material(near,as_of=AS_OF)['topic_strength'],score_material(far,as_of=AS_OF)['topic_strength'])
        self.assertEqual(score_material(far,as_of=AS_OF)['penalties']['distance'], 8)
        self.assertEqual(score_material(far,as_of=AS_OF)['penalties']['background'], 8)
        # A far-away story with an exceptional hook may still compete.
        far['review']['background_cost']['value']='LOW'
        self.assertTrue(score_material(far,as_of=AS_OF)['admitted'])

    def test_writing_95_topic_low_cannot_ready(self):
        c=candidate(); c['writing_quality']=95
        for k in WEIGHTS:c['material_pool'][0]['review'][k]['rating']=1
        c['material_hash']=material_hash(c['material_pool'][0])
        p=prepare_candidate(c)
        self.assertNotEqual(p['state'],'READY_FOR_MANUAL_PUBLISH')
        self.assertLess(p['viral_admission']['topic_strength'],60)

    def test_forged_contract_or_modified_pool_is_recomputed(self):
        p=prepare_candidate(candidate())
        self.assertEqual(p['state'],'READY_FOR_MANUAL_PUBLISH')
        p['viral_admission']['topic_strength']=99
        self.assertFalse(validate_candidate(p).ready)
        p=prepare_candidate(candidate());p['material_pool'][1]['review']['raw_material_strength']['rating']=4
        self.assertFalse(validate_candidate(p).ready)

    def test_missing_evidence_time_and_synthetic_hold_but_close_ranking_admits(self):
        m=material();m['review']['mass_relevance']['evidence']='no matching evidence'
        self.assertFalse(score_material(m,as_of=AS_OF)['admitted'])
        m=material();m['source']['published_at']=None
        self.assertFalse(score_material(m,as_of=AS_OF)['admitted'])
        pool=self.pool();pool[0]['fixture_type']='SYNTHETIC_TEST_FIXTURE'
        self.assertIsNone(rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)['selected_material_id'])
        pool=self.pool();pool[0]=material('near_tie',4)
        report=rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(len(report['selected_material_ids']),1)
        self.assertEqual(report['second_stage_judge']['status'],'SECOND_STAGE_EDITORIAL_JUDGE')

    def test_material_draft_cannot_be_swapped_after_ranking(self):
        p=prepare_candidate(candidate());p['draft_text_before_human_style']='另一篇帖子'
        self.assertIn('MATERIAL_DRAFT_MISMATCH',candidate_admission(p)['reasons'])

    def test_missing_rating_is_not_promoted_from_auto_screen(self):
        pool = self.pool()
        pool[0]['review'].pop('mass_relevance')
        pool[1]['source']['published_at'] = '2026-10-10T00:00:00Z'
        report = rank_materials(pool, as_of=AS_OF, admission_mode=PRODUCTION_MODE)
        row = next(r for r in report['rows'] if r['material_id']=='m0')
        self.assertIsNone(row['editorial_topic_score'])
        self.assertIn('MISSING_GROUNDED_REVIEW:mass_relevance',row['reasons'])
        self.assertTrue(report['competition_passed'])

    def test_contaminated_winner_never_enters_human_style(self):
        c = candidate(); c['reader_model'] = good_profile()
        with patch('growth_engine.candidate_pipeline.run_human_style_pipeline') as rewrite:
            p = prepare_candidate(c)
        rewrite.assert_not_called()
        self.assertNotEqual(p['state'], 'READY_FOR_MANUAL_PUBLISH')

    def test_saved_real_dry_run_and_ranking_are_reproducible(self):
        packet = json.loads(Path('data/viral_admission_challenge_2026-10-16.json').read_text())
        saved = json.loads(Path('data/viral_admission_ranking_2026-10-16.json').read_text())
        self.assertEqual(saved['version'], 'VIRAL_ADMISSION_V1')  # Historical policy snapshot, never overwritten.
        current = rank_materials(packet['materials'], as_of=packet['as_of'])
        self.assertEqual(current, rank_materials(packet['materials'], as_of=packet['as_of']))
        self.assertEqual(current['version'], 'VIRAL_ADMISSION_V3')
        self.assertEqual(current['admission_mode'], PREVIEW_MODE)
        dry = json.loads(Path('data/viral_admission_dry_run_2026-10-16.json').read_text())
        self.assertFalse(validate_candidate(dry).ready)  # V1 admission cannot masquerade as current V2.
        dry = prepare_candidate(dry)
        self.assertNotEqual(dry['state'], 'READY_FOR_MANUAL_PUBLISH')
        self.assertEqual(dry['publication_mode'], 'DRY_RUN_ONLY')
        with self.assertRaisesRegex(ValueError, 'not READY'):
            pre_publish_assert(dry, dry['text'], dry_run=True)

    def test_batch_cli_competes_whole_pool_before_preparing_winner(self):
        records = []
        source_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        for index in range(30):
            c = candidate()
            m = material('cli'+str(index), 4 if index == 29 else 3 if index == 0 else 1)
            m['source']['published_at'] = source_time
            m['draft_text'] = c['text']
            # This batch replaces the fixture's material/source identity, so
            # its independent text review must bind the replacement too.
            from tests.topic_helpers import text_review
            m['source']['event_time_status'] = 'EVENT_DATE_CHECKED'
            m['source_evidence'] = [{'url':m['source']['url'],'excerpt':c['text']}]
            c['content_review'] = text_review(c['text'], m['source_evidence'], c['publication_memory'])
            c.update(material=m, source_refs=[m['source']['url']])
            c['reader_model'] = grounded_profile(c)
            records.append(c)
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'input.json', Path(directory)/'output.json'
            source.write_text(json.dumps(records))
            run = subprocess.run([sys.executable, '-m', 'growth_engine', 'prepare-candidates',
                                  str(source), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(output.read_text())
        ready = [c['material_id'] for c in result if c['state'] == 'READY_FOR_MANUAL_PUBLISH']
        self.assertEqual(ready, ['cli29'])

    def test_full_entry_ready_but_real_publication_stays_paused(self):
        p=prepare_candidate(candidate())
        self.assertTrue(validate_candidate(p).ready)
        self.assertTrue(pre_publish_assert(p,p['text'],dry_run=True)['passed'])
        self.assertFalse(pre_publish_assert(p,p['text'],dry_run=True)['publication_allowed'])
        with patch('growth_engine.publication_control.publication_control', return_value={'status':'PAUSED'}):
            with self.assertRaisesRegex(ValueError,'PUBLICATION_PAUSED'):
                pre_publish_assert(p,p['text'])

    def test_real_challenge_replay_and_c390_demoted_without_id_rule(self):
        packet=json.loads(Path('data/viral_admission_challenge_2026-10-16.json').read_text())
        report=rank_materials(packet['materials'],as_of=packet['as_of'])
        self.assertGreaterEqual(report['candidate_count'],30)
        c390=next(r for r in report['rows'] if r['material_id']=='C390')
        self.assertFalse(c390['admitted'])
        self.assertIsNone(c390['editorial_topic_score'])
        self.assertNotEqual(report['selected_material_id'],'C390')
        renamed=deepcopy(next(m for m in packet['materials'] if m['material_id']=='C390'))
        renamed['material_id']='unseen-id'
        self.assertEqual(score_material(renamed,as_of=packet['as_of'])['auto_screen_score'],c390['auto_screen_score'])

if __name__=='__main__':unittest.main()
