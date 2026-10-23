# Field Notes Workflow｜观世间，见自己

**2026-10-23 立心：** 不扮演“清醒的人”“道家博主”或“反人设博主”。只是一个普通人，记录自己在这个时代的经历、情绪、念头、错误、遗憾、改变和日常生活。可以希望获得传播和收入，但不以流量决定什么生活值得记录。

## 生产逻辑

作者的原始观察 → 区分事实、感受、转述、猜测 → 忠于原意的正文 → 作者审阅 → 事实与隐私检查 → 可选的人工发布 → 可选的真实反馈。

“观事、察机、观心、践行”是自问的方法，不是每篇必须遵循的结构。新闻、经济、AI、政治、战争、娱乐、宗教、街边闲聊和普通小事都能成为输入。老子、庄子、《阴符经》只是可选视角，不强行引经据典。

不要求：热点Top1、30条素材池、首次3秒钩子、煽动争论、情绪剧场、关注理由、一定给读者某种价值、所谓金句、固定频率或任何粉丝增长门槛。

## 数据与命令

运行下面命令查看**空白模板**：

    python3 -m growth_engine.field_notes template

填好 JSON 并保存至忽略的私人目录 data/private/，然后：

    python3 -m growth_engine.field_notes check data/private/my-note.json
    python3 -m growth_engine.field_notes check data/private/my-note.json --require-ready
    python3 -m growth_engine.field_notes preview data/private/my-note.json

核心字段：
- mode = LIFE_RECORD_V1
- note_id：唯一记录标识。
- observed_at：带时区的时间，例如 2026-10-23T09:03:00+08:00。
- kind：PERSONAL、OBSERVED_SCENE、PUBLIC_EVENT、CONVERSATION、IDEA。
- origin：USER_DIRECT；**必须真的由作者提供原始观察**，AI不能私自补成这个状态。
- raw_observation：作者原话或忠实原始笔记；my_reaction、my_thought、what_i_did、uncertainty 选填。
- draft_text：准备审核的文字。允许无结论的普通日常。
- source_urls：公共事件需要至少一个HTTPS来源；来源地址本身不是事实已核实的证明。
- commercial_intent：NONE、SPONSORED、AFFILIATE 或 SELF_PROMOTION；赞助/分销要有 commercial_disclosure。
- review：author_approved、facts_and_uncertainty_checked、privacy_checked、no_invented_experience、no_manipulative_pressure 都必须人工核实为 true；CONVERSATION 还需 conversation_privacy_handled=true。

若尚未完成作者检查，状态就是 HOLD，不可让 AI 默默勾选。若检查通过，状态为 READY_FOR_MANUAL_PUBLISH，**只意味着本地编辑就绪**，没有调用任何 X API、浏览器、排程或真实发帖。

## 不操纵他人

不能通过羞辱、攀比、嫉妒、情欲、恐惧或虚假的匮乏感诱导评论、关注和购买；不造问题再卖解药。商业合作可以有，但需要透明披露、面向真实需求，尊重读者的自主判断。也不必为反对操纵而扮演道德完人。

## 旧资产的地位

旧的 VIRAL_ADMISSION、Human Style、Reader Model、爆帖研究和历史发布队列继续保存用于历史研究、反例和核查，**不再决定新的 LIFE_RECORD_V1 是否值得表达**。旧的定时热点收集改为人工按需调用。旧的准备/排队功能不会自动把旧候选转换成真实第一人称记录。

本轮不迁移用户私人记录，不伪造以前的经历，不自动发表 X 内容。原账号发布开关保留 PAUSED。确需实际发帖时，必须单独完成作者确认、合规官方路径核验、正文hash绑定、账号身份和回执确认。
