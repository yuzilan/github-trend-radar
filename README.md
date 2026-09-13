# GitHub Trend Radar

[简体中文](README_zh-CN.md)

A small, auditable agent skill for manually generating GitHub daily or weekly Top 10 reports, explaining repositories in plain language, investigating selected projects, and learning user-controlled recommendation preferences over time.

The deterministic Python helpers fetch, validate, rank, and store feedback. The host agent reads primary repository sources and writes the human-facing explanation. It is intentionally not a scheduler, notification service, repository executor, or opaque machine-learning recommender.

## Install

After this repository is published, install the skill with the Skills CLI:

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

No third-party Python packages are required. Python 3.9 or newer is recommended.

Current version: `0.4.0`. See [CHANGELOG.md](CHANGELOG.md) for release history.

Source repository: [github.com/yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar)

## Use

Invoke `$github-trend-radar`, or ask naturally:

- “Show today's GitHub Top 10.”
- “Summarize this week's GitHub trending repositories in Chinese.”
- “Investigate number 3 in detail.”
- “I am not interested in this repository; exclude it.”
- “Show what you have learned about my preferences.”

The skill keeps objective popularity separate from personalized relevance. Exclusions affect recommendations without rewriting the factual objective list.

## Local data and privacy

When `~/Documents/Codex/` exists, the default data directory is:

```text
~/Documents/Codex/github-trend-radar-data/
```

Other environments fall back to `~/.github-trend-radar/`. Override either default with `GITHUB_TREND_RADAR_HOME` or `--data-dir`. The directory contains the current profile, append-only feedback history, snapshots, latest rankings, and one profile backup. Credentials are never written to these files. An optional `GITHUB_TOKEN` is read only from the environment when API enrichment is requested.

## Ranking

Objective heat combines period star gain, GitHub Trending position, relative growth, daily/weekly overlap, and comparable snapshot velocity. Personalized ranking is 75% objective heat and 25% explicit or observed interest match, with hard user-controlled exclusions and one exploration position.

This is a discovery heuristic, not an official GitHub score and not a software-quality rating. See `references/ranking-and-feedback.md` for the exact rules.

## Reliability

- GitHub Trending HTML is validated before a snapshot is saved.
- Transient network failures are retried; a different leaderboard is never silently substituted.
- Equal metric values receive equal percentile scores.
- Profile changes use a lock, atomic replacement, and a last-known-good backup.
- Repository and topic weights are capped to limit runaway reinforcement.
- Unknown repositories are never installed or executed by the skill.

Run the test suite with:

```bash
python3 -m unittest discover -s tests -v
```

Before publishing a release, run:

```bash
python3 scripts/release_check.py --strict --tag v0.4.0
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution and release workflow
and [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance.

## License

MIT
