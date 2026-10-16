"""Repository publication stop switch; dry runs never authorize a submission."""
import json
from pathlib import Path

CONTROL_PATH = Path(__file__).resolve().parents[1] / 'state' / 'publication_control.json'


def publication_control():
    try:
        state = json.loads(CONTROL_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'status': 'PAUSED', 'reason': 'MISSING_OR_INVALID_PUBLICATION_CONTROL'}
    return state
