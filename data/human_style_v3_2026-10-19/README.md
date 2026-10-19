# Human Style V3：Codex写，标准库检查

本轮不安装本地模型，不接付费API，不新增运行依赖、数据库、服务或评分模块。保留HUMAN_STYLE_V2校验合同字段和历史调用；引擎版本更新为human-style-v3-lightweight，未发布旧合同需按当前规则重检，已发布记录不改；V3是写作交接和正文比较，不是新的推理引擎。无人值守采集仍只产出线索，实质写作需要Codex会话执行。

- [九篇原稿与新稿全文、具体得失](nine_comparisons.md)
- [最新来源的三个不同选题与全文](fresh_three.md)
- [实际候选链重放，含原稿与新稿](replay.md)

`gen_default.json`的六句writing_brief就是可复用风格指引。可选口语不是配额。尚无用户认可的V3正例，approved_examples留空；不能把上一轮机器通过的九稿当作用户认可。C390与校园A作为明确失败参照，未覆盖历史记录。

交接：`run_human_style_pipeline({draft_text: 原稿, authored_text: Codex成稿, locked_facts: 原稿事实锁, primary_action: ...})`。`prepare_candidate`接受同名authored_text字段；hunt的previews接受original_text + text + locked_facts。事实核查和正文评审须对应最终清理后的正文重新做，旧评审不自动沿用。没有authored_text时保留旧行为，同时明确标记只做清理；原文未变不等于质量合格。正文比较和来源绑定仍由content_review承担，没有增加另一套评分。

重放：

```sh
python3 -m growth_engine validate-hunt data/content_quality_2026-10-19/source_packet.json data/human_style_v3_2026-10-19/editorial_reviews.json --output /tmp/v3-replay.json
python3 -m unittest discover -s tests -q
```

fresh_three.json保留原始摘要、实际成稿、事实锁、逐句来源证据与编辑比较，现有回归测试会重跑事实与来源检查。记录不是自动晋级到READY：三篇只可进入人工内容审核，尚未构造完整发布预检。全程未向X提交。

资源实测：Apple本机Python 3.9，`/usr/bin/time -l python3 -m growth_engine validate-hunt ...`：0.54秒real、24,772,608字节峰值RSS。限于本地20题/9稿检查；不包含网络采集等待或Codex生成时间。无GPU要求、无常驻进程。pytest仅为已有开发测试依赖。

## 开源参考与许可证评估

2026-10-19读取三个项目的README、SKILL和LICENSE，均为MIT。只借鉴方法，由本仓库独立实现，没有引入包、复制源码/提示词/词库或安装其运行系统；因此不分发其软件副本。原项目版权与MIT文本仍在各项目对应版本的LICENSE中。

| 项目与核对版本 | 吸收的方法 | 未采用 |
| --- | --- | --- |
| [jiji262/humanizer-chinese](https://github.com/jiji262/humanizer-chinese/tree/1d6c08e10fbfe0e1b36ac784834451c6aae0a92c) | 区分语境，具体细节来自来源，防止统一假口语 | 整套模式库和长提示词 |
| [YottaMeta/yotta-humanize](https://github.com/YottaMeta/yotta-humanize/tree/8bfa946e72c3a7e4b018eaa2d600dd270d1bdc75) | 机械清理与需要判断的编辑分开，原事实优先 | 再加一个确定性评分引擎 |
| [lynote-ai/humanize-text-skill](https://github.com/lynote-ai/humanize-text-skill/tree/9359e17a8d7d54263adb726f4e6c71e0b0940651) | 先保护事实，再按目标声音做最小有效编辑 | 完整skill依赖或通用写作流水线 |

限制：同一Codex分别写作与复审，没有第二位真人认可；中文含义、误导性删节与幽默分寸仍需编辑判断。技术检查不能验证文学质量、事实真伪或真实流量；本轮曝光、互动、涨粉均UNKNOWN。完达山一号是旧事；BT是10月13日报道，都未伪装48小时新事件。
