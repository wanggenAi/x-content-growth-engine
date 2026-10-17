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
                 "status": "PASS_STYLE_PENDING_EDITORIAL" if style["passed"] else "NEEDS_EDITORIAL_REWRITE",
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
        review.update(review_type="DEEP_EDITORIAL_REVIEW", reviewer=reviewer, reviewed_at=reviewed_at,
                      possible_reply_branches=record.get("possible_reply_branches", []), novelty="CHECKED_DISTINCT")
        for key in ("audience_distance", "background_cost", "hook"):
            value = record.get(key)
            if not isinstance(value, dict): raise ValueError(f"{key} review required")
            review[key] = value
        material["review"] = review
    return list(by_id.values())


def production_dry_run(feed_packet: dict, review_packet: dict) -> dict:
    """Run the strict competition and preview three authored Top1 variants."""
    materials = apply_deep_review_records(feed_packet.get("materials", []), review_packet)
    ranking = rank_materials(materials, as_of=feed_packet["as_of"], admission_mode=PRODUCTION_MODE)
    winner_id = ranking["selected_material_id"]
    previews = []
    if winner_id:
        record = next((r for r in review_packet["records"] if r.get("material_id") == winner_id), {})
        winner = next(m for m in materials if m["material_id"] == winner_id)
        for variant in record.get("previews", []):
            text = variant.get("text", "")
            style = run_human_style_pipeline({"draft_text": text, "locked_facts": lock_draft_facts(text),
                "primary_action": variant.get("primary_action", "SHARE"), "target_platform": "X_ZH",
                "voice_profile": "GEN_DEFAULT", "preserve_quotes": True})
            previews.append({"id": variant.get("id"), "before": text, "after": style["rewritten_text"],
                             "human_style_passed": style["passed"], "publication_allowed": False})
    return {"version": "VIRAL_HUNT_PRODUCTION_DRY_RUN_V1", "as_of": feed_packet["as_of"],
            "ranking": ranking, "top1_previews": previews, "publication_allowed": False,
            "automatic_x_submission": False}
