# GitHub Trend Radar

[简体中文](README_zh-CN.md)

GitHub Trend Radar is a small, transparent, and auditable Agent Skill. Run it manually to collect a GitHub daily or weekly Top 10, explain each repository in plain language, investigate selected projects, and gradually personalize recommendations from explicit user feedback.

It does not schedule notifications, star or fork repositories, install trending code, or interpret silence as dislike.

Current version: `0.5.0`. Source: [yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar). See [CHANGELOG.md](CHANGELOG.md) for release history.

## Recommended installation

For personal use across projects, install it at user scope:

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar --global
```

Omit `--global` for a project-local trial:

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

The runtime uses only the Python standard library and supports Python 3.9 or newer. Invoke the skill in a new conversation turn after installation.

## Three-minute start

Ask naturally; no script commands are required:

- “Show today's GitHub Top 10.”
- “Summarize this week's GitHub trending repositories.”
- “Show only weekly Python trending projects.”
- “Investigate number 3, focusing on architecture and setup.”

A normal report contains the collection time and period, an objective Top 10, a separate personalized Top 10, plain-language project cards, caveats, recommendation reasons, and direct repository links. Exclusions change recommendations without rewriting the factual objective list.

## Teaching and correcting preferences

| User intent | Stored scope |
| --- | --- |
| Investigate a repository | One weak interest signal |
| Explicitly interested | Repository and up to three narrow topics |
| Actually tried it | Stronger repository and topic interest |
| Not interested in this repository | Exact repository exclusion only |
| Not interested in this category | Only the explicitly named category |
| Restore a repository or topic | Remove the matching exclusion |
| Forget this repository or topic | Remove its active weight and exclusion |

Ask “What have you learned about my preferences?” to inspect the profile. Forgetting changes the active recommendation profile while retaining the local append-only audit history. Resetting all active preferences requires an explicit confirmation immediately before the action.

The profile and feedback history can be exported to a portable JSON file. Existing exports are not overwritten unless explicitly allowed.

## Ranking

Objective heat combines GitHub Trending period star gain, original position, relative growth, daily/weekly overlap, and comparable local snapshot velocity.

Personalized ranking uses:

```text
75% objective heat + 25% interest match
```

Interest uses a fixed 0—10 scale, so the only matching repository cannot turn one weak investigation into a full preference bonus. Top 10 reports reserve one exploration position; Top 1 requests do not. This is a transparent discovery heuristic, not an official GitHub score or a software-quality rating. See [references/ranking-and-feedback.md](references/ranking-and-feedback.md) for exact rules.

## Local data, metadata cache, and privacy

When `~/Documents/Codex/` exists, the default data directory is `~/Documents/Codex/github-trend-radar-data/`. Other environments use `~/.github-trend-radar/`. Override either with `GITHUB_TREND_RADAR_HOME` or `--data-dir`.

The directory contains the active profile, append-only feedback, one profile backup, leaderboard snapshots, recent rankings, and a cache of public GitHub repository metadata. By default, up to 25 interleaved daily and weekly candidates are enriched and cached for 24 hours.

The skill works without `GITHUB_TOKEN`, although unauthenticated API limits are lower. When the variable is present, the token is read only from the process environment and is never written to snapshots, caches, profiles, or logs.

## Update and remove

```bash
npx skills update github-trend-radar --global --yes
npx skills remove github-trend-radar --global --yes
```

Removing the skill does not automatically delete preference data stored outside the skill directory. Back up and verify that directory separately before deleting user data.

## Troubleshooting

- **Trending fetch fails:** GitHub has no official Trending API. Incomplete or changed HTML fails closed instead of producing a partial report or silently substituting another leaderboard.
- **Metadata cache is unsupported or corrupt:** rerun collection with `--refresh-metadata`; the cache is derived public data and rebuilding it does not change feedback.
- **Profile is corrupt:** inspect the reported path and backup first. `profile.py repair` restores the previous backup and must not run silently.
- **Recommendations feel wrong:** inspect the profile, then forget or exclude the exact repository or topic. Stored weights remain visible and editable.

## Development

```bash
python3 -m unittest discover -s tests -v
ruff check scripts tests
python3 scripts/release_check.py --strict --tag v0.5.0
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and release steps and [SECURITY.md](SECURITY.md) for private vulnerability reporting guidance. Licensed under MIT.
