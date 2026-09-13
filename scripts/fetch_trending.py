#!/usr/bin/env python3
"""Fetch GitHub daily/weekly Trending pages into a validated JSON snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

from state import StateError, atomic_write_json, load_json, resolve_data_dir


BASE_URL = "https://github.com/trending"
SKILL_VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
USER_AGENT = f"github-trend-radar/{SKILL_VERSION} (+manual local research)"
TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
MIN_COMPARABLE_INTERVAL_SECONDS = 15 * 60
DEFAULT_ENRICH_LIMIT = 25
DEFAULT_METADATA_TTL_HOURS = 24.0
METADATA_CACHE_SCHEMA = 1


def parse_number(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def attributes(values: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key: value or "" for key, value in values}


class TrendingParser(HTMLParser):
    """Parse semantic repository fields without depending on complete HTML blocks."""

    def __init__(self, period: str):
        super().__init__(convert_charrefs=True)
        self.period = period
        self.items: list[dict] = []
        self.current: dict | None = None
        self.in_heading = 0
        self.capture: str | None = None
        self.capture_tag: str | None = None
        self.buffer: list[str] = []

    def start_capture(self, kind: str, tag: str) -> None:
        if self.capture is None:
            self.capture = kind
            self.capture_tag = tag
            self.buffer = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = attributes(attrs_list)
        classes = set(attrs.get("class", "").split())
        if tag == "article" and "Box-row" in classes and self.current is None:
            self.current = {
                "full_name": None,
                "description": "",
                "language": "",
                "stars": None,
                "forks": 0,
                "period_stars": None,
                "period": self.period,
                "topics": [],
            }
            return
        if self.current is None:
            return
        if tag == "h2":
            self.in_heading += 1
        elif tag == "a" and self.in_heading:
            match = re.fullmatch(r"/([^/\s?#]+/[^/\s?#]+)", html.unescape(attrs.get("href", "")))
            if match:
                self.current["full_name"] = match.group(1)
        elif tag == "p" and "color-fg-muted" in classes:
            self.start_capture("description", tag)
        elif tag == "span" and attrs.get("itemprop") == "programmingLanguage":
            self.start_capture("language", tag)
        elif tag == "a" and attrs.get("href", "").endswith("/stargazers"):
            self.start_capture("stars", tag)
        elif tag == "a" and attrs.get("href", "").endswith("/forks"):
            self.start_capture("forks", tag)
        elif tag == "span" and "float-sm-right" in classes:
            self.start_capture("period_stars", tag)

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "h2" and self.in_heading:
            self.in_heading -= 1
        if self.capture and tag == self.capture_tag:
            value = " ".join("".join(self.buffer).split())
            if self.capture in ("stars", "forks"):
                self.current[self.capture] = parse_number(value)
            elif self.capture == "period_stars":
                expected = "today" if self.period == "daily" else "this week"
                if expected in value.lower():
                    self.current[self.capture] = parse_number(value)
            else:
                self.current[self.capture] = value
            self.capture = None
            self.capture_tag = None
            self.buffer = []
        if tag == "article":
            self.finish_item()

    def finish_item(self) -> None:
        if self.current is None:
            return
        self.current["github_position"] = len(self.items) + 1
        if self.current.get("full_name"):
            self.current["url"] = f"https://github.com/{self.current['full_name']}"
        self.items.append(self.current)
        self.current = None
        self.in_heading = 0
        self.capture = None
        self.capture_tag = None
        self.buffer = []


def validate_items(items: list[dict], period: str) -> None:
    if not items:
        raise StateError("GitHub Trending contained no repository rows; markup may have changed")
    seen: set[str] = set()
    errors: list[str] = []
    for index, item in enumerate(items, start=1):
        name = item.get("full_name")
        if not isinstance(name, str) or not re.fullmatch(r"[^/\s]+/[^/\s]+", name):
            errors.append(f"row {index}: invalid repository name")
        elif name.lower() in seen:
            errors.append(f"row {index}: duplicate repository {name}")
        else:
            seen.add(name.lower())
        if not isinstance(item.get("stars"), int) or item["stars"] <= 0:
            errors.append(f"row {index}: missing total stars")
        if not isinstance(item.get("period_stars"), int) or item["period_stars"] <= 0:
            errors.append(f"row {index}: missing {period} star gain")
    if errors:
        preview = "; ".join(errors[:5])
        extra = f"; plus {len(errors) - 5} more" if len(errors) > 5 else ""
        raise StateError(f"incomplete GitHub Trending parse: {preview}{extra}")


def parse_page(page: str, period: str) -> list[dict]:
    parser = TrendingParser(period)
    parser.feed(page)
    parser.close()
    validate_items(parser.items, period)
    return parser.items


def fetch_url(url: str, attempts: int = 3) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_type = response.headers.get_content_type()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    raise StateError(f"unexpected content type from GitHub: {content_type}")
                body = response.read().decode("utf-8", errors="replace")
                if "github.com/trending" not in body.lower() and "Box-row" not in body:
                    raise StateError("response does not look like GitHub Trending HTML")
                return body
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in TRANSIENT_HTTP_CODES:
                break
        except urllib.error.URLError as error:
            last_error = error
        if attempt + 1 < attempts:
            time.sleep(0.5 * (2**attempt))
    raise StateError(f"unable to fetch {url}: {last_error}")


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def repository_metadata(full_name: str, token: str | None, attempts: int = 3) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                return {"enrichment_error": "GitHub repository API returned a non-object response"}
            break
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in TRANSIENT_HTTP_CODES:
                return {"enrichment_error": f"GitHub repository API HTTP {error.code}"}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        if attempt + 1 < attempts:
            time.sleep(0.5 * (2**attempt))
    else:
        return {"enrichment_error": f"GitHub repository API unavailable: {type(last_error).__name__}"}
    return {
        "topics": data.get("topics") or [],
        "license": (data.get("license") or {}).get("spdx_id"),
        "archived": bool(data.get("archived")),
        "created_at": data.get("created_at"),
        "pushed_at": data.get("pushed_at"),
        "homepage": data.get("homepage"),
        "open_issues": data.get("open_issues_count"),
    }


def ordered_unique_names(periods: dict[str, list[dict]]) -> list[str]:
    """Interleave lists so one period cannot consume the whole enrichment budget."""
    period_names = [name for name in ("daily", "weekly") if name in periods]
    period_names.extend(name for name in periods if name not in period_names)
    names: list[str] = []
    seen: set[str] = set()
    largest = max((len(periods[name]) for name in period_names), default=0)
    for index in range(largest):
        for period in period_names:
            items = periods[period]
            if index >= len(items):
                continue
            name = items[index]["full_name"]
            if name.lower() not in seen:
                names.append(name)
                seen.add(name.lower())
    return names


def default_metadata_cache() -> dict:
    return {"schema_version": METADATA_CACHE_SCHEMA, "repositories": {}}


def load_metadata_cache(path: Path | None) -> dict:
    if path is None or not path.exists():
        return default_metadata_cache()
    cache = load_json(path)
    if cache.get("schema_version") != METADATA_CACHE_SCHEMA or not isinstance(cache.get("repositories"), dict):
        raise StateError(f"unsupported repository metadata cache: {path}; use --refresh-metadata to rebuild it")
    return cache


def enrich_periods(
    periods: dict[str, list[dict]],
    limit: int,
    token: str | None,
    *,
    cache_path: Path | None = None,
    ttl_hours: float = DEFAULT_METADATA_TTL_HOURS,
    refresh: bool = False,
    current_time: dt.datetime | None = None,
) -> dict:
    current_time = current_time or dt.datetime.now(dt.timezone.utc)
    cache = default_metadata_cache() if refresh else load_metadata_cache(cache_path)
    entries = cache["repositories"]
    metadata: dict[str, dict] = {}
    cache_hits = 0
    errors = 0
    changed = False
    misses: list[str] = []
    for name in ordered_unique_names(periods)[: max(0, limit)]:
        key = name.lower()
        entry = entries.get(key)
        fetched_at = parse_timestamp(entry.get("fetched_at")) if isinstance(entry, dict) else None
        age = (current_time - fetched_at).total_seconds() if fetched_at else None
        cached_value = entry.get("metadata") if isinstance(entry, dict) else None
        if isinstance(cached_value, dict) and age is not None and 0 <= age <= ttl_hours * 3600:
            metadata[key] = cached_value
            cache_hits += 1
            continue
        misses.append(name)

    if misses:
        with ThreadPoolExecutor(max_workers=min(4, len(misses))) as executor:
            fetched_values = executor.map(lambda name: repository_metadata(name, token), misses)
            fetched = zip(misses, fetched_values)
            for name, value in fetched:
                key = name.lower()
                metadata[key] = value
                if "enrichment_error" in value:
                    errors += 1
                    continue
                entries[key] = {"fetched_at": current_time.isoformat(), "metadata": value}
                changed = True
    if cache_path is not None and (changed or refresh):
        atomic_write_json(cache_path, cache, backup=True)
    for items in periods.values():
        for item in items:
            if item["full_name"].lower() in metadata:
                item.update(metadata[item["full_name"].lower()])
    return {
        "requested_limit": max(0, limit),
        "enriched_repositories": len(metadata) - errors,
        "cache_hits": cache_hits,
        "api_requests": len(misses),
        "errors": errors,
        "ttl_hours": ttl_hours,
    }


def find_previous_snapshot(history_dir: Path, output: Path) -> dict | None:
    if not history_dir.exists():
        return None
    snapshots: list[tuple[dt.datetime, dict]] = []
    for candidate in history_dir.glob("*.json"):
        if candidate.resolve() == output.resolve():
            continue
        try:
            data = load_json(candidate)
        except StateError:
            continue
        generated_at = parse_timestamp(data.get("generated_at"))
        if generated_at and isinstance(data.get("periods"), dict):
            snapshots.append((generated_at, data))
    return max(snapshots, key=lambda pair: pair[0])[1] if snapshots else None


def add_previous_metrics(periods: dict[str, list[dict]], previous: dict | None, generated_at: dt.datetime) -> float | None:
    previous_at = parse_timestamp(previous.get("generated_at")) if previous else None
    elapsed = (generated_at - previous_at).total_seconds() if previous_at else None
    previous_by_name: dict[str, int] = {}
    if previous:
        for items in previous.get("periods", {}).values():
            for item in items:
                previous_by_name[item.get("full_name", "").lower()] = int(item.get("stars") or 0)
    for items in periods.values():
        for item in items:
            prior = previous_by_name.get(item["full_name"].lower())
            delta = max(0, item["stars"] - prior) if prior is not None else None
            item["stars_since_previous"] = delta
            item["stars_per_hour_since_previous"] = (
                round(delta / (elapsed / 3600), 4)
                if delta is not None and elapsed is not None and elapsed >= MIN_COMPARABLE_INTERVAL_SECONDS
                else None
            )
    return elapsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--period", choices=("daily", "weekly", "both"), default="both")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--programming-language",
        "--language",
        dest="language",
        help="Optional GitHub Trending programming-language path (--language remains as a compatibility alias)",
    )
    parser.add_argument(
        "--enrich-limit",
        type=int,
        default=DEFAULT_ENRICH_LIMIT,
        help="Enrich this many interleaved daily/weekly repos via GitHub API (default: 25; use 0 to disable)",
    )
    parser.add_argument("--metadata-cache", type=Path)
    parser.add_argument("--metadata-ttl-hours", type=float, default=DEFAULT_METADATA_TTL_HOURS)
    parser.add_argument("--refresh-metadata", action="store_true")
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    history_dir = args.history_dir or data_dir / "snapshots"
    generated_at = dt.datetime.now(dt.timezone.utc)
    output = args.output or history_dir / generated_at.strftime("%Y%m%dT%H%M%SZ.json")
    requested = ("daily", "weekly") if args.period == "both" else (args.period,)
    periods: dict[str, list[dict]] = {}
    try:
        for period in requested:
            language_path = f"/{args.language.strip('/')}" if args.language else ""
            url = f"{BASE_URL}{language_path}?since={period}"
            periods[period] = parse_page(fetch_url(url), period)[: max(1, args.limit)]
        enrichment = {"enabled": False}
        if args.enrich_limit:
            cache_path = args.metadata_cache or data_dir / "repository-metadata.json"
            enrichment = {
                "enabled": True,
                **enrich_periods(
                    periods,
                    args.enrich_limit,
                    os.environ.get("GITHUB_TOKEN"),
                    cache_path=cache_path,
                    ttl_hours=max(0.0, args.metadata_ttl_hours),
                    refresh=args.refresh_metadata,
                    current_time=generated_at,
                ),
            }
        previous = find_previous_snapshot(history_dir, output)
        elapsed = add_previous_metrics(periods, previous, generated_at)
        names = {period: {item["full_name"].lower() for item in items} for period, items in periods.items()}
        for period, items in periods.items():
            counterpart = "weekly" if period == "daily" else "daily"
            for item in items:
                item["in_both_periods"] = item["full_name"].lower() in names.get(counterpart, set())
        payload = {
            "schema_version": 2,
            "generated_at": generated_at.isoformat(),
            "previous_snapshot_at": previous.get("generated_at") if previous else None,
            "seconds_since_previous": elapsed,
            "source": "https://github.com/trending",
            "filters": {"period": args.period, "programming_language": args.language},
            "enrichment": enrichment,
            "periods": periods,
        }
        atomic_write_json(output, payload, backup=False)
    except (StateError, OSError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
