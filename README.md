# 双轨内容发布 / Living Record

A 每20分钟（Asia/Shanghai :00/:20/:40）发现素材、比较候选、核事实、写一篇合格热点，通过 Codex Computer Use 发布到 X。B 接收作者明确批准的完整个人表达，独立按时间或尽快发布。两者共用轻量 SQLite 队列、发布记录和 OS 浏览器锁，不需要两条长期 Git 分支。

题材优先用户指定 Telegram 吃瓜线索、具体人物的冲突和转折，以及马斯克、黄仁勋、特朗普等名人的具体事件。普通产品/平台规则更新不作默认主菜。原话、感受和经历只能来自本人；不编造、侵私、消费受害者或靠色情血腥吸引点击。没有合格素材就记录原因，不凑数、不把旧闻包装成刚发生。

## 实现与运行

```sh
python3 -m growth_engine.discovery                  # 原有RSS + Telegram公开预览 + Reddit Atom
python3 -m growth_engine.handoff scan --root outbox --strict
python3 -m growth_engine.pipeline ingest            # 只导入符合审核/授权约定的成稿
python3 -m growth_engine.pipeline cycle             # 当前20分钟周期；记遗漏，不补发
python3 -m growth_engine.pipeline status
python3 -u -m growth_engine.pipeline executor       # 持有共享浏览器锁的交互租约
python3 -m growth_engine.pipeline pause             # 紧急暂停；resume解除，不重置未知状态
python3 -m unittest discover -s tests -v
```

只用 Python 标准库，无本地模型、GPU、付费API或新常驻服务。`state/publication.sqlite3` 保存两轨全文、来源、计划/实际时间、状态和帖子URL。`state/browser.lock` 用 flock 跨进程互斥；进程异常后 IN_FLIGHT 转 UNKNOWN，必须先查账号近期帖子，不能重试点击。`reports/candidates/`、失败 audit、私人材料、截图均在 gitignore 范围内。

**Python 不会点击 X，GitHub Actions 也不会。** 持久调度由 Codex app 原有 heartbeat 唤醒具备 Computer Use 的 agent；每次依照 [双轨规程](docs/DUAL_TRACK_RUNBOOK.md) 操作同一个执行器。需要电脑开机、联网、app运行、Chrome登录及工具权限。写好配置、一次实发、只读工具可用都不能单独证明持续自动发布已运行；真实状态见 [本次验收](docs/DUAL_TRACK_ACCEPTANCE.md)。

A 每20分钟；B 可每分钟检查新增/到期成稿，不生成思想，不占用 A 周期。两个唤醒只在实际执行期间占同一浏览器锁，不在对话里 sleep 冒充调度。休眠/断网恢复只执行当前周期，A 过期稿不积压补发。具体登录、验证码、账号或权限阻塞停止相应操作并记录，无限重试和绕过限制均不允许。

## B轨：ChatGPT → GitHub → Codex

准确入库路径：`outbox/ready/<post_id>.json`。格式沿用现有 `LIVING_RECORD_X_HANDOFF_V1`，新增 `track=B`、`allow_publication`、`scheduled_at`、`original_material` 和绑定全文的 `approved_content_sha256`。**只有 READY_FOR_CODEX + 允许公开 + 实际完成审核**才入队，普通聊天/备忘/草稿不入队；批准的稿件不逐篇重复索要授权。完整长文/完整串帖继续采用原有无损协议，不能默默缩短。

[不可发布格式示例](outbox/examples/b-not-publishable.json) 为 DRAFT/false，存放在 examples，绝不发布。[字段说明](outbox/README.md)。

公开仓库只存允许公开的原始材料和批准成稿。原话与整理稿分开；私人原话存在本机 `journal/<id>.json`，GitHub 只存 private_ref，不上传聊天记录和隐私。公开原话必须单独确认 public_approved。只讨论、不想公开时，不提交发布包。

历史 Ally 完整长文与 [真实回执](outbox/receipts/20261023-ally-full-record.json) 保留。旧 Ally 短稿仍为 HOLD/REJECTED。Airbnb 清洁新规帖虽已实发，但被作者否定为不吸引人的选题，保留准确回执，严禁作为正面范例。

旧 `python3 -m growth_engine digest` / `note` 和每小时 Actions 简报继续可用，作为发现与私人笔记工具，不决定20分钟发布频率。原则见 [FOUNDATION](docs/FOUNDATION.md)，可见发布核验见 [CODEX_PUBLISH](CODEX_PUBLISH.md)。
