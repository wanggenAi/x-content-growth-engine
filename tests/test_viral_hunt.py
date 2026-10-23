import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from growth_engine.ai_flavor_gate import PATTERNS, analyze_ai_flavor
from growth_engine.capture import auto_discover_materials, build_search_queries
from growth_engine.candidate_pipeline import prepare_candidate
from growth_engine.discovery import import_search_leads, parse_rss, parse_telegram, reddit_authorized, _public_url
from growth_engine.human_voice import generate_viral_variants_prompt, run_human_style_pipeline
from growth_engine.hunt import collector_health, hunt_materials, production_dry_run, scheduled_collection
from growth_engine.viral_admission import PREVIEW_MODE, PRODUCTION_MODE, WEIGHTS, auto_rate_material, rank_materials, score_material, material_hash
from growth_engine.x_native_style import review_comment_impulse, review_x_native_style
from tests.topic_helpers import AS_OF, material
from tests.test_human_style_production import candidate


RSS = '''<rss><channel><item><title>一笔账</title><link>https://example.com/story</link>
<pubDate>Fri, 16 Oct 2026 09:00:00 +0800</pubDate><description><![CDATA[<p>业主付了500元。物业却发来一张1000元账单。</p>]]></description></item></channel></rss>'''
TG = '''<div class="tgme_widget_message" data-post="channel_test/12"><div>
<div class="tgme_widget_message_text">家属收到一份通报。<br>记者看到500元赔偿单。</div>
<span class="tgme_widget_message_views">1.2K</span><time datetime="2026-10-16T01:00:00+00:00"></time></div></div>'''


class DiscoveryTests(unittest.TestCase):
    def test_rss_records_original_time_and_fetch_scope_not_fact_truth(self):
        m = parse_rss(RSS, 'https://example.com/feed', AS_OF)[0]
        self.assertEqual(m['source']['published_at'], '2026-10-16T01:00:00Z')
        self.assertEqual(m['source']['fact_verification'], 'UNVERIFIED')
        self.assertFalse(m['human_checked'])
        self.assertEqual(m['review']['novelty_scope'], 'EXACT_TITLE_CONTENT_HASH_ONLY')
        self.assertNotIn('<p>', m['text'])

    def test_atom_and_unknown_dates_never_use_capture_time(self):
        body = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>公开线索</title><link href="https://example.com/a"/><summary>正文</summary></entry></feed>'
        m = parse_rss(body, 'https://example.com/feed', AS_OF)[0]
        self.assertIsNone(m['source']['published_at'])
        self.assertIn('UNKNOWN_SOURCE_TIMESTAMP', score_material(m, as_of=AS_OF)['reasons'])

    def test_telegram_nested_html_keeps_approximate_views_as_text(self):
        m = parse_telegram(TG, AS_OF)[0]
        self.assertEqual(m['source']['url'], 'https://t.me/channel_test/12')
        self.assertEqual(m['source']['views_display'], '1.2K')
        self.assertIsNone(m['source']['views'])
        self.assertIn('记者看到500元', m['text'])
        self.assertFalse(m['source']['media_inspected'])

    def test_telegram_self_closing_tags_do_not_lose_dates_or_next_post(self):
        m = parse_telegram(TG.replace('<br>', '<br/><img src="x"/>')+TG.replace('/12','/13'), AS_OF)
        self.assertEqual(len(m), 2)
        self.assertTrue(all(row['source']['published_at'] for row in m))

    def test_dedup_against_run_and_prior_hashes(self):
        p = auto_discover_materials(rss_urls=['https://example.com/a','https://example.com/b'], as_of=AS_OF, fetcher=lambda _: RSS)
        self.assertEqual(len(p['materials']), 1)
        self.assertEqual(p['collection']['duplicates'], 1)
        second = auto_discover_materials(rss_urls=['https://example.com/a'], seen_hashes=[p['materials'][0]['content_hash']], as_of=AS_OF, fetcher=lambda _: RSS)
        self.assertEqual(second['materials'], [])

    def test_source_failure_does_not_erase_success(self):
        def fetch(url):
            if url.endswith('bad'): raise TimeoutError('source timeout')
            return RSS
        p = auto_discover_materials(rss_urls=['https://example.com/bad','https://example.com/good'], as_of=AS_OF, fetcher=fetch)
        self.assertEqual(len(p['errors']), 1)
        self.assertEqual(p['collection']['under24h'], 1)

    def test_reddit_does_not_request_without_verified_rights(self):
        with patch('growth_engine.discovery.fetch_public') as fetch:
            p = auto_discover_materials(rss_urls=[], reddit_communities=['China_irl'], as_of=AS_OF)
        fetch.assert_not_called()
        self.assertEqual(p['errors'][0]['reason'], 'HOLD_AUTHORIZATION_AND_USE_RIGHTS')

    def test_authorized_reddit_parser_retains_metrics_and_source_time(self):
        rights = {'verified': True, 'rights_reference':'documented-use-grant', 'expires_at':'2027-01-01T00:00:00Z','subreddits':['China_irl']}
        data = {'data': {'children': [{'data': {'title':'一笔钱','selftext':'当事人收到500元。','created_utc':1792112400,
            'permalink':'/r/China_irl/comments/abc/title/','score':12,'num_comments':None}}]}}
        p = auto_discover_materials(rss_urls=[], reddit_communities=['China_irl'], reddit_authorization=rights,
            as_of=AS_OF, fetcher=lambda _: json.dumps(data))
        self.assertEqual(p['materials'][0]['source']['score'], 12)
        self.assertIsNone(p['materials'][0]['source']['comments'])
        self.assertFalse(reddit_authorized(rights, ['other'], AS_OF))
        self.assertFalse(reddit_authorized({**rights,'expires_at':'2026-10-16T02:00:00Z'}, ['China_irl'], AS_OF))

    def test_authorized_hot_and_daily_top_routes_are_both_supported(self):
        rights = {'verified':True,'rights_reference':'grant','expires_at':'2027-01-01T00:00:00Z','subreddits':['China_irl']}
        urls = []
        def fetch(url):
            urls.append(url)
            return '{"data":{"children":[]}}'
        for order in ['hot', 'top']:
            auto_discover_materials(rss_urls=[], reddit_communities=['China_irl'],reddit_authorization=rights,
                reddit_sort=order, as_of=AS_OF,fetcher=fetch)
        self.assertIn('/hot.json?limit=20',urls[0])
        self.assertIn('/top.json?t=day',urls[1])

    def test_hacker_news_official_top_best_new_are_supported(self):
        urls=[]
        def fetch(url):
            urls.append(url)
            if 'stories.json' in url: return '[101]'
            return json.dumps({'id':101,'type':'story','title':'A public release','url':'https://example.com/release',
                               'time':1792112400,'score':20,'descendants':4,'by':'author'})
        packet=auto_discover_materials(rss_urls=[],hacker_news=['top','best','new'],as_of=AS_OF,fetcher=fetch)
        self.assertEqual(packet['materials'][0]['source']['family'],'HACKER_NEWS')
        self.assertTrue(any('/topstories.json' in url for url in urls))
        self.assertTrue(any('/beststories.json' in url for url in urls))
        self.assertTrue(any('/newstories.json' in url for url in urls))

    def test_network_boundary_rejects_private_x_credentials_and_dtd(self):
        for url in ['http://example.com', 'https://x.com/a', 'https://user:pass@example.com', 'https://reddit.com/r/a']:
            with self.subTest(url=url), self.assertRaises(ValueError): _public_url(url)
        with patch('growth_engine.discovery.socket.getaddrinfo', return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError): _public_url('https://localhost')
        with self.assertRaises(ValueError): parse_rss('<!DOCTYPE rss><rss/>','https://example.com',AS_OF)


