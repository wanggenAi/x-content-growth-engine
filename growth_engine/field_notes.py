"""Honest field notes. Editorial review only: never send anything to X."""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

MODE = "LIFE_RECORD_V1"
KINDS = {"PERSONAL", "OBSERVED_SCENE", "PUBLIC_EVENT", "CONVERSATION", "IDEA"}
COMMERCIAL_INTENTS = {"NONE", "SPONSORED", "AFFILIATE", "SELF_PROMOTION"}
REVIEW_CHECKS = ("author_approved", "facts_and_uncertainty_checked", "privacy_checked",
                 "no_invented_experience", "no_manipulative_pressure")


def _has_text(value):
    return isinstance(value, str) and bool(value.strip())


def _valid_time(value):
    if not _has_text(value):
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.tzinfo is not None and timestamp.utcoffset() is not None
    except ValueError:
        return False


def _valid_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and not parsed.username and not parsed.password)
    except ValueError:
        return False


def text_hash(value):
    return sha256(str(value).encode("utf-8")).hexdigest()


def evaluate_note(note):
    """Fail closed without filling any content or pretending checks happened.

    Neither "viral" scores, mandatory emotional hooks, calls to action nor a
    forced moral/conclusion belong to this path. Human checkboxes are attestations,
    NOT computer-generated proof that an experience or a public claim is true.
    """
    if not isinstance(note, dict):
        return {"state": "HOLD", "reasons": ["NOTE_MUST_BE_OBJECT"],
                "ready_for_manual_publish": False, "external_action": False}
    reasons = []
    if note.get("mode") != MODE:
        reasons.append("WRONG_CONTENT_MODE")
    if not _has_text(note.get("note_id")):
        reasons.append("NOTE_ID_REQUIRED")
    if not _valid_time(note.get("observed_at")):
        reasons.append("TIMEZONE_AWARE_OBSERVATION_TIME_REQUIRED")
    if note.get("kind") not in KINDS:
        reasons.append("UNKNOWN_KIND")
    if note.get("origin") != "USER_DIRECT":
        reasons.append("USER_ORIGINAL_INPUT_REQUIRED")
    if not _has_text(note.get("raw_observation")):
        reasons.append("RAW_OBSERVATION_REQUIRED")
    if not _has_text(note.get("draft_text")):
        reasons.append("DRAFT_REQUIRED")
    if note.get("fixture_type") == "EXAMPLE_ONLY":
        reasons.append("EXAMPLE_CANNOT_PUBLISH")
    sources = note.get("source_urls", [])
    if not isinstance(sources, list) or any(not _valid_url(url) for url in sources):
        reasons.append("SOURCE_URLS_MUST_BE_HTTPS")
        sources = []
    if note.get("kind") == "PUBLIC_EVENT" and not sources:
        reasons.append("PUBLIC_EVENT_SOURCE_REQUIRED")
    commercial = note.get("commercial_intent", "NONE")
    if commercial not in COMMERCIAL_INTENTS:
        reasons.append("UNKNOWN_COMMERCIAL_INTENT")
    if commercial in {"SPONSORED", "AFFILIATE"} and not _has_text(note.get("commercial_disclosure")):
        reasons.append("COMMERCIAL_DISCLOSURE_REQUIRED")
    review = note.get("review", {})
    if not isinstance(review, dict):
        review = {}
    for check in REVIEW_CHECKS:
        if review.get(check) is not True:
            reasons.append("AUTHOR_REVIEW_REQUIRED:" + check)
    if note.get("kind") == "CONVERSATION" and review.get("conversation_privacy_handled") is not True:
        reasons.append("CONVERSATION_PRIVACY_REVIEW_REQUIRED")
    return {
        "mode": MODE, "note_id": note.get("note_id"),
        "state": "READY_FOR_MANUAL_PUBLISH" if not reasons else "HOLD",
        "ready_for_manual_publish": not reasons, "reasons": reasons,
        "text_sha256": text_hash(note.get("draft_text", "")),
        "external_action": False, "automatic_x_submission": False,
        "warning": "Editorial readiness is not proof of truth or X publication permission.",
    }


def blank_template():
    """Empty on purpose; no manufactured first-person experience."""
    return {
        "mode": MODE, "note_id": "", "observed_at": "", "kind": "PERSONAL",
        "origin": "USER_DIRECT", "raw_observation": "", "my_reaction": "",
        "my_thought": "", "what_i_did": "", "uncertainty": "",
        "source_urls": [], "draft_text": "", "commercial_intent": "NONE",
        "commercial_disclosure": "",
        "review": {**{name: False for name in REVIEW_CHECKS},
                   "conversation_privacy_handled": False},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Author-owned X field notes; no publishing")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("template")
    check = sub.add_parser("check")
    check.add_argument("path")
    check.add_argument("--require-ready", action="store_true")
    preview = sub.add_parser("preview")
    preview.add_argument("path")
    args = parser.parse_args(argv)
    if args.cmd == "template":
        print(json.dumps(blank_template(), ensure_ascii=False, indent=2))
        return 0
    try:
        note = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.cmd == "preview":
        print(note.get("draft_text", "") if isinstance(note, dict) else "")
        return 0
    result = evaluate_note(note)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.require_ready and not result["ready_for_manual_publish"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
