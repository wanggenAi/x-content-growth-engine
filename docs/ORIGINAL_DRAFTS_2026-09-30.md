# Original candidates for human review

Status: `EXPLORATORY_DRAFT`. These are three distinct topics and angles. No X propagation formula has been validated. The author should decide account positioning and publication; none has been posted.

## 1. Tool boundary: the free converter and the OCR assumption

Draft:

> 把文件转成 Markdown，和读懂扫描件里的字，是两件事。MarkItDown 最近的版本说明提到 OCR 插件重构，但插件文档写得更关键：它需要视觉模型客户端；没有提供客户端时，OCR 会跳过，回到普通转换。以后看到“开源工具支持 OCR”，我会先问三个问题：扫描件能否读出字？模型调用由谁提供？失败时会不会悄悄漏掉内容？这三项比演示视频更能决定它是否适合日常资料整理。

Facts checked: [official release](https://github.com/microsoft/markitdown/releases/tag/v0.1.8) and [OCR plugin instructions](https://github.com/microsoft/markitdown/blob/main/packages/markitdown-ocr/README.md). The plugin explicitly says OCR is skipped without an `llm_client`; its example uses an OpenAI-compatible client. Do not claim all OCR must be paid; a separately authorized local vision model could change the cost, but this project has not tested one. Originality check: original framing/questions, no copied prose, no personal-use claim. Before publication: try a text PDF and a scanned PDF locally, or keep this clearly labeled as a documentation-based observation.

## 2. Everyday access: passkey security versus account recovery

Draft:

> “不用密码”听起来像是登录问题结束了，其实只是把难题换了位置。Passkey 用设备上的密钥完成登录，设计目标之一是防钓鱼；但换手机、丢设备、跨平台迁移时，能否顺利找回账号，还要看密钥保存方式和网站提供的恢复流程。对普通用户来说，第一次设置时值得多看一眼的不是动画有多顺，而是：第二台设备能不能用？旧设备没了怎么办？

Facts checked: [FIDO Alliance explainer and FAQ](https://fidoalliance.org/passkeys/), including synced/device-bound keys and cross-device/recovery routes. No claim that a particular provider's recovery works or fails. Originality check: own decision questions, no copied wording or invented account-loss story. Before publication: verify current recovery steps for any named service; this draft names none.

## 3. Urban life: the shade gap behind city heat

Draft:

> 同一座城市里，“今天很热”也可能是两条完全不同的步行路线。NASA 介绍的一项研究用卫星资料比较了 500 个大城市的绿地降温能力，指出城市之间存在明显差距。这个研究量的是地表温度与植被，不等于你站在树下时的体感温度；但它提醒我一个更具体的问题：规划一条路时，我们到底有没有把能遮阴的绿地当成基础设施？

Facts checked: [NASA's study summary](https://science.nasa.gov/missions/landsat/landsat-reveals-role-of-green-spaces-in-cooling-cities/), dated 2024-11-26, describing satellite data for 2017-2019 and 500 large cities. Do not transplant its numerical cooling estimates to a Chinese street or to air temperature. Originality check: own framing and question, no copied text, no invented firsthand experience. Before publication: optionally add a separately documented local route observation; do not assert one without evidence.

## Editorial gate

Each draft needs user approval, present-tense source recheck and final originality review. These are experimental candidates, not evidence-supported formula output. There is no automatic posting path.
