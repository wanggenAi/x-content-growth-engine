"""Test-only grounded fixtures. Production must never import this module."""
from copy import deepcopy
from growth_engine.human_voice import stable_hash
from growth_engine.reader_model import empty_value_profile, reader_context
from growth_engine.viral_admission import WEIGHTS, material_hash

AS_OF = '2026-10-16T02:00:00Z'


def material(mid='m1', rating=4):
    text = '朋友聚餐后给我发来一张500元账单。' + ('第'+mid+'场聚餐。' if mid != 'm1' else '')
    proof = {'evidence': '500元账单', 'reason': '聚餐的关系与分账成本具体可见，仍是待反馈检验的编辑判断。'}
    review = {k: dict(proof, rating=rating) for k in WEIGHTS}
    review.update(audience_distance=dict(proof, value='NEAR'), background_cost=dict(proof, value='LOW'),
                  hook=dict(proof, text='聚餐后才收到500元账单'), novelty='CHECKED_DISTINCT')
    return {'material_id': mid, 'event_id': mid, 'topic': '朋友聚餐分账', 'text': text,
            'source': {'url': 'https://example.com/'+mid, 'published_at': '2026-10-16T00:00:00Z',
                       'timestamp_precision': 'SECOND', 'evidence_text': text, 'status': 'SOURCE_CHECKED', 'confidence': 'SELF_REPORT'},
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
    pool = [material()] + [material('m'+str(n), rating=1) for n in range(2,11)]
    pool[0]['draft_text'] = candidate['text']
    candidate.update(material_id='m1', material_hash=material_hash(pool[0]), material_pool=pool,
                     competition_as_of=AS_OF, source_refs=[pool[0]['source']['url']])
    candidate['reader_model']=grounded_profile(candidate)
    return candidate
