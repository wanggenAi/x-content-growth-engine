"""Repository publication stop switch; dry runs never authorize a submission."""
import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import re

from .human_voice import stable_hash
from .reader_model import utc, window_measurement

CONTROL_PATH = Path(__file__).resolve().parents[1] / 'state' / 'publication_control.json'


def publication_control():
    try:
        state = json.loads(CONTROL_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'status': 'PAUSED', 'reason': 'MISSING_OR_INVALID_PUBLICATION_CONTROL'}
    return state


def new_queue(account='qiluo27808'):
    """A local ledger, never a remote scheduler or proof of publication."""
    if account != 'qiluo27808':
        raise ValueError('only the authorized account is supported')
    return {'account': account, 'interval_minutes': 20, 'items': [], 'slots': []}


def review_for_queue(queue, candidate, *, now, candidate_ref, feedback):
    from .publication_preflight import pre_publish_assert
    checked = utc(now)
    if queue.get('account') != 'qiluo27808':
        raise ValueError('UNAUTHORIZED_ACCOUNT')
    reviewed = utc(candidate['competition_as_of'])
    if not 0 <= (checked - reviewed).total_seconds() <= 86400:
        raise ValueError('COMPETITION_EXPIRED')
    pre_publish_assert(candidate, candidate['text'], dry_run=True)
    if candidate.get('production_holds'):
        raise ValueError('PRODUCTION_HOLD')
    if (feedback.get('candidate_id') != candidate['candidate_id']
            or feedback.get('publication_text_digest') != stable_hash(candidate['text'])
            or feedback.get('published_at_utc') is not None):
        raise ValueError('MATCHING_UNPUBLISHED_FEEDBACK_TEMPLATE_REQUIRED')
    digest = stable_hash(candidate['text'])
    for item in queue['items']:
        if (item['candidate_id'] == candidate['candidate_id'] or item['text_hash'] == digest
                or item['material_id'] == candidate['material_id']):
            raise ValueError('DUPLICATE_QUEUE_ITEM')
    item = {'candidate_id': candidate['candidate_id'], 'material_id': candidate['material_id'],
            'status': 'DRAFT', 'text': candidate['text'], 'text_hash': digest,
            'candidate_ref': str(candidate_ref), 'reviewed_at': now,
            'competition_as_of': candidate['competition_as_of'],
            'history': [{'status': 'DRAFT', 'at': now}, {'status': 'REVIEWED', 'at': now}],
            'post_url': None, 'published_at': None, 'scheduled_for': None,
            'feedback_24h': deepcopy(feedback)}
    item['status'] = 'REVIEWED'
    queue['items'].append(item)
    return item


