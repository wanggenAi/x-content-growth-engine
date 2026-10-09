"""Reproduce the first retrospective check using existing ignored account evidence.

Requires local evidence; a fresh public clone cannot reconstruct account analytics.
Run from repository root: python3 scripts/backtest_reader_history.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from growth_engine.reader_model import METRICS, backtest

SOURCE = Path("data/private/content_review_2026-10-04/observations.json")
DESTINATION = Path("data/private/self_mirroring_2026-10-08")


def main():
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    campaign = json.loads(Path("data/publication_campaign_200_2026-10-01.json").read_text())
    posts = {r["url"]: r for r in campaign["posts"] if r.get("url")}
    normalized = {}
    for observation in original["recent_observations"] + original["rechecked_higher_read_posts"]:
        post = posts[observation["url"]]
        record = {key: observation.get(key) for key in METRICS}
        record.update(entity_id=post["id"], post_url=observation["url"],
                      published_at_utc=post.get("published_at"),
                      observed_at_utc=observation.get("exact_observed_at_utc"),
                      evidence_saved_at_utc=observation.get("saved_at_utc"),
                      evidence_ref=observation["evidence_ref"], source_record_file=str(SOURCE),
                      source_kind=original["source_kind"], human_reviewed=False, agent_checked=True, window=None,
                      missing_reason="Capture timestamp unknown; save time is not metric time. Nonvisible metrics null; no retroactive fixed-window assignment.")
        # Independent detail replaces profile snapshot of the same URL, never counts twice.
        normalized[post["id"]] = record
    annotations = json.loads(Path("data/reader_model_annotations_2026-10-08.json").read_text())
    DESTINATION.mkdir(parents=True, exist_ok=True)
    observations = list(normalized.values())
    outputs = {"historical_feedback.json": observations,
               "backtest_exploratory.json": backtest(annotations, observations),
               "backtest_24h.json": backtest(annotations, observations, window="24h")}
    for name, content in outputs.items():
        (DESTINATION / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"distinct_posts": len(observations), "fixed_24h_eligible": outputs["backtest_24h.json"]["n"],
                      "raw_outputs": str(DESTINATION)}))


if __name__ == "__main__":
    main()
