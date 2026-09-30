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
