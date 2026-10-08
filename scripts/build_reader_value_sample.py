"""Build a small stratified V2 reader-value review sample.

The sample is deliberately bounded. It is a review set, not a replacement for
the historical annotation inventory and not a claim that any route caused reach.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from growth_engine.reader_model import VALUE_MODEL_VERSION, text_hash, validate_annotation

ANNOTATIONS = Path("data/reader_model_annotations_2026-10-08.json")
OUTPUT = Path("data/reader_value_stratified_sample_2026-10-08.json")
ANNOTATED_AT = "2026-10-08T00:00:00Z"
EXTERNAL_URLS = {
    "2103389699989450879": "https://x.com/jarvis11x/status/2103389699989450879",
    "2102998967034519923": "https://x.com/xieqianwan642/status/2102998967034519923",
    "2103825666156179753": "https://x.com/xupaopaogm/status/2103825666156179753",
    "2104046434941276402": "https://x.com/yihui_indie/status/2104046434941276402",
    "2103308533508997170": "https://x.com/0xlangeai/status/2103308533508997170",
    "2104379795761205451": "https://x.com/AI_DVD6/status/2104379795761205451",
    "2104945040208560623": "https://x.com/qihang_zeng6688/status/2104945040208560623",
    "2104470333193609533": "https://x.com/CharlesJHChen/status/2104470333193609533",
    "2101569201668505658": "https://x.com/nini_incrypto_/status/2101569201668505658",
    "2104945205841461259": "https://x.com/STANLEES4/status/2104945205841461259",
    "2103678695881986382": "https://x.com/niumoney/status/2103678695881986382",
    "2104793492996456735": "https://x.com/xiaoshunli/status/2104793492996456735",
    "2105136786083377330": "https://x.com/zbc2008/status/2105136786083377330",
    "2105206013783953894": "https://x.com/wangxiaolong188/status/2105206013783953894",
    "2104772155024293930": "https://x.com/lengs4189/status/2104772155024293930",
}


SPECS = [
    ("external", "2103389699989450879", "SOCIAL_CURRENCY", "SHARE", "AI 工具邀请码需要转给正在找入口的朋友。", "UNKNOWN"),
    ("external", "2102998967034519923", "EMOTIONAL_RESONANCE", "REPLY", "错过机会的叙述可能触发读者回看自己的经历。", "LOW"),
    ("external", "2103825666156179753", "CURIOSITY", "DWELL", "陌生的 AI 短剧收入案例留下可核对的机制问题。", "LOW"),
    ("external", "2104046434941276402", "EPISTEMIC_REWARD", "DWELL", "连续工作的 Agent 能力留下具体的机制和边界问题。", "LOW"),
    ("external", "2103308533508997170", "WONDER", "DWELL", "高上限工具额度本身构成惊奇入口。", "LOW"),
    ("external", "2104379795761205451", "UTILITY", "CLICK_RESOURCE", "清单和入口能在以后被具体使用。", "LOW"),
    ("external", "2104945040208560623", "KNOWLEDGE_CORRECTION", "REPLY", "面试资料的真实范围需要核对，不把夸张标题当事实。", "LOW"),
    ("external", "2104470333193609533", "OPINION_EXPRESSION", "REPLY", "对歌曲评论的不同解释留下真实意见空间。", "LOW"),
    ("external", "2101569201668505658", "SOCIAL_CURRENCY", "SHARE", "开源书链接有明确的转发对象和使用理由。", "LOW"),
    ("external", "2104945205841461259", "SELF_RELEVANCE", "REPLY", "政策预期与普通人的生活判断存在接口。", "MEDIUM"),
    ("external", "2103678695881986382", "STATUS", "DWELL", "职业路径的比较基准可能让读者核对差距。", "LOW"),
    ("external", "2104793492996456735", "HUMOR_ABSURDITY", "LIKE", "荒诞的日常比喻提供轻量情绪价值。", "LOW"),
    ("external", "2105136786083377330", "NARRATIVE_CLOSURE", "DWELL", "政策故事的后续结果是明确的追问。", "LOW"),
    ("external", "2105206013783953894", "COMPARISON", "REPLY", "宏观判断和个人处境之间存在可讨论的比较。", "LOW"),
    ("external", "2104772155024293930", "IDENTITY", "FOLLOW", "正在考虑转行的人可能把它看作同类经验。", "LOW"),
    ("own", "C016", "KNOWLEDGE_CORRECTION", "DWELL", "奖项名称的常识纠正即使与读者职业无关也有认知价值。", "LOW"),
    ("own", "C201", "OPINION_EXPRESSION", "REPLY", "数字是否公平留下解释和经验分歧。", "MEDIUM"),
    ("own", "C204", "SELF_RELEVANCE", "SHARE", "就业总量与分项的落差可让相关读者核对自己的处境。", "MEDIUM"),
    ("own", "C282", "IDENTITY", "FOLLOW", "家庭补助和兴趣选择构成特定生活阶段的身份入口。", "MEDIUM"),
    ("own", "C284", "EMOTIONAL_RESONANCE", "REPLY", "养老担忧可能唤起读者自己的家庭经验。", "MEDIUM"),
    ("own", "C289", "STATUS", "REPLY", "福利和合同期限让读者比较机会与代价。", "MEDIUM"),
    ("own", "C291", "CURIOSITY", "DWELL", "陌生工艺的时间成本留下具体的制作问题。", "LOW"),
    ("own", "C297", "COMPARISON", "REPLY", "生活费和联系成本可以引出不同家庭经验。", "MEDIUM"),
    ("own", "C338", "UTILITY", "SAVE_RETURN", "原始资料入口具备日后回查价值。", "LOW"),
    ("own", "C348", "WONDER", "LIKE", "罕见对象和细节本身提供惊奇。", "LOW"),
    ("own", "C350", "HUMOR_ABSURDITY", "LIKE", "具体荒诞场景提供轻量笑点。", "LOW"),
    ("own", "C353", "NARRATIVE_CLOSURE", "DWELL", "事件最后如何收束是读者继续看的理由。", "LOW"),
    ("own", "C355", "CURIOSITY", "SHARE", "熟悉品牌的收入组合留下解释缺口；这是发布后的新模型回顾。", "LOW"),
]


def profile(route: str, why: str, self_relevance: str) -> dict:
    route_entry = {"route": route, "strength": "HIGH", "cue": why, "reader_thought": "原来还有这种入口。"}
    value = {
        "model_version": VALUE_MODEL_VERSION, "claim_status": "HYPOTHESIS",
        "material_strength": "HIGH", "evidence_strength": "FULL_RECORDED_TEXT",
        "novelty_status": "CHECKED", "reader_value_routes": [route_entry],
        "dominant_reader_value_route": route, "why_reader_cares": why,
        "predicted_inner_response": "我想继续看清楚这件事。", "self_relevance": self_relevance,
        "acceptable_editorial_mechanism": "ACCEPTABLE_WITH_SOURCE_CHECK", "controversy_risk": "UNKNOWN",
        "curiosity": "HIGH", "curiosity_types": ["KNOWLEDGE_GAP"],
        "information_gap": "材料交付前后仍有一个可以核对的解释问题。",
        "narrative_progression": "先给出可核验事实，再交付过程或结果。",
        "expectation_violation": "MEDIUM", "opinion_activation": "MEDIUM", "opinion_space": "MEDIUM",
        "social_currency": "MEDIUM", "actionability": "MEDIUM", "utility": "MEDIUM",
        "resource_value": "MEDIUM", "source_accessibility": "MEDIUM",
        "activation_mechanisms": ["EXPLANATION_RIGHT"],
        "share_recipient": "对该主题有具体问题的朋友", "share_reason": "提供可核对的材料或入口。",
        "concrete_resource": "原始资料链接或步骤摘要", "future_usefulness": "下次需要时可以回查。",
        "identity_trigger": "经历相同生活阶段或兴趣的人", "comparison_basis": "同一标准下的机会、成本或结果。",
        "concrete_stakes": "时间、机会或判断成本", "comic_turn": "事实落点与日常预期形成轻微错位。",
        "closure_payload": "最终结果或关键解释", "opinion_space_reason": "事实交付后仍有真实经验差异。",
        "why_follow": "持续提供有来源的具体材料。", "repeatable_value": "每次交付一个可核验入口。",
        "account_positioning": "来源清楚的材料解读", "future_expectation": "下一条仍有具体来源和边界。",
        "correction": {"common_claim": "常见说法与材料表面印象相同。", "supported_correction": "原始来源显示需要更精确的说法。", "source_ref": "公开来源待逐项复核。"},
    }
    return value


def build() -> list[dict]:
    old = {row["entity_id"]: row for row in json.loads(ANNOTATIONS.read_text(encoding="utf-8")) if row["entity_kind"] == "own"}
    rows = []
    for kind, entity_id, route, action, why, self_relevance in SPECS:
        if kind == "own":
            source = old.get(entity_id)
            if not source:
                raise ValueError(f"missing own source {entity_id}")
            post_url = source["post_url"]
            refs = [{"url": post_url, "basis": "PUBLICATION_RECORD", "human_checked": True}]
            record = {"post_url": post_url, "published_at_utc": source.get("published_at_utc"),
                      "publication_text_digest": source.get("publication_text_digest")}
            evidence = "FULL_RECORDED_TEXT"
        else:
            post_url = EXTERNAL_URLS[entity_id]
            refs = [{"url": post_url, "basis": "PUBLIC_DISCOVERY_SUMMARY_ONLY", "human_checked": False}]
            record = {"post_url": post_url}
            evidence = "STRUCTURE_SUMMARY_ONLY"
        model = profile(route, why, self_relevance)
        model["evidence_strength"] = evidence
        record.update({"entity_kind": kind, "entity_id": entity_id, "version": 3,
                       "annotated_at_utc": ANNOTATED_AT, "annotator": "CODEX_STRATIFIED_REVIEW",
                       "annotation_note": "Bounded stratified review; route is an explicit hypothesis, not a measured cause.",
                       "source_refs": refs, "source_digest": text_hash(json.dumps(refs, sort_keys=True)),
                       "primary_action": action, "reader_model": model})
        validate_annotation(record)
        rows.append(record)
    return rows


if __name__ == "__main__":
    rows = build()
    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(rows), "external": sum(r["entity_kind"] == "external" for r in rows),
                      "own": sum(r["entity_kind"] == "own" for r in rows), "output": str(OUTPUT)}))
