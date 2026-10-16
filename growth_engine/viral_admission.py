"""Evidence-backed topic screening and competition, independent of prose quality.

Ratings are ordinal editorial hypotheses, not audience measurements. No source
brand, relationship noun, number count, or writing score can create HIGH value.
Unknown reviews fail closed. All ranking inputs and reasons remain auditable.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .human_voice import stable_hash

VERSION = "VIRAL_ADMISSION_V1"
WEIGHTS = {"raw_material_strength": 18, "surprise": 12, "conflict": 10,
           "self_insertion": 10, "first_screen_stopping_power": 22,
           "mass_relevance": 18, "share_potential": 5, "reply_potential": 5}
GENERIC = {"reviewed", "concrete evidence reviewed", "high", "strong", "有冲突", "有数字", "已核实"}
MIN_POOL = 10
MIN_TOPIC = 60


def canonical_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    parsed = urlsplit(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "v2ex.com" or host.endswith(".v2ex.com"):
        host = "v2ex.com"
    return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))


def material_hash(material: dict) -> str:
    return stable_hash({k: material.get(k) for k in ("material_id", "event_id", "topic", "text", "draft_text", "source", "review")})


def _evidence(item: Any, text: str) -> bool:
    return (isinstance(item, dict) and isinstance(item.get("evidence"), str)
            and len(item["evidence"].strip()) >= 2 and item["evidence"] in text
            and isinstance(item.get("reason"), str) and len(item["reason"].strip()) >= 8
            and item["reason"].strip().lower() not in GENERIC)


def score_material(material: dict, *, as_of: str) -> dict:
    """Apply the fixed rubric to source-grounded editorial observations.

    Semantic ratings must be supplied with exact source spans and reasoning.
    This avoids disguising noun/regex matches as audience-interest judgments.
    """
    errors = []
    source = material.get("source") or {}
    review = material.get("review") or {}
    if not isinstance(source, dict) or not isinstance(review, dict):
        raise ValueError("source and review must be objects")
    text = str(material.get("text", "")) + "\n" + str(source.get("evidence_text", ""))
    scores = {}
    for key in WEIGHTS:
        item = review.get(key)
        if not _evidence(item, text) or type(item.get("rating")) is not int or not 0 <= item["rating"] <= 4:
            errors.append(f"MISSING_GROUNDED_REVIEW:{key}")
            scores[key] = None
        else:
            scores[key] = item["rating"] * 25
    distance = review.get("audience_distance") or {}
    background = review.get("background_cost") or {}
    if not isinstance(distance, dict) or not isinstance(background, dict):
        raise ValueError("audience distance and background reviews must be objects")
    distance_value = distance.get("value", "UNKNOWN")
    background_value = background.get("value", "UNKNOWN")
    if not _evidence(distance, text) or distance_value not in {"NEAR", "MEDIUM", "FAR"}:
        errors.append("MISSING_GROUNDED_REVIEW:audience_distance")
    if not _evidence(background, text) or background_value not in {"LOW", "MEDIUM", "HIGH"}:
        errors.append("MISSING_GROUNDED_REVIEW:background_cost")
    hook = review.get("hook") or {}
    if not isinstance(hook, dict):
        raise ValueError("hook must be an object")
    if not _evidence(hook, text) or not isinstance(hook.get("text"), str) or not 2 <= len(hook["text"]) <= 30:
        errors.append("REJECT_NO_HOOK")
    try:
        observed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        published = datetime.fromisoformat(str(source["published_at"]).replace("Z", "+00:00"))
        if observed.tzinfo is None or published.tzinfo is None:
            raise ValueError("timezone required")
        age = (observed - published).total_seconds() / 3600
        if age < 0:
            raise ValueError("future source")
    except (KeyError, ValueError, TypeError):
        age = None
        errors.append("UNKNOWN_SOURCE_TIMESTAMP")
    freshness = "UNKNOWN" if age is None else "UNDER_24H" if age < 24 else "24_TO_48H" if age < 48 else "OLDER_THAN_48H"
    if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"):
        errors.append("SOURCE_REFERENCE_REQUIRED")
    if source.get("status") != "SOURCE_CHECKED":
        errors.append("HOLD_SOURCE_CHECK")
    if review.get("novelty") != "CHECKED_DISTINCT":
        errors.append("HOLD_NOVELTY_CHECK")
    # Source confidence remains an independent factual annotation. It never
    # contributes to the interest score or cures a weak stopping reason.
    total = sum((scores[k] or 0) * weight / 100 for k, weight in WEIGHTS.items())
    distance_penalty = {"NEAR": 0, "MEDIUM": 7, "FAR": 20}.get(distance_value, 30)
    background_penalty = {"LOW": 0, "MEDIUM": 9, "HIGH": 22}.get(background_value, 30)
    freshness_penalty = 0 if age is not None and age < 48 else 6 if age is not None and age < 168 else 12
    topic = max(0, round(total - distance_penalty - background_penalty - freshness_penalty, 2))
    if (scores["raw_material_strength"] or 0) < 50:
        errors.append("REJECT_WEAK_RAW_MATERIAL")
    if (scores["first_screen_stopping_power"] or 0) < 50:
        errors.append("REJECT_LOW_STOPPING_REASON")
    if distance_value == "FAR" and ((scores["surprise"] or 0) < 75 or (scores["first_screen_stopping_power"] or 0) < 75):
        errors.append("REJECT_DISTANCE_WITHOUT_EXCEPTIONAL_HOOK")
    if topic < MIN_TOPIC:
        errors.append("REJECT_LOW_TOPIC_STRENGTH")
    return {"version": VERSION, "material_hash": material_hash(material), "topic_strength": topic,
            "writing_quality": None, "audience_distance": distance_value, "background_cost": background_value,
            "freshness": freshness, "source_age_hours": round(age, 2) if age is not None else None,
            "source_timestamp_precision": source.get("timestamp_precision", "UNKNOWN"),
            "source_confidence": source.get("confidence", "UNKNOWN"), "novelty": review.get("novelty"),
            "headline_hook": hook.get("text"), **scores,
            "mass_relevance_score": scores["mass_relevance"],
            "penalties": {"distance": distance_penalty, "background": background_penalty, "freshness": freshness_penalty},
            "admitted": not errors, "reasons": errors, "as_of": as_of,
            "rating_status": "EDITORIAL_HYPOTHESIS_NOT_REACH_PREDICTION"}


def rank_materials(materials: list[dict], *, as_of: str) -> dict:
    if not isinstance(materials, list):
        raise ValueError("material pool must be an array")
    rows, ids, urls, events, texts = [], set(), set(), set(), set()
    synthetic_entries = []
    duplicates = []
    for material in materials:
        if not isinstance(material, dict):
            raise ValueError("each material must be an object")
        mid = material.get("material_id")
        source = material.get("source") or {}
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        url = canonical_url(source.get("url", ""))
        event = material.get("event_id") or url
        digest = stable_hash(material.get("text", ""))
        if str(material.get("fixture_type", "")).startswith("SYNTHETIC"):
            synthetic_entries.append(mid)
        if not mid or mid in ids or url in urls or event in events or digest in texts:
            duplicates.append(mid)
            continue
        ids.add(mid); urls.add(url); events.add(event); texts.add(digest)
        report = score_material(material, as_of=as_of)
        rows.append({"material_id": mid, "topic": material.get("topic"), "source": source.get("url"), **report})
    # Inadmissible entries cannot beat an admissible entry by source prestige.
    # Ties use lower background, nearer audience, then actual source age.
    rows.sort(key=lambda r: (not r["admitted"], -r["topic_strength"],
                            {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(r["background_cost"], 3),
                            {"NEAR": 0, "MEDIUM": 1, "FAR": 2}.get(r["audience_distance"], 3),
                            r["source_age_hours"] if r["source_age_hours"] is not None else float("inf"), r["material_id"]))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    top = rows[0] if rows else None
    margin = round(top["topic_strength"] - rows[1]["topic_strength"], 2) if len(rows) > 1 else None
    # Close scores are explicitly reported; a deterministic near/fresh/simple
    # tie-break picks a review proposal. It does not claim a meaningful lead.
    significant = margin is not None and margin >= 5
    reviewed = [row for row in rows if not any(reason.startswith(("MISSING_GROUNDED_REVIEW", "SOURCE_REFERENCE_REQUIRED", "UNKNOWN_SOURCE_TIMESTAMP"))
                                 for reason in row["reasons"]) and "HOLD_SOURCE_CHECK" not in row["reasons"]]
    reviewed_count = len(reviewed)
    fresh_count = sum(row["source_age_hours"] is not None and row["source_age_hours"] < 48 for row in rows)
    reviewed_fresh_count = sum(row["source_age_hours"] < 48 for row in reviewed)
    pool_ok = reviewed_fresh_count >= MIN_POOL and not duplicates and not synthetic_entries
    return {"version": VERSION, "as_of": as_of, "pool_hash": stable_hash(materials),
            "candidate_count": len(rows), "raw_count": len(materials), "duplicates": duplicates, "synthetic_entries": synthetic_entries,
            "competition_passed": pool_ok, "reviewed_source_count": reviewed_count, "under48h_count": fresh_count,
            "reviewed_under48h_count": reviewed_fresh_count, "ranking_margin": margin,
            "meaningful_lead": significant, "selection_basis": "SCORE_MARGIN" if significant else "CLOSE_REQUIRES_EDITORIAL_REVIEW",
            "selected_material_id": top["material_id"] if pool_ok and top and top["admitted"] and significant else None,
            "top10": rows[:10], "top5": rows[:5], "top1": top, "rows": rows}


def candidate_admission(candidate: dict) -> dict:
    pool = candidate.get("material_pool")
    as_of = candidate.get("competition_as_of")
    if not isinstance(pool, list) or not isinstance(as_of, str):
        return {"admitted": False, "reasons": ["INSUFFICIENT_COMPETITION_POOL"]}
    competition = rank_materials(pool, as_of=as_of)
    mid = candidate.get("material_id")
    row = next((r for r in competition["rows"] if r["material_id"] == mid), None)
    reasons = list(row["reasons"]) if row else ["MATERIAL_NOT_IN_POOL"]
    if not competition["competition_passed"]:
        reasons.append("INSUFFICIENT_OR_DUPLICATE_COMPETITION_POOL")
    if competition["selected_material_id"] != mid:
        reasons.append("NOT_COMPETITION_WINNER")
    material = next((m for m in pool if m.get("material_id") == mid), {})
    # Rewriting can change publication text; the source material and locked
    # facts must be bound independently from the downstream prose contract.
    if candidate.get("material_hash") != material_hash(material):
        reasons.append("MATERIAL_BINDING_MISMATCH")
    original_draft = candidate.get("draft_text_before_human_style", candidate.get("text"))
    if original_draft != material.get("draft_text", material.get("text")):
        reasons.append("MATERIAL_DRAFT_MISMATCH")
    source_url = material.get("source", {}).get("url")
    refs = [r.get("url") if isinstance(r, dict) else r for r in candidate.get("source_refs", [])]
    if source_url not in refs:
        reasons.append("MATERIAL_SOURCE_MISMATCH")
    return {"version": VERSION, "admitted": not reasons, "reasons": reasons,
            "material_id": mid, "material_hash": material_hash(material),
            "pool_hash": competition["pool_hash"], "competition_count": competition["candidate_count"],
            "rank": row.get("rank") if row else None, "ranking_margin": competition["ranking_margin"],
            "topic_strength": row.get("topic_strength") if row else None,
            "writing_quality": None, "as_of": as_of}
