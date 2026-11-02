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
