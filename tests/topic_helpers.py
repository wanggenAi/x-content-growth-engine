"""Test-only grounded fixtures. Production must never import this module."""
from copy import deepcopy
from growth_engine.human_voice import stable_hash
from growth_engine.reader_model import empty_value_profile, reader_context
from growth_engine.viral_admission import PRODUCTION_MODE, WEIGHTS, material_hash
from growth_engine.content_review import body_sentences


def text_review(text, sources, memory):
    """Explicitly synthetic source/editor contract; never used by production."""
    first = body_sentences(text)[0]
    return {'method':'TEXT_FIRST_COMPARISON','reviewer':'TEST_ONLY_EDITOR','reviewed_at':AS_OF,
            'text_hash':stable_hash(text),'source_hash':stable_hash(sources),'decision':'PASS','failure_reasons':[],
            'opening':{'quote':first[:20],'reason':'测试夹具中的账单动作可在首句直接理解。'},
            'payoff':{'quote':first[:20],'reason':'测试夹具明确展示账单金额和付款关系的具体事实。'},
            'comparison':{'reference_text':'普通人都需要重视朋友之间的关系和边界。',
                          'reference_failure':'抽象规劝没有人物行动或可以核对的具体交付。',
                          'difference':'当前夹具呈现具体账单，断言仅限合约验证而非真实内容质量。'},
            'novelty':{'memory_hash':stable_hash(memory),'distinct':True,'reason':'测试用空发布记录，不代表真实账号已完成去重。'},
            'claims':[{'draft_span':s,'url':sources[0]['url'],'source_span':sources[0]['excerpt'],
                       'verdict':'SUPPORTED','reason':'合成来源逐字支持这一句，只用于验证绑定行为。'} for s in body_sentences(text)]}

AS_OF = '2026-10-16T02:00:00Z'


def material(mid='m1', rating=4):
    suffix = '第'+mid+'场聚餐。' if mid != 'm1' else ''
    text = ('朋友聚餐后给我发来一张500元账单。原本说好他请客，结果散场后才发账单。'
            '朋友坚持分账，我认为请客约定应该算数。这笔钱够买一周午饭。'
            '聚餐后才收到500元账单。吃饭分账不需要行业背景。有人会照付，也有人会先问清约定。'
            '我会把这张账单发给同桌的人。评论里会分成按账单付和按原约定两种立场。'+suffix)
    evidence = {
        'raw_material_strength':'朋友聚餐后给我发来一张500元账单',
        'surprise':'原本说好他请客，结果散场后才发账单',
        'conflict':'朋友坚持分账，我认为请客约定应该算数',
        'self_insertion':'这笔钱够买一周午饭',
        'first_screen_stopping_power':'聚餐后才收到500元账单',
        'mass_relevance':'吃饭分账不需要行业背景',
        'share_potential':'我会把这张账单发给同桌的人',
        'reply_potential':'评论里会分成按账单付和按原约定两种立场',
    }
    reasons = {
        'raw_material_strength':'金额、动作和当事人关系都在原文里，素材不是抽象观点。',
        'surprise':'先说请客后发账单形成明确预期反差，意外结果由原文支持。',
        'conflict':'朋友双方对请客约定和分账责任有直接利益冲突。',
        'self_insertion':'普通读者能把一周午饭钱映射到自己的日常支出并产生代入。',
        'first_screen_stopping_power':'首屏第一句同时给出朋友、聚餐和500元具体动作，三秒内可懂。',
        'mass_relevance':'吃饭分账是大众日常经验，不需专业背景，随机读者也能理解。',
        'share_potential':'读者可转发给同桌朋友核对分账约定，分享对象明确。',
        'reply_potential':'按账单付款与按原约定处理形成两个真实评论分叉和立场。',
    }
    review = {k: {'evidence':evidence[k], 'reason':reasons[k], 'rating':rating} for k in WEIGHTS}
    review.update(review_type='DEEP_EDITORIAL_REVIEW', reviewer='TEST_EDITOR', reviewed_at=AS_OF,
                  possible_reply_branches=['按账单支付','按请客约定处理'],
                  audience_distance={'evidence':'吃饭分账不需要行业背景','reason':'角色和付款行为是普通读者熟悉的日常关系，不需额外前情。','value':'NEAR'},
                  background_cost={'evidence':'朋友聚餐后给我发来一张500元账单','reason':'一句话即可交代人物、动作与金额，阅读背景成本低。','value':'LOW'},
                  hook={'evidence':'聚餐后才收到500元账单','reason':'首屏直接给出散场后收到具体金额账单的动作。','text':'聚餐后才收到500元账单'}, novelty='CHECKED_DISTINCT')
    family = ('CHINESE_MEDIA','TELEGRAM','HACKER_NEWS','GITHUB')[sum(ord(c) for c in mid) % 4]
    return {'material_id': mid, 'event_id': mid, 'topic': '朋友聚餐分账', 'text': text,
            'source': {'url': 'https://example.com/'+mid, 'published_at': '2026-10-16T00:00:00Z',
                       'timestamp_precision': 'SECOND', 'evidence_text': text, 'status': 'SOURCE_CHECKED',
                       'confidence': 'SELF_REPORT', 'family': family},
            'review': review}


