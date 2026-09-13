# Security Policy

## Supported versions

Security fixes are applied to the latest released version.

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting feature when it is enabled for
the repository. Do not include access tokens, private profile data, or unpublished
exploit details in a public issue.

This skill reads public GitHub pages and optionally reads `GITHUB_TOKEN` from the
process environment. It must never store that token in snapshots, logs, profiles,
or repository files.

The skill does not install or execute code from trending repositories. A request
to run third-party repository code is a separate action and requires explicit user
authorization and an appropriate safety review.
