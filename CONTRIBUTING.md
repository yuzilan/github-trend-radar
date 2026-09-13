# Contributing

Thank you for helping improve GitHub Trend Radar. Small, reviewable changes with
observable tests are preferred.

## Development setup

The runtime scripts require Python 3.9 or newer and use only the standard library.
Install Ruff only when you want to run the same lint check as CI:

```bash
python3 -m pip install ruff==0.15.1
```

Run the checks from the repository root:

```bash
python3 -m unittest discover -s tests -v
ruff check scripts tests
python3 scripts/release_check.py
```

## Change boundaries

- Keep objective popularity separate from personalized relevance.
- Never infer negative preferences from silence.
- Do not broaden repository exclusions into topic exclusions.
- Do not install or execute trending repositories as part of discovery.
- Do not silently replace GitHub Trending with a different data source.
- Keep user state outside the skill directory and preserve existing migrations.

Add or update tests for behavioral changes. Do not include local snapshots,
profiles, feedback logs, tokens, or generated rankings in a pull request.

## Releasing

1. Update `VERSION` using semantic versioning.
2. Add a matching dated section to `CHANGELOG.md`.
3. Confirm that `REPOSITORY` and both README installation commands identify the
   intended public GitHub repository.
4. Run `python3 scripts/release_check.py --strict --tag vX.Y.Z`.
5. Create the matching Git tag only after all checks pass.

The repository maintainer controls publishing and release credentials. A pull
request must not publish packages, create releases, or modify remote settings.
