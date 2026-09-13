#!/usr/bin/env python3
"""Create objective and personalized rankings from a Trending snapshot."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

from state import StateError, atomic_write_json, load_json, resolve_data_dir


REQUIRED_ITEM_FIELDS = {
    "full_name": str,
    "stars": int,
    "period_stars": int,
    "github_position": int,
}
INTEREST_WEIGHT_CAP = 10.0


def percentile_scores(values: list[float]) -> list[float]:
    """Return tie-aware relative scores in [0, 1]."""
    if not values:
        return []
    unique = sorted(set(values))
    if len(unique) == 1:
        neutral = 0.0 if unique[0] == 0 else 0.5
        return [neutral] * len(values)
    score_by_value = {value: index / (len(unique) - 1) for index, value in enumerate(unique)}
    return [score_by_value[value] for value in values]


def validate_items(items: list[dict], period: str) -> None:
    if not items:
        raise StateError(f"snapshot has no {period} items")
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise StateError(f"{period} item {index} is not an object")
        for field, expected_type in REQUIRED_ITEM_FIELDS.items():
            if field not in item or not isinstance(item[field], expected_type):
                raise StateError(f"{period} item {index} has invalid {field}")
        full_name = item["full_name"].lower()
        if full_name in seen:
            raise StateError(f"duplicate repository in {period}: {item['full_name']}")
        seen.add(full_name)
        if item["stars"] <= 0 or item["period_stars"] <= 0 or item["github_position"] <= 0:
            raise StateError(f"{period} item {index} has non-positive ranking metrics")


def search_blob(item: dict) -> str:
    parts = [
        item.get("full_name", ""),
        item.get("description", ""),
        item.get("language", ""),
        " ".join(item.get("topics") or []),
    ]
    return " ".join(str(part).lower() for part in parts if part)


def topic_matches(topic: str, blob: str) -> bool:
    topic = topic.strip().lower()
    if not topic:
        return False
    if all(character.isalnum() or character in "-_+." for character in topic):
        normalized_topic = topic.replace("_", "-")
        normalized_blob = blob.replace("_", "-")
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_topic)}(?![a-z0-9])"
        return re.search(pattern, normalized_blob) is not None
    return topic in blob


def objective_scores(items: list[dict]) -> None:
    gains = [math.log1p(item["period_stars"]) for item in items]
    relative = []
    snapshot_velocity = []
    for item in items:
        gain = item["period_stars"]
        relative.append(gain / max(item["stars"] - gain, 1))
        velocity = item.get("stars_per_hour_since_previous")
        snapshot_velocity.append(math.log1p(max(0.0, float(velocity or 0))))

    gain_scores = percentile_scores(gains)
    relative_scores = percentile_scores(relative)
    velocity_scores = percentile_scores(snapshot_velocity)
    has_velocity = any(value > 0 for value in snapshot_velocity)
    raw_weights = {"gain": 0.45, "position": 0.25, "relative": 0.15, "cross": 0.10}
    if has_velocity:
        raw_weights["previous_velocity"] = 0.05
    weight_total = sum(raw_weights.values())

    count = len(items)
    for index, item in enumerate(items):
        position_score = 1.0 if count == 1 else 1 - (item["github_position"] - 1) / (count - 1)
        components = {
            "gain": gain_scores[index],
            "position": max(0.0, min(1.0, position_score)),
            "relative": relative_scores[index],
            "cross": 1.0 if item.get("in_both_periods") else 0.0,
            "previous_velocity": velocity_scores[index],
        }
        item["objective_heat"] = round(
            100 * sum(raw_weights[name] * components[name] for name in raw_weights) / weight_total,
            2,
        )
        item["score_components"] = {name: round(components[name], 4) for name in raw_weights}


def rank(snapshot: dict, profile: dict, period: str, top: int) -> dict:
    items = [dict(item) for item in snapshot.get("periods", {}).get(period, [])]
    validate_items(items, period)
    objective_scores(items)

    excluded_repos = {value.lower() for value in profile.get("excluded_repositories", [])}
    excluded_topics = [value.lower() for value in profile.get("excluded_topics", [])]
    positive_repos = {key.lower(): float(value) for key, value in profile.get("positive_repositories", {}).items()}
    positive_topics = {key.lower(): float(value) for key, value in profile.get("positive_topics", {}).items()}

    for item in items:
        name = item["full_name"].lower()
        blob = search_blob(item)
        item["matched_positive_topics"] = sorted(topic for topic in positive_topics if topic_matches(topic, blob))
        item["matched_excluded_topics"] = sorted(topic for topic in excluded_topics if topic_matches(topic, blob))
        item["excluded"] = name in excluded_repos or bool(item["matched_excluded_topics"])
        repository_interest = positive_repos.get(name, 0.0)
        matched_topic_weights = [positive_topics[topic] for topic in item["matched_positive_topics"]]
        topic_interest = sum(matched_topic_weights) / len(matched_topic_weights) if matched_topic_weights else 0.0
        item["repository_interest"] = round(repository_interest, 2)
        item["topic_interest"] = round(topic_interest, 2)
        item["interest_raw"] = round(
            min(INTEREST_WEIGHT_CAP, max(0.0, repository_interest, topic_interest)),
            2,
        )

    max_interest = max((item["interest_raw"] for item in items if not item["excluded"]), default=0.0)
    cold_start = max_interest <= 0
    for item in items:
        interest = item["interest_raw"] / INTEREST_WEIGHT_CAP
        item["interest_match"] = round(100 * interest, 2)
        item["personalized_score"] = round(
            item["objective_heat"] if cold_start else 0.75 * item["objective_heat"] + 25 * interest,
            2,
        )

    objective = sorted(items, key=lambda item: (-item["objective_heat"], item["github_position"]))
    eligible = [item for item in items if not item["excluded"]]
    personalized = sorted(eligible, key=lambda item: (-item["personalized_score"], -item["objective_heat"]))

    exploration_enabled = top >= 2
    first_entries = personalized[: max(0, top - 1) if exploration_enabled else top]
    selected = {item["full_name"].lower() for item in first_entries}
    exploration = next(
        (item for item in objective if not item["excluded"] and item["full_name"].lower() not in selected),
        None,
    )
    final_personalized = list(first_entries)
    if exploration_enabled and exploration is not None and len(final_personalized) < top:
        exploration = dict(exploration)
        exploration["exploration_slot"] = True
        final_personalized.append(exploration)

    selected = {item["full_name"].lower() for item in final_personalized}
    for item in personalized:
        if len(final_personalized) >= top:
            break
        if item["full_name"].lower() not in selected:
            final_personalized.append(item)
            selected.add(item["full_name"].lower())

    return {
        "schema_version": 2,
        "generated_at": snapshot.get("generated_at"),
        "previous_snapshot_at": snapshot.get("previous_snapshot_at"),
        "source": snapshot.get("source"),
        "period": period,
        "cold_start": cold_start,
        "candidate_count": len(items),
        "objective_top": objective[:top],
        "personalized_top": final_personalized[:top],
        "excluded_in_objective_top": [item for item in objective[:top] if item["excluded"]],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--period", choices=("daily", "weekly"), required=True)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    profile_path = args.profile or data_dir / "profile.json"
    output = args.output or data_dir / f"latest-{args.period}-ranking.json"
    try:
        snapshot = load_json(args.snapshot)
        profile = load_json(profile_path)
        result = rank(snapshot, profile, args.period, max(1, args.top))
        atomic_write_json(output, result, backup=True)
    except (StateError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
