# X Content Research & Growth Engine

面向单人中文 X 创作者的本地研究工作台。目标是把真实帖子发现、对照研究、独立素材、人工创作与发布后反馈连成可复查的闭环。当前仅完成首批数据来源验证和样本库基础能力；没有经过验证的“爆款公式”。

## 运行

需要 Python 3.10+，不需要 API 密钥或额外付费依赖。

```sh
python3 -m growth_engine init
python3 -m growth_engine import data/seed_x_observations.json
python3 -m growth_engine import data/direct_page_probe.json
python3 -m growth_engine import-materials data/seed_materials.json
python3 -m growth_engine report
python3 -m growth_engine audit
python3 -m growth_engine packet
python3 -m unittest discover -s tests -v
```

默认数据库为 `data/research.sqlite3`（不提交 Git）；`--db 路径` 可指定位置。导入可重复执行，按 X 帖子 ID 去重，同一帖子可有多次来源不同的观察；`ingest_runs` 表保存每次导入的数量、失败原因和重试数。种子文件是版本化的公开搜索索引观察记录，指标可能是过时快照；`UNKNOWN` 用 JSON `null` 表示。`direct_page_probe.json` 只记录一次原帖公开摘要核对，没有可用浏览量。样本不是随机抽取，不能用于推断传播效果。新记录按同一 JSON 结构人工录入，必须附原帖 URL、观察来源 URL、采集方式和 UTC 观察时间。切勿自动读取浏览器 Cookie 或绕过访问限制。

当前工作顺序和断点见 [TASK_STATE.md](TASK_STATE.md)；研究规范、参考项目证据和架构决策见 `docs/`。任务用 GitHub Issues 跟踪，实际数据与结论以仓库版本为准。

`packet` 将有来源的探索任务包输出到终端，供人工交给当前 ChatGPT 会话处理，不调用模型 API。真实发布后，可用 `python3 -m growth_engine import-feedback feedback.json` 人工录入：JSON 数组的每项需包含 `url`、UTC `published_at` 与 `observed_at`、`human_reviewed: true`、`evidence_note`；可选非负整数或 `null` 指标为 `impressions`、`likes`、`replies`、`reposts`、`profile_visits`、`new_follows`。项目不附伪造的反馈样例，也不连接 X 账号。
