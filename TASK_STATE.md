# Task State

Checkpoint: 2026-09-29. Machine state: `state/task_state.json`. Runtime sample DB is reproducible from `data/seed_x_observations.json`.

GitHub workstreams: [X samples](https://github.com/wanggenAi/x-content-growth-engine/issues/1), [reference research](https://github.com/wanggenAi/x-content-growth-engine/issues/2), [original material](https://github.com/wanggenAi/x-content-growth-engine/issues/3), [validation and feedback](https://github.com/wanggenAi/x-content-growth-engine/issues/4).

## Completed

- Inspected empty independent repository and available GitHub authorization.
- Reviewed required reference repositories and Upworthy methods at source level; documented evidence and BUILD/ADAPT/REFERENCE/REJECT decisions.
- Probed free public-index X discovery; saved 7 real Chinese X URLs, including 4 high-reach candidates and 3 ordinary candidates. Four posts belong to one author, giving a preliminary same-author comparison pool; one high post is marked a paid partnership and excluded from clean comparisons.
- Implemented local SQLite import, provenance/metric validation, deduplication, audit and separate research/material/formula/own-outcome tables.
- Recorded the first evidence interpretation and disqualifying caveats in `docs/FIRST_SAMPLE_REVIEW.md`.
- Built a separate material import with provenance, verification status, rights note and recheck date; imported two first-party source-checked leads (details in `docs/FIRST_MATERIAL_REVIEW.md`).

## Evidence gaps

- All seven observations use a single public search-index route. Search results are selection-biased and stale; no claim of live metrics or scalable collection.
- Author follower counts and most interaction fields are UNKNOWN. No valid normalized reach estimate.
- No formal propagation hypothesis, replicated finding or experimental support. No user-account performance data.
- Official X reads charge per resource; no verified free authorized bulk X source. Reddit is excluded pending authorization.

## Next executable work

1. Broaden discovery across author/topic/time queries and manually confirm direct public-page availability; register all failures and query denominators.
2. Add more ordinary controls from the same authors and time windows; label promotions/quotes and obtain follower information only where publicly and lawfully available.
3. Expand source-checked external materials beyond the two first leads, then create manual ChatGPT research/creation packets and own-post feedback import.
4. Only after adequate coverage: preregister structure labels and holdout comparisons, then test hypotheses against independent data.
