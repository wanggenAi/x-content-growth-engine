# Free X Discovery Probe

As of 2026-09-29, seven Chinese X links were found through public web search and recorded as historical index snapshots. Author-filtered follow-up queries such as `site:x.com/huangyun_122/status/ "Views" AI` and `site:x.com/0xValkyrie_ai/status/ "Views" AI` did not reliably return posts from those authors; results mixed unrelated languages and accounts. The search provider did not expose a stable denominator of all eligible posts. No clean new matched control was admitted from that pass.

A single unauthenticated direct GET of [one known X post](https://x.com/AI_Jasonyu/status/2026216830940110922) returned HTTP 200 HTML with public `og:description` text matching the indexed post excerpt. The checked metadata did not provide a reliable view count. A second observation in `data/direct_page_probe.json` therefore has `direct_public_page` provenance and all metrics `null`. This was a manual feasibility probe, not a scheduled scraper; it does not establish permission or stability for bulk collection.

The practical zero-cost route currently is manual/public-index URL discovery plus limited manual original-page confirmation and user-entered screenshots or metrics. [Official X API pricing](https://developer.twitter.com/) charges for reads, so it is excluded. No browser cookies, third-party session tools or unofficial GraphQL clients were used. The target of 300 high and 150 ordinary posts remains conditional on finding an authorized, sustainable source; present evidence does not support treating it as achievable automatically.

