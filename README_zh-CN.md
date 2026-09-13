# GitHub 热榜雷达

[English](README.md)

这是一个小型、透明、可审计的 Agent Skill：每天由用户手动触发，生成 GitHub 日榜或周榜 Top 10，用人话解释项目，并根据用户明确的兴趣、深入询问和排除反馈逐步调整个人推荐。

Python 脚本只负责抓取、校验、排序和保存反馈；宿主 Agent 负责阅读仓库 README、版本、许可证等一手资料并生成解释。它不是定时推送系统，不会自动 star、安装或执行热点仓库。

## 安装

仓库发布后，可以通过 Skills CLI 安装：

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

脚本只使用 Python 标准库，建议使用 Python 3.9 或更高版本。

当前版本：`0.4.0`。版本历史见 [CHANGELOG.md](CHANGELOG.md)。

源码仓库：[github.com/yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar)

## 使用

可以明确调用 `$github-trend-radar`，也可以直接说：

- “运行 GitHub 今日日榜。”
- “总结本周 GitHub Top 10。”
- “详细看看第 3 个项目。”
- “这个仓库我不感兴趣，以后排除。”
- “列出你目前记录的我的偏好。”

客观热度榜和个人推荐榜始终分开。排除规则影响个人推荐，但不会改写客观榜的事实。

## 数据与隐私

如果存在 `~/Documents/Codex/`，默认数据目录为：

```text
~/Documents/Codex/github-trend-radar-data/
```

其他环境回退到 `~/.github-trend-radar/`。可以通过 `GITHUB_TREND_RADAR_HOME` 或 `--data-dir` 修改。

本地目录保存偏好、反馈流水、历史快照、最新排名和一份偏好备份。脚本不会把凭据写入文件；只有显式启用 API 补充信息时，才会从环境读取可选的 `GITHUB_TOKEN`。

## 排名说明

客观热度综合考虑：周期新增 star、GitHub Trending 原始位置、相对增长、日榜与周榜重合情况，以及间隔足够长的本地快照增速。

个人推荐采用：

```text
75% 客观热度 + 25% 兴趣匹配
```

另有明确排除和一个探索位。这是发现项目的启发式排名，不是 GitHub 官方分数，也不代表软件质量。

## 可靠性设计

- 保存快照前检查 GitHub Trending 必填字段，局部解析失败会直接阻断。
- 暂时性网络错误会有限重试，不会偷偷换成另一类榜单。
- 并列指标获得相同分数。
- 偏好写入采用锁、原子替换和上一版本备份。
- 仓库与主题兴趣权重设有上限，避免无限强化。
- 不自动安装或执行任何热点仓库代码。

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

正式发布前运行：

```bash
python3 scripts/release_check.py --strict --tag v0.4.0
```

参与开发和发布步骤见 [CONTRIBUTING.md](CONTRIBUTING.md)，漏洞反馈边界见
[SECURITY.md](SECURITY.md)。

## 许可证

MIT
