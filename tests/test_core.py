from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fetch_trending  # noqa: E402
import profile  # noqa: E402
import rank_trending  # noqa: E402
import state  # noqa: E402


def article(name: str, *, stars: int = 1000, gain: int = 50, period: str = "daily") -> str:
    label = "today" if period == "daily" else "this week"
    return f"""
    <article class="Box-row">
      <h2><a href="/{name}">{name}</a></h2>
      <p class="col-9 color-fg-muted">An AI tool for local workflows.</p>
      <span itemprop="programmingLanguage">Python</span>
      <a href="/{name}/stargazers"><svg></svg>{stars:,}</a>
      <a href="/{name}/forks"><svg></svg>12</a>
      <span class="d-inline-block float-sm-right"><svg></svg>{gain:,} stars {label}</span>
    </article>
    """


class FetchTests(unittest.TestCase):
    def test_parser_extracts_required_fields(self) -> None:
        items = fetch_trending.parse_page(article("owner/repo"), "daily")
        self.assertEqual(items[0]["full_name"], "owner/repo")
        self.assertEqual(items[0]["stars"], 1000)
        self.assertEqual(items[0]["period_stars"], 50)
        self.assertEqual(items[0]["language"], "Python")

    def test_parser_rejects_partial_markup(self) -> None:
        broken = article("owner/repo").replace("50 stars today", "not available")
        with self.assertRaises(state.StateError):
            fetch_trending.parse_page(broken, "daily")

    def test_enrichment_propagates_to_both_periods(self) -> None:
        periods = {
            "daily": [{"full_name": "owner/repo"}],
            "weekly": [{"full_name": "owner/repo"}],
        }
        with mock.patch.object(fetch_trending, "repository_metadata", return_value={"topics": ["ai"]}):
            fetch_trending.enrich_periods(periods, 1, None)
        self.assertEqual(periods["daily"][0]["topics"], ["ai"])
        self.assertEqual(periods["weekly"][0]["topics"], ["ai"])

    def test_snapshot_velocity_requires_comparable_interval(self) -> None:
        current = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc)
        periods = {"daily": [{"full_name": "owner/repo", "stars": 110}]}
        too_recent = {
            "generated_at": (current - dt.timedelta(minutes=5)).isoformat(),
            "periods": {"daily": [{"full_name": "owner/repo", "stars": 100}]},
        }
        fetch_trending.add_previous_metrics(periods, too_recent, current)
        self.assertIsNone(periods["daily"][0]["stars_per_hour_since_previous"])

        comparable = {
            "generated_at": (current - dt.timedelta(hours=2)).isoformat(),
            "periods": {"daily": [{"full_name": "owner/repo", "stars": 100}]},
        }
        fetch_trending.add_previous_metrics(periods, comparable, current)
        self.assertEqual(periods["daily"][0]["stars_per_hour_since_previous"], 5.0)


class RankingTests(unittest.TestCase):
    def test_percentiles_treat_ties_equally(self) -> None:
        self.assertEqual(rank_trending.percentile_scores([0, 0, 1]), [0.0, 0.0, 1.0])
        self.assertEqual(rank_trending.percentile_scores([0, 0]), [0.0, 0.0])
        self.assertEqual(rank_trending.percentile_scores([4, 4]), [0.5, 0.5])

    def test_short_topic_does_not_match_inside_word(self) -> None:
        self.assertFalse(rank_trending.topic_matches("ai", "a tool for maintaining servers"))
        self.assertTrue(rank_trending.topic_matches("ai", "an ai tool"))

    def test_exact_repo_interest_and_exclusion(self) -> None:
        items = [
            {
                "full_name": "owner/liked",
                "stars": 1000,
                "period_stars": 50,
                "github_position": 2,
                "description": "tool",
                "language": "Python",
                "topics": [],
                "in_both_periods": False,
            },
            {
                "full_name": "owner/hot",
                "stars": 2000,
                "period_stars": 100,
                "github_position": 1,
                "description": "tool",
                "language": "Go",
                "topics": [],
                "in_both_periods": True,
            },
        ]
        snapshot = {"generated_at": "2026-01-01T00:00:00+00:00", "periods": {"daily": items}}
        user_profile = {
            "positive_repositories": {"owner/liked": 3},
            "positive_topics": {},
            "excluded_repositories": ["owner/hot"],
            "excluded_topics": [],
        }
        result = rank_trending.rank(snapshot, user_profile, "daily", 10)
        self.assertEqual([item["full_name"] for item in result["personalized_top"]], ["owner/liked"])
        self.assertEqual([item["full_name"] for item in result["excluded_in_objective_top"]], ["owner/hot"])


class ProfileAndStateTests(unittest.TestCase):
    def test_global_location_can_be_overridden(self) -> None:
        with mock.patch.dict(os.environ, {state.DATA_HOME_ENV: "/tmp/custom-radar-home"}):
            self.assertEqual(state.resolve_data_dir(), Path("/tmp/custom-radar-home").resolve())

    def test_codex_documents_directory_is_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "Documents" / "Codex").mkdir(parents=True)
            self.assertEqual(
                state.default_data_dir(home),
                (home / "Documents" / "Codex" / state.CODEX_DATA_DIR_NAME).resolve(),
            )

    def test_record_migrates_profile_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile_path = data_dir / "profile.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "positive_topics": {},
                        "excluded_repositories": [],
                        "excluded_topics": [],
                        "notes": [],
                        "updated_at": None,
                    }
                ),
                encoding="utf-8",
            )
            profile.record_event(data_dir, signal="detail", repo="Owner/Repo", topics=["AI"])
            current = state.load_json(profile_path)
            self.assertEqual(current["schema_version"], 2)
            self.assertEqual(current["positive_repositories"]["owner/repo"], 0.5)
            self.assertEqual(current["positive_topics"]["ai"], 0.5)
            self.assertTrue(state.backup_path(profile_path).exists())

    def test_repair_restores_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.initialize(data_dir)
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            profile_path = data_dir / "profile.json"
            profile_path.write_text("{broken", encoding="utf-8")
            profile.repair(data_dir)
            repaired = state.load_json(profile_path)
            self.assertEqual(repaired["schema_version"], 2)

    def test_required_feedback_scope_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(state.StateError):
                profile.record_event(Path(directory), signal="detail")

    def test_concurrent_feedback_updates_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)

            def add_feedback(_: int) -> None:
                profile.record_event(data_dir, signal="detail", repo="owner/repo", topics=["python"])

            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(add_feedback, range(8)))
            current = state.load_json(data_dir / "profile.json")
            self.assertEqual(current["positive_repositories"]["owner/repo"], 4.0)
            self.assertEqual(current["positive_topics"]["python"], 4.0)
            self.assertEqual(len((data_dir / "feedback.jsonl").read_text(encoding="utf-8").splitlines()), 8)


if __name__ == "__main__":
    unittest.main()
