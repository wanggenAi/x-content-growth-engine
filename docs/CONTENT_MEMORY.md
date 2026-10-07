# Account content memory

内容记忆是发布前的反重复约束，不是生成器或传播评分器。每次候选审核比较近 20、50、100 条已发布正文及研究候选，记录：主题、人物关系、冲突、首屏 hook、结尾、情绪、价值判断、媒体、payload 和语义指纹；分别输出 `semantic_repetition`、`hook_repetition`、`ending_repetition`、`moral_repetition`、`conflict_repetition`。

只要重复严重就 `HOLD` 或 `FAIL_REPETITIVE`，不能靠换几个词绕过。已有 C001–C353 是历史 corpus，不能删除或改写；当前不声称已经完成语义聚类，后续需在人工审核中逐步补齐指纹。


## 2026-10-07 去重失误修复

C354与C338同来源URL、同幸存者偏差交付；前次仅查C344–C353漏检，现已淘汰。以后先查全campaign来源URL和旧内容交付，再核近20/50/100条人物/机制/首屏/结尾，不能用字符低相似度或最近十条检查替代。用户认为C354兴趣不足，这属于编辑反馈，不作传播指标。
