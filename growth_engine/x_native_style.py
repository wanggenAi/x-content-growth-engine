"""Deterministic X-native and comment-impulse review signals.

The reviewer uses structural evidence (roles, actions, quantities, boundaries
and competing costs). It avoids a list of historical scene words so new topics
are evaluated by the same contract as old ones.
"""

from __future__ import annotations

import re
from typing import Any

from .ai_flavor_gate import ABSTRACT_NOUNS, analyze_ai_flavor


ROLE_RE = re.compile(r"(?:一个|一位|这位|那个)?(?:网友|当事人|知情人|家属|业主|保安|物业|城管|官方|领导|闺蜜|大爷|大妈|博主|记者|外卖员|网约车司机|男人|女人|男朋友|女朋友|伴侣|丈夫|妻子|前任|朋友|同事|老板|员工|父母|妈妈|爸爸|爸妈|我妈|我爸|孩子|室友|邻居|租客|乘客|客人|店员|服务员|客户|司机|医生|老师|同学|学生|游客|家人|新人|老人|顾客|雇主|雇员|她|他|我|我们|对方)")
ACTION_RE = re.compile(r"(?:删帖|封号|禁言|撤热搜|通报|辟谣|曝光|实名举报|录音|截图|背刺|反转|拉黑|跑路|维权|瞒报|甩锅|算账|给|拿|说|买|删|回|借|等|住|打|发|收|转|付|抢|退|换|问|看|做|带|躲|关|开|送|约|见|分|存|管|领|加|辞|搬|吃|喝|睡|签|改|拒绝|允许|不同意|公开|隐藏|联系|取消|安排|比较|支付|请|记|算|收走)")
QUANTITY_RE = re.compile(r"(?:\d+(?:\.\d+)?\s*(?:万|亿|元|块|岁|人|小时|分钟|点|次|天|个月|年|公里|米)?|[一二三四五六七八九十百千万两]+(?:个)?(?:次|年|个月|天|小时|分钟|块|元|人|岁))")
TIME_RE = re.compile(r"(?:凌晨|早上|上午|中午|下午|晚上|半夜)?\s*\d{1,2}(?::\d{1,2})?(?:点|时)?|(?:今天|昨天|明天|上周|今年|去年|三年|多年)")
OBJECT_RE = re.compile(r"(?:聊天记录|微信群|通告|截图|监控录像|监控|视频|词条|热搜|赔偿|嫁妆|编制|烂尾楼|贷款|医药费|工资|收入|账单|房租|房子|照片|消息|电话|合同|红包|礼物|车票|机票|饭|火锅|钱|账户|订单|钥匙|门|行李|手机|电脑|药|包|床位|房间|椅子|朋友圈|聊天|工作|岗位|考试|学费|彩礼|借款|存款|加班|假期|家|酒店|餐厅|飞机|高铁)")
QUOTE_RE = re.compile(r"[\"“”『』「」‘’].+?[\"“”『』「」‘’]")
LOCATION_RE = re.compile(r"(?:在|从|到|回|住在|来自)[\u4e00-\u9fff]{1,12}(?:，|。|、|的|上|里|中|$)")
BOUNDARY_RE = {
    "censorship_truth_boundary": re.compile(r"被删|404|发不出来|夹了|捂嘴|通报|真相|外网|墙内|热搜消失"),
    "human_nature_boundary": re.compile(r"人性|底线|凉薄|算计|白眼狼|救命|落井下石|真面目|利益面前|大难临头"),
    "relationship_boundary": re.compile(r"(?:恋爱|结婚|男朋友|女朋友|伴侣|前任|朋友|家人|妈妈|爸爸|父母|夫妻|相亲|约会|室友|陌生人|朋友圈|发照片|公开|联系|已读|删除)"),
    "money_boundary": re.compile(r"(?:钱|工资|收入|房租|借款|借钱|还钱|转账|账单|分摊|AA|买单|请客|存款|存着|花钱|消费|彩礼|红包|价格|贵|便宜|失业|酒店)"),
    "privacy_boundary": re.compile(r"(?:隐私|私下|公开|照片|消息|聊天|手机|账号|密码|朋友圈|已读|删除|不发|不说|逐笔|陌生人|房间|控制)"),
}
TRADEOFF_RE = re.compile(r"(?:收入|工资|成本|价格|时间|精力|风险|机会|面子|便利|自由|安全|照顾|责任|隐私|公开|公平|方便|麻烦|压力)")
CONSENSUS_RE = re.compile(r"(?:克扣|拖欠|少发|不给[^。！？!?]{0,8}工资|骗取|诈骗|殴打|推倒|打人|打了|盗用|强迫|威胁|违法|未成年|伤害|明显不合理|凭什么\s*让|不应该发生|全部拿走)")


