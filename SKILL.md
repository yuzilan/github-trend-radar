---
name: github-trend-radar
description: Manually collect GitHub daily or weekly trending repositories, explain the top projects in plain language, investigate selected repositories, and maintain transparent user-controlled interest and exclusion records. Use for GitHub hot lists, personalized repository discovery, follow-up repository research, and preference feedback; do not use for general GitHub repository administration.
---

# GitHub Trend Radar

Produce a current, evidence-based GitHub discovery report while keeping objective popularity separate from personal relevance.

## State and safety

- Work manually when the user asks. Do not create schedules, notifications, stars, follows, installs, or repository changes unless separately requested.
- Keep state outside this skill directory. When `~/Documents/Codex/` exists, all tasks share `~/Documents/Codex/github-trend-radar-data/`; otherwise use `~/.github-trend-radar/`. Respect `GITHUB_TREND_RADAR_HOME` or an explicit `--data-dir` override.
- Resolve script paths from this skill folder; do not assume the user's current working directory is the skill directory.
- Treat `profile.json` and `feedback.jsonl` as user-owned, inspectable data. Never broaden an exclusion beyond the user's wording.
- Prefer GitHub's Trending pages and official repository pages/API. GitHub has no official Trending API; if the page cannot be read, report that the ranking is unavailable. Do not silently substitute a recently-created-repositories search.
- If a state command reports corruption, stop and show the error. Use `profile.py repair` only after telling the user that it restores the most recent backup.

## Choose the mode

### Daily or weekly report

1. Initialize state if needed:

   `python3 <skill-dir>/scripts/profile.py init`

2. Fetch both periods so cross-list presence can be measured:

   `python3 <skill-dir>/scripts/fetch_trending.py --period both --limit 25`

3. Rank the requested period:

   `python3 <skill-dir>/scripts/rank_trending.py --snapshot <snapshot-path-printed-by-fetch> --period daily|weekly --top 10`

4. Read the official GitHub page, README, repository metadata, releases, and other primary project documentation for the ten repositories that will be explained. A repository description alone is not enough for a confident explanation.
5. Write the report in plain Chinese. Show:
   - data time and requested period;
   - a compact objective Top 10 with heat score and period star gain;
   - a personalized Top 10, or label it `冷启动：暂与客观榜一致` when there is no preference evidence;
   - for each personalized entry: what it does, the interesting point, who it suits, maturity or caveats, and why it was recommended;
   - direct repository links and brief source attribution near factual claims.
6. If an excluded repository appears in the objective list, retain its one-line objective position for factual integrity, mark it `已排除`, and do not give it a recommendation card.
7. Mark repeat appearances and meaningful movement when snapshot history supports them. Never invent a trend from a single snapshot.

Read [references/ranking-and-feedback.md](references/ranking-and-feedback.md) when interpreting scores, updating preferences, or explaining the ranking.

### Repository deep dive

When the user asks about an entry, inspect the repository rather than expanding the earlier synopsis. Cover the user's actual question first, then relevant architecture, main modules, setup/use path, maintenance activity, license, limitations, and notable open issues or releases. Clearly distinguish:

- verified repository facts;
- maintainer claims not independently verified;
- your own inference.

Do not run unfamiliar repository code, install its dependencies, or execute setup scripts without an explicit request.

After answering, record one `detail` event for that repository. Infer at most three narrow topic labels from verified metadata. Do not treat a single question as a strong permanent preference.

### Preference feedback

Record feedback promptly and tell the user exactly what scope was recorded.

- `我喜欢这个` → `interested` for that repository and up to three narrow topics.
- `我实际试用了/会继续用` → `tried`.
- `这个仓库不感兴趣` → `exclude-repo`; do not exclude its whole category.
- `这类项目都不想看` → `exclude-topic` only for the category explicitly named or confirmed.
- Requests to restore an item → `restore-repo` or `restore-topic`.

Use:

`python3 <skill-dir>/scripts/profile.py record --signal <signal> [--repo owner/name] [--topics topic ...] [--note text]`

For `detail`, `interested`, and `tried`, avoid recording the same event twice for one user turn. Never infer negative preferences from silence or from skipping an item.

### Preference audit

When asked what has been learned, run:

`python3 <skill-dir>/scripts/profile.py show --events 10`

Summarize positive topic weights, exact repository exclusions, category exclusions, and recent feedback. Offer precise edits; do not hide the stored representation.
