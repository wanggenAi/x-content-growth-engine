# Latest control — 2026-10-20 lightweight content competitiveness V4

Latest direct user request authorizes research, code, tests, real editorial dry-run, PR and merge after CI. **No X publication**; existing `state/publication_control.json` stays PAUSED. New explicit publication authorization is required. Collector cadence and scheduler unchanged; automatic_x_submission=false.

V4 extends existing Human Style/source/content-review interfaces; HUMAN_STYLE_V2 contract remains compatible. Ten actual topics and fifteen drafts are editorial examples, not traffic validation or a production-admitted pool. Existing strict production competition and exact prepublish controls remain. Current comparable traffic/engagement/follows UNKNOWN; C390 user rejection retained.

PR [#16](https://github.com/wanggenAi/x-content-growth-engine/pull/16) merged as `79b92cac3e7af22a3eecff937bbe905e39d76c6a`; [merged-main CI](https://github.com/wanggenAi/x-content-growth-engine/actions/runs/39359006847) passed, as did local 137 unittest/137 pytest/compileall. Follow-up changes only record verification.

See [V4 evidence and drafts](CONTENT_COMPETITIVENESS_V4_2026-10-20.md). Older controls below are historical.

# 2026-10-19 — merged code; drafts awaiting human review

PR #14 merged as c63d905. Main tests and fresh collector passed. Source-bound text review is mandatory for new READY admission. Top3 have nine reviewable drafts; actual growth remains UNKNOWN. X submission remains PAUSED under the current user instruction. Reproducible artifacts: `data/content_quality_2026-10-19/`; main replay/CI receipt: `main_verification.json`. This is a code-repair milestone, not a claim of proven reader appeal.

# 2026-10-19 — content quality repair; dry-run only

Latest direct instruction: repair, test, create PR and merge main; research and authored dry runs only. No new X submission is authorized in this round. `content_review` is now required before a new READY admission and final prepublish validation. Style/keyword scores are surface checks, never content success. Full source/time/text/memory binding and a separate text-first editorial comparison are required. Older control snapshots below are historical.

# 2026-10-17 — Codex active hunting and rewrite

Latest direct user request adopts `claude_x_upgrade_prompts.md`, with **Codex** as executor. Current mode is `ACTIVE_VIRAL_HUNTING_AND_REWRITE`; the previous topic-repair pause and ten-material/five-point-margin admission policy are superseded. Existing historical posts, review records and DRY_RUN_ONLY candidates are not silently migrated or republished.

Codex may proactively search public web results, read permitted public RSS/Atom and Telegram previews, use free built-in discovery scripts, and prepare source-attributed drafts. Search results are usable discovery evidence with method and capture time; they are not direct-X observations or independent factual corroboration. Supported modes: high-interest source refinement with attribution; multi-source lead checking; an outside-platform perspective on a documented domestic event. No whole-article copying, fabricated first-person experience, invented metrics or unsubstantiated censorship claims.

Missing ratings can receive labelled structural estimates. `VIRAL_ADMISSION_V2` uses MIN_POOL=1, topic>=62 and default Top5; margin is informational. Human Style, fact locks, semantic binding, source-fact review, provenance and exact prepublish checks remain. Claims of deletion/restriction require specific supporting evidence; this is not a universal requirement for ordinary social/human-interest topics.

The `hunt` command never submits X. ACTIVE permits research, rewrite and qualified manual publication through existing controls, not an unattended publisher. Existing scheduler settings are not changed by this engineering round. Reddit remains unavailable without verified authorization/use-rights evidence. Ordinary public HTTP requires no session, cookies, paid service or new subscription. Manual X capture remains compatible and its genuine human-check field is not auto-filled.

Older dated control snapshots below are historical.

# Latest control — 2026-10-17 strict Viral Hunt production competition

`VIRAL_ADMISSION_V3` separates preview auto screening from production editorial scoring. Preview can show Top5 from one item; production requires >=10 distinct events plus raw30/deep-reviewed20/under48h10/source-families4, and only unique Top1 can continue. Missing ratings are not filled for production. Repeated evidence/reason invalidates deep review.

The scheduled GitHub Actions collector runs every four hours and only collects/deduplicates/screens public leads. It cannot submit X and `state/publication_control.json` keeps `automatic_x_submission=false`. Latest on-demand run: `2026-10-17T12:56:38.143594Z`, 83 materials, 65 under48h, four source families. No new X submission occurred.

See `docs/CODEX_VIRAL_HUNT.md` and `data/viral_hunt_validation_2026-10-17.json`. Older control sections below are historical.

# Historical control — 2026-10-16 topic admission repair

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
