"""Versioned reader hypotheses, bottleneck review and descriptive own-post checks.

No model calls, automatic psychological labeling, virality score or publication.
JSON is the reproducible evidence layer; SQLite is a local queryable copy.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

MODEL_VERSION = "SELF_MIRRORING_V1"
LEVELS = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
ACCOUNTS = {
    "SELF_POSITION", "FAIRNESS", "INTEREST", "UNKNOWN", "EXPECTATION_VIOLATION",
    "HIDDEN_RULE", "DIGNITY", "STATUS_SHIFT", "IDENTITY", "SELF_JUDGMENT",
    "DESIRE_FEAR", "REGRET", "CONTROL", "SOCIAL_CURRENCY",
}
ACTIVATIONS = {
    "IDENTITY_TOUCHED", "PERSONAL_EXPERIENCE", "DISAGREEMENT", "FAIRNESS_JUDGMENT",
    "MORAL_JUDGMENT", "EXPLANATION_RIGHT", "PREDICTION", "ATTRIBUTION",
    "KNOWLEDGE_DISPLAY", "EXPERIENCE_DISPLAY", "IDENTITY_DISPLAY", "CORRECTION",
}
COMMENT_TYPES = {
    "PERSONAL_EXPERIENCE", "DISAGREEMENT", "AGREEMENT", "IDENTITY_SIGNAL",
    "CORRECTION", "MORAL_JUDGMENT", "EXPLANATION", "QUESTION",
    "TAG_OR_SHARE_INTENT", "HUMOR", "OTHER",
}
DISTANCES = ("age", "income", "occupation", "city", "identity", "life_stage", "experience", "interest")
DIMENSIONS = (
    "self_relevance", "psychological_stakes", "expectation_violation",
    "concrete_scene_strength", "information_gap", "opinion_activation",
    "social_currency", "material_strength", "opinion_space", "topic_strength",
)
WINDOWS = {"1h": 1, "6h": 6, "24h": 24, "72h": 72, "7d": 168}
METRICS = ("views", "impressions", "likes", "replies", "reposts", "quotes", "bookmarks",
           "profile_visits", "follows_attributed", "account_follower_delta", "link_clicks")


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return result


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def empty_profile() -> dict:
    return {
        "model_version": MODEL_VERSION, "claim_status": "HYPOTHESIS",
        **{key: "UNKNOWN" for key in DIMENSIONS},
        "psychological_accounts": [], "concrete_stakes": None,
        "self_relevance_distance": {**{key: None for key in DISTANCES}, "bridge": None},
        "hidden_rule": {"claim": None, "evidence_status": "UNKNOWN"},
        "status_shift": None, "identity_trigger": None,
        "activation_mechanisms": [], "opinion_space_reason": None,
        "share_recipient": None, "share_reason": None,
        "why_reader_cares": None, "predicted_inner_response": None,
        "evidence_strength": "UNKNOWN", "controversy_risk": "UNKNOWN",
        "attention_mechanism": None, "acceptable_editorial_mechanism": "NEEDS_REVIEW",
        "rationale": {}, "novelty_status": "UNKNOWN",
    }


def profile_errors(profile: Any, *, for_candidate: bool = False) -> list[str]:
    if not isinstance(profile, dict):
        return ["reader_model must be an object"]
    errors = []
    if profile.get("model_version") != MODEL_VERSION or profile.get("claim_status") != "HYPOTHESIS":
        errors.append("reader model must remain SELF_MIRRORING_V1 / HYPOTHESIS")
    for key in DIMENSIONS:
        if profile.get(key) not in LEVELS:
            errors.append(f"invalid/missing reader dimension: {key}")
    accounts = profile.get("psychological_accounts")
    if not isinstance(accounts, list):
        errors.append("psychological_accounts must be a list")
    else:
        for account in accounts:
            if not isinstance(account, dict) or not isinstance(account.get("account"), str) or not account.get("account"):
                errors.append("account must name a psychological stake")
                continue
            # The vocabulary is open, but novel accounts need the same concrete evidence.
            for key in ("stake", "cue", "reader_thought"):
                if not isinstance(account.get(key), str) or not account[key].strip():
                    errors.append(f"account needs {key}")
    distance = profile.get("self_relevance_distance")
    if not isinstance(distance, dict) or any(key not in distance for key in (*DISTANCES, "bridge")):
        errors.append("distance needs eight dimensions and a bridge; unknown values stay null")
    else:
        if any(value not in {None, "NEAR", "FAR", "MIXED", "UNKNOWN"} for key, value in distance.items() if key in DISTANCES):
            errors.append("invalid distance category")
    mechanisms = profile.get("activation_mechanisms")
    if not isinstance(mechanisms, list) or any(not isinstance(x, str) or x not in ACTIVATIONS for x in mechanisms):
        errors.append("invalid activation mechanism")
    if profile.get("evidence_strength") not in {"FULL_RECORDED_TEXT", "STRUCTURE_SUMMARY_ONLY", "UNKNOWN"}:
        errors.append("evidence_strength describes annotation coverage, not factual truth")
    if profile.get("controversy_risk") not in LEVELS:
        errors.append("controversy_risk must be HIGH, MEDIUM, LOW or UNKNOWN")
    if profile.get("novelty_status") not in {"UNKNOWN", "CHECKED", "REPETITIVE"}:
        errors.append("novelty_status must describe a review, never an automatic semantic claim")
    if profile.get("acceptable_editorial_mechanism") not in {"ACCEPTABLE_WITH_SOURCE_CHECK", "RESEARCH_ONLY", "NEEDS_REVIEW"}:
        errors.append("invalid editorial mechanism")
    rule = profile.get("hidden_rule")
    if not isinstance(rule, dict) or rule.get("evidence_status") not in {"UNKNOWN", "AUTHOR_INTERPRETATION", "SPECULATION", "SOURCE_SUPPORTED"}:
        errors.append("hidden rule needs explicit evidence status")
    if for_candidate:
        for key in ("concrete_stakes", "identity_trigger", "why_reader_cares", "predicted_inner_response",
                    "share_recipient", "share_reason", "opinion_space_reason", "attention_mechanism"):
            if not isinstance(profile.get(key), str) or not profile[key].strip():
                errors.append(f"reader review needs a concrete {key}")
        if not accounts:
            errors.append("reader review needs at least one concrete psychological account")
        rationale = profile.get("rationale")
        if not isinstance(rationale, dict) or any(not isinstance(rationale.get(k), str) or not rationale[k].strip() for k in DIMENSIONS):
            errors.append("each dimension needs a rationale before candidate review")
    return errors


def review_profile(profile: Any) -> dict:
    """A-I bottlenecks; never multiply ordinal labels or promote a formula."""
    errors = profile_errors(profile, for_candidate=True)
    if errors:
        return {"priority": "HOLD_NEEDS_ANNOTATION", "reasons": errors}
    checks = {
        "A_MATERIAL": profile["material_strength"], "B_SELF_MIRROR": profile["self_relevance"],
        "C_STAKES": profile["psychological_stakes"], "D_CONTRAST": profile["expectation_violation"],
        "E_SCENE": profile["concrete_scene_strength"], "F_EXPRESSION": profile["opinion_activation"],
        "G_SHARE": profile["social_currency"], "H_EVIDENCE": profile["evidence_strength"],
        "I_NOVELTY": profile["novelty_status"],
    }
    reasons = [key for key, value in checks.items() if value in {"LOW", "UNKNOWN"}]
    if profile["predicted_inner_response"].strip("。！! ") in {"哦", "知道了", "挺有道理"}:
        reasons.append("PASSIVE_INNER_RESPONSE")
    if profile["novelty_status"] == "REPETITIVE":
        reasons.append("REPETITIVE")
    if profile["acceptable_editorial_mechanism"] != "ACCEPTABLE_WITH_SOURCE_CHECK":
        reasons.append("ATTENTION_NOT_EDITORIALLY_ACCEPTABLE")
    # A summary is enough for a hypothesis, never enough for production evidence.
    if profile["evidence_strength"] != "FULL_RECORDED_TEXT":
        reasons.append("NEEDS_FULL_MATERIAL")
    return {"priority": "LOWER_PRIORITY" if reasons else "REVIEW_FIRST", "reasons": reasons,
            "checks": checks, "score": None, "prediction_is_observed_response": False}


def migrate(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS reader_annotations (
        entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL, version INTEGER NOT NULL,
        annotated_at_utc TEXT NOT NULL, source_digest TEXT NOT NULL, payload TEXT NOT NULL,
        PRIMARY KEY(entity_kind,entity_id,version))""")