def _body(text: str) -> str:
    return re.sub(r"https?://\S+", "", text or "").strip()


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?\n]+", _body(text)) if item.strip()]


def _score(value: float) -> int:
    return max(0, min(100, round(value)))


def extract_scene_features(text: str | None) -> dict[str, Any]:
    """Return topic-agnostic scene evidence used by both native gates."""
    body = _body(text or "")
    sentences = _sentences(body)
    roles = sorted(set(ROLE_RE.findall(body)))
    actions = sorted(set(ACTION_RE.findall(body)))
    quantities = QUANTITY_RE.findall(body)
    times = TIME_RE.findall(body)
    objects = sorted(set(OBJECT_RE.findall(body)))
    quotes = QUOTE_RE.findall(body)
    event_chain = len(actions) >= 2 and (len(sentences) >= 2 or len(quantities) >= 1)
    return {
        "concrete_entity": bool(roles), "entity_count": len(roles), "entities": roles,
        "concrete_action": bool(actions), "action_count": len(actions), "actions": actions,
        "concrete_quantity": bool(quantities), "quantity_count": len(quantities), "time_count": len(times),
        "direct_quote": bool(quotes), "specific_object": bool(objects), "object_count": len(objects),
        "event_chain": event_chain, "location_hint": bool(LOCATION_RE.search(body)),
    }


