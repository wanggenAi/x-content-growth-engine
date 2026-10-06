# Account content memory

内容记忆是发布前的反重复约束，不是生成器或传播评分器。每次候选审核比较近 20、50、100 条已发布正文及研究候选，记录：主题、人物关系、冲突、首屏 hook、结尾、情绪、价值判断、媒体、payload 和语义指纹；分别输出 `semantic_repetition`、`hook_repetition`、`ending_repetition`、`moral_repetition`、`conflict_repetition`。

只要重复严重就 `HOLD` 或 `FAIL_REPETITIVE`，不能靠换几个词绕过。已有 C001–C353 是历史 corpus，不能删除或改写；当前不声称已经完成语义聚类，后续需在人工审核中逐步补齐指纹。
