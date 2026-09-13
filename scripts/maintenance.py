#!/usr/bin/env python3
"""Inspect storage and safely prune derived GitHub Trend Radar data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from fetch_trending import METADATA_CACHE_SCHEMA, parse_timestamp
from state import StateError, atomic_write_json, load_json, resolve_data_dir, state_lock


def file_info(path: Path) -> dict:
    return {"path": str(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}


def snapshot_time(path: Path) -> dt.datetime | None:
    try:
        return parse_timestamp(load_json(path).get("generated_at"))
    except StateError:
        return None


def status(data_dir_value: Path | str | None) -> dict:
    data_dir = resolve_data_dir(data_dir_value)
    snapshots = sorted((data_dir / "snapshots").glob("*.json")) if (data_dir / "snapshots").exists() else []
    dated = [(path, snapshot_time(path)) for path in snapshots]
    valid_dates = [value for _, value in dated if value]
    cache_path = data_dir / "repository-metadata.json"
    cache_entries = 0
    cache_error = None
    if cache_path.exists():
        try:
            cache = load_json(cache_path)
            if cache.get("schema_version") != METADATA_CACHE_SCHEMA or not isinstance(cache.get("repositories"), dict):
                raise StateError("unsupported metadata cache schema")
            cache_entries = len(cache["repositories"])
        except StateError as error:
            cache_error = str(error)
    return {
        "data_dir": str(data_dir),
        "profile": file_info(data_dir / "profile.json"),
        "feedback": file_info(data_dir / "feedback.jsonl"),
        "metadata_cache": {**file_info(cache_path), "entries": cache_entries, "error": cache_error},
        "snapshots": {
            "directory": str(data_dir / "snapshots"),
            "count": len(snapshots),
            "bytes": sum(path.stat().st_size for path in snapshots),
            "oldest": min(valid_dates).isoformat() if valid_dates else None,
            "newest": max(valid_dates).isoformat() if valid_dates else None,
            "invalid": sum(value is None for _, value in dated),
        },
    }


def prune(
    data_dir_value: Path | str | None,
    *,
    snapshot_days: int = 180,
    metadata_days: int = 90,
    apply: bool = False,
    current_time: dt.datetime | None = None,
) -> dict:
    if snapshot_days < 0 or metadata_days < 0:
        raise StateError("retention days must be zero or greater")
    data_dir = resolve_data_dir(data_dir_value)
    current_time = current_time or dt.datetime.now(dt.timezone.utc)
    snapshot_cutoff = current_time - dt.timedelta(days=snapshot_days)
    metadata_cutoff = current_time - dt.timedelta(days=metadata_days)
    snapshot_candidates: list[Path] = []
    skipped_snapshots: list[str] = []
    snapshots_dir = data_dir / "snapshots"
    for path in sorted(snapshots_dir.glob("*.json")) if snapshots_dir.exists() else []:
        generated_at = snapshot_time(path)
        if generated_at is None:
            skipped_snapshots.append(str(path))
        elif generated_at < snapshot_cutoff:
            snapshot_candidates.append(path)

    cache_path = data_dir / "repository-metadata.json"
    cache_candidates: list[str] = []
    cache = None
    if cache_path.exists():
        cache = load_json(cache_path)
        if cache.get("schema_version") != METADATA_CACHE_SCHEMA or not isinstance(cache.get("repositories"), dict):
            raise StateError(f"unsupported repository metadata cache: {cache_path}")
        for name, entry in cache["repositories"].items():
            fetched_at = parse_timestamp(entry.get("fetched_at")) if isinstance(entry, dict) else None
            if fetched_at and fetched_at < metadata_cutoff:
                cache_candidates.append(name)

    if apply:
        data_dir.mkdir(parents=True, exist_ok=True)
        with state_lock(data_dir):
            for path in snapshot_candidates:
                generated_at = snapshot_time(path)
                if generated_at is not None and generated_at < snapshot_cutoff:
                    path.unlink(missing_ok=True)
            if cache is not None and cache_candidates and cache_path.exists():
                current_cache = load_json(cache_path)
                if current_cache.get("schema_version") != METADATA_CACHE_SCHEMA or not isinstance(
                    current_cache.get("repositories"), dict
                ):
                    raise StateError(f"unsupported repository metadata cache: {cache_path}")
                for name in cache_candidates:
                    entry = current_cache["repositories"].get(name)
                    fetched_at = parse_timestamp(entry.get("fetched_at")) if isinstance(entry, dict) else None
                    if fetched_at and fetched_at < metadata_cutoff:
                        current_cache["repositories"].pop(name, None)
                atomic_write_json(cache_path, current_cache, backup=True)
    return {
        "data_dir": str(data_dir),
        "applied": apply,
        "snapshot_days": snapshot_days,
        "metadata_days": metadata_days,
        "snapshot_files": [str(path) for path in snapshot_candidates],
        "metadata_entries": sorted(cache_candidates),
        "skipped_invalid_snapshots": skipped_snapshots,
        "protected": ["profile.json", "feedback.jsonl"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--data-dir", type=Path)
    prune_parser = subparsers.add_parser("prune")
    prune_parser.add_argument("--data-dir", type=Path)
    prune_parser.add_argument("--snapshot-days", type=int, default=180)
    prune_parser.add_argument("--metadata-days", type=int, default=90)
    prune_parser.add_argument("--apply", action="store_true", help="apply the displayed derived-data deletion plan")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = status(args.data_dir) if args.command == "status" else prune(
            args.data_dir,
            snapshot_days=args.snapshot_days,
            metadata_days=args.metadata_days,
            apply=args.apply,
        )
    except (StateError, OSError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
