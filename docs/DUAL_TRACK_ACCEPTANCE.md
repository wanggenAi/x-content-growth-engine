# 双轨实施验收（2026-10-23）

## 已验证

- Python 标准库实现，离线回归 25 项通过；覆盖两轨排期入队、审批绑定、同事件/同稿/近似正文持久去重、跨进程浏览器锁、点击待定阻断、崩溃后 UNKNOWN 核验优先、登录阻塞紧急暂停、过期不补发和遗漏周期记录。
- `handoff scan --root outbox --strict`：3 条真实回执，无待发或无效包。B 无新成稿，没有制造个人观点或发测试帖。
- 真实定时只读任务在北京时间 20:24:37 调用了原生 Computer Use，读到 X 并确认 @qiluo27808。细节在 ignored `state/scheduled-runtime-probe.json`；公开仓库不保存浏览器日志/截图。单靠工具清单不作为验收。
- 20:17 Airbnb 帖虽已实发，但作者否定其吸引力；已记录为负面选题，不作为质量成功。
- 按作者最新选题纠正，20:33:02 正式发布特朗普/BBC 问询进展：[真实帖子](https://x.com/qiluo27808/status/2113609641556934690)。独立页面核对完整正文、账号、来源目标和时间，回执绑定正文 hash。
- 首帖结果回写曾遇 PTY 长行截断；执行器恢复后真实进入 RECONCILE_ONLY，核查独立页面后补写回执。增加文件短命令避免终端长行；没有再次点击发布。

## 实际读取

20:22 北京时间：DNYQWCG Telegram 5 条、iizuk Telegram 6 条、Reddit offbeat Atom 25 条、BBC World RSS 25 条、名人 Google News RSS 25 条、社会1条、政要24条、世界25条、AI7条；合并去重/时间过滤候选127条。people、streamers、business RSS 返回空，不能声称读到了文章。另实际补采 DNYQWCG 较早一页11条。以上数量为源解析数，不是真实性/热度证明。

Telegram 地址恢复自历史用户配置： https://t.me/DNYQWCG 、 https://t.me/iizuk 。当前无互动数据时记未知。剧组“今天道歉”线索查到原报道10月13日，排除旧闻；工厂食品视频未核实主体与语境，暂不发布。特朗普稿沿 BBC 全文与路透供稿核对，非冒称 Telegram 原帖。

## 持续运行的边界

调度使用 Codex app 本地 heartbeat，A 每20分钟，B 独立检查 GitHub 批准成稿，两者共享固定仓库和执行器。启用情况及下一次时间以应用实际状态为准，不能把本文件当作已启动的证据。电脑需醒着、联网、app运行、Chrome已登录及原生 Computer Use 权限有效；休眠后只处理后续当前周期，不集中补发。没有承诺每次必有合格素材或精确唤醒。

browser-harness Chrome 调试连接因 DevToolsActivePort 访问权限失败，原生 cua_repl Chrome 已实际发布及后台只读验收成功；没有绕过权限或读取 cookie。

B准确入库：`outbox/ready/<post_id>.json`。不可发布示例：`outbox/examples/b-not-publishable.json`，DRAFT、allow_publication=false、全部审批false。原话独立保留，公开须 public_approved，私人内容只存 ignored journal 引用。成功结果见 `outbox/receipts/<post_id>.json`。紧急暂停：`python3 -m growth_engine.pipeline pause`。

## 已启用的本机调度

北京时间20:36至20:37，已通过 app automation_update 实际更新既有 A heartbeat `x` 为 ACTIVE，周期为每小时 :00/:20/:40（北京时间），并创建独立 B heartbeat `x-b` 为 ACTIVE、每分钟接稿检查。已再次 view 并读取落盘状态确认，不以配置文件代替启用动作。只读检查 app 调度器实际状态：A next_run_nominal_at=2026-10-23 20:40:00+08:00、next_run_at=20:41:28+08:00（调度器存在偏移）；B 首次 next_run_at=20:37:55+08:00，随后约每分钟检查；实际唤醒仍受电脑/app状态和任务繁忙影响。20:40后的正式自动发布周期尚未在本验收时观察，不能声称长期每轮发帖已得到实测。此前真实后台原生CU只读验收已通过。
