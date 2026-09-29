# Design Decisions

Decisions as of 2026-09-29. Reconsider only when new evidence or a concrete need appears; record the test and migration cost first.

| Decision | Class | Reason and validation gate |
| --- | --- | --- |
| Python standard library CLI + SQLite local database | BUILD | Single-user, zero service cost, easy checkpoint and dedupe. First seed import and tests validate the path. |
| Source adapter contract with provenance, method and failure reporting | ADAPT | Inspired by Harken's fetch/analyze/store isolation and last30days multi-backend discovery; implement only authorized sources. |
| Public search index plus human URL/metric import | BUILD | Seven real X examples are retrievable, but coverage and freshness are unproven. A one-page direct public HTML probe confirmed an excerpt without a reliable view count. No unattended X scraper. |
| Cookie-based X GraphQL clients and unofficial X endpoints | REJECT | Session access/security and platform compliance unverified; risk of account exposure and brittle access. |
| Official X API for research | REJECT | Current public pricing charges for reads; violates zero incremental cost. Recheck only if truly free authorized access changes. |
| Two persisted workflows: research/creation and feedback/learning | ADAPT | AutoViralAI separates flows, but its paid model and scraper dependencies are excluded. Human handoff is explicit. |
| BERTopic model stack | REFERENCE | Useful local topic modeling later; initial sample too small, embedding/UMAP/HDBSCAN cost and complexity unjustified. Clusters cannot validate mechanisms. |
| Growthmate or Postiz as application foundation | REJECT | Growthmate needs X OAuth/API, model providers, Postgres/Redis; Postiz has AGPL obligations and a multi-service scheduler footprint. Both overshoot a single-user research notebook. |
| Reddit automated ingestion | REJECT | Reddit's current developer terms restrict commercial use and prohibit model training without permission; authorization for this intended use is not established. |
| Upworthy discovery/holdout design | REFERENCE | Strong experimental pattern, but outcome and platform differ; no direct formula transfer. |
| Separate X samples, external material, formula versions and own-post outcomes | BUILD | Prevents source material from being mistaken for a mechanism or tested outcome. |

Minimum architecture: versioned JSON evidence input -> validated Python import -> SQLite research tables -> audit/report CLI -> manually reviewed research packet and own-post feedback import. Additional UI, local clustering and automation follow demonstrated data quality and rights.
