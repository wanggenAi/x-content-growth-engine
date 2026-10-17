# Codex viral hunt — implemented behavior

Executor: Codex. No Claude service, paid model, detection SaaS, subscription or account scraping dependency.

## Commands and source contract

`search-queries [all|censorship|human_conflict|social|viral_x]` prints search matrices for Codex. Search snippets remain labelled discovery observations; URLs do not establish live X metrics. `capture.auto_discover_materials()` reexports the new standard-library collector; the existing authenticated local manual form is unchanged.

`hunt [--rss URL ...] [--telegram CHANNEL ...] [--reddit COMMUNITY ... --reddit-authorization FILE] [--materials FILE] [--top-n 5] [--limit 20] [--output data/private/hunt/latest.json]` collects sources or reads a material packet, applies auto initial review, ranks and actually executes `run_human_style_pipeline()` for each selected draft. Defaults to CDT RSS; Telegram channels are explicit. RSS/Atom, bounded Telegram HTML and authorized Reddit daily-top JSON parsers preserve original URLs, source time, capture time, attribution and unknown values. Approximate Telegram views remain text; no numeric metric is invented. Reddit rights must be independently verified, scoped and unexpired; user intent alone does not manufacture platform authorization. No Reddit call was made in the live run.

Fetch failures are per-source errors. HTTP timeouts, unknown dates and parser failures cannot create fresh material. A channel-message or feed publication time is not necessarily event time; event_time remains unknown until separately reviewed. Reposts can be new while the event is old. Exact title/text hash and URL dedup support prior-run seen hashes, but do not establish semantic novelty. Raw feed text and private review outputs stay ignored/local. Collectors do not inspect linked videos/screenshots or infer what they show.

## Admission V2

Threshold62, minimum1 real material, default Top5, configurable1–20. Multiple equally good topics can pass. Margin remains visible but is not a blocker. Freshness remains source-age scoring, unknown/future time still holds. Duplicate/synthetic pools and mismatched material/source/draft contracts still hold.

Weights remain raw18/surprise12/conflict10/self-insertion10/stopping22/mass18/share5/reply5. FAR and HIGH background deduct8 each (MEDIUM4). Bonus cap20: documented censorship8; verified artifact or concrete monetary number6; supported comment-branch structure6. A censorship/artifact keyword alone contributes zero verified-evidence bonus. Bonus fields are part of the material binding. Numerical details are a structural signal, not proof a claim is true.

`auto_rate_material()` fills missing 0–4 ratings with labelled structural estimates; it never overwrites supplied ratings or turns unknown audience behavior into observations. Evidence/feature traces remain in reports; supplied invalid evidence still fails. No engagement counter promotes a topic automatically. These heuristics cannot promise viral reach or solve subjective audience judgment.

## Rewriting and review boundary

Existing AI flavor patterns, abstractness, fake-humanization and fact locks remain. Added newsroom-residue phrases are penalized and cleaned outside protected direct quotes. Conservative scene-first reordering applies only to independent paragraphs with generic background, never unsupported pronouns, attribution or conditional context. At most two intact sentences are grouped per paragraph; physical screen lines depend on the client. Long quotes and qualified/conditional statements are kept intact. Multiple URLs, quotes, numbers and uncertainty markers remain locked; risky cleanup returns HOLD_FACT_DRIFT instead of silently losing facts.

`generate_viral_variants_prompt()` returns A scene/fact contrast, B concrete interests/relationship cost, C outcome/timeline contracts for Codex. It forbids invented first-person experience, unsupported motives, copying a full article, withholding contrary evidence and forced conclusions. This is a writing interface, not an external model call or a guarantee of 100% PASS.

`hunt` outputs clean previews under `drafts`, failures under `held_drafts`, and source-fact/Reader Model/semantic-novelty production holds. It deliberately never fills human_checked or agent_checked. `source.status=SOURCE_CHECKED` means retrieval only; `source.fact_verification=UNVERIFIED` remains. Before READY, Codex must review source boundaries and provide `source_fact_review` (FACT_BOUNDARIES_REVIEWED, exact evidence, reason, matching source URL), a current Reader Model and the existing review/authorization fields, then actually call `prepare_candidate()` / `prepare-candidates`. This preserves the previous contamination fix without requiring every raw lead to be manually entered.

Research/rewrite control is ACTIVE. Qualified manual publication remains separate; the hunt command never submits, schedules or authorizes an X post. Existing DRY_RUN_ONLY candidates and production holds remain. The existing scheduler is not resumed or changed by this implementation task.

## Validation

Mocked RSS/Atom/Telegram/Reddit inputs, failure recovery, cross-run dedup, missing timestamps, private destinations, unauthorized Reddit, singleton/equal-score admission, Top-N limits, preserved human ratings, evidence-only censorship bonus, discovered-source fact review, actual style/fact preview, offline CLI and existing human-style/semantic/contract regressions run without network in CI. The real smoke summary is stored separately from research claims; no reach or growth outcome is inferred.

## Actual 2026-10-17 smoke

Three free public source requests produced33 parsed/30 retained entries, source-message under24h=30, 24–48h=0, unknown message time=0, duplicate ratio0 within this run, two domains. Five selected:4 passed actual style/fact-preservation previews,1 held at AI flavor46. Underlying facts/event dates remain unverified. Safe source links and numeric gate results: `data/codex_hunt_smoke_2026-10-17.json`; raw source/excerpt/draft outputs remain ignored. Initial DNS/timeouts and Telegram self-closing-tag timestamp failures were retained and corrected. Browser-harness had no working daemon, so public HTTP completed the smoke. No X/Reddit account action, paid call or scheduler change.

Also found during the required isolated seed audit: the previous rank-materials local variable named report shadowed the existing report() function inside main(), breaking report/audit. Renamed it and added CLI regression coverage. Seed audit runs with seven old index observations and reports its real limitations; it is not a current feed or growth-validation audit.
