<p align="center">
  <img src="docs/assets/dulac-1911-the-princess-and-the-pea.jpg" width="300" alt="豌豆公主，Edmund Dulac 1911 年插图">
</p>
<p align="center"><sub>Edmund Dulac, 1911 · 公有领域</sub></p>

<h1 align="center">Pea Princess · 豌豆公主</h1>

<p align="center"><a href="README.md">English</a> · <a href="README.zh-TW.md">繁體中文</a> · <b>简体中文</b></p>

<p align="center">用英国官方与公开数据，替你尻洗（台语，roast）一套伦敦出租公寓，<br>并老实说出它不知道的事。</p>

<p align="center">
  <img alt="技能文字：CC BY 4.0" src="https://img.shields.io/badge/skill%20text-CC%20BY%204.0-8A2846">
  <img alt="代码：MIT" src="https://img.shields.io/badge/code-MIT-2F6F55">
  <img alt="格式：Agent Skills" src="https://img.shields.io/badge/format-Agent%20Skills-1F1D26">
  <img alt="房源网站：从不抓取" src="https://img.shields.io/badge/listing%20sites-never%20fetched-6B6679">
</p>

这是一个在伦敦查验和搜索房源用的 agent skill，用官方与公开的英国数据，像谨慎的验房师一样尻洗一套伦敦出租公寓：身份、面积、房龄、供暖、周边工地、治安、物业评价、中介合规、价格、采光、每月总成本、通勤，最后给出判决。任何支持 [Agent Skills](https://agentskills.io) 格式的 agent 都能用（Ex: GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc）；普通的 chat mode 也可以，只是建议使用 agent mode，复杂的任务会更稳定。跟 AI 讲大白话就行。

## 从这里开始，不需要终端

三条路，从最省事到最手动。挑一条和你现在用的工具对得上的。

1. **你在用 agent 应用**（Claude Code、Codex、Cursor、Gemini CLI、Grok Build……）。把这句话贴给它，然后等：

   > 请安装 https://github.com/jacky18008/pea-princess 这个技能，装好后告诉我它能做什么

   Agent 会把这个项目拉下来，用 `pea-princess` 这个名字把技能装好，然后回答你。从此就只要讲话：「尻洗这套房：」再把房源贴上去。

2. **你在用有 Skills 功能的聊天软件**（claude.ai、Claude Cowork、ChatGPT Business）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下载 `pea-princess-skill.zip`，打开 Settings → Skills → Upload，选这个 zip。然后问它「这能干嘛？」。

3. **你在用没有 Skills 的聊天软件**（ChatGPT Plus Projects、Grok Projects、Gemini Gems、Perplexity Spaces）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下载提示词包，把 `INSTRUCTIONS.md` 贴进项目的指令栏，再附上 `references/` 里的文件。之后技能会一次性告诉你要贴什么。

不用写代码，不用改配置文件：接下来全部都是一句一句的话，打字或用语音都行。五分钟上手看 [USING.zh-CN.md](docs/USING.zh-CN.md)；每一种安装方式和它的注意事项在 [INSTALL.md](docs/INSTALL.md)。

## 它查什么，答案从哪里来

| 问题 | 答案从哪里来 |
|---|---|
| 这套房是不是广告上写的那套——哪一户、多大、多旧、怎么供暖？ | GOV.UK 能源证书登记册 |
| 隔壁在盖什么，盖多高？ | GLA 的规划申请 |
| 这条街安不安全？晚上走回家呢？ | police.uk 犯罪数据，六个月，300 米方框 |
| 房东或中介到底是谁，是否合规？ | Companies House、Client Money Protect、Heat Trust、GLA 不良房东查询 |
| 这个价位段的租金合不合理？一个月实际要花多少？ | HM Land Registry 成交记录，加上技能自己的算式，每一项来源都列出来 |
| 采光、噪音、主干道、夜间经济 | OpenStreetMap、Defra 噪音地图 |
| 通勤要多久？有没有备用线路？ | TfL 行程规划工具 |
| 文件流程：押金上限、预付租金、2026-05-01 起的租约规定、租客资格审查 | 技能内置的 Renters' Rights Act 2025 规定，加上你自己的文件 |

每一项结论都带着它的证据等级。查不到的东西，它会一次性用一条消息问你。它不会自己去打开房源网站：页面由你交给它，[上手指南](docs/USING.zh-CN.md)里有三种做法。

## 为什么叫「豌豆公主」
童话里，只有真正的公主能隔着二十层床垫感觉到那颗豌豆。在这里，**你**就是那位公主。这个工具帮你一层一层掀开床垫：翻登记资料、数犯罪案件、查规划申请和公司备案文件，告诉你豌豆可能藏在哪里。但只有你感觉得到：亲自去看房、走一走那条街、跟中介和房东聊一聊。这份报告是一道筛子，赶时间的时候，它也只是一道筛子。它的第一个责任，是说出自己不知道什么，然后开口问你。

作者自己的经历，发在社群的繁体中文原文：[到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md)。

## 三种模式
| 模式 | 你手上有 | 会发生什么 |
|---|---|---|
| Shell | python3 + curl + internet | 脚本负责抓取和解析；模型只读精简过的 JSON |
| Fetch | 有网址抓取工具，没有 shell | 只用公开 GET 的来源；其余的技能会问你 |
| Manual | 一个聊天框 | 技能会一次性列出要打开、要粘贴的页面，并附上链接 |

> 状态：**草稿**。本地采集、区域扫描、报告生成和实验框架都已经做好了。处理个人数据或要做发布之前，先读[安全与隐私边界](SECURITY.md)。使用方式：`docs/INSTALL.md`、`docs/SCRIPTS.md`、`docs/CONVENTIONS.md`。

**分发方式：** 下载这个技能／工具，用你自己的 agent 跑。Pea Princess 不托管模型工作进程，也不碰订阅账号的凭据。本地的人物实验室只是测试用的伙伴。详见[桌面端／移动端的界线、供应商订阅政策、发布关卡](docs/local-product-and-provider-policy.md)。

<details>
<summary><b>给工程师：安装命令、脚本、基准测试、测试</b></summary>

### 安装
```bash
# most agents (Codex, Gemini CLI, Cursor, Copilot, OpenCode, Cline, Goose, pi, OpenClaw, Hermes…)
npx skills add jacky18008/pea-princess
# Claude Code
/plugin marketplace add jacky18008/pea-princess && /plugin install pea-princess@pea-princess
# claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
# then, on any host with a shell: is it installed right? (one request per open register)
python3 ~/.claude/skills/pea-princess/scripts/doctor.py   # or the folder your agent installed it to
```
这个技能安装和调用的名字都是 **`pea-princess`**；上传用的文件是 `dist/pea-princess-skill.zip`。项目源码仍然放在 `skills/vet-flat/`，这样已有的脚本路径和实验记录才不会失效。这就是一个技能，一个安装名称。

Codex：把沙箱网络打开（`sandbox_workspace_write.network_access = true`），或改用 manual 模式。

### 脚本（只用 Python 3.9 标准库；网络走 curl）
全部在 `skills/vet-flat/scripts/`；每一个都打印一个 JSON 对象，里面有 `source_url`、`retrieved_at`、`http_status`、`ok` 和一个证据等级。用法细节在 `docs/SCRIPTS.md`。

| 脚本 | 来源（官方？需要密钥？） | 能拿到什么 |
|---|---|---|
| `epc.py` | GOV.UK EPC register (official, no key; HTML only) | 按邮编／街道搜索、单份证书、整栋楼的画像（面积分布、首次评估年份、供暖、气密性）。10/10 条面积已验证 |
| `geo.py` | postcodes.io (open) | 邮编 ↔ 坐标、附近邮编、半径内的六边形网格覆盖、边界框 |
| `crime.py` | data.police.uk (official, no key) | 固定六个月、约 300 米方框内的数据，分类、掠夺型子集、锚点、±20 米敏感度、走回家的路径带 |
| `commute.py` | TfL Unified API (official, no key) | 门到门的行程（全部／轨道／公交）、附近车站、罢工同族的备用等级 |
| `company.py` | Companies House (official, no key) | 带状态的搜索、公司概况（SIC、抵押登记、董事、财报）、备案文件、用注册地址找住户管理公司 |
| `redress.py` | Client Money Protect, Heat Trust, GLA rogue landlord checker (open) | 中介的 CMP 会籍、热网的站点／供应商、已公布的处罚记录；PRS／TPO 要手动查 |
| `landregistry.py` | HM Land Registry price-paid linked data (official, no key) | 按邮编查成交记录、用最早的新房成交当作竣工年份的证据；产权登记簿要手动查（£7） |
| `planning.py` | GLA Planning Datahub (open; all 33 boroughs) | 按地理距离抓半径内的申请、高楼提示、批复条件的文字 |
| `roads.py` | OpenStreetMap via Overpass (open) | 最近的主干道、地面铁路、隧道口、夜间经济、气味来源、超市、可能挡住采光的建筑（含方位角与仰角） |
| `render.py` | — | `report.json` → HTML 或 Markdown，并用 `references/report-schema.json` 校验 |

没有 shell 的人要看报告排版：用浏览器打开 `viewer/viewer.html`，把 JSON 粘贴进去。需求页面对另一个文件也是同样的做法：`scripts/panel.py --profile profile.yaml --out requirements.html` 会写出一页只读的现状，让人随时想看就打开。没有任何助理会自己写 HTML；模型写 YAML 和 JSON，由脚本负责排版。

### 问它能做什么
问它 **「这能干嘛？」**（或 "What can this do?"）。答案来自 `skills/vet-flat/references/onboarding.md`：一段简短说明、三个起点（有房源 → 尻洗它；有区域或目的地 → 扫一遍；完全没概念 → 十个基本事实加六个带建议默认值的问题）。你自己的规则写在 `profile.yaml`（预算、面积、户型、不能接受的条件、优先级，还有 `budget_mode` lite/standard/deep，给 £20 套餐和只能纯聊天的情况用）。Agent 必须问的硬问题在 `references/questions.md`。

### 基准测试（事实在每个模型上都要对；判决可以不一样）
`evals/evals.json` 收了 7 个行政区的 8 套真实房子，加上 2 个对话场景（「这能干嘛」、「我完全没概念」），标准答案由项目自己的抓取脚本在 2026-09-03 生成。`bench/grade.py` 评分的项目有事实召回率、编造、引用、对未知的诚实度、硬性条件的一致性；`bench/run.py --dry-run` 会打印 Claude Code、Codex、Gemini CLI 或 OpenAI 兼容 API 的完整命令。详见 `bench/README.md`。

**要跑哪一种配置：** `docs/EXPERIMENTS.md` 记录了最早的看房比较实验。[后来的上下文消融实验](docs/ablation-2026-09-09/results.md)包含生成成本和来源审阅：在测到的规模下，额外的摘要、结构化记忆和多次检索调用并没有省下 token。起点就维持「一个 agent 带完整上下文」；四角色流水线还在实验阶段。这些研究测的是不同的任务，不是一份通用的模型排名。

**长时间的项目和会变的需求：** [session harness](docs/session-harness.md) 会保存用户的原话、带版本的需求和条件式例外、来源快照、目标、待办和执行状态。受管理的 runner 自己把当前的数据包塞进去，并拒绝过期的结果。`AGENTS.md`／`CLAUDE.md` 保持简短，只链到详细规则；光放指针不能保证对方会去读。[生命周期验证](docs/session-harness-validation.md)测的是不调用模型也能恢复，不是质量等价或省 token。

**想试一整段人物对话：** 运行 `python3 tools/persona_playground.py`，再打开它打印出来的本地网址。[交互实验室](docs/persona-playground.md)用你本地的 Codex 登录来生成动态的人物回复和助理答案，支持单步／连续／暂停、排队的真人提问、场景修订、私有历史和共用的用量上限。16 张人物卡都有，以清楚标注的聊天改编版呈现；这是本地 alpha，没有公开部署，也没有隐藏的模型裁判。

**社区反馈，第一阶段：** 打开[本地选项表单](community/index.html)，照着[指南](docs/community-feedback-stage1.md)做。公开的 JSON 只放受控的选项；选填的文字留在作者自己的设备上。本地的验证、导入和搜索用的是虚构的演示目录。目前还没有在线提交服务，也没有真实的评论数据集。

**看的是整段对话，不是单一回答：** `docs/JOURNEYS.md` 为九段写好脚本的多轮旅程评分，`docs/PERSONAS.md` 再往前一步——十六个由模型扮演的虚构人物，搭配一个确定性的控制器保管他们的文件，让任何东西都编不出来；裁判必须引用自己的证据；每个人还配一个只动一项设置的对照探针。`python3 bench/personas.py --matrix pilot --dry-run` 不调用模型就能打印出整份计划。

### 测试
```bash
python3 -m unittest tests/test_epc.py
```

</details>

## 这里不会有的来源
Rightmove、Zoopla、OnTheMarket、OpenRent、HomeViews、Trustpilot、Airbnb、Booking.com 在这里只会出现名字。它们的条款不希望程序自动访问，所以这个项目不提供任何做法；技能会向你要页面（PDF、截图或纯文本），不会自己去打开房源链接。这个包里没有这些网页的爬虫，也不能鼓励你让 agent 去爬。

## 改成你的样子

技能就是一个文件夹，里面是 Markdown 和几个脚本，这一包本来就是设计来让你随手改的。不用读代码：跟你的 agent 用说的。

- **你的规则，用你的话讲。** 「含账单上限改成 £2,300」、「安静比采光重要」、「只问我钱的那八题」。助理会先列出要改什么，等你说好才写进你的 `profile.yaml`。查多深也一样：$20 方案用 `lite`，认真看的房子用 `deep`。
- **你自己的检查项目。** 共用技能没查、但你在意的东西（到健身房的步行时间、学区、你知道的噪音来源），写成一页放进 `extensions/`，或直接口述一串让 agent 帮你写。报告里会标成你自己加的，不会自己改变判决。
- **改技能本身。** 跟 agent 说哪里不顺、少了什么：「每份报告先讲每月总花费」、「加一项高楼层没电梯的检查」、「用粤语问我问题」。它会改 `skills/vet-flat/` 里的文件；`python3 -m unittest discover -s tests` 会告诉你有没有弄坏什么，报告格式有规范文件守着，查看器照样读得懂。
- **你的私人版本。** 作者自己有一个很吃 token 的「超无敌尻洗版」；你的可以是一个 fork，或只是一个 `extensions/` 文件夹。要公开任何东西之前，把 `profile.yaml`、`.pea-state/` 和你的文件留在自己电脑上（见 [SECURITY.md](SECURITY.md)）。
- **别的国家。** 想做台湾版、美国版、欧洲版就 fork：要换的是查登记册的脚本，对话规则直接带走。记得保留署名（文字 CC BY 4.0、代码 MIT）并注明出处；作者很乐意交流。
- **分享心得，不分享地址。** 「分享我的种子」会给你一段短码，带的是你的口味和你要问的问题，从来不含你住哪、什么时候搬。

任何主机都能先试这一句：

> 把这个技能改成每份报告开头先讲每月总花费，改完跑测试，告诉我你改了什么。

## 许可与署名（提案中）
文档和技能文字：CC BY 4.0。代码：MIT。每一份报告都会带着 "Generated with pea-princess <version> — <source URL>"。请留着它。

插图出自 Edmund Dulac 1911 年为 *Stories from Hans Andersen*（Hodder & Stoughton，伦敦）画的彩页，属于公有领域。`docs/assets/mark.svg` 里的标志（七层床垫下的一颗豌豆）是原创的，跟文档一起以 CC BY 4.0 发布；`docs/assets/social-preview.png` 是同一个标志做成的 1280×640 预览卡。
