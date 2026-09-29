# First X Sample Review

Observation collected 2026-09-29 UTC through public search-index results linking to X pages. The seven post URLs and compact excerpts are versioned in `data/seed_x_observations.json`; run `python3 -m growth_engine import data/seed_x_observations.json` and `python3 -m growth_engine audit` to reproduce counts. Indexed metrics may reflect crawls several months earlier. The observation timestamp records when *we saw the index*, not when X produced the count.

| Author | Post | Indexed views | Provisional role | Limitation |
| --- | --- | ---: | --- | --- |
| @AI_Jasonyu | [Feb 24](https://x.com/AI_Jasonyu/status/2026216830940110922) | 293,300 (rounded) | high candidate | Satirical reply/quote context; not a clean text-only comparison. |
| @AI_Jasonyu | [Feb 1](https://x.com/AI_Jasonyu/status/2018150490757095507) | 6,593 | ordinary candidate | Earlier date and different subject/context. |
| @AI_Jasonyu | [Jan 18](https://x.com/AI_Jasonyu/status/2013107568663843183) | 3,582 | ordinary candidate | Different subject and outside a tight time window. |
| @AI_Jasonyu | [Mar 22](https://x.com/AI_Jasonyu/status/2035687356104102330) | 56,600 (rounded) | high candidate | Indexed page marks paid partnership; exclude from clean comparisons. |
| @huangyun_122 | [Mar 20](https://x.com/huangyun_122/status/2034927556605227031) | 23,600 (rounded) | high candidate | Claimed sales figures not independently checked. |
| @0xluffy_eth | [Feb 13](https://x.com/0xluffy_eth/status/2022303468741095697) | 45,300 (rounded) | high candidate | Promotes another product; possible ad context. |
| @AYi_AInotes | [Apr 4](https://x.com/AYi_AInotes/status/2040403020144587155) | 9,678 | ordinary candidate | Long quote-based post; interview claims not checked. |

The same-author set shows variation in indexed views. It cannot isolate wording, topic, audience size, quote distribution, promotion, timing or index freshness. No传播公式 is proposed or validated from these seven posts. The only supported technical result is that manual public-index discovery can produce traceable URLs and some historical public metrics at zero added cost. Query denominators, missed posts and current-count drift remain unmeasured, so sustainability is unproven.

Next probe: register each search query and count seen/eligible/missing-metrics URLs, test direct public-page reading where permitted, add comparable ordinary posts near each candidate's publication period, and obtain public follower counts only when available. The paid-partnership example is retained as a flagged case, not a clean mechanism example.

