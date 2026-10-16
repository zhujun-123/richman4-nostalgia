"""Launcher validation with generated data; contains no original game resources."""
import contextlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import nostalgia


class NostalgiaSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.game = self.root / "游戏 目录"
        self.game.mkdir()
        # Minimal archive headers test the preflight, not the game's full decoder.
        for name in nostalgia.REQUIRED:
            (self.game / name).write_bytes(struct.pack("<6I", 20, 0, 0, 0, 0, 4))
        for name in nostalgia.MUSIC:
            (self.game / name).write_bytes(b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60")

    def test_native_assets_do_not_require_executable(self):
        result = nostalgia.check_assets(self.game)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["archives"]), 7)
        self.assertEqual(len(set(nostalgia.MUSIC)), 25)

    def test_missing_directory_returns_diagnostic(self):
        self.assertTrue(nostalgia.check_assets(self.root / "absent")["errors"])

    def test_corrupt_archive_is_rejected(self):
        (self.game / "data.mkf").write_bytes(b"bad")
        self.assertTrue(any("data.mkf" in e for e in nostalgia.check_assets(self.game)["errors"]))

    def test_missing_and_empty_music_are_rejected(self):
        (self.game / nostalgia.MUSIC[0]).unlink()
        (self.game / nostalgia.MUSIC[1]).write_bytes(b"")
        self.assertEqual(len(nostalgia.check_assets(self.game)["errors"]), 2)

    def test_names_are_case_insensitive(self):
        source = self.game / "data.mkf"
        source.rename(self.game / "DATA.MKF")
        self.assertEqual(nostalgia.check_assets(self.game)["errors"], [])

    def test_setup_keeps_source_files_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.game.iterdir()}
        config = self.root / "local/config.json"
        with patch.object(nostalgia, "CONFIG", config), patch.dict(os.environ, {"RICH4_ASSETS": ""}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(nostalgia.main(["setup", str(self.game)]), 0)
            self.assertEqual(nostalgia.asset_directory(), self.game)
        self.assertEqual(json.loads(config.read_text())["assets"], str(self.game))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.game.iterdir()})

    def test_missing_assets_stop_before_build_or_launch(self):
        with patch.object(nostalgia, "build_native") as build, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(nostalgia.main(["play", "--assets", str(self.root / "absent")]), 2)
            build.assert_not_called()

    def test_explicit_path_overrides_environment_and_local_config(self):
        with patch.dict(os.environ, {"RICH4_ASSETS": str(self.root / "other")}):
            self.assertEqual(nostalgia.asset_directory(self.game), self.game)

    def test_invalid_config_shape_reports_error(self):
        config = self.root / "invalid.json"
        config.write_text('[]')
        with patch.object(nostalgia, "CONFIG", config), patch.dict(os.environ, {"RICH4_ASSETS": ""}), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(nostalgia.main(["check"]), 1)

    def test_broken_json_reports_error(self):
        config = self.root / "invalid.json"
        config.write_text('{')
        with patch.object(nostalgia, "CONFIG", config), patch.dict(os.environ, {"RICH4_ASSETS": ""}), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(nostalgia.main(["check"]), 1)

    def test_rosetta_python_selects_native_arm64(self):
        result = subprocess.CompletedProcess([], 0, stdout="1\n", stderr="")
        with patch.object(nostalgia.platform, "machine", return_value="x86_64"), \
                patch.object(nostalgia.subprocess, "run", return_value=result):
            self.assertEqual(nostalgia.native_architecture(), "arm64")

    def test_native_arm64_does_not_need_rosetta_probe(self):
        with patch.object(nostalgia.platform, "machine", return_value="arm64"), \
                patch.object(nostalgia.subprocess, "run") as probe:
            self.assertEqual(nostalgia.native_architecture(), "arm64")
            probe.assert_not_called()

    def test_intel_mac_keeps_x86_64(self):
        result = subprocess.CompletedProcess([], 0, stdout="0\n", stderr="")
        with patch.object(nostalgia.platform, "machine", return_value="x86_64"), \
                patch.object(nostalgia.subprocess, "run", return_value=result):
            self.assertEqual(nostalgia.native_architecture(), "x86_64")

    def test_unavailable_hardware_probe_keeps_process_architecture(self):
        with patch.object(nostalgia.platform, "machine", return_value="x86_64"), \
                patch.object(nostalgia.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(nostalgia.native_architecture(), "x86_64")


if __name__ == "__main__":
    unittest.main()
