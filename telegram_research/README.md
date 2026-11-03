# 深度好文 Telegram 只读研究采集器

目标：授权读取 `@shenduhaowen`，按关键词优先级生成**可追溯的文章索引**，可在自己的电脑上选择提取部分 PDF 文本。此模块与现有 X 发布系统隔离，**不主动加入频道、不发帖、不转发、不对 Telegram 进行批量互动**。

## 1. 在自己的电脑上完成一次授权

需要 Python 3.11+。进入本项目根目录：

```bash
python3 -m pip install -r telegram_research/requirements.txt
mkdir -p data/telegram
```

到 https://my.telegram.org/apps 用**自己的 Telegram 账号**申请 `api_id` 和 `api_hash`（官方开发者凭证）。在仓库根目录创建 `data/telegram/credentials.env`：

```text
TG_API_ID=在这里填写数字ID
TG_API_HASH=在这里填写API_HASH
```

`data/` 已被 .gitignore 忽略；**不要把凭证、手机号、验证码、两步验证密码或 session 发给 ChatGPT，也不要提交到 GitHub**。

```bash
chmod 600 data/telegram/credentials.env
python3 -m telegram_research.auth
```

本机终端按 Telegram 提示完成登录。授权成功后，私密会话保存在 `data/telegram/session.txt`（文件权限 0600）。Session 相当于已登录账号的钥匙，泄露时应在 Telegram 的 *Settings → Devices* 撤销相应会话，并更新 GitHub Secret。

## 2. 采集与检索

```bash
# 最近 7 天消息：标题、日期、原文链接、主题评分；不会下载附件
python3 -m telegram_research.reader --channel shenduhaowen --days 7

# 自己电脑上获取最近 500 条，最多下载 10 份 PDF 并提取前 15 页可选文字
python3 -m telegram_research.reader --channel shenduhaowen --days 0 --max-messages 500 --download-pdfs --pdf-limit 10
```

文件在 `reports/telegram/brief.md`、`reports/telegram/posts.json` 和（启用时）`data/telegram/pdfs/`。均处于 gitignore 目录，不会上传公开仓库。PDF 若为扫描图像，将提示「无可提取文字」；**不使用 OCR**。关键词匹配只决定阅读顺序，不等于已由 AI 完整阅读或验证观点。若账号没有访问权限，会明确失败，不绕过访问控制。

## 3. GitHub Actions 定时（可选）

仓库包含 `.github/workflows/telegram-research.yml`，每 6 小时检查最近 3 天的至多 200 条消息，只生成链接、元信息和说明短摘；**GitHub Actions 不下载 PDF、不保存文章全文、不自动发布到 X**。在仓库 **Settings → Secrets and variables → Actions → New repository secret** 设置三个仓库 Secret：

- `TG_API_ID`：开发者 ID
- `TG_API_HASH`：开发者 hash
- `TG_STRING_SESSION`：将本机 `data/telegram/session.txt` 的完整值直接粘贴到 GitHub Secret（不要粘贴到聊天、Issues 或代码）

然后在 **Actions → Telegram read-only research → Run workflow** 手动测试。成功报告见运行页面的 Step Summary 和 Artifact；缺少 Secret 时跳过采集并提示配置。定时执行可能因 GitHub 调度延迟，或 Telegram 风控/连接限制而失败；**未配置 Secrets 前不可视为已启用自动采集**。

### 安全与权利

这是公开 GitHub 仓库，Action artifact 和运行摘要可能被有权查看仓库的人读取，因此只输出有限标题、链接与说明短摘。**禁止将付费文章完整 PDF 或未经许可的全文公开上传、再分发**。仅阅读有合法访问权限的内容，尊重原作者权益和 Telegram 规则。建议把长期保存全文的工作放在本机私人目录。

## 本次补全：本机导出、可靠增量与公开输出边界

先利用已登录的官方客户端打开 `https://t.me/shenduhaowen`。如果客户端提供 **Export chat history**，只导出该公开频道，选择 JSON 和有权下载的 PDF，不导出私人聊天。不读取客户端数据库、Cookie 或会话令牌。macOS 原生版和跨平台 Telegram Desktop 的功能不同；界面无导出入口时，不假设存在导出能力。

