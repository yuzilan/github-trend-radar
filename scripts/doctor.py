#!/usr/bin/env python3
"""Run read-only local and network diagnostics for GitHub Trend Radar."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from fetch_trending import METADATA_CACHE_SCHEMA, USER_AGENT, fetch_url, parse_page, trending_url
from profile import migrate_profile, recent_events, validate_feedback
from state import StateError, backup_path, load_json, resolve_data_dir


def check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def local_checks(data_dir_value: Path | str | None) -> list[dict]:
    data_dir = resolve_data_dir(data_dir_value)
    results = [
        check(
            "python",
            "pass" if sys.version_info >= (3, 9) else "fail",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    ]
    probe_parent = data_dir
    while not probe_parent.exists() and probe_parent != probe_parent.parent:
        probe_parent = probe_parent.parent
    results.append(check("data-directory", "pass" if probe_parent.exists() and os.access(probe_parent, os.W_OK) else "fail", str(data_dir)))

    profile_path = data_dir / "profile.json"
    if not profile_path.exists():
        results.append(check("profile", "warn", "not initialized; run profile.py init"))
    else:
        try:
            profile = migrate_profile(load_json(profile_path))
            results.append(check("profile", "pass", f"schema {profile['schema_version']}"))
        except StateError as error:
            results.append(check("profile", "fail", str(error)))
    profile_backup = backup_path(profile_path)
    if profile_backup.exists():
        try:
            migrate_profile(load_json(profile_backup))
            results.append(check("profile-backup", "pass", str(profile_backup)))
        except StateError as error:
            results.append(check("profile-backup", "fail", str(error)))

    feedback_path = data_dir / "feedback.jsonl"
    try:
        events = recent_events(feedback_path, 2**31 - 1)
        validate_feedback(events)
        event_count = len(events)
        results.append(check("feedback", "pass" if feedback_path.exists() else "warn", f"{event_count} events"))
    except StateError as error:
        results.append(check("feedback", "fail", str(error)))

    cache_path = data_dir / "repository-metadata.json"
    if cache_path.exists():
        try:
            cache = load_json(cache_path)
            valid = cache.get("schema_version") == METADATA_CACHE_SCHEMA and isinstance(cache.get("repositories"), dict)
            results.append(check("metadata-cache", "pass" if valid else "fail", f"{len(cache.get('repositories', {})) if valid else 0} entries"))
        except StateError as error:
            results.append(check("metadata-cache", "fail", str(error)))
    else:
        results.append(check("metadata-cache", "warn", "not created yet"))
    return results


def network_checks() -> list[dict]:
    results: list[dict] = []
    try:
        rows = parse_page(fetch_url(trending_url("daily")), "daily", 10)
        results.append(check("github-trending", "pass", f"parsed {len(rows)} repositories"))
    except (StateError, OSError, ValueError) as error:
        results.append(check("github-trending", "fail", str(error)))

    request = urllib.request.Request(
        "https://api.github.com/rate_limit",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
        core = payload.get("resources", {}).get("core", {})
        results.append(check("github-api", "pass", f"remaining {core.get('remaining', '?')} of {core.get('limit', '?')}; reset {core.get('reset', '?')}"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        results.append(check("github-api", "fail", f"{type(error).__name__}: {error}"))
    return results


def diagnose(data_dir_value: Path | str | None, *, offline: bool = False) -> dict:
    checks = local_checks(data_dir_value)
    if offline:
        checks.append(check("network", "skip", "offline mode"))
    else:
        checks.extend(network_checks())
    return {
        "ok": not any(item["status"] == "fail" for item in checks),
        "data_dir": str(resolve_data_dir(data_dir_value)),
        "checks": checks,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--offline", action="store_true", help="skip GitHub connectivity and API checks")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = diagnose(args.data_dir, offline=args.offline)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            print(f"[{item['status'].upper():4}] {item['name']}: {item['detail']}")
        print("Ready." if report["ok"] else "Problems found; see FAIL checks above.")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
