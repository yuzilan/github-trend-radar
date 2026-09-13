#!/usr/bin/env python3
"""Initialize, update, repair, and inspect recommendation preferences."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from state import (
    StateError,
    append_jsonl,
    atomic_write_json,
    load_json,
    resolve_data_dir,
    restore_backup,
    state_lock,
)


SIGNAL_WEIGHTS = {"detail": 0.5, "interested": 2.0, "tried": 3.0, "like-topic": 3.0}
SIGNALS = tuple(SIGNAL_WEIGHTS) + (
    "exclude-repo",
    "exclude-topic",
    "restore-repo",
    "restore-topic",
)
MAX_WEIGHT = 10.0


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def default_profile() -> dict:
    return {
        "schema_version": 2,
        "positive_repositories": {},
        "positive_topics": {},
        "excluded_repositories": [],
        "excluded_topics": [],
        "notes": [],
        "updated_at": None,
    }


def paths(data_dir: Path) -> tuple[Path, Path]:
    return data_dir / "profile.json", data_dir / "feedback.jsonl"


def migrate_profile(profile: dict) -> dict:
    migrated = default_profile()
    migrated.update(profile)
    migrated["schema_version"] = 2
    migrated.setdefault("positive_repositories", {})
    return migrated


def initialize(data_dir_value: Path | str | None) -> tuple[Path, dict]:
    data_dir = resolve_data_dir(data_dir_value)
    data_dir.mkdir(parents=True, exist_ok=True)
    profile_path, feedback_path = paths(data_dir)
    with state_lock(data_dir):
        if not profile_path.exists():
            atomic_write_json(profile_path, default_profile())
        if not feedback_path.exists():
            feedback_path.touch(mode=0o600)
        original = load_json(profile_path)
        profile = migrate_profile(original)
        if profile != original:
            atomic_write_json(profile_path, profile, backup=True)
    return data_dir, profile


def normalized(values: list[str] | None) -> list[str]:
    return sorted({value.strip().lower() for value in (values or []) if value.strip()})


def increase(mapping: dict, keys: list[str], weight: float) -> None:
    for key in keys:
        mapping[key] = round(min(MAX_WEIGHT, float(mapping.get(key, 0)) + weight), 2)


def apply_event(profile: dict, event: dict) -> dict:
    signal = event["signal"]
    repo = event.get("repository") or ""
    topics = event.get("topics") or []
    if signal in SIGNAL_WEIGHTS:
        weight = SIGNAL_WEIGHTS[signal]
        increase(profile.setdefault("positive_topics", {}), topics, weight)
        if repo and signal != "like-topic":
            increase(profile.setdefault("positive_repositories", {}), [repo], weight)
    elif signal == "exclude-repo":
        profile.setdefault("excluded_repositories", []).append(repo)
    elif signal == "exclude-topic":
        profile.setdefault("excluded_topics", []).extend(topics)
    elif signal == "restore-repo":
        profile["excluded_repositories"] = [value for value in profile.get("excluded_repositories", []) if value != repo]
    elif signal == "restore-topic":
        profile["excluded_topics"] = [value for value in profile.get("excluded_topics", []) if value not in topics]

    profile["excluded_repositories"] = sorted(set(profile.get("excluded_repositories", [])))
    profile["excluded_topics"] = sorted(set(profile.get("excluded_topics", [])))
    profile["positive_repositories"] = dict(sorted(profile.get("positive_repositories", {}).items()))
    profile["positive_topics"] = dict(sorted(profile.get("positive_topics", {}).items()))
    if event.get("note") and signal == "like-topic":
        profile.setdefault("notes", []).append(event["note"])
    profile["updated_at"] = event["timestamp"]
    return profile


def validate_event(signal: str, repo: str, topics: list[str]) -> None:
    if signal in ("detail", "interested", "tried", "exclude-repo", "restore-repo") and not repo:
        raise StateError(f"--repo is required for {signal}")
    if signal in ("exclude-topic", "restore-topic", "like-topic") and not topics:
        raise StateError(f"--topics is required for {signal}")


def record_event(
    data_dir_value: Path | str | None,
    *,
    signal: str,
    repo: str = "",
    topics: list[str] | None = None,
    note: str = "",
) -> tuple[Path, dict]:
    data_dir, _ = initialize(data_dir_value)
    profile_path, feedback_path = paths(data_dir)
    normalized_repo = repo.strip().lower()
    normalized_topics = normalized(topics)
    validate_event(signal, normalized_repo, normalized_topics)
    event = {
        "timestamp": now(),
        "signal": signal,
        "repository": normalized_repo or None,
        "topics": normalized_topics,
        "note": note.strip() or None,
    }
    with state_lock(data_dir):
        profile = migrate_profile(load_json(profile_path))
        updated = apply_event(profile, event)
        append_jsonl(feedback_path, event)
        atomic_write_json(profile_path, updated, backup=True)
    return data_dir, event


def recent_events(path: Path, count: int) -> list[dict]:
    if not path.exists() or count <= 0:
        return []
    events: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise StateError(f"invalid JSONL event at {path}:{line_number}") from error
        if not isinstance(event, dict):
            raise StateError(f"event must be an object at {path}:{line_number}")
        events.append(event)
    return events[-count:]


def show_state(data_dir_value: Path | str | None, event_count: int) -> dict:
    data_dir = resolve_data_dir(data_dir_value)
    profile_path, feedback_path = paths(data_dir)
    if profile_path.exists():
        profile = migrate_profile(load_json(profile_path))
    else:
        data_dir, profile = initialize(data_dir)
    return {
        "data_dir": str(data_dir),
        "profile": profile,
        "recent_feedback": recent_events(feedback_path, event_count),
    }


def repair(data_dir_value: Path | str | None) -> Path:
    data_dir = resolve_data_dir(data_dir_value)
    profile_path, _ = paths(data_dir)
    with state_lock(data_dir):
        restore_backup(profile_path)
    return profile_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("init", "location", "repair"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-dir", type=Path)

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--data-dir", type=Path)
    record_parser.add_argument("--signal", choices=SIGNALS, required=True)
    record_parser.add_argument("--repo", default="")
    record_parser.add_argument("--topics", nargs="*")
    record_parser.add_argument("--note", default="")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--data-dir", type=Path)
    show_parser.add_argument("--events", type=int, default=10)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "location":
            print(resolve_data_dir(args.data_dir))
        elif args.command == "init":
            data_dir, profile = initialize(args.data_dir)
            print(json.dumps({"data_dir": str(data_dir), "profile": profile}, ensure_ascii=False, indent=2))
        elif args.command == "record":
            data_dir, event = record_event(
                args.data_dir,
                signal=args.signal,
                repo=args.repo,
                topics=args.topics,
                note=args.note,
            )
            print(json.dumps({"data_dir": str(data_dir), "event": event}, ensure_ascii=False, indent=2))
        elif args.command == "repair":
            print(repair(args.data_dir))
        else:
            print(json.dumps(show_state(args.data_dir, args.events), ensure_ascii=False, indent=2))
    except StateError as error:
        print(f"ERROR: {error}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
