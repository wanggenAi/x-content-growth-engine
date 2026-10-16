"""Human Style pipeline for text candidates.

The historical module name is retained for compatibility. New production
admissions use ``HUMAN_STYLE_V2`` and receive an auditable, hash-bound contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .ai_flavor_gate import AIFlavorReport, ai_flavor_passes, analyze_ai_flavor
from .fact_preservation import check_fact_preservation
from .x_native_style import review_comment_impulse, review_x_native_style


VOICE_VERSION = "HUMAN_VOICE_V1"
HUMAN_STYLE_VERSION = "HUMAN_STYLE_V2"
HUMAN_STYLE_ENGINE_VERSION = "human-style-v2-deterministic"
HUMAN_STYLE_GENERATOR = "growth_engine.candidate_pipeline.prepare_candidate"
URL_RE = re.compile(r"https?://[^\s]+")
QUOTE_RE = re.compile(r"[\"“”『』「」‘’].*?[\"“”『』「」‘’]")
GENERIC_ENDINGS = re.compile(r"(?:所以|也许这就是|这才是|值得我们思考|这件事让我意识到|真正的问题是|也该|应该|不应该|必须|没有标准答案)")
GENERIC_QUESTIONS = re.compile(r"(?:凭什么|公平吗|这合理吗|大家觉得呢|你怎么看)[？?]?$|你怎么看[？?]")


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


def stable_hash(value: Any) -> str:
    if isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _protect(text: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f"__HS_PROTECTED_{len(protected)}__"
        protected[token] = match.group(0)
        return token

    return URL_RE.sub(replace, QUOTE_RE.sub(replace, text)), protected


def _restore(text: str, protected: Mapping[str, str]) -> str:
    for token, value in protected.items():
        text = text.replace(token, value)
    return text


def _without_source_link(text: str) -> str:
    return URL_RE.sub("", text).rstrip()


def _trim_generic_tail(text: str, changes: list[dict[str, Any]]) -> str:
    body = _without_source_link(text).rstrip()
    link = URL_RE.search(text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
    if not paragraphs:
        return text
    tail = paragraphs[-1]
    original_tail = tail
    # Remove only the residue from the final paragraph. A short, one-paragraph
    # post must keep its concrete setup when the last phrase is a question or
    # verdict; deleting the whole paragraph turns a rewrite into an empty post.
    marker = re.search(r"(?:也许这就是|这才是|值得我们思考|这件事让我意识到|真正的问题是|没有标准答案|换句话说|从某种意义上说|某种程度上|所以)", tail)
    if marker:
        tail = tail[:marker.start()].rstrip(" ，,：:")
    else:
        question = re.search(r"(?:凭什么[^。！？!?]*|公平吗|这合理吗|大家觉得呢|你怎么看)[？?]?$", tail)
        if question:
            prefix = tail[:question.start()].rstrip(" ，,：:")
            comma = max(prefix.rfind("，"), prefix.rfind(","))
            sentence_start = max(prefix.rfind("。"), prefix.rfind("！"), prefix.rfind("？"), prefix.rfind("!"), prefix.rfind("?"))
            if comma > sentence_start and question.group(0).startswith(("凭什么", "公平吗", "这合理吗")):
                tail = prefix[:comma].rstrip(" ，,：:")
            else:
                tail = prefix
    # Imperative/author-verdict endings are often attached to a concrete
    # sentence, so trim from the marker instead of dropping the paragraph.
    verdict = re.search(r"(?:也该|应该|不应该|必须)[^。！？!?]*[。！？!?]?$", tail)
    if verdict:
        prefix = tail[:verdict.start()].rstrip(" ，,：:")
        if prefix:
            tail = prefix
        else:
            tail = ""
    if tail != original_tail:
        removed = original_tail[len(tail):].strip(" ，,：:。！？!?")
        changes.append({"type": "REMOVE_EDITORIAL_RESIDUE", "span": removed or original_tail,
                        "reason": "author_verdict_or_mechanical_question"})
        paragraphs[-1] = tail
    if not paragraphs[-1]:
        paragraphs.pop()
    result = "\n\n".join(paragraphs).strip()
    result = re.sub(r"([。！？!?])[，,：:]+", r"\1", result)
    result = re.sub(r"[，,]{2,}", "，", result)
    if link:
        result = f"{result}\n\n{link.group(0)}" if result else link.group(0)
    return result


def _conservative_rewrite(text: str) -> tuple[str, list[dict[str, Any]]]:
    protected_text, protected = _protect(text)
    changes: list[dict[str, Any]] = []
    replacements = (
        (r"救急我能理解\s*[，,。]?\s*但(?:是)?", "救急我能理解。"),
        (r"我能理解\s*[，,。]?\s*但(?:是)?", "我能理解。"),
        (r"(?:更值得关注的是|值得注意的是|这背后反映的是|换句话说|从某种意义上说|某种程度上|真正的问题是)[^。！？!?]*[。！？!?]", ""),
        (r"据[^，。]{1,30}(?:报道|消息)\s*[，,：:]\s*", ""),
    )
    for pattern, replacement in replacements:
        new_text, count = re.subn(pattern, replacement, protected_text)
        if count:
            changes.append({"type": "REMOVE_EDITORIAL_RESIDUE", "pattern": pattern, "count": count})
            protected_text = new_text
    protected_text = re.sub(r"[ \t]+", " ", protected_text)
    protected_text = re.sub(r"\n{3,}", "\n\n", protected_text).strip()
    rewritten = _restore(protected_text, protected)
    rewritten = _trim_generic_tail(rewritten, changes)
    if any(item.get("reason") == "author_verdict_or_mechanical_question" for item in changes):
        # Keep the historical replay marker while the auditable operation remains structured.
        changes.append("removed_author_verdict_or_mechanical_question")
    if rewritten != text and not any(isinstance(item, dict) and item.get("type") == "NATURAL_SEGMENTATION" for item in changes):
        changes.append({"type": "NATURAL_SEGMENTATION", "reason": "mixed paragraphs and short stops"})
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
        "scene_first": bool(sentences and len(sentences[0]) <= 40),
        "short_sentence_ratio": round(sum(length <= 12 for length in lengths) / max(len(lengths), 1), 3),
        "mixed_rhythm": report.sentence_stats.get("stdev", 0) >= 3 or len(lengths) <= 2,
        "open_ending": not bool(GENERIC_ENDINGS.search(body) or (sentences and GENERIC_QUESTIONS.search(sentences[-1]))),
    }


def humanize_text(request: Mapping[str, Any]) -> dict[str, Any]:
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
        "operations": changes,
        "voice_features": _voice_features(rewritten, after_report, _raw_reaction(draft)),
        "warnings": warnings,
        "version": HUMAN_STYLE_VERSION,
        "voice_profile": profile,
        "rewrite_applied": rewritten != draft,
        "ai_flavor_before": before_report.to_dict(),
        "ai_flavor_after": after_report.to_dict(),
        "ai_flavor_pass": ai_flavor_passes(after_report),
        "target_platform": request.get("target_platform", "X_ZH"),
        "primary_action": request.get("primary_action"),
        "preserve_quotes": request.get("preserve_quotes", True),
    }


def run_human_style_pipeline(request: Mapping[str, Any]) -> dict[str, Any]:
    """Run rewrite and every deterministic gate, returning an attestable V2 contract."""
    result = humanize_text(request)
    before = str(request.get("draft_text", ""))
    after = result["rewritten_text"]
    locked_facts = request.get("locked_facts", {})
    fact_report = check_fact_preservation(before, after, locked_facts)
    native_report = review_x_native_style(after, str(request.get("primary_action", "")))
    comment_report = review_comment_impulse(after, str(request.get("primary_action", "REPLY")))
    before_report = analyze_ai_flavor(before)
    ai_report = analyze_ai_flavor(after)
    contract = {
        "version": HUMAN_STYLE_VERSION,
        "input_text_hash": stable_hash(before),
        "output_text_hash": stable_hash(after),
        "locked_facts_hash": stable_hash(locked_facts),
        "ai_flavor_score_before": before_report.score,
        "ai_flavor_score_after": ai_report.score,
        "fact_preservation": fact_report["status"],
        "x_native_style": native_report["status"],
        "comment_impulse": comment_report["status"],
        "rewrite_applied": result["rewrite_applied"],
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "engine_version": HUMAN_STYLE_ENGINE_VERSION,
    }
    result.update({
        "fact_preservation_report": fact_report,
        "x_native_style_report": native_report,
        "comment_impulse_report": comment_report,
        "ai_flavor_report": ai_report.to_dict(),
        "ai_flavor_report_before": before_report.to_dict(),
        "human_style": contract,
        "human_voice": contract,  # compatibility for replay consumers
        "passed": all((ai_flavor_passes(ai_report), fact_report["passed"], native_report["passed"], comment_report["passed"])),
    })
    return result


# Historical callers and V1 replay data keep the old symbol.
run_human_voice_pipeline = run_human_style_pipeline