def validate_annotation(row: dict) -> None:
    if row.get("entity_kind") not in {"external", "own", "material", "candidate"}:
        raise ValueError("invalid reader annotation entity kind")
    if type(row.get("version")) is not int or row["version"] < 1:
        raise ValueError("annotation version must be a positive integer")
    for key in ("entity_id", "annotated_at_utc", "annotator", "source_digest", "annotation_note"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"missing annotation {key}")
    utc(row["annotated_at_utc"])
    if not isinstance(row.get("source_refs"), list) or not row["source_refs"]:
        raise ValueError("annotation needs source references")
    errors = profile_errors(row.get("reader_model"))
    if errors:
        raise ValueError("; ".join(errors))


def import_annotations(db: sqlite3.Connection, path: Path) -> int:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("reader annotations must be an array")
    for row in rows:
        validate_annotation(row)
    migrate(db)
    added = 0
    with db:
        for row in rows:
            payload = json.dumps(row, sort_keys=True, ensure_ascii=False)
            key = (row["entity_kind"], row["entity_id"], row["version"])
            old = db.execute("SELECT payload FROM reader_annotations WHERE entity_kind=? AND entity_id=? AND version=?", key).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError("annotation revision conflict; append a new version")
                continue
            db.execute("INSERT INTO reader_annotations VALUES (?,?,?,?,?,?)",
                       (*key, row["annotated_at_utc"], row["source_digest"], payload))
            added += 1
    return added


