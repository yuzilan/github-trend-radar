#!/usr/bin/env python3
"""Validate repository structure and release metadata without third-party packages."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REQUIRED_PATHS = (
    ".github/workflows/ci.yml",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "README_zh-CN.md",
    "REPOSITORY",
    "SECURITY.md",
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "references/ranking-and-feedback.md",
    "scripts/fetch_trending.py",
    "scripts/profile.py",
    "scripts/rank_trending.py",
    "scripts/release_check.py",
    "scripts/state.py",
    "tests/test_core.py",
    "tests/test_release.py",
)
PUBLISHING_PLACEHOLDER = "<owner>/<repository>"


def validate(root: Path, *, strict: bool = False, tag: str | None = None) -> tuple[list[str], list[str]]:
    """Return blocking errors and non-blocking warnings for a repository root."""
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_PATHS:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    version_path = root / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else ""
    if not SEMVER.fullmatch(version):
        errors.append("VERSION must contain one semantic version such as 1.2.3")

    changelog_path = root / "CHANGELOG.md"
    if version and changelog_path.is_file():
        changelog = changelog_path.read_text(encoding="utf-8")
        if not re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE):
            errors.append(f"CHANGELOG.md has no dated section for version {version}")

    if tag:
        expected = f"v{version}"
        if tag != expected:
            errors.append(f"release tag {tag!r} does not match VERSION; expected {expected!r}")

    repository_path = root / "REPOSITORY"
    repository = repository_path.read_text(encoding="utf-8").strip() if repository_path.is_file() else ""
    if not REPOSITORY_NAME.fullmatch(repository):
        errors.append("REPOSITORY must contain one GitHub owner/name value")

    placeholder_files: list[str] = []
    for relative in ("README.md", "README_zh-CN.md"):
        path = root / relative
        if path.is_file():
            contents = path.read_text(encoding="utf-8")
            if version and f"`{version}`" not in contents:
                errors.append(f"{relative} does not identify current version {version}")
            if repository and repository not in contents:
                errors.append(f"{relative} does not identify repository {repository}")
            if PUBLISHING_PLACEHOLDER in contents:
                placeholder_files.append(relative)
    if placeholder_files:
        message = "publishing placeholder remains in: " + ", ".join(placeholder_files)
        (errors if strict else warnings).append(message)

    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="treat publishing placeholders as errors")
    parser.add_argument("--tag", help="release tag to compare with VERSION, for example v1.2.3")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors, warnings = validate(args.root.resolve(), strict=args.strict, tag=args.tag)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Release metadata is consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
