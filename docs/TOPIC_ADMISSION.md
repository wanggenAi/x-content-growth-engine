# Topic admission production contract

The supported production entry is `growth_engine.candidate_pipeline.prepare_candidate()`; the batch CLI is `python3 -m growth_engine prepare-candidates INPUT --output OUTPUT`. Each input candidate has a `material` object, current draft, locked facts, source references and an explicitly reviewed Reader Model. The CLI ranks the entire input pool before preparing any candidate. A single candidate can also be prepared directly, but must carry the complete `material_pool`, `material_id`, `material_hash` and `competition_as_of`.

`fresh material pool → evidence-backed Viral Admission → relative competition → fact lock / Reader Model semantic integrity → draft → Human Style → Editorial Gate → READY → pre_publish_assert → visible manual publication`

## Grounded topic review

`viral_admission.score_material()` accepts eight 0–4 editorial ratings: raw material strength (18%), surprise (12%), conflict (10%), self-insertion (10%), topic first-screen stopping power (22%), mass relevance (18%), share (5%) and reply (5%). Every rating requires an exact source span and a specific reason. Missing, generic or ungrounded observations hold; no word list creates HIGH. These are **editorial hypotheses**, not measurements of how many of 100 readers will care.

Reviewers perform the three-second/scroll test on the event: can a stranger understand the conflict without reading several layers of background, and why would they stop? `first_screen_stopping_power` records the observation and reason; `hook` records a short internal extraction, exact evidence and explanation. It is not a mandatory public headline or an instruction to add reactions to the post. No hook means REJECT_NO_HOOK; weak stopping reason means REJECT_LOW_STOPPING_REASON. A source URL or a smooth sentence does not count as interest evidence.

The weighted topic score deducts audience distance NEAR/MEDIUM/FAR (0/7/20), background LOW/MEDIUM/HIGH (0/9/22), and source age (<48h:0, <7d:6, older:12). Source timestamps must be timezone-aware and not future. Date-only historical timestamps retain their precision label. Unknown source time or unchecked provenance holds. Thresholds: topic >=60, raw >=50, stopping >=50. FAR additionally needs surprise and stopping >=75. This permits an exceptional distant story without privileging domestic nouns. Source confidence remains separate; writing quality is a downstream score and cannot compensate for a rejected topic.

## Competition

At least ten **source-checked, evidence-reviewed, under-48h independent materials** are required (20–50 recommended). Missing source time cannot inflate this count. Duplicate IDs, canonical URLs, event IDs or identical material text invalidate the pool; V2EX host aliases are normalized. Synthetic fixtures invalidate a production pool. Event identity across different accounts still needs editorial review: exact matching cannot guarantee semantic deduplication.

Admitted materials sort before held materials, then by topic score, background cost, audience distance and freshness. Reports keep Top10, Top5, Top1, every score/reason, reviewed/fresh counts and a pool hash. Only rank 1 with a >=5-point lead may continue. A close result remains held for editorial review; it is not an arbitrary first passing candidate.

`candidate_admission()` recomputes the complete competition and binds the selected source and pre-rewrite draft to the material hash. Editorial Gate recomputes it again. A hand-written rank, count or PASS flag is insufficient. Source/material, draft or pool edits invalidate the contract. The contract is reproducibility protection, not cryptographic proof of a human author: ratings themselves still require competent editorial review.

## Reader Model integrity

`reader_model_semantic_integrity()` binds text, subject value, payload, source references, topic, action and locked facts. Every populated semantic statement and HIGH needs an exact source-fact span, specific reasoning and a value hash. Missing origin, defaults, generic HIGH rationales and stale context fail. Broad semantic anchors catch conspicuous copied topics; they are deliberately not claimed to be a full language-understanding model. Per-field checks prevent one on-topic sentence masking an unrelated profile. Failed integrity stops before rewriting. A conservative rewrite may rebind unchanged statements; removed supporting evidence still fails the final gate.

Production modules must not import tests or use `good_profile()` as a fallback. Empty profiles remain UNKNOWN. Tests enforce this import boundary. An external assembly script importing fixtures is still caught by the runtime evidence/context gate.

## Publication boundary

`state/publication_control.json` is PAUSED for the current repair. Missing/invalid control fails closed. `pre_publish_assert()` independently reruns Editorial Gate; live use requires ACTIVE, no DRY_RUN_ONLY/production_holds, exact admitted text, and competition no older than 24 hours. `dry_run=True` always returns publication_allowed=false. No module calls X or bypasses visible manual submission. Direct UI use outside this preflight cannot be technically prevented by repository Python code; agents must not treat a style PASS as publication authorization.

Published historical records remain readable and are not rescored in place. C390 retains its original contaminated annotation for audit; only its actual prior publication metadata was reconciled. Repair introduces zero new X submissions.

## Reproduce the real challenge

```sh
python3 -m growth_engine rank-materials data/viral_admission_challenge_2026-10-16.json --output /tmp/topic-ranking.json
python3 -m unittest discover -s tests -v
python3 -m compileall -q growth_engine tests
python3 -m pytest -q
```

Core has no new runtime dependency. pytest is only a test runner. Saved real dry-run and ranking are replay-checked in tests. Research snapshots use fixed `as_of` for reproducibility; live publication requires a refreshed pool rather than reusing a frozen research result.
