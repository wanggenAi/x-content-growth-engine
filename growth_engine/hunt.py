"""Codex's free public-material hunting and checked draft-preview workflow."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .discovery import auto_discover_materials
from .human_voice import generate_viral_variants_prompt, run_human_style_pipeline
from .viral_admission import PREVIEW_MODE, PRODUCTION_MODE, auto_rate_material, rank_materials
from .x_native_style import extract_scene_features
from .content_review import review_content, review_variant_set


def lock_draft_facts(text: str) -> dict:
    """Extract literal rewrite locks, not independent factual verification."""
    return {
        "numbers": sorted(set(re.findall(r"\d+(?:[.,:]\d+)*(?:万|亿|元|块|岁|人|小时|点)?", text))),
        "dates": sorted(set(re.findall(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日", text))),
        "quotes": re.findall(r'[“「『\"].*?[”」』\"]', text),
        "urls": re.findall(r"https?://\S+", text),
        "roles": extract_scene_features(text)["entities"],
        "boundaries": [word for word in ("据称", "自述", "网传", "未经核实", "尚未", "否认", "如果", "假如") if word in text],
    }


def hunt_materials(materials: list[dict], *, as_of: str | None = None, top_n: int = 5) -> dict:
    """Rank all leads, then actually run rewrite/fact/style gates on each selection.

    An unreviewed source excerpt remains a preview. No human/agent review,
    semantic novelty or underlying factual verification is manufactured here.
    Codex can use the returned contracts to write variants, then submit the
    completed source-reviewed candidate via prepare_candidate().
    """
    now = as_of or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rated = [auto_rate_material(m) for m in materials]
    ranking = rank_materials(rated, as_of=now, top_n=top_n, admission_mode=PREVIEW_MODE)
    drafts = []; held = []
    for mid in ranking["selected_material_ids"]:
        material = deepcopy(next(m for m in rated if m["material_id"] == mid))
        source = material.get("source", {})
        body = material.get("draft_text") or material["text"]
        # Preserve the complete provided excerpt and attribution. Rewriting a
        # long report or omitting its denial/context needs an editorial pass.
        draft = body.rstrip() + "\n\n来源原文：" + source["url"]
        facts = lock_draft_facts(draft)
        style = run_human_style_pipeline({"draft_text": draft, "locked_facts": facts,
                    "primary_action": material.get("primary_action", "SHARE"), "target_platform": "X_ZH",
                    "voice_profile": "GEN_DEFAULT", "preserve_quotes": True})
        entry = {"material_id": mid, "source_refs": [source["url"]], "before": draft,
                 "draft_text": style["rewritten_text"], "locked_facts": facts,
                 "primary_action": material.get("primary_action", "SHARE"),
                 "status": ("SOURCE_EXCERPT_NOT_AUTHORED" if not material.get("draft_text") else
                            "PASS_STYLE_PENDING_EDITORIAL" if style["passed"] else "NEEDS_EDITORIAL_REWRITE"),
                 "authoring_required": not bool(material.get("draft_text")),
                 "publication_allowed": False, "human_checked": False, "agent_checked": False,
                 "production_holds": ["SOURCE_FACTS_REQUIRE_REVIEW", "READER_MODEL_REQUIRES_REVIEW",
                                      "EXACT_DEDUP_IS_NOT_SEMANTIC_NOVELTY"],
                 "human_style_preview": style, "variants_prompt": generate_viral_variants_prompt(material)}
        (drafts if style["passed"] else held).append(entry)
    return {"engine": "CODEX_VIRAL_HUNT_V2", "as_of": now, "admission_mode": PREVIEW_MODE,
            "publication_allowed": False,
            "ranking": ranking, "drafts": drafts, "held_drafts": held,
            "next_step": "Codex核对原始证据、事实边界、语义新颖性和Reader Model后，逐版调用prepare_candidate；本命令不提交X。"}


def hunt(*, top_n=5, **discovery_options) -> dict:
    packet = auto_discover_materials(**discovery_options)
    result = hunt_materials(packet["materials"], as_of=packet["as_of"], top_n=top_n)
    return {**result, "collection": packet["collection"], "errors": packet["errors"], "search_queries": packet["search_queries"]}


def collector_health(packet: dict, *, now: str | None = None) -> dict:
    observed = datetime.fromisoformat((now or datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
    completed_raw = (packet.get("collection") or {}).get("latest_run_completed_at") or packet.get("as_of")
    reasons = []
    try:
        completed = datetime.fromisoformat(str(completed_raw).replace("Z", "+00:00"))
        age = max(0, (observed - completed).total_seconds() / 3600)
    except (TypeError, ValueError):
        age = None
    if age is None or age > 8: reasons.append("STALE")
    families = packet.get("source_families") or (packet.get("collection") or {}).get("source_families") or []
    if len(set(families)) < 3: reasons.append("LOW_SOURCE_DIVERSITY")
    collection = packet.get("collection") or {}
    if collection.get("under24h", 0) + collection.get("between24and48h", 0) < 10:
        reasons.append("INSUFFICIENT_FRESH_MATERIAL")
    return {"status": "HEALTHY" if not reasons else "DEGRADED", "reasons": reasons,
            "completion_age_hours": round(age, 3) if age is not None else None,
            "source_family_count": len(set(families)),
            "under48h": collection.get("under24h", 0) + collection.get("between24and48h", 0)}


def scheduled_collection(*, output_root: Path, rss_urls=None, telegram_channels=("DNYQWCG", "iizuk"),
                         limit: int = 100, as_of: str | None = None, fetcher=None) -> dict:
    """Write one collection packet. This function has no publication imports."""
    packet = auto_discover_materials(rss_urls=rss_urls, telegram_channels=telegram_channels,
                                     hacker_news=("top", "best", "new"),
                                     limit=limit, as_of=as_of, fetcher=fetcher)
    screened = [auto_rate_material(material) for material in packet["materials"]]
    ranking = rank_materials(screened, as_of=packet["as_of"], top_n=20, admission_mode=PREVIEW_MODE)
    output = {
        "schema_version": "VIRAL_FEED_PACKET_V3", "as_of": packet["as_of"],
        "collection": packet["collection"], "source_families": ranking["source_families"],
        "source_family_counts": ranking["source_family_counts"], "duplicates": ranking["duplicate_clusters"],
        "errors": packet["errors"], "materials": screened, "top20_preview": ranking["rows"][:20],
        "search_queries": packet["search_queries"], "admission_mode": PREVIEW_MODE,
        "automatic_x_submission": False, "publication_triggered": False,
    }
    output["collector_health"] = collector_health(output, now=packet["as_of"])
    stamp = datetime.fromisoformat(packet["as_of"].replace("Z", "+00:00"))
    dated = output_root / stamp.strftime("%Y-%m-%d") / (stamp.strftime("%H%M") + ".json")
    latest = output_root / "latest.json"; index_path = output_root / "index.json"
    dated.parent.mkdir(parents=True, exist_ok=True); output_root.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    dated.write_text(serialized, encoding="utf-8"); latest.write_text(serialized, encoding="utf-8")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        index = {"schema_version": "VIRAL_FEED_INDEX_V2", "runs": []}
    runs = index.setdefault("runs", [])
    runs.append({"as_of": output["as_of"], "path": str(dated), "materials": len(screened),
                 "source_families": output["source_families"], "health": output["collector_health"]["status"]})
    index["runs"] = runs[-100:]; index["latest"] = str(dated)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**output, "paths": {"packet": str(dated), "latest": str(latest), "index": str(index_path)}}


def aggregate_production_packets(packets: list[dict], *, as_of: str) -> dict:
    """Combine recent packets; only separately deep-reviewed rows can win."""
    cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00")); materials = []
    for packet in packets:
        for material in packet.get("materials", []):
            try: published = datetime.fromisoformat(str(material["source"]["published_at"]).replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError): continue
            if 0 <= (cutoff - published).total_seconds() <= 48 * 3600: materials.append(material)
    return rank_materials(materials, as_of=as_of, admission_mode=PRODUCTION_MODE)


def apply_deep_review_records(materials: list[dict], review_packet: dict) -> list[dict]:
    """Bind explicit Codex/human judgments to source material without scoring them."""
    from .viral_admission import WEIGHTS
    records = review_packet.get("records")
    if not isinstance(records, list): raise ValueError("deep review records must be an array")
    by_id = {m.get("material_id"): deepcopy(m) for m in materials}
    reviewer = review_packet.get("reviewer"); reviewed_at = review_packet.get("reviewed_at")
    dimensions = list(WEIGHTS)
    for record in records:
        material = by_id.get(record.get("material_id"))
        if material is None: raise ValueError("deep review material is not in feed packet")
        ratings, evidence, reasons = record.get("ratings"), record.get("evidence"), record.get("reasons")
        if not all(isinstance(value, list) and len(value) == len(dimensions) for value in (ratings, evidence, reasons)):
            raise ValueError("deep review needs eight ratings, evidence spans and reasons")
        review = {key: {"rating": ratings[index], "evidence": evidence[index], "reason": reasons[index]}
                  for index, key in enumerate(dimensions)}
        review.update(review_type=record.get("review_type", "DEEP_EDITORIAL_REVIEW"), reviewer=reviewer, reviewed_at=reviewed_at,
                      possible_reply_branches=record.get("possible_reply_branches", []), novelty="CHECKED_DISTINCT")
        if review_packet.get("strategy_version") == "V4" or "reader_value" in record:
            review.update(strategy_version="V4", reader_value=record.get("reader_value"))
        if "contrast_basis" in record: review["contrast_basis"] = record["contrast_basis"]
        if "decision" in record: review["decision"] = record["decision"]
        for key in ("audience_distance", "background_cost", "hook"):
            value = record.get(key)
            if not isinstance(value, dict): raise ValueError(f"{key} review required")
            review[key] = value
        material["review"] = review
    return list(by_id.values())


def production_dry_run(feed_packet: dict, review_packet: dict) -> dict:
    """Compete topics, then vet authored A/B/C text separately from scores.

    Old packets replay as historical style previews but cannot obtain a final
    recommendation without a source-bound text-first editorial decision.
    """
    materials = apply_deep_review_records(feed_packet.get("materials", []), review_packet)
    ranking = rank_materials(materials, as_of=feed_packet["as_of"], admission_mode=PRODUCTION_MODE)
    winner_id = ranking["selected_material_id"]
    previews = []; topics = []
    memory = review_packet.get("publication_memory")
    # A strong but stale/held story may still have authored alternatives worth
    # reviewing. Check them without moving it into the eligible winner tier.
    authored_ids = {r.get("material_id") for r in review_packet["records"] if r.get("previews")}
    for row in ranking["rows"]:
        if row not in ranking["top5"] and row["material_id"] not in authored_ids:
            continue
        mid = row["material_id"]
        record = next((r for r in review_packet["records"] if r.get("material_id") == mid), {})
        material = next(m for m in materials if m["material_id"] == mid)
        authored = record.get("previews", [])
        checked = []
        for variant in authored:
            text = variant.get("text", "")
            before = variant.get("original_text", text)
            style = run_human_style_pipeline({"draft_text": before,
                "authored_text": text if "original_text" in variant or variant.get("strategy_version") == "V4" else None,
                "locked_facts": variant.get("locked_facts", lock_draft_facts(before)),
                "primary_action": variant.get("primary_action", "SHARE"), "target_platform": "X_ZH",
                "voice_profile": "GEN_DEFAULT", "preserve_quotes": True})
            content = review_content({**variant, "text": style["rewritten_text"], "content_review": variant.get("content_review"),
                                      "opening_comparison_required": review_packet.get("opening_comparison_required", False) or variant.get("opening_comparison_required", False),
                                      "publication_memory": memory}, material)
            checked.append({**variant, "before": before, "after": style["rewritten_text"],
                            "authoring": style["authoring"], "fact_preservation_report": style["fact_preservation_report"],
                            "human_style_passed": style["passed"], "content_review_result": content,
                            "publication_allowed": False})
        if mid == winner_id: previews = checked
        diversity = review_variant_set(authored)
        preferred = next((v for v in checked if v.get("id") == record.get("recommended_variant")), None)
        # Sending text to a human editor is allowed below the production topic
        # threshold. Only the unchanged competition winner can become Top1.
        reviewable = bool(diversity["passed"] and preferred
                          and preferred["content_review_result"]["passed"] and preferred["human_style_passed"])
        topics.append({"material_id": mid, "topic": material.get("topic"), "source": material.get("source"),
                       "variants": checked, "variant_set_review": diversity,
                       "recommended_variant": record.get("recommended_variant") if reviewable else None,
                       "editorial_recommendation": "REVIEWABLE_DRAFT" if reviewable else "HOLD",
                       "topic_admitted": row["admitted"],
                       "production_preflight_passed": False})
    final = next((t for t in topics if t["material_id"] == winner_id
                  and t["editorial_recommendation"] == "REVIEWABLE_DRAFT"), None)
    closure = _prepare_production_winner(materials, review_packet, ranking, final)
    if final:
        final["production_preflight_passed"] = closure["prepublish"]["passed"]
    return {"version": "VIRAL_HUNT_PRODUCTION_DRY_RUN_V2", "as_of": feed_packet["as_of"],
            "ranking": ranking, "top1_previews": previews, "publication_allowed": False,
            "topics": topics, "recommended_top1": final["material_id"] if final else None,
            "final_status": ("READY_CANDIDATE_DRY_RUN" if closure["prepublish"]["passed"] else
                             "EDITORIAL_REVIEW_DRAFTS" if final else "NO_ACCEPTED_TOP1_CONTINUE_HUNTING"),
            "production_pipeline": closure,
            "automatic_x_submission": False}


def _prepare_production_winner(materials: list[dict], reviews: dict, ranking: dict, winner: dict | None) -> dict:
    """Join existing gates using an explicit editor packet, never invented reviews.

    A checked preview alone is not a production candidate. Identity, source,
    pool and exact prose come from this competition; reader/agent judgments
    must be supplied by the editor. PAUSED remains independent of dry-run PASS.
    """
    from .candidate_pipeline import prepare_candidate
    from .publication_preflight import pre_publish_assert
    from .publication_control import publication_control
    from .reader_model import METRICS, text_hash, window_measurement
    from .viral_admission import material_hash

    control = publication_control()
    result = {"candidate": None, "prepublish": {"passed": False, "reasons": []},
              "publication_control": {"status": control.get("status"), "reason": control.get("reason")},
              "publication_allowed": False, "feedback_24h": None}
    packet = reviews.get("production_candidate")
    reasons = result["prepublish"]["reasons"]
    if not isinstance(packet, dict):
        reasons.append("PRODUCTION_CANDIDATE_REVIEW_REQUIRED")
        return result
    if (not winner or packet.get("material_id") != ranking["selected_material_id"]
            or packet.get("variant_id") != winner["recommended_variant"]):
        reasons.append("PRODUCTION_CANDIDATE_MUST_MATCH_REVIEWED_TOP1_VARIANT")
        return result
    variant = next(v for v in winner["variants"] if v["id"] == packet["variant_id"])
    text = variant["after"]
    if "text" in packet and packet["text"] != text:
        reasons.append("PRODUCTION_CANDIDATE_TEXT_CHANGED")
        return result
    pool = deepcopy(materials)
    material = next(m for m in pool if m["material_id"] == packet["material_id"])
    material["draft_text"] = text
    candidate = {**deepcopy(packet), "text": text, "authored_text": text,
                 "locked_facts": variant.get("locked_facts", lock_draft_facts(text)),
                 "primary_action": variant.get("primary_action", "SHARE"),
                 "source_refs": [material["source"]["url"]], "material_pool": pool,
                 "material_hash": material_hash(material), "admission_mode": PRODUCTION_MODE,
                 "competition_as_of": ranking["as_of"], "publication_memory": reviews.get("publication_memory"),
                 "content_review": variant.get("content_review"), "strategy_version": variant.get("strategy_version"),
                 "opening_comparison_required": reviews.get("opening_comparison_required", False) or variant.get("opening_comparison_required", False),
                 "state": "DRAFT", "publication_mode": "DRY_RUN_ONLY"}
    prepared = prepare_candidate(candidate)
    result["candidate"] = prepared
    reasons.extend(prepared["editorial_gate"]["reasons"])
    if not prepared["editorial_gate"]["ready"] and not reasons:
        reasons.append("EDITORIAL_GATE_NOT_READY: inspect Human Style and source review reports")
    if prepared["editorial_gate"]["ready"]:
        try:
            result["prepublish"] = pre_publish_assert(prepared, prepared["text"], dry_run=True)
        except ValueError as exc:
            reasons.append(str(exc))
    # Unpublished drafts have neither a post URL nor a publication timestamp.
    # Existing feedback machinery keeps missing values null, displayed UNKNOWN.
    result["feedback_24h"] = {
        "candidate_id": prepared.get("candidate_id"), "status": "AWAITING_PUBLICATION",
        "publication_text_digest": text_hash(prepared["text"]),
        "primary_action": prepared.get("primary_action"), "topic": prepared.get("topic"),
        "preregistered_at_utc": reviews.get("reviewed_at"),
        "window": "24h", "post_url": None, "published_at_utc": None, "observed_at_utc": None,
        "evidence_ref": None, "human_reviewed": False, "metrics_status": "UNKNOWN",
        **{key: None for key in METRICS}, **window_measurement(None, None, "24h"),
        "learning_eligible": False,
    }
    return result


def render_editorial_drafts(result: dict) -> str:
    """Readable artifact from the actual checked output, including rejected text."""
    lines = ["# 实际素材与原创稿（未发布）", "", "竞争时点：" + result["as_of"], "",
             "编辑判断不等于用户认可或真实流量。所有稿件仍需人工发布审核。", ""]
    closure = result.get("production_pipeline") or {}
    candidate = closure.get("candidate")
    if candidate:
        lines += ["## 正式候选审核结果", "", "状态：" + result["final_status"], "",
                  "Reader Model：" + str(candidate.get("reader_model_integrity", {}).get("passed")),
                  "Editorial Gate：" + str(candidate["editorial_gate"]["ready"]),
                  "Prepublish dry-run：" + str(closure["prepublish"]["passed"]),
                  "发布控制：" + str(closure["publication_control"]["status"]) + "；未授权提交X。", "",
                  "候选全文：", "", candidate["text"], "",
                  "未通过原因：" + "; ".join(closure["prepublish"].get("reasons", []) or ["技术审核无剩余失败；dry-run不授予发布权限"]), ""]
    for index, topic in enumerate(result["topics"], 1):
        source = topic["source"]
        lines += [f"## {index}. {topic['topic']}", "", source["url"], "",
                  "事件时间状态：" + str(source.get("event_time_status", "UNKNOWN")), "",
                  "编辑建议：" + topic["editorial_recommendation"] + "；推荐版本：" + str(topic["recommended_variant"]), ""]
        for v in topic["variants"]:
            reasons = list(v["content_review_result"]["reasons"])
            if not v["human_style_passed"]:
                reasons.append("风格或事实保留检查未通过；不能进入发布审核")
            lines += ["### " + str(v.get("id")) + " / " + str(v.get("mode", "UNKNOWN")), ""]
            if "original_text" in v:
                lines += ["原稿：", "", v["before"], "", "Codex改写后的实际检查正文：", ""]
            lines += [v["after"], "",
                      "编辑依据：" + str((v.get("content_review") or {}).get("payoff", {}).get("reason", "未审")), "",
                      "淘汰/保留问题：" + "; ".join(reasons or ["编辑通过；实际传播效果UNKNOWN"]), ""]
    return "\n".join(lines)
