# Viral Feed / Analysis Contract

Updated: 2026-10-11

This document defines the durable handoff between scheduled public discovery, structural analysis and later editorial work.

## 1. Collector output

The collector writes one immutable run packet to:

`data/viral_feed/YYYY-MM-DD/HHMM.json`

It also refreshes:

- `data/viral_feed/latest.json`
- `data/viral_feed/index.json`

Unresolved but useful public leads may be preserved in an immutable sidecar such as:

- `data/viral_feed/YYYY-MM-DD/HHMM_leads.json`

A lead without a resolved original X status permalink/status ID stays outside the canonical admitted set.

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
- `route_stats`
- `queries`
- `failures`
- `posts`

Each admitted post should preserve, where publicly observable:

- `url`
- `status_id`
- `author_handle`
- `published_at`
- `published_at_source`
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
- `metric_precision`
- `metric_observations`
- `source_freshness_state`
- `source_snapshot_at`
- `source_cache_risk`
- `sampling_intent`
- `post_type`
- `promotion_status`
- `discovery_query`
- `discovery_route`
- `source_url`
- `corroborating_urls`
- `evidence_level`
- `original_access_status`
- `evidence_note`
- `freshness_class`
- `near_duplicate_group`

Unknown values remain JSON `null`. Missing metrics must never be converted to zero.

## 2. Discovery routes

Allowed `discovery_route` values:

- `AUTHOR_WATCH` — rotate historically useful public author leads from `data/discovery_author_pool.json`; historical metrics are discovery seeds only and never carry forward to a new post.
- `TOPIC_WATCH` — rotate current-interest topic searches.
- `EVENT_TWO_HOP` — identify a current entity/event from public news/Hacker News/Reddit-index/GitHub sources, then search for a corresponding X post. Upstream event popularity is context, not X reach evidence.
- `PUBLIC_X_AGGREGATOR` — use free public pages that expose current X post IDs/permalinks, excerpts or publicly displayed engagement, then corroborate the original X identity with additional public evidence where possible. Registered sources and limitations live in `data/public_x_discovery_sources.json`.

The collector should not depend on one generic search route. A normal run should attempt a bounded mix of routes and rotate them when yield drops.

## 3. Evidence levels

Allowed `evidence_level` values:

- `ORIGINAL_X_RENDERED` — original X status/article page rendered and checked directly.
- `ORIGINAL_PERMALINK_CORROBORATED` — a real numeric X status permalink is corroborated by one or more public sources, but original X rendering is blocked or unavailable.
- `PUBLIC_EMBED_METRICS` — a public third-party page exposes the X status ID plus labeled public engagement values.
- `SECONDARY_METRIC_OBSERVATION` — a secondary source reports a numeric observation such as “about 17K views after 10 minutes”; precision and timing must be retained.
- `PUBLIC_MIRROR_OBSERVED` — a public mirror shows post text/date/metrics but the original permalink may not yet be resolved.
- `DISCOVERY_LEAD_ONLY` — useful lead, not strong enough for structural/propagation claims.

Direct X `403` does not invalidate a real permalink if the status ID, author and content are independently corroborated. It does lower the evidence level.

A numeric X `status_id` may be used to derive `published_at` from the X/Twitter Snowflake epoch. If so, set `published_at_source` to `X_SNOWFLAKE_STATUS_ID`; do not present it as an original-page timestamp.

Mirror-only records without a resolved original status URL remain discovery leads unless the analysis explicitly supports mirror evidence.

## 4. Metric and source-freshness discipline

Third-party metrics are allowed only with provenance.

- exact labeled values may populate canonical fields when there is no conflicting evidence;
- approximate prose values require `metric_precision=APPROXIMATE`;
- untimed cached values should have `metric_as_of=null` and an explanatory note;
- multiple observations belong in `metric_observations` rather than being overwritten;
- if two untimed sources show impossible decreasing cumulative metrics, canonical metric fields become `null` and the conflict is retained;
- do not infer unlabeled metric positions from a mirror layout; preserve the raw sequence only;
- do not infer X reach from upstream news/HN/Reddit popularity.

