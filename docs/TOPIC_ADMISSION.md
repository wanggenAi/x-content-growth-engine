# Topic admission V3 production contract

`PREVIEW_ONLY` accepts a small pool and returns up to five auto-screened leads for editorial work. It never grants publication admission.

`PRODUCTION_COMPETITION` requires at least 10 distinct events and enforces raw pool >=30, valid deep reviews >=20, source age under48h >=10 and source families >=4. Deep reviews require eight separate rating/evidence/reason records; repeated evidence or reasons invalidate the score. Plain monetary numbers produce no hard-evidence bonus.

The production shortlist exposes Top10 and Top3 for review, but `candidate_admission()` accepts only the unique Top1. A margin under five triggers the deterministic second-stage judge over first-screen stop, mass relevance, background cost, audience distance, freshness and human tension. It still produces at most one winner.

Candidate material, pool, source, draft and Reader Model remain hash-bound. Human Style, Editorial Gate and prepublish run after topic admission. Frozen V1/V2 snapshots remain readable as history but cannot serve as current contracts.
