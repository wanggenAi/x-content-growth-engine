# Topic admission repair — 2026-10-16

Starting main: `6a18d016061aa914afdac254e9e16a8694be2158`. Zero new X submissions in this repair. Existing heartbeat x was already PAUSED and remains paused. Publication requires review of this shortlist and a later explicit resume instruction.

## C390 incident

The production assembly script `/tmp/build_c390.py` imported `tests/test_reader_model.py::good_profile()`. Two local evaluation scripts used the same pattern. This attached an application/submission-failure profile, all legacy HIGH labels and the generic rationale “concrete evidence reviewed” to a family-finance story. It was fixture contamination, not shallow-copy mutation or previous-state leakage. Script hashes and relevant lines are retained in `data/topic_admission_incident_c390_2026-10-16.json`.

Five draft materials were evaluated in that round. There was no competitive Top5 or topic-ranking function. The agent selected C390 manually; `prepare_candidate()` ran Human Style, Editorial Gate checked profile completeness, and `pre_publish_assert()` treated that result as sufficient. This was an agent selection error plus missing upstream enforcement. The root cause was not X Native prose scoring alone.

Before: topic_strength absent; native style 84, native first screen 75, comment impulse 92; Reader Model legacy dimensions HIGH; READY=true. No numeric audience outcome is inferred from the user’s qualitative rejection. After: topic 0, rank 30/30, audience FAR, background HIGH, stopping 25, mass relevance 25. Renaming the ID preserves the result; there is no C390 exception. Source confidence, topic interest and prose quality remain separate.

Prior actual C390 post: https://x.com/qiluo27808/status/2110912757210173693 . Visible send confirmation and independent public detail body/account were observed before this repair request; UI time 09:56 Oct16 Shanghai is recorded at minute precision (01:56Z). The additional independent reload/source-target follow-up was interrupted, so the record does not claim full verification. Original text/Reader Model/old scores preserved. No edit, deletion or repost.

## Actual material collection

Completed `2026-10-16T02:22:15.771569Z`: 26 real page requests, 24 readable original pages, 24 unique URLs, one domain, duplicate ratio 0. Under24h=6, 24–48h=8, older48h=10, from original topic-header timestamps (not recent replies or search-index dates). Raw pages remain ignored/private. Two failures are retained in the challenge packet.

The challenge has 30 real items: 24 newly fetched materials plus six explicitly historical cases spanning brands, Nvidia, Musk, ordinary workers and a distant story. Coverage also includes AI, jobs, money, relationships, consumption and social life. **This is not 30 new current news stories, nor an independent blind audience test.** The concentrated V2EX convenience sample cannot establish population-level interest; earlier user preference against making V2EX the main production source is preserved. It is a repair challenge, not authorization to publish that feed. No labels were changed to manufacture a perfect pass rate.

Pool accounting: 30 unique, 28 source-reviewed, 14 under48h, 12 both reviewed and under48h. Scheduled canonical viral feed still reports `2026-10-12T00:28:27.377Z`; it is stale. This one collection does not mean scheduled recovery.

## Competition Top10

Ranking places publishable-topic candidates before held entries. A higher numeric score with HOLD_SOURCE_CHECK does not outrank an admitted item. Scores are explicit source-grounded **agent editorial hypotheses**, not observed reach or calibrated probabilities.

