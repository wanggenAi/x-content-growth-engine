"""Public, bounded discovery using existing RSS code; never fact-verifies leads."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from .observer import fetch_rss, feed_url, parse_rss, clean, key_for, now_utc, _time


class TelegramPreview(HTMLParser):
    def __init__(self, feed, at):
        super().__init__()
        self.source_feed, self.at = feed, at
        self.items, self.item, self.depth, self.text_depth = [], None, 0, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'div':
            if a.get('data-post') and 'tgme_widget_message' in a.get('class', '').split():
                self.item = {'title': '', 'link': 'https://t.me/' + a['data-post'],
                             'published_at': None, 'fetched_at': self.at.isoformat(),
                             'category_id': self.source_feed['id'], 'category': self.source_feed['name'],
                             'source': self.source_feed['name'], 'verification': 'UNVERIFIED_TELEGRAM_LEAD',
                             'engagement': None, 'engagement_observed_at': None}
                self.depth = 0
            if self.item:
                self.depth += 1
                if 'tgme_widget_message_text' in a.get('class', '').split():
                    self.text_depth = self.depth
        if self.item and tag == 'time':
            self.item['published_at'] = a.get('datetime')
        if self.item and tag == 'br' and self.text_depth:
            self.item['title'] += ' '

    def handle_data(self, text):
        if self.item and self.text_depth:
            self.item['title'] += text

    def handle_endtag(self, tag):
        if tag == 'div' and self.item:
            if self.text_depth == self.depth:
                self.text_depth = None
            self.depth -= 1
            if self.depth == 0:
                self.item['title'] = clean(self.item['title'])[:1600]
                self.item['key'] = key_for(self.item['title'])
                if self.item['title']:
                    self.items.append(self.item)
                self.item = None


def parse_atom(payload, feed, at):
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    result = []
    for item in ET.fromstring(payload).findall('a:entry', ns)[:25]:
        link = next((e.get('href') for e in item.findall('a:link', ns) if e.get('rel', 'alternate') == 'alternate'), '')
        title = clean(item.findtext('a:title', '', ns))
        if not title or urlparse(link).scheme != 'https':
            continue
        result.append({'title': title, 'link': link, 'source': feed['name'],
                       'category_id': feed['id'], 'category': feed['name'],
                       'published_at': item.findtext('a:published', None, ns) or item.findtext('a:updated', None, ns),
                       'fetched_at': at.isoformat(), 'key': key_for(title), 'verification': 'UNVERIFIED_PUBLIC_LEAD',
                       'engagement': None, 'engagement_observed_at': None})
    return result


def read_feed(feed, at, fetcher):
    url = feed_url(feed)
    result = {'id': feed['id'], 'url': url, 'observed_at': at.isoformat()}
    try:
        body = fetcher(url)
        if feed.get('kind') == 'telegram':
            parser = TelegramPreview(feed, at)
            parser.feed(body.decode('utf-8', errors='replace'))
            items = parser.items
        else:
            items = parse_rss(body, feed, at=at)
            if not items:
                items = parse_atom(body, feed, at)
        if not items:
            result.update(status='EMPTY_OR_UNREADABLE', count=0)
        else:
            result.update(status='READ', count=len(items))
        for item in items:
            item.setdefault('engagement', None)
            item.setdefault('engagement_observed_at', None)
        return items, result
    except Exception as exc:
        result.update(status='ACCESS_FAILED', count=0, error=type(exc).__name__ + ': ' + str(exc)[:160])
        return [], result


def collect(config='config/sources.json', out='reports/candidates', *, at=None, fetcher=None):
    at, fetcher = at or now_utc(), fetcher or fetch_rss
    feeds = json.loads(Path(config).read_text())['feeds']
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda f: read_feed(f, at, fetcher), feeds))
    leads, sources = [], []
    seen = set()
    for items, source in results:
        sources.append(source)
        for item in items:
            when = _time(item.get('published_at'))
            if when and at - timedelta(hours=48) <= when <= at + timedelta(minutes=5) and item['key'] not in seen:
                item['age_hours'] = round((at - when).total_seconds() / 3600, 2)
                item['timing_basis'] = 'SOURCE_PUBLICATION_TIME_EVENT_TIME_NOT_YET_VERIFIED'
                item['popularity'] = 'UNKNOWN'
                seen.add(item['key'])
                leads.append(item)
    leads.sort(key=lambda x: x['published_at'], reverse=True)
    packet = {'observed_at': at.isoformat(), 'sources': sources, 'candidates': leads,
              'count': len(leads), 'publication_triggered': False,
              'next_step': 'AGENT_COMPARE_POOL_READ_ORIGINALS_VERIFY_EVENT_TIME_AND_WRITE; zero acceptable'}
    folder = Path(out); folder.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(packet, ensure_ascii=False, indent=2) + '\n'
    (folder / (at.strftime('%Y%m%d-%H%M%S') + '.json')).write_text(encoded)
    (folder / 'latest.json').write_text(encoded)
    return packet


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='config/sources.json')
    p.add_argument('--out', default='reports/candidates')
    a = p.parse_args()
    result = collect(a.config, a.out)
    print(json.dumps({'count': result['count'], 'sources': result['sources'], 'packet': a.out + '/latest.json'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
