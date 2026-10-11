"""Rebuild derived annotations from immutable public records and explicit reviews.

Run from repository root: python3 scripts/build_reader_recode.py
This script performs no semantic inference or metric-based labeling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from growth_engine.reader_model import empty_profile, text_hash, validate_annotation

REVIEW_FILE = Path("data/reader_model_reviews_2026-10-08.json")
OUTPUT = Path("data/reader_model_annotations_2026-10-08.json")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build():
    reviews = read(REVIEW_FILE)
    by_key = {(r["entity_kind"], r["entity_id"]): r for r in reviews["reviews"]}
    if len(by_key) != len(reviews["reviews"]):
        raise ValueError("duplicate explicit review")
    inventory = {}
    external_files = [Path("data/viral_samples_2026-10-01.json"),
                      Path("data/viral_validation_stage2_2026-10-01.json"),
                      Path("data/public_figure_contrast_research_2026-10-01.json"),
                      *sorted(Path("data").glob("high_view_structure_round*.json"))]
    for path in external_files:
        data = read(path)
        rows = data.get("posts", data.get("samples", data.get("observations", data.get("rows", data.get("records", []))))) + data.get("comparisons", [])
        for index, row in enumerate(rows):
            entity_id = row["url"].rstrip("/").split("/")[-1]
            key = ("external", entity_id)
            ref = {"file": str(path), "record_id": row.get("id"), "url": row["url"],
                   "record_digest": text_hash(json.dumps(row, sort_keys=True, ensure_ascii=False)),
                   "observation_source": row.get("source_kind", row.get("observation_source")),
                   "observed_at_utc": row.get("observed_at"), "metric_as_of": row.get("metric_as_of"),
                   "evidence_saved_at_utc": row.get("evidence_saved_at_utc"),
                   "human_checked": row.get("human_checked", False),
                   "agent_checked": row.get("agent_checked", row.get("detail_post_body_confirmed_by_agent")),
                   "private_evidence_ref": row.get("private_evidence_dir", row.get("private_evidence")),
                   "threshold_above_10000": row.get("above_10000", row.get("above_10000_display", row.get("threshold_passed",
                                                row["views"] > 10000 if type(row.get("views")) is int else None)))}
            if key not in inventory:
                inventory[key] = {"post_url": row["url"], "source_refs": [], "aliases": [],
                                  "basis_text": row.get("summary", row.get("structure_summary", row.get("editorial_summary"))),
                                  "source_limits": row.get("boundaries", row.get("limits", row.get("interpretation_and_limits")))}
            inventory[key]["source_refs"].append(ref)
            inventory[key]["aliases"].append(row.get("id", entity_id))
    campaign = Path("data/publication_campaign_200_2026-10-01.json")
    for row in read(campaign)["posts"]:
        if row.get("status") != "PUBLISHED_AGENT_VERIFIED":
            continue
        inventory[("own", row["id"])] = {
            "post_url": row["url"], "aliases": [row["id"]],
            "publication_version": row.get("publication_version"),
            "publication_text_digest": text_hash(row.get("text", "")),
            "published_at_utc": row.get("published_at"),
            "basis_text": row.get("first_screen_conflict", row.get("text", "").split("\n")[0]),
            "source_refs": [{"file": str(campaign), "record_id": row["id"], "url": row["url"],
                             "record_digest": text_hash(json.dumps(row, sort_keys=True, ensure_ascii=False)),
                             "verification_source": row.get("verification_source"),
                             "verified_at_utc": row.get("verified_at"),
                             "human_checked": row.get("human_checked", False),
                             "agent_checked": row.get("agent_checked"),
                             "private_evidence_ref": row.get("private_evidence_dir")}],
        }
    # The 25 pre-campaign originals use overlapping P/H/etc IDs. Namespace by status ID.
    own_urls = {r["post_url"] for (kind, _), r in inventory.items() if kind == "own"}
    for path in sorted(Path("data").glob("publication*.json")):
        if path == campaign:
            continue
        for row in read(path).get("posts", []):
            url = row.get("url", row.get("published_url"))
            if row.get("status") != "PUBLISHED_AGENT_VERIFIED" or not url or url in own_urls:
                continue
            own_urls.add(url)
            entity_id = "BASELINE-" + url.rstrip("/").split("/")[-1]
            body = row.get("text") or ""
            inventory[("own", entity_id)] = {
                "post_url": url, "aliases": [row.get("id", entity_id)],
                "publication_version": row.get("publication_version"), "publication_text_digest": text_hash(body),
                "published_at_utc": row.get("published_minute_utc", row.get("published_at")),
                "basis_text": body.split("\n")[0],
                "source_refs": [{"file": str(path), "record_id": row.get("id"), "url": url,
                    "record_digest": text_hash(json.dumps(row, sort_keys=True, ensure_ascii=False)),
                    "verified_at_utc": row.get("verified_at", row.get("verification_at")),
                    "human_checked": row.get("human_checked", False)}]}
    result = []
    consumed = set()
    for key, source in inventory.items():
        review = by_key.get(key)
        if not review:
            # External reviews may use existing aliases; entity IDs are always canonical status IDs.
            review = next((by_key[(key[0], alias)] for alias in source["aliases"] if (key[0], alias) in by_key), None)
        profile = empty_profile()
        if review:
            consumed.add((review["entity_kind"], review["entity_id"]))
            profile.update(review["reader_model"])
        record = {"entity_kind": key[0], "entity_id": key[1], "version": reviews.get("annotation_version", 1),
                  "annotated_at_utc": reviews["annotated_at_utc"], "annotator": "CODEX_EDITORIAL_REVIEW",
                  "human_reviewed": False, "annotation_state": "ANNOTATED" if review else "NEEDS_REVIEW",
                  "annotation_note": ("Retrospective, unblinded editorial hypothesis; evidence coverage is explicit."
                                      if review else "Inventory linked; psychological fields intentionally unknown until review."),
                  "reader_model": profile, **source}
        record["source_digest"] = text_hash(json.dumps(source["source_refs"], sort_keys=True, ensure_ascii=False))
        validate_annotation(record)
        result.append(record)
    if consumed != set(by_key):
        raise ValueError(f"unresolved review IDs: {set(by_key) - consumed}")
    return sorted(result, key=lambda r: (r["entity_kind"], r["entity_id"]))


if __name__ == "__main__":
    rows = build()
    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), "annotated": sum(r["annotation_state"] == "ANNOTATED" for r in rows),
                      "external": sum(r["entity_kind"] == "external" for r in rows),
                      "own": sum(r["entity_kind"] == "own" for r in rows)}))
