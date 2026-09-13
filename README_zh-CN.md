# GitHub 热榜雷达

[English](README.md)

[![Release](https://img.shields.io/github/v/release/yuzilan/github-trend-radar?style=flat-square)](https://github.com/yuzilan/github-trend-radar/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/yuzilan/github-trend-radar/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/yuzilan/github-trend-radar/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-7c3aed?style=flat-square)](LICENSE)

这是一个小型、透明、可审计的 Agent Skill。你手动让它查看 GitHub 日榜或周榜，它会给出客观 Top 10，用人话解释每个仓库在做什么、有什么意思、适合谁，并根据你明确表达的兴趣和排除反馈逐渐调整个人推荐。

它不会定时骚扰你，不会自动 star、fork、安装或运行热门仓库，也不会把“你没点开”擅自理解成“不喜欢”。

当前版本：`0.6.0`。源码位于 [yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar)，版本历史见 [CHANGELOG.md](CHANGELOG.md)。

## 目录

- [功能一览](#功能一览)
- [推荐安装方式](#推荐安装方式)
- [三分钟上手](#三分钟上手)
- [如何教它了解你](#如何教它了解你)
- [排名是怎样算的](#排名是怎样算的)
- [数据、缓存与隐私](#数据缓存与隐私)
- [高级用法：直接运行脚本](#高级用法直接运行脚本)
- [更新与卸载](#更新与卸载)
- [常见问题](#常见问题)
- [开发与验证](#开发与验证)

## 功能一览

| 功能 | 它会做什么 |
| --- | --- |
| 日榜与周榜 | 手动读取 GitHub Trending 的 daily / weekly 榜单 |
| 编程语言筛选 | 查看 Python、Rust、JavaScript 等指定语言的 Trending |
| 客观 Top N | 根据公开热度信号排序，不受个人偏好影响 |
| 个人推荐 Top N | 在客观热度基础上加入你明确表达的兴趣 |
| 人话解读 | 说明项目用途、亮点、适合人群、成熟度和限制 |
| 项目深挖 | 继续研究架构、主要模块、使用方式、许可证、维护状态与问题 |
| 偏好学习 | 区分“问过”“明确喜欢”“实际试用”等不同强度 |
| 排除与恢复 | 精确排除一个仓库或明确主题，也可以随时恢复 |
| 忘记与重置 | 删除当前偏好；完整重置前必须再次确认 |
| 画像查看、导入与导出 | 查看已学到的内容，并安全迁移画像和反馈记录 |
| 本地缓存 | 缓存公开仓库元数据，减少重复 API 请求 |
| 历史比较 | 有可比较快照时标注重复出现和有依据的变化 |
| 诊断与空间清理 | 只读检查环境；预览并清理可重建的过期数据 |

## 推荐安装方式

### 1. 准备环境

你需要：

- 能够使用 Agent Skills 的 Codex 或兼容客户端；
- Node.js / `npx`，用于运行 Skills CLI；
- Python 3.9 或更高版本。

运行时只使用 Python 标准库，不需要另外安装 Python 依赖。

### 2. 安装到用户级

日常使用推荐全局安装，这样不同项目和新任务都能发现同一个 Skill：

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar --global
```

### 3. 只在当前项目试用

如果暂时不想全局安装，去掉 `--global`：

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

### 4. 安装后开始使用

安装完成后新建一个任务，然后自然地提出需求即可。你可以显式写 `$github-trend-radar`，也可以直接说“运行 GitHub 今日日榜”。

如果当前对话是在安装 Skill 之前创建的，建议新开任务，让客户端重新发现已安装的 Skill。

## 三分钟上手

### 第一次运行：查看今日日榜

```text
$github-trend-radar 运行 GitHub 今日日榜，给我客观 Top 10 和个人推荐 Top 10，并用中文解释每个项目。
```

第一次运行还没有偏好证据，个人榜会标注为冷启动，暂时与客观榜一致。这是正常现象。

### 查看本周热榜

```text
总结本周 GitHub Top 10。每个仓库说明它在做什么、亮点、适合谁和需要注意的问题。
```

这里的日榜和周榜对应 GitHub Trending 提供的 daily / weekly 页面，不是自行推算的自然日或自然周统计。

### 只看某种编程语言

```text
只看 Python 项目的本周 GitHub 热榜。
```

```text
查看 Rust 项目的今日日榜前 5 名。
```

语言名称会规范成 GitHub Trending 的语言路径并安全进行 URL 编码，因此 `C#`、`Visual Basic` 等名称不会破坏周期参数。若 GitHub 不识别该语言或返回的页面不完整，Skill 会明确报错，不会偷偷换成其他榜单。

### 自定义数量

默认输出 Top 10，也可以要求其他数量：

```text
只给我今天最值得关注的前 5 个项目。
```

```text
给我本周 Top 20，只需要简短说明。
```

### 一份标准报告包含什么

正常报告会逐项给出：

1. 抓取时间、daily / weekly 周期和语言筛选；
2. 不受个人喜好影响的客观热度 Top N；
3. 单独列出的个人推荐 Top N；
4. 每个推荐项目在做什么；
5. 项目最有意思或最值得关注的地方；
6. 它适合哪类用户；
7. 成熟度、许可证、维护状态或明显限制；
8. 为什么给你推荐；
9. GitHub 仓库直达链接和靠近事实的来源说明；
10. 有历史快照支持时的重复出现或变化标记。

排除规则只影响个人推荐。即使某个仓库已被你排除，只要它仍在客观榜前列，报告仍会保留它的一行客观位置并标记 `已排除`，但不会继续给它完整推荐卡片。

### 继续详细了解一个项目

看到感兴趣的项目后，可以按编号或仓库名继续问：

```text
详细看看第 3 个项目。先说明它解决什么问题，再讲架构、主要模块、怎么安装和目前的限制。
```

```text
深入研究 owner/repository，重点看它最近是否还在维护、采用什么许可证、有哪些值得注意的 Issue。
```

深挖不会只扩写上一段简介。Skill 会重新查看仓库 README、官方文档、元数据、Release 和相关公开信息，并区分：

- **已核实事实**：仓库或官方资料能够直接支持；
- **维护者声明**：项目方这样描述，但尚未独立验证；
- **分析判断**：基于资料做出的推断，会明确标注。

详细了解仓库不等于安装或运行它。除非你另行明确要求，Skill 不会执行陌生仓库代码、安装依赖或运行设置脚本。

## 如何教它了解你

### 偏好学习原则

- 只有明确反馈才会形成强偏好；
- 一次详细询问只算弱兴趣；
- 没有继续询问不等于不喜欢；
- 排除一个仓库不会自动排除整个类别；
- 类别排除只使用你明确说出的主题；
- 所有当前权重和排除项都可以查看、恢复或忘记。

### 所有支持的反馈操作

| 你可以这样说 | 实际记录 | 影响范围 |
| --- | --- | --- |
| “详细看看这个仓库” | `detail` | 仓库和最多三个窄主题各增加弱兴趣 `+0.5` |
| “我对这个感兴趣” | `interested` | 仓库和最多三个窄主题各增加 `+2` |
| “我实际试过，会继续用” | `tried` | 仓库和最多三个窄主题各增加 `+3` |
| “我喜欢本地优先工具” | `like-topic` | 只给明确主题增加 `+3` |
| “这个仓库不感兴趣” | `exclude-repo` | 只硬排除这个仓库 |
| “这类低代码平台都不想看” | `exclude-topic` | 只硬排除明确主题 |
| “恢复这个仓库” | `restore-repo` | 取消仓库排除，历史记录保留 |
| “恢复这个主题” | `restore-topic` | 取消主题排除，历史记录保留 |
| “忘记这个仓库的偏好” | `forget-repo` | 删除仓库当前权重和仓库排除 |
| “忘记 Python 主题偏好” | `forget-topic` | 删除主题当前权重和主题排除 |
| “重置全部偏好” | `reset-profile` | 清空全部当前画像，执行前必须再次确认 |

仓库与主题的正向权重最高为 10，不会因反复询问无限增长。同一轮对话中的同一次反馈不会重复记录。

### 查看目前学到了什么

```text
你目前记住了我的哪些 GitHub 推荐偏好？请列出仓库、主题、排除项和最近反馈。
```

报告会展示当前正向主题权重、精确仓库权重、仓库排除、主题排除以及最近的反馈事件。

### 恢复、忘记和重置有什么区别

- **恢复**：只取消排除，不删除已经形成的正向权重；
- **忘记**：删除该仓库或主题的当前权重，同时取消对应排除；
- **重置**：清空全部当前偏好和排除项，必须立即再次确认。

无论忘记还是重置，历史 `feedback.jsonl` 都会保留，便于审计。它不会继续参与当前推荐计算；真正生效的是 `profile.json` 中的当前画像。

### 导出画像和反馈

```text
把我的 GitHub 推荐画像和完整反馈记录导出为 JSON 文件。
```

导出文件包含当前画像、完整反馈和导出时间。已有文件默认不会被覆盖；只有你明确允许时才会强制覆盖。

## 排名是怎样算的

### 客观热度

客观榜只使用公开热度信号，不加入个人偏好或主观 README 质量判断：

| 信号 | 默认权重 |
| --- | ---: |
| GitHub Trending 显示的周期新增 star | 45% |
| GitHub Trending 原始位置 | 25% |
| 相对增长率 | 15% |
| 同时出现在日榜和周榜 | 10% |
| 与最近可比较快照之间的 star 增速 | 5% |

如果没有历史快照、两次快照间隔小于 15 分钟，或没有任何仓库增长，最后一项会被省略，其余权重重新归一化。相同数值获得相同的百分位分数。

客观热度反映当前关注度，不代表项目质量、安全性或长期价值，也不是 GitHub 官方分数。

### 个人推荐

先删除你明确排除的仓库和主题，然后计算：

```text
75% 客观热度 + 25% 兴趣匹配
```

兴趣匹配取“精确仓库权重”和“已命中主题平均权重”中较大的一个，再除以固定上限 10。它不会按照当天最强候选重新缩放，所以一次 `detail` 的 `0.5` 只会得到 5 分兴趣匹配，不会被放大成满分。

默认 Top 10 会保留一个探索位：从尚未入选的高客观热度项目中补入一个，降低推荐逐渐封闭的风险。请求 Top 1 时不会强行使用探索位。

完整公式和反馈规则见 [references/ranking-and-feedback.md](references/ranking-and-feedback.md)。

## 数据、缓存与隐私

### 默认数据目录

如果存在 `~/Documents/Codex/`，默认使用：

```text
~/Documents/Codex/github-trend-radar-data/
```

其他环境回退到：

```text
~/.github-trend-radar/
```

可以通过 `GITHUB_TREND_RADAR_HOME` 或任一脚本的 `--data-dir` 指定其他位置。所有项目默认共享同一份画像，因此你的偏好不会因切换工作目录而消失。

### 文件分别保存什么

| 文件 | 内容 | 是否可以重建 |
| --- | --- | --- |
| `profile.json` | 当前生效的权重和排除项 | 用户数据，不应随意删除 |
| `profile.json.bak` | 上一次画像备份 | 用于修复 |
| `feedback.jsonl` | 追加式完整反馈事件 | 用户审计数据 |
| `feedback.jsonl.bak` | 导入覆盖前的上一份反馈备份 | 仅临时恢复用途 |
| `repository-metadata.json` | topics、许可证、维护状态等公开元数据 | 可以重建 |
| `snapshots/*.json` | 每次经过校验的热榜快照 | 可以重新积累 |
| `latest-daily-ranking.json` | 最近一次日榜排序 | 可以重建 |
| `latest-weekly-ranking.json` | 最近一次周榜排序 | 可以重建 |

画像写入使用文件锁、原子替换和上一份备份，避免并发反馈破坏文件。如果画像损坏，脚本会停止并报错，不会静默重建一份空画像。

### 元数据缓存

默认从日榜和周榜交错选择最多 25 个候选，通过 GitHub API 补充 topics、许可证、归档状态和维护信息：

- 最多 4 个并发请求；
- 缓存默认有效 24 小时；
- 命中缓存时不重复请求 API；
- 快照会记录缓存命中数、API 请求数和错误数；
- `--enrich-limit 0` 可以关闭补充；
- `--refresh-metadata` 可以强制重建缓存。

缓存只包含公开信息，损坏或版本不兼容时可以安全重建，不会修改用户偏好。

### 主题别名

主题会使用保守、可查看的小型别名表规范化。例如 `ai-agents` 会归到 `ai-agent`，`devtools` 会归到 `developer-tools`，`llms` 会归到 `llm`。发生转换时，反馈事件会保留 `topic_aliases` 供审计。它不会依靠模糊模型猜测擅自把不同类别合并。

### 保存期限与清理边界

`maintenance.py prune` 只处理可重建的历史快照和公开元数据缓存，默认只是预览。只有加入 `--apply` 才会实际删除，且该命令永远不会删除 `profile.json` 或 `feedback.jsonl`。默认保留 180 天快照、90 天元数据；这只是手工清理工具，不会在后台自动运行。

### GitHub Token

没有 `GITHUB_TOKEN` 也可以运行，但未认证 GitHub API 的限额较低。如果本地环境已经设置 Token，脚本只从进程环境读取，不会写入快照、缓存、画像、日志或仓库文件。

### 第三方内容安全边界

GitHub Trending 页面、仓库 README、Issue、Release 和 API 字段均视为不可信第三方资料，而不是 Agent 指令。远程文本不能覆盖 Skill 规则、要求泄露 Token 或本地数据、触发工具、联系他人或扩大任务范围。

## 高级用法：直接运行脚本

普通用户不需要运行下面的命令；Agent 会根据 [SKILL.md](SKILL.md) 自动调用。此部分用于调试、审计和手工复现。

<details>
<summary><strong>展开完整命令教程</strong></summary>

以下命令中的 `<skill-dir>` 表示本 Skill 的安装目录。

### 1. 查看数据保存位置

```bash
python3 <skill-dir>/scripts/profile.py location
```

使用自定义目录：

```bash
python3 <skill-dir>/scripts/profile.py location --data-dir /path/to/data
```

### 2. 初始化画像

```bash
python3 <skill-dir>/scripts/profile.py init
```

该命令会在画像不存在时创建默认文件；已存在的有效画像不会被静默清空。

### 3. 抓取热榜快照

```bash
python3 <skill-dir>/scripts/fetch_trending.py --period both --limit 25
```

成功后会打印快照 JSON 路径。推荐抓取 `both`，即使最终只展示日榜或周榜，也能判断仓库是否同时出现在两个周期。

常用示例：

```bash
# 只抓日榜
python3 <skill-dir>/scripts/fetch_trending.py --period daily --limit 25

# Python 周榜
python3 <skill-dir>/scripts/fetch_trending.py --period weekly --programming-language python

# 关闭 API 元数据补充
python3 <skill-dir>/scripts/fetch_trending.py --period both --enrich-limit 0

# 强制刷新公开元数据缓存
python3 <skill-dir>/scripts/fetch_trending.py --period both --refresh-metadata
```

抓取参数：

| 参数 | 含义 |
| --- | --- |
| `--data-dir PATH` | 覆盖默认数据目录 |
| `--period daily\|weekly\|both` | 抓取周期，默认 `both` |
| `--limit N` | 每个周期保留的候选数量，默认 25 |
| `--programming-language NAME` | GitHub Trending 编程语言筛选 |
| `--language NAME` | 上一个参数的兼容别名 |
| `--enrich-limit N` | API 补充候选数量，默认 25；设为 0 关闭 |
| `--metadata-cache PATH` | 自定义缓存文件位置 |
| `--metadata-ttl-hours HOURS` | 缓存有效小时数，默认 24 |
| `--refresh-metadata` | 忽略旧缓存并重新获取 |
| `--history-dir PATH` | 自定义历史快照目录 |
| `--output PATH` | 自定义本次快照输出文件 |

### 4. 生成排序结果

把抓取命令打印的路径传给 `--snapshot`：

```bash
python3 <skill-dir>/scripts/rank_trending.py \
  --snapshot /path/to/snapshot.json \
  --period daily \
  --top 10
```

默认写入 `latest-daily-ranking.json` 或 `latest-weekly-ranking.json`，并打印输出路径。

排序参数：

| 参数 | 含义 |
| --- | --- |
| `--data-dir PATH` | 数据目录 |
| `--snapshot PATH` | 必填；待排序的快照 |
| `--profile PATH` | 使用另一份画像文件 |
| `--period daily\|weekly` | 必填；要排序的周期 |
| `--top N` | 输出数量，默认 10，最小按 1 处理 |
| `--output PATH` | 自定义排序 JSON 输出位置 |

### 5. 查看画像和最近反馈

```bash
python3 <skill-dir>/scripts/profile.py show --events 10
```

`--events` 控制返回多少条最近反馈。

### 6. 手工记录反馈

```bash
# 弱兴趣
python3 <skill-dir>/scripts/profile.py record --signal detail --repo owner/name --topics ai python

# 明确感兴趣
python3 <skill-dir>/scripts/profile.py record --signal interested --repo owner/name --topics ai

# 实际试用
python3 <skill-dir>/scripts/profile.py record --signal tried --repo owner/name --topics developer-tools

# 明确喜欢一个主题
python3 <skill-dir>/scripts/profile.py record --signal like-topic --topics local-first

# 排除或恢复仓库
python3 <skill-dir>/scripts/profile.py record --signal exclude-repo --repo owner/name
python3 <skill-dir>/scripts/profile.py record --signal restore-repo --repo owner/name

# 排除或恢复主题
python3 <skill-dir>/scripts/profile.py record --signal exclude-topic --topics low-code
python3 <skill-dir>/scripts/profile.py record --signal restore-topic --topics low-code

# 忘记仓库或主题当前偏好
python3 <skill-dir>/scripts/profile.py record --signal forget-repo --repo owner/name
python3 <skill-dir>/scripts/profile.py record --signal forget-topic --topics python
```

可以使用 `--note "文字"` 给事件加入短备注。仓库名会统一转为小写，主题会去重并规范化。

### 7. 重置全部当前偏好

没有确认参数时会拒绝执行：

```bash
python3 <skill-dir>/scripts/profile.py record --signal reset-profile
```

确认后才会清空当前画像：

```bash
python3 <skill-dir>/scripts/profile.py record --signal reset-profile --confirm-reset
```

反馈历史仍然保留。

### 8. 导出画像和反馈

```bash
python3 <skill-dir>/scripts/profile.py export --output /path/to/github-trend-profile.json
```

如果文件已存在，命令会拒绝覆盖。只有确认允许覆盖时才使用：

```bash
python3 <skill-dir>/scripts/profile.py export \
  --output /path/to/github-trend-profile.json \
  --force
```

### 9. 导入画像和反馈

先预览合并结果，不写入任何文件：

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json \
  --dry-run
```

确认后执行默认合并：

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json
```

合并会对权重取两边较大值、合并排除项和备注，并按完整事件内容去重，所以重复导入同一份文件不会反复增加兴趣。若确实要完全替换当前画像和历史，必须显式确认：

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json \
  --mode replace \
  --confirm-replace
```

替换导入会为原画像和反馈各保留一份 `.bak`。导入文件中的文本只被视为数据，不会作为 Agent 指令执行。

### 10. 删除反馈历史但保留当前画像

没有确认参数时命令会拒绝执行。确认后：

```bash
python3 <skill-dir>/scripts/profile.py purge-history --confirm-purge
```

这会清空 `feedback.jsonl` 并删除它的旧备份，但不会改变 `profile.json` 中当前生效的权重和排除项。Skill 不提供恢复这段历史的命令；如需保留，请先导出。

### 11. 运行只读诊断

```bash
python3 <skill-dir>/scripts/doctor.py
```

它会检查 Python 版本、数据目录、画像、备份、反馈日志、元数据缓存、GitHub Trending 页面解析和 API 限额。不会修改数据，也不会显示 Token。没有网络时可用：

```bash
python3 <skill-dir>/scripts/doctor.py --offline
```

机器处理可增加 `--json`。

### 12. 查看占用并清理可重建数据

```bash
python3 <skill-dir>/scripts/maintenance.py status
python3 <skill-dir>/scripts/maintenance.py prune
```

第二条只预览待清理项目。核对路径和列表后再实际执行：

```bash
python3 <skill-dir>/scripts/maintenance.py prune \
  --snapshot-days 180 \
  --metadata-days 90 \
  --apply
```

无法读取日期的快照会被跳过而不是冒险删除。

### 13. 从备份修复画像

```bash
python3 <skill-dir>/scripts/profile.py repair
```

该命令会用 `profile.json.bak` 替换当前画像。请先检查错误信息与备份内容，不要把它当作普通重试命令，也不要静默执行。

### 14. 查看真实格式示例

- [历史日榜报告节选](examples/sample-daily-report.md)
- [对应热榜快照](examples/sample-snapshot.json)
- [脱敏示例画像](examples/sample-profile.json)
- [报告质量检查表](references/report-quality.md)

</details>

## 更新与卸载

### 更新用户级安装

```bash
npx skills update github-trend-radar --global --yes
```

更新 Skill 不会清空放在外部数据目录里的画像和历史。

### 卸载 Skill

```bash
npx skills remove github-trend-radar --global --yes
```

卸载 Skill 同样不会自动删除用户数据。如果确实要删除画像和历史，请先运行 `profile.py location` 核对准确目录并备份；不要根据猜测删除目录。

## 常见问题

### 安装后 Agent 找不到 Skill

先确认安装命令没有报错，然后新建一个任务。已经打开的旧任务不一定会重新加载刚安装的 Skill。也可以显式使用 `$github-trend-radar`。

### GitHub Trending 抓取失败

GitHub 没有正式 Trending API，本项目读取公开 Trending 网页。网页结构变化、网络失败或返回内容不完整时，脚本会明确失败，不会拿残缺数据生成榜单，也不会偷偷换成“最近新建仓库”。

先运行 `python3 <skill-dir>/scripts/doctor.py`，可以区分本地状态问题、Trending 页面解析问题与 GitHub API 限额问题。

### GitHub API 限额不足

热榜页面仍可能可用，但 topics、许可证等补充信息可能失败。可以稍后重试、设置本地 `GITHUB_TOKEN`，或使用 `--enrich-limit 0` 暂时关闭 API 补充。Token 不应写入命令、README 或仓库文件。

### 元数据缓存损坏或版本不支持

缓存只包含可重新获取的公开仓库信息。下一次抓取时使用 `--refresh-metadata` 重建；这不会修改画像和反馈。

### 画像文件损坏

脚本会停止并显示文件路径。先检查 `profile.json.bak`，确认后再执行 `profile.py repair`。修复会恢复上一份画像，不保证包含最后一次写入。

### 推荐不合口味

先问“你目前记住了我的哪些偏好？”，再决定恢复、忘记还是排除准确的仓库或主题。不要仅通过跳过项目来训练它，因为沉默不会被解释为负面反馈。

### 为什么客观榜里还有已排除项目

这是设计行为。客观榜记录事实，不能因个人偏好被改写；排除只阻止该项目进入个人推荐卡片。

### 为什么第一次个人榜和客观榜一样

这是冷启动。只有当候选仓库命中已记录的正向仓库或主题时，兴趣权重才会参与排序。

### 为什么没有月榜

当前 Skill 明确实现并验证的是 daily 与 weekly。它不会假装已经支持未经当前代码验证的月榜。

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
ruff check scripts tests
python3 scripts/release_check.py --strict --tag v0.6.0
```

自动测试覆盖 HTML 解析失败保护、语言 URL 编码、缓存命中、日榜周榜交错补充、主题别名、权重计算、Top 1 探索位边界、排除、忘记、重置确认、导入导出、历史清除、派生数据清理、只读诊断、并发反馈、备份修复和发布元数据。GitHub Actions 还在 Linux、macOS 和 Windows 上验证 Python 3.11 兼容性，并每周对当前 Trending 页面做一次真实解析冒烟测试。

参与开发和发布步骤见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全与漏洞反馈见 [SECURITY.md](SECURITY.md)。项目采用 [MIT License](LICENSE)。
