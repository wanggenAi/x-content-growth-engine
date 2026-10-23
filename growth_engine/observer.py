"""Hourly person-and-action leads. No publishing, no paid APIs, no invented opinions."""
from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

UTC = timezone.utc
ACTOR = re.compile(r"男子|女子|女孩|男孩|孩子|学生|父母|父亲|母亲|家长|老人|夫妻|邻居|外卖员|司机|员工|工人|店主|主播|网红|博主|嘉宾|明星|演员|歌手|企业家|老板|CEO|科学家|警察|医生|马斯克|黄仁勋|特朗普|习近平|普京|泽连斯基|孙宇晨|陈泽|Trump|Musk|Xi|Putin|Zelensky|Jensen Huang|worker|student|child|mother|father|woman|man|streamer|creator|founder|president|researcher", re.I)
ACTION = re.compile(r"说|表示|回应|宣布|发布|被|遭|称|发现|救助|帮助|起诉|举报|赔偿|拒绝|质疑|道歉|争论|获得|失去|遇|做|发生|拍|直播|停播|投诉|维权|逮捕|调查|判决|离职|辞职|任命|推出|参与|会见|采访|解释|曝光|救出|says?|said|announces?|launches?|meets?|rescues?|helps?|wins?|loses?|sues?|arrested|criticizes?|shares?|quits?|reports?|faces?|reveals?|speaks?|joins?", re.I)


def now_utc():
    return datetime.now(UTC)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))).strip()


