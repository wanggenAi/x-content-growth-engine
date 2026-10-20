"""Text-first editorial decisions, separate from topic/style heuristics.

This validates an editor's source-bound comparison; it does not manufacture
that judgment, predict traffic, or claim that two roles are two people.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re

from .human_voice import stable_hash


def body_sentences(text: str) -> list[str]:
    body = re.sub(r"https?://\S+", "", text)
    return [s.strip() for s in re.split(r"[。！？!?\n]+", body) if s.strip()]


def _note(value) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 10


def review_content(candidate: dict, material: dict) -> dict:
    """Fail closed on missing, rejected, stale or ungrounded editorial work.

    Source checks are against retrieved evidence, never draft-derived locks.
    Semantic entailment and reader interest remain explicit editor judgments.
    """
    text = str(candidate.get("text") or "")
    review = candidate.get("content_review") or {}
    sources = material.get("source_evidence") or []
    reasons = []
    if (candidate.get("user_content_verdict") == "REJECT"
            or material.get("user_content_verdict") == "REJECT"):
        reasons.append("CONTENT_USER_REJECTED")
    if review.get("method") != "TEXT_FIRST_COMPARISON":
        reasons.append("CONTENT_REVIEW_REQUIRED")
    if not review.get("reviewer") or not review.get("reviewed_at"):
        reasons.append("CONTENT_REVIEW_AUDIT_REQUIRED")
    if review.get("text_hash") != stable_hash(text):
        reasons.append("CONTENT_REVIEW_TEXT_CHANGED")
    if review.get("source_hash") != stable_hash(sources):
        reasons.append("CONTENT_REVIEW_SOURCE_CHANGED")
    if review.get("decision") != "PASS":
        reasons.append("CONTENT_EDITOR_HOLD")
    if review.get("failure_reasons"):
        reasons.append("CONTENT_UNRESOLVED_FAILURES")
    if candidate.get("strategy_version") == "V4" and review.get("version") != "CONTENT_REVIEW_V4":
        reasons.append("CONTENT_V4_REVIEW_REQUIRED")
    if review.get("version") == "CONTENT_REVIEW_V4":
        # Qualitative answers, not a ninth score or a traffic prediction.
        value = review.get("reader_value") or {}
        for key in ("stop_reason", "reader_gain", "response_reason", "distinct_angle"):
            if not _note(value.get(key)):
                reasons.append("CONTENT_READER_VALUE_REQUIRED:" + key)
        from .x_native_style import platform_length
        length = platform_length(text)
        if not length["fits_standard"]:
            reasons.append("CONTENT_STANDARD_LENGTH_OR_COMPOSER_REVIEW_REQUIRED")
    sentences = body_sentences(text)
    opening = review.get("opening") or {}
    payoff = review.get("payoff") or {}
    if not opening.get("quote") or opening["quote"] not in text[:80] or not _note(opening.get("reason")):
        reasons.append("CONTENT_OPENING_NOT_REVIEWED")
    if not payoff.get("quote") or payoff["quote"] not in text or not _note(payoff.get("reason")):
        reasons.append("CONTENT_PAYOFF_NOT_REVIEWED")
    comparison = review.get("comparison") or {}
    if (not _note(comparison.get("reference_text"))
            or not _note(comparison.get("reference_failure"))
            or not _note(comparison.get("difference"))
            or comparison.get("reference_text") == text):
        reasons.append("CONTENT_NEGATIVE_COMPARISON_REQUIRED")
    # Full publication memory supplied by the caller, with event/source keys.
    memory = candidate.get("publication_memory")
    novelty = review.get("novelty") or {}
    if not isinstance(memory, list) or novelty.get("memory_hash") != stable_hash(memory):
        reasons.append("CONTENT_PUBLICATION_MEMORY_REQUIRED")
    if not _note(novelty.get("reason")) or novelty.get("distinct") is not True:
        reasons.append("CONTENT_NOVELTY_REVIEW_REQUIRED")
    for post in memory or []:
        if not isinstance(post, dict):
            reasons.append("CONTENT_INVALID_PUBLICATION_MEMORY"); continue
        from .viral_admission import canonical_url
        if ((post.get("event_id") and post["event_id"] == material.get("event_id"))
                or (post.get("source_url") and canonical_url(post["source_url"]) == canonical_url((material.get("source") or {}).get("url", "")))
                or (post.get("text") and SequenceMatcher(None, text, post["text"]).ratio() >= .86)):
            reasons.append("CONTENT_ALREADY_PUBLISHED")
    source = material.get("source") or {}
    event_status = source.get("event_time_status")
    if event_status == "EVERGREEN_REDISCOVERY":
        if not _note(source.get("rediscovery_reason")) or not source.get("event_time"):
            reasons.append("CONTENT_REDISCOVERY_REASON_REQUIRED")
        # Date/year must be visible; an old event cannot read as breaking news.
        if str(source.get("event_time", ""))[:7].replace("-", "年") not in text and not any(
                tag in text for tag in source.get("visible_date_labels", [])):
            reasons.append("CONTENT_OLD_EVENT_DATE_HIDDEN")
    elif event_status not in {"EVENT_DATE_CHECKED", "CURRENT_REPORT_EVENT_DATE_UNKNOWN"}:
        reasons.append("CONTENT_EVENT_TIME_REVIEW_REQUIRED")
    if event_status == "CURRENT_REPORT_EVENT_DATE_UNKNOWN" and not any(
            label in text for label in source.get("visible_date_labels", [])):
        reasons.append("CONTENT_REPORT_DATE_BOUNDARY_REQUIRED")
    if not sources:
        reasons.append("CONTENT_SOURCE_EVIDENCE_REQUIRED")
    proofs = review.get("claims") or []
    for sentence in sentences:
        proof = next((p for p in proofs if isinstance(p, dict) and p.get("draft_span") == sentence), {})
        original = next((s for s in sources if s.get("url") == proof.get("url")), {})
        evidence = proof.get("source_span") or ""
        span_range = proof.get("source_range")
        if (isinstance(span_range, list) and len(span_range) == 2
                and all(type(n) is int for n in span_range)
                and 0 <= span_range[0] < span_range[1] <= len(original.get("excerpt", ""))):
            evidence = original["excerpt"][span_range[0]:span_range[1]]
        if (not evidence or evidence not in original.get("excerpt", "")
                or proof.get("verdict") != "SUPPORTED" or not _note(proof.get("reason"))):
            reasons.append("CONTENT_UNSUPPORTED_SENTENCE:" + sentence[:24]); continue
        # Translation and arithmetic still need an explicit checked mapping.
        for number in re.findall(r"\d+(?:[,.]\d+)*", sentence):
            normalized = number.replace(",", "")
            source_numbers = {n.replace(",", "") for n in re.findall(r"\d+(?:[,.]\d+)*", evidence)}
            mappings = proof.get("number_mappings") or []
            translated = any(isinstance(p, dict) and p.get("draft") == number
                             and p.get("source") and p["source"] in evidence and _note(p.get("reason")) for p in mappings)
            if normalized not in source_numbers and not translated:
                reasons.append("CONTENT_UNSOURCED_NUMBER:" + number)
    if re.search(r"对此你怎么看|你们觉得呢|这说明了什么|值得所有人深思", text):
        reasons.append("CONTENT_CANNED_ENDING")
    return {"passed": not reasons, "reasons": sorted(set(reasons)),
            "decision": review.get("decision", "UNKNOWN"),
            "basis": "EDITOR_JUDGMENT_NOT_TRAFFIC_VALIDATION", "text_hash": stable_hash(text)}


def review_variant_set(variants: list[dict]) -> dict:
    """Reject missing modes and cosmetic rewrites, regardless of style scores."""
    reasons = []
    if len(variants) != 3 or {v.get("id") for v in variants} != {"A", "B", "C"}:
        reasons.append("THREE_VARIANTS_REQUIRED")
    versions = {v.get("strategy_version", "LEGACY") for v in variants}
    if len(versions) != 1 or not versions <= {"LEGACY", "V4"}:
        reasons.append("VARIANT_STRATEGY_VERSION_MISMATCH")
    modes = ({"A": "DIRECT", "B": "PERSONAL", "C": "HUMAN_CONTRAST"} if versions == {"V4"}
             else {"A": "STORY", "B": "CONTRAST", "C": "DISCUSSION"})
    for v in variants:
        if v.get("mode") != modes.get(v.get("id")):
            reasons.append("VARIANT_MODE_MISMATCH")
        if not _note(v.get("structure_reason")):
            reasons.append("VARIANT_STRUCTURE_REVIEW_REQUIRED")
    for i, left in enumerate(variants):
        for right in variants[i+1:]:
            a, b = body_sentences(left.get("text", "")), body_sentences(right.get("text", ""))
            if (not a or not b or SequenceMatcher(None, a[0], b[0]).ratio() >= .72
                    or SequenceMatcher(None, "".join(a), "".join(b)).ratio() >= .82):
                reasons.append("COSMETIC_VARIANTS:" + str(left.get("id")) + str(right.get("id")))
    return {"passed": not reasons, "reasons": sorted(set(reasons))}
