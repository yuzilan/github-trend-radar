# Changelog

All notable changes to GitHub Trend Radar are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [0.6.1] - 2026-09-14

### Fixed

- Accepted GitHub Trending entries with a legitimate zero period star gain,
  while continuing to reject missing, negative, or malformed ranking metrics.
- Prevented valid lower-ranked entries on smaller programming-language lists
  from causing an otherwise usable Top N request to fail.

## [0.6.0] - 2026-09-14

### Added

- Confirmation-protected profile import, merge/replace modes, dry-run previews,
  and idempotent feedback merging.
- Separate feedback-history purge while preserving the active profile.
- Read-only local/network diagnostics and derived-data storage inspection.
- Preview-first retention cleanup for snapshots and repository metadata cache.
- Conservative canonical aliases for common repository topics.
- Real historical snapshot/profile/report examples and a behavioral report
  quality evaluation guide.
- macOS and Windows compatibility CI, plus a weekly live Trending parser smoke
  test.
- Structured bug, feature, pull request, and private security report templates.

### Fixed

- URL-encoded programming-language paths so names such as `C#` cannot swallow
  the requested Trending period query.
- Renamed GitHub's combined issue and pull-request count field to
  `open_issues_and_pull_requests` to avoid claiming it contains issues only.

### Changed

- Expanded the bilingual tutorial with a compact table of contents, profile
  portability, diagnostics, retention, examples, and canonical topic behavior.
- Added a report-quality checklist to the runtime workflow without making the
  primary Skill instructions unnecessarily long.

## [0.5.0] - 2026-09-14

### Fixed

- Calibrated interest against a fixed ten-point scale so one weak `detail`
  event no longer receives the full personalization bonus.
- Disabled the exploration override for `Top 1` requests.
- Clarified that the recommended Skills CLI installation is user-level.

### Added

- `forget-repo`, `forget-topic`, and confirmation-protected `reset-profile`
  feedback controls.
- Portable profile and feedback export with overwrite protection.
- Interleaved daily/weekly GitHub metadata enrichment, a 24-hour local cache,
  transient API retry handling, and enrichment audit counts in snapshots.
- User-oriented installation, first-run, feedback, privacy, update, and
  troubleshooting guidance in both READMEs.

### Changed

- GitHub metadata enrichment now covers up to 25 interleaved candidates by
  default; pass `--enrich-limit 0` to disable it.
- Added `--programming-language` while retaining `--language` as a compatible
  alias.

## [0.4.0] - 2026-09-14

### Changed

- Aligned the public repository name, skill identifier, and skill directory as
  `github-trend-radar`.
- Replaced publishing placeholders with the final GitHub and Skills CLI paths.
- Added a machine-readable `REPOSITORY` identity checked against both READMEs.
- Enabled strict release validation for tag `v0.4.0`.
- Updated the official checkout and Python setup Actions to their Node.js 24-based
  stable major versions.

## [0.3.0] - 2026-09-13

### Added

- Public contribution, security, and release documentation.
- GitHub Actions checks for Python 3.9, 3.11, and 3.13.
- A deterministic release checker for required files, version consistency, and
  unresolved publishing placeholders.
- Package-level tests for the release checker.

### Changed

- Expanded the English and Chinese READMEs with versioning, contribution, and
  release-verification instructions.

## [0.2.0] - 2026-09-13

### Added

- Validated HTML parsing with fail-closed behavior.
- Retry handling for transient GitHub failures.
- Tie-aware ranking and exact repository preferences.
- Schema-v2 preference migration, locking, atomic writes, backup, and repair.
- Tests for parsing, ranking, migration, recovery, and concurrent updates.

## [0.1.0] - 2026-09-13

### Added

- Initial daily and weekly GitHub Trending collection.
- Objective and personalized Top 10 ranking.
- Transparent local topic and repository feedback.
