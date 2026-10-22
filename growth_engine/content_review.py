"""Text-first editorial decisions, separate from topic/style heuristics.

This validates an editor's source-bound comparison; it does not manufacture
that judgment, predict traffic, or claim that two roles are two people.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re

from .human_voice import stable_hash

READER_CHECKS = ("stop_reason", "immediate_comprehension", "new_information",
                 "share_reason", "natural_voice", "discussion_space", "errors")
FACT_CHECKS = {"original_source", "publication_time", "event_time", "numbers",
               "names", "quotes", "causality", "uncertainty"}


def reader_review_packet(candidate: dict, material: dict) -> dict:
    """A final-pass input without the writer's scores or recommendation.

    This supports process separation, not a claim of independent people or
    genuine audience validation. Reviews must be authored, never synthesized here.
    """
    review = candidate.get("content_review") or {}
    source = material.get("source") or {}
    # evidence_text may contain the topic editor's translated pitch. Original
    # quotations belong in source_evidence, not that recommendation channel.
    source = {k: source[k] for k in ("url", "published_at", "event_time", "event_time_status",
              "timestamp_precision", "captured_at", "visible_date_labels", "rediscovery_reason") if k in source}
    return {"text": candidate.get("text"), "source": source,
            "source_evidence": material.get("source_evidence", []),
            "claims": review.get("claims", []), "fact_review": review.get("fact_review"),
            "publication_memory": candidate.get("publication_memory"),
            "user_content_verdict": candidate.get("user_content_verdict") or material.get("user_content_verdict")}


def review_final_reader(candidate: dict, material: dict) -> dict:
    """Validate fact-first, sentence-by-sentence editorial evidence; no score."""
    from .reader_model import utc
    review = candidate.get("content_review") or {}
    final = review.get("final_reader_review") or {}
    fact = review.get("fact_review") or {}
    final = final if isinstance(final, dict) else {}
    fact = fact if isinstance(fact, dict) else {}
    text = str(candidate.get("text") or "")
    reasons = []
    if (fact.get("decision") != "PASS" or fact.get("unresolved") != []
            or not isinstance(fact.get("checked"), list)
            or not all(isinstance(k, str) for k in fact["checked"])
            or set(fact["checked"]) != FACT_CHECKS
            or fact.get("text_hash") != stable_hash(text)
            or fact.get("source_hash") != stable_hash(material.get("source_evidence", []))
            or not _note(fact.get("event_time_note")) or not fact.get("reviewer")):
        reasons.append("CONTENT_FACT_RECHECK_REQUIRED")
    if (final.get("method") != "TEXT_AND_SOURCE_ONLY"
            or final.get("stage") != "FINAL_CHINESE_READER"
            or final.get("reviewer_scope") not in {"SEPARATE_PASS_SAME_AGENT", "SECOND_REVIEWER"}
            or not final.get("reviewer") or final.get("author_scores_used") is not False
            or final.get("input_hash") != stable_hash(reader_review_packet(candidate, material))):
        reasons.append("CONTENT_FINAL_READER_REVIEW_REQUIRED")
    try:
        if not utc(review["author_completed_at"]) <= utc(fact["reviewed_at"]) <= utc(final["reviewed_at"]):
            reasons.append("CONTENT_REVIEW_STAGE_ORDER_INVALID")
    except (KeyError, TypeError, ValueError):
        reasons.append("CONTENT_REVIEW_STAGE_ORDER_INVALID")
    rows = final.get("sentences", [])
    sentences = body_sentences(text)
    if (not isinstance(rows, list) or len(rows) != len(sentences)
            or [r.get("text") for r in rows if isinstance(r, dict)] != sentences
            or not sentences):
        reasons.append("CONTENT_SENTENCE_REVIEW_INCOMPLETE")
    elif any(r.get("decision") != "PASS" or r.get("issues") != []
             or r.get("background_cost") not in {"NONE", "EXPLAINED"}
             or not _note(r.get("reason")) for r in rows):
        reasons.append("CONTENT_CHINESE_LANGUAGE_OR_BACKGROUND_HOLD")
    for key in READER_CHECKS:
        checks = final.get("checks")
        answer = checks.get(key) if isinstance(checks, dict) else None
        answer = answer if isinstance(answer, dict) else {}
        if (answer.get("decision") != "PASS" or not _note(answer.get("reason"))
                or not answer.get("quote") or answer["quote"] not in text):
            reasons.append("CONTENT_READER_HOLD:" + key)
    variety = final.get("variety") or {}
    variety = variety if isinstance(variety, dict) else {}
    if variety.get("decision") != "PASS" or not _note(variety.get("reason")):
        reasons.append("CONTENT_VARIETY_REVIEW_REQUIRED")
    if final.get("decision") != "PASS" or final.get("unresolved") != []:
        reasons.append("CONTENT_FINAL_EDITOR_HOLD")
    # A recorded user rejection is a regression, never overridden by self-PASS.
    # This narrow example is not advertised as a general Chinese grammar model.
    if re.search(r"(?:有把)?私钥竟然是\s*4(?:\D|$)", text):
        reasons.append("CONTENT_USER_REJECTED_CHINESE_PRIVATE_KEY")
    return {"passed": not reasons, "reasons": sorted(set(reasons)),
            "reviewer_scope": final.get("reviewer_scope", "UNKNOWN"),
            "audience_validation": "UNKNOWN"}


def body_sentences(text: str) -> list[str]:
    body = re.sub(r"https?://\S+", "", text)
    return [s.strip() for s in re.split(r"[。！？!?\n]+", body) if s.strip()]


def _note(value) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 10


def reader_value_reasons(value) -> list[str]:
    """The same four editorial questions at selection and text review."""
    value = value if isinstance(value, dict) else {}
    return ["CONTENT_READER_VALUE_REQUIRED:" + key
            for key in ("stop_reason", "reader_gain", "response_reason", "distinct_angle")
            if not _note(value.get(key))]


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
        reasons.extend(reader_value_reasons(review.get("reader_value")))
        from .x_native_style import platform_length
        length = platform_length(text)
        if not length["fits_standard"]:
            reasons.append("CONTENT_STANDARD_LENGTH_OR_COMPOSER_REVIEW_REQUIRED")
    sentences = body_sentences(text)
    opening = review.get("opening") or {}
    payoff = review.get("payoff") or {}
    if not opening.get("quote") or opening["quote"] not in text[:80] or not _note(opening.get("reason")):
        reasons.append("CONTENT_OPENING_NOT_REVIEWED")
    if candidate.get("opening_comparison_required") or "alternatives" in opening:
        alternatives = opening.get("alternatives")
        valid = isinstance(alternatives, list) and len(alternatives) == 2
        if valid:
            corpus = "\n".join(str(s.get("excerpt") or "") for s in sources)
            valid = all(isinstance(a, dict) and _note(a.get("text"))
                        and _note(a.get("reader_reason")) and _note(a.get("source_span"))
                        and a["source_span"] in corpus and a.get("approach") for a in alternatives)
        if valid:
            left, right = alternatives
            valid = (left["approach"] != right["approach"]
                     and SequenceMatcher(None, left["text"], right["text"]).ratio() < .72
                     and any(text.startswith(a["text"]) for a in alternatives)
                     and _note(opening.get("selection_reason")))
        if not valid:
            reasons.append("CONTENT_OPENING_COMPARISON_REQUIRED")
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
    final = review_final_reader(candidate, material)
    if candidate.get("final_reader_review_required") or review.get("final_reader_review"):
        reasons.extend(final["reasons"])
    return {"passed": not reasons, "reasons": sorted(set(reasons)),
            "quality_ready": not reasons and final["passed"], "final_reader": final,
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