def slot_check(queue, candidates, *, now, control=None):
    """One check per UTC :00/:20/:40 slot; missed slots are never backfilled.

    This function performs no external action and cannot mark SCHEDULED/PUBLISHED.
    A failed/unknown attempt remains locked until an actual receipt is reconciled.
    """
    from .publication_preflight import pre_publish_assert
    clock = utc(now)
    if queue.get('account') != 'qiluo27808':
        raise ValueError('UNAUTHORIZED_ACCOUNT')
    slot = clock.replace(minute=clock.minute // 20 * 20, second=0, microsecond=0).isoformat()
    prior = next((s for s in queue['slots'] if s['slot'] == slot), None)
    if prior:
        return prior
    if queue['slots'] and clock < utc(queue['slots'][-1]['checked_at']):
        raise ValueError('CLOCK_MOVED_BACKWARDS')
    policy = publication_control() if control is None else control
    result = {'slot': slot, 'checked_at': now, 'status': 'SKIPPED',
              'reason': 'NO_REVIEWED_CONTENT', 'candidate_id': None,
              'external_action': False}
    # Ambiguous submission blocks the whole account, even if other drafts exist.
    if any(i['status'] == 'FAILED' or i.get('delivery_violation') for i in queue['items']):
        result['reason'] = 'RECONCILE_UNKNOWN_SUBMISSION_BEFORE_RETRY'
    else:
        for item in queue['items']:
            if item['status'] != 'REVIEWED':
                continue
            result['candidate_id'] = item['candidate_id']
            try:
                candidate = candidates[item['candidate_id']]
                if stable_hash(candidate['text']) != item['text_hash']:
                    raise ValueError('QUEUED_TEXT_CHANGED')
                if not 0 <= (clock - utc(candidate['competition_as_of'])).total_seconds() <= 86400:
                    raise ValueError('COMPETITION_EXPIRED')
                pre_publish_assert(candidate, item['text'], dry_run=True)
            except (ValueError, KeyError, TypeError) as exc:
                item.update(status='SKIPPED', skip_reason=str(exc))
                item['history'].append({'status': 'SKIPPED', 'at': now, 'reason': str(exc)})
                result['reason'] = str(exc)
                continue
            try:
                if policy.get('status') != 'ACTIVE':
                    raise ValueError(policy.get('reason', 'PUBLICATION_PAUSED'))
                validate_cadence(queue, now=now, control=policy)
                # Live authorization, freshness, facts and exact-text gates still apply.
                pre_publish_assert(candidate, item['text'], publication_queue=queue)
                raise ValueError('EXTERNAL_CONFIRMATION_REQUIRED')
            except (ValueError, KeyError, TypeError) as exc:
                result['reason'] = str(exc)
            break
    queue['slots'].append(result)
    return result


def record_failure(queue, candidate_id, *, now, reason):
    utc(now)
    item = next(i for i in queue['items'] if i['candidate_id'] == candidate_id)
    if item['status'] != 'REVIEWED' or not reason.strip():
        raise ValueError('INVALID_FAILURE_TRANSITION')
    item.update(status='FAILED', failure_reason=reason)
    item['history'].append({'status': 'FAILED', 'at': now, 'reason': reason})
    return item


def check_spacing(queue, target, *, exclude=None):
    """Confirmed actual times and future official reservations both occupy slots."""
    clock = utc(target)
    for item in queue['items']:
        if item['candidate_id'] == exclude:
            continue
        value = item.get('published_at') if item['status'] == 'PUBLISHED' else item.get('scheduled_for')
        if value and abs((clock - utc(value)).total_seconds()) < 1200:
            raise ValueError('MINIMUM_20_MINUTE_INTERVAL')


def validate_cadence(queue, *, now, control):
    """Shared by the queue and final live preflight; no parallel gate/scorer."""
    clock = utc(now)
    if queue.get('account') != 'qiluo27808':
        raise ValueError('UNAUTHORIZED_ACCOUNT')
    if any(i['status'] == 'FAILED' or i.get('delivery_violation') for i in queue['items']):
        raise ValueError('RECONCILE_UNKNOWN_SUBMISSION_BEFORE_RETRY')
    if control.get('transport', {}).get('verified') is not True:
        raise ValueError('NO_VERIFIED_COMPLIANT_TRANSPORT')
    check_spacing(queue, now)
    history = control.get('account_history', {})
    if (history.get('complete') is not True
            or not 0 <= (clock - utc(history['checked_at'])).total_seconds() <= 300):
        raise ValueError('RECENT_ACCOUNT_HISTORY_UNKNOWN')
    times = history['published_at']
    if any(utc(t) > clock for t in times):
        raise ValueError('ACCOUNT_HISTORY_HAS_FUTURE_PUBLICATION')
    if any((clock - utc(t)).total_seconds() < 1200 for t in times):
        raise ValueError('MINIMUM_20_MINUTE_INTERVAL')
    # Conservative while account-specific verification/actual limits are unknown.
    if sum((clock - utc(t)).total_seconds() < 86400 for t in times) >= 50:
        raise ValueError('CONSERVATIVE_DAILY_LIMIT_50')


def record_confirmation(queue, candidate_id, receipt, *, now):
    """Import an agent-checked official receipt; caller must actually observe it.

    A local planner URL, proposed date or submit toast is not a receipt. Account
    screenshots/analytics stay private; only a safe evidence reference is stored.
    """
    clock = utc(now)
    item = next(i for i in queue['items'] if i['candidate_id'] == candidate_id)
    if item['status'] not in {'REVIEWED', 'FAILED', 'SCHEDULED'}:
        raise ValueError('INVALID_QUEUE_TRANSITION')
    if (receipt.get('agent_checked') is not True or receipt.get('provider') != 'X'
            or receipt.get('account') != queue['account']
            or receipt.get('text_hash') != item['text_hash']
            or receipt.get('observed_text') != item['text']
            or not receipt.get('evidence_ref')):
        raise ValueError('OFFICIAL_EXACT_TEXT_RECEIPT_REQUIRED')
    if not 0 <= (clock - utc(receipt['observed_at'])).total_seconds() <= 300:
        raise ValueError('STALE_OR_FUTURE_RECEIPT')
    status = receipt['status']
    updated = deepcopy(item)
    if status == 'SCHEDULED':
        if not receipt.get('official_schedule_id') or not receipt.get('scheduled_for'):
            raise ValueError('OFFICIAL_SCHEDULE_CONFIRMATION_REQUIRED')
        if utc(receipt['scheduled_for']) <= clock:
            raise ValueError('SCHEDULE_MUST_BE_FUTURE')
        if utc(receipt['scheduled_for']) - utc(item['competition_as_of']) > timedelta(hours=24):
            raise ValueError('SCHEDULE_EXCEEDS_REVIEW_VALIDITY')
        check_spacing(queue, receipt['scheduled_for'], exclude=candidate_id)
        updated['scheduled_for'] = receipt['scheduled_for']
    elif status == 'PUBLISHED':
        url = receipt.get('post_url', '')
        if not re.fullmatch(r'https://x\.com/' + re.escape(queue['account']) + r'/status/[0-9]+', url):
            raise ValueError('VERIFIED_OWN_POST_URL_REQUIRED')
        if any(i.get('post_url') == url and i['candidate_id'] != candidate_id for i in queue['items']):
            raise ValueError('DUPLICATE_POST_URL')
        published = utc(receipt['published_at'])
        if published > clock or published < utc(item['reviewed_at']):
            raise ValueError('INVALID_PUBLICATION_TIME')
        # Record reality even if X delivered late/too close; flag and stop further dispatch.
        try:
            check_spacing(queue, receipt['published_at'], exclude=candidate_id)
        except ValueError:
            updated['delivery_violation'] = 'MINIMUM_20_MINUTE_INTERVAL'
        updated.update(post_url=url, published_at=receipt['published_at'])
        updated['feedback_24h'].update(published_at_utc=receipt['published_at'], post_url=url,
                                       status='AWAITING_OBSERVATION',
                                       due_at_utc=(published + timedelta(hours=24)).isoformat(),
                                       **window_measurement(receipt['published_at'], None, '24h'))
    else:
        raise ValueError('ONLY_OFFICIAL_SCHEDULED_OR_PUBLISHED_RECEIPTS')
    updated['status'] = status
    updated['confirmation'] = dict(receipt)
    updated['history'].append({'status': status, 'at': now})
    item.clear()
    item.update(updated)
    return item
