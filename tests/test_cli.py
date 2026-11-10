from __future__ import annotations

import json
import os
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

from shazam_cli import cli


class CliTests(unittest.TestCase):
    def test_clean_flattens_remote_text(self) -> None:
        self.assertEqual(cli.clean("  Artist\n  Name  "), "Artist Name")

    @patch("shazam_cli.cli.subprocess.run")
    def test_muted_microphone_is_detected(self, run) -> None:
        run.return_value = CompletedProcess([], 0, "Mute: yes\n", "")
        self.assertTrue(cli.microphone_is_muted(None))

    @patch("shazam_cli.cli.subprocess.run")
    def test_unmuted_microphone_is_detected(self, run) -> None:
        run.return_value = CompletedProcess([], 0, "Mute: no\n", "")
        self.assertFalse(cli.microphone_is_muted(None))

    def test_history_round_trip_and_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            with patch.dict(os.environ, {"XDG_STATE_HOME": state_dir}):
                cli.save_history({"title": "First", "subtitle": "Artist A"})
                cli.save_history({"title": "Second", "subtitle": "Artist B"})
                entries = cli.load_history()

                self.assertEqual([entry["title"] for entry in entries], ["First", "Second"])
                history = Path(state_dir) / "shazam" / "history.jsonl"
                self.assertEqual(history.stat().st_mode & 0o777, 0o600)

    def test_history_skips_damaged_lines(self) -> None:
        with tempfile.TemporaryDirectory() as state_dir:
            with patch.dict(os.environ, {"XDG_STATE_HOME": state_dir}):
                path = cli.history_path()
                path.parent.mkdir(parents=True)
                path.write_text('{broken}\n' + json.dumps({"title": "Good"}) + "\n")
                self.assertEqual(cli.load_history(), [{"title": "Good"}])


if __name__ == "__main__":
    unittest.main()