def normalize(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", clean(text).lower())[:110]


def key_for(title):
    return hashlib.sha256(normalize(title).encode("utf-8")).hexdigest()[:24]


def feed_url(feed):
    if "url" in feed:
        parsed = urlparse(feed["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("RSS URL must be HTTPS")
        return feed["url"]
    language = feed.get("locale", "zh-CN")
    hl, gl, ceid = ("en-US", "US", "US:en") if language == "en-US" else ("zh-CN", "CN", "CN:zh-Hans")
    return "https://news.google.com/rss/search?q=" + quote_plus(feed["query"]) + "&hl=" + hl + "&gl=" + gl + "&ceid=" + ceid


def fetch_rss(url):
    request = Request(url, headers={"User-Agent": "LivingRecord/1.0 (public RSS reader)"})
    with urlopen(request, timeout=12) as response:
        return response.read(1_500_000)


def parse_rss(payload, feed, *, at=None):
    at = at or now_utc()
    root = ET.fromstring(payload)
    result = []
    for item in root.findall(".//item")[:25]:
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        if not title or urlparse(link).scheme != "https":
            continue
        source = clean(item.findtext("source"))
        if not source and " - " in title:
            title, source = title.rsplit(" - ", 1)
        try:
            published = parsedate_to_datetime(item.findtext("pubDate")).astimezone(UTC)
        except (TypeError, ValueError, IndexError):
            published = None
        if published and published > at + timedelta(minutes=30):
            continue
        result.append({
            "title": title, "link": link, "source": source or "未标注",
            "category": feed["name"], "category_id": feed["id"],
            "published_at": published.isoformat() if published else None,
            "fetched_at": at.isoformat(), "verification": "UNVERIFIED_RSS_LEAD",
            "key": key_for(title),
        })
    return result


def _time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (TypeError, ValueError, AttributeError):
        return None


def person_action(story):
    title = story.get("title", "")
    return bool(ACTOR.search(title) and ACTION.search(title))


def select(stories, seen, *, at=None, limit=5, max_age_hours=48):
    at = at or now_utc()
    if not 1 <= limit <= 8:
        raise ValueError("limit outside 1..8")
    candidates = []
    for story in sorted(stories, key=lambda s: s.get("published_at") or "", reverse=True):
        when = _time(story.get("published_at"))
        if not when or when > at + timedelta(minutes=30) or at - when > timedelta(hours=max_age_hours):
            continue
        if not person_action(story) or story["key"] in seen:
            continue
        if any(SequenceMatcher(None, normalize(story["title"]), normalize(other["title"])).ratio() >= .83 for other in candidates):
            continue
        candidates.append(story)
    chosen, category_seen = [], set()
    for story in candidates:
        if story["category_id"] not in category_seen:
            chosen.append(story)
            category_seen.add(story["category_id"])
            if len(chosen) == limit:
                return chosen
    for story in candidates:
        if len(chosen) >= limit:
            break
        if story not in chosen:
            chosen.append(story)
    return chosen


def seen_recent(path, at, cooldown_hours):
    try:
        entries = json.loads(Path(path).read_text(encoding="utf-8")).get("entries", {})
    except (OSError, ValueError, TypeError):
        entries = {}
    cutoff = at - timedelta(hours=cooldown_hours)
    return {k: when for k, stamp in entries.items() if (when := _time(stamp)) and when >= cutoff}


def markdown_brief(selected, *, at, errors):
    tz = timezone(timedelta(hours=8))
    lines = ["# 时代观察｜" + at.astimezone(tz).strftime("%Y-%m-%d %H:%M（北京时间）"), "",
             "本轮最多五件具体人物事件。这不是任务清单；可以只看、不评论，也可以一件都不写。", ""]
    if not selected:
        lines.append("本轮没有符合条件的新人物事件。不凑数。")
    for index, story in enumerate(selected, 1):
        when = _time(story.get("published_at"))
        date = when.astimezone(tz).strftime("%m-%d %H:%M") if when else "未知"
        lines += ["## " + str(index) + ". [" + story["category"] + "] " + story["title"], "",
                  "来源线索：[" + story["source"] + "](" + story["link"] + ") · 发布时间（北京）" + date, "",
                  "边界：此为 RSS/聚合标题，未经独立核实。原报道与事件细节需要进一步核验；不可据此推断动机。", ""]
    if errors:
        lines.append("来源读取失败：" + str(len(errors)) + " 个；本次覆盖不完整。")
    lines.append("随时可以不写、不评、不发布。")
    return "\n".join(lines) + "\n"


def build_digest(config_path="config/sources.json", out="reports/hourly", state="state/seen.json",
                 *, at=None, fetcher=None):
    at = at or now_utc()
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    limit = int(config.get("max_items_per_hour", 5))
    age = int(config.get("max_age_hours", 48))
    cooldown = int(config.get("cooldown_hours", 72))
    if not 1 <= limit <= 8 or not 1 <= age <= 168 or not 1 <= cooldown <= 720:
        raise ValueError("invalid digest bounds")
    seen = seen_recent(state, at, cooldown)
    fetcher = fetcher or fetch_rss
    leads, errors = [], []
    for feed in config["feeds"]:
        try:
            leads.extend(parse_rss(fetcher(feed_url(feed)), feed, at=at))
        except (OSError, ValueError, TimeoutError, ET.ParseError) as exc:
            errors.append({"feed": feed["id"], "error": type(exc).__name__ + ": " + str(exc)[:180]})
    chosen = select(leads, seen, at=at, limit=limit, max_age_hours=age)
    for story in chosen:
        seen[story["key"]] = at
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = at.strftime("%Y%m%d-%H%M")
    md = markdown_brief(chosen, at=at, errors=errors)
    packet = {"generated_at": at.isoformat(), "items": chosen, "errors": errors, "count": len(chosen),
              "summary_method": "DETERMINISTIC_RSS_HEADLINE_BRIEF_NOT_AI_INFERENCE",
              "automatic_x_submission": False, "publication_triggered": False}
    (folder / (stamp + ".md")).write_text(md, encoding="utf-8")
    (folder / (stamp + ".json")).write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "latest.md").write_text(md, encoding="utf-8")
    (folder / "latest.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    seen_file = Path(state)
    seen_file.parent.mkdir(parents=True, exist_ok=True)
    seen_file.write_text(json.dumps({"entries": {k: v.isoformat() for k, v in seen.items()}}, indent=2) + "\n", encoding="utf-8")
    return {"count": len(chosen), "errors": errors, "markdown": md, "output": str(folder / (stamp + ".md"))}


def save_note(text, kind="personal", out="journal", *, at=None):
    if kind not in {"personal", "seen", "thought"} or not isinstance(text, str) or not text.strip():
        raise ValueError("a real observation and valid kind are required")
    at = at or now_utc()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    path = folder / (at.strftime("%Y%m%d-%H%M%S") + "-" + suffix + ".md")
    path.write_text("# 私人观察\n\n" + at.isoformat() + "\n\n" + text.strip() + "\n", encoding="utf-8")
    return str(path)
