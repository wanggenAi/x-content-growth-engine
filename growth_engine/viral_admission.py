"""Preview screening and strict production topic competition.

Automatic signals only decide what deserves editorial review. Production
admission requires a grounded deep review, a fresh multi-source pool, and one
winner. Scores are editorial hypotheses, never reach predictions.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
from difflib import SequenceMatcher
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .human_voice import stable_hash
from .x_native_style import extract_scene_features, review_comment_impulse

VERSION = "VIRAL_ADMISSION_V3"
PREVIEW_MODE = "PREVIEW_ONLY"
PRODUCTION_MODE = "PRODUCTION_COMPETITION"
ABSOLUTE_MIN_POOL = 10
TARGET_RAW_POOL = 30
TARGET_REVIEWED_POOL = 20
MIN_FRESH_POOL = 10
MIN_SOURCE_FAMILIES = 4
MIN_TOPIC = 62
DEFAULT_TOP_N = 5
WEIGHTS = {
    # Editorial policy, not fitted engagement coefficients. Importance and
    # audience breadth must not substitute for a concrete reader payoff.
    "raw_material_strength": 18, "surprise": 16, "conflict": 6,
    "self_insertion": 14, "first_screen_stopping_power": 22,
    "mass_relevance": 10, "share_potential": 9, "reply_potential": 5,
}
GENERIC = {"reviewed", "concrete evidence reviewed", "high", "strong", "有冲突", "有数字", "已核实"}
SUPPORT_TERMS = {
    "surprise": r"反差|意外|反转|预期|矛盾|没想到|unexpected|reversal|contrast",
    "conflict": r"冲突|双方|利益|规则|边界|对立|责任|承担|conflict|boundary",
    "self_insertion": r"读者|普通人|用户|上班族|家庭|朋友|伴侣|代入|audience|reader",
    "first_screen_stopping_power": r"首屏|第一句|三秒|停留|具体动作|hook|first.screen",
    "mass_relevance": r"大众|多数|广泛|日常|低门槛|不需背景|随机读者|mass|broad",
    "share_potential": r"转发|分享|发给|提醒|共鸣|share",
    "reply_potential": r"分叉|不同判断|评论方向|立场|取舍|branch|reply",
}


def canonical_url(url: str) -> str:
    if not isinstance(url, str): return ""
    parsed = urlsplit(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "v2ex.com" or host.endswith(".v2ex.com"): host = "v2ex.com"
    return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))


def source_family(source: dict) -> str:
    explicit = str(source.get("family") or source.get("source_family") or "").upper()
    if explicit: return explicit
    method = str(source.get("method") or "").upper()
    host = urlsplit(str(source.get("url") or "")).netloc.lower()
    if "TELEGRAM" in method or host == "t.me": return "TELEGRAM"
    if "HACKER_NEWS" in method or host.endswith("ycombinator.com"): return "HACKER_NEWS"
    if "GITHUB" in method or host == "github.com": return "GITHUB"
    if "REDDIT" in method or host.endswith("reddit.com"): return "REDDIT"
    if "SEARCH" in method: return "SEARCH_LEADS"
    if host.endswith("chinadigitaltimes.net"): return "CHINESE_MEDIA"
    if "RSS" in method: return "NEWS_MEDIA"
    return "OTHER"


def material_hash(material: dict) -> str:
    fields = {k: material.get(k) for k in ("material_id", "event_id", "event_key", "topic", "text", "draft_text", "source", "review")}
    if "verified_evidence" in material: fields["verified_evidence"] = material["verified_evidence"]
    if "source_evidence" in material: fields["source_evidence"] = material["source_evidence"]
    return stable_hash(fields)


def _evidence(item: Any, text: str) -> bool:
    return (isinstance(item, dict) and isinstance(item.get("evidence"), str)
            and len(item["evidence"].strip()) >= 2 and item["evidence"] in text
            and isinstance(item.get("reason"), str) and len(item["reason"].strip()) >= 8
            and item["reason"].strip().lower() not in GENERIC)


def auto_rate_material(material: dict) -> dict:
    """Attach a coarse screen without creating or modifying editorial review."""
    result = deepcopy(material)
    text = str(result.get("text") or "")
    scene = extract_scene_features(text)
    concrete = sum(scene[k] for k in ("concrete_entity", "concrete_action", "concrete_quantity", "direct_quote", "specific_object", "event_chain"))
    contrast = bool(re.search(r"却|反而|结果|原本|没想到|先.{1,24}再|以前.{1,30}现在", text))
    conflict = bool(re.search(r"拒绝|赔偿|举报|解雇|辞退|删除|争议|隐瞒|拖欠|维权|分账|不同意|责任", text))
    branch = bool(review_comment_impulse(text, "REPLY")["opinion_branching"])
    first = next((s.strip() for s in re.split(r"[。！？!?\n]", text) if s.strip()), "")
    components = {
        "concrete_scene": min(25, concrete * 4), "contrast": 20 if contrast else 0,
        "visible_conflict": 18 if conflict else 0,
        "first_screen": 22 if first and len(first) <= 70 and concrete >= 2 else 6 if first else 0,
        "branch_signal": 15 if branch else 0,
    }
    score = min(100, sum(components.values()))
    result["auto_screen"] = {
        "version": "AUTO_SCREEN_V2", "score": score, "components": components,
        "features": scene, "decision": "SEND_TO_DEEP_REVIEW" if score >= 45 else "LOW_PRIORITY",
        "status": "HEURISTIC_ONLY_NOT_PRODUCTION_SCORE", "engagement_used": False,
    }
    return result


def validate_deep_review(material: dict) -> dict:
    """Validate that production ratings are independent and dimension-grounded."""
    review = material.get("review") or {}; source = material.get("source") or {}
    corpus = str(material.get("text") or "") + "\n" + str(source.get("evidence_text") or "")
    reasons: list[str] = []
    if review.get("strategy_version") == "V4":
        from .content_review import reader_value_reasons
        reasons.extend(reader_value_reasons(review.get("reader_value")))
    if review.get("review_type") != "DEEP_EDITORIAL_REVIEW": reasons.append("MISSING_DEEP_EDITORIAL_REVIEW")
    if not review.get("reviewer") or not review.get("reviewed_at"): reasons.append("MISSING_DEEP_REVIEW_AUDIT")
    evidences, rationales = [], []
    for key in WEIGHTS:
        item = review.get(key)
        if not _evidence(item, corpus) or type((item or {}).get("rating")) is not int or not 0 <= item["rating"] <= 4:
            reasons.append(f"MISSING_GROUNDED_REVIEW:{key}"); continue
        evidences.append(item["evidence"].strip()); rationales.append(item["reason"].strip())
        support = SUPPORT_TERMS.get(key)
        if support and item["rating"] >= 2 and not re.search(support, item["reason"], re.I):
            reasons.append(f"UNSUPPORTED_DIMENSION_REASON:{key}")
    if any(count >= 3 for count in Counter(evidences).values()): reasons.append("DUPLICATED_DIMENSION_EVIDENCE")
    if any(count >= 3 for count in Counter(rationales).values()): reasons.append("DUPLICATED_DIMENSION_REASON")
    surprise = review.get("surprise") or {}
    contrast = review.get("contrast_basis") or {}
    grounded_contrast = (all(isinstance(contrast.get(k), str) and len(contrast[k]) >= 4 and contrast[k] in corpus
                             for k in ("before", "after")) and contrast.get("before") != contrast.get("after"))
    if surprise.get("rating", 0) >= 2 and not grounded_contrast and not re.search(r"却|反而|结果|原本|没想到|先.{1,20}再|以前.{1,30}现在", surprise.get("evidence", "")):
        reasons.append("UNSUPPORTED_DIMENSION_EVIDENCE:surprise")
    conflict = review.get("conflict") or {}
    if conflict.get("rating", 0) >= 2 and not re.search(r"拒绝|争议|分账|不同意|承担|责任|冲突|一方|另一方|老板|员工|朋友", conflict.get("evidence", "")):
        reasons.append("UNSUPPORTED_DIMENSION_EVIDENCE:conflict")
    reply = review.get("reply_potential") or {}; branches = review.get("possible_reply_branches")
    if reply.get("rating", 0) >= 2 and (not isinstance(branches, list) or len({str(x).strip() for x in branches if str(x).strip()}) < 2):
        reasons.append("UNSUPPORTED_REPLY_BRANCHES")
    for key, allowed in (("audience_distance", {"NEAR", "MEDIUM", "FAR"}), ("background_cost", {"LOW", "MEDIUM", "HIGH"})):
        item = review.get(key) or {}
        if not _evidence(item, corpus) or item.get("value") not in allowed: reasons.append(f"MISSING_GROUNDED_REVIEW:{key}")
    hook = review.get("hook") or {}
    if not _evidence(hook, corpus) or not isinstance(hook.get("text"), str) or not 2 <= len(hook["text"]) <= 30 or hook["text"] not in corpus:
        reasons.append("REJECT_NO_HOOK")
    if review.get("novelty") != "CHECKED_DISTINCT": reasons.append("HOLD_NOVELTY_CHECK")
    return {"passed": not reasons, "reasons": sorted(set(reasons))}


def _verified_bonus(material: dict, corpus: str) -> dict:
    evidence = material.get("verified_evidence") or {}
    if not isinstance(evidence, dict): evidence = {}
    def verified(key: str) -> bool:
        item = evidence.get(key)
        return (_evidence(item, corpus) and item.get("status") == "VERIFIED"
                and isinstance(item.get("url"), str) and item["url"].startswith("https://"))
    censorship = 8 if verified("censorship") else 0
    artifact = 6 if verified("artifact") else 0
    cost = evidence.get("cost_binding") or {}
    bound_cost = 6 if verified("cost_binding") and re.search(r"差距|代价|成本|反差|省.{0,20}(?:花|烧|赔)|多.{0,10}少", cost.get("reason", "")) else 0
    # Reply potential already has a review dimension. Counting the same
    # keyword-derived fork again was circular evidence for a high topic score.
    dilemma = 0
    hard = max(artifact, bound_cost)
    return {"censorship_scarcity_bonus": censorship, "hard_evidence_bonus": hard,
            "human_nature_dilemma_bonus": dilemma, "total": min(20, censorship + hard + dilemma),
            "status": "VERIFIED_EDITORIAL_SIGNALS_NOT_PROOF_OF_VIRALITY"}


def _source_age(source: dict, as_of: str) -> tuple[float | None, str | None]:
    try:
        # A recent mirror/repost cannot reset a known event's age.
        timestamp = source.get("event_time") or source.get("published_at")
        observed = datetime.fromisoformat(as_of.replace("Z", "+00:00")); published = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if observed.tzinfo is None or published.tzinfo is None: raise ValueError
        age = (observed - published).total_seconds() / 3600
        if age < 0: raise ValueError
        return age, None
    except (KeyError, ValueError, TypeError): return None, "UNKNOWN_SOURCE_TIMESTAMP"


def score_material(material: dict, *, as_of: str, admission_mode: str = PRODUCTION_MODE) -> dict:
    if admission_mode not in {PREVIEW_MODE, PRODUCTION_MODE}: raise ValueError("invalid admission mode")
    screened = auto_rate_material(material); source = material.get("source") or {}; review = material.get("review") or {}
    if not isinstance(source, dict) or not isinstance(review, dict): raise ValueError("source and review must be objects")
    corpus = str(material.get("text") or "") + "\n" + str(source.get("evidence_text") or "")
    deep = validate_deep_review(material); errors = list(deep["reasons"]) if admission_mode == PRODUCTION_MODE else []
    scores = {key: (review.get(key) or {}).get("rating") * 25 if deep["passed"] else None for key in WEIGHTS}
    distance = (review.get("audience_distance") or {}).get("value", "UNKNOWN") if deep["passed"] else "UNKNOWN"
    background = (review.get("background_cost") or {}).get("value", "UNKNOWN") if deep["passed"] else "UNKNOWN"
    age, age_error = _source_age(source, as_of)
    if age_error: errors.append(age_error)
    if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"): errors.append("SOURCE_REFERENCE_REQUIRED")
    if source.get("status") != "SOURCE_CHECKED": errors.append("HOLD_SOURCE_CHECK")
    if material.get("user_content_verdict") == "REJECT": errors.append("CONTENT_USER_REJECTED")
    if review.get("decision", "PASS") != "PASS": errors.append("TOPIC_EDITOR_HOLD")
    bonus = _verified_bonus(material, corpus)
    if deep["passed"]:
        total = sum(scores[k] * weight / 100 for k, weight in WEIGHTS.items())
        distance_penalty = {"NEAR": 0, "MEDIUM": 4, "FAR": 8}[distance]; background_penalty = {"LOW": 0, "MEDIUM": 4, "HIGH": 8}[background]
        freshness_penalty = 0 if age is not None and age < 48 else 6 if age is not None and age < 168 else 12
        editorial = min(100, max(0, round(total + bonus["total"] - distance_penalty - background_penalty - freshness_penalty, 2)))
        if scores["raw_material_strength"] < 50: errors.append("REJECT_WEAK_RAW_MATERIAL")
        if scores["first_screen_stopping_power"] < 50: errors.append("REJECT_LOW_STOPPING_REASON")
        if editorial < MIN_TOPIC: errors.append("REJECT_LOW_TOPIC_STRENGTH")
    else:
        editorial = None; distance_penalty = background_penalty = 0
        freshness_penalty = 0 if age is not None and age < 48 else 6 if age is not None and age < 168 else 12
    return {"version": VERSION, "admission_mode": admission_mode, "material_hash": material_hash(material),
        "auto_screen_score": screened["auto_screen"]["score"], "auto_screen": screened["auto_screen"],
        "editorial_topic_score": editorial, "topic_strength": editorial, "deep_review": deep,
        "viral_bonus": bonus, "source_family": source_family(source), "source_age_hours": round(age, 3) if age is not None else None,
        "freshness": "UNKNOWN" if age is None else "UNDER_24H" if age < 24 else "24_TO_48H" if age < 48 else "OLDER_THAN_48H",
        "audience_distance": distance, "background_cost": background,
        "headline_hook": (review.get("hook") or {}).get("text") if deep["passed"] else None,
        **scores, "mass_relevance_score": scores["mass_relevance"],
        "penalties": {"distance": distance_penalty, "background": background_penalty, "freshness": freshness_penalty},
        "preview_eligible": screened["auto_screen"]["score"] >= 45,
        "admitted": admission_mode == PRODUCTION_MODE and editorial is not None and not errors,
        "reasons": sorted(set(errors)), "as_of": as_of,
        "rating_status": "EDITORIAL_DEEP_REVIEW" if deep["passed"] else "AUTO_SCREEN_ONLY"}


def _event_key(material: dict) -> str:
    explicit = material.get("event_key") or material.get("event_id")
    if explicit and explicit != (material.get("source") or {}).get("url"): return str(explicit)
    title = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(material.get("topic") or "").lower())
    return stable_hash({"title": title, "day": str((material.get("source") or {}).get("published_at") or "")[:10]})


def _same_event(left: dict, right: dict) -> bool:
    ls, rs = left.get("source") or {}, right.get("source") or {}
    if canonical_url(ls.get("url", "")) == canonical_url(rs.get("url", "")): return True
    left_event, right_event = left.get("event_id"), right.get("event_id")
    if left_event and right_event:
        if left_event == right_event: return True
        # Explicit, independently assigned event identities take precedence
        # over fuzzy title matching.
        if left_event != ls.get("url") and right_event != rs.get("url"): return False
    if left.get("event_key") and left.get("event_key") == right.get("event_key"): return True
    if stable_hash(re.sub(r"\s+", "", str(left.get("text") or ""))) == stable_hash(re.sub(r"\s+", "", str(right.get("text") or ""))): return True
    lt, rt = str(left.get("topic") or ""), str(right.get("topic") or "")
    same_day = str(ls.get("published_at") or "")[:10] == str(rs.get("published_at") or "")[:10]
    return bool(same_day and lt and rt and SequenceMatcher(None, lt, rt).ratio() >= .86)


def deduplicate_materials(materials: list[dict]) -> tuple[list[dict], list[dict]]:
    unique: list[dict] = []; clusters: list[dict] = []
    for material in materials:
        match = next((i for i, existing in enumerate(unique) if _same_event(existing, material)), None)
        if match is None: unique.append(material); continue
        cluster = next((c for c in clusters if c["canonical_material_id"] == unique[match].get("material_id")), None)
        if cluster is None:
            cluster = {"event_key": _event_key(unique[match]), "canonical_material_id": unique[match].get("material_id"), "merged_material_ids": [], "source_families": [source_family(unique[match].get("source") or {})]}; clusters.append(cluster)
        cluster["merged_material_ids"].append(material.get("material_id")); cluster["source_families"] = sorted(set(cluster["source_families"] + [source_family(material.get("source") or {})]))
    return unique, clusters


def _second_stage(rows: list[dict]) -> dict | None:
    if len(rows) < 2 or rows[0]["editorial_topic_score"] is None or rows[1]["editorial_topic_score"] is None: return None
    margin = round(rows[0]["editorial_topic_score"] - rows[1]["editorial_topic_score"], 2)
    if margin >= 5: return None
    contenders = [r for r in rows if r["admitted"] and rows[0]["editorial_topic_score"] - r["editorial_topic_score"] < 5]
    if len(contenders) < 2: return None
    def judge(row: dict):
        return (row["first_screen_stopping_power"] or 0, row["surprise"] or 0,
                row["self_insertion"] or 0, row["share_potential"] or 0, row["reply_potential"] or 0,
                row["raw_material_strength"] or 0, -row["penalties"]["background"],
                -row["penalties"]["distance"], row["mass_relevance"] or 0,
                -(row["source_age_hours"] if row["source_age_hours"] is not None else 10**9))
    ordered = sorted(contenders, key=lambda r: (judge(r), r["material_id"]), reverse=True); winner = ordered[0]
    return {"status": "SECOND_STAGE_EDITORIAL_JUDGE", "trigger_margin": margin,
        "criteria": ["3_SECOND_STOP", "SURPRISE", "SELF_INSERTION", "SHARE_POTENTIAL", "REPLY_POTENTIAL",
                     "RAW_MATERIAL_STRENGTH", "BACKGROUND_COST", "AUDIENCE_DISTANCE", "MASS_RELEVANCE", "SOURCE_FRESHNESS"],
        "contenders": [r["material_id"] for r in ordered], "winner": winner["material_id"],
        "decision_trace": {r["material_id"]: list(judge(r)) for r in ordered}}


def rank_materials(materials: list[dict], *, as_of: str, top_n: int = DEFAULT_TOP_N, admission_mode: str = PREVIEW_MODE) -> dict:
    if not isinstance(materials, list): raise ValueError("material pool must be an array")
    if not isinstance(top_n, int) or not 1 <= top_n <= 20: raise ValueError("top_n must be between 1 and 20")
    if admission_mode not in {PREVIEW_MODE, PRODUCTION_MODE}: raise ValueError("invalid admission mode")
    synthetic = [m.get("material_id") for m in materials if str(m.get("fixture_type", "")).startswith("SYNTHETIC")]
    unique, clusters = deduplicate_materials(materials); rows = []
    for material in unique:
        if not isinstance(material, dict): raise ValueError("each material must be an object")
        mid = material.get("material_id")
        if not mid: raise ValueError("material_id required")
        report = score_material(material, as_of=as_of, admission_mode=admission_mode)
        rows.append({"material_id": mid, "topic": material.get("topic"), "source": (material.get("source") or {}).get("url"), **report})
    def rank_score(row):
        value = row["editorial_topic_score"] if row["editorial_topic_score"] is not None else row["auto_screen_score"]
        if admission_mode == PRODUCTION_MODE:
            tier = 0 if row["admitted"] else 1 if row["deep_review"]["passed"] else 2
        else:
            tier = 0 if row["preview_eligible"] else 1
        return (tier, -value, row["penalties"]["background"], row["penalties"]["distance"], row["source_age_hours"] if row["source_age_hours"] is not None else float("inf"), row["material_id"])
    rows.sort(key=rank_score); stage = _second_stage(rows) if admission_mode == PRODUCTION_MODE else None
    if stage and rows and stage["winner"] != rows[0]["material_id"]:
        winner = next(r for r in rows if r["material_id"] == stage["winner"]); rows.remove(winner); rows.insert(0, winner)
    for index, row in enumerate(rows, 1): row["rank"] = index
    valid = [r for r in rows if r["deep_review"]["passed"] and "UNKNOWN_SOURCE_TIMESTAMP" not in r["reasons"] and "HOLD_SOURCE_CHECK" not in r["reasons"]]
    fresh = [r for r in rows if r["source_age_hours"] is not None and r["source_age_hours"] < 48]
    families = sorted({r["source_family"] for r in rows}); pool_reasons = []
    if len(unique) < ABSOLUTE_MIN_POOL: pool_reasons.append("FAIL_INSUFFICIENT_PRODUCTION_COMPETITION")
    if len(unique) < TARGET_RAW_POOL: pool_reasons.append("HUNT_INCOMPLETE_RAW_POOL")
    if len(valid) < TARGET_REVIEWED_POOL: pool_reasons.append("HUNT_INCOMPLETE_DEEP_REVIEW")
    if len(fresh) < MIN_FRESH_POOL: pool_reasons.append("HUNT_INCOMPLETE_FRESH_POOL")
    if len(families) < MIN_SOURCE_FAMILIES: pool_reasons.append("HUNT_INCOMPLETE_SOURCE_DIVERSITY")
    if synthetic: pool_reasons.append("SYNTHETIC_MATERIAL_IN_PRODUCTION_POOL")
    production_ok = admission_mode == PRODUCTION_MODE and not pool_reasons
    if admission_mode == PREVIEW_MODE:
        selected = [r["material_id"] for r in rows if r["preview_eligible"]][:top_n]; status = PREVIEW_MODE
    else:
        selected = [rows[0]["material_id"]] if production_ok and rows and rows[0]["admitted"] else []; status = "PRODUCTION_WINNER" if selected else "HUNT_INCOMPLETE"
    margin = None
    if len(rows) > 1:
        key = "editorial_topic_score" if admission_mode == PRODUCTION_MODE else "auto_screen_score"; a, b = rows[0][key], rows[1][key]
        if a is not None and b is not None: margin = round(a - b, 2)
    return {"version": VERSION, "admission_mode": admission_mode, "status": status, "as_of": as_of,
        "pool_hash": stable_hash(materials), "candidate_count": len(unique), "raw_count": len(materials),
        "duplicate_clusters": clusters, "duplicates": [x for c in clusters for x in c["merged_material_ids"]], "synthetic_entries": synthetic,
        "competition_passed": production_ok if admission_mode == PRODUCTION_MODE else bool(selected),
        "pool_reasons": pool_reasons if admission_mode == PRODUCTION_MODE else [], "reviewed_source_count": len(valid),
        "under48h_count": len(fresh), "reviewed_under48h_count": sum(r in fresh for r in valid),
        "source_families": families, "source_family_count": len(families), "source_family_counts": dict(Counter(r["source_family"] for r in rows)),
        "production_requirements": {"absolute_min_pool": ABSOLUTE_MIN_POOL, "target_raw_pool": TARGET_RAW_POOL, "target_reviewed_pool": TARGET_REVIEWED_POOL, "min_under48h": MIN_FRESH_POOL, "min_source_families": MIN_SOURCE_FAMILIES},
        "ranking_margin": margin, "second_stage_judge": stage,
        "selection_basis": "AUTO_SCREEN_PREVIEW_TOP_N" if admission_mode == PREVIEW_MODE else "DEEP_REVIEW_UNIQUE_TOP1",
        "top_n": top_n if admission_mode == PREVIEW_MODE else 1, "selected_material_ids": selected, "selected_material_id": selected[0] if selected else None,
        "top10": rows[:10], "top5": rows[:5], "top3": rows[:3], "top1": rows[0] if rows else None, "rows": rows}


def candidate_admission(candidate: dict) -> dict:
    pool, as_of = candidate.get("material_pool"), candidate.get("competition_as_of")
    if not isinstance(pool, list) or not isinstance(as_of, str): return {"version": VERSION, "admitted": False, "reasons": ["INSUFFICIENT_COMPETITION_POOL"]}
    competition = rank_materials(pool, as_of=as_of, admission_mode=PRODUCTION_MODE); mid = candidate.get("material_id")
    row = next((r for r in competition["rows"] if r["material_id"] == mid), None); reasons = list(row["reasons"]) if row else ["MATERIAL_NOT_IN_POOL"]
    if candidate.get("admission_mode") != PRODUCTION_MODE: reasons.append("PRODUCTION_COMPETITION_REQUIRED")
    reasons.extend(competition["pool_reasons"])
    if mid != competition["selected_material_id"]: reasons.append("NOT_PRODUCTION_WINNER")
    material = next((m for m in pool if m.get("material_id") == mid), {})
    if candidate.get("material_hash") != material_hash(material): reasons.append("MATERIAL_BINDING_MISMATCH")
    original_draft = candidate.get("draft_text_before_human_style", candidate.get("text"))
    if original_draft != material.get("draft_text", material.get("text")): reasons.append("MATERIAL_DRAFT_MISMATCH")
    source = material.get("source", {}); source_url = source.get("url")
    if source.get("fact_verification") == "UNVERIFIED":
        proof = candidate.get("source_fact_review"); corpus = str(material.get("text", "")) + "\n" + str(source.get("evidence_text", ""))
        if not _evidence(proof, corpus) or proof.get("status") != "FACT_BOUNDARIES_REVIEWED" or proof.get("url") != source_url: reasons.append("HOLD_DISCOVERED_SOURCE_FACT_REVIEW")
    refs = [r.get("url") if isinstance(r, dict) else r for r in candidate.get("source_refs", [])]
    if source_url not in refs: reasons.append("MATERIAL_SOURCE_MISMATCH")
    reasons = sorted(set(reasons))
    return {"version": VERSION, "admitted": not reasons, "reasons": reasons, "material_id": mid,
        "material_hash": material_hash(material), "pool_hash": competition["pool_hash"], "competition_count": competition["candidate_count"],
        "rank": row.get("rank") if row else None, "ranking_margin": competition["ranking_margin"], "second_stage_judge": competition["second_stage_judge"],
        "top_n": 1, "topic_strength": row.get("editorial_topic_score") if row else None, "writing_quality": None, "as_of": as_of}
