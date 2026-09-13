#!/usr/bin/env python3
"""Initialize, update, repair, and inspect recommendation preferences."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

from state import (
    StateError,
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    backup_path,
    load_json,
    resolve_data_dir,
    restore_backup,
    state_lock,
)
from topics import canonical_topic, normalize_topics


SIGNAL_WEIGHTS = {"detail": 0.5, "interested": 2.0, "tried": 3.0, "like-topic": 3.0}
SIGNALS = tuple(SIGNAL_WEIGHTS) + (
    "exclude-repo",
    "exclude-topic",
    "restore-repo",
    "restore-topic",
    "forget-repo",
    "forget-topic",
    "reset-profile",
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
    if not isinstance(profile, dict):
        raise StateError("profile must be a JSON object")
    migrated = default_profile()
    migrated.update(profile)
    migrated["schema_version"] = 2
    positive_repositories = migrated.get("positive_repositories", {})
    positive_topics = migrated.get("positive_topics", {})
    excluded_repositories = migrated.get("excluded_repositories", [])
    excluded_topics = migrated.get("excluded_topics", [])
    notes = migrated.get("notes", [])
    if not isinstance(positive_repositories, dict) or not isinstance(positive_topics, dict):
        raise StateError("profile positive weights must be JSON objects")
    if not isinstance(excluded_repositories, list) or not isinstance(excluded_topics, list) or not isinstance(notes, list):
        raise StateError("profile exclusions and notes must be JSON arrays")

    canonical_repositories: dict[str, float] = {}
    for repository, weight in positive_repositories.items():
        normalized_repository = str(repository).strip().lower()
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError) as error:
            raise StateError(f"invalid repository weight for {repository}") from error
        if not normalized_repository or not math.isfinite(numeric_weight) or numeric_weight < 0:
            raise StateError(f"invalid repository weight for {repository}")
        canonical_repositories[normalized_repository] = min(MAX_WEIGHT, numeric_weight)
    migrated["positive_repositories"] = dict(sorted(canonical_repositories.items()))

    canonical_weights: dict[str, float] = {}
    for topic, weight in positive_topics.items():
        canonical = canonical_topic(str(topic))
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError) as error:
            raise StateError(f"invalid topic weight for {topic}") from error
        if not canonical or not math.isfinite(numeric_weight) or numeric_weight < 0:
            raise StateError(f"invalid topic weight for {topic}")
        if canonical:
            canonical_weights[canonical] = min(MAX_WEIGHT, canonical_weights.get(canonical, 0.0) + numeric_weight)
    migrated["positive_topics"] = dict(sorted(canonical_weights.items()))
    migrated["excluded_repositories"] = sorted(
        {str(value).strip().lower() for value in excluded_repositories if str(value).strip()}
    )
    migrated["excluded_topics"] = normalize_topics([str(value) for value in excluded_topics])[0]
    migrated["notes"] = [str(value) for value in notes if str(value).strip()]
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
    return normalize_topics(values)[0]


def increase(mapping: dict, keys: list[str], weight: float) -> None:
    for key in keys:
        mapping[key] = round(min(MAX_WEIGHT, float(mapping.get(key, 0)) + weight), 2)


def apply_event(profile: dict, event: dict) -> dict:
    signal = event["signal"]
    repo = event.get("repository") or ""
    topics = event.get("topics") or []
    if signal == "reset-profile":
        profile = default_profile()
    elif signal in SIGNAL_WEIGHTS:
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
    elif signal == "forget-repo":
        profile.setdefault("positive_repositories", {}).pop(repo, None)
        profile["excluded_repositories"] = [value for value in profile.get("excluded_repositories", []) if value != repo]
    elif signal == "forget-topic":
        for topic in topics:
            profile.setdefault("positive_topics", {}).pop(topic, None)
        profile["excluded_topics"] = [value for value in profile.get("excluded_topics", []) if value not in topics]

    profile["excluded_repositories"] = sorted(set(profile.get("excluded_repositories", [])))
    profile["excluded_topics"] = sorted(set(profile.get("excluded_topics", [])))
    profile["positive_repositories"] = dict(sorted(profile.get("positive_repositories", {}).items()))
    profile["positive_topics"] = dict(sorted(profile.get("positive_topics", {}).items()))
    if event.get("note") and signal == "like-topic":
        profile.setdefault("notes", []).append(event["note"])
    profile["updated_at"] = event["timestamp"]
    return profile


def validate_event(signal: str, repo: str, topics: list[str], *, confirm_reset: bool = False) -> None:
    if signal not in SIGNALS:
        raise StateError(f"unknown feedback signal: {signal}")
    if signal in ("detail", "interested", "tried", "exclude-repo", "restore-repo", "forget-repo") and not repo:
        raise StateError(f"--repo is required for {signal}")
    if signal in ("exclude-topic", "restore-topic", "like-topic", "forget-topic") and not topics:
        raise StateError(f"--topics is required for {signal}")
    if signal == "reset-profile" and not confirm_reset:
        raise StateError("--confirm-reset is required for reset-profile")


def record_event(
    data_dir_value: Path | str | None,
    *,
    signal: str,
    repo: str = "",
    topics: list[str] | None = None,
    note: str = "",
    confirm_reset: bool = False,
) -> tuple[Path, dict]:
    data_dir, _ = initialize(data_dir_value)
    profile_path, feedback_path = paths(data_dir)
    normalized_repo = repo.strip().lower()
    normalized_topics, topic_aliases = normalize_topics(topics)
    validate_event(signal, normalized_repo, normalized_topics, confirm_reset=confirm_reset)
    event = {
        "timestamp": now(),
        "signal": signal,
        "repository": normalized_repo or None,
        "topics": normalized_topics,
        "note": note.strip() or None,
    }
    if topic_aliases:
        event["topic_aliases"] = topic_aliases
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


def export_state(data_dir_value: Path | str | None, output: Path, *, force: bool = False) -> Path:
    data_dir = resolve_data_dir(data_dir_value)
    profile_path, feedback_path = paths(data_dir)
    output = output.expanduser().resolve()
    if output.exists() and not force:
        raise StateError(f"export already exists; pass --force to replace it: {output}")
    with state_lock(data_dir):
        profile = migrate_profile(load_json(profile_path))
        feedback = recent_events(feedback_path, 2**31 - 1)
        atomic_write_json(
            output,
            {
                "schema_version": 1,
                "exported_at": now(),
                "profile": profile,
                "feedback": feedback,
            },
        )
    return output


def validate_feedback(events: object) -> list[dict]:
    if not isinstance(events, list):
        raise StateError("import feedback must be a JSON array")
    validated: list[dict] = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise StateError(f"import feedback event {index} must be an object")
        signal = event.get("signal")
        repository = event.get("repository")
        topics = event.get("topics", [])
        timestamp = event.get("timestamp")
        if repository is not None and not isinstance(repository, str):
            raise StateError(f"import feedback event {index} has invalid repository")
        if not isinstance(topics, list) or not all(isinstance(topic, str) for topic in topics):
            raise StateError(f"import feedback event {index} has invalid topics")
        if not isinstance(timestamp, str) or not timestamp:
            raise StateError(f"import feedback event {index} has invalid timestamp")
        try:
            parsed_timestamp = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as error:
            raise StateError(f"import feedback event {index} has invalid timestamp") from error
        if parsed_timestamp.tzinfo is None:
            raise StateError(f"import feedback event {index} timestamp must include a timezone")
        if event.get("note") is not None and not isinstance(event.get("note"), str):
            raise StateError(f"import feedback event {index} has invalid note")
        normalized_repository = (repository or "").strip().lower()
        normalized_topics, topic_aliases = normalize_topics(topics)
        validate_event(str(signal), normalized_repository, normalized_topics, confirm_reset=True)
        normalized_event = dict(event)
        normalized_event["signal"] = signal
        normalized_event["repository"] = normalized_repository or None
        normalized_event["topics"] = normalized_topics
        if topic_aliases:
            normalized_event["topic_aliases"] = topic_aliases
        validated.append(normalized_event)
    return validated


def read_import(path: Path) -> tuple[dict, list[dict]]:
    payload = load_json(path.expanduser().resolve())
    if payload.get("schema_version") != 1:
        raise StateError("unsupported profile export schema")
    profile_value = payload.get("profile")
    if not isinstance(profile_value, dict):
        raise StateError("import profile must be a JSON object")
    return migrate_profile(profile_value), validate_feedback(payload.get("feedback"))


def merge_profiles(current: dict, incoming: dict) -> dict:
    merged = migrate_profile(current)
    for key in ("positive_repositories", "positive_topics"):
        for name, weight in incoming.get(key, {}).items():
            merged[key][name] = max(float(merged[key].get(name, 0.0)), float(weight))
        merged[key] = dict(sorted(merged[key].items()))
    merged["excluded_repositories"] = sorted(
        set(merged.get("excluded_repositories", [])) | set(incoming.get("excluded_repositories", []))
    )
    merged["excluded_topics"] = sorted(set(merged.get("excluded_topics", [])) | set(incoming.get("excluded_topics", [])))
    merged["notes"] = list(dict.fromkeys([*merged.get("notes", []), *incoming.get("notes", [])]))
    merged["updated_at"] = now()
    return merged


def unique_feedback(events: list[dict]) -> list[dict]:
    unique: list[dict] = []
    seen: set[str] = set()
    for event in events:
        key = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            unique.append(event)
    return unique


def import_state(
    data_dir_value: Path | str | None,
    input_path: Path,
    *,
    mode: str = "merge",
    dry_run: bool = False,
    confirm_replace: bool = False,
) -> dict:
    if mode not in {"merge", "replace"}:
        raise StateError("import mode must be merge or replace")
    if mode == "replace" and not dry_run and not confirm_replace:
        raise StateError("--confirm-replace is required for replace import")
    incoming_profile, incoming_feedback = read_import(input_path)
    data_dir = resolve_data_dir(data_dir_value)
    profile_path, feedback_path = paths(data_dir)

    def calculate_result() -> tuple[dict, list[dict]]:
        current_profile = migrate_profile(load_json(profile_path)) if profile_path.exists() else default_profile()
        current_feedback = recent_events(feedback_path, 2**31 - 1)
        result_profile = incoming_profile if mode == "replace" else merge_profiles(current_profile, incoming_profile)
        result_feedback = incoming_feedback if mode == "replace" else unique_feedback([*current_feedback, *incoming_feedback])
        return result_profile, result_feedback

    if dry_run:
        result_profile, result_feedback = calculate_result()
    else:
        data_dir.mkdir(parents=True, exist_ok=True)
        with state_lock(data_dir):
            # Re-read under the lock so feedback arriving during validation is not lost.
            result_profile, result_feedback = calculate_result()
            atomic_write_json(profile_path, result_profile, backup=True)
            text = "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in result_feedback)
            atomic_write_text(feedback_path, text, backup=True)
    summary = {
        "data_dir": str(data_dir),
        "mode": mode,
        "dry_run": dry_run,
        "repositories": len(result_profile["positive_repositories"]),
        "topics": len(result_profile["positive_topics"]),
        "excluded_repositories": len(result_profile["excluded_repositories"]),
        "excluded_topics": len(result_profile["excluded_topics"]),
        "feedback_events": len(result_feedback),
    }
    return summary


def purge_history(data_dir_value: Path | str | None, *, confirm_purge: bool = False) -> Path:
    if not confirm_purge:
        raise StateError("--confirm-purge is required for purge-history")
    data_dir, _ = initialize(data_dir_value)
    _, feedback_path = paths(data_dir)
    with state_lock(data_dir):
        atomic_write_text(feedback_path, "", backup=False)
        backup = backup_path(feedback_path)
        if backup.exists():
            backup.unlink()
    return feedback_path


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
    record_parser.add_argument("--confirm-reset", action="store_true")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--data-dir", type=Path)
    show_parser.add_argument("--events", type=int, default=10)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--data-dir", type=Path)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--force", action="store_true")

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--data-dir", type=Path)
    import_parser.add_argument("--input", type=Path, required=True)
    import_parser.add_argument("--mode", choices=("merge", "replace"), default="merge")
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.add_argument("--confirm-replace", action="store_true")

    purge_parser = subparsers.add_parser("purge-history")
    purge_parser.add_argument("--data-dir", type=Path)
    purge_parser.add_argument("--confirm-purge", action="store_true")
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
                confirm_reset=args.confirm_reset,
            )
            print(json.dumps({"data_dir": str(data_dir), "event": event}, ensure_ascii=False, indent=2))
        elif args.command == "repair":
            print(repair(args.data_dir))
        elif args.command == "export":
            print(export_state(args.data_dir, args.output, force=args.force))
        elif args.command == "import":
            print(
                json.dumps(
                    import_state(
                        args.data_dir,
                        args.input,
                        mode=args.mode,
                        dry_run=args.dry_run,
                        confirm_replace=args.confirm_replace,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "purge-history":
            print(purge_history(args.data_dir, confirm_purge=args.confirm_purge))
        else:
            print(json.dumps(show_state(args.data_dir, args.events), ensure_ascii=False, indent=2))
    except StateError as error:
        print(f"ERROR: {error}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
