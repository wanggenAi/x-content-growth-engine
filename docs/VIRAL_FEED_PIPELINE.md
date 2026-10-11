# Viral Feed Pipeline Contract

Updated: 2026-10-11

This contract defines the scheduled discovery layer feeding the X content-growth research system. It is a data-production contract, not a virality formula and not a publishing workflow.

## 1. Collection cadence and scope

- Nominal cadence: every ~4 hours.
- Default freshness window: posts from the last 48 hours.
- Primary topics: AI, technology, digital products, internet discoveries, ordinary-person experiences, social observation, cognitive reversal, unusual facts, culture and history.
- Old posts may enter only as `EVERGREEN_REDISCOVERY` when the material remains surprising/useful, is source-verifiable and is not presented as current news.

## 2. Required run metadata

Each collection run should record at minimum:

- `run_id`
- `collected_at_utc`
- `queries_attempted`
- `candidate_count`
- `admitted_count`
- `failure_count`
- `failure_reasons`
- `source_routes`

A low-yield or zero-yield run is still a valid run and must be recorded rather than backfilled with stale samples.

## 3. Post observation fields

Each admitted observation should preserve where available:

- `url`
- `status_id`
- `author_handle`
- `posted_at`
- `observed_at`
- `topic`
- `language`
- `excerpt`
- `views`
- `likes`
- `reposts`
- `replies`
- `metric_source`
- `metric_as_of`
- `post_type`
- `promotion_status`
- `discovery_query`
- `evidence_note`
- `freshness_class`
- `near_duplicate_group`

Missing metrics remain `null`; search snippets and stale snapshots must not be upgraded to live metrics.

## 4. Admission preference

For recent posts, prefer candidates with visible views >= 10,000 or clearly abnormal interaction relative to comparable material. This is a discovery preference, not a definition of quality and not a causal label.

Do not reject potentially useful candidates solely because one metric is unavailable, but keep the uncertainty explicit.

## 5. Deduplication

- Primary identity: X status id.
- Exact duplicates are merged/ignored according to evidence provenance.
- Highly similar text or multiple posts about the same event should be marked with `near_duplicate_group` so later analysis does not count the same event repeatedly.

## 6. Storage

- Immutable run packet: `data/viral_feed/YYYY-MM-DD/HHMM.json`
- Latest pointer/materialized latest packet: `data/viral_feed/latest.json`
- Feed index and run history: `data/viral_feed/index.json`

## 7. Analysis separation

The collector does not generate posts and does not promote formulas.

The daily analysis stage reads accumulated feed data and produces:

- `data/viral_analysis/YYYY-MM-DD.json`
- `data/viral_analysis/latest.json`
- `docs/VIRAL_PATTERN_LATEST.md`

Analysis should compare high-propagation material with ordinary/low-propagation controls where possible, track counterexamples, and explicitly note author/topic/time/age confounding.

## 8. Safety and access boundaries

Do not extract cookies, call hidden endpoints, bypass access controls, solve CAPTCHAs, or use unapproved bulk scraping mechanisms. Use publicly accessible discovery/search surfaces and ordinary accessible pages only. Preserve failures instead of bypassing restrictions.
