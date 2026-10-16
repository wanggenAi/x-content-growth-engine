"""X-native style and comment-impulse review signals."""

from __future__ import annotations

import re
from typing import Any

from .ai_flavor_gate import ABSTRACT_NOUNS, analyze_ai_flavor


def _body(text: str) -> str:
    return re.sub(r"https?://\S+", "", text or "").strip()


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[。！？!?\n]+", _body(text)) if item.strip()]


def _score(value: float) -> int:
    return max(0, min(100, round(value)))


def review_x_native_style(text: str | None) -> dict[str, Any]:
    """Review whether a draft reads like a concrete X post rather than an essay."""
    text = text or ""
    sentences = _sentences(text)
    report = analyze_ai_flavor(text)
    body = _body(text)
    chars = len(re.findall(r"[\u4e00-\u9fff]", body))
    concrete = len(re.findall(r"\d|[床柜衣服蜡烛面条工牌打卡宿舍游客生日蛋糕骑手老板工资]", body))
    abstract = sum(body.count(term) for term in ABSTRACT_NOUNS)
    first = sentences[0] if sentences else ""
    first_screen = _score(45 + min(30, len(first) * 0.8) + (18 if concrete else 0) - (20 if len(first) > 60 else 0))
    scene = _score(35 + min(45, concrete * 8) + (12 if re.search(r"[“\"]", body) else 0))
    reaction = _score(42 + (18 if re.search(r"我|让人|真的|居然|却|偏偏", body) else 0) + (15 if re.search(r"[“\"]", body) else 0))
    rhythm = _score(55 + min(25, report.sentence_stats.get("stdev", 0) * 4) - (20 if report.sentence_stats.get("stdev", 0) < 2 else 0))
    abstractness = _score(92 - (abstract / max(chars, 1)) * 1200)
    explanation = _score(90 - report.pattern_counts.get("mechanical_explanation", 0) * 25 - report.pattern_counts.get("over_explanation", 0) * 30)
    overreach = _score(92 - report.pattern_counts.get("summary_ending", 0) * 45 - report.pattern_counts.get("author_verdict", 0) * 38 - report.pattern_counts.get("rhetorical_question", 0) * 18)
    scores = {
        "first_screen_stopping_power": first_screen,
        "scene_concreteness": scene,
        "human_reaction": reaction,
        "sentence_rhythm": rhythm,
        "abstractness": abstractness,
        "explanation_overload": explanation,
        "conclusion_overreach": overreach,
    }
    native = _score(sum(scores.values()) / len(scores))
    reasons: list[str] = []
    if len(sentences) >= 5 and abstractness < 60:
        reasons.append("essay_like_abstraction")
    if report.pattern_counts.get("fact_to_value_question"):
        reasons.append("fact_to_value_moral_question")
    if explanation < 60:
        reasons.append("explanation_overload")
    if overreach < 60:
        reasons.append("conclusion_overreach")
    if scene < 55:
        reasons.append("scene_needs_concrete_detail")
    passed = native >= 62 and not {"essay_like_abstraction", "fact_to_value_moral_question", "conclusion_overreach"}.intersection(reasons)
    return {"passed": passed, "status": "PASS" if passed else "FAIL", "score": native,
            "dimensions": scores, "reasons": reasons, "sentence_count": len(sentences)}


def review_comment_impulse(text: str | None, primary_action: str = "REPLY") -> dict[str, Any]:
    """Require a real opinion fork for replies; do not manufacture a question."""
    if primary_action != "REPLY":
        return {"passed": True, "status": "NOT_APPLICABLE", "reason": "primary_action_is_not_REPLY"}
    text = text or ""
    body = _body(text)
    sentences = _sentences(text)
    self_insertion = bool(re.search(r"我|我的|自己|家里|上班|打工|身边|换成", body))
    identity_trigger = bool(re.search(r"学生|工人|老板|父母|妈妈|伴侣|夫妻|朋友|骑手|租客|打工人", body))
    experience_trigger = bool(re.search(r"床|柜子|衣服|打卡|生日|工资|房租|面条|蛋糕|加班|借钱|送礼", body))
    real_tradeoff = bool(re.search(r"但是|但|不过|同时|既.{0,12}又|也可以|两边|有人会|也有人|取决于", body))
    branch = real_tradeoff or bool(re.search(r"(?:同意|不同意|能理解|难说|不好说).{0,18}(?:但|不过|也)", body))
    obvious_cues = bool(re.search(r"(?:凭什么|难道|为什么|公平吗|应该吗|这合理吗|道德吗|谁能接受|必须|当然不)[^。！？!?]{0,45}[？?]?$", body))
    moral_consensus = bool(re.search(r"(?:工牌只记|提前干的活|不让人|不给|克扣|侵犯|不公平|凭什么)", body))
    obvious_penalty = 78 if obvious_cues and moral_consensus and not real_tradeoff else 30 if obvious_cues else 0
    low_friction = 1 <= len(sentences) <= 6 and len(body) <= 210
    score = 0
    score += 18 if self_insertion else 0
    score += 18 if identity_trigger else 0
    score += 18 if experience_trigger else 0
    score += 28 if branch else 0
    score += 12 if low_friction else 0
    score -= obvious_penalty
    score = _score(score)
    reasons: list[str] = []
    if obvious_penalty:
        reasons.append("obvious_answer_penalty")
    if not branch:
        reasons.append("no_natural_opinion_branch")
    if not low_friction:
        reasons.append("reply_friction_high")
    passed = score >= 48 and not obvious_penalty and branch
    return {"passed": passed, "status": "PASS" if passed else "FAIL", "score": score,
            "self_insertion": self_insertion, "real_tradeoff": real_tradeoff,
            "opinion_branching": branch, "identity_trigger": identity_trigger,
            "experience_trigger": experience_trigger, "low_reply_friction": low_friction,
            "obvious_answer_penalty": obvious_penalty, "reasons": reasons}

