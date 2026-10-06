# Own-post feedback learning loop

更新：2026-10-06。发布成功只是事件，不是成功指标。只有合法可见的本人账号数据，且 `human_reviewed: true`、证据引用和 UTC 观察时间齐全，才可进入学习表。

## 记录 schema

每个 own post 记录：`post_url`、`published_at_utc`、`post_age`、`text_media_type`、`source_type`、`topic`、`mechanism`、`primary_action`、`account_follower_baseline`，以及窗口 `1h`、`6h`、`24h`、`72h`、`7d`。每个窗口保存 `observed_at_utc`、`impressions/views`、`likes`、`replies`、`reposts`、`quotes`、`bookmarks`、`profile_visits`、`follows_attributed`、`account_follower_delta`、`link_clicks`；不可见就 `null`，不能用 0 代替。

保存证据来源（原生截图/AX/用户笔记）、人工核对状态和缺失原因。固定窗口按发布时间计算，未到窗口为 `PENDING`，不能提前比较。

## 学习字段与限制

在数据足够时计算：engagement/impression、reply/impression、share/impression、follow conversion proxy、24h normalized reach、相对近期账号基线的倍数/百分位。分母缺失时为 null。小样本、账号基线漂移、推荐分发、时间段、题材和媒体混杂都写进限制；这些指标不能证明 X 推荐因果。

## 负例与内容记忆

每轮同时保留高、普通、低浏览外部样本和自己的高/低表现；“结构相似但表现普通”的条目是负例，不能删除。账号内容记忆维护近 20/50/100 条的题材、冲突、hook、结尾、道德判断、人物关系、媒介和语义指纹，检测 `semantic/hook/ending/moral/conflict repetition`。记忆只用于 HOLD/FAIL 和设计对照，不自动评分或生成内容。
