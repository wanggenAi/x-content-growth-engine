# 轻量内容竞争力 V4 — 2026-10-20

从最新远程 main `5c0c5d90d3f154fd2ecdbac1de34a38dc5dba175` 开始；本地 main 与其分叉，原有未推送历史保留。本轮独立分支从 origin/main 建立，不重置用户分支。先读控制、工作流、决策、状态、指定五个模块、V3产物和C390负例。不是重建采集器，也不是新增中文吸引力模型。

暂停开关原样保留：`PAUSED / CONTENT_QUALITY_REPAIR_DRY_RUN_ONLY`，`automatic_x_submission=false`。四小时采集计划未改，自动化未恢复，没有访问X、没有发布或互动。本轮十题只是内容编辑竞争，未满足既有生产raw30/deep20/families4；不能声称完整发布预检通过。

## 开源源码审查

三个项目本轮核对LICENSE，均MIT。只借鉴方法，独立实现轻量检查；没有复制源码、提示词、词库，没有运行上游程序或安装脚本，也没有引入上游运行系统。无软件副本分发；版权与MIT文本见各版本LICENSE。

| 项目及固定版本 | 实际读取 | 吸收与舍弃 |
|---|---|---|
| [x-agent-skill / 7822c29](https://github.com/Jakeschincariol/x-agent-skill/tree/7822c29b4aedbd400b9339839d3f59f3652b1317) | x-post的SKILL、count.py、hookscore.py、hooks.json；x-viral的SKILL、pull.py、swipe.py；x-audit的SKILL、audit.py；templates/voice.md、LICENSE | 首句先兑现、先比较策略；NFC/CJK权重/HTTP链接23权重；同账号自身中位数、连续普通帖与高帖比较、按曝光分母分开观察互动。保留来源与负例。 |
| [humanizer-chinese / 1d6c08e](https://github.com/jiji262/humanizer-chinese/tree/1d6c08e10fbfe0e1b36ac784834451c6aae0a92c) | README、SKILL、LICENSE；与V3已审版本一致 | 不重复引入模式词库；继续保护事实、语境和原有自然句。它是中文写作skill指引，无需安装运行系统。 |
| [yotta-humanize / 8bfa946](https://github.com/YottaMeta/yotta-humanize/tree/8bfa946e72c3a7e4b018eaa2d600dd270d1bdc75) | SKILL、README、package.json、LICENSE；与V3已审版本一致 | 确定性规则与需编辑判断的改写分开；其Python标准库引擎与Node安装包装均不接入，不叠第三个检测器。 |

x-agent的上述Python脚本使用标准库；没有需要移植的服务。`hookscore.py`使用英文分词、首字母大写、STAKES词表和21类英文模式，不能当中文兴趣模型。`swipe.py`按账号自身median和同一指标比较，但未匹配发帖年龄，也允许views缺失时用likes；`audit.py`的derive把部分缺值折成0。这两种处理都不移植。3倍、1.4倍或样本数阈值不构成因果证明，平台权重也不作为未来曝光承诺。没有执行pull.py或接X oEmbed。

voice.md强调用户真实样例与可使用的亲历证据。当前尚无用户认可的V3/V4正例，`approved_examples=[]`保留；不能把代理自评当作声音校准。口头禅无配额，不把作者的第一人称经历移给账号。

## 最小代码改动

- `human_voice.py`：继续接收draft_text/authored_text/locked_facts，保留HUMAN_STYLE_V2合同；引擎标为V4。干净稿不再为了两句一段而强制重排。写作交接明确四个读者问题，A直接信息差、B个人表达、C人的反差；不强塞口头禅。
- `content_review.py`：V4在原正文审查内要求四个定性答案和长度核对；不是新增分数。旧审查合同与STORY/CONTRAST/DISCUSSION回放保留；新旧策略不能混用，文本/来源/记忆hash、逐句证据、拒绝记录仍然有效。
- `x_native_style.py`：新增一个标准库长度函数，NFC、CJK双权重和显式HTTP链接23。不是完整twitter-text解析器；emoji、裸域名、国际化域名返回需编辑器核对，不能宣称精确适配。现有英文词表没有移植。
- `hunt.py`：原文+链接明确标为未原创素材，不能把表面检查PASS说成好稿；可送人工编辑与达到生产门槛分开，`topic_admitted`单列。生产unique Top1、后续prepare_candidate和pre_publish_assert没有放行捷径。
- `gen_default.json`：扩展V3现有声音指引，题材同池竞争；未新建评分模块、模型调用或数据流水线。

## 实际材料竞争与编辑取舍

本轮使用现有fetch_public/parse_rss一次性读取免费RSS，12个文章请求中10个成功。另两次分别连接关闭、公共地址校验拒绝，均未绕过或编造正文。对照193条既有发布记忆与388条campaign全表来源，未见精确来源重复；摘要与历史正文的最大相似度仅作人工复查线索，不冒充语义查重证明。逐页保存真实UTC捕获时间、原URL和少量原文证据；报道时间与事件时间分开。历史回忆不当作新发生。具体原文片段、十题八维理由、四个读者问题和15稿逐句审查在[来源包](../data/content_competition_v4_2026-10-20/source_packet.json)与[编辑记录](../data/content_competition_v4_2026-10-20/editorial_reviews.json)。

| 次序/题材 | 为什么可能值得读 | 取舍 |
|---|---|---|
| 1 相亲复盘 | 同场约会，两人记住的尴尬不同；具体到错名、鞋跟和球赛 | 选C，比较双方想改什么；A把两种尴尬先说完，B只是轻巧反应，C多一层人物差别。自述，不推断后来交往。 |
| 2 住房换陪伴 | 50小时抵1000元，四招一住；真正的细节是病后差4小时获准补 | 选B，从租金诱惑看到执行代价；A像服务说明，C问句可能被读成院方已起争执，故不用。不是普遍租房推荐。 |
| 3 动物照护 | 先重新学走路，后来成为导盲犬；防滑垫子连接两段照护 | 选C，养育者动作与新主人等待连起来；A偏康复时间线，B仍在解释小物件。不是病例核验或治疗建议。 |
| 4 古怪情人节礼物 | 两个素食者，真牛心、假血，收到者反而兴奋 | 三稿留档，不进最终三篇。靠惊奇打开却有恶心风险，艺术语境距离大；C的试探不能推广成关系建议。 |
| 5 1990年代夜班 | 餐饮客人从醉汉到警察、水兵，时间和口味很具体 | 三稿留档，不进最终三篇。叙事切口有变，但缺一个更强的结果；B仍接近作者见闻转述。旧事已标年代。 |
| 6 丧偶后的新关系 | 想再恋爱与育儿、对方忽冷忽热的真实代价 | 不写稿；短帖容易抹掉创伤前提，只有来信，没有独立核对。 |
| 7 新老人生活 | 外卖、Vlog、咖啡有日常接口 | 不写稿；原文是类别概括和倡议，缺一个具体人物及结果。 |
| 8 儿童礼物测试 | 可以观察孩子与成人选物差异 | 不写稿；页面有佣金利益、英国购买情境，当前未找到单个意外发现。 |
| 9 晴空颠簸 | 没云也会颠簸有认知差 | 不写稿；需一手航空研究复核，不能用旧事故制造当下恐惧。 |
| 10 柴油传言 | 车主有直接消费利益 | 不写稿；未复核国标，不能把合格产品要求泛化成所有站绝无问题。 |

这些分数与次序是同一Codex的编辑判断，不是独立盲评或浏览量预测。十题topic分数约23.5–73.25；导盲犬60.5低于62，也可送人工编辑，却不获生产admission。相亲69排住房73.25之前，是既有second-stage按首屏等指标裁决；未改权重来迎合稿件。

## 与实际旧稿相比

10月19日的[九稿](../data/human_style_v3_2026-10-19/nine_comparisons.md)与[新三题](../data/human_style_v3_2026-10-19/fresh_three.md)均原样保留。养老床位稿先用200平方米/155床位制造误解，再澄清术语，最后又解释一次；V4住房稿把可感知的时间交换、实际仅一人入住与病后补时放在一起，不靠概念误会吊胃口。旧虎稿只有距离稀奇和背景，V4狗稿保留身体动作与另一个人的等待。旧校园稿双线并排，V4相亲C只围绕同一个问题的不同答案展开。

每个新题还有一个本轮按新闻摘要方式实际写出的baseline与三版全文，在[15稿对照](../data/content_competition_v4_2026-10-20/drafts.md)。这些baseline明确标为本轮对照，不冒称旧系统早已产出的历史稿。C390的金额、低AI味和愤怒引语仍保留为失败参照；不把技术通过改写成用户认可。

## 推荐人工审核的三篇全文

### Dd73920ea4d1c6abc / C / 权重241/280

同一场相亲，男方想改约会时间，女方想换双鞋。

《卫报》10月17日栏目里，他下班后很累，还错过了球赛。她散场时鞋跟断了。

James把Michelle叫成Melissa，自己很尴尬，女方却没把它列为尴尬时刻。

他给7.5分，她给7分，都愿再见。

https://www.theguardian.com/lifeandstyle/2026/oct/17/blind-date-michelle-james

### D9abbf4c672da514a / B / 权重244/280

免房租挺诱人，细看还有差的4小时。

中青报10月20日报道，南宁一处养老院，陪老人50小时抵1000元房租。计划招4人，住进1人。

她9月忙工作，又重感冒，怕传染老人，少做4小时。院方让她10月补。

单人宿舍，入住有审核，服务也要记录。

https://www.chinanews.com.cn/sh/2026/10-20/10717558.shtml

### D2ed8c18c9e01bb7f / C / 权重218/280

养育者怕小狗滑倒，把地板铺上垫子。后来，这只狗去给别人带路了。

《卫报》10月19日刊登的回忆里，Orlando患破伤风后一度瘫痪，吃饭、走路重新学。

康复后它成为导盲犬。新主人视力受损，已经等了好几年。

https://www.theguardian.com/lifeandstyle/2026/oct/19/the-pet-ill-never-forget-orlando-was-paralysed-and-almost-died-then-became-the-perfect-guide-dog

## 尚未解决的内容弱点

仍以报道、栏目自述和回忆作材料，来源集中在中青报与卫报；没有账号本人可核对的独家经历，也未获用户验收。三篇适合轻量人情观察，但不代表账号已形成稳定立场。部分备选仍像顺口的摘要，尤其夜班题不够有结果。来源归因不可省掉，有些段落因此仍略书面；不能靠删掉边界换流畅。语义蕴含、幽默分寸和实际吸引力依靠编辑，Python的字面证据检查不能证明事实真伪。

## 真实反馈与下一次学习

实际重跑现有`scripts/backtest_reader_history.py`：21条历史观察，21条有累计views、4条有可见likes/replies/reposts，**0条有可靠捕获UTC时间，0条合格24h对照**；impressions/profile_visits/follows_attributed无值。私有逐帖数据继续ignored，只提交安全汇总。`data/viral_analysis/latest.json`仍是10月15日旧分析，verified_x_views=0、合格普通帖对照=0；不擅自覆盖成新结论。

曝光、点赞、回复、转发、主页访问、归因新增关注的当前可比结果均UNKNOWN。只在将来另获发布授权且采到真实窗口后，复用现有1h/6h/24h/72h/7d记录，分别计算有真实分母的互动与关注率。跨账号不直接比绝对量；同账号也须同年龄窗口、包含普通帖、保留反例，才讨论差异。C390等用户否定是保留的定性否决，不能被自动高分覆盖。没有公式升级，F01–F05仍HYPOTHESIS；真实流量增长尚未验证。

## 测试与资源

升级前132个unittest通过；本轮137个unittest、137个pytest通过，compileall和diff检查通过。pytest在临时隔离测试环境，生产依赖仍为0。隔离SQLite七条seed的import/audit命令正常执行，仍报告旧索引、未知作者规模和样本不足三项历史限制，不包装成生产审计全绿。旧V1/V2合同、V3九稿、盲测、事实漂移、source/hash、用户REJECT优先和暂停发布测试保留。新增测试验证自然段不乱改、CJK/NFC/链接权重及不支持格式不虚报适配、V4读者问题、新旧策略兼容、真实10题/15稿和篡改失效。

同一Mac、Python3.14、同一旧20题/9稿离线production_dry_run、7轮取中位数：旧0.32177秒/峰值34,635,776字节，新0.32105秒/峰值32,604,160字节。约-0.2%的耗时差属于测量噪声，不宣传性能提升；未见明显退化。该测量不包含网络或Codex写作等待。另有同一V3稿200次检查的7批基准，旧约0.128秒、新约0.109秒，仅供局部参考。

新增运行依赖0；没有GPU、本地模型、浏览器常驻、数据库、Docker、Node服务或定时大模型调用。已有采集脚本、频率、调度与publication_control文件内容不变。基准、失败及实际测试回执见[validation.json](../data/content_competition_v4_2026-10-20/validation.json)。

离线重放（复用193条原有发布记忆，不复制另一份）：

```python
import json
from pathlib import Path
from growth_engine.hunt import production_dry_run
p = Path("data/content_competition_v4_2026-10-20")
feed = json.loads((p / "source_packet.json").read_text())
reviews = json.loads((p / "editorial_reviews.json").read_text())
reviews["publication_memory"] = json.loads(Path(reviews["publication_memory_ref"]).read_text())["publication_memory"]
result = production_dry_run(feed, reviews)
assert result["publication_allowed"] is False
```
