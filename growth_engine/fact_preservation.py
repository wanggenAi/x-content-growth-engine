"""Fact-lock checks for deterministic Human Voice rewrites."""

from __future__ import annotations

import re
from typing import Any, Mapping


HOLD_FACT_DRIFT = "HOLD_FACT_DRIFT"
_URL_RE = re.compile(r"https?://[^\s]+")
_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:[.,:]\d+)*(?:万|亿|元|块|岁|人|小时|点)?")
_DATE_RE = re.compile(r"(?:\d{4}年\d{1,2}月\d{0,2}日?|\d{1,2}月\d{1,2}日?|\d{4}-\d{1,2}-\d{1,2})")
_QUOTE_RE = re.compile(r"[\"“”『』「」].*?[\"“”『』「」]")
_CAUSAL_RE = re.compile(r"(?:因为|因此|导致|说明|证明|意味着|所以|为了|从而)")


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        result: list[str] = []
        for item in value.values():
            result.extend(_strings(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_strings(item))
        return result
    return [str(value)]


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _locked_values(locked_facts: Mapping[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for category, value in locked_facts.items():
        result[str(category)] = [_compact(item) for item in _strings(value) if _compact(item)]
    return result


def _tokens(text: str, pattern: re.Pattern[str]) -> set[str]:
    return set(pattern.findall(text or ""))


def check_fact_preservation(before: str, after: str, locked_facts: Mapping[str, Any] | None) -> dict[str, Any]:
    """Check locked entities, numbers, dates, quotations and source links.

    Missing locks are a review warning rather than an excuse to infer facts.  A
    supplied lock that disappears is always a HOLD, including when the wording
    around it was changed safely.
    """
    before = before or ""
    after = after or ""
    if not isinstance(locked_facts, Mapping):
        return {"passed": False, "changed_facts": [], "missing_facts": ["locked_facts"],
                "new_unverified_claims": [], "status": HOLD_FACT_DRIFT}
    grouped = _locked_values(locked_facts)
    missing: list[dict[str, str]] = []
    for category, values in grouped.items():
        for value in values:
            if value and value not in after:
                missing.append({"category": category, "value": value})

    changed: list[dict[str, Any]] = []
    locked_quotes = grouped.get("quote", []) + grouped.get("quotes", [])
    token_checks = (("number", _NUMBER_RE), ("date", _DATE_RE), ("url", _URL_RE))
    if locked_quotes:
        token_checks += (("quote", _QUOTE_RE),)
    for label, pattern in token_checks:
        before_tokens = _tokens(before, pattern)
        after_tokens = _tokens(after, pattern)
        removed = sorted(before_tokens - after_tokens)
        added = sorted(after_tokens - before_tokens)
        if removed or (label == "url" and added):
            changed.append({"category": label, "removed": removed, "added": added})

    before_sentences = { _compact(item) for item in re.split(r"[。！？!?\n]+", before) if _compact(item) }
    new_claims: list[str] = []
    for sentence in ( _compact(item) for item in re.split(r"[。！？!?\n]+", after) if _compact(item) ):
        if sentence not in before_sentences and _CAUSAL_RE.search(sentence):
            new_claims.append(sentence)

    passed = not missing and not changed and not new_claims
    return {
        "passed": passed,
        "changed_facts": changed,
        "missing_facts": missing,
        "new_unverified_claims": new_claims,
        "status": "PASS" if passed else HOLD_FACT_DRIFT,
    }

