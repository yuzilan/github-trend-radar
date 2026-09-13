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
from html.parser import HTMLParser
from pathlib import Path

from state import StateError, atomic_write_json, load_json, resolve_data_dir


BASE_URL = "https://github.com/trending"
USER_AGENT = "github-trend-radar/2.0 (+manual local research)"
TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
MIN_COMPARABLE_INTERVAL_SECONDS = 15 * 60


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


def repository_metadata(full_name: str, token: str | None) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        return {"enrichment_error": f"GitHub repository API HTTP {error.code}"}
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        return {"enrichment_error": f"GitHub repository API unavailable: {type(error).__name__}"}
    return {
        "topics": data.get("topics") or [],
        "license": (data.get("license") or {}).get("spdx_id"),
        "archived": bool(data.get("archived")),
        "created_at": data.get("created_at"),
        "pushed_at": data.get("pushed_at"),
        "homepage": data.get("homepage"),
        "open_issues": data.get("open_issues_count"),
    }


def enrich_periods(periods: dict[str, list[dict]], limit: int, token: str | None) -> None:
    names: list[str] = []
    for items in periods.values():
        for item in items:
            if item["full_name"].lower() not in {value.lower() for value in names}:
                names.append(item["full_name"])
    metadata = {name.lower(): repository_metadata(name, token) for name in names[: max(0, limit)]}
    for items in periods.values():
        for item in items:
            if item["full_name"].lower() in metadata:
                item.update(metadata[item["full_name"].lower()])


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


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
    parser.add_argument("--language", help="Optional GitHub Trending programming-language path")
    parser.add_argument("--enrich-limit", type=int, default=0, help="Enrich this many unique repos via GitHub API")
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
        if args.enrich_limit:
            enrich_periods(periods, args.enrich_limit, os.environ.get("GITHUB_TOKEN"))
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
