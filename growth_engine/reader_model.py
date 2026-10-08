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
VALUE_MODEL_VERSION = "READER_VALUE_V2"
VALUE_ROUTES = {
    "SELF_RELEVANCE", "CURIOSITY", "EPISTEMIC_REWARD", "KNOWLEDGE_CORRECTION", "WONDER",
    "UTILITY", "IDENTITY", "STATUS", "COMPARISON", "STATUS_COMPARISON", "EMOTIONAL_RESONANCE", "OPINION_EXPRESSION",
    "SOCIAL_CURRENCY", "HUMOR_ABSURDITY", "NARRATIVE_CLOSURE",
}
CURIOSITY_TYPES = {"KNOWLEDGE_GAP", "MECHANISM_CURIOSITY", "CORRECTION", "NOVELTY", "WONDER",
                   "COUNTERINTUITIVE_FACT", "HIDDEN_PROCESS", "RARE_OBJECT", "RARE_SKILL"}
ACTION_FIELDS = {
    "SHARE": ("social_currency", "share_recipient", "share_reason"),
    "QUOTE": ("social_currency", "share_recipient", "share_reason"),
    "REPLY": ("opinion_activation", "activation_mechanisms", "opinion_space"),
    "SAVE_RETURN": ("utility", "future_usefulness", "concrete_resource"),
    "CLICK_RESOURCE": ("resource_value", "source_accessibility", "actionability"),
    "DWELL": ("curiosity", "information_gap", "narrative_progression", "expectation_violation"),
    "FOLLOW": ("why_follow", "repeatable_value", "account_positioning", "future_expectation"),
    "LIKE": (),
}
WINDOW_TOLERANCE_MINUTES = {"1h": 20, "6h": 30, "24h": 60, "72h": 180, "7d": 360}
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
           "profile_visits", "follows_attributed", "account_follower_delta", "link_clicks",
           "expanded_details", "return_visits")


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


def _legacy_profile_errors(profile: Any, *, for_candidate: bool = False) -> list[str]:
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


def empty_value_profile() -> dict:
    """Small common core. Action and route fields are added only when relevant."""
    return {"model_version": VALUE_MODEL_VERSION, "claim_status": "HYPOTHESIS",
            "material_strength": "UNKNOWN", "evidence_strength": "UNKNOWN", "novelty_status": "UNKNOWN",
            "reader_value_routes": [], "dominant_reader_value_route": None,
            "why_reader_cares": None, "predicted_inner_response": None,
            "self_relevance": "UNKNOWN", "acceptable_editorial_mechanism": "NEEDS_REVIEW",
            "controversy_risk": "UNKNOWN"}


def migrate_profile(profile: dict) -> dict:
    """Copy a legacy profile; never infer a route from fame, topic or a high rating."""
    import copy
    if profile.get("model_version") == VALUE_MODEL_VERSION:
        return copy.deepcopy(profile)
    errors = _legacy_profile_errors(profile)
    if errors:
        raise ValueError("; ".join(errors))
    result = {**copy.deepcopy(profile), "model_version": VALUE_MODEL_VERSION,
              "reader_value_routes": [], "dominant_reader_value_route": None,
              "migration_note": "Legacy signals preserved. Routes require explicit editorial review; no inferred strengths."}
    return result