def reader_packet(db: sqlite3.Connection, kind: str | None = None) -> list[dict]:
    migrate(db)
    query = """SELECT r.payload FROM reader_annotations r JOIN
        (SELECT entity_kind,entity_id,max(version) version FROM reader_annotations
         GROUP BY entity_kind,entity_id) latest
        USING(entity_kind,entity_id,version)"""
    params = ()
    if kind:
        query += " WHERE r.entity_kind=?"
        params = (kind,)
    query += " ORDER BY r.entity_kind,r.entity_id"
    return [json.loads(row[0]) for row in db.execute(query, params)]


def ratios(row: dict) -> dict:
    # Keep views and impressions distinct: public replies/views are not analytics impressions.
    result = {}
    for denominator in ("views", "impressions"):
        for numerator in ("replies", "reposts", "likes"):
            n, d = row.get(numerator), row.get(denominator)
            result[f"{numerator}_per_{denominator}"] = n / d if type(n) is int and n >= 0 and type(d) is int and d > 0 else None
    return result


def window_status(published_at: str, as_of: str, window: str) -> str:
    if window not in WINDOWS:
        raise ValueError("unknown feedback window")
    return "DUE_MISSING" if utc(as_of) >= utc(published_at) + timedelta(hours=WINDOWS[window]) else "PENDING_WINDOW"


def validate_comment(row: dict) -> dict:
    from urllib.parse import urlparse
    from .__main__ import POST_RE
    for key in ("comment_url", "parent_post_url", "evidence_ref", "coding_note"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"comment needs {key}")
    for key in ("comment_url", "parent_post_url"):
        url = urlparse(row[key])
        if url.scheme != "https" or url.hostname not in {"x.com", "twitter.com"} or not POST_RE.fullmatch(url.path):
            raise ValueError("comment must reference real canonical X URLs")
    utc(row["observed_at_utc"])
    categories = row.get("categories")
    if not isinstance(categories, list) or not categories or any(c not in COMMENT_TYPES for c in categories):
        raise ValueError("comment needs allowed categories")
    if row.get("agent_checked") is not True and row.get("human_reviewed") is not True:
        raise ValueError("comment needs a recorded inspection")
    return {**row, "learning_eligible": row.get("human_reviewed") is True}


