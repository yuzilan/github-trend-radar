#!/usr/bin/env python3
"""Shared state paths, locking, backups, and atomic file writes."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path


DATA_HOME_ENV = "GITHUB_TREND_RADAR_HOME"
DEFAULT_DIR_NAME = ".github-trend-radar"
CODEX_DATA_DIR_NAME = "github-trend-radar-data"


class StateError(RuntimeError):
    """Raised when durable local state cannot be safely read or written."""


def resolve_data_dir(value: Path | str | None = None) -> Path:
    """Resolve one canonical data directory, with explicit input taking priority."""
    if value:
        return Path(value).expanduser().resolve()
    configured = os.environ.get(DATA_HOME_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return default_data_dir()


def default_data_dir(home: Path | None = None) -> Path:
    home = (home or Path.home()).resolve()
    codex_root = home / "Documents" / "Codex"
    if codex_root.is_dir():
        return (codex_root / CODEX_DATA_DIR_NAME).resolve()
    return (home / DEFAULT_DIR_NAME).resolve()


def backup_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.bak")


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise StateError(f"state file does not exist: {path}") from error
    except json.JSONDecodeError as error:
        backup = backup_path(path)
        suffix = f"; valid backup may be available at {backup}" if backup.exists() else ""
        raise StateError(f"state file is not valid JSON: {path}{suffix}") from error
    if not isinstance(data, dict):
        raise StateError(f"state file must contain a JSON object: {path}")
    return data


def atomic_write_text(path: Path, text: str, *, backup: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if backup and path.exists():
            shutil.copy2(path, backup_path(path))
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name:
            with contextlib.suppress(FileNotFoundError):
                Path(temporary_name).unlink()


def atomic_write_json(path: Path, data: dict, *, backup: bool = False) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", backup=backup)


def append_jsonl(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def restore_backup(path: Path) -> None:
    backup = backup_path(path)
    if not backup.exists():
        raise StateError(f"backup does not exist: {backup}")
    restored = load_json(backup)
    atomic_write_json(path, restored, backup=False)


class FileLock:
    """Small cross-platform lock-file guard for short local state updates."""

    def __init__(self, path: Path, *, timeout: float = 5.0, stale_after: float = 120.0):
        self.path = path
        self.timeout = timeout
        self.stale_after = stale_after
        self.acquired = False

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps({"pid": os.getpid(), "created_at": time.time()}))
                    handle.flush()
                    os.fsync(handle.fileno())
                self.acquired = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > self.stale_after:
                        self.path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise StateError(f"timed out waiting for state lock: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.acquired:
            with contextlib.suppress(FileNotFoundError):
                self.path.unlink()
            self.acquired = False


def state_lock(data_dir: Path) -> FileLock:
    return FileLock(data_dir / ".state.lock")
