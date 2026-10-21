# V4生产闭环实测 — 2026-10-21

从最新远程main `3f4c7e3340d2ccac7b09ed85e080d30a04c9b42f` 开始，基准CI39546711953 SUCCESS，146测试。最新用户要求：不开发V5，只接通真实采集到正式候选的闭环；允许工程、PR及CI后合并，禁止提交X。此前C390 REJECT、发布暂停、采集频率均保留。

## 断点与最小修复

1. hunt生产dry-run只生成来源/风格预览，`production_preflight_passed=False`写死，未调用现成prepare_candidate和pre_publish_assert。现在只有唯一胜出素材的已推荐版本且显式production_candidate编辑包齐全，才顺序调用这些合同。
2. Reader Model不是要再建模型，而是缺少真实编辑输入。新包由Codex逐项写读者价值假设、原文依据和正文上下文绑定；Python只检验。缺项、过期绑定、错题/换稿/换来源、用户拒绝均不能READY。
3. validate-hunt之前不展开publication_memory_ref；现在读取已有193条发布记忆供精确来源/事件及近似正文审核，缺失不伪造空记忆。
4. V4原创稿没有original_text时曾走legacy cleanup；现在V4稿明确走authored_text保留原句。没有新增检测器。

正式候选继续用HUMAN_STYLE_V2、READER_VALUE_V2、既有八维及source review。ranking代码和门槛未修改。约90行生产代码连接现有接口，没有依赖、服务、数据库或任务新增。

## 本轮新采集与竞争

现有免费collect-feed在12:25 UTC新取回100条；本轮打开36个候选对应公开页面，29个得到可读原文，7个无可用原文或付费，全部保留HOLD，不付费或绕过访问。另读作者链接的Mozilla事件单和公开研究说明；仅保留短证据摘录、URL、UTC时间及页面哈希。不是重放早间30条。

36独立原始素材，28条逐项编辑记录，**22条有效深评**，30条来源时间在48小时内（其中22条有效深评）；4族：中文媒体、国际媒体、HN、Telegram。来源族用于素材池覆盖，不是4个独立事实佐证。HN时间只标记分享发现，不伪称原始事件日期。已知过去的事件保留原日期或日期精度UNKNOWN，不用今日转载时间重置。

| 排名 | 题目 | 编辑分 | 题材准入 |
| --- | --- | --- | --- |
| 1 | 证书私钥竟然只是数字4 | 77.0 | 准入 |
| 2 | 嫌攻略太像，闭眼指地图真去了 | 79.5 | 准入 |
| 3 | 75岁大爷走红后熬夜回粉丝 | 73.0 | HOLD |
| 4 | 看到别人违规，有人会加码 | 62.75 | HOLD |
| 5 | 电影里的外墙消防梯为何变少 | 57.75 | HOLD |
| 6 | 学校多放一周，谁来带孩子 | 57.5 | HOLD |
| 7 | 香蕉变黑，反而适合做面包 | 57.25 | HOLD |
| 8 | 失恋后不听情歌，去了硬核现场 | 57.25 | HOLD |
| 9 | 电动车后轮藏20千克银粒 | 55.25 | HOLD |
| 10 | 给模型换客户国籍，漏洞率变了 | 54.5 | HOLD |

数字4稿77分、随机旅行稿79.5分，在现有小于5分的接近候选复审中，首屏同为100、反差100对75，因此数字4胜出。没有调权重迎合赢家。评分只是编辑假设，没有曝光预测含义。第三名75岁大爷因10月19日晚缺精确时间，被48小时边界否决，并未凑成三个正式候选。

权威媒体平淡对照：科技论坛开幕、青海办案统计均HOLD；原文在且重要，不等于读者停留价值。每条深评及强素材落选原因在editorial_reviews.json的selection_note；其他8条不可核验或未独立核实传闻的材料在source_packet.json保留具体hold原因。

## 实际文案比较

本轮先实际写出的摘要对照（不是声称旧系统曾生成此稿）：

> 研究者近日披露，eMudhra部分中间证书存在弱私钥问题，相关厂商已采取措施。这一事件说明安全检查需要更加完善。

