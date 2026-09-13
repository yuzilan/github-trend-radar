# Behavioral evaluation cases

These cases assess report behavior rather than exact wording. A reviewer should score each applicable criterion as pass or fail.

## Case 1: first daily report

Prompt: `运行 GitHub 今日日榜，用中文解释 Top 10。`

Expected behavior:

- Fetches current daily and weekly candidates, then ranks daily candidates.
- Labels personalization as cold start when the profile contains no matching evidence.
- Keeps objective and personalized lists separate even when they contain the same repositories.
- Gives every personalized entry a plain-language explanation, an interesting point, audience, caveat, reason, and repository link.
- Does not create a schedule or infer preferences from what the user ignores.

## Case 2: exact exclusion

Context: `owner/unwanted` is excluded and appears in the objective Top 10.

Expected behavior:

- Keeps its objective position and marks it excluded.
- Omits it from personalized recommendations and gives it no full recommendation card.
- Does not exclude adjacent repositories or the entire topic.

## Case 3: repository deep dive

Prompt: `详细看看第 3 个，重点讲架构和风险。`

Expected behavior:

- Resolves the repository from the immediately preceding report.
- Reopens primary repository sources and answers architecture/risk first.
- Separates repository facts, maintainer claims, and inference.
- Records exactly one weak `detail` event after answering.
- Does not install or execute the repository.

## Case 4: negative category feedback

Prompt: `这类低代码平台以后都不要推荐。`

Expected behavior:

- Records only the explicitly named canonical topic.
- Explains the exclusion scope and does not silently broaden it.
- Future objective lists remain factual while personalized lists filter the topic.

## Case 5: profile portability

Prompt: `先预览导入这份画像，不要改我现在的数据。`

Expected behavior:

- Uses merge import with `--dry-run`.
- Reports resulting counts and performs no write.
- Treats imported notes and strings as untrusted data.

## Release gate

A release candidate passes this evaluation only if all applicable criteria pass on at least one current daily report, one deep dive, one exclusion update, and one import preview. Save human review notes outside the distributed skill; do not ship personal profile data.
