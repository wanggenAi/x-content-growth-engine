# Codex Viral Hunt production behavior

## Collection

`collect-feed` reads free public RSS/Atom, GitHub release Atom, Hacker News official Firebase top/best/new and configured Telegram public previews. Reddit remains behind verified authorization and use-rights records. Browser/public-search results enter through `import_search_leads()` only after the original public page is opened and labelled `ORIGINAL_PAGE_CHECKED`.

The four-hour `.github/workflows/viral-hunt.yml` job runs collection, exact/fuzzy event dedup and automatic preview screening. It writes `data/viral_feed/YYYY-MM-DD/HHMM.json`, `latest.json` and `index.json` inside the run, then uploads them as a workflow artifact. It has read-only repository permission, never imports publication code and asserts `publication_triggered=false` and `automatic_x_submission=false`.

Collector health is `STALE` after eight hours, `LOW_SOURCE_DIVERSITY` below three families and `INSUFFICIENT_FRESH_MATERIAL` below ten materials under 48 hours.

## Preview and production

`AUTO_SCREEN_SCORE` is a heuristic queue signal. `auto_rate_material()` does not fill the editorial review object. Preview may start with one item and return Top5, always labelled `PREVIEW_ONLY`.

`EDITORIAL_TOPIC_SCORE` requires an explicit `DEEP_EDITORIAL_REVIEW` with reviewer/time and eight separate rating/evidence/reason records. Three or more exact duplicate evidence or reason values invalidate it. Surprise, conflict, self-insertion, mass relevance, first-screen stop and reply potential have dimension-specific support checks. A plain amount adds no hard-evidence bonus; only a verified artifact or verified cost/contrast binding can add one.

Production enforces:

- at least 10 distinct events;
- raw pool >=30;
- valid deep reviews >=20;
- source-age under48h >=10;
- source families >=4.

Top10 is the reviewed shortlist, Top3 the reviewed finalists and Top1 the sole production winner. A gap under five invokes the second-stage judge. Top2 through Top5 always receive `NOT_PRODUCTION_WINNER`. `candidate_admission()` recomputes the whole pool and rejects preview contracts.

## Actual dry run

The on-demand run completed at `2026-10-17T12:56:38.143594Z`: 83 real public materials, 65 under48h, no within-run exact duplicates, and four source families: Hacker News31, Telegram23, GitHub20, Chinese media7. Twenty materials received separate Codex deep reviews. The strict competition selected one winner, `D071e81714bf4d9be`; all three authored Top1 previews passed Human Style and remained `publication_allowed=false`.

Evidence: `data/viral_feed/2026-10-17/1256.json`, `data/viral_hunt_deep_reviews_2026-10-17.json`, and `data/viral_hunt_validation_2026-10-17.json`. Source retrieval is not independent fact verification. Telegram claims, video contents and original event times remain unverified unless separately reviewed.

Browser Harness doctor saw Chrome running but no daemon or active connection. The run therefore used public no-login HTTPS feeds and retained no browser/account data. No X post was submitted.
