# Browser research permission gate

Reviewed 2026-09-29. The local Browser Harness CLI reported version 0.1.13, a live Chrome connection and a working navigation to a non-X test page. It subsequently opened the project's local capture form and submitted one synthetic record to a temporary database. No X session, login state or account permission was inspected or assumed. One initial navigation timed out while the temporary server was starting; retry succeeded after the server was listening. Local UI testing yielded one synthetic test record, zero research samples.

## A. Human use of X's ordinary interface

The user can open individual post links in X, read the original, author context and comments, and manually note visible metrics, post form and promotion signals. A researcher can enter their own observations through the local form, with original URL, UTC observation and metric time, evidence reference and notes. A human decision to save a screenshot does not authorize publishing private account information; screenshots stay outside the public Git repository. No automatic interaction with X is needed for this path.

## B. Browser-assisted work within confirmed scope

Browser Harness is useful here for testing the local capture interface and navigating other openly accessible sources when their terms permit the action. It can help inspect a user-supplied, locally stored screenshot or research note only with permission and without extracting browser cookies. Current verified project use: local form opened and one synthetic submission passed. It has not produced any genuine X sample.

## C. Unapproved X automation

[X's terms](https://x.com/en/tos) prohibit crawling or scraping in any form without prior written consent. [X's automation rules](https://help.x.com/en/rules-and-policies/x-automation) warn against non-API automation such as scripting the website. No such written authorization is present. Therefore no scripted X search, navigation, DOM extraction, bulk sampling, login/account actions, Cookie reading, captcha bypass, hidden endpoints or API-cost circumvention are enabled. `data/phase2_queries.json` records this blocked channel as q5, with zero attempted X automated visits and zero samples. A changed permission decision requires a specific written authorization scope and a new recorded review.

## Actual feasibility

| Route | Attempts | Admitted research links | Original confirmed | Dated metric evidence | Limit |
| --- | ---: | ---: | ---: | ---: | --- |
| Public-search q1-q14 (q5 is policy gate) | 13 queries | 5 admitted candidate observations, 4 new unique IDs | 0 | 0 | Fourteen logged records include the blocked gate; author/month filters unreliable |
| Browser Harness X automation | 0 visits | 0 | 0 | 0 | Permission gate blocked |
| Browser Harness local UI | 1 synthetic submission | 0 | 0 | 0 | Test DB only; not an X data source |
| Existing one-off direct public page probe | 1 known URL | 0 new IDs | 1 excerpt confirmation | 0 | Did not expose reliable views; does not imply bulk permission |

The manual-original path remains executable but requires the user or authorized researcher to inspect individual X pages. Its measured yield in this phase is zero because no such user observations were supplied. Search candidates stay discovery leads until that step occurs. The routes are complementary; neither HN nor GitHub material is counted as X research data.

## Account publishing authorization — 2026-10-01 (Asia/Shanghai)

The user explicitly authorized Codex to publish through their account in this chat. Earlier restrictions on user permission for posting are superseded for this task; repeating the same authorization question is unnecessary. This is not permission for likes, follows, direct messages, settings changes, credential extraction or research scraping.

Re-read the official [X automation rules](https://help.x.com/en/rules-and-policies/x-automation) at 2026-09-30T16:15:06Z. Section I / Don’t prohibits non-API automation including scripting the website. Browser Harness posting remains blocked by this platform-method review. No free approved posting integration is configured; no new paid integration was added. Draft preparation is permitted; an X homepage URL in ambient state does not establish login, account identity, or a completed post.

## User-directed Computer Use publishing scope — 2026-09-30T16:45:04.204139Z

After being informed of the non-API automation restriction, the user explicitly instructed Codex to use Computer Use for posting. For this task this supersedes the previous project-level manual-only publishing instruction and authorizes a small batch of prepared original posts through visible UI. This records user scope, not X platform approval or a claim of compliance. No account settings, follows, likes, replies, scraping, cookies, hidden endpoints or paid integrations are authorized by this change. Confirm the visible active profile and empty composer, post each item once, and verify the result before the next item. Keep screenshots and account-specific publication logs under ignored `data/private/`.

## User-directed visible research scope — 2026-10-01T00:12:06.509880Z

The user now explicitly requests Browser Harness inspection of public X posts exceeding 10,000 views, comparative analysis, original creation and previously authorized publication. This supersedes the earlier project-level prohibition on browser-assisted X research for this user-directed task. The scoped review permits a bounded first batch of visible public search/detail pages through the existing local Chrome session. Record agent inspection separately from human confirmation, preserve original URLs, UTC observation time, raw visible metrics and private evidence. Search-index claims alone do not meet the threshold. Do not install third-party account tools, extract cookies, invoke hidden endpoints, bypass access controls or collect bulk Reddit data. This records user authorization; X written permission is absent and the previously disclosed platform-method restriction has not changed. Publishing remains the separately authorized visible Computer Use route.

## Continued research scope — 2026-10-01T01:15:04.507227Z

The user explicitly requested continued research until justified confidence before further publication. This continues the existing user-directed local visible research authorization; platform approval is still not confirmed. Subsequent heartbeat runs are bounded to at most 15 new public priority pages per run, preserve evidence and failures, and keep publication conditional on the documented confidence gate. No new credentials, endpoints, third-party automation installations, account settings, social engagement or cloud/paid integrations are authorized.

2026-10-01T01:23:40.265674Z: User adds public-figure historical contrast and requests gradual larger-volume originals. Visible research and original source-checked test publication remain authorized; earlier unmet virality confidence is preserved as a finding, not represented as achieved. Native Computer Use may submit the small reviewed batch. This does not extend to private allegations, manufactured imagery or engagement actions.

2026-10-01T01:45:12.244160Z: User explicitly expands original-publication scope to at least200 further posts, progressively and across broad factual topics. Native visible Computer Use may publish source-checked distinct candidates; existing gates against unreviewed tools, cookies, hidden APIs, invented records and engagement actions remain. No platform approval is claimed. Campaign work item count is not an actual publication count.

2026-10-01T02:08:00Z: Four additional source-checked originals (C014–C017) were posted once each and verified on their public detail pages. Campaign count is 17 new / 42 cumulative agent-verified account publications, with 183 briefs still pending source review. C017 uses the Nobel primary citation; no view, engagement or virality result is inferred. Public-figure death/decline claims remain restricted to attributable dated records.

2026-10-01T02:37:00Z: C019 and C020 were posted once each through visible Chrome and returned the platform's visible send confirmation. Campaign count is 19 new / 44 cumulative agent-verified account publications, with 181 briefs pending source review. The posts use Nobel and NASA primary records; no reach, engagement or virality result is inferred.

2026-10-01T02:40:00Z: C021 was posted once through visible Chrome as an explicitly labeled editorial hypothesis. Campaign count is 20 new / 45 cumulative agent-verified account publications, with 180 briefs pending source review. “暴论” framing is allowed only when the text labels opinion or hypothesis and does not present an unsupported factual claim as news.

2026-10-01T03:16:16Z: The user requests Browser Harness first for normal operations and Computer Use where necessary, direct relevant neutral conversation, no dedicated account-monitoring overhead, and mandatory body checks. Latest three submissions had CJK loss; send-confirmation-only verification was invalid and repaired. Record old and edited URLs; verify editor text before save and reload full public body afterward. Browser-assisted navigation and editorial preparation were used during repair; final updates used native visible Computer Use. No tool switch creates platform approval or permission to bypass limits. User authorization now includes natural content-relevant replies, but no duplicated bulk replies or manufactured engagement.

2026-10-01T05:09:10Z: The user expanded the publication target to at least 1000 additional distinct originals. Browser Harness verified the official YouTube 2021 dislike-count announcement for candidate C201; native visible Chrome paste timed out and keyboard input dropped Chinese characters, so the draft was cleared and no post was submitted. The existing user authorization still applies, but publication remains gated on a complete visible-editor body and independent public-page reload.

2026-10-01T05:27:17Z: C201 was submitted once after native visible Chrome accepted the full Chinese body. The independent public detail page was reloaded and matched the account, five body paragraphs, no duplicate paragraphs, minute timestamp and YouTube source card. The source URL appears as X's t.co card rendering; the original URL is retained in the campaign manifest. No engagement action was performed.

2026-10-01T05:37:46Z: C202 was submitted once after native visible Chrome accepted the full Chinese body. The independent public detail page was reloaded and matched the account, five body paragraphs, no duplicate paragraphs, minute timestamp and openai.com source card. The original URL is retained in the campaign manifest. No engagement action was performed.

2026-10-01T06:03:04Z: C203 was submitted once after native visible Chrome accepted the full Chinese body. The independent public detail page was reloaded and matched the account, five body paragraphs, no duplicate paragraphs, minute timestamp and uscourts.gov source card. The original URL is retained in the campaign manifest. No engagement action was performed.
