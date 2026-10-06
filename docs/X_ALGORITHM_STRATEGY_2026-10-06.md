# X 推荐机制：可用事实与待验证推断

检查日期：2026-10-06（UTC）。本页只引用 X 官方一手资料；线上 feature switch、模型和权重会变，不能把本页当作当前排名公式。

## FACT（官方公开）

- X Help Center 说明推荐覆盖 Home/For You、Explore、Notifications 等位置，使用多种兴趣与互动信号，没有公开承诺某一个信号固定权重：[Our approach to recommendations](https://help.x.com/en/rules-and-policies/recommendations)。页面也说明 For You 会包含未关注账号，并列举关注账号/Topic、自己点赞、网络中他人点赞和关注等信号。
- X 官方推荐系统总览仍把 Home Timeline Recommendations 列为独立系统：[Recommender Systems](https://help.x.com/en/resources/recommender-systems)。
- X 2023 官方透明度文章公开了推荐代码仓库，但不等于线上代码、参数或 feature switch 永久不变：[A new era of transparency](https://blog.x.com/en_us/topics/company/2023/a-new-era-of-transparency-for-twitter)。
- 官方页面明确存在“Not interested”反馈和防止有害内容被推荐的处理；这支持记录负反馈与可推荐性边界，不支持反推某个帖子会获得多少曝光。

## 代码与参数边界

`xai-org/x-algorithm` 的公开仓库/修订必须在每次正式实验前重新记录 commit 或 release；本轮没有把无法稳定读取的线上修订伪造成已核参数。若代码出现 predicted favorite、reply、repost/share、DM/copy-link share、dwell/click dwell、quote、follow、negative feedback、out-of-network、author diversity 或 candidate retrieval/ranking 字段，只能作为公开代码中的组件线索逐项标注，不能当成当前线上开关。

权重作用于模型预测概率/特征组合，不是“一个点赞等于几个曝光”的 raw-count 换算。项目不得从权重直接推出收益，也不得把高浏览样本的结构标签写成算法因果。

## INFERENCE / EXPERIMENTAL HYPOTHESIS

- **INFERENCE**：有具体素材、明确读者动作和真实信息增量，可能提高被读完、回复、分享或关注的机会；这是创作设计推断，不是算法保证。
- **HYPOTHESIS**：不同 primary action、题材强度和发布间隔是否改变相对账号基线，需在 `EXPERIMENT_PROTOCOL.md` 的固定窗口和反例下测试。
- **未知**：线上排名权重、作者规模校正、临时事件策略、任何单一行为的边际效果。本仓库不据此承诺曝光。
