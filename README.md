# 观世间，见自己｜X Content Growth Engine

2026年10月23日，我们为这个项目重新「立心」。

这是一个普通人生活在21世纪的真实记录。不塑造“清醒”“高人”“道家博主”或“反人设”形象；记录时代，也观察自己的起心动念。不必为了观众、商业或粉丝写出某种被期待的答案。

**入世做事，观照内心；尽力理解世界，也诚实地看见自己。**

## 新的默认路径

个人生活、日常对话、AI与科技、经济、国际新闻、文化娱乐、宗教、社会现象，都可作为素材。作者提供真实的观察和想法，AI可核实公共事实、辅助整理文字，但**不能虚构作者的第一人称经历、感觉和思考**。

新路线：真实素材 → 事实/感受/推断区分 → 文字整理 → 作者确认 → 隐私和商业伦理检查 → 选择是否人工发布。

- 不要求爆款评分、Top1竞争、强情绪、冲突、关注理由、评论诱导或固定发布量。
- 不要求每篇都解释古籍或得出结论。
- 允许普通、琐碎、不成熟、反复甚至后来被推翻的记录。
- 希望获得流量和收入是正常的，但不以煽动攀比、嫉妒、羞辱、恐惧或成瘾倾向来换取商业利益。
- 可以记录阅读和真实反馈，但数据不会替作者决定值得写什么。

### 本地使用（Python 3.10+，标准库）

    python3 -m growth_engine.field_notes template
    python3 -m growth_engine.field_notes check data/private/my-note.json
    python3 -m growth_engine.field_notes check data/private/my-note.json --require-ready
    python3 -m growth_engine.field_notes preview data/private/my-note.json
    python3 -m unittest discover -s tests -v

详细格式与审查边界：[真实记录工作流](docs/FIELD_NOTES_WORKFLOW.md)。

**隐私：** 不要把私人生活原始记录、截图、联系方式或私人谈话放进这个公开仓库。使用已被忽略的 data/private/ 路径，核对隐私后才决定是否公开文字。

## 旧增长引擎的处理

既有爆帖收集、内容研究、VIRAL_ADMISSION、Reader Model、Human Style、素材与历史发布数据**不删除、不篡改**。它们现在只是按需使用的研究工具，不能决定 LIFE_RECORD_V1 的表达方向。

旧 viral-hunt 定时采集已改为手动触发。旧的发布候选不得因通过历史流量门槛而直接取得新路线的发布许可。

**当前实际发帖仍为 PAUSED。** 新的 field_notes.py 只能审稿和预览，不能操作 X。当前没有经过核实的自动发布通道，也没有任何此次重构产生的实际发帖或增长结果。

历史研究入口保留在 growth_engine 的现有命令以及 docs/ 旧档案中。最新治理以 [项目愿景](docs/PROJECT_VISION.md)、[当前控制状态](docs/CURRENT_CONTROL_STATE.md)、[工作流](docs/FIELD_NOTES_WORKFLOW.md) 为准。
