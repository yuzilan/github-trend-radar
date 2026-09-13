# GitHub Trend Radar

[简体中文](README_zh-CN.md)

[![Release](https://img.shields.io/github/v/release/yuzilan/github-trend-radar?style=flat-square)](https://github.com/yuzilan/github-trend-radar/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/yuzilan/github-trend-radar/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/yuzilan/github-trend-radar/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-7c3aed?style=flat-square)](LICENSE)

GitHub Trend Radar is a small, transparent, and auditable Agent Skill. Run it manually to collect a GitHub daily or weekly Top 10, explain each repository in plain language, investigate selected projects, and gradually personalize recommendations from explicit user feedback.

It does not schedule notifications, star or fork repositories, install trending code, or interpret silence as dislike.

Current version: `0.6.0`. Source: [yuzilan/github-trend-radar](https://github.com/yuzilan/github-trend-radar). See [CHANGELOG.md](CHANGELOG.md) for release history.

## Contents

- [Feature overview](#feature-overview)
- [Recommended installation](#recommended-installation)
- [Three-minute start](#three-minute-start)
- [Teaching and correcting preferences](#teaching-and-correcting-preferences)
- [Ranking](#ranking)
- [Local data, metadata cache, and privacy](#local-data-metadata-cache-and-privacy)
- [Advanced usage](#advanced-usage-run-the-scripts-directly)
- [Update and remove](#update-and-remove)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Feature overview

| Feature | What it does |
| --- | --- |
| Daily and weekly discovery | Manually reads GitHub Trending daily and weekly pages |
| Programming-language filter | Finds Python, Rust, JavaScript, and other language-specific trends |
| Objective Top N | Ranks public attention signals without personal preferences |
| Personalized Top N | Adds relevance from preferences the user explicitly expressed |
| Plain-language briefs | Explains purpose, highlights, audience, maturity, and limitations |
| Repository deep dives | Investigates architecture, modules, setup, license, maintenance, and issues |
| Preference learning | Distinguishes investigation, explicit interest, and actual use |
| Exclude and restore | Excludes an exact repository or named topic and can restore it later |
| Forget and reset | Removes active preferences; full reset requires confirmation |
| Inspect, import, and export | Shows learned state and safely moves profiles with feedback history |
| Local metadata cache | Reduces repeated GitHub API requests |
| Historical comparison | Marks repeats and evidence-backed movement when snapshots allow it |
| Diagnostics and retention | Checks the environment read-only and previews cleanup of rebuildable data |

## Recommended installation

### 1. Requirements

You need:

- Codex or another client that supports Agent Skills;
- Node.js / `npx` to run the Skills CLI;
- Python 3.9 or newer.

The runtime uses only the Python standard library. No third-party Python packages are required.

### 2. Install at user scope

For normal use, install globally so different projects and new tasks can discover the same skill:

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar --global
```

### 3. Try it in one project

Omit `--global` for a project-local trial:

```bash
npx skills add yuzilan/github-trend-radar --skill github-trend-radar
```

### 4. Start after installation

Create a new task and ask naturally. You may invoke `$github-trend-radar` explicitly or simply ask for today's GitHub Top 10.

If the current task was already open before installation, start a new one so the client can discover the newly installed skill.

## Three-minute start

### First run: today's leaderboard

```text
$github-trend-radar Show today's GitHub Top 10. Give me an objective Top 10 and a personalized Top 10, and explain each project in plain language.
```

On the first run there is no preference evidence. The personalized list is labeled as a cold start and initially matches the objective list. This is expected.

### This week's leaderboard

```text
Summarize this week's GitHub Top 10. Explain what each repository does, why it is interesting, who it suits, and what caveats matter.
```

Daily and weekly refer to GitHub Trending's daily and weekly pages; they are not independently reconstructed calendar-period statistics.

### Filter by programming language

```text
Show only Python projects from this week's GitHub Trending list.
```

```text
Show the first five Rust projects from today's list.
```

The language is normalized and safely URL-encoded as part of the GitHub Trending path, so names such as `C#` and `Visual Basic` cannot corrupt the period query. If GitHub does not recognize it or returns incomplete markup, the skill fails clearly rather than substituting another leaderboard.

### Choose a different result count

The default is Top 10, but other sizes are supported:

```text
Show only the five projects most worth my attention today.
```

```text
Give me this week's Top 20 with short descriptions.
```

### What a standard report contains

A normal report includes:

1. collection time, daily / weekly period, and language filter;
2. an objective Top N unaffected by personal preferences;
3. a separately labeled personalized Top N;
4. what each recommended repository does;
5. its most interesting or useful aspect;
6. who it is suitable for;
7. maturity, license, maintenance state, or material limitations;
8. why it was recommended;
9. direct repository links with source attribution near factual claims;
10. repeat appearances or movement only when historical snapshots support them.

Exclusions affect only personalized recommendations. If an excluded repository still ranks highly on the objective list, its factual one-line position remains and is marked `excluded`, but it does not receive a full recommendation card.

### Investigate one repository

Continue by position or repository name:

```text
Investigate number 3. Explain the problem first, then cover architecture, main modules, setup, and current limitations.
```

```text
Research owner/repository. Focus on whether it is actively maintained, its license, and notable open issues.
```

A deep dive does not merely expand the earlier synopsis. The skill rechecks the repository README, official documentation, metadata, releases, and relevant public information. It distinguishes:

- **verified facts** directly supported by repository or official material;
- **maintainer claims** that have not been independently verified;
- **analysis or inference** derived from the available evidence.

Investigating a repository does not install or run it. Unless separately requested, the skill never executes unfamiliar repository code, installs its dependencies, or runs setup scripts.

## Teaching and correcting preferences

### Learning principles

- Strong preferences require explicit feedback.
- One deep-dive request is only a weak interest signal.
- Silence and lack of follow-up do not mean dislike.
- Excluding one repository never excludes its whole category.
- Topic exclusions use only a category the user explicitly named.
- Every active weight and exclusion remains inspectable, restorable, and forgettable.

### Every supported feedback action

| User intent | Stored signal | Active effect |
| --- | --- | --- |
| “Investigate this repository” | `detail` | Repository and up to three narrow topics gain weak interest `+0.5` |
| “I am interested in this” | `interested` | Repository and up to three narrow topics gain `+2` |
| “I tried it and will keep using it” | `tried` | Repository and up to three narrow topics gain `+3` |
| “I like local-first tools” | `like-topic` | The explicitly named topic gains `+3` |
| “Not interested in this repository” | `exclude-repo` | Only that exact repository is hard-excluded |
| “I do not want low-code platforms” | `exclude-topic` | Only the explicitly named topic is hard-excluded |
| “Restore this repository” | `restore-repo` | Removes the repository exclusion; history remains |
| “Restore this topic” | `restore-topic` | Removes the topic exclusion; history remains |
| “Forget this repository” | `forget-repo` | Removes its active weight and repository exclusion |
| “Forget my Python preference” | `forget-topic` | Removes the topic's active weight and exclusion |
| “Reset all preferences” | `reset-profile` | Clears active state only after immediate confirmation |

Positive repository and topic weights are capped at 10. Repeated questions cannot grow them without limit, and the same feedback event is not recorded twice for one user turn.

### Inspect what has been learned

```text
What have you learned about my GitHub recommendation preferences? List repositories, topics, exclusions, and recent feedback.
```

The response shows positive topic weights, exact repository weights, repository exclusions, topic exclusions, and recent feedback events.

### Restore, forget, and reset are different

- **Restore** removes an exclusion but keeps an existing positive weight.
- **Forget** removes current weight and the matching exclusion for one repository or topic.
- **Reset** clears every active preference and exclusion and requires immediate confirmation.

Forget and reset deliberately retain the append-only `feedback.jsonl` audit history. Historical entries no longer drive recommendations; the active state comes from `profile.json`.

### Export the profile and feedback

```text
Export my GitHub recommendation profile and complete feedback history to JSON.
```

The export contains active state, complete feedback, and an export timestamp. Existing files are not overwritten unless the user explicitly approves it.

## Ranking

### Objective heat

The objective list uses public attention signals only. Personal interests and subjective README quality never enter this score:

| Signal | Default weight |
| --- | ---: |
| Period star gain shown by GitHub Trending | 45% |
| Original GitHub Trending position | 25% |
| Relative growth | 15% |
| Presence in both daily and weekly lists | 10% |
| Star velocity since a comparable local snapshot | 5% |

If no previous snapshot exists, snapshots are less than 15 minutes apart, or no repository gained stars, the last component is omitted and the remaining weights are renormalized. Equal metric values receive equal percentile scores.

Objective heat measures current attention. It is not a software-quality or security score and is not an official GitHub ranking.

### Personalized ranking

Explicitly excluded repositories and topics are removed first. Remaining candidates use:

```text
75% objective heat + 25% interest match
```

Interest match uses the larger of an exact repository weight and the average of matched topic weights, divided by the fixed cap of 10. It is not rescaled against the strongest candidate that day. A single `detail` event at `0.5` therefore produces an interest match of 5, not 100.

Top 10 normally reserves one exploration position for a high-objective candidate outside the first personalized entries. This reduces recommendation lock-in. A Top 1 request never receives an exploration override.

See [references/ranking-and-feedback.md](references/ranking-and-feedback.md) for the full formula and feedback rules.

## Local data, metadata cache, and privacy

### Default data directory

When `~/Documents/Codex/` exists, the default is:

```text
~/Documents/Codex/github-trend-radar-data/
```

Other environments use:

```text
~/.github-trend-radar/
```

Override the location with `GITHUB_TREND_RADAR_HOME` or any script's `--data-dir`. The default state is shared across working directories, so preferences do not disappear when switching projects.

### What each file stores

| File | Contents | Rebuildable? |
| --- | --- | --- |
| `profile.json` | Active weights and exclusions | User state; do not delete casually |
| `profile.json.bak` | Previous profile backup | Used for repair |
| `feedback.jsonl` | Append-only feedback events | User audit data |
| `feedback.jsonl.bak` | Previous feedback before an import replacement | Temporary recovery aid |
| `repository-metadata.json` | Public topics, license, and maintenance metadata | Yes |
| `snapshots/*.json` | Validated leaderboard observations | Can accumulate again |
| `latest-daily-ranking.json` | Latest daily ranking | Yes |
| `latest-weekly-ranking.json` | Latest weekly ranking | Yes |

Profile updates use a file lock, atomic replacement, and one previous backup to protect concurrent writes. A corrupt profile causes a clear failure; it is not silently replaced with an empty profile.

### Metadata cache

By default, the skill interleaves daily and weekly candidates and enriches up to 25 with GitHub topics, license, archive state, and maintenance metadata:

- at most four concurrent requests;
- a default 24-hour cache lifetime;
- no repeated API request on a valid cache hit;
- cache hit, API request, and error counts stored in the snapshot;
- `--enrich-limit 0` to disable enrichment;
- `--refresh-metadata` to rebuild the cache.

The cache contains only rebuildable public information. Rebuilding it never changes user preferences.

### Topic aliases

Topics use a small, conservative, inspectable alias map. For example, `ai-agents` becomes `ai-agent`, `devtools` becomes `developer-tools`, and `llms` becomes `llm`. When a conversion occurs, the feedback event retains `topic_aliases` for auditing. The skill does not use fuzzy model guesses to merge unrelated categories.

### Retention and cleanup boundary

`maintenance.py prune` handles only rebuildable snapshots and public metadata cache entries. It previews by default and deletes only with `--apply`; it never removes `profile.json` or `feedback.jsonl`. Defaults are 180 days for snapshots and 90 days for metadata. This is a manual tool and never runs in the background.

### GitHub token

The skill works without `GITHUB_TOKEN`, although unauthenticated GitHub API limits are lower. When present, the token is read only from the process environment and is never written to snapshots, caches, profiles, logs, or repository files.

### Third-party content boundary

GitHub Trending pages, repository READMEs, issues, releases, and API fields are untrusted third-party data rather than agent instructions. Remote text cannot override the skill's rules, request a token or unrelated local data, trigger tools, contact people, or expand task scope.

## Advanced usage: run the scripts directly

Normal users do not need these commands; the agent follows [SKILL.md](SKILL.md) and runs them as needed. This section is for debugging, auditing, and manual reproduction.

<details>
<summary><strong>Expand the complete command tutorial</strong></summary>

In these examples, `<skill-dir>` is the installed skill directory.

### 1. Show the data location

```bash
python3 <skill-dir>/scripts/profile.py location
```

Use `--data-dir /path/to/data` to preview an override.

### 2. Initialize the profile

```bash
python3 <skill-dir>/scripts/profile.py init
```

This creates default state only when needed. It does not silently clear an existing valid profile.

### 3. Fetch a leaderboard snapshot

```bash
python3 <skill-dir>/scripts/fetch_trending.py --period both --limit 25
```

The command prints the snapshot JSON path. Fetching `both` is recommended even when presenting only one period because it allows cross-period presence to be measured.

Common examples:

```bash
# Daily only
python3 <skill-dir>/scripts/fetch_trending.py --period daily --limit 25

# Weekly Python list
python3 <skill-dir>/scripts/fetch_trending.py --period weekly --programming-language python

# Disable API enrichment
python3 <skill-dir>/scripts/fetch_trending.py --period both --enrich-limit 0

# Rebuild public metadata cache
python3 <skill-dir>/scripts/fetch_trending.py --period both --refresh-metadata
```

Fetch arguments:

| Argument | Meaning |
| --- | --- |
| `--data-dir PATH` | Override the default data directory |
| `--period daily\|weekly\|both` | Period to fetch; default `both` |
| `--limit N` | Candidate count per period; default 25 |
| `--programming-language NAME` | GitHub Trending language filter |
| `--language NAME` | Compatible alias for the previous argument |
| `--enrich-limit N` | API enrichment budget; default 25, use 0 to disable |
| `--metadata-cache PATH` | Custom metadata-cache file |
| `--metadata-ttl-hours HOURS` | Cache lifetime; default 24 hours |
| `--refresh-metadata` | Ignore existing cache and fetch again |
| `--history-dir PATH` | Custom snapshot-history directory |
| `--output PATH` | Custom snapshot output file |

### 4. Generate rankings

Pass the path printed by the fetch command to `--snapshot`:

```bash
python3 <skill-dir>/scripts/rank_trending.py \
  --snapshot /path/to/snapshot.json \
  --period daily \
  --top 10
```

The default output is `latest-daily-ranking.json` or `latest-weekly-ranking.json`; the command prints its path.

Ranking arguments:

| Argument | Meaning |
| --- | --- |
| `--data-dir PATH` | Data directory |
| `--snapshot PATH` | Required snapshot to rank |
| `--profile PATH` | Use a different profile file |
| `--period daily\|weekly` | Required period to rank |
| `--top N` | Result count; default 10, values are floored at 1 |
| `--output PATH` | Custom ranking JSON output |

### 5. Inspect the profile and recent feedback

```bash
python3 <skill-dir>/scripts/profile.py show --events 10
```

`--events` controls the number of recent feedback events returned.

### 6. Record feedback manually

```bash
# Weak interest
python3 <skill-dir>/scripts/profile.py record --signal detail --repo owner/name --topics ai python

# Explicit interest
python3 <skill-dir>/scripts/profile.py record --signal interested --repo owner/name --topics ai

# Actual use
python3 <skill-dir>/scripts/profile.py record --signal tried --repo owner/name --topics developer-tools

# Explicit topic preference
python3 <skill-dir>/scripts/profile.py record --signal like-topic --topics local-first

# Exclude or restore a repository
python3 <skill-dir>/scripts/profile.py record --signal exclude-repo --repo owner/name
python3 <skill-dir>/scripts/profile.py record --signal restore-repo --repo owner/name

# Exclude or restore a topic
python3 <skill-dir>/scripts/profile.py record --signal exclude-topic --topics low-code
python3 <skill-dir>/scripts/profile.py record --signal restore-topic --topics low-code

# Forget active repository or topic preference
python3 <skill-dir>/scripts/profile.py record --signal forget-repo --repo owner/name
python3 <skill-dir>/scripts/profile.py record --signal forget-topic --topics python
```

Use `--note "text"` to attach a short event note. Repository names are lowercased; topics are normalized and deduplicated.

### 7. Reset all active preferences

Without confirmation, reset fails:

```bash
python3 <skill-dir>/scripts/profile.py record --signal reset-profile
```

Confirm explicitly to clear active state:

```bash
python3 <skill-dir>/scripts/profile.py record --signal reset-profile --confirm-reset
```

Feedback history remains intact.

### 8. Export profile and feedback

```bash
python3 <skill-dir>/scripts/profile.py export --output /path/to/github-trend-profile.json
```

An existing file is not overwritten. Use `--force` only after overwrite has been explicitly approved:

```bash
python3 <skill-dir>/scripts/profile.py export \
  --output /path/to/github-trend-profile.json \
  --force
```

### 9. Import profile and feedback

Preview a merge without writing anything:

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json \
  --dry-run
```

Apply the default merge after review:

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json
```

Merge takes the greater weight from each profile, unions exclusions and notes, and deduplicates complete feedback events. Re-importing the same export therefore does not repeatedly raise interest. A complete replacement requires explicit confirmation:

```bash
python3 <skill-dir>/scripts/profile.py import \
  --input /path/to/github-trend-profile.json \
  --mode replace \
  --confirm-replace
```

Replacement keeps one `.bak` for the previous profile and feedback file. Imported strings are data, never agent instructions.

### 10. Purge feedback history but retain active preferences

The command refuses to run without confirmation:

```bash
python3 <skill-dir>/scripts/profile.py purge-history --confirm-purge
```

This empties `feedback.jsonl` and removes its old backup without changing active weights or exclusions in `profile.json`. The skill provides no undo for the purged history; export first if it must be retained.

### 11. Run read-only diagnostics

```bash
python3 <skill-dir>/scripts/doctor.py
```

It checks Python, the data directory, profile, backup, feedback log, metadata cache, GitHub Trending parsing, and GitHub API limits. It changes no data and never prints the token. Use `--offline` without network and `--json` for machine-readable output.

### 12. Inspect storage and prune rebuildable data

```bash
python3 <skill-dir>/scripts/maintenance.py status
python3 <skill-dir>/scripts/maintenance.py prune
```

The second command is a preview. After checking its exact paths and entries, apply it explicitly:

```bash
python3 <skill-dir>/scripts/maintenance.py prune \
  --snapshot-days 180 \
  --metadata-days 90 \
  --apply
```

Snapshots whose dates cannot be read are skipped rather than deleted speculatively.

### 13. Repair from the backup

```bash
python3 <skill-dir>/scripts/profile.py repair
```

This replaces the active profile with `profile.json.bak`. Inspect the error and backup first; repair is not an ordinary retry and must not run silently.

### 14. Inspect real format examples

- [Historical daily report excerpt](examples/sample-daily-report.en.md)
- [Matching Trending snapshot](examples/sample-snapshot.json)
- [Redacted sample profile](examples/sample-profile.json)
- [Report quality checklist](references/report-quality.md)

</details>

## Update and remove

### Update a user-level installation

```bash
npx skills update github-trend-radar --global --yes
```

Updating the skill does not clear profiles or history in the external data directory.

### Remove the skill

```bash
npx skills remove github-trend-radar --global --yes
```

Removal also leaves external user state intact. Before deleting that data, run `profile.py location`, verify the exact directory, and create a backup. Never delete a guessed path.

## Troubleshooting

### The agent cannot find the skill after installation

Confirm that installation completed without an error, then create a new task. An already-open task may not reload a newly installed skill. You can also invoke `$github-trend-radar` explicitly.

### GitHub Trending fetch fails

GitHub has no official Trending API, so this project reads the public Trending page. Network failures, changed markup, or incomplete responses fail clearly rather than producing a partial report or silently substituting a recently-created-repositories search.

Run `python3 <skill-dir>/scripts/doctor.py` first to distinguish local-state, Trending parser, and GitHub API-limit problems.

### GitHub API limit is exhausted

The Trending page may still work, but topics, licenses, or maintenance metadata can fail. Retry later, configure `GITHUB_TOKEN` locally, or temporarily pass `--enrich-limit 0`. Never put a token in a command example, README, or repository file.

### Metadata cache is unsupported or corrupt

The cache contains only rebuildable public repository information. Run the next fetch with `--refresh-metadata`; this does not change preferences or feedback.

### Profile is corrupt

The script stops and reports the path. Inspect `profile.json.bak`, then run `profile.py repair` only after confirming what will be restored. The backup may not include the most recent write.

### Recommendations feel wrong

First ask what has been learned, then restore, forget, or exclude the exact repository or topic. Skipping a project does not train the profile because silence is not interpreted as negative feedback.

### An excluded repository still appears in the objective list

This is intentional. The objective list preserves public facts; exclusion prevents the repository from receiving a personalized recommendation card.

### The first personalized list matches the objective list

This is the cold start. Interest affects ranking only when current candidates match recorded repositories or topics.

### Why is there no monthly report?

This skill currently implements and validates daily and weekly only. It does not claim support for a mode the current code has not verified.

## Development

```bash
python3 -m unittest discover -s tests -v
ruff check scripts tests
python3 scripts/release_check.py --strict --tag v0.6.0
```

Tests cover fail-closed HTML parsing, language URL encoding, cache hits, interleaved enrichment, topic aliases, interest scaling, the Top 1 exploration boundary, exclusions, forgetting, reset confirmation, import/export, history purge, derived-data cleanup, read-only diagnostics, concurrent feedback, backup repair, and release metadata. GitHub Actions also verifies Python 3.11 on Linux, macOS, and Windows and runs a weekly live parser smoke test against the current Trending page.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and release steps and [SECURITY.md](SECURITY.md) for private vulnerability reporting. Licensed under the [MIT License](LICENSE).