def _statement(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() not in {"UNKNOWN", "NOT_PRIMARY", "N/A"}


def route_strength(profile: dict, route: str) -> str:
    return next((r["strength"] for r in profile.get("reader_value_routes", []) if r.get("route") == route), "UNKNOWN")


def profile_errors(profile: Any, *, for_candidate: bool = False, primary_action: str | None = None) -> list[str]:
    if not isinstance(profile, dict):
        return ["reader_model must be an object"]
    if profile.get("model_version") == MODEL_VERSION:
        errors = _legacy_profile_errors(profile)
        if for_candidate:
            errors.append("legacy model is readable; new production needs explicit READER_VALUE_V2 route review")
        return errors
    errors = []
    if profile.get("model_version") != VALUE_MODEL_VERSION or profile.get("claim_status") != "HYPOTHESIS":
        errors.append("reader value model must remain READER_VALUE_V2 / HYPOTHESIS")
    for key in ("material_strength", "self_relevance", "controversy_risk"):
        if profile.get(key, "UNKNOWN") not in LEVELS:
            errors.append(f"invalid {key}")
    if profile.get("evidence_strength") not in {"FULL_RECORDED_TEXT", "STRUCTURE_SUMMARY_ONLY", "UNKNOWN"}:
        errors.append("invalid evidence coverage")
    if profile.get("novelty_status") not in {"CHECKED", "REPETITIVE", "UNKNOWN"}:
        errors.append("invalid novelty status")
    if profile.get("acceptable_editorial_mechanism") not in {"ACCEPTABLE_WITH_SOURCE_CHECK", "NEEDS_REVIEW", "RESEARCH_ONLY"}:
        errors.append("invalid editorial mechanism")
    routes = profile.get("reader_value_routes")
    route_names = []
    if not isinstance(routes, list):
        errors.append("reader_value_routes must be a list")
        routes = []
    for route in routes:
        if not isinstance(route, dict) or not _statement(route.get("route")):
            errors.append("route must name a reader-value entrance")
            continue
        route_names.append(route["route"])
        if route.get("strength") not in LEVELS:
            errors.append("route strength must preserve an ordinal label, including UNKNOWN")
        for key in ("cue", "reader_thought"):
            if not _statement(route.get(key)):
                errors.append(f"route {route['route']} needs concrete {key}")
        if route["route"] not in VALUE_ROUTES and not _statement(route.get("definition")):
            errors.append("new route needs a definition; vocabulary is open")
    if len(set(route_names)) != len(route_names):
        errors.append("duplicate reader value route")
    types = profile.get("curiosity_types", [])
    if not isinstance(types, list) or any(t not in CURIOSITY_TYPES for t in types):
        errors.append("invalid curiosity types")
    mechanisms = profile.get("activation_mechanisms", [])
    if not isinstance(mechanisms, list) or any(m not in ACTIVATIONS for m in mechanisms):
        errors.append("invalid activation mechanisms")
    for key in ("opinion_activation", "opinion_space", "social_currency", "actionability", "expectation_violation"):
        if key in profile and profile[key] not in LEVELS:
            errors.append(f"invalid optional signal {key}")
    if not for_candidate:
        return errors
    for key in ("why_reader_cares", "predicted_inner_response"):
        if not _statement(profile.get(key)):
            errors.append(f"common reader review needs {key}")
    dominant = profile.get("dominant_reader_value_route")
    if dominant not in route_names:
        errors.append("choose one explicitly supported dominant reader value route")
    required = []
    active = {r["route"] for r in routes if isinstance(r, dict) and r.get("strength") in {"HIGH", "MEDIUM"} and "route" in r}
    if active & {"CURIOSITY", "EPISTEMIC_REWARD", "WONDER"}:
        if not types:
            errors.append("curiosity/wonder route needs curiosity_types")
        required.extend(("curiosity", "information_gap"))
    if "KNOWLEDGE_CORRECTION" in active:
        correction = profile.get("correction")
        if not isinstance(correction, dict) or any(not _statement(correction.get(k)) for k in ("common_claim", "supported_correction", "source_ref")):
            errors.append("knowledge correction needs original claim, sourced correction and source_ref")
    if "UTILITY" in active:
        required.extend(("utility", "concrete_resource"))
    if "SELF_RELEVANCE" in active:
        required.append("concrete_stakes")
    if "IDENTITY" in active:
        required.append("identity_trigger")
    if active & {"STATUS", "COMPARISON", "STATUS_COMPARISON"}:
        required.append("comparison_basis")
    if "HUMOR_ABSURDITY" in active:
        required.append("comic_turn")
    if "NARRATIVE_CLOSURE" in active:
        required.extend(("narrative_progression", "closure_payload"))
    if "SOCIAL_CURRENCY" in active:
        required.extend(ACTION_FIELDS["SHARE"])
    if "OPINION_EXPRESSION" in active:
        required.extend(("opinion_activation", "opinion_space"))
        if not mechanisms:
            errors.append("opinion route needs activation_mechanisms")
    if primary_action is not None:
        if primary_action not in ACTION_FIELDS:
            errors.append("invalid primary action")
        else:
            required.extend(ACTION_FIELDS[primary_action])
        if primary_action == "REPLY" and not mechanisms:
            errors.append("REPLY needs activation_mechanisms")
        if primary_action == "DWELL" and "expectation_violation" not in profile:
            errors.append("DWELL needs an explicit expectation_violation signal; LOW/UNKNOWN is allowed")
    for key in dict.fromkeys(required):
        value = profile.get(key)
        valid = bool(value) if key == "activation_mechanisms" else _statement(value)
        if not valid:
            errors.append(f"route/action review needs {key}")
    return errors


def review_profile(profile: Any, primary_action: str | None = None) -> dict:
    errors = profile_errors(profile, for_candidate=True, primary_action=primary_action)
    if errors:
        return {"priority": "HOLD_NEEDS_ANNOTATION", "reasons": errors, "primary_action": primary_action}
    dominant = profile["dominant_reader_value_route"]
    checks = {"A_MATERIAL": profile["material_strength"], "B_READER_VALUE_ROUTE": route_strength(profile, dominant),
              "H_EVIDENCE": profile["evidence_strength"], "I_NOVELTY": profile["novelty_status"]}
    reasons = [key for key, value in checks.items() if value in {"LOW", "UNKNOWN"}]
    if dominant in {"CURIOSITY", "EPISTEMIC_REWARD", "WONDER", "UTILITY"} and route_strength(profile, dominant) != "HIGH":
        reasons.append("dominant curiosity/utility route needs strong material-supported value")
    action_signal = {"SHARE": ("social_currency", "SOCIAL_CURRENCY"), "QUOTE": ("social_currency", "SOCIAL_CURRENCY"),
                     "REPLY": ("opinion_activation", "OPINION_EXPRESSION"),
                     "SAVE_RETURN": (None, "UTILITY"), "CLICK_RESOURCE": ("actionability", "UTILITY")}.get(primary_action)
    if action_signal:
        field, route = action_signal
        value = profile.get(field, "UNKNOWN") if field else route_strength(profile, route)
        checks[f"ACTION_{primary_action}"] = value
        if value not in {"HIGH", "MEDIUM"}:
            reasons.append(f"primary action {primary_action} lacks supported {field or route}")
    if primary_action == "REPLY":
        checks["REPLY_OPINION_SPACE"] = profile.get("opinion_space", "UNKNOWN")
        if checks["REPLY_OPINION_SPACE"] not in {"HIGH", "MEDIUM"}:
            reasons.append("REPLY needs genuine opinion space")
    if primary_action == "DWELL" and not any(route_strength(profile, r) in {"HIGH", "MEDIUM"} for r in
                                             ("CURIOSITY", "EPISTEMIC_REWARD", "WONDER", "KNOWLEDGE_CORRECTION", "NARRATIVE_CLOSURE")):
        reasons.append("DWELL needs a supported curiosity, correction, wonder or narrative entrance")
    if profile["novelty_status"] == "REPETITIVE":
        reasons.append("REPETITIVE")
    if profile["acceptable_editorial_mechanism"] != "ACCEPTABLE_WITH_SOURCE_CHECK":
        reasons.append("ATTENTION_NOT_EDITORIALLY_ACCEPTABLE")
    if profile["evidence_strength"] != "FULL_RECORDED_TEXT":
        reasons.append("NEEDS_FULL_MATERIAL")
    return {"priority": "LOWER_PRIORITY" if reasons else "REVIEW_FIRST", "reasons": reasons,
            "primary_action": primary_action, "dominant_route": dominant, "checks": checks,
            "signals": {k: profile.get(k, "UNKNOWN") for k in ("self_relevance", "opinion_activation", "social_currency", "expectation_violation")},
            "prediction_is_observed_response": False}


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
        for numerator in ("replies", "reposts", "quotes", "likes", "bookmarks", "link_clicks", "follows_attributed"):
            n, d = row.get(numerator), row.get(denominator)
            result[f"{numerator}_per_{denominator}"] = n / d if type(n) is int and n >= 0 and type(d) is int and d > 0 else None
    return result


def window_status(published_at: str, as_of: str, window: str) -> str:
    if window not in WINDOWS:
        raise ValueError("unknown feedback window")
    return "DUE_MISSING" if utc(as_of) >= utc(published_at) + timedelta(hours=WINDOWS[window]) else "PENDING_WINDOW"


def window_measurement(published_at: str | None, observed_at: str | None, window: str | None) -> dict:
    """Retain actual age/offset. A late target stays late, never becomes another window."""
    if window is not None and window not in WINDOWS:
        raise ValueError("unknown feedback window")
    metadata = {"actual_observed_at": observed_at, "actual_post_age_minutes": None,
                "target_window": window, "offset_from_target_minutes": None,
                "tolerance_minutes": WINDOW_TOLERANCE_MINUTES.get(window), "window_class": "MISSING"}
    if not published_at or not observed_at:
        return metadata
    age = (utc(observed_at) - utc(published_at)).total_seconds() / 60
    if age < 0:
        raise ValueError("observation precedes publication")
    metadata["actual_post_age_minutes"] = age
    if window is None:
        metadata["window_class"] = "UNWINDOWED_EXPLORATORY"
        return metadata
    offset = age - WINDOWS[window] * 60
    metadata["offset_from_target_minutes"] = offset
    tolerance = WINDOW_TOLERANCE_MINUTES[window]
    metadata["window_class"] = ("ON_WINDOW" if abs(offset) <= 5 else "NEAR_WINDOW" if abs(offset) <= tolerance
                                else "LATE_EXPLORATORY" if offset > tolerance else "MISSING")
    return metadata


ACTIVATION_COMMENT_TYPES = {
    "PERSONAL_EXPERIENCE": {"PERSONAL_EXPERIENCE"}, "EXPERIENCE_DISPLAY": {"PERSONAL_EXPERIENCE"},
    "IDENTITY_TOUCHED": {"IDENTITY_SIGNAL"}, "IDENTITY_DISPLAY": {"IDENTITY_SIGNAL"},
    "DISAGREEMENT": {"DISAGREEMENT"}, "CORRECTION": {"CORRECTION"},
    "EXPLANATION_RIGHT": {"EXPLANATION"}, "ATTRIBUTION": {"EXPLANATION"},
    "MORAL_JUDGMENT": {"MORAL_JUDGMENT"},
}


def activation_prediction_match(row: dict, prediction: dict | None) -> dict:
    result = {"status": "NOT_PREREGISTERED", "matched_mechanisms": [],
              "basis": "Consistency of evidence-backed comment categories with preregistration; not psychological causation."}
    if not prediction or not prediction.get("preregistered_at_utc") or not prediction.get("published_at_utc"):
        return result
    if (prediction.get("publication_url") != row.get("parent_post_url") or
            not utc(prediction["preregistered_at_utc"]) <= utc(prediction["published_at_utc"]) <= utc(row["observed_at_utc"])):
        return {**result, "status": "NOT_EVALUABLE", "reason": "parent or preregistration timing mismatch"}
    predicted = prediction.get("activation_mechanisms", [])
    if not predicted:
        return {**result, "status": "NOT_EVALUABLE", "reason": "no preregistered activation prediction"}
    if any(m not in ACTIVATIONS for m in predicted):
        raise ValueError("invalid preregistered activation mechanism")
    matched = [m for m in predicted if set(row["categories"]) & ACTIVATION_COMMENT_TYPES.get(m, set())]
    evaluable = all(m in ACTIVATION_COMMENT_TYPES for m in predicted)
    return {**result, "status": "MATCH" if matched else "NO_MATCH" if evaluable else "NOT_EVALUABLE",
            "matched_mechanisms": matched, "predicted_mechanisms": predicted,
            "observed_categories": row["categories"], "prediction_ref": prediction.get("experiment_id")}


def validate_comment(row: dict, *, prediction: dict | None = None) -> dict:
    from urllib.parse import urlparse
    from .__main__ import POST_RE
    for key in ("comment_url", "parent_post_url", "evidence_ref", "coding_note", "body"):
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
    return {**row, "learning_eligible": row.get("human_reviewed") is True,
            "activation_prediction_match": activation_prediction_match(row, prediction)}


def action_outcomes(row: dict, primary_action: str | None) -> dict:
    rates = ratios(row)
    metrics = {
        "DWELL": ("views", "impressions", "read_proxy", "expanded_details"),
        "REPLY": ("replies", "replies_per_views", "reply_types"),
        "SHARE": ("reposts", "quotes", "reposts_per_views", "quotes_per_views"),
        "QUOTE": ("quotes", "quotes_per_views"), "LIKE": ("likes", "likes_per_views"),
        "SAVE_RETURN": ("bookmarks", "return_visits"), "CLICK_RESOURCE": ("link_clicks",),
        "FOLLOW": ("follows_attributed",),
    }.get(primary_action, ())
    return {"primary_action": primary_action, "metrics": {k: rates.get(k, row.get(k)) for k in metrics},
            "measurement_limit": "Views/impressions measure exposure, not reading duration." if primary_action == "DWELL" else None}


def qualitative_outcome(row: dict, primary_action: str | None) -> str:
    note = row.get("qualitative_outcome_note")
    if _statement(note):
        return note
    replies = row.get("replies")
    if type(replies) is int and replies > 0:
        return f"可见{replies}条回复；若没有真实评论正文及分类，不能判定经验/身份/解释动机。曝光与分发仍需独立评估。"
    metrics = action_outcomes(row, primary_action)["metrics"]
    if metrics and all(value is None for value in metrics.values()):
        return "主动作指标不可见或缺失，结果未知；不能以回复少或views排名替代该动作的结果。"
    return "记录可见动作与缺失值；低浏览不等于内容失败，缺少主动作/分发证据时保持未知。"


def backtest(annotations: list[dict], observations: list[dict], *, window: str | None = None) -> dict:
    """Retain observations, report per-action outcomes and explicit timing uncertainty."""
    if window is not None and window not in WINDOWS:
        raise ValueError("unknown feedback window")
    by_id = {}
    for annotation in sorted(annotations, key=lambda r: r.get("version", 0)):
        if annotation["entity_kind"] == "own":
            by_id[annotation["entity_id"]] = annotation
    rows, excluded, seen = [], [], set()
    for observation in observations:
        target = observation.get("target_window", observation.get("window"))
        observed = observation.get("actual_observed_at", observation.get("observed_at_utc"))
        if observation.get("actual_observed_at") and observation.get("observed_at_utc") and utc(observation["actual_observed_at"]) != utc(observation["observed_at_utc"]):
            raise ValueError("conflicting actual observation timestamps")
        identity = (observation.get("entity_id"), observed, target, observation.get("evidence_ref"))
        if identity in seen:
            continue
        seen.add(identity)
        annotation = by_id.get(observation.get("entity_id"))
        if not annotation or observation.get("post_url") != annotation.get("post_url"):
            excluded.append({"observation": observation, "reason": "URL_OR_ANNOTATION_MISMATCH"})
            continue
        for key in METRICS:
            value = observation.get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{key} must be a nonnegative integer or null")
        distribution = observation.get("distribution_confidence", "UNKNOWN")
        if distribution not in LEVELS:
            raise ValueError("invalid distribution confidence")
        timing = window_measurement(annotation.get("published_at_utc"), observed, target)
        reason = None
        if observation.get("human_reviewed") is not True or not observation.get("evidence_ref"):
            reason = "NEEDS_HUMAN_REVIEW_AND_EVIDENCE"
        elif observation.get("source_kind") not in {
                "AGENT_NATIVE_CHROME_VISIBLE_UI", "DIRECT_X_RENDERED_UI_AGENT", "DIRECT_NATIVE_CHROME_DETAIL",
                "NATIVE_CHROME_VISIBLE_DETAIL", "NATIVE_CHROME_PUBLIC_DETAIL_RELOAD", "USER_SCREENSHOT", "USER_NOTE"}:
            reason = "NON_DIRECT_METRIC_SOURCE"
        elif (observation.get("publication_text_digest") != annotation.get("publication_text_digest") or
              annotation.get("publication_text_digest") is None or
              observation.get("published_at_utc") != annotation.get("published_at_utc") or
              annotation.get("published_at_utc") is None):
            reason = "PUBLICATION_VERSION_OR_TIME_MISMATCH"
        elif timing["window_class"] not in {"ON_WINDOW", "NEAR_WINDOW"}:
            reason = timing["window_class"]
        if window is not None and target != window:
            reason = "OTHER_OR_UNREGISTERED_TARGET_WINDOW"
        primary_action = annotation.get("primary_action", observation.get("primary_action"))
        comments = [validate_comment(c, prediction=annotation.get("preregistered_prediction"))
                    for c in observation.get("comments", [])]
        if any(c["parent_post_url"] != annotation["post_url"] for c in comments):
            raise ValueError("comment parent does not match observed post")
        row = {**observation, **timing, "rates": ratios(observation), "comments": comments,
               "learning_eligible": reason is None, "exclusion_reason": reason,
               "reader_model": annotation["reader_model"], "distribution_confidence": distribution,
               "content_failure": "UNKNOWN", "outcome": action_outcomes(observation, primary_action),
               "qualitative_outcome_note": qualitative_outcome(observation, primary_action)}
        if comments:
            row["outcome"]["actual_comment_types"] = sorted({category for c in comments for category in c["categories"]})
            row["outcome"]["activation_prediction_matches"] = [c["activation_prediction_match"] for c in comments]
        rows.append(row)
    groups = {}
    for row in rows:
        if row["learning_eligible"]:
            groups.setdefault((row["entity_id"], row["target_window"]), []).append(row)
    for group in groups.values():
        if len(group) > 1:
            for row in group:
                row.update(learning_eligible=False, exclusion_reason="MULTIPLE_CAPTURES_RECONCILE_FIRST")
    eligible = [r for r in rows if r["learning_eligible"]]
    # Keep capture order. Exposure ranking is an optional diagnostic, never the outcome verdict.
    ranking = sorted((r for r in rows if r.get("views") is not None), key=lambda r: (-r["views"], r["entity_id"]))
    analysis = eligible if window else rows
    known = [r["views"] for r in analysis if r.get("views") is not None]
    return {"scope": "FIXED_WINDOW_DESCRIPTIVE" if window else "EXPLORATORY_UNMATCHED",
            "window": window, "rows": rows, "excluded": excluded, "n": len(analysis), "retained_observations": len(rows),
            "exposure_ranking_only": [r["entity_id"] for r in ranking],
            "median_views": median(known) if known else None,
            "learning_eligible_observations": len(eligible),
            "observations_with_positive_visible_interaction": sum(any((r.get(k) or 0) > 0 for k in ("replies", "reposts", "likes", "quotes")) for r in analysis),
            "verified_on_own_account": False, "formula_promotions": 0,
            "limits": ["Views/impressions are exposure proxies, not observed dwell duration.",
                       "Low exposure does not identify content failure or an X distribution mechanism.",
                       "Late/early/missing captures remain retained with actual age and target offset.",
                       "Route annotations and coded prediction matches do not establish causal effects."]}
