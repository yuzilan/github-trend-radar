# GitHub 热榜雷达

[English](README.md)

这是一个小型、透明、可审计的 Agent Skill。你手动让它查看 GitHub 日榜或周榜，它会给出客观 Top 10，用人话解释每个仓库在做什么、有什么意思、适合谁，并根据你明确表达的兴趣和排除反馈逐渐调整个人推荐。

它不会定时骚扰你，不会自动 star、fork、安装或运行热门仓库，也不会把“你没点开”擅自理解成“不喜欢”。

当前版本：`0.5.0`。源码位于 [yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar)，版本历史见 [CHANGELOG.md](CHANGELOG.md)。

## 推荐安装方式

日常个人使用建议安装到用户级，这样不同项目和对话都能发现同一个 Skill：

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar --global
```

如果只想在当前项目试用，去掉 `--global`：

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

运行脚本需要 Python 3.9 或更高版本，不需要安装第三方 Python 包。安装后请在新一轮对话中调用 Skill。

## 三分钟上手

不需要记命令，直接对 Agent 说：

- “运行 GitHub 今日日榜。”
- “总结本周 GitHub Top 10。”
- “只看 Python 项目的本周热榜。”
- “详细看看第 3 个项目，重点讲架构和怎么运行。”

一份正常报告会包含：

1. 抓取时间和日榜/周榜范围；
2. 不受个人喜好影响的客观热度 Top 10；
3. 个人推荐 Top 10，冷启动时会明确标注；
4. 每个推荐项目的用途、有意思之处、适合人群、成熟度与风险；
5. GitHub 仓库直达链接和推荐原因。

客观榜与个人推荐榜始终分开。排除规则只影响个人推荐，不会改写客观事实。

## 如何教它了解你

你可以自然地说：

| 你说的话 | 保存的范围 |
| --- | --- |
| “详细看看这个仓库” | 一次弱兴趣，不等于明确喜欢 |
| “我对这个感兴趣” | 当前仓库和最多三个窄主题 |
| “我实际试过，会继续用” | 更强的仓库与主题兴趣 |
| “这个仓库不感兴趣” | 只排除这个仓库 |
| “这类项目都不想看” | 只排除你明确说出的类别 |
| “恢复这个仓库/主题” | 取消相应排除 |
| “忘记这个仓库/主题的偏好” | 删除当前权重和排除状态 |

查看画像可以说：“你目前记住了我的哪些偏好？”

“忘记”只修改当前推荐画像，历史反馈仍保留在本地审计日志中。如果要清空全部当前偏好，可以说“重置全部偏好”；Agent 必须在执行前再次向你确认。

需要备份时可以说：“把我的 GitHub 推荐画像和反馈记录导出到一个 JSON 文件。”已有文件不会在未确认的情况下被覆盖。

## 排名是怎样算的

客观热度综合考虑：周期新增 star、GitHub Trending 原始位置、相对增长、日榜与周榜重合，以及间隔足够长的本地快照增速。

个人推荐采用：

```text
75% 客观热度 + 25% 兴趣匹配
```

兴趣使用固定的 0—10 权重尺度，不会因为当天只有一个偏好命中，就把一次弱询问放大成满额兴趣。Top 10 中保留一个探索位，避免推荐越来越封闭；请求 Top 1 时不会强行使用探索位。

这是一种用于发现项目的透明启发式排名，不是 GitHub 官方分数，也不代表软件质量。精确规则见 [references/ranking-and-feedback.md](references/ranking-and-feedback.md)。

## 数据、缓存与隐私

如果存在 `~/Documents/Codex/`，默认数据目录为：

```text
~/Documents/Codex/github-trend-radar-data/
```

其他环境回退到 `~/.github-trend-radar/`。可以通过环境变量 `GITHUB_TREND_RADAR_HOME` 或脚本参数 `--data-dir` 修改。

主要文件：

- `profile.json`：当前有效的推荐画像；
- `feedback.jsonl`：追加式反馈审计记录；
- `profile.json.bak`：上一份可恢复画像；
- `repository-metadata.json`：GitHub 公开元数据缓存；
- `snapshots/`：历史热榜快照；
- `latest-*-ranking.json`：最近一次排序结果。

默认会给日榜和周榜交错排列的前 25 个候选补充 GitHub topics、许可证和维护信息，并缓存 24 小时。没有 `GITHUB_TOKEN` 也能工作，但公开 API 限额较低；如果本地环境已经设置 Token，脚本只从环境读取，不会把它写进快照、缓存或画像。

仓库页面和 README 都属于第三方内容，因此 Skill 只把它们当作待核实的资料，不会把其中夹带的提示词或命令当成 Agent 指令。远程内容不能覆盖 Skill 规则、索取 Token 或本地资料，也不能自行触发工具。详细了解一个项目不等于安装或运行它；后者必须由用户另行明确提出，并单独进行安全检查。

## 更新与卸载

更新用户级安装：

```bash
npx skills update github-trend-radar --global --yes
```

卸载 Skill：

```bash
npx skills remove github-trend-radar --global --yes
```

卸载 Skill 不会主动删除放在外部数据目录里的偏好和历史。如果要删除这些用户数据，请先确认目录位置并自行备份。

## 常见问题

### GitHub Trending 抓取失败

GitHub 没有正式 Trending API，本项目读取公开 Trending 网页。网页结构变化或返回内容不完整时，脚本会明确失败，不会拿残缺数据生成榜单，也不会偷偷换成“最近新建仓库”。

### 元数据缓存损坏或版本不支持

缓存只包含可重新获取的公开仓库信息。可以在下一次抓取时使用 `--refresh-metadata` 重建；这不会修改你的偏好和反馈。

### 画像文件损坏

先查看错误提示和 `.bak` 备份。`profile.py repair` 会恢复上一份备份，因此执行前应让用户知道会恢复什么，不能静默处理。

### 推荐不合口味

先查看画像，再明确说“忘记某个仓库/主题”或“排除某类项目”。不要通过反复点击来猜测系统学到了什么——所有权重和排除项都可以查看。

## 开发与验证

```bash
python3 -m unittest discover -s tests -v
ruff check scripts tests
python3 scripts/release_check.py --strict --tag v0.5.0
```

参与开发和发布步骤见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全与漏洞反馈见 [SECURITY.md](SECURITY.md)。项目采用 MIT 许可证。
