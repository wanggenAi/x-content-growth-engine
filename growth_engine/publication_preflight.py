"""Final local assertions before visible X publication."""

from __future__ import annotations

from typing import Any, Mapping

from .editorial_gate import validate_candidate
from .human_voice import HUMAN_STYLE_VERSION, stable_hash


def pre_publish_assert(candidate: Mapping[str, Any], publish_text: str) -> dict[str, Any]:
    """Fail closed if the text about to be pasted differs from the admitted candidate."""
    if candidate.get("fixture_type") == "SYNTHETIC_TEST_FIXTURE":
        raise ValueError("synthetic fixture cannot be published")
    if not isinstance(publish_text, str) or not publish_text.strip():
        raise ValueError("publish text is required")
    if candidate.get("state") != "READY_FOR_MANUAL_PUBLISH":
        raise ValueError("candidate is not READY_FOR_MANUAL_PUBLISH")
    contract = candidate.get("human_style")
    if not isinstance(contract, dict) or contract.get("version") != HUMAN_STYLE_VERSION:
        raise ValueError("HUMAN_STYLE_V2 contract is required")
    if publish_text != candidate.get("text"):
        raise ValueError("publish text differs from candidate.text")
    if stable_hash(publish_text) != contract.get("output_text_hash"):
        raise ValueError("publish text hash does not match Human Style output")
    if contract.get("fact_preservation") != "PASS":
        raise ValueError("fact preservation must PASS")
    if contract.get("x_native_style") != "PASS":
        raise ValueError("X native style must PASS")
    if not isinstance(contract.get("ai_flavor_score_after"), (int, float)) or contract["ai_flavor_score_after"] >= 40:
        raise ValueError("AI flavor score is too high")
    result = candidate.get("human_style_result", {})
    ai_report = result.get("ai_flavor_report", {})
    if ai_report.get("blocked") or any(item in ai_report.get("matched_patterns", []) for item in ("forced_humanization", "author_verdict", "fact_to_value_question")):
        raise ValueError("AI flavor report contains a publication blocker")
    native_report = result.get("x_native_style_report", {})
    if native_report.get("hard_blockers"):
        raise ValueError("X native style has hard blockers")
    if candidate.get("primary_action") == "REPLY":
        comment = result.get("comment_impulse_report", {})
        if contract.get("comment_impulse") != "PASS" or len(comment.get("possible_reply_branches", [])) < 2:
            raise ValueError("REPLY requires two real comment branches")
    if "**" in publish_text or "fixture" in publish_text.lower() or "human_style" in publish_text.lower():
        raise ValueError("internal or test content detected")
    gate = validate_candidate(dict(candidate))
    if not gate.ready:
        raise ValueError("editorial gate failed: " + "; ".join(gate.reasons))
    return {"passed": True, "text_hash": stable_hash(publish_text), "candidate_id": candidate.get("candidate_id")}