class HuntAdmissionTests(unittest.TestCase):
    def test_social_payoff_can_beat_broad_serious_conflict_without_authority_bonus(self):
        funny = material('funny'); serious = material('serious')
        # Same source quality and first-screen clarity. One has a concrete
        # surprise and a forwarding audience, the other merely broad stakes.
        ratings = {'funny': [3, 4, 0, 3, 4, 2, 4, 2],
                   'serious': [3, 2, 4, 3, 4, 4, 1, 2]}
        for m in (funny, serious):
            for key, value in zip(WEIGHTS, ratings[m['material_id']]):
                m['review'][key]['rating'] = value
        result = rank_materials([serious, funny], as_of=AS_OF, admission_mode=PRODUCTION_MODE)
        self.assertEqual(result['top1']['material_id'], 'funny')
        self.assertEqual(result['second_stage_judge']['winner'], 'funny')
        before = score_material(serious, as_of=AS_OF)['editorial_topic_score']
        serious['source'].update(publisher='国家权威通讯社', family='CHINESE_MEDIA')
        self.assertEqual(score_material(serious, as_of=AS_OF)['editorial_topic_score'], before)

    def test_editor_and_user_veto_survive_perfect_topic_ratings(self):
        m = material()
        m['review']['decision'] = 'HOLD'
        self.assertIn('TOPIC_EDITOR_HOLD', score_material(m, as_of=AS_OF)['reasons'])
        self.assertFalse(score_material(m, as_of=AS_OF)['admitted'])
        m['review']['decision'] = 'PASS'; m['user_content_verdict'] = 'REJECT'
        self.assertIn('CONTENT_USER_REJECTED', score_material(m, as_of=AS_OF)['reasons'])
        self.assertFalse(score_material(m, as_of=AS_OF)['admitted'])

    def test_interesting_recollection_cannot_borrow_recent_republication_date(self):
        m = material(); m['source']['event_time'] = '2022'
        result = score_material(m, as_of=AS_OF)
        self.assertIsNone(result['source_age_hours'])
        self.assertIn('UNKNOWN_SOURCE_TIMESTAMP', result['reasons'])
        self.assertFalse(result['admitted'])

    def test_single_material_preview_passes_but_production_fails(self):
        preview = rank_materials([material()], as_of=AS_OF)
        self.assertEqual(preview['selected_material_ids'], ['m1'])
        self.assertEqual(preview['status'], PREVIEW_MODE)
        production = rank_materials([material()], as_of=AS_OF, admission_mode=PRODUCTION_MODE)
        self.assertFalse(production['competition_passed'])
        self.assertIn('FAIL_INSUFFICIENT_PRODUCTION_COMPETITION', production['pool_reasons'])

    def test_preview_top_n_never_means_production_admission(self):
        pool = [material(str(i),4) for i in range(7)]
        self.assertEqual(len(rank_materials(pool,as_of=AS_OF)['selected_material_ids']), 5)
        self.assertEqual(len(rank_materials(pool,as_of=AS_OF,top_n=2)['selected_material_ids']), 2)
        production = rank_materials(pool,as_of=AS_OF,admission_mode=PRODUCTION_MODE)
        self.assertEqual(production['selected_material_ids'], [])

    def test_auto_screen_does_not_fill_editorial_dimensions(self):
        m = parse_rss(RSS, 'https://example.com/feed', AS_OF)[0]
        p = auto_rate_material(m)
        self.assertIn('auto_screen', p)
        self.assertNotIn('mass_relevance', p['review'])
        report = score_material(p, as_of=AS_OF)
        self.assertIsNone(report['editorial_topic_score'])
        self.assertFalse(report['admitted'])

    def test_censorship_and_artifact_words_alone_do_not_create_evidence_bonus(self):
        m = material(); m['text'] += '据称被删，404，截图，热搜。'
        self.assertEqual(score_material(m,as_of=AS_OF)['viral_bonus']['censorship_scarcity_bonus'], 0)
        m['verified_evidence'] = {'censorship':{'status':'VERIFIED','url':'https://example.com/archive',
            'evidence':'500元账单','reason':'归档明确记录该原文链接的具体删除处置，已复核原始记录。'}}
        self.assertEqual(score_material(m,as_of=AS_OF)['viral_bonus']['censorship_scarcity_bonus'], 8)
        m['verified_evidence']['censorship']['status'] = 'CLAIMED'
        self.assertEqual(score_material(m,as_of=AS_OF)['viral_bonus']['censorship_scarcity_bonus'], 0)

    def test_discovered_source_requires_fact_review_before_production_ready(self):
        c = candidate()
        c['material_pool'][0]['source']['fact_verification'] = 'UNVERIFIED'
        c['material_hash'] = material_hash(c['material_pool'][0])
        self.assertIn('HOLD_DISCOVERED_SOURCE_FACT_REVIEW', prepare_candidate(c)['editorial_gate']['reasons'])
        c['source_fact_review'] = {'status':'FACT_BOUNDARIES_REVIEWED','url':c['source_refs'][0],
            'evidence':'500元账单','reason':'原文逐字核对账单金额和当事人归因，不把其自述当作独立证实事实。'}
        from tests.topic_helpers import add_test_final_review
        add_test_final_review(c, c['material_pool'][0])
        self.assertEqual(prepare_candidate(c)['state'], 'READY_FOR_MANUAL_PUBLISH')

    def test_hunt_runs_actual_style_and_fact_pipeline_without_inventing_ready(self):
        p = hunt_materials([material()], as_of=AS_OF)
        self.assertEqual(len(p['drafts']), 1)
        draft = p['drafts'][0]
        self.assertTrue(draft['human_style_preview']['fact_preservation_report']['passed'])
        self.assertFalse(draft['publication_allowed'])
        self.assertFalse(draft['agent_checked'])
        self.assertEqual(draft['variants_prompt']['executor'], 'Codex')

    def test_queries_and_offline_cli_are_provider_neutral(self):
        self.assertTrue(any('site:x.com' in q for q in build_search_queries()))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'materials.json'; output = Path(directory)/'drafts.json'
            source.write_text(json.dumps([material()]))
            run = subprocess.run([sys.executable,'-m','growth_engine','hunt','--materials',str(source),
                                  '--output',str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(output.read_text())
            self.assertEqual(result['engine'], 'CODEX_VIRAL_HUNT_V2')
            self.assertFalse(result['publication_allowed'])

    def test_search_lead_requires_checked_original_page(self):
        lead = {'title':'公开页','target_url':'https://example.com/story','query':'公开搜索',
                'original_page_text':'原页面写明朋友散场后收到一张账单。','original_page_status':'SEARCH_SNIPPET_ONLY'}
        with patch('growth_engine.discovery.socket.getaddrinfo', return_value=[(2,1,6,'',('93.184.216.34',443))]):
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_PAGE_CHECKED'):
                import_search_leads([lead], captured_at=AS_OF)

    def test_collector_health_and_manual_collection_never_publish(self):
        stale = {'as_of':'2026-10-15T00:00:00Z','source_families':['TELEGRAM'],
                 'collection':{'latest_run_completed_at':'2026-10-15T00:00:00Z','under24h':2,'between24and48h':0}}
        health = collector_health(stale, now=AS_OF)
        self.assertEqual(set(health['reasons']), {'STALE','LOW_SOURCE_DIVERSITY','INSUFFICIENT_FRESH_MATERIAL'})
        with tempfile.TemporaryDirectory() as directory:
            packet = scheduled_collection(output_root=Path(directory), rss_urls=['https://example.com/feed'],
                telegram_channels=(), as_of=AS_OF, fetcher=lambda _: RSS)
            self.assertFalse(packet['publication_triggered'])
            self.assertFalse(packet['automatic_x_submission'])
            self.assertTrue(Path(packet['paths']['latest']).exists())
        workflow = Path('.github/workflows/viral-hunt.yml').read_text()
        self.assertIn('workflow_dispatch:', workflow)
        self.assertNotIn('17 */4 * * *', workflow)
        self.assertIn('collect-feed', workflow)
        self.assertNotIn('pre_publish_assert', workflow)
        self.assertNotIn('x.com/compose', workflow)

    def test_saved_real_multisource_dry_run_has_one_winner_and_three_safe_previews(self):
        feed=json.loads(Path('data/viral_feed/2026-10-17/1256.json').read_text())
        reviews=json.loads(Path('data/viral_hunt_deep_reviews_2026-10-17.json').read_text())
        result=production_dry_run(feed,reviews); ranking=result['ranking']
        self.assertEqual(ranking['raw_count'],83)
        self.assertEqual(ranking['reviewed_source_count'],20)
        self.assertEqual(ranking['source_family_count'],4)
        self.assertEqual(len(ranking['selected_material_ids']),1)
        self.assertEqual(len(result['top1_previews']),3)
        self.assertTrue(all(row['human_style_passed'] for row in result['top1_previews']))
        self.assertFalse(result['publication_allowed'])

    def test_existing_report_and_audit_cli_are_not_shadowed_by_ranking_variable(self):
        with tempfile.TemporaryDirectory() as directory:
            for command in ['report', 'audit']:
                run = subprocess.run([sys.executable,'-m','growth_engine','--db',str(Path(directory)/'test.sqlite3'),command],
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn('x_posts' if command == 'report' else 'stats', json.loads(run.stdout))


class SocialStyleTests(unittest.TestCase):
    def test_old_ai_blockers_and_new_newsroom_residue(self):
        for key in ['balanced_contrast','abstract_conclusion','mechanical_transition','summary_ending','author_verdict','rhetorical_question','abstract_value_chain','fact_to_value_question']:
            self.assertIn(key, PATTERNS)
        text = '业主付了500元。引发了广泛关注。网友们纷纷表示，这不禁让人深思。'
        self.assertIn('newsroom_residue', analyze_ai_flavor(text).matched_patterns)
        self.assertFalse(review_x_native_style(text)['passed'])

    def test_quote_attribution_numbers_and_multiple_sources_survive_segmentation(self):
        text = '记者称，家属收到500元赔偿。\n\n家属说：“网友们纷纷表示。”\n\nhttps://example.com/a\nhttps://example.com/b'
        locks = {'amount':'500元','quote':'“网友们纷纷表示。”','urls':['https://example.com/a','https://example.com/b']}
        p = run_human_style_pipeline({'draft_text':text,'locked_facts':locks,'primary_action':'SHARE'})
        self.assertTrue(p['fact_preservation_report']['passed'],p)
        self.assertIn('记者称', p['rewritten_text'])
        self.assertIn('家属说', p['rewritten_text'])

    def test_social_scene_and_fake_consensus_are_separate(self):
        text = '业主付了500元。物业却发来一张1000元赔偿单。'
        self.assertTrue(review_x_native_style(text)['passed'])
        for text in ['通报被删了，真相，人性，外网，底线。','老板拖欠三个月工资，记者曝光了，合理吗？']:
            self.assertFalse(review_comment_impulse(text)['passed'])

    def test_variants_prompt_never_promises_pass_or_fake_experience(self):
        p = generate_viral_variants_prompt(material())
        self.assertEqual([v['id'] for v in p['variants']], ['A','B','C'])
        self.assertIn('不伪造第一人称', json.dumps(p,ensure_ascii=False))


if __name__ == '__main__': unittest.main()
