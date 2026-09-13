from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import release_check  # noqa: E402


class ReleaseCheckTests(unittest.TestCase):
    def test_current_repository_metadata_is_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        errors, warnings = release_check.validate(root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_strict_mode_accepts_resolved_repository_location(self) -> None:
        root = Path(__file__).resolve().parents[1]
        errors, warnings = release_check.validate(root, strict=True, tag="v0.6.1")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_release_tag_must_match_version(self) -> None:
        root = Path(__file__).resolve().parents[1]
        errors, _ = release_check.validate(root, tag="v9.9.9")
        self.assertIn("release tag 'v9.9.9' does not match VERSION; expected 'v0.6.1'", errors)

    def test_missing_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = release_check.validate(Path(directory))
        self.assertTrue(any(error.startswith("missing required file:") for error in errors))


if __name__ == "__main__":
    unittest.main()
