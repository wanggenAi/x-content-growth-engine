"""Bounded, unauthenticated public-source discovery. Fetching is not fact checking."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import ipaddress
import json
import re
import socket
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET

from .human_voice import stable_hash

DEFAULT_RSS = (
    "https://chinadigitaltimes.net/chinese/feed",
    "https://github.com/openai/openai-python/releases.atom",
    "https://github.com/python/cpython/releases.atom",
)
HN_INDEXES = {name: f"https://hacker-news.firebaseio.com/v0/{name}stories.json" for name in ("top", "best", "new")}
SEARCH_QUERIES = {
    "censorship": ['"被删" "404" 最新 原文 存档', '"热搜消失" "通报" 时间 原始链接'],
    "human_conflict": ['"聊天记录" "转账" 真实经历 原话', '"录音" "曝光" 反转 当事人 回应'],
    "social": ['"突发" "通报" "现场" 最新', '"赔偿" "合同" "家属" 当事人'],
    "viral_x": ['site:x.com (热议 OR 疯传 OR 离谱 OR 破防)'],
}


def build_search_queries(category: str = "all") -> list[str]:
    if category == "all":
        return [query for queries in SEARCH_QUERIES.values() for query in queries]
    if category not in SEARCH_QUERIES:
        raise ValueError("unknown search category")
    return list(SEARCH_QUERIES[category])


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"br", "p", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _Text(); parser.feed(value or "")
    return re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()


def source_time(value: str | None) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if dt.tzinfo else None


def _public_url(url: str, *, reddit_allowed: bool = False) -> None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("only public HTTPS URLs without credentials are supported")
    if host in {"x.com", "twitter.com", "t.co"} or host.endswith((".x.com", ".twitter.com")):
        raise ValueError("X URLs are discovery references, not scraping endpoints")
    if (host == "reddit.com" or host.endswith(".reddit.com")) and not reddit_allowed:
        raise ValueError("Reddit requires verified authorization and use rights")
    # Fixed public feed hosts are authenticated by HTTPS. Respect the user's
    # existing network routing: a local DNS filter can synthesize addresses
    # while their configured HTTPS proxy resolves the actual public host.
    if host in {"chinadigitaltimes.net", "t.me"}:
        return
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("private/local network destinations are not allowed")


def fetch_public(url: str, *, timeout: float = 12, reddit_allowed: bool = False) -> str:
    _public_url(url, reddit_allowed=reddit_allowed)

    class Redirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            _public_url(newurl, reddit_allowed=reddit_allowed)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    request = Request(url, headers={"User-Agent": "x-content-growth-engine/2 (public feed discovery)",
                                    "Accept": "application/rss+xml, application/atom+xml, application/json, text/html"})
    # No cookies, account session, proxy service, paid API or credentials.
    with build_opener(Redirect()).open(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("source exceeds 2MB discovery limit")
        return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def _material(title, text, url, published_at, captured_at, method, **extra):
    title, text = plain_text(title), plain_text(text)
    text = text or title
    digest = stable_hash({"title": title, "text": text})
    return {"material_id": "D" + stable_hash(url)[:16], "event_id": url, "topic": title,
            "text": text, "source": {"url": url, "published_at": source_time(published_at),
                "timestamp_precision": "SOURCE_TIMESTAMP" if source_time(published_at) else "UNKNOWN",
                "captured_at": captured_at, "evidence_text": text, "status": "SOURCE_CHECKED",
                "confidence": "ATTRIBUTED_SOURCE_NOT_INDEPENDENTLY_CORROBORATED",
                "check_scope": "PUBLIC_SOURCE_CONTENT_RETRIEVED_NOT_FACT_VERIFIED",
                "fact_verification": "UNVERIFIED", "event_time": None,
                "event_time_status": "NOT_INFERRED_FROM_REPOST_TIME", "method": method, **extra},
            "content_hash": digest, "review": {"novelty": "CHECKED_DISTINCT",
                "novelty_scope": "EXACT_TITLE_CONTENT_HASH_ONLY"}, "human_checked": False}


def parse_rss(body: str, feed_url: str, captured_at: str) -> list[dict]:
    if "<!DOCTYPE" in body.upper() or "<!ENTITY" in body.upper():
        raise ValueError("DTD/entity declarations are not supported")
    root = ET.fromstring(body)
    local = lambda tag: tag.rsplit("}", 1)[-1]
    output = []
    for node in root.iter():
        if local(node.tag) not in {"item", "entry"}:
            continue
        fields = {}; link = ""
        for child in node:
            key = local(child.tag)
            fields.setdefault(key, "".join(child.itertext()))
            if key == "link" and child.get("rel", "alternate") == "alternate":
                link = child.get("href") or child.text or ""
        if not link.startswith("https://"):
            continue
        # Keep excerpts bounded; archives remain discovery leads, not proof of deletion.
        excerpt = fields.get("encoded") or fields.get("content") or fields.get("description") or fields.get("summary") or ""
        host = urlsplit(feed_url).netloc.lower()
        family = "HACKER_NEWS" if host == "hnrss.org" else "GITHUB" if host == "github.com" else "CHINESE_MEDIA" if host.endswith("chinadigitaltimes.net") else "NEWS_MEDIA"
        output.append(_material(fields.get("title", ""), plain_text(excerpt)[:1600], link.strip(),
            fields.get("pubDate") or fields.get("published") or fields.get("updated"), captured_at,
            "PUBLIC_RSS", feed_url=feed_url, author=fields.get("creator") or fields.get("author") or None,
            family=family,
            timestamp_basis="FEED_PUBLICATION_TIME_NOT_CONFIRMED_EVENT_TIME"))
    return output


class _Telegram(HTMLParser):
    VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0; self.current = None; self.text_depth = None; self.view_depth = None
        self.output = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in self.VOID:
            self.depth += 1
        if attrs.get("data-post"):
            self.current = {"post": attrs["data-post"], "depth": self.depth, "text": [], "views": [], "time": None}
        if not self.current:
            return
        classes = attrs.get("class", "").split()
        if "tgme_widget_message_text" in classes: self.text_depth = self.depth
        if "tgme_widget_message_views" in classes: self.view_depth = self.depth
        if tag == "time": self.current["time"] = attrs.get("datetime")
        if tag == "br" and self.text_depth: self.current["text"].append("\n")

    def handle_data(self, data):
        if self.current and self.text_depth: self.current["text"].append(data)
        if self.current and self.view_depth: self.current["views"].append(data)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.text_depth == self.depth: self.text_depth = None
        if self.view_depth == self.depth: self.view_depth = None
        if self.current and self.depth == self.current["depth"]:
            self.output.append(self.current); self.current = None
        self.depth = max(0, self.depth - 1)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)


def parse_telegram(body: str, captured_at: str) -> list[dict]:
    parser = _Telegram(); parser.feed(body)
    output = []
    for row in parser.output:
        text = "".join(row["text"]).strip()
        if not text or not re.fullmatch(r"[A-Za-z0-9_]+/\d+", row["post"]):
            continue
        output.append(_material(text.splitlines()[0][:100], text[:1600], "https://t.me/"+row["post"],
            row["time"], captured_at, "PUBLIC_TELEGRAM", views_display="".join(row["views"]) or None,
            views=None, media_inspected=False, author=row["post"].split('/')[0], family="TELEGRAM",
            timestamp_basis="CHANNEL_MESSAGE_TIME_NOT_ORIGINAL_EVENT_TIME"))
    return output


def reddit_authorized(record: dict | None, communities: list[str], as_of: str) -> bool:
    if not isinstance(record, dict) or record.get("verified") is not True or not record.get("rights_reference"):
        return False
    expiry = source_time(record.get("expires_at"))
    return bool(expiry and datetime.fromisoformat(expiry.replace("Z", "+00:00")) > datetime.fromisoformat(as_of.replace("Z", "+00:00"))
                and set(communities) <= set(record.get("subreddits", [])))


def auto_discover_materials(*, rss_urls=None, telegram_channels=(), hacker_news=(), reddit_communities=(),
                            reddit_authorization=None, reddit_sort="top", seen_hashes=(), limit=20, as_of=None, fetcher=None) -> dict:
    """Collect bounded public leads. Exact dedup is never semantic novelty proof."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if reddit_sort not in {"top", "hot"}:
        raise ValueError("reddit_sort must be top or hot")
    now = as_of or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources = [("rss", url) for url in (DEFAULT_RSS if rss_urls is None else rss_urls)]
    for channel in telegram_channels:
        if not re.fullmatch(r"[A-Za-z0-9_]{3,64}", channel): raise ValueError("invalid Telegram channel")
        sources.append(("telegram", "https://t.me/s/"+channel))
    for route in hacker_news:
        if route not in HN_INDEXES: raise ValueError("Hacker News route must be top, best or new")
        sources.append(("hacker_news", HN_INDEXES[route]))
    errors = []; authorized = reddit_authorized(reddit_authorization, list(reddit_communities), now)
    if reddit_communities and not authorized:
        errors.append({"channel": "reddit", "reason": "HOLD_AUTHORIZATION_AND_USE_RIGHTS"})
    elif authorized:
        for community in reddit_communities:
            if not re.fullmatch(r"[A-Za-z0-9_]{2,64}", community): raise ValueError("invalid subreddit")
            query = "t=day&limit=20" if reddit_sort == "top" else "limit=20"
            sources.append(("reddit", f"https://www.reddit.com/r/{community}/{reddit_sort}.json?{query}"))
    if len(sources) > 12: raise ValueError("at most 12 source requests per run")
    materials = []; seen = set(seen_hashes); urls = set(); duplicates = 0; requests = 0
    for kind, url in sources:
        requests += 1
        try:
            body = fetcher(url) if fetcher else fetch_public(url, reddit_allowed=kind == "reddit" and authorized)
            if kind == "rss": rows = parse_rss(body, url, now)
            elif kind == "telegram": rows = parse_telegram(body, now)
            elif kind == "hacker_news":
                ids = json.loads(body); rows = []
                if not isinstance(ids, list): raise ValueError("invalid Hacker News index")
                for item_id in ids[:12]:
                    item_url = f"https://hacker-news.firebaseio.com/v0/item/{int(item_id)}.json"
                    try:
                        requests += 1
                        item = json.loads(fetcher(item_url) if fetcher else fetch_public(item_url))
                        if not isinstance(item, dict) or item.get("deleted") or item.get("dead") or item.get("type") != "story": continue
                        discussion = f"https://news.ycombinator.com/item?id={item['id']}"
                        target = item.get("url") if isinstance(item.get("url"), str) and item["url"].startswith("https://") else discussion
                        published = datetime.fromtimestamp(item["time"], timezone.utc).isoformat()
                        rows.append(_material(item.get("title", ""), plain_text(item.get("text") or item.get("title") or "")[:1600],
                            target, published, now, "OFFICIAL_HACKER_NEWS_FIREBASE", family="HACKER_NEWS",
                            discussion_url=discussion, hn_score=item.get("score"), hn_comments=item.get("descendants"),
                            author=item.get("by"), timestamp_basis="HACKER_NEWS_STORY_TIME_NOT_ORIGINAL_EVENT_TIME"))
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        errors.append({"url": item_url, "reason": str(exc)[:200]})
            else:
                packet = json.loads(body); rows = []
                for child in packet["data"]["children"]:
                    r = child["data"]
                    if r.get("over_18") or r.get("stickied"): continue
                    published = datetime.fromtimestamp(r["created_utc"], timezone.utc).isoformat()
                    rows.append(_material(r["title"], r.get("selftext", "")[:1600], "https://www.reddit.com"+r["permalink"],
                        published, now, "AUTHORIZED_REDDIT_JSON", score=r.get("score"), comments=r.get("num_comments"),
                        outbound_url=r.get("url"), author=r.get("author"), family="REDDIT"))
            for row in rows:
                if row["content_hash"] in seen or row["source"]["url"] in urls:
                    duplicates += 1; continue
                seen.add(row["content_hash"]); urls.add(row["source"]["url"])
                materials.append(row)
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
            errors.append({"url": url, "reason": str(exc)[:200]})
    # Source time, never capture time, determines freshness and ordering.
    materials.sort(key=lambda m: m["source"]["published_at"] or "", reverse=True)
    retained = materials[:limit]
    ages = [(datetime.fromisoformat(now.replace("Z", "+00:00"))-datetime.fromisoformat(m["source"]["published_at"].replace("Z", "+00:00"))).total_seconds()/3600
            for m in retained if m["source"]["published_at"]]
    return {"as_of": now, "materials": retained, "search_queries": build_search_queries(), "errors": errors,
            "collection": {"latest_run_completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "attempted_sources": requests, "unique_sources": len({urlsplit(m["source"]["url"]).netloc for m in retained}),
                "source_families": sorted({m["source"].get("family", "OTHER") for m in retained}),
                "collected": len(materials), "returned": len(retained), "duplicates": duplicates,
                "duplicate_ratio": duplicates/max(1, len(materials)+duplicates), "under24h": sum(0 <= a < 24 for a in ages),
                "between24and48h": sum(24 <= a < 48 for a in ages), "unknown_time": sum(not m["source"]["published_at"] for m in retained)}}


def import_search_leads(records: list[dict], *, captured_at: str) -> list[dict]:
    """Import browser/public-search leads only after the original page was opened.

    Search snippets remain discovery context. The material text must be copied
    from the checked public page and the record must preserve its query.
    """
    output = []
    for row in records:
        if not isinstance(row, dict): raise ValueError("search lead must be an object")
        url = row.get("target_url")
        _public_url(url)
        if row.get("original_page_status") != "ORIGINAL_PAGE_CHECKED":
            raise ValueError("search lead requires ORIGINAL_PAGE_CHECKED")
        text = row.get("original_page_text")
        if not isinstance(text, str) or len(text.strip()) < 10:
            raise ValueError("checked original page text required")
        output.append(_material(row.get("title", ""), text[:1600], url, row.get("published_at"), captured_at,
            "PUBLIC_SEARCH_ORIGINAL_PAGE", family="SEARCH_LEADS", discovery_query=row.get("query"),
            search_result_url=row.get("search_result_url"), search_snippet=row.get("snippet"),
            original_page_status="ORIGINAL_PAGE_CHECKED", timestamp_basis="ORIGINAL_PAGE_TIMESTAMP_OR_UNKNOWN"))
    return output
