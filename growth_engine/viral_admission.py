"""V2 absolute topic admission and optional, traceable structural estimates.

Ratings and bonuses are editorial hypotheses, never audience measurements or
proof of underlying claims. Prose quality cannot compensate for weak material.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .human_voice import stable_hash
from .x_native_style import extract_scene_features, review_comment_impulse

VERSION = "VIRAL_ADMISSION_V2"
WEIGHTS = {"raw_material_strength": 18, "surprise": 12, "conflict": 10,
           "self_insertion": 10, "first_screen_stopping_power": 22,
           "mass_relevance": 18, "share_potential": 5, "reply_potential": 5}
GENERIC = {"reviewed", "concrete evidence reviewed", "high", "strong", "有冲突", "有数字", "已核实"}
MIN_POOL = 1
MIN_TOPIC = 62
DEFAULT_TOP_N = 5


def auto_rate_material(material: dict) -> dict:
    """Fill missing ratings with auditable estimates, never observed engagement.

    Existing editorial judgments are preserved. Keywords can locate evidence,
    but neither a censorship word nor an engagement counter proves a claim.
    """
    result = deepcopy(material)
    text = str(result.get("text") or "")
    scene = extract_scene_features(text)
    quantities = scene["quantity_count"]
    concrete = sum(scene[k] for k in ("concrete_entity", "concrete_action", "concrete_quantity", "direct_quote", "specific_object", "event_chain"))
    contrast = bool(re.search(r"却|反而|结果|原本|一边|前后|先.{1,24}再|以前.{1,30}现在", text))
    conflict = bool(re.search(r"拒绝|赔偿|举报|辟谣|解雇|辞退|撤回|删除|删帖|封禁|争议|隐瞒|拖欠|维权|撤销", text))
    fork = review_comment_impulse(text, "REPLY")["opinion_branching"]
    near = bool(re.search(r"工资|工作|房租|朋友|父母|同事|老板|微信|AI|模型|员工|医院|学校|业主", text, re.I))
    first = next((s.strip() for s in re.split(r"[。！？!?\n]", text) if s.strip()), "")
    dimensions = {
        "raw_material_strength": min(4, 1 + (concrete >= 3) + (quantities > 0 or scene["direct_quote"]) + contrast),
        "surprise": min(4, 1 + contrast * 2 + (conflict and quantities > 0)),
        "conflict": min(4, 1 + conflict + (scene["entity_count"] >= 2) + fork),
        "self_insertion": 3 if near and concrete >= 3 else 2 if concrete >= 3 else 1,
        "first_screen_stopping_power": min(4, 1 + (len(first) <= 70 and concrete >= 3) + contrast + (conflict and quantities > 0)),
        "mass_relevance": 3 if near and len(first) <= 70 else 2 if concrete >= 3 else 1,
        "share_potential": min(4, 1 + (concrete >= 3) + contrast + bool(scene["direct_quote"])),
        "reply_potential": 3 if fork else 1,
    }
    review = result.setdefault("review", {})
    if not isinstance(review, dict): raise ValueError("review must be an object")
    evidence = text[:200]
    trace = f"具体结构{concrete}/6、数量{quantities}、反差{int(contrast)}、冲突{int(conflict)}；仅启发式初评，须编辑核验。"
    added = []
    for key, rating in dimensions.items():
        existing = review.get(key)
        if key not in review or (isinstance(existing, dict) and existing.get("rating") is None):
            review[key] = {"rating": int(rating), "evidence": evidence, "reason": key+": "+trace,
                           **(existing or {})}
            review[key]["rating"] = int(rating)
            added.append(key)
    review.setdefault("audience_distance", {"value": "NEAR" if near else "MEDIUM", "evidence": evidence, "reason": "按明确工作生活线索估计读者距离，不能把身份词当成已证实的读者兴趣。"})
    review.setdefault("background_cost", {"value": "HIGH" if len(text) > 800 else "MEDIUM" if len(text) > 350 else "LOW", "evidence": evidence, "reason": "按需要阅读的原始文本长度估计前情成本，保留人工覆盖能力。"})
    review.setdefault("hook", {"text": first[:30], "evidence": evidence, "reason": "提取原文第一句作为待编辑检验的首屏假设，不自动编写反转或夸张标题。"})
    result["auto_rating"] = {"version": "STRUCTURAL_ESTIMATE_V1", "filled_dimensions": added,
        "features": scene, "status": "HEURISTIC_NOT_VERIFIED_REACH", "engagement_used": False}
    return result


def _viral_bonus(material: dict, text: str) -> dict:
    evidence = material.get("verified_evidence", {})
    if not isinstance(evidence, dict): evidence = {}
    def verified(key):
        item = evidence.get(key)
        return (_evidence(item, text) and item.get("status") == "VERIFIED"
                and isinstance(item.get("url"), str) and item["url"].startswith("https://"))
    # A 404/被删/截图 keyword alone is not proof of censorship or an artifact.
    censorship = 8 if verified("censorship") else 0
    hard = 6 if verified("artifact") or re.search(r"\d+(?:\.\d+)?\s*(?:万|亿)?(?:元|美元|块)", text) else 0
    dilemma = 6 if review_comment_impulse(text, "REPLY")["opinion_branching"] else 0
    return {"censorship_scarcity_bonus": censorship, "hard_evidence_bonus": hard,
            "human_nature_dilemma_bonus": dilemma, "total": min(20, censorship+hard+dilemma),
            "status": "EDITORIAL_SIGNALS_NOT_PROOF_OF_VIRALITY"}


def canonical_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    parsed = urlsplit(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "v2ex.com" or host.endswith(".v2ex.com"):
        host = "v2ex.com"
    return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))


def material_hash(material: dict) -> str:
    fields = {k: material.get(k) for k in ("material_id", "event_id", "topic", "text", "draft_text", "source", "review")}
    if "verified_evidence" in material:
        fields["verified_evidence"] = material["verified_evidence"]
    return stable_hash(fields)


def _evidence(item: Any, text: str) -> bool:
    return (isinstance(item, dict) and isinstance(item.get("evidence"), str)
            and len(item["evidence"].strip()) >= 2 and item["evidence"] in text
            and isinstance(item.get("reason"), str) and len(item["reason"].strip()) >= 8
            and item["reason"].strip().lower() not in GENERIC)


def score_material(material: dict, *, as_of: str) -> dict:
    """Apply the fixed rubric to source-grounded editorial observations.

    Supplied judgments retain priority. Missing ratings receive explicitly
    labelled heuristic estimates; invalid evidence and unknown provenance hold.
    """
    errors = []
    rated = auto_rate_material(material)
    source = rated.get("source") or {}
    review = rated.get("review") or {}
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
    distance_penalty = {"NEAR": 0, "MEDIUM": 4, "FAR": 8}.get(distance_value, 30)
    background_penalty = {"LOW": 0, "MEDIUM": 4, "HIGH": 8}.get(background_value, 30)
    freshness_penalty = 0 if age is not None and age < 48 else 6 if age is not None and age < 168 else 12
    bonus = _viral_bonus(material, text)
    topic = min(100, max(0, round(total + bonus["total"] - distance_penalty - background_penalty - freshness_penalty, 2)))
    if (scores["raw_material_strength"] or 0) < 50:
        errors.append("REJECT_WEAK_RAW_MATERIAL")
    if (scores["first_screen_stopping_power"] or 0) < 50:
        errors.append("REJECT_LOW_STOPPING_REASON")
    if topic < MIN_TOPIC:
        errors.append("REJECT_LOW_TOPIC_STRENGTH")
    return {"version": VERSION, "material_hash": material_hash(material), "topic_strength": topic,
            "writing_quality": None, "audience_distance": distance_value, "background_cost": background_value,
            "viral_bonus": bonus, "auto_rating": rated["auto_rating"],
            "freshness": freshness, "source_age_hours": round(age, 2) if age is not None else None,
            "source_timestamp_precision": source.get("timestamp_precision", "UNKNOWN"),
            "source_confidence": source.get("confidence", "UNKNOWN"), "novelty": review.get("novelty"),
            "headline_hook": hook.get("text"), **scores,
            "mass_relevance_score": scores["mass_relevance"],
            "penalties": {"distance": distance_penalty, "background": background_penalty, "freshness": freshness_penalty},
            "admitted": not errors, "reasons": errors, "as_of": as_of,
            "rating_status": "EDITORIAL_HYPOTHESIS_NOT_REACH_PREDICTION"}


def rank_materials(materials: list[dict], *, as_of: str, top_n: int = DEFAULT_TOP_N) -> dict:
    if not isinstance(materials, list):
        raise ValueError("material pool must be an array")
    if not isinstance(top_n, int) or not 1 <= top_n <= 20:
        raise ValueError("top_n must be between 1 and 20")
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
    # Margin remains audit information; V2 does not use it to reject ties.
    significant = margin is not None and margin >= 5
    reviewed = [row for row in rows if not any(reason.startswith(("MISSING_GROUNDED_REVIEW", "SOURCE_REFERENCE_REQUIRED", "UNKNOWN_SOURCE_TIMESTAMP"))
                                 for reason in row["reasons"]) and "HOLD_SOURCE_CHECK" not in row["reasons"]]
    reviewed_count = len(reviewed)
    fresh_count = sum(row["source_age_hours"] is not None and row["source_age_hours"] < 48 for row in rows)
    reviewed_fresh_count = sum(row["source_age_hours"] < 48 for row in reviewed)
    pool_ok = reviewed_count >= MIN_POOL and not duplicates and not synthetic_entries
    selected = [row["material_id"] for row in rows if row["admitted"]][:top_n] if pool_ok else []
    return {"version": VERSION, "as_of": as_of, "pool_hash": stable_hash(materials),
            "candidate_count": len(rows), "raw_count": len(materials), "duplicates": duplicates, "synthetic_entries": synthetic_entries,
            "competition_passed": pool_ok, "reviewed_source_count": reviewed_count, "under48h_count": fresh_count,
            "reviewed_under48h_count": reviewed_fresh_count, "ranking_margin": margin,
            "meaningful_lead": significant, "selection_basis": "ABSOLUTE_THRESHOLD_TOP_N", "top_n": top_n,
            "selected_material_ids": selected, "selected_material_id": selected[0] if selected else None,
            "top10": rows[:10], "top5": rows[:5], "top1": top, "rows": rows}


def candidate_admission(candidate: dict) -> dict:
    pool = candidate.get("material_pool")
    as_of = candidate.get("competition_as_of")
    if not isinstance(pool, list) or not isinstance(as_of, str):
        return {"admitted": False, "reasons": ["INSUFFICIENT_COMPETITION_POOL"]}
    competition = rank_materials(pool, as_of=as_of, top_n=candidate.get("admission_top_n", DEFAULT_TOP_N))
    mid = candidate.get("material_id")
    row = next((r for r in competition["rows"] if r["material_id"] == mid), None)
    reasons = list(row["reasons"]) if row else ["MATERIAL_NOT_IN_POOL"]
    if not competition["competition_passed"]:
        reasons.append("INSUFFICIENT_OR_DUPLICATE_COMPETITION_POOL")
    if mid not in competition["selected_material_ids"]:
        reasons.append("NOT_IN_ADMITTED_TOP_N")
    material = next((m for m in pool if m.get("material_id") == mid), {})
    # Rewriting can change publication text; the source material and locked
    # facts must be bound independently from the downstream prose contract.
    if candidate.get("material_hash") != material_hash(material):
        reasons.append("MATERIAL_BINDING_MISMATCH")
    original_draft = candidate.get("draft_text_before_human_style", candidate.get("text"))
    if original_draft != material.get("draft_text", material.get("text")):
        reasons.append("MATERIAL_DRAFT_MISMATCH")
    source_url = material.get("source", {}).get("url")
    source = material.get("source", {})
    if source.get("fact_verification") == "UNVERIFIED":
        proof = candidate.get("source_fact_review")
        corpus = str(material.get("text", "")) + "\n" + str(source.get("evidence_text", ""))
        if (not _evidence(proof, corpus) or proof.get("status") != "FACT_BOUNDARIES_REVIEWED"
                or proof.get("url") != source_url):
            reasons.append("HOLD_DISCOVERED_SOURCE_FACT_REVIEW")
    refs = [r.get("url") if isinstance(r, dict) else r for r in candidate.get("source_refs", [])]
    if source_url not in refs:
        reasons.append("MATERIAL_SOURCE_MISMATCH")
    return {"version": VERSION, "admitted": not reasons, "reasons": reasons,
            "material_id": mid, "material_hash": material_hash(material),
            "pool_hash": competition["pool_hash"], "competition_count": competition["candidate_count"],
            "rank": row.get("rank") if row else None, "ranking_margin": competition["ranking_margin"],
            "top_n": competition["top_n"],
            "topic_strength": row.get("topic_strength") if row else None,
            "writing_quality": None, "as_of": as_of}
