# 首篇 Ally：原文已审核，尚未发布

本轮从 main `9ef80bc43bbbe3b16bb428a1a8a791fbabdf9077` 开始。作者明确选择并授权 `20261023-ally-labels` 原文公开发布一次；没有缺少作者授权。这里只记录公开交接结果，不保存聊天全文。

## 内容核验

- `outbox/drafts/20261023-ally-labels.json` 与本次授权正文逐字一致，保留三段及两个空行，不作任何改写。
- UTF-8 正文 SHA-256：`fbf8b9ee18459663277481933fa5a8a8ca44a349ee7236f9d480c8538ce786f9`。
- [优酷综艺的嘉宾官宣](https://weibo.com/2/detail/5355672121644708)列出刘予宁及其公开账号；[微博电视的节目片段说明](https://weibo.com/2/detail/5356432346319742)将 Ally 对应至同一公开账号。两页均通过无认证公开 HTTPS 取得可见正文，核对节目名与人物对应；实际抓取时间和可见正文哈希见 `outbox/reviews/20261023-ally-labels.json`。
- 看剪辑、评论标签及自我判断变化属于作者提供并批准的观察，未冒充代理经历或独立调查，不推断评论具有代表性。正文没有营销指控、阴谋论、私人信息或新增攻击。
- 已生成 `outbox/ready/20261023-ally-labels.json`；原 drafts 文件是历史交接输入，不能直接发布。格式和 hash 通过不代表已经发布。

## 为什么没有提交 X

[X 官方自动化规则](https://help.x.com/en/rules-and-policies/x-automation)仍禁止非 API 自动化，包括脚本操作网站。本轮没有核实适用于代理页面提交的例外许可。按照作者「平台不允许执行就停在经过验证的交接阶段」的条件，状态为 `NOT_SUBMITTED_PLATFORM_RULES_HOLD`。

提交尝试 **0 次**，未操作 X 账号，未核验当前登录账号、重复帖、编辑器或账号字符限额，未取得帖子 URL。Computer Use 可用性没有在此平台规则阻塞后另行测试；不能把阻塞说成工具不可用。`outbox/receipts/20261023-ally-labels.json` **未创建**，没有成功回执可供 check-receipt 校验。重新处理时必须先解决平台许可，再核对账号、重复内容与原文，不能直接重试提交。

## 生产与验证

- `python3 -m unittest discover -s tests -v`：10 项通过。
- GitHub handoff 工作流的原命令 `python3 -m unittest tests.test_handoff -v`：6 项通过。
- `python3 -m compileall -q growth_engine tests`：通过。
- `python3 -m growth_engine.handoff scan --root outbox --strict`：ready 1、completed 0、blocked 0；此 blocked 仅表示文件校验错误，**不包含平台执行许可判断**。
- `python3 -m growth_engine digest`：北京时间 2026-10-23 10:28 完成，5 条未核实 RSS 线索，来源读取错误 0；输出在忽略的 `reports/hourly/`，不作为事实证实或发帖候选排名。
- 已手动启动现有 [hourly-living-record 运行](https://github.com/wanggenAi/x-content-growth-engine/actions/runs/39889888867)，结果 SUCCESS。原每小时排程、48 小时时效、72 小时去重与最多5条配置保留；旧本地 `x` 20分钟任务实际为 PAUSED，未恢复。
- 新增付费调用、依赖、常驻服务、数据库及自动发帖器均为0。旧排名、Top1、强制互动、20分钟发布不参与当前生产。

## 之后的一句话交接

作者说「把刚才那段发到 X」且所指文字唯一、无需改写时，即授权该段原文公开一次。ChatGPT 忠实整理；如需实质修改，先确认最终正文；GitHub 只保存批准的公开正文与必要来源、校验摘要；Codex 核实平台许可、账号、去重及原生页面后执行一次并独立核对回执。普通聊天和私人全文不进入 outbox。GitHub 提交不会自动唤起 Codex，也不保证平台当前允许执行。
