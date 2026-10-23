# GitHub 出稿箱（公开仓库）

当前仓库为 public。只放**明确要公开发布**的 X 正文和必要核验字段，不放聊天全文、隐私记录、联系方式、认证信息或未经最终确认的草稿。Git 历史无法保证删除后不可恢复。

**长篇记录**：`scope=LONGFORM_OR_THREAD`，`text` 为本人批准的完整原文；`thread_parts` 是由原段落分组的完整文本，必须通过 `"\\n\\n".join(thread_parts) == text` 的逐字校验。Codex 可以在真实账号支持时发完整长帖，或将这些原文按顺序发成串帖，不得重新改写或省略。回执必须标注 `publish_mode`，单条长帖核验全文，串帖核验全部独立链接、正文和顺序。

旧 Ally 短稿已被作者拒绝，已移到 `outbox/rejected/`，不是授权的待发稿。

`ready/<post_id>.json` 是 ChatGPT 提交的交接单。例子仅供说明，**下方不是实际待发布内容**：

```json
{
  "schema": "LIVING_RECORD_X_HANDOFF_V1",
  "post_id": "20261023-observation-example",
  "status": "READY_FOR_CODEX",
  "platform": "X",
  "account": "qiluo27808",
  "scope": "ORIGINAL_POST",
  "origin": "CHATGPT_USER_CONVERSATION",
  "created_at": "2026-10-23T09:30:00+08:00",
  "text": "此处替换为已经确认允许公开的实际正文",
  "content_sha256": "必须由该实际正文UTF-8字符计算出的SHA-256",
  "claim_type": "PERSONAL_REFLECTION",
  "source_urls": [],
  "review": {
    "user_explicitly_requested_publication": true,
    "final_text_approved": true,
    "author_voice_checked": true,
    "privacy_checked": true,
    "no_invented_first_person": true,
    "facts_and_uncertainty_checked": true,
    "no_manipulative_pressure": true
  }
}
```

**只在这些复核确实完成后**才设为 true。对用户不愿公开的内容，不上传。对于新闻事件，把 `claim_type` 改为 `PUBLIC_FACTS` 或 `MIXED`，提供至少一条 HTTPS `source_urls`，但链接存在不意味着已核实事实；仍要逐项查证。无需为了“高传播”添加争论问题或口头禅。

`content_sha256` 的计算方式：`hashlib.sha256(text.encode("utf-8")).hexdigest()`。一次交接正文一个 ID；不要改动已放入发布队列的正文。如果需要改稿，先撤销旧队列再生成新的 ID，避免未知提交重复发帖。

`receipts/<post_id>.json` 只能在 Codex 通过 Computer Use 实际查看独立 X 详情、核对精确文字后创建：

```json
{
  "post_id": "20261023-observation-example",
  "content_sha256": "与ready中的hash完全相同",
  "account": "qiluo27808",
  "provider": "X",
  "url": "https://x.com/qiluo27808/status/1234567890123456789",
  "observed_exact_text": true,
  "verified_at": "2026-10-23T10:00:00+08:00"
}
```

上例 URL 是虚构格式示例，不是真实发布回执。

```sh
python3 -m growth_engine.handoff scan --root outbox --strict
python3 -m growth_engine.handoff check outbox/ready/<post_id>.json
python3 -m growth_engine.handoff check-receipt outbox/ready/<post_id>.json outbox/receipts/<post_id>.json
```

GitHub Actions 仅校验，不登录 X，也不会自动启动 Codex。如果希望在对话里一句「整理并发布」就执行，仍需要在支持的 Work / Codex 环境运行 Computer Use 任务；此仓库只是清晰可审计的交接面。
