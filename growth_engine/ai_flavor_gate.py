"""Deterministic Chinese AI-flavor signals for editorial review.

The detector is deliberately a review signal, not a claim about authorship.  It
scores repeated editorial templates, abstract conclusions and rhythm problems;
it does not reward typos, slang or low language quality.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Mapping


ABSTRACT_NOUNS = (
    "边界", "尊严", "权益", "价值", "认同", "选择权", "公平性", "社会意义",
    "现实处境", "群体结构", "公共讨论", "情绪价值", "道德责任", "制度安排",
)
URL_RE = re.compile(r"https?://\S+")

PATTERNS: dict[str, tuple[str, int]] = {
    "newsroom_residue": (r"(?:引发了广泛关注|网友们纷纷表示|这不禁让人深思|事情的真相究竟如何|在这个快节奏的时代|让我们拭目以待)", 15),
    "balanced_contrast": (r"(?:不是.{0,42}[，,]?而是|重要的不是.{0,42}[，,。！？]?而是|一方面.{0,42}另一方面)", 13),
    "abstract_conclusion": (r"(?:真正的问题是|更值得关注的是|这背后反映的是|换句话说|值得我们思考|这件事让我意识到|从某种意义上说|某种程度上|本质上|归根结底)", 10),
    "mechanical_transition": (r"(?:我能理解[，,。]?但是|救急我能理解[，,。]?但|看起来.{0,25}其实|首先.{0,25}其次.{0,25}(?:最后|再次)|值得注意的是)", 9),
    "summary_ending": (r"(?:所以.{0,36}|也许这就是.{0,36}|这才是.{0,36}|这说明.{0,36}|值得我们思考.{0,20}|没有标准答案.{0,20})$", 12),
    "author_verdict": (r"(?:也该|应该|不应该|必须|不能再|帮.{0,18}也要).{0,48}$", 16),
    "rhetorical_question": (r"(?:凭什么|难道|为什么|公平吗|你怎么看|大家觉得呢|这合理吗)[^。！？!?]{0,45}[？?]", 12),
    "abstract_value_chain": (r"(?:公平|边界|尊严|权益|选择权|价值|认同|社会意义).{0,18}(?:公平|边界|尊严|权益|选择权|价值|认同|社会意义)", 8),
    "mechanical_explanation": (r"(?:因为|因此|所以|这意味着|这说明|也就是说|换句话说).{0,42}(?:因为|因此|所以|这意味着|这说明|也就是说|换句话说)", 8),
    "fact_to_value_question": (r"(?:\d|小时|工资|工牌|考勤)[\s\S]{0,180}(?:公平|尊严|权益|边界|选择权|凭什么|为什么)[\s\S]{0,45}[？?]", 35),
}

FORCED_HUMANIZATION = re.compile(r"(?:卧槽|兄弟们|哈哈哈|哈哈哈哈|绝了|离谱了吧).*(?:卧槽|兄弟们|哈哈哈|哈哈哈哈|绝了|离谱了吧)|[!！]{3,}|[😂🤣😅😭🤡]{2,}")
QUESTION_END = re.compile(r"[？?]$")


@dataclass(frozen=True)
class AIFlavorReport:
    score: int
    severity: str
    matched_patterns: tuple[str, ...]
    pattern_counts: dict[str, int]
    sentence_stats: dict[str, Any]
    blocked: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["matched_patterns"] = list(self.matched_patterns)
        result["warnings"] = list(self.warnings)
        return result


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？!?\n]+", text) if part.strip()]


def _sentence_stats(text: str, sentences: list[str]) -> dict[str, Any]:
    lengths = [len(re.sub(r"\s+", "", sentence)) for sentence in sentences]
    if not lengths:
        return {"count": 0, "lengths": [], "mean": 0.0, "stdev": 0.0, "short_ratio": 0.0, "question_count": 0}
    mean = sum(lengths) / len(lengths)
    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    questions = len(re.findall(r"[？?]", text))
    return {
        "count": len(lengths),
        "lengths": lengths,
        "mean": round(mean, 2),
        "stdev": round(math.sqrt(variance), 2),
        "short_ratio": round(sum(value <= 12 for value in lengths) / len(lengths), 3),
        "question_count": questions,
    }


def analyze_ai_flavor(text: str | None) -> AIFlavorReport:
    """Return a stable report suitable for JSON, CI and the editorial gate."""
    text = text or ""
    analysis_text = URL_RE.sub("", text).rstrip()
    sentences = _sentences(analysis_text)
    counts: Counter[str] = Counter()
    score = 0
    for name, (pattern, weight) in PATTERNS.items():
        target = re.sub(r'[“「『\"].*?[”」』\"]', '', analysis_text) if name == "newsroom_residue" else analysis_text
        matches = re.findall(pattern, target, flags=re.IGNORECASE)
        if matches:
            counts[name] = len(matches)
            score += weight * min(len(matches), 2)

    stats = _sentence_stats(text, sentences)
    if stats["count"] >= 4 and stats["stdev"] <= 3.0 and stats["mean"] >= 10:
        counts["uniform_sentence_length"] += 1
        score += 10
    if stats["question_count"] >= 2:
        counts["repeated_rhetorical_question"] += 1
        score += 8
    abstract_count = sum(analysis_text.count(term) for term in ABSTRACT_NOUNS)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    abstract_density = abstract_count / max(chinese_chars, 1)
    if abstract_count >= 3 and abstract_density >= 0.025:
        counts["abstract_noun_density"] += 1
        score += 10
    paragraph_lengths = [len(p.strip()) for p in re.split(r"\n\s*\n", analysis_text) if p.strip()]
    if len(paragraph_lengths) >= 3 and len(set(round(value / 5) for value in paragraph_lengths)) <= 2:
        counts["uniform_paragraph_structure"] += 1
        score += 6
    if len(sentences) >= 6 and all(any(marker in sentence for marker in ("因为", "所以", "但是", "因此", "这")) for sentence in sentences[1:]):
        counts["over_explanation"] += 1
        score += 8
    forced = bool(FORCED_HUMANIZATION.search(analysis_text))
    if forced:
        counts["forced_humanization"] += 1
        score += 25

    score = min(100, score)
    severity = "HIGH" if score >= 45 else "MEDIUM" if score >= 25 else "LOW"
    warnings: list[str] = []
    if forced:
        warnings.append("forced_humanization_signals")
    if abstract_density >= 0.025:
        warnings.append("abstract_terms_are_a_signal_not_a_ban")
    blocked = severity == "HIGH" or forced
    return AIFlavorReport(
        score=score,
        severity=severity,
        matched_patterns=tuple(counts),
        pattern_counts=dict(counts),
        sentence_stats={**stats, "abstract_count": abstract_count, "abstract_density": round(abstract_density, 4),
                        "paragraph_lengths": paragraph_lengths},
        blocked=blocked,
        warnings=tuple(warnings),
    )


def ai_flavor_passes(report: AIFlavorReport | Mapping[str, Any], threshold: int = 44) -> bool:
    """Gate helper.  A low score never overrides other editorial gates."""
    score = report.score if isinstance(report, AIFlavorReport) else int(report.get("score", report.get("ai_flavor_score", 100)))
    blocked = report.blocked if isinstance(report, AIFlavorReport) else bool(report.get("blocked", False))
    return score <= threshold and not blocked

