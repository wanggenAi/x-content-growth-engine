# Phase 2 query probe, 2026-09-29

Counts describe the returned public-search result list, not X-wide coverage. No X page was automatically browsed. Search indexes may be stale and the result presentation may vary by locale or time. Observation time below is the time this research session saved the findings, not the unknown time of the indexed metric.

## q1

Exact query `site:x.com/status/ "浏览次数" "AI" "2026" 中文`: zero visible results. No X candidate.

## q2

Exact query `site:x.com/status/ "万次浏览" "普通人" "2026"`: zero visible results. No X candidate.

## q3

Author query `site:x.com/AYi_AInotes/status/ 2026 AI`: 13 visible results, two relevant status URLs, 11 other results (profile, unrelated content or search pages). [April 4 post](https://x.com/AYi_AInotes/status/2040403020144587155) displayed 9,678 views in the indexed result. [April 5 post](https://x.com/AYi_AInotes/status/2040669222838341969) displayed approximately 9.9 万 views. Both are AI podcast interpretations by the same author on adjacent days, but content length, quoted material, promotional intent and metric timing remain unresolved. No cohort assignment or comparison pair is justified yet. Search query output is ephemeral; this record preserves the observed summary and links, not an independent snapshot of X.

## q4

Author query `site:x.com/tangchuan_CN/status/ Claude 2026`: 14 visible results, one unrelated author's status URL and no admissible candidate. The search engine did not reliably respect the author restriction. This makes broad result counts a poor proxy for valid samples.

## Channel decision

Public search helps discover links but has high off-topic noise and cannot establish current metric timestamps or full context. Current Browser Harness has a working Chrome connection and can operate the local capture page. Its presence does not authorize scripted X access. The next useful evidence comes from a person viewing selected original posts in X's ordinary interface and entering observed context, screenshots or notes through the local form. No claim that 30-50 verified samples are available is supported by this probe.

## q6-q14: broader author, topic and month checks

The nine further public-search queries are logged in `data/phase2_queries_round2.json`. Their shared `executed_at` is the session logging time, not nine separately timed executions; durations remain unknown. Result counts are the visible result list, while candidate counts are manually screened potentially relevant status links. This is not a full search recall estimate.

| Query | Visible | Admitted | Duplicate | Rejected | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| q6, @kenw_2 / e-commerce | 10 | 1 | 0 | 0 | [March 13 education post](https://x.com/kenw_2/status/2032391247369838904), 37.1K indexed views only as approximate prose |
| q7, @kenw_2 / school | 12 | 0 | 1 | 0 | Same post; no new control |
| q8, @GongYouchai / AI | 13 | 1 | 0 | 0 | [AI roundup](https://x.com/GongYouchai/status/2035537777870434788), no reliable metrics/date; factual claims need checking |
| q9, @vista8 / 2026 | 13 | 0 | 0 | 0 | No target-author status |
| q10, July city heat | 0 | 0 | 0 | 0 | No result |
| q11, workers and AI | 1 | 0 | 0 | 1 | Grok reply, excluded |
| q12, @AYi_AInotes / August | 12 | 0 | 0 | 0 | Trend-summary pages; no target status |
| q13, @dotey / AI | 13 | 1 | 0 | 0 | [February 10 translation/commentary](https://x.com/dotey/status/2021477874411225256), about 5.1万 indexed views; form/rights confounder |
| q14, @dotey / March | 12 | 0 | 1 | 0 | Repeated February post despite March query |

The second round adds three distinct **discovery links**, not confirmed original-page research samples. Across q1-q4 and q6-q14, thirteen public-search queries yielded five admitted candidate observations but only four new unique IDs relative to the original seven (q3 had one existing ID). Two queries repeated links, and seven did not admit a new link. The topic/month queries especially underperformed. No original-page metrics were verified by this route; the manual path remains the next gate.
