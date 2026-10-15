"""Machine-readable editorial gate; this validates readiness, never predicts reach."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai_flavor_gate import ai_flavor_passes
from .reader_model import profile_errors, review_profile

PRIMARY_ACTIONS = {
    "SHARE", "REPLY", "QUOTE", "FOLLOW", "DWELL", "SAVE_RETURN", "CLICK_RESOURCE", "LIKE"
}
EDITORIAL_STATES = {
    "DISCOVERED", "SOURCE_CHECKED", "MATERIAL_STRONG", "DRAFT", "EDITORIAL_REVIEW",
    "READY_FOR_MANUAL_PUBLISH", "PUBLISHED_PENDING_FEEDBACK", "OBSERVATION_CLOSED",
    "LEARNING_REVIEWED", "FAIL_LOW_INTEREST", "FAIL_REPETITIVE", "FAIL_NO_PAYLOAD",
    "FAIL_NO_PRIMARY_ACTION", "HOLD_NEEDS_EVIDENCE", "RESEARCH_ONLY",
}
REQUIRED_FIELDS = (
    "candidate_id", "research_version", "publication_version", "subject_value",
    "payload", "primary_action", "novelty_check", "audit_language_separation", "material_strength",
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


def _human_voice_errors(candidate: dict[str, Any]) -> list[str]:
    """Validate the publication contract without rewriting the candidate."""
    contract = candidate.get("human_voice")
    if not isinstance(contract, dict):
        return ["human_voice contract is required before manual publication"]
    errors: list[str] = []
    if contract.get("version") != "HUMAN_VOICE_V1":
        errors.append("human_voice version must be HUMAN_VOICE_V1")
    score = contract.get("ai_flavor_score")
    if not isinstance(score, (int, float)):
        errors.append("human_voice.ai_flavor_score is required")
    elif not ai_flavor_passes({"score": score, "blocked": bool(contract.get("ai_flavor_blocked", False))}):
        errors.append("AI flavor gate is blocked or above threshold")
    if contract.get("x_native_style") != "PASS":
        errors.append("X native style gate must be PASS")
    if contract.get("fact_preservation") != "PASS":
        errors.append("fact preservation gate must be PASS")
    action = candidate.get("primary_action")
    comment_status = contract.get("comment_impulse")
    if action == "REPLY" and comment_status != "PASS":
        errors.append("REPLY requires a passing comment impulse gate")
    if action != "REPLY" and comment_status not in {"PASS", "NOT_APPLICABLE"}:
        errors.append("non-REPLY comment impulse status is invalid")
    return errors


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
    # Historical published records predate HUMAN_VOICE_V1 and remain auditable.
    # Any record seeking a new manual publication slot must carry the contract.
    if state == "READY_FOR_MANUAL_PUBLISH":
        reasons.extend(_human_voice_errors(candidate))
    profile = candidate.get("reader_model")
    # Published historical V1 records remain readable for audit and feedback.
    # New admissions still require the explicit V2 route/action contract.
    historical_legacy = (isinstance(profile, dict) and profile.get("model_version") == "SELF_MIRRORING_V1" and
                         state in {"PUBLISHED_PENDING_FEEDBACK", "OBSERVATION_CLOSED", "LEARNING_REVIEWED"})
    model_errors = profile_errors(profile, for_candidate=not historical_legacy, primary_action=action if isinstance(action, str) else None)
    reasons.extend(model_errors)
    if not model_errors and not historical_legacy:
        review = review_profile(profile, action)
        reasons.extend(review["reasons"])
        if profile["material_strength"] != "HIGH":
            reasons.append("reader_model material strength must be HIGH")
        if profile["novelty_status"] != "CHECKED":
            reasons.append("reader_model novelty review must be CHECKED")
    if state == "READY_FOR_MANUAL_PUBLISH" and reasons:
        reasons.append("READY_FOR_MANUAL_PUBLISH is not allowed while gate reasons remain")
    return GateResult(not reasons, tuple(reasons), state if state in EDITORIAL_STATES else "EDITORIAL_REVIEW")
