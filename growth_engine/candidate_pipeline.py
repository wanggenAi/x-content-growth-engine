"""Production candidate assembly: draft -> Human Style -> editorial gate."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .editorial_gate import validate_candidate
from .human_voice import HUMAN_STYLE_GENERATOR, run_human_style_pipeline


def prepare_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Generate the publication contract for a new candidate.

    This is the only supported path for a new candidate to obtain a V2 Human
    Style contract. Synthetic blind fixtures are explicitly refused here.
    """
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be a mapping")
    if candidate.get("fixture_type") == "SYNTHETIC_TEST_FIXTURE":
        raise ValueError("synthetic blind fixtures cannot enter production")
    result = deepcopy(dict(candidate))
    draft = str(result.get("text", result.get("draft_text", "")))
    locked_facts = result.get("locked_facts")
    if not draft.strip():
        raise ValueError("candidate text is required")
    if not isinstance(locked_facts, Mapping) or not locked_facts:
        raise ValueError("locked_facts are required before Human Style")
    pipeline = run_human_style_pipeline({
        "draft_text": draft,
        "locked_facts": locked_facts,
        "target_platform": result.get("target_platform", "X_ZH"),
        "voice_profile": result.get("voice_profile", "GEN_DEFAULT"),
        "primary_action": result.get("primary_action", "REPLY"),
        "source_context": result.get("source_context", []),
        "preserve_quotes": result.get("preserve_quotes", True),
    })
    result["draft_text_before_human_style"] = draft
    result["text"] = pipeline["rewritten_text"]
    result["human_style"] = {
        **pipeline["human_style"],
        "generated_by": HUMAN_STYLE_GENERATOR,
        "operations": pipeline["operations"],
    }
    result.pop("human_voice", None)
    result["human_style_result"] = {
        "passed": pipeline["passed"],
        "ai_flavor_report": pipeline["ai_flavor_report"],
        "fact_preservation_report": pipeline["fact_preservation_report"],
        "x_native_style_report": pipeline["x_native_style_report"],
        "comment_impulse_report": pipeline["comment_impulse_report"],
    }
    result["state"] = result.get("state", "EDITORIAL_REVIEW")
    if pipeline["passed"] and result["state"] in {"DRAFT", "EDITORIAL_REVIEW"}:
        result["state"] = "READY_FOR_MANUAL_PUBLISH"
    gate = validate_candidate(result)
    result["editorial_gate"] = {
        "ready": gate.ready,
        "state": gate.state,
        "reasons": list(gate.reasons),
    }
    if result["state"] == "READY_FOR_MANUAL_PUBLISH" and not gate.ready:
        result["state"] = "EDITORIAL_REVIEW"
    return result
