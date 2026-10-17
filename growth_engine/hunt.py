"""Codex's free public-material hunting and checked draft-preview workflow."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re

from .discovery import auto_discover_materials
from .human_voice import generate_viral_variants_prompt, run_human_style_pipeline
from .viral_admission import auto_rate_material, rank_materials
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
    ranking = rank_materials(rated, as_of=now, top_n=top_n)
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
    return {"engine": "CODEX_VIRAL_HUNT_V1", "as_of": now, "publication_allowed": False,
            "ranking": ranking, "drafts": drafts, "held_drafts": held,
            "next_step": "Codex核对原始证据、事实边界、语义新颖性和Reader Model后，逐版调用prepare_candidate；本命令不提交X。"}


def hunt(*, top_n=5, **discovery_options) -> dict:
    packet = auto_discover_materials(**discovery_options)
    result = hunt_materials(packet["materials"], as_of=packet["as_of"], top_n=top_n)
    return {**result, "collection": packet["collection"], "errors": packet["errors"], "search_queries": packet["search_queries"]}