def grounded_profile(candidate):
    p = empty_value_profile()
    p.update(material_strength='HIGH', self_relevance='MEDIUM', evidence_strength='FULL_RECORDED_TEXT',
             novelty_status='CHECKED', acceptable_editorial_mechanism='ACCEPTABLE_WITH_SOURCE_CHECK',
             dominant_reader_value_route='SELF_RELEVANCE',
             reader_value_routes=[{'route':'SELF_RELEVANCE','strength':'MEDIUM','cue':'朋友聚餐后给我发来一张500元账单',
                                   'reader_thought':'聚餐的钱之前说好了吗'}],
             why_reader_cares='朋友聚餐后的账单影响自己付多少钱', predicted_inner_response='朋友这张账单该付吗',
             concrete_stakes='朋友聚餐的500元账单', social_currency='MEDIUM', share_recipient='一起聚餐的朋友',
             share_reason='朋友可以比较聚餐的分账约定', opinion_activation='MEDIUM', opinion_space='MEDIUM',
             activation_mechanisms=['PERSONAL_EXPERIENCE'], annotation_origin='TEST_ONLY_EXPLICIT_REVIEW')
    fields = [k for k in ('why_reader_cares','predicted_inner_response','concrete_stakes','reader_value_routes',
                         'share_recipient','share_reason') if p.get(k)] + ['material_strength']
    p['semantic_binding']={'context_hash':stable_hash(reader_context(candidate)), 'field_evidence':{
        k:{'quote':'500元账单','reason':'正文明确给出聚餐后的账单，是这项假设的具体事实线索。','value_hash':stable_hash(p[k])} for k in fields}}
    return p


def bind_candidate(candidate):
    candidate = deepcopy(candidate)
    pool = [material()] + [material('m'+str(n), rating=1) for n in range(2,31)]
    pool[0]['draft_text'] = candidate['text']
    pool[0]['source'].update(event_time_status='EVENT_DATE_CHECKED')
    pool[0]['source_evidence'] = [{'url':pool[0]['source']['url'],'excerpt':candidate['text']}]
    candidate['publication_memory'] = []
    candidate['content_review'] = text_review(candidate['text'], pool[0]['source_evidence'], [])
    candidate.update(material_id='m1', material_hash=material_hash(pool[0]), material_pool=pool,
                     admission_mode=PRODUCTION_MODE,
                     competition_as_of=AS_OF, source_refs=[pool[0]['source']['url']])
    candidate['reader_model']=grounded_profile(candidate)
    return candidate
