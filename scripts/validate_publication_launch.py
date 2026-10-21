"""Replay a hash-bound editorial correction through existing V4 gates, offline.

This never refreshes competition time, collects material, authorizes or submits X.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from growth_engine.human_voice import stable_hash
from growth_engine.hunt import production_dry_run, render_editorial_drafts


def replay():
    amendment = json.loads(Path('data/publication_launch_2026-10-21/editorial_amendment.json').read_text())
    feed = json.loads(Path(amendment['base_feed']).read_text())
    reviews = json.loads(Path(amendment['base_reviews']).read_text())
    if stable_hash(feed) != amendment['base_feed_hash'] or stable_hash(reviews) != amendment['base_reviews_hash']:
        raise ValueError('BASE_EVIDENCE_CHANGED')
    material, record = amendment['material'], amendment['editorial_record']
    feed['materials'] = [material if m['material_id'] == material['material_id'] else m for m in feed['materials']]
    reviews['records'] = [record if r['material_id'] == record['material_id'] else r for r in reviews['records']]
    reviews.update(production_candidate=amendment['production_candidate'], reviewed_at=amendment['reviewed_at'])
    reviews['publication_memory'] = json.loads(Path(reviews['publication_memory_ref']).read_text())['publication_memory']
    return production_dry_run(feed, reviews)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/private/publication_launch/production.json'))
    args = parser.parse_args()
    result = replay()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    args.output.with_suffix('.md').write_text(render_editorial_drafts(result))
    print(json.dumps({'status': result['final_status'], 'top1': result['recommended_top1'],
                      'prepublish': result['production_pipeline']['prepublish'], 'publication_allowed': False}))
    if result['final_status'] != 'READY_CANDIDATE_DRY_RUN':
        sys.exit(1)