它隐去最有价值的4，只剩领域术语与套话。本轮A把机构、私钥、4同时放在首句；B以误读数字的反应推进，但多一层理解；C先强调格式合规，讨论性强但抽象总结味更重。A/B/C均经两种实质不同开头对比、逐句来源审核；最终选A，没有为了口语配额加口头禅。全部原文在[实际三稿](../data/production_closure_v4_2026-10-21/drafts.md)。

### 最终候选全文（未发布）

给网站发安全证书的机构，有把私钥竟然是4。

Scott Helme在10月20日文章里核对eMudhra证书：本该是384位随机数，实际取值小到一个字节就装得下。另两把是56和115。

更新后的主流浏览器已阻断相关证书。格式检查都过，钥匙却简单成这样。

https://scotthelme.co.uk/eight-bits-of-trust-emudhras-ca-keys-cracked-in-milliseconds/

字符计数：246/280。词长检查仅现有NFC正文与显式HTTP URL权重合同，不冒充完整twitter-text或真实编辑器试贴。

## 每个阶段的真实状态

采集PASS → 36素材竞争PRODUCTION_WINNER → Codex三稿实写/对比PASS → source fact boundaries PASS → content review PASS → Reader Model语义绑定及路由审核PASS → HUMAN_STYLE_V2 PASS → Editorial Gate PASS → exact-text Prepublish dry_run PASS。

输出`READY_CANDIDATE_DRY_RUN`，内部沿用`READY_FOR_MANUAL_PUBLISH`合同，但`publication_mode=DRY_RUN_ONLY`、publication_allowed=false。**正式X提交资格仍没有：PAUSED且无本轮发布授权。** 实测非dry调用报PUBLICATION_PAUSED；即便开关ACTIVE，本候选仍被DRY_RUN_ONLY阻断。解除开关并不自动授权这份dry-run稿。

human_checked=false、agent_checked=true；沿用AGENTS.md明确记录的逐条正文人工审核豁免USER_AUTHORIZED_AGENT_REVIEW，作用范围仅正文代理审核，不是发布授权。未伪填人工核验。发布时仍需新的明确授权、刷新竞争时效、移交合格的可见人工发布路线并重新核对exact text；本轮不执行这些操作。

复现命令：

```sh
python3 -m growth_engine validate-hunt data/production_closure_v4_2026-10-21/source_packet.json data/production_closure_v4_2026-10-21/editorial_reviews.json --output /tmp/x-production-closure.json
```

输出完整JSON（包含正式候选池与所有合同）及Markdown，不向X提交。历史包无production_candidate仍可重放预览，但明确报PRODUCTION_CANDIDATE_REVIEW_REQUIRED，不能冒充完成闭环。

## 事实与内容仍有的弱点

明确显示10月20日原文日期，实验精确发生时间保持UNKNOWN，不能用发表时间充当实验时刻。具体4/56/115由研究者文章复现归因；Mozilla独立确认弱密钥可恢复，不是逐个数字的第二次本机验证。本轮没有执行攻击、下载安装工具或验证用户设备。主流更新浏览器已阻断不代表所有客户端均安全，正文不扩展建议或声称实际攻击发生。证书与384位仍有术语门槛；最后一句的反应也可能被真实读者认为普通。技术PASS不等于好内容或流量保证。

## 反馈与负载

现有历史21帖，带精确observed_at_utc的0条，固定24h合格0条；有views21条，likes/replies/reposts各4条，profile_visits和follows_attributed均0条有值。不能把不同时龄或未知观察时点的记录当实验。本轮未发布，准备的24h记录post_url/published_at/observed_at及所有指标均null，显示UNKNOWN；learning_eligible=false。只有未来真实发布后才按真实发布时间计算24h，保存实际观测时间和证据，错过窗口不回填。无定时任务、无自动抓X、公式无升级。

原有同一20题9稿基准7批中位：0.322098s → 0.299456s；峰值RSS 32,505,856 → 33,259,520B（约+0.72MiB）。小样本有运行抖动，不宣称加速效果。新36题完整审核约0.235502s，峰值33,423,360B。运行依赖新增0、常驻负载新增0、定时任务新增0。149 unittest /149pytest /compileall PASS；负例覆盖缺判断/错题/换版/换文/换来源/缺事实审核/权限豁免缺失/用户否定，保留原合同。

交付CI与合并收据另记录于validation.json的delivery，避免在审前捏造成功。
