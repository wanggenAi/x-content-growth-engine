"""Local full-text search; no network, model, or API calls."""
import argparse
from .store import Store

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('query')
    a = p.parse_args()
    store = Store()
    try:
        for record in store.records('shenduhaowen'):
            body = store.root / 'bodies' / 'shenduhaowen' / f"{record['id']}.txt"
            if a.query.casefold() in (record['title'] + (body.read_text() if body.is_file() else '')).casefold():
                print(record['date_beijing'], record['title'], record['link'])
    finally:
        store.close()

if __name__ == '__main__':
    main()