|Rank|Hook / source|Topic|Freshness|Distance / background|Raw|Stop|Mass|Reply|Share|Topic score|Admission|
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
|1|[让AI标数据，它先花200美元](https://v2ex.com/t/1248681)|AI/钱|24_TO_48H|NEAR/LOW|100|100|75|50|100|88.0|PASS|
|2|[领导让员工做AI项目比拼](https://v2ex.com/t/1248593)|工作/AI|OLDER_THAN_48H|NEAR/LOW|75|75|75|75|75|69.0|PASS|
|3|[第五个月被劝退还自己提离职](https://v2ex.com/t/1249128)|工作/就业|UNDER_24H|NEAR/MEDIUM|75|75|100|75|50|68.75|PASS|
|4|[十年经验，HR已读不回](https://v2ex.com/t/1248157)|工作/招聘|OLDER_THAN_48H|NEAR/LOW|75|75|75|50|50|63.5|PASS|
|5|[宕机近五小时，退七天消耗](https://v2ex.com/t/1249099)|AI/消费|UNDER_24H|NEAR/LOW|75|75|75|50|75|71.25|HOLD_SOURCE_CHECK|
|6|[干十小时，只记八小时](https://chinadigitaltimes.net/chinese/725195.html)|普通人/工作|OLDER_THAN_48H|NEAR/LOW|75|75|100|25|75|64.5|HOLD_NOVELTY_CHECK|
|7|[把生日蜡烛插在面条上](https://chinadigitaltimes.net/chinese/727105.html)|普通人/生活|OLDER_THAN_48H|NEAR/LOW|75|75|75|25|100|56.75|HOLD_NOVELTY_CHECK, REJECT_LOW_TOPIC_STRENGTH|
|8|[房子卖了还要倒贴十万](https://v2ex.com/t/1248572)|钱/房子|OLDER_THAN_48H|NEAR/HIGH|75|75|100|75|50|52.75|REJECT_LOW_TOPIC_STRENGTH|
|9|[纠偏先耗掉两成额度](https://v2ex.com/t/1248570)|AI/消费|OLDER_THAN_48H|NEAR/LOW|50|75|50|50|50|52.0|REJECT_LOW_TOPIC_STRENGTH|
|10|[恋爱三个月，发现前任欠钱](https://v2ex.com/t/1249080)|男女/钱|UNDER_24H|NEAR/HIGH|75|75|75|75|50|51.75|REJECT_LOW_TOPIC_STRENGTH|

## Top5 editorial review / Top1 dry run

1. AI labels data and spends $200: an agent trying to save human effort creates a concrete cost, then reports completion after a blocked request. One action/cost sequence; ordinary tool users can understand it without four years of family history. Author self-report only, not an independently established incident or claim that all agents behave this way.
2. Company AI project contest: clear workplace demand and extra effort, but less surprising and already >48h at collection time.
3. Asked to resign in fifth month: concrete employment cost, but only the worker’s account, not confirmed unlawful dismissal.
4. Ten years’ experience and HR silence: recognizable job-search mismatch, but one person cannot prove an industry trend.
5. Five-hour outage / seven-day compensation: strong concrete loss, but only a community repost; HOLD until primary notice corroboration. It is not publishable merely because it occupies fifth place.

Top1 R1248681: topic88, margin19 over the next admitted alternative; downstream writing78. Actual production entry produced `TOPIC-DRYRUN-20261016`, READY_FOR_MANUAL_PUBLISH, code-generated HUMAN_STYLE_V2 and Editorial Gate PASS. See `data/viral_admission_dry_run_2026-10-16.json`. It is marked DRY_RUN_ONLY, with explicit user-pause, missing domestic restriction evidence and author-self-report corroboration holds; live preflight refuses even if the global switch becomes ACTIVE. READY here is a technical dry-run outcome, not permission to submit.

Compared with C390, the winner has one comprehensible action/cost contradiction, less background and closer tool/work relevance; C390’s secondary foreign personal story needs several transfers and old events explained first. This is an auditable editorial judgment, not proof the winner will perform better.

## Validation and remaining limits

Local pytest: 81 passed. `python3 -m unittest discover -s tests -v`: 81 passed. compileall passed; GitHub Actions will verify the pushed commit. Coverage includes contamination, source/action/context changes, unsupported HIGH, no production test imports, first-pass trap, insufficient/duplicate/ungrounded/stale pools, topic/prose/source separation, contract tampering, draft swap, real ranking replay and dry-run live-submission refusal. Existing Human Style blind/regression tests remain intact.

No supported READY/preflight path accepts the first passing draft without relative competition. Human annotations still determine semantic ratings; exact evidence and topic anchors cannot guarantee arbitrary semantic correctness or audience interest. Source diversity, independent reader feedback, stale scheduled collection, and the top candidate’s production evidence holds remain unresolved. The repair does not silently grant publication authorization or invent performance metrics.
