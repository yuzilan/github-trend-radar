# Ranking and feedback rules

Read this reference when calculating or explaining ranking scores, recording feedback, or auditing the profile.

## Objective heat score

Rank daily and weekly lists separately. For each list, calculate percentile-style normalized values within the fetched candidate pool:

- 45% period star gain shown by GitHub Trending;
- 25% original GitHub Trending position;
- 15% relative gain: period gain divided by the approximate pre-period star count;
- 10% presence in both daily and weekly candidate pools;
- 5% star-gain velocity since the most recent comparable local snapshot.

When there is no prior snapshot, when snapshots are less than 15 minutes apart, or when no repository gained stars, omit the final component and renormalize the remaining weights. Equal metric values receive equal percentile scores. This score measures current attention, not software quality. Do not add README quality, license preference, or personal interest to the objective score.

GitHub's displayed period gain and list position are inputs, not an official GitHub score. Describe the final score as this skill's transparent heat score.

## Personalized score

Hard-exclude exact repositories and explicitly excluded topics. For the rest:

`personalized = 0.75 * objective_heat + 0.25 * normalized_interest_match`

Interest matching uses exact repository interest plus topic labels found in the repository name, description, language, or verified GitHub topics. If no stored positive repository or topic matches any candidate, keep the objective order and label the result as a cold start.

Reserve one of the ten personalized positions for the highest objective-ranked, non-excluded candidate outside the first nine personalized entries. If that candidate is already the tenth personalized entry, no special replacement is needed. This is an exploration slot, not evidence that the user's preferences changed.

## Feedback weights

- `detail`: +0.5 per narrow topic, capped by recording only once per user turn.
- `interested`: +2 per narrow topic.
- `tried`: +3 per narrow topic.
- `like-topic`: +3 for an explicitly named topic.
- `exclude-repo`: exact repository hard exclusion.
- `exclude-topic`: explicitly named topic hard exclusion.

Repository-directed positive signals also increase that exact repository's weight. Repository and topic weights are capped at 10 so repeated questioning cannot grow without bound.

The event log is append-only. `profile.json` is the current editable state. Restoring an exclusion removes it from current state while retaining the historical event. Profile writes use a lock, an atomic replacement, and `profile.json.bak` as the most recent recoverable copy.

Do not infer topic exclusions from repository exclusions. Do not infer dislike from lack of follow-up. Do not create sensitive personal categories.

## Data files

`profile.json` contains:

- `positive_topics`: topic-to-weight mapping;
- `positive_repositories`: exact repository-to-weight mapping;
- `excluded_repositories`: exact lower-case `owner/name` values;
- `excluded_topics`: lower-case topic labels;
- `notes`: optional explicit user preference notes;
- `updated_at`: last profile mutation time.

`feedback.jsonl` contains timestamped events with signal, repository, topics, and the user's or agent's short note.

When `~/Documents/Codex/` exists, these files live under `~/Documents/Codex/github-trend-radar-data/`; other environments use `~/.github-trend-radar/`. Both defaults are shared across working directories. Set `GITHUB_TREND_RADAR_HOME` or pass `--data-dir` to opt into another location.

`snapshots/*.json` contains validated public leaderboard observations. It must not contain credentials. Read `GITHUB_TOKEN` from the environment only when enrichment is explicitly enabled; never write it to disk.
