# Latest control — 2026-10-16 topic admission repair

`PAUSED_FOR_TOPIC_ADMISSION_REVIEW` overrides the older continued-publishing authorizations below for this repair. User explicitly requested no new X submission and review of Top10/Top5/Top1 first. Repository stop switch: `state/publication_control.json` (PAUSED); heartbeat x was already PAUSED and was not resumed. Only dry-run preparation is allowed. See `docs/TOPIC_ADMISSION_REPAIR_2026-10-16.md` and `docs/TOPIC_ADMISSION.md`.

# Current Control State

Updated: 2026-10-11 (Asia/Shanghai)

This file is the canonical current-state entry point for ongoing automation and future agents. When historical notes elsewhere conflict with this file, use this file as the control-state authority and treat older README / `TASK_STATE.md` checkpoints as historical evidence unless a newer dated control-state update explicitly supersedes it.

## Repository authority

- Canonical working branch: `main`.
- PR #5 (`feature/x-research-phase2`) was squash-merged into `main` on 2026-10-11.
- Merge commit: `4184a4299550a1a8226a62cf939feeadf6819562`.
- The push-triggered `tests` workflow for that merge completed successfully.
- New research-data and analysis tasks write against `main`.

## Primary objective

Optimize long-term natural reach, meaningful interaction and follower growth for the user's Chinese X account through evidence-backed topic selection, strong original writing and explicit learning from outcomes.

Publication count, queue length and the historical 1000-post target are inventory/audit fields only. They are not success metrics and must not force weak publication.

## Cost policy

Current data/research operation is `FREE_ONLY`.

- Do not depend on Metricool for viral discovery or analytics.
- Do not depend on X's paid API.
- Do not depend on paid social-listening, scraping, analytics or data-reseller services.
- If a source requires payment, subscription, credit purchase or recharge, skip it and continue with free public routes.
- Current production discovery uses public aggregators/mirrors, public search, real X status permalinks, Snowflake timestamp derivation from numeric status IDs, and multi-source corroboration where original X rendering is unavailable.

## Publication control

Current state: `PUBLICATION_ACTIVE_WITH_QUALITY_GATES`.

- `PUBLICATION_PAUSED_FOR_LEARNING` is historical state from 2026-10-06 and is no longer the global control state.
- The user's 2026-10-09 instruction restored continued ordinary public-post publication for qualified content.
- Missing feedback does not by itself block a new qualified post.
- Source checking, duplication checks, content-quality gates, visible-editor verification and independent public-detail verification remain required.
- Do not fabricate metrics, comments, reach or reader reactions.
- No bulk manufactured engagement, hidden endpoint use, cookie extraction or access-control bypass is authorized.
- Historical hypotheses such as F01-F05 and reader-model mechanisms remain hypotheses unless the actual evidence standard is met.

## Viral research data pipeline

Collection and analysis are separate jobs. The durable contract is [VIRAL_FEED_CONTRACT.md](VIRAL_FEED_CONTRACT.md).

### 1. Viral feed collection

A scheduled task runs approximately every four hours and produces public-discovery observations under:

- `data/viral_feed/YYYY-MM-DD/HHMM.json`
- `data/viral_feed/latest.json`
- `data/viral_feed/index.json`

The machine-readable schema is `data/viral_feed/schema.json`.

Priority is recent material, normally within 48 hours. Older items may enter only as `EVERGREEN_REDISCOVERY` when they have durable novelty and verifiable evidence. A zero-yield run should record its queries/failures rather than recycle stale samples.

The collector only discovers, normalizes, deduplicates and freshness-labels evidence. It does not generate posts, publish posts or promote a viral formula.

The current free discovery routes include:

- `PUBLIC_X_AGGREGATOR` — free public pages/mirrors that expose current X status IDs/permalinks, excerpts or labeled engagement;
- `AUTHOR_WATCH` — free public search against a rotating author pool;
- `TOPIC_WATCH` — free public topic/date searches;
- `EVENT_TWO_HOP` — current public event discovery followed by free lookup of real X status permalinks.

Registered public corroboration sources and their limitations are maintained in `data/public_x_discovery_sources.json`.

### 2. Viral structure analysis

A separate daily task consumes the feed and writes:

- `data/viral_analysis/YYYY-MM-DD.json`
- `data/viral_analysis/latest.json`
- `docs/VIRAL_PATTERN_LATEST.md`

The machine-readable schema is `data/viral_analysis/schema.json`.

The analyzer compares high-distribution samples with available ordinary/low-distribution controls and tracks hooks, information gaps, reversal, specificity, self-relevance, psychological stakes, opinion space, forwarding target, structure, media form, freshness and topic.

Patterns remain `HYPOTHESIS` unless supported across batches with meaningful controls and later evidence.

## Evidence discipline

- Prefer recent material; keep old material only when it has durable rediscovery value and is explicitly labeled.
- Preserve post URL/status id, author, post time, observation time, discovery route, visible metrics and metric provenance when available.
- Unknown values stay `null`/`UNKNOWN`.
- A real numeric X status ID may be used to derive `published_at` via the X/Twitter Snowflake epoch, but this must be labeled as derived rather than original-page observation.
- Public aggregator/mirror evidence must keep its source and evidence level; it is never silently treated as direct original-X rendering.
- Deduplicate by status id and mark near-duplicate text/events.
- Never label stale search-index snapshots as current metrics.
- Do not claim a stable viral formula from small, age-mismatched or selection-biased samples.

## Relationship to own-account learning

External viral observations teach candidate mechanisms; they do not prove the user's account will reproduce those outcomes. Own-account fixed-window feedback is the stronger validation layer when reliably observed. Missing historical windows remain missing and are not backfilled with current cumulative metrics.

## Immediate operating order

1. Keep free fresh viral-feed ingestion running.
2. Build daily high-vs-control structural analysis from that feed.
3. Use the newest strong material plus current pattern hypotheses to select and write candidates.
4. Publish only qualified, distinct candidates; never publish merely to satisfy volume.
5. Capture trustworthy own-account feedback where available and use it to reject or refine hypotheses.
6. Prefer evidence and negative examples over adding more untested writing theories.
