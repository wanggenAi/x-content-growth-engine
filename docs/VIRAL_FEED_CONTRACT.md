# Viral Feed / Analysis Contract

Updated: 2026-10-11

This document defines the durable handoff between scheduled public discovery, structural analysis and later editorial work.

## 1. Collector output

The collector writes one immutable run packet to:

`data/viral_feed/YYYY-MM-DD/HHMM.json`

It also refreshes:

- `data/viral_feed/latest.json`
- `data/viral_feed/index.json`

A run packet must contain run metadata even when zero usable posts are found.

Required run-level fields:

- `schema_version`
- `run_id`
- `started_at`
- `completed_at`
- `discovery_window_hours`
- `query_count`
- `candidate_count`
- `admitted_count`
- `failure_count`
- `queries`
- `failures`
- `posts`

Each admitted post should preserve, where publicly observable:

- `url`
- `status_id`
- `author_handle`
- `published_at`
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
- `discovery_route`
- `source_url`
- `evidence_note`
- `freshness_class`
- `near_duplicate_group`

Allowed `discovery_route` values:

- `AUTHOR_WATCH` — rotate historically useful public author leads from `data/discovery_author_pool.json`; historical metrics are discovery seeds only and never carry forward to a new post.
- `TOPIC_WATCH` — rotate current-interest topic searches.
- `EVENT_TWO_HOP` — identify a current entity/event from public news/Hacker News/Reddit-index/GitHub sources, then search public indexes for a corresponding real `x.com/.../status` URL. The upstream event source is discovery context, not X-post reach evidence.

Unknown values remain JSON `null`. Do not infer a numeric metric from prose such as “viral” or “many views”.

Allowed `freshness_class` values:

- `RECENT_0_24H`
- `RECENT_24_48H`
- `RECENT_2_7D`
- `EVERGREEN_REDISCOVERY`
- `STALE_REFERENCE_ONLY`

`STALE_REFERENCE_ONLY` items may be preserved for audit but must not be counted as current-trend evidence.

The collector does not generate drafts, publish posts or promote a writing mechanism.

## 2. Discovery discipline

The collector should not depend on one generic search route. Each normal run should attempt a bounded mix of author-watch, topic-watch and event-to-X two-hop discovery. If one route is blocked or produces no usable status URLs, preserve that failure and rotate the next run rather than silently substituting old observations.

A specific X permalink may be admitted only to the evidence level actually supported by public observation. If the URL is real but current metrics cannot be seen, keep those metrics `null`. If publication time cannot be established, do not classify the item as a fresh 0–48h sample.

## 3. Index behavior

`data/viral_feed/index.json` is a compact registry rather than a second copy of all post bodies. It should track at least:

- latest run path and timestamp;
- total run count;
- recent admitted post count;
- unique status-id count;
- latest successful non-zero run;
- consecutive zero-yield/blocked runs;
- known duplicate / near-duplicate totals.

The index must not turn missing metrics into zero.

## 4. Analyzer input and output

The analyzer consumes the most recent available feed packets, normally at least seven days when enough history exists.

It writes:

- `data/viral_analysis/YYYY-MM-DD.json`
- `data/viral_analysis/latest.json`
- `docs/VIRAL_PATTERN_LATEST.md`

Required analysis-level fields include:

- `schema_version`
- `analysis_as_of`
- `input_run_ids`
- `sample_counts`
- `cohort_definitions`
- `structure_labels`
- `candidate_patterns`
- `counterexamples`
- `confounders`
- `recent_changes`
- `next_sampling_priorities`
- `evidence_grade`

Candidate patterns must carry an evidence state such as:

- `OBSERVATION`
- `HYPOTHESIS`
- `REPLICATED_HYPOTHESIS`
- `SUPPORTED_ON_HOLDOUT`
- `SUPPORTED_ON_OWN_ACCOUNT`

No pattern may jump directly from a small convenience sample to a “viral formula”.

## 5. Comparison discipline

Prefer comparisons that reduce obvious confounding:

- same or similar author scale when available;
- similar topic;
- similar post age;
- similar publication window;
- original vs original rather than reply vs original;
- promotion/paid-partnership status separated;
- quoted/reposted material separated when it changes the exposure mechanism.

When matching is not possible, the analysis must retain the limitation instead of treating raw view differences as causal evidence.

## 6. Editorial consumption

Editorial work may use the newest analysis as a hypothesis source, but must still independently check:

- material strength;
- source quality;
- novelty against recent own-account posts;
- reader value;
- self-relevance / psychological stake where relevant;
- a single primary reader action;
- factual and safety boundaries.

External viral observations are not proof that the same mechanism will work on the user's account.

## 7. Failure semantics

A blocked or zero-yield collector run is valid data when it records the reason. Do not recycle old posts merely to keep admitted-count positive.

If public discovery access degrades for several consecutive runs, preserve route-level failures in `index.json`, expand the next run's route rotation, and surface the problem instead of silently substituting stale snapshots.
