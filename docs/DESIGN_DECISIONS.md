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
| Sunbreak/TopicEye discovery designs | REFERENCE | Sunbreak's checkpoint overlap is useful for authorized HN/RSS sources; TopicEye confirms that its X adapters depend on Apify or unverified third-party RSS. No production source is added from either. |
| Growthmate or Postiz as application foundation | REJECT | Growthmate needs X OAuth/API, model providers, Postgres/Redis; Postiz has AGPL obligations and a multi-service scheduler footprint. Both overshoot a single-user research notebook. |
| Reddit automated ingestion | REJECT | Reddit's current developer terms restrict commercial use and prohibit model training without permission; authorization for this intended use is not established. |
| Upworthy discovery/holdout design | REFERENCE | Strong experimental pattern, but outcome and platform differ; no direct formula transfer. |
| Separate X samples, external material, formula versions and own-post outcomes | BUILD | Prevents source material from being mistaken for a mechanism or tested outcome. |

Minimum architecture: versioned JSON evidence input -> validated Python import -> SQLite research tables -> audit/report CLI -> manually reviewed research packet and own-post feedback import. Additional UI, local clustering and automation follow demonstrated data quality and rights.

## Phase 2 decision, 2026-09-30

| Decision | Class | Evidence and limit |
| --- | --- | --- |
| Local manual capture form and CSV batch import | BUILD | Browser Harness successfully exercised the local form; explicit human check, source reference and metric time reduce JSON-entry friction. Local-only binding and ignored private files protect account data. |
| Browser Harness for local UI and permitted non-X public sources | ADAPT | Existing Chrome connection works. Capability is not platform permission; no X browser automation was run. See [permission gate](BROWSER_RESEARCH_POLICY.md). |
| Scripted X site browsing or scraping through Browser Harness | REJECT | X terms require prior written consent for crawling/scraping, and automation rules warn against website scripting. No authorization in this session. |
| Query-level yields and failed-channel records | BUILD | Thirteen public-search queries yielded four new unique candidate IDs; the separate blocked policy record marks X browser automation stopped before execution. Search still provides zero dated original-page metrics. |
| Dated screenshot/page metrics and relative cohort basis | BUILD | Index views are undated historical clues. READY comparison requires two original-confirmed posts, explicit relative baselines and dated non-index view evidence. |
| MarkItDown OCR as free production material processor | REJECT | Official plugin documentation requires a supplied vision-model client; without one OCR is skipped. No paid API or untested local model is added. |
| HN/GitHub/NASA/FIDO material research | BUILD | Separate from X post evidence; original drafts cite primary sources and still require human editorial review. |

The minimum working architecture is now SQLite plus provenance-aware JSON/CSV import, the localhost manual capture form, query/quality reports, and Markdown/JSON research packets. Search supplies leads; a person verifies X originals. Materials and drafts proceed in parallel. The architecture still does not contain an automated X collector or a validated formula engine.
