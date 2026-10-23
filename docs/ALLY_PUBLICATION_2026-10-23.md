# Ally 完整思想记录：已发布并核验

批准源为 records/2026-10-23-ally-attention-and-self.md；正式交接单 outbox/ready/20261023-ally-full-record.json。1362字符、40段与12段备用串帖无损拼接一致，SHA-256：`704f4d8c100489bff49718cc4f14d0dd8928fd332aad6402eaf386c3af013d13`。本轮基线 main 为 `16b32416d06ac6e7f7d31c88bd5d2bee9868f94b`。

## 实际发布

- 使用本人授权的原生可见 Chrome Computer Use，确认账号 @qiluo27808。发布前检查主页，并用 X Top / Latest 搜索 `from:qiluo27808 "今天跟" "Ally"` 未发现完整稿重复。
- 原生编辑器支持长帖，粘贴完整正文后显示剩余22,388字符；没有摘要、删改或拆分。点击 Post 一次，独立打开 [原文字版](https://x.com/qiluo27808/status/2113468088205357337)，时间11:10 AM · Oct 23, 2026。
- 逐屏滚动核对40段、空行和最后一句。原生详情 AX 单个文本节点只返回512字符；这不是实际正文截断。重新打开已保存帖子的原生编辑器，可取得完整正文；仅将 AX 折叠的段落换行标准化后逐字比较通过。空行另经可见详情核对。
- 用户随后明确要求 Ally / 恋综配图。通过原帖 Edit post 加入两张真实官方图，正文不变，Update 一次。独立打开 [最新图文版本](https://x.com/qiluo27808/status/2113473377105248319)，显示 Last edited 11:31 AM · Oct 23, 2026。新版完整正文保存后比较通过，两个 photo 链接、图片和 ALT 来源已核验；无额外回复或重发。最后的复核编辑器未修改且未提交。
- 成功回执：outbox/receipts/20261023-ally-full-record.json；核验摘要：outbox/reviews/20261023-ally-full-record.json。回执以最新版本 URL 为准，并保留原版本 URL。截图和浏览器本地资料不提交公开仓库。

## 人物与配图来源

[优酷官宣](https://weibo.com/2/detail/5355672121644708)列出刘予宁及公开账号，附第二季群像海报。[节目官方女嘉宾约会物料](https://weibo.com/2/detail/5356411996605348)按姓名顺序列出八位女嘉宾，刘予宁第五，对应上传的第五张剧照。两张保留原节目和优酷标识，ALT 写明来源。原图片 URL、上传字节哈希记录在回执中，仓库不复制图片文件。

作者谈到自己的讨论与金钱比较，属于本人明确批准的记录；营销保持疑问且明确没有证据，不新增指控、私人信息或代理虚构经历。

## 修复内部误判

原 CODEX_PUBLISH.md 第0条把未找到非API单次例外当成必须停止的全局条件，未经实际 UI 尝试就给出平台规则阻塞。已改为先检查真实 Computer Use、账号和页面；无 X API、旧 PAUSED、NO_VERIFIED_COMPLIANT_TRANSPORT 等无人值守状态不自动否定明确授权的单次可见操作。具体工具拒绝、访问控制、验证码与实际适用执行限制仍须尊重，不绕过。

handoff.py 本身不操作浏览器，也不检查 API 凭据。新增 scan 的 `validation_scope: LOCAL_HANDOFF_INTEGRITY_ONLY`，避免将文件检查当作平台许可判定；回归测试保留明确授权、正文哈希、隐私、账号、完整串帖和真实回执保护。

旧128字稿后来被拒绝，继续留在 rejected。它曾在拒绝之前依据原授权发布为 [历史短稿](https://x.com/qiluo27808/status/2113461638137589986)，本会话当时独立详情核验；不假造它现在仍可访问、不为它恢复 ready。之前“0次提交”的说明已过时，由此记录纠正。

## 验证与日常交接

执行：`python3 -m unittest discover -s tests -v`、`python3 -m unittest tests.test_handoff -v`、`python3 -m compileall -q growth_engine tests`、`python3 -m growth_engine.handoff scan --root outbox --strict`、完整 ready 与 receipt 的 `check-receipt`。本地15项测试及11项 handoff 定向测试通过，compileall、diff --check、check-receipt 均通过；strict scan 为 ready 0、completed 1、blocked 0。GitHub CI 随提交另行核实。

每小时人物事件简报保持现有排程，旧排名、Top1、强制互动和20分钟发布不恢复。没有付费API、新依赖或常驻服务。

以后说「把刚才那段发到 X」且指代唯一、无需实质改写，即授权那段原文公开一次；ChatGPT 整理，GitHub 只存确认稿，Codex 在当前有权限的会话执行并独立核验。需实质修改时先确认最终稿。GitHub 提交本身不会自动唤起 Codex，普通聊天不进入公开 outbox。
