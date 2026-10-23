# 时代观察 / Living Record

**2026-10-23 完全重构。** 新项目不再是爆款增长引擎，而是为一个普通人观察时代提供少量、具体、可追溯的人物事件。

每小时公开 RSS → 识别人物与行动 → 过去48小时 → 72小时去重 → 最多5件新事 → 简报。无需每条评论，也不强制哲学升华。人物可以是普通人、纠纷当事人、主播网红、恋综人物、企业家、政治人物、AI技术人物。

每小时的 GitHub Actions 运行名为 hourly-living-record；在 Actions → Run → Summary 查看简报，也可下载 Markdown/JSON 工件。GitHub 定时工作流可能延迟，不保证精确整点。

## 日常写作：从聊天直接交给 Codex

你和 ChatGPT 自然聊日常所见、新闻和自己的起心动念；**只有你明确想发 X 时**，ChatGPT 才根据对话梳理出自然、忠实的原创正文。正文经你确认后，可以通过已连接的 GitHub 写到 `outbox/ready/<post_id>.json`，再由你启动的 Codex + Computer Use 打开自己的 X 账号进行发布。Codex 需要按 [CODEX_PUBLISH.md](CODEX_PUBLISH.md) 核实正文、账号和发布回执。

- **聊天不等于公开**：不上传聊天全文、原始日志、私人心情日记、他人电话号码或未经批准的个人细节。只把确实准备公开的**最终正文**交给 GitHub。
- **仓库是公开的**：上传到 outbox 的正文在发布到 X 之前就可能被他人看到。敏感内容不要进入此仓库；若需私密草稿，先采用私人存储或私有仓库。
- 原始文字可以没有哲理、结论、爆点或互动钩子；AI 不得编造你的第一人称经历、情绪、引语和对第三人的指控。
- **交接不等于自动发布**：GitHub 提交不会自动启动 Codex 的 Computer Use 会话。Codex 需有用户可用的 Computer Use 环境并实际运行对应任务；本站的 GitHub Actions 只校验交接文件，不登录 X。
- 成功发布后，Codex 应仅在重新查看独立帖子详情、核对账号和全文后写入 `outbox/receipts/<post_id>.json`；失败/状态未知不反复点击「发布」。
- 不支持自动回复、互动、水军或强行按20分钟频率输出。不为发布而硬凑。

### 交接文件校验（免费、Python标准库）

```sh
python3 -m growth_engine.handoff scan --root outbox --strict
python3 -m growth_engine.handoff check outbox/ready/20261023-your-note.json
python3 -m growth_engine.handoff check-receipt outbox/ready/20261023-your-note.json outbox/receipts/20261023-your-note.json
```

见 [outbox/README.md](outbox/README.md) 的字段说明。状态 `READY_FOR_CODEX` 只代表经过审核并等待 Codex 处理，**绝不代表已经发布**。真实发帖仍取决于工具可用性、账号权限及平台规则。

## 每小时观察和私人笔记

```sh
python3 -m growth_engine digest
python3 -m growth_engine note --text "我今天看到的事与心情……" --kind personal
python3 -m unittest discover -s tests -v
```

通过 `config/sources.json` 修改订阅主题、条数和时效。无新增付费 API、数据库或常驻服务。默认是规则化 RSS 线索简报，不冒充大模型事实核实。RSS 标题只是发现线索；进一步的 AI 整理可以交给 Codex / ChatGPT 核查，不得捏造个人经验。

私人记录保存在被 gitignore 排除的 `journal/`。被删除的旧爆款分析和20分钟自动发布程序仍可通过 Git 历史回看，不影响当前生产。

更多原则见 [docs/FOUNDATION.md](docs/FOUNDATION.md)。