def _opinion_model(text: str) -> dict[str, Any]:
    body = _body(text)
    scene = extract_scene_features(body)
    stakeholders = scene["entity_count"]
    boundary_flags = {key: bool(pattern.search(body)) for key, pattern in BOUNDARY_RE.items()}
    # Topic labels alone must not manufacture two reasonable positions.
    public_tradeoff = bool(re.search(r"公开|知情|透明|披露", body) and re.search(r"隐私|核实|安全|规则|调查", body))
    boundary_flags["censorship_truth_boundary"] &= public_tradeoff and stakeholders >= 2
    boundary_flags["human_nature_boundary"] &= scene["event_chain"] and stakeholders >= 2 and bool(TRADEOFF_RE.search(body))
    categories = sum(boundary_flags.values())
    work_tradeoff = bool(re.search(r"(?:加班|升职|责任心|努力|绩效)", body)) and stakeholders >= 1
    cost_tradeoff = (bool(TRADEOFF_RE.search(body)) and (stakeholders >= 2 or scene["quantity_count"] >= 1)) or \
        (boundary_flags["money_boundary"] and scene["quantity_count"] >= 2) or work_tradeoff
    identity_split = stakeholders >= 2 and bool(re.search(r"(?:我|他|她|对方|别人|父母|老板|员工|朋友|学生|游客|客户|雇主|雇员)", body))
    experience_split = bool(re.search(r"(?:从没|一次都没|每次|一直|已经|却|只|才|比我|比他|知道|现实|网上|公开|私下)", body))
    norm_conflict = categories >= 2 or bool(re.search(r"(?:应该|可以|能不能|算不算|到底|是否|合不合适|不同意|没地方|只能|加班|升职|责任心|努力)", body))
    # Harm/rights violations remain consensus cases even when the text also
    # contains family or money vocabulary. A second topic marker must not turn
    # a fake debate into a genuine opinion fork.
    fairness_consensus = bool(CONSENSUS_RE.search(body))
    question = bool(re.search(r"[？?]", body))
    obvious_probability = 0.86 if fairness_consensus and question else 0.72 if fairness_consensus else 0.24
    branches: list[dict[str, str]] = []
    if boundary_flags["relationship_boundary"]:
        branches.append({"direction": "relationship_boundary", "basis": "公开程度与现实承诺的权重不同"})
    if boundary_flags["money_boundary"]:
        branches.append({"direction": "money_boundary", "basis": "公平分摊与照顾关系的成本不同"})
    if boundary_flags["privacy_boundary"]:
        branches.append({"direction": "privacy_boundary", "basis": "个人隐私与关系确认的边界不同"})
    if boundary_flags["censorship_truth_boundary"]:
        branches.append({"direction": "public_transparency", "basis": "公众知情与隐私、调查核实或安全之间有具体代价"})
    if boundary_flags["human_nature_boundary"]:
        branches.append({"direction": "relationship_cost", "basis": "不同当事人在具体动作中承担的利益和关系成本不同"})
    if cost_tradeoff:
        branches.append({"direction": "cost_tradeoff", "basis": "时间、收入或精力的交换不同"})
    if norm_conflict and len(branches) < 2:
        branches.append({"direction": "norm_conflict", "basis": "规则、责任或现实限制的取舍不同"})
    if identity_split and len(branches) < 2:
        branches.append({"direction": "identity_experience", "basis": "不同角色承担的代价不同"})
    branches = branches[:4]
    real_branch = len({item["direction"] for item in branches}) >= 2 and not fairness_consensus
    return {
        "stakeholder_count": stakeholders, "competing_interests": categories >= 2 or cost_tradeoff or (norm_conflict and stakeholders >= 2),
        "identity_split": identity_split, "experience_split": experience_split, "norm_conflict": norm_conflict,
        "cost_tradeoff": cost_tradeoff, **boundary_flags, "fairness_consensus": fairness_consensus,
        "obvious_answer_probability": obvious_probability, "possible_reply_branches": branches,
        "opinion_branching": real_branch,
    }


def review_x_native_style(text: str | None, primary_action: str | None = None) -> dict[str, Any]:
    """Review concrete, compressed, human-shaped X writing."""
    text = text or ""
    sentences = _sentences(text)
    report = analyze_ai_flavor(text)
    body = _body(text)
    scene = extract_scene_features(body)
    chars = len(re.findall(r"[\u4e00-\u9fff]", body))
    abstract = sum(body.count(term) for term in ABSTRACT_NOUNS)
    first = sentences[0] if sentences else ""
    concrete_points = sum(scene[key] for key in ("concrete_entity", "concrete_action", "concrete_quantity", "direct_quote", "specific_object", "event_chain"))
    first_screen = _score(42 + min(30, len(first) * 0.75) + concrete_points * 4 - (22 if len(first) > 70 else 0))
    scene_score = _score(30 + concrete_points * 11 + min(16, scene["entity_count"] * 4))
    reaction = _score(42 + (16 if re.search(r"我|我的|却|居然|偏偏|没想到", body) else 0) + (12 if scene["direct_quote"] else 0))
    lengths = [len(item) for item in sentences]
    rhythm = _score(52 + min(25, (max(lengths) - min(lengths)) if lengths else 0) - (18 if lengths and len(set(lengths)) == 1 and len(lengths) >= 3 else 0))
    abstractness = _score(94 - (abstract / max(chars, 1)) * 1300)
    explanation = _score(92 - report.pattern_counts.get("mechanical_explanation", 0) * 25 - report.pattern_counts.get("over_explanation", 0) * 30)
    overreach = _score(94 - report.pattern_counts.get("summary_ending", 0) * 45 - report.pattern_counts.get("author_verdict", 0) * 40 - report.pattern_counts.get("rhetorical_question", 0) * 18)
    dimensions = {
        "first_screen_stopping_power": first_screen, "scene_concreteness": scene_score,
        "human_reaction": reaction, "sentence_rhythm": rhythm, "abstractness": abstractness,
        "explanation_overload": explanation, "conclusion_overreach": overreach,
        "open_ending": 82 if not re.search(r"(?:所以|这才是|值得我们思考|大家觉得呢|你怎么看)[^。！？!?]*[。！？!?]?$", body) else 32,
    }
    hard_blockers: list[str] = []
    if report.blocked:
        hard_blockers.append("ai_flavor_blocked")
    if report.pattern_counts.get("author_verdict") or report.pattern_counts.get("summary_ending"):
        hard_blockers.append("author_verdict")
    if report.pattern_counts.get("forced_humanization"):
        hard_blockers.append("forced_humanization")
    if report.pattern_counts.get("fact_to_value_question"):
        hard_blockers.append("obvious_ai_moral_question")
    if report.pattern_counts.get("newsroom_residue"):
        hard_blockers.append("newsroom_residue")
    reasons = list(hard_blockers)
    if len(sentences) >= 5 and abstractness < 60:
        reasons.append("essay_like_abstraction")
    if explanation < 60:
        reasons.append("explanation_overload")
    if scene_score < 52:
        reasons.append("scene_needs_concrete_detail")
    soft_score = _score(sum(dimensions.values()) / len(dimensions))
    passed = not hard_blockers and soft_score >= 62 and scene_score >= 52
    return {"passed": passed, "status": "PASS" if passed else "FAIL", "score": soft_score, "soft_score": soft_score,
            "hard_blockers": hard_blockers, "dimensions": dimensions, "scene_features": scene,
            "reasons": reasons, "sentence_count": len(sentences)}