```bash
# 官方单频道导出；请先确认 result.json 确实来自目标频道
.venv/bin/python -m telegram_research.import_export /absolute/path/to/result.json
# 安全录入开发者凭证（由本人在终端操作，无回显，不覆盖现有文件）
.venv/bin/python -m telegram_research.setup_local
.venv/bin/python -m telegram_research.auth
# 首次最近至少 200 条，不再默认为最近7天
.venv/bin/python -m telegram_research.reader --max-messages 200 --download-pdfs --pdf-limit 10
# 后续按消息 ID 增量；大于单批上限的积压从旧到新分批处理，不跳过中间消息
.venv/bin/python -m telegram_research.reader --incremental --max-messages 500
# 明确时区，左闭右开时间区间（与增量游标独立）
.venv/bin/python -m telegram_research.reader --since 2026-10-01T00:00:00+08:00 --until 2026-11-01T00:00:00+08:00 --max-messages 5000
.venv/bin/python -m telegram_research.search 东南亚
```

SQLite 索引和游标在 `data/telegram/index.sqlite3`；正文在 `data/telegram/bodies/`，完整可提取 PDF 文字不再截断前15页。文件按 Telegram document ID 复用；下载写 `.part`，校验大小后原子重命名。中断会保存已完成消息，下一次从上次成功整轮游标重放并去重；**目前是消息级断点恢复，未实现 PDF 字节偏移续传**。网络错误最多重试3次；FloodWait 立即停止并报告等待时间，不规避限流。首次默认仅读取最近200条，更早历史需显式日期采集。消息编辑和删除不自动同步，需定期重扫指定区间。

正文 SHA256 标注重复消息；不会丢掉各自的来源链接。`posts.json` 保留标题、日期、附件名、说明和研究字段。摘要、观点、论据、逻辑问题、业务相关性、机会均默认为 `null`，等待 Codex **实际读取正文**后填写；“提取成功”不是“完成阅读或深度判断”。关键词优先级不调用模型、不产生付费 API 费用。扫描 PDF 明确标记未 OCR；损坏、加密 PDF 单独记失败。扫描 PDF 已下载但未可读，不计入文本解析成功。

### 持久化与 GitHub Actions（修订说明，覆盖上方旧 Artifact 描述）

公开 Artifact 和 Step Summary **只含统计 `status.md`**，不再上传 `brief.md`、`posts.json`、说明摘录、PDF、SQLite 或 Session。完整研究索引仅本地查看。GitHub 托管 runner 的本地磁盘不跨运行持久化，每轮会重新检查最新500条；不能声称具有可靠历史状态，也可能漏掉超过500条的更新。不要把 Actions cache 当永久数据库。

低成本可靠方式：使用自己的专用 **self-hosted runner**，仓库变量 `TG_RUNNER_JSON` 设为 `["self-hosted","telegram-research"]`，`TG_STATE_DIR` 设为 checkout 目录以外的私有绝对路径。该目录保留数据库、正文及游标，定期做本机加密备份。不要与其他不受信任仓库共用 runner，不要在公开 PR 上运行采集或暴露凭证。若不希望 Session 进入 GitHub Secrets，可直接在本机调度同一 CLI；当前仓库 Actions 仍会因缺 Secrets 明确跳过。选择持久化方式和真实授权前，自动采集不算已启用。

验收必须分别看：workflow 的配置/调度存在、手动 job 是否成功、creds 步骤是否 ready、collect 步骤是否实际运行、采集数量是否达到要求。缺 Secrets 的绿色 job 仅代表**跳过正确**。

### 不想执行命令时：本机浏览器授权

操作者可启动 `.venv/bin/python -m telegram_research.local_login`，然后打开程序显示的 `http://127.0.0.1:端口/`。依次输入官方开发者凭证、手机号、验证码，以及需要时的两步验证密码。所有输入均隐藏；不输出账号名、凭证、验证码或 Session。仅监听本机回环地址，校验 Host、Origin 和 CSRF；页面禁止缓存和外部资源。完成后停止服务，再执行原有采集命令。Codex 可负责启动与后续命令，用户只需在本机输入登录验证码/密码。
