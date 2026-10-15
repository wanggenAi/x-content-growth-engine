"""Local Human Voice pipeline for Chinese X candidates.

This module is intentionally conservative.  It removes known editorial residue,
leaves concrete facts and quotations alone, then reports the independent gates
that still need to pass before publication.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .ai_flavor_gate import AIFlavorReport, analyze_ai_flavor, ai_flavor_passes
from .fact_preservation import check_fact_preservation
from .x_native_style import review_comment_impulse, review_x_native_style


VOICE_VERSION = "HUMAN_VOICE_V1"
URL_RE = re.compile(r"https?://[^\s]+")
QUOTE_RE = re.compile(r"[\"“”『』「」].*?[\"“”『』「」]")
GENERIC_ENDINGS = re.compile(
    r"(?:^|\n)(?:所以|也许这就是|这才是|值得我们思考|这件事让我意识到|真正的问题是|也该|应该|不应该|必须).{0,100}[。！？!?]?\s*$"
)
GENERIC_QUESTIONS = re.compile(r"(?:凭什么|公平吗|这合理吗|大家觉得呢|你怎么看)[？?]?$")


@dataclass(frozen=True)
class VoiceProfile:
    platform: str = "X_ZH"
    sentence_length: str = "mixed"
    short_sentence_ratio: float = 0.55
    abstract_noun_tolerance: str = "LOW"
    conclusion_tolerance: str = "LOW"
    rhetorical_question_tolerance: str = "MEDIUM"
    first_person_tolerance: str = "MEDIUM"
    internet_slang_tolerance: str = "LOW_MEDIUM"
    imperfection_tolerance: str = "MEDIUM"
    explanation_depth: str = "LOW"
    scene_first: bool = True
    concrete_detail_priority: str = "HIGH"


def _profile(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return asdict(VoiceProfile(platform=value or "X_ZH"))


def _protect(text: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f"__HV_PROTECTED_{len(protected)}__"
        protected[token] = match.group(0)
        return token

    return URL_RE.sub(replace, QUOTE_RE.sub(replace, text)), protected


def _restore(text: str, protected: Mapping[str, str]) -> str:
    for token, value in protected.items():
        text = text.replace(token, value)
    return text


def _without_source_link(text: str) -> str:
    return URL_RE.sub("", text).rstrip()


def _trim_generic_tail(text: str, changes: list[str]) -> str:
    body = _without_source_link(text).rstrip()
    link = ""
    match = URL_RE.search(text)
    if match:
        link = match.group(0)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if not paragraphs:
        return text
    tail = paragraphs[-1]
    tail_is_verdict = bool(re.search(
        r"(?:也该|应该|不应该|必须|值得我们思考|没有标准答案|真正的问题是|这才是|也许这就是)"
        r"[^。！？!?]{0,100}[。！？!?]?\s*$", tail
    ))
    if GENERIC_ENDINGS.search("\n".join(paragraphs)) or tail_is_verdict or GENERIC_QUESTIONS.search(tail):
        paragraphs.pop()
        changes.append("removed_author_verdict_or_mechanical_question")
    result = "\n\n".join(paragraphs).strip()
    if link:
        result = f"{result}\n\n{link}" if result else link
    return result


def _conservative_rewrite(text: str) -> tuple[str, list[str]]:
    protected_text, protected = _protect(text)
    changes: list[str] = []
    replacements = (
        (r"救急我能理解\s*[，,。]?\s*但(?:是)?", "救急我能理解。"),
        (r"我能理解\s*[，,。]?\s*但(?:是)?", "我能理解。"),
        (r"更值得关注的是\s*", ""),
        (r"值得注意的是\s*", ""),
        (r"这背后反映的是\s*", ""),
        (r"换句话说\s*", ""),
        (r"从某种意义上说\s*", ""),
        (r"某种程度上\s*", ""),
        (r"真正的问题是\s*", ""),
    )
    for pattern, replacement in replacements:
        new_text, count = re.subn(pattern, replacement, protected_text)
        if count:
            changes.append(f"removed_template:{pattern}")
            protected_text = new_text
    protected_text = re.sub(r"[ \t]+", " ", protected_text)
    protected_text = re.sub(r"\n{3,}", "\n\n", protected_text).strip()
    rewritten = _restore(protected_text, protected)
    rewritten = _trim_generic_tail(rewritten, changes)
    return rewritten, changes


def _raw_reaction(text: str) -> str:
    first = next((part.strip() for part in re.split(r"\n\s*\n|[。！？!?]", text) if part.strip()), "")
    return first[:80]


def _voice_features(text: str, report: AIFlavorReport, reaction: str) -> dict[str, Any]:
    body = _without_source_link(text)
    sentences = [part.strip() for part in re.split(r"[。！？!?\n]+", body) if part.strip()]
    lengths = [len(part) for part in sentences]
    return {
        "raw_human_reaction": reaction,
        "scene_first": bool(sentences and len(sentences[0]) <= 34),
        "short_sentence_ratio": round(sum(length <= 12 for length in lengths) / max(len(lengths), 1), 3),
        "mixed_rhythm": report.sentence_stats.get("stdev", 0) >= 3 or len(lengths) <= 2,
        "open_ending": not bool(GENERIC_ENDINGS.search(body) or (sentences and GENERIC_QUESTIONS.search(sentences[-1]))),
        "concrete_detail_count": len(re.findall(r"\d|[床柜衣服蜡烛面条工牌打卡宿舍游客生日蛋糕]", body)),
    }


def humanize_text(request: Mapping[str, Any]) -> dict[str, Any]:
    """Humanize a draft under a fact-lock contract.

    The function does not invent a new voice, add slang or call a paid model.
    It returns a complete audit object so a provider-backed rewriter can be
    introduced later without bypassing the same gates.
    """
    if not isinstance(request, Mapping):
        raise TypeError("humanize_text expects a mapping")
    draft = str(request.get("draft_text", ""))
    if not draft.strip():
        raise ValueError("draft_text is required")
    locked_facts = request.get("locked_facts")
    warnings: list[str] = []
    if not isinstance(locked_facts, Mapping) or not locked_facts:
        warnings.append("locked_facts_missing")
    profile = _profile(request.get("voice_profile"))
    before_report = analyze_ai_flavor(draft)
    rewritten, changes = _conservative_rewrite(draft)
    after_report = analyze_ai_flavor(rewritten)
    return {
        "rewritten_text": rewritten,
        "changes": changes,
        "voice_features": _voice_features(rewritten, after_report, _raw_reaction(draft)),
        "warnings": warnings,
        "version": VOICE_VERSION,
        "voice_profile": profile,
        "rewrite_applied": rewritten != draft,
        "ai_flavor_before": before_report.to_dict(),
        "ai_flavor_after": after_report.to_dict(),
        "ai_flavor_pass": ai_flavor_passes(after_report),
        "target_platform": request.get("target_platform", "X_ZH"),
        "primary_action": request.get("primary_action"),
        "preserve_quotes": request.get("preserve_quotes", True),
    }


def run_human_voice_pipeline(request: Mapping[str, Any]) -> dict[str, Any]:
    """Run rewrite plus every deterministic voice contract gate.

    The returned ``human_voice`` object is the compact contract consumed by
    ``editorial_gate``.  The detailed reports remain available for replay and
    audit, so a low AI-flavor score cannot hide fact drift or a weak X fit.
    """
    result = humanize_text(request)
    before = str(request.get("draft_text", ""))
    after = result["rewritten_text"]
    locked_facts = request.get("locked_facts", {})
    fact_report = check_fact_preservation(before, after, locked_facts)
    native_report = review_x_native_style(after)
    comment_report = review_comment_impulse(after, str(request.get("primary_action", "REPLY")))
    ai_report = analyze_ai_flavor(after)
    result["fact_preservation_report"] = fact_report
    result["x_native_style_report"] = native_report
    result["comment_impulse_report"] = comment_report
    result["ai_flavor_report"] = ai_report.to_dict()
    result["human_voice"] = {
        "version": VOICE_VERSION,
        "ai_flavor_score": ai_report.score,
        "ai_flavor_severity": ai_report.severity,
        "ai_flavor_blocked": ai_report.blocked,
        "x_native_style": native_report["status"],
        "fact_preservation": fact_report["status"],
        "comment_impulse": comment_report["status"],
        "rewrite_applied": result["rewrite_applied"],
    }
    result["passed"] = all((
        ai_flavor_passes(ai_report),
        fact_report["passed"],
        native_report["passed"],
        comment_report["passed"],
    ))
    return result