def backtest(annotations: list[dict], observations: list[dict], *, window: str | None = None) -> dict:
    """Exploratory rank plus strict-window eligibility; outputs account metrics privately."""
    if window is not None and window not in WINDOWS:
        raise ValueError("unknown feedback window")
    by_id = {row["entity_id"]: row for row in annotations if row["entity_kind"] == "own"}
    rows, excluded = [], []
    seen = set()
    fixed_seen = set()
    for observation in observations:
        identity = (observation.get("entity_id"), observation.get("observed_at_utc"), observation.get("evidence_ref"))
        if identity in seen:
            continue
        seen.add(identity)
        annotation = by_id.get(observation.get("entity_id"))
        if not annotation or observation.get("post_url") != annotation.get("post_url"):
            excluded.append({"entity_id": observation.get("entity_id"), "reason": "URL_OR_ANNOTATION_MISMATCH"})
            continue
        for key in METRICS:
            value = observation.get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{key} must be a nonnegative integer or null")
        eligible = False
        reason = "NOT_HUMAN_REVIEWED_OR_NO_FIXED_WINDOW"
        if (observation.get("human_reviewed") is True and observation.get("window") in WINDOWS
                and observation.get("evidence_ref") and observation.get("source_kind") in {
                    "AGENT_NATIVE_CHROME_VISIBLE_UI", "DIRECT_X_RENDERED_UI_AGENT", "DIRECT_NATIVE_CHROME_DETAIL",
                    "NATIVE_CHROME_VISIBLE_DETAIL", "NATIVE_CHROME_PUBLIC_DETAIL_RELOAD", "USER_SCREENSHOT", "USER_NOTE"}
                and observation.get("publication_text_digest") == annotation.get("publication_text_digest")
                and annotation.get("publication_text_digest") is not None
                and observation.get("published_at_utc") == annotation.get("published_at_utc")
                and annotation.get("published_at_utc") is not None):
            if observation.get("observed_at_utc") and observation.get("published_at_utc"):
                hours = WINDOWS[observation["window"]]
                due = utc(observation["published_at_utc"]) + timedelta(hours=hours)
                captured = utc(observation["observed_at_utc"])
                # Late captures are cumulative; they cannot backfill an earlier window.
                eligible = due <= captured <= due + timedelta(minutes=15)
                reason = None if eligible else "OUTSIDE_WINDOW_15_MIN_TOLERANCE"
        if window is not None and (not eligible or observation.get("window") != window):
            excluded.append({"entity_id": observation["entity_id"], "reason": reason or "OTHER_WINDOW"})
            continue
        if window is not None:
            if observation["entity_id"] in fixed_seen:
                raise ValueError("multiple observations for one post/window; reconcile evidence first")
            fixed_seen.add(observation["entity_id"])
        rows.append({**observation, "rates": ratios(observation), "learning_eligible": eligible,
                     "exclusion_reason": reason, "reader_model": annotation["reader_model"]})
    known = [r for r in rows if r.get("views") is not None]
    known.sort(key=lambda r: (-r["views"], r["entity_id"]))
    positive = sum(1 for r in rows if any((r.get(k) or 0) > 0 for k in ("replies", "reposts", "likes")))
    return {"scope": "FIXED_WINDOW_DESCRIPTIVE" if window else "EXPLORATORY_UNMATCHED",
            "window": window, "rows": known + [r for r in rows if r.get("views") is None],
            "excluded": excluded, "n": len(rows), "median_views": median(r["views"] for r in known) if known else None,
            "learning_eligible_observations": sum(r["learning_eligible"] for r in rows),
            "observations_with_positive_visible_interaction": positive,
            "verified_on_own_account": False, "formula_promotions": 0,
            "limits": ["Convenience sample; cumulative views and post ages differ.",
                       "Predicted thoughts and accounts are annotations, not measured psychology.",
                       "Zero visible interactions does not establish a causal failure mechanism.",
                       "No independent holdout, controlled comparison or attributed follows."]}
