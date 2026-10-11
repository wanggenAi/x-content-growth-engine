# Current Control State

Updated: 2026-10-11 (Asia/Shanghai)

This file is the canonical current-state entry point for ongoing automation and future agents. When historical notes elsewhere conflict with this file, use this file plus the newest `TASK_STATE.md` / `state/task_state.json` evidence.

## Repository authority

- Canonical working branch: `main`.
- PR #5 (`feature/x-research-phase2`) was squash-merged into `main` on 2026-10-11.
- Merge commit: `4184a4299550a1a8226a62cf939feeadf6819562`.
- The push-triggered `tests` workflow for that merge completed successfully.

## Publication control

- `PUBLICATION_PAUSED_FOR_LEARNING` is historical state from 2026-10-06 and is no longer the global control state.
- The user's 2026-10-09 instruction restored continued ordinary public-post publication for qualified content.
- Publication count is not a success KPI. Quality, natural reach, substantive engagement, follower growth and learning quality remain the objective.
- Source checking, duplication checks, content-quality gates, visible-editor verification and independent public-detail verification remain required.
- Missing feedback does not justify fabricating outcomes and does not automatically block otherwise qualified research/publication.
- No bulk manufactured engagement, hidden endpoint use, cookie extraction or access-control bypass is authorized.

## Viral research data pipeline

Two scheduled tasks maintain the new research input loop:

1. **Viral feed collection**: every ~4 hours, prioritize recent public X posts (normally within 48h) and source-verifiable evergreen rediscoveries. Normalize evidence and metrics without inventing missing values.
2. **Viral structure analysis**: daily, analyze accumulated feed data with high/ordinary/low propagation comparisons where available. Patterns remain `HYPOTHESIS` until supported across batches and counterexamples.

Canonical locations:

- `data/viral_feed/` — raw normalized discovery packets and freshness metadata.
- `data/viral_analysis/` — machine-readable comparative analysis.
- `docs/VIRAL_PATTERN_LATEST.md` — current human-readable pattern summary once generated.

Collection and analysis are deliberately separate. The collector must not generate posts or promote a formula; the analyzer must not auto-publish.

## Evidence discipline

- Prefer recent material; keep old material only when it has durable rediscovery value and is explicitly labeled.
- Preserve post URL/status id, author, post time, observation time, discovery route, visible metrics and metric provenance when available.
- Unknown values stay `null`/`UNKNOWN`.
- Deduplicate by status id and mark near-duplicate text/events.
- Do not claim a stable viral formula from small, age-mismatched or selection-biased samples.
