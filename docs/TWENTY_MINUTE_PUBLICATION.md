# 2026-10-21 — 20分钟发布窗口：已授权，通道未就绪

用户正式授权本人 Gen @qiluo27808 的中文原创普通公开帖和官方排程，无需逐篇确认；全天每20分钟一个窗口，每窗口最多一篇，实际发布至少间隔20分钟。旧每日一篇、10分钟与必须发帖计划全部被覆盖。72是理论窗口数，不是平台额度或产量指标；弱稿、缺稿、过期、权限或平台限制均可跳过。

## 本次真实结果

- 起点 main `5f5a250de32ba8df64021a59f201389893119aa2`，PR19 MERGED，main CI39603152432 SUCCESS。
- 最新免费采集100条，4来源族，采集时间 `2026-10-21T13:47:35.864840Z`；96条源时间在48h内仅是采集观察，**不是100条完成深评**。采集频率仍4小时。
- 复核现有36条竞争池、22有效深评、30条源时间48h内、4族，唯一Top1仍是eMudhra弱私钥。保留原竞争时间 `2026-10-21T12:36:09.598620Z`，没有把重放时间充作新审核时间。
- 重新打开Scott Helme原文，HTTP200，捕获 `2026-10-21T13:47:41.847330+00:00`。旧稿把原文的Chrome/Firefox直接封锁扩大成全部主流浏览器，现已收紧；Safari的CT要求不冒充直接封锁。正文以明确事实收尾，删去泛化结论。ABC均重新逐句事实、文风检查，选A；三个版本不能算三个独立可发选题。
- Reader Model、Human Style V4/HUMAN_STYLE_V2、来源与事实、Editorial Gate、exact-text Prepublish dry-run PASS。human_checked=false，代理正文审核沿用已有明确豁免；不伪填人工核对。
- 本地队列1 REVIEWED、0 SCHEDULED、0 PUBLISHED；**没有首篇真实X链接**，未尝试绕过规则提交。唯一已检查窗口为UTC13:40—14:00，13:53:30检查，因通道不可用SKIPPED。质量不足跳过0次；其他未实际检查窗口不编造执行记录。

## 官方能力与阻塞

[X官方自动化规则](https://help.x.com/en/rules-and-policies/x-automation)明确禁止非API网站自动化。原生Computer Use不是平台规则的例外；本轮没有使用DOM、Cookie、隐藏请求或网页自动提交。

[X官方Media Studio说明](https://help.x.com/en/using-x/media-studio-faqs)确认服务器定时发布能力及精确时间选择，并列出1000个草稿/排程的错误上限；这不是已核实本账号拥有Media Studio或已排程的证据。本账号原生排程入口、认证状态与具体可用配额均UNKNOWN。已绑定的Chrome仅取得可见窗口状态，未进入发布编辑器。只有实际官方确认的排程才能关机继续，当前确认数量0。

[X当前英文限额页](https://help.x.com/en/rules-and-policies/x-limits)的current-limits段列出未认证账号每天50篇原创、另有半小时间隔限额；同页下方仍残留2400旧文字。不能据此承诺72篇。队列保守按滚动24h最多50篇检查；平台更低的账号限额始终优先，不绕限。

[X官方API价格](https://docs.x.com/x-api/getting-started/pricing)为按量收费，未核实已有零成本合规API通道，未购买credits。Metricool只执行只读账号连接查询，结果为无任何已连接社交网络；[其官方说明](https://help.metricool.com/x-twitter-access-in-metricool-2bt66)要求付费套餐和X附加项。本轮未连接新账号、扩大权限或支付。

所以控制仍PAUSED，原因已由旧“没有发布授权”改为`NO_VERIFIED_COMPLIANT_FREE_TRANSPORT`；user_publication_authorized=true。解除阻塞需要真实可用的免费官方合规通道证据，或由用户直接在X官方界面人工完成原生排程。不能仅切ACTIVE、去掉DRY_RUN_ONLY就提交。

## 最小工程

复用`publication_control.py`增加本地JSON队列，CLI `publication-queue`串行加锁、原子替换文件；没有新发布服务或新评分器。支持DRAFT→REVIEWED，本地时段SKIPPED；有实际失败/不明结果才记FAILED，阻塞全账号重试。只有代理实际观察并核对官方回执、本人账号、全文、哈希、时间和证据引用，才能人工导入SCHEDULED/PUBLISHED。回执导入器是证据校验合同，**自身不连接X也不能证明一个凭空填写的回执真实**。

窗口检查幂等，不追补。过期或改文稿标SKIPPED并继续后面的已审核稿，通道阻塞保留REVIEWED。实际发布时间与已确认排程均参与20分钟防撞；提交前还需完整、最近5分钟核对的账号历史。未知提交不得换稿绕过。若实际投递违反间隔，保存真实发布事实并标记delivery_violation，后续停止，不能丢掉坏结果美化记录。

队列检查**不会执行外部提交**，也不会自动把DRY_RUN_ONLY提升成可发状态。未来通道接入仍须使用现有live Prepublish并单独核验真实账号与平台限制；本轮没有宣称该接线已可用。

已有自动化`x`已由PAUSED/10分钟改为ACTIVE/20分钟，通知仍failed_runs_only。其提示词覆盖旧计划、只检查本地队列，相同通道阻塞保持静默；不反复采集、研究或打开X。它依赖Mac与Codex在线，不是云端发布服务；触发按现有心跳时钟，窗口账本按UTC :00/:20/:40归档，不声称官方按整点排程。无新增自动化、常驻浏览器/Node、GPU、模型、数据库、付费API或第三方运行依赖。恢复心跳相较此前PAUSED会增加每20分钟一次短检查和Codex用量，不能称总运行成本绝对为零。

## 复现与验证

```sh
python3 scripts/validate_publication_launch.py
python3 -m growth_engine publication-queue state/publication_queue.json data/private/publication_launch/production.json
# 只在第一次入队时增加 --enqueue；重复入队会拒绝。
python3 -m unittest discover -s tests -q
python3 -m pytest -q
python3 -m compileall -q growth_engine tests scripts
python3 -m growth_engine audit
```

`editorial_amendment.json`以原证据哈希引用PR19素材与深评，只保存被明确修正的话题；离线重放校验原证据未变，复用现有完整生产接口。完整重放产物放ignored private路径，未重复提交36条大产物；历史PR19原稿保留。

本地161 unittest、161pytest、compileall、修正稿完整dry-run通过。离线同一20题/9稿、7批中位0.320386875→0.312813792秒，峰值33,619,968→33,177,600字节。该基准不包括网络和Codex会话耗时；没有新增长驻运行负载。原4h采集workflow与C390负例哈希未变。

已有24h反馈模板原样复用；未发布无发布时间、无观测时间，全部指标null/UNKNOWN，未启动反馈窗。已知历史可比较24h样本0；现有audit仍提示搜索索引陈旧、作者规模未知、不能验证公式，不能宣称真实增长。详细回执见`data/publication_launch_2026-10-21/verification.json`，实际三稿见同目录`drafts.md`。PR/合并结果以最终回执为准。