Keep three clocks separate:

- `published_at` describes the X post;
- `source_snapshot_at` describes the public corroborating page snapshot when known;
- `metric_as_of` describes the engagement observation when known.

A crawler's cache/crawl timestamp is not automatically any of those three. If a source snapshot predates the X post, reject that source's metrics for the post. Generic aggregator pages with obvious stale-cache risk must be downgraded rather than treated as current evidence merely because the URL is live.

Allowed `source_freshness_state` values are:

- `CURRENT_VERIFIED`
- `CURRENT_BUT_UNTIMED`
- `CACHE_STALE_RISK`
- `STALE_CONFIRMED`
- `UNKNOWN`

Allowed `freshness_class` values:

- `RECENT_0_24H`
- `RECENT_24_48H`
- `RECENT_2_7D`
- `EVERGREEN_REDISCOVERY`
- `STALE_REFERENCE_ONLY`

`STALE_REFERENCE_ONLY` items may be preserved for audit but must not be counted as current-trend evidence.

## 5. Sampling intent and controls

Allowed `sampling_intent` values are:

- `NATURAL_DISCOVERY`
- `MATCHED_COMPARISON_CANDIDATE`
- `CONTROL_SEARCH`

When a strong or high-interaction sample is found, the collector should attempt a same-author or similar-author comparison from a similar publication window where feasible. Prefer same author ±24h before falling back to similar author scale/topic/age.

A `MATCHED_COMPARISON_CANDIDATE` is **not** automatically a low-distribution control. It becomes a control only when comparable distribution evidence supports that classification. If the mirror exposes unlabeled number positions, preserve them as raw observations and do not use them to decide high vs low.

## 6. Index behavior

`data/viral_feed/index.json` is a compact registry rather than a second copy of all post bodies. It should track at least:

- latest run path and timestamp;
- total run count;
- recent admitted post count;
- unique status-id count;
- latest successful non-zero run;
- consecutive zero-yield/blocked runs;
- duplicate / near-duplicate totals;
- per-route query/candidate/admitted/failure totals;
- matched-comparison candidate count where available;
- unresolved current lead count where available;
- current discovery health.

The index must not turn missing metrics into zero.

## 7. Analyzer input and output

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

Candidate patterns may carry:

- `OBSERVATION`
- `HYPOTHESIS`
- `REPLICATED_HYPOTHESIS`
- `SUPPORTED_ON_HOLDOUT`
- `SUPPORTED_ON_OWN_ACCOUNT`

No pattern may jump directly from a convenience sample to a “viral formula”. Mirror evidence should be down-weighted relative to direct original-page evidence when the two disagree.

## 8. Comparison discipline

Prefer comparisons that reduce obvious confounding:

- same author first when available;
- otherwise similar author scale;
- similar topic;
- similar post age;
- similar publication window;
- original vs original rather than reply vs original;
- promotion/paid-partnership status separated;
- quoted/reposted material separated when it changes exposure mechanism.

When matching is not possible, retain the limitation instead of treating raw metric differences as causal evidence.

## 9. Editorial consumption

Editorial work may use the newest analysis as a hypothesis source, but must still independently check material strength, source quality, novelty against recent own-account posts, reader value, self-relevance / psychological stake where relevant, a single primary reader action, and factual/safety boundaries.

External viral observations are not proof that the same mechanism will work on the user's account.

## 10. Failure semantics

A blocked or zero-yield collector run is valid data when it records the reason. Do not recycle old posts merely to keep admitted-count positive.

If direct X rendering is blocked, the collector should attempt registered free `PUBLIC_X_AGGREGATOR` and corroboration sources before declaring the discovery chain blocked. If all permitted public routes degrade for several consecutive runs, surface the blocker instead of silently substituting stale snapshots.

Paid sources are outside the current production contract.
