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
import doctor  # noqa: E402
import maintenance  # noqa: E402
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
    def test_language_path_is_encoded_without_losing_period_query(self) -> None:
        self.assertEqual(fetch_trending.trending_url("daily", "C#"), "https://github.com/trending/c%23?since=daily")
        self.assertEqual(
            fetch_trending.trending_url("weekly", "Visual Basic"),
            "https://github.com/trending/visual-basic?since=weekly",
        )

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

    def test_parser_validates_only_requested_candidates(self) -> None:
        page = article("owner/good") + article("owner/zero", gain=0)
        self.assertEqual(len(fetch_trending.parse_page(page, "daily", 1)), 1)
        self.assertEqual(fetch_trending.parse_page(page, "daily", 2)[1]["period_stars"], 0)
        broken_page = article("owner/good") + article("owner/missing", gain=0).replace(
            "0 stars today", "not available"
        )
        with self.assertRaises(state.StateError):
            fetch_trending.parse_page(broken_page, "daily", 2)

    def test_enrichment_propagates_to_both_periods(self) -> None:
        periods = {
            "daily": [{"full_name": "owner/repo"}],
            "weekly": [{"full_name": "owner/repo"}],
        }
        with mock.patch.object(fetch_trending, "repository_metadata", return_value={"topics": ["ai"]}):
            fetch_trending.enrich_periods(periods, 1, None)
        self.assertEqual(periods["daily"][0]["topics"], ["ai"])
        self.assertEqual(periods["weekly"][0]["topics"], ["ai"])

    def test_enrichment_interleaves_daily_and_weekly_candidates(self) -> None:
        periods = {
            "daily": [{"full_name": "owner/daily-1"}, {"full_name": "owner/daily-2"}],
            "weekly": [{"full_name": "owner/weekly-1"}, {"full_name": "owner/weekly-2"}],
        }
        with mock.patch.object(fetch_trending, "repository_metadata", return_value={"topics": []}) as request:
            fetch_trending.enrich_periods(periods, 2, None)
        self.assertEqual({call.args[0] for call in request.call_args_list}, {"owner/daily-1", "owner/weekly-1"})

    def test_repository_metadata_cache_avoids_repeated_api_calls(self) -> None:
        periods = {"daily": [{"full_name": "owner/repo"}]}
        current = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "repository-metadata.json"
            with mock.patch.object(fetch_trending, "repository_metadata", return_value={"topics": ["ai"]}) as request:
                first = fetch_trending.enrich_periods(periods, 1, None, cache_path=cache_path, current_time=current)
                second_periods = {"daily": [{"full_name": "owner/repo"}]}
                second = fetch_trending.enrich_periods(
                    second_periods,
                    1,
                    None,
                    cache_path=cache_path,
                    current_time=current + dt.timedelta(hours=1),
                )
            self.assertEqual(request.call_count, 1)
            self.assertEqual(first["api_requests"], 1)
            self.assertEqual(second["cache_hits"], 1)
            self.assertEqual(second_periods["daily"][0]["topics"], ["ai"])

    def test_fetch_defaults_to_cached_enrichment_and_keeps_language_alias(self) -> None:
        defaults = fetch_trending.build_parser().parse_args([])
        legacy = fetch_trending.build_parser().parse_args(["--language", "python"])
        explicit = fetch_trending.build_parser().parse_args(["--programming-language", "rust"])
        self.assertEqual(defaults.enrich_limit, 25)
        self.assertEqual(legacy.language, "python")
        self.assertEqual(explicit.language, "rust")

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
    def test_zero_period_gain_is_valid_and_rankable(self) -> None:
        item = {
            "full_name": "owner/quiet",
            "stars": 1000,
            "period_stars": 0,
            "github_position": 1,
            "description": "A quiet but valid Trending entry",
            "language": "C#",
            "topics": [],
            "in_both_periods": False,
        }
        snapshot = {"generated_at": "2026-01-01T00:00:00+00:00", "periods": {"daily": [item]}}
        result = rank_trending.rank(snapshot, profile.default_profile(), "daily", 1)
        self.assertEqual(result["objective_top"][0]["period_stars"], 0)

    def test_distributed_sample_snapshot_matches_reported_order_and_scores(self) -> None:
        root = Path(__file__).resolve().parents[1]
        snapshot = state.load_json(root / "examples" / "sample-snapshot.json")
        result = rank_trending.rank(snapshot, profile.default_profile(), "daily", 3)
        self.assertEqual(
            [(item["full_name"], item["objective_heat"]) for item in result["objective_top"]],
            [
                ("bilawalsidhu/gods-eye-view", 73.68),
                ("JustVugg/colibri", 57.89),
                ("ever-co/ever-gauzy", 13.16),
            ],
        )

    def test_percentiles_treat_ties_equally(self) -> None:
        self.assertEqual(rank_trending.percentile_scores([0, 0, 1]), [0.0, 0.0, 1.0])
        self.assertEqual(rank_trending.percentile_scores([0, 0]), [0.0, 0.0])
        self.assertEqual(rank_trending.percentile_scores([4, 4]), [0.5, 0.5])

    def test_short_topic_does_not_match_inside_word(self) -> None:
        self.assertFalse(rank_trending.topic_matches("ai", "a tool for maintaining servers"))
        self.assertTrue(rank_trending.topic_matches("ai", "an ai tool"))

    def test_topic_alias_matches_canonical_preference(self) -> None:
        self.assertIn("ai-agent", rank_trending.search_blob({"topics": ["ai-agents"]}))

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

    def test_weak_interest_is_not_scaled_to_full_strength(self) -> None:
        item = {
            "full_name": "owner/asked",
            "stars": 1000,
            "period_stars": 50,
            "github_position": 1,
            "description": "AI developer tool",
            "language": "Python",
            "topics": ["ai", "developer-tools"],
            "in_both_periods": False,
        }
        snapshot = {"generated_at": "2026-01-01T00:00:00+00:00", "periods": {"daily": [item]}}
        user_profile = {
            "positive_repositories": {"owner/asked": 0.5},
            "positive_topics": {"ai": 0.5, "developer-tools": 0.5},
            "excluded_repositories": [],
            "excluded_topics": [],
        }
        result = rank_trending.rank(snapshot, user_profile, "daily", 1)
        ranked = result["personalized_top"][0]
        self.assertEqual(ranked["repository_interest"], 0.5)
        self.assertEqual(ranked["topic_interest"], 0.5)
        self.assertEqual(ranked["interest_match"], 5.0)

    def test_top_one_uses_personalized_ranking_without_exploration_override(self) -> None:
        items = [
            {
                "full_name": "owner/hot",
                "stars": 1000,
                "period_stars": 100,
                "github_position": 1,
                "description": "tool",
                "language": "Go",
                "topics": [],
                "in_both_periods": False,
            },
            {
                "full_name": "owner/favorite",
                "stars": 1000,
                "period_stars": 100,
                "github_position": 2,
                "description": "tool",
                "language": "Python",
                "topics": [],
                "in_both_periods": False,
            },
        ]
        snapshot = {"generated_at": "2026-01-01T00:00:00+00:00", "periods": {"daily": items}}
        user_profile = {
            "positive_repositories": {"owner/favorite": 10},
            "positive_topics": {},
            "excluded_repositories": [],
            "excluded_topics": [],
        }
        result = rank_trending.rank(snapshot, user_profile, "daily", 1)
        self.assertEqual(result["personalized_top"][0]["full_name"], "owner/favorite")


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
            with self.assertRaises(state.StateError):
                profile.record_event(Path(directory), signal="unknown")

    def test_forget_repo_removes_current_interest_and_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            profile.record_event(data_dir, signal="exclude-repo", repo="owner/repo")
            profile.record_event(data_dir, signal="forget-repo", repo="owner/repo")
            current = state.load_json(data_dir / "profile.json")
            self.assertNotIn("owner/repo", current["positive_repositories"])
            self.assertNotIn("owner/repo", current["excluded_repositories"])
            self.assertEqual(current["positive_topics"]["python"], 2.0)

    def test_forget_topic_removes_current_interest_and_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.record_event(data_dir, signal="like-topic", topics=["python"])
            profile.record_event(data_dir, signal="exclude-topic", topics=["python"])
            profile.record_event(data_dir, signal="forget-topic", topics=["python"])
            current = state.load_json(data_dir / "profile.json")
            self.assertNotIn("python", current["positive_topics"])
            self.assertNotIn("python", current["excluded_topics"])

    def test_reset_requires_confirmation_and_clears_current_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            with self.assertRaises(state.StateError):
                profile.record_event(data_dir, signal="reset-profile")
            profile.record_event(data_dir, signal="reset-profile", confirm_reset=True)
            current = state.load_json(data_dir / "profile.json")
            self.assertEqual(current["positive_repositories"], {})
            self.assertEqual(current["positive_topics"], {})
            self.assertEqual(len((data_dir / "feedback.jsonl").read_text(encoding="utf-8").splitlines()), 2)

    def test_export_contains_profile_and_feedback_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory) / "state"
            export_path = Path(directory) / "profile-export.json"
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            profile.export_state(data_dir, export_path)
            exported = state.load_json(export_path)
            self.assertEqual(exported["profile"]["positive_repositories"]["owner/repo"], 2.0)
            self.assertEqual(len(exported["feedback"]), 1)
            with self.assertRaises(state.StateError):
                profile.export_state(data_dir, export_path)

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

    def test_topic_aliases_are_canonicalized_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            _, event = profile.record_event(data_dir, signal="like-topic", topics=["AI Agents", "devtools"])
            current = state.load_json(data_dir / "profile.json")
            self.assertEqual(event["topics"], ["ai-agent", "developer-tools"])
            self.assertEqual(event["topic_aliases"], {"ai agents": "ai-agent", "devtools": "developer-tools"})
            self.assertEqual(current["positive_topics"], {"ai-agent": 3.0, "developer-tools": 3.0})

    def test_import_merge_is_idempotent_and_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            export_path = root / "export.json"
            profile.record_event(source, signal="interested", repo="Owner/Repo", topics=["AI Agents"])
            profile.export_state(source, export_path)
            preview = profile.import_state(destination, export_path, dry_run=True)
            self.assertTrue(preview["dry_run"])
            self.assertFalse(destination.exists())
            profile.import_state(destination, export_path)
            profile.import_state(destination, export_path)
            current = state.load_json(destination / "profile.json")
            self.assertEqual(current["positive_repositories"], {"owner/repo": 2.0})
            self.assertEqual(current["positive_topics"], {"ai-agent": 2.0})
            self.assertEqual(len(profile.recent_events(destination / "feedback.jsonl", 10)), 1)

    def test_replace_import_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            export_path = root / "export.json"
            profile.record_event(source, signal="interested", repo="owner/new", topics=["python"])
            profile.export_state(source, export_path)
            profile.record_event(destination, signal="interested", repo="owner/old", topics=["rust"])
            with self.assertRaises(state.StateError):
                profile.import_state(destination, export_path, mode="replace")
            profile.import_state(destination, export_path, mode="replace", confirm_replace=True)
            current = state.load_json(destination / "profile.json")
            self.assertEqual(current["positive_repositories"], {"owner/new": 2.0})

    def test_import_rejects_timestamp_without_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            import_path = Path(directory) / "invalid.json"
            import_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profile": profile.default_profile(),
                        "feedback": [
                            {
                                "timestamp": "2026-01-01T12:00:00",
                                "signal": "detail",
                                "repository": "owner/repo",
                                "topics": [],
                                "note": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(state.StateError):
                profile.import_state(Path(directory) / "destination", import_path, dry_run=True)

    def test_purge_history_keeps_active_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            with self.assertRaises(state.StateError):
                profile.purge_history(data_dir)
            profile.purge_history(data_dir, confirm_purge=True)
            current = state.load_json(data_dir / "profile.json")
            self.assertEqual(current["positive_repositories"], {"owner/repo": 2.0})
            self.assertEqual((data_dir / "feedback.jsonl").read_text(encoding="utf-8"), "")


class MaintenanceAndDoctorTests(unittest.TestCase):
    def test_prune_defaults_to_preview_and_only_removes_derived_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.record_event(data_dir, signal="interested", repo="owner/repo", topics=["python"])
            snapshots = data_dir / "snapshots"
            snapshots.mkdir()
            old_snapshot = snapshots / "old.json"
            old_snapshot.write_text(json.dumps({"generated_at": "2025-01-01T00:00:00+00:00"}), encoding="utf-8")
            cache_path = data_dir / "repository-metadata.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repositories": {
                            "owner/repo": {"fetched_at": "2025-01-01T00:00:00+00:00", "metadata": {}}
                        },
                    }
                ),
                encoding="utf-8",
            )
            current = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
            preview = maintenance.prune(data_dir, snapshot_days=30, metadata_days=30, current_time=current)
            self.assertFalse(preview["applied"])
            self.assertTrue(old_snapshot.exists())
            maintenance.prune(data_dir, snapshot_days=30, metadata_days=30, apply=True, current_time=current)
            self.assertFalse(old_snapshot.exists())
            self.assertEqual(state.load_json(cache_path)["repositories"], {})
            self.assertTrue((data_dir / "profile.json").exists())
            self.assertTrue((data_dir / "feedback.jsonl").exists())

    def test_doctor_offline_reports_valid_and_corrupt_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            profile.initialize(data_dir)
            healthy = doctor.diagnose(data_dir, offline=True)
            self.assertTrue(healthy["ok"])
            (data_dir / "profile.json").write_text("{broken", encoding="utf-8")
            broken = doctor.diagnose(data_dir, offline=True)
            self.assertFalse(broken["ok"])
            self.assertTrue(any(item["name"] == "profile" and item["status"] == "fail" for item in broken["checks"]))


if __name__ == "__main__":
    unittest.main()
