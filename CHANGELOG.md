# Changelog

All notable changes to GitHub Trend Radar are documented here. The project follows
[Semantic Versioning](https://semver.org/).

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