def review_comment_impulse(text: str | None, primary_action: str = "REPLY") -> dict[str, Any]:
    """Require a genuine social fork, independent of explicit transition words."""
    if primary_action != "REPLY":
        return {"passed": True, "status": "NOT_APPLICABLE", "reason": "primary_action_is_not_REPLY", "possible_reply_branches": []}
    body = _body(text or "")
    sentences = _sentences(body)
    model = _opinion_model(body)
    self_insertion = bool(re.search(r"我|我的|自己|换成|身边|我家|我们", body))
    low_friction = 1 <= len(sentences) <= 6 and len(body) <= 240
    obvious_penalty = 78 if model["obvious_answer_probability"] >= 0.8 else 0
    score = 0
    score += 16 if self_insertion else 0
    score += 15 if model["stakeholder_count"] >= 2 else 0
    score += 17 if model["competing_interests"] else 0
    score += 22 if model["opinion_branching"] else 0
    score += 12 if model["experience_split"] else 0
    score += 10 if low_friction else 0
    open_detail = bool(sentences and not re.search(r"[？?]$|你怎么看|大家觉得", body)
                       and (QUOTE_RE.search(sentences[-1]) or QUANTITY_RE.search(sentences[-1])))
    detail_bonus = 6 if open_detail and model["opinion_branching"] and not model["fairness_consensus"] else 0
    score = _score(score + detail_bonus - obvious_penalty)
    reasons: list[str] = []
    if obvious_penalty:
        reasons.append("obvious_answer_penalty")
    if not model["opinion_branching"]:
        reasons.append("FAIL_NO_REAL_BRANCH")
    if not low_friction:
        reasons.append("reply_friction_high")
    passed = score >= 48 and model["opinion_branching"] and not obvious_penalty
    return {"passed": passed, "status": "PASS" if passed else "FAIL", "score": score,
            "open_detail_bonus": detail_bonus, "self_insertion": self_insertion, "real_tradeoff": model["competing_interests"],
            "opinion_branching": model["opinion_branching"], "identity_trigger": model["identity_split"],
            "experience_trigger": model["experience_split"], "low_reply_friction": low_friction,
            "obvious_answer_penalty": obvious_penalty, "reasons": reasons, **model}
