"""Pure analysis and report formatting for read-only Telegram observations."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CHANNEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
BEIJING = ZoneInfo("Asia/Shanghai")
TOPICS = {
    "跨境B2B": ("出海", "跨境", "外贸", "供应链", "东南亚", "马来西亚", "工厂", "b2b", "海外客户", "出口", "合规", "电力设备", "工业检测"),
    "AI与算力": ("人工智能", "ai", "大模型", "算力", "gpu", "自动化", "agent", "云服务", "数据中心", "软件工具"),
    "商业机会": ("商业模式", "创业", "赚钱", "变现", "需求", "获客", "定价", "市场缺口", "客户", "现金流"),
    "投资与经济": ("投资", "股票", "a股", "估值", "宏观", "利率", "经济", "周期", "财报", "行业"),
    "人性与认知": ("人性", "心理", "社会", "欲望", "认知", "哲学", "思考", "道德", "人生", "情绪"),
}

def validate_channel(channel: str) -> str:
    value = channel.strip().removeprefix("@").removeprefix("https://t.me/")
    if not CHANNEL_RE.fullmatch(value):
        raise ValueError("频道必须是公开用户名，如 shenduhaowen")
    return value

def concise(text: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]

def classify(text: str) -> tuple[list[str], int]:
    data = (text or "").lower()
    matched = []
    score = 0
    for topic, terms in TOPICS.items():
        hits = sum(term.lower() in data for term in terms)
        if hits:
            matched.append(topic)
            score += min(hits, 5) * (3 if topic in ("跨境B2B", "商业机会") else 2)
    return matched, score

def make_record(*, channel: str, msg_id: int, date: datetime, caption: str, filename: str | None,
                file_size: int | None, pdf_text: str = "", pdf_pages: int = 0,
                pdf_error: str = "") -> dict:
    pdf_seen = bool(filename and filename.lower().endswith(".pdf"))
    topics, score = classify("\n".join((caption, filename or "", pdf_text)))
    if pdf_seen:
        score += 1
    local_date = date.astimezone(BEIJING).isoformat(timespec="minutes")
    title = filename or concise(caption, 90) or f"帖子 {msg_id}"
    return {
        "id": msg_id,
        "date_beijing": local_date,
        "title": title[:160],
        "link": f"https://t.me/{channel}/{msg_id}",
        "topics": topics,
        "score": score,
        "excerpt": concise(caption, 140),
        "pdf": pdf_seen,
        "pdf_read": bool(pdf_text),
        "pdf_pages_read": pdf_pages,
        "pdf_error": pdf_error[:140],
        "file_size": file_size,
        "analysis_basis": "标题/说明+PDF可提取文本" if pdf_text else "标题/说明（未读取附件正文）",
    }

def build_brief(channel: str, records: list[dict], generated: datetime, *, pdf_mode: bool) -> str:
    lines = [f"# Telegram 研究索引：@{channel}", "",
             f"生成时间（北京时间）：{generated.astimezone(BEIJING):%Y-%m-%d %H:%M}",
             f"检查消息数：{len(records)}；发现 PDF：{sum(r['pdf'] for r in records)}；成功提取 PDF 文本：{sum(r['pdf_read'] for r in records)}", "",
             "> 本报告是基于关键词的**阅读优先级索引**，不是 AI 深度分析或事实核查。文章观点、付费来源的授权状态均未核实。",
             "> 未读取 PDF 的条目不能按标题推断文章结论。报告不含 PDF 全文。", ""]
    if not records:
        lines += ["没有检索到符合日期范围的消息。可能是频道不可访问、指定区间无更新或权限不足。", ""]
    for r in sorted(records, key=lambda x: (-x["score"], -x["id"]))[:40]:
        title = r["title"].replace("\n", " ").replace("|", "/")
        lines += [f"### {title}",
                  f"- 日期：{r['date_beijing']}；评分：{r['score']}；主题：{'、'.join(r['topics']) or '未分类'}",
                  f"- 来源：{r['link']}",
                  f"- 内容依据：{r['analysis_basis']}"]
        if r["excerpt"]:
            lines.append(f"- 说明摘要：{r['excerpt']}")
        if r["pdf_error"]:
            lines.append(f"- PDF 状态：{r['pdf_error']}")
        lines.append("")
    if pdf_mode:
        lines += ["本地 PDF 文件和提取结果仅保存在被 gitignore 忽略的 data/、reports/ 目录；请勿公开转载受版权保护的全文。", ""]
    return "\n".join(lines)

def save_reports(output: Path, channel: str, records: list[dict], *, pdf_mode: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    (output / "brief.md").write_text(build_brief(channel, records, now, pdf_mode=pdf_mode), encoding="utf-8")
    (output / "posts.json").write_text(json.dumps({"channel": channel, "generated_at": now.isoformat(), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
