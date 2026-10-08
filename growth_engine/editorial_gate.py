"""Machine-readable editorial gate; this validates readiness, never predicts reach."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .reader_model import profile_errors, review_profile

PRIMARY_ACTIONS = {
    "SHARE", "REPLY", "QUOTE", "FOLLOW", "DWELL", "SAVE_RETURN", "CLICK_RESOURCE"
}
EDITORIAL_STATES = {
    "DISCOVERED", "SOURCE_CHECKED", "MATERIAL_STRONG", "DRAFT", "EDITORIAL_REVIEW",
    "READY_FOR_MANUAL_PUBLISH", "PUBLISHED_PENDING_FEEDBACK", "OBSERVATION_CLOSED",
    "LEARNING_REVIEWED", "FAIL_LOW_INTEREST", "FAIL_REPETITIVE", "FAIL_NO_PAYLOAD",
    "FAIL_NO_PRIMARY_ACTION", "HOLD_NEEDS_EVIDENCE", "RESEARCH_ONLY",
}
REQUIRED_FIELDS = (
    "candidate_id", "research_version", "publication_version", "subject_value",
    "information_gap", "payload", "primary_action", "primary_action_reader",
    "novelty_check", "audit_language_separation", "follow_reason", "material_strength",
    "source_refs", "fact_check_status", "human_checked",
    "reader_model",
)

@dataclass(frozen=True)
class GateResult:
    ready: bool
    reasons: tuple[str, ...]
    state: str


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_candidate(candidate: dict[str, Any]) -> GateResult:
    """Validate a candidate record without changing its state or inventing evidence."""
    reasons: list[str] = []
    state = candidate.get("state", "EDITORIAL_REVIEW")
    missing = [key for key in REQUIRED_FIELDS if key not in candidate]
    if missing:
        reasons.append("missing fields: " + ", ".join(missing))
    for key in REQUIRED_FIELDS:
        if key in {"source_refs", "human_checked", "reader_model"}:
            continue
        if key in candidate and not _text(candidate[key]):
            reasons.append(f"{key} must be a concrete non-empty statement")
    if not isinstance(candidate.get("source_refs"), list) or not candidate.get("source_refs"):
        reasons.append("source_refs must be a non-empty list")
    action = candidate.get("primary_action")
    if not isinstance(action, str) or action not in PRIMARY_ACTIONS:
        reasons.append("primary_action must be exactly one allowed action")
    if candidate.get("material_strength") != "STRONG":
        reasons.append("material_strength must be STRONG")
    if candidate.get("human_checked") is not True:
        reasons.append("human_checked must be true before manual publication review")
    if candidate.get("fact_check_status") in {"UNVERIFIED", "UNKNOWN", None}:
        reasons.append("fact_check_status must describe checked boundaries")
    if state not in EDITORIAL_STATES:
        reasons.append(f"invalid editorial state: {state}")
    if state in {"FAIL_LOW_INTEREST", "FAIL_REPETITIVE", "FAIL_NO_PAYLOAD", "FAIL_NO_PRIMARY_ACTION", "HOLD_NEEDS_EVIDENCE", "RESEARCH_ONLY"}:
        reasons.append(f"editorial hold/failure state cannot pass: {state}")
    profile = candidate.get("reader_model")
    reasons.extend(profile_errors(profile, for_candidate=True))
    if isinstance(profile, dict) and not profile_errors(profile, for_candidate=True):
        review = review_profile(profile)
        for key in ("material_strength", "self_relevance", "psychological_stakes"):
            if profile[key] in {"LOW", "UNKNOWN"}:
                reasons.append(f"reader_model.{key} needs substantive material review")
        for blocker in ("REPETITIVE", "ATTENTION_NOT_EDITORIALLY_ACCEPTABLE", "NEEDS_FULL_MATERIAL", "PASSIVE_INNER_RESPONSE"):
            if blocker in review["reasons"]:
                reasons.append(blocker)
        if profile["novelty_status"] != "CHECKED":
            reasons.append("reader_model novelty review must be CHECKED")
        target = {"REPLY": "opinion_activation", "SHARE": "social_currency"}.get(action) if isinstance(action, str) else None
        if target and profile[target] in {"LOW", "UNKNOWN"}:
            reasons.append(f"primary action {action} lacks {target}")
    if state == "READY_FOR_MANUAL_PUBLISH" and reasons:
        reasons.append("READY_FOR_MANUAL_PUBLISH is not allowed while gate reasons remain")
    return GateResult(not reasons, tuple(reasons), state if state in EDITORIAL_STATES else "EDITORIAL_REVIEW")
