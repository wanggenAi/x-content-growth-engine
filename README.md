# 时代观察 / Living Record

**2026-10-23 完全重构。** 新项目不再是爆款增长引擎，而是为一个普通人观察时代提供少量、具体、可追溯的人物事件。

每小时公开 RSS → 识别人物与行动 → 过去48小时 → 72小时去重 → 最多5件新事 → 简报。无需每条评论，也不强制哲学升华。人物可以是普通人、纠纷当事人、主播网红、恋综人物、企业家、政治人物、AI技术人物。

每小时的 GitHub Actions 运行名为 hourly-living-record；在 Actions → Run → Summary 查看简报，也可下载 Markdown/JSON 工件。GitHub 定时工作流可能延迟，不保证精确到整点。

本地运行：

    python3 -m growth_engine digest
    python3 -m growth_engine note --text "我今天看到的事与心情……" --kind personal
    python3 -m unittest discover -s tests -v

通过 config/sources.json 修改订阅主题、每轮条数和时效。无新增付费 API、数据库或常驻服务。**默认只做自动规则化 RSS 简报，不冒充大模型生成。** RSS 标题只是发现线索，没有独立核实。进一步 AI 整理可以把简报交给 Codex / ChatGPT 来查证和写作，但不能虚构用户的经历、感受和结论。GitHub Models 已停止服务，因此不依赖它。

不自动发 X；不恢复旧队列和旧20分钟发帖程序。私人记录位于被 gitignore 排除的 journal/。被删除的旧研究和代码可通过 Git 历史查看，不再影响当前生产。

参见 docs/FOUNDATION.md。