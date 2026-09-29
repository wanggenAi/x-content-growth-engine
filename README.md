# X Content Research & Growth Engine

面向单人中文 X 创作者的本地研究工作台。目标是把真实帖子发现、对照研究、独立素材、人工创作与发布后反馈连成可复查的闭环。当前仅完成首批数据来源验证和样本库基础能力；没有经过验证的“爆款公式”。

## 运行

需要 Python 3.10+，不需要 API 密钥或额外付费依赖。

```sh
python3 -m growth_engine init
python3 -m growth_engine import data/seed_x_observations.json
python3 -m growth_engine report
python3 -m growth_engine audit
python3 -m unittest discover -s tests -v
```

默认数据库为 `data/research.sqlite3`（不提交 Git）；`--db 路径` 可指定位置。导入可重复执行，按 X 帖子 ID 去重，保留首次发现时间并更新最近观察时间。种子文件是版本化的公开搜索索引观察记录，指标可能是过时快照；`UNKNOWN` 用 JSON `null` 表示。它不是随机样本，也不能用于推断传播效果。新记录按同一 JSON 结构人工录入，必须附原帖 URL、观察来源 URL、采集方式和 UTC 观察时间。切勿自动读取浏览器 Cookie 或绕过访问限制。

当前工作顺序和断点见 [TASK_STATE.md](TASK_STATE.md)；研究规范、参考项目证据和架构决策见 `docs/`。任务用 GitHub Issues 跟踪，实际数据与结论以仓库版本为准。

