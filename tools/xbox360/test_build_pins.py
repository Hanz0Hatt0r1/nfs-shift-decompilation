#!/usr/bin/env python3
"""Regression tests for the Xbox 360 build pin ledger and verifier.

Style matches the other tools/xbox360/test_*.py scripts: plain unittest with a
main() that exits non-zero on failure.

Covers:
  * pins.json schema (required keys, artifact entries, status vocabulary);
  * every sha256 in the ledger is 64 lowercase hex;
  * verify_pins.py tolerates missing artifacts (unavailable, not a crash);
  * verify_pins.py fails loudly on a hash mismatch;
  * verify_pins.py reports exit code 2 on an invalid ledger;
  * --json and --explain behave.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_DIR = HERE / "build"
LEDGER_PATH = BUILD_DIR / "pins.json"
VERIFY_PATH = BUILD_DIR / "verify_pins.py"


def _load_verify_module():
    spec = importlib.util.spec_from_file_location("verify_pins", VERIFY_PATH)
    assert spec is not None and spec.loader is not None, "cannot load verify_pins.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verify_pins = _load_verify_module()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _valid_ledger(artifacts: dict) -> dict:
    """Minimal ledger that passes schema validation."""
    return {
        "_schema_version": 1,
        "updated_on": "2026-10-30",
        "title": {
            "name": "test", "title_id": "454108B4",
            "xex_sha256": "0" * 64, "xex_status": "unverified",
        },
        "sdk": {
            "repository": "https://github.com/rexglue/rexglue-sdk",
            "fork_repository": "https://github.com/Hanz0Hatt0r1/rexglue-sdk",
            "fork_commit": "32afce4",
            "fork_commit_status": "unverified",
            "integrated": False,
        },
        "recipe": {"source": "tools/xbox360/build/README.md"},
        "artifacts": artifacts,
    }


class LedgerSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(LEDGER_PATH.is_file(), f"missing {LEDGER_PATH}")
        self.ledger = verify_pins.load_ledger(LEDGER_PATH)

    def test_loads_and_has_required_keys(self) -> None:
        for key in ("_schema_version", "updated_on", "title", "sdk",
                    "artifacts", "recipe"):
            self.assertIn(key, self.ledger, f"ledger missing {key}")

    def test_expected_artifacts_present(self) -> None:
        for name in ("runtime", "host", "plugin_native_vulkan", "plugin_xenos"):
            self.assertIn(name, self.ledger["artifacts"], f"missing artifact {name}")

    def test_sdk_section_names_fork_and_recipe(self) -> None:
        sdk = self.ledger["sdk"]
        self.assertIn("fork_repository", sdk)
        self.assertIn("Hanz0Hatt0r1/rexglue-sdk", sdk["fork_repository"])
        self.assertIn("fork_commit", sdk)
        self.assertIn("fork_commit_status", sdk)
        self.assertEqual(sdk.get("build_recipe"), "tools/xbox360/build/pins.json")

    def test_recipe_section_records_recovered_config(self) -> None:
        recipe = self.ledger["recipe"]
        self.assertEqual(recipe["build_type"], "Release")
        self.assertEqual(recipe["generator"], "Ninja Multi-Config")
        self.assertIn("clang", recipe["compiler"]["cxx"])
        self.assertIn("march=x86-64-v2", recipe["cxx_flags"])
        self.assertTrue(
            any("REXGLUE_USE_VULKAN=ON" in flag
                for flag in recipe["configuration_flags"]),
            "recipe must record -DREXGLUE_USE_VULKAN=ON",
        )

    def test_every_sha_is_64_lowercase_hex(self) -> None:
        seen = 0
        for name, entry in self.ledger["artifacts"].items():
            sha = entry["sha256"]
            self.assertIsInstance(sha, str, f"{name}.sha256 not a string")
            self.assertEqual(len(sha), 64, f"{name}.sha256 is not 64 chars")
            self.assertEqual(sha, sha.lower(), f"{name}.sha256 has uppercase")
            int(sha, 16)  # raises if not hex
            seen += 1
        self.assertGreaterEqual(seen, 4)

    def test_commit_hashes_are_hex_or_null(self) -> None:
        sdk = self.ledger["sdk"]
        for key in ("fork_commit", "fork_commit_full", "base_release_tag"):
            value = sdk.get(key)
            if value is None:
                continue
            self.assertIsInstance(value, str)
            int(value, 16)  # raises if not hex
            self.assertGreaterEqual(len(value), 7)
        for name, entry in self.ledger["artifacts"].items():
            value = entry.get("built_from_commit")
            if value is not None:
                int(value, 16)
                self.assertEqual(len(value), 40,
                                 f"{name}.built_from_commit must be a full id")

    def test_status_vocabulary(self) -> None:
        allowed = {"verified", "unverified", "unavailable", "mismatch"}
        self.assertIn(self.ledger["sdk"]["fork_commit_status"], allowed)
        self.assertIn(self.ledger["title"]["xex_status"], allowed)
        for name, entry in self.ledger["artifacts"].items():
            self.assertIn(entry["status"], allowed, f"{name}.status invalid")
            if entry.get("built_from_commit_status") is not None:
                self.assertIn(entry["built_from_commit_status"], allowed)

    def test_verified_entries_carry_a_verification_date(self) -> None:
        self.assertRegex(self.ledger["verified_on"], r"^\d{4}-\d{2}-\d{2}$")
        for name, entry in self.ledger["artifacts"].items():
            if entry["status"] == "verified":
                self.assertRegex(entry.get("verified_on", ""),
                                 r"^\d{4}-\d{2}-\d{2}$",
                                 f"{name} is verified but has no verified_on")


class VerifyBehaviourTests(unittest.TestCase):
    def _write(self, tmp: Path, ledger: dict) -> Path:
        path = tmp / "pins.json"
        path.write_text(json.dumps(ledger), encoding="utf-8")
        return path

    def test_missing_artifacts_are_unavailable_not_failure(self) -> None:
        ledger = _valid_ledger({
            "ghost": {
                "name": "does-not-exist.so", "kind": "graphics_plugin",
                "sha256": "a" * 64, "status": "verified",
                "path": "/nonexistent/does-not-exist.so",
            }
        })
        report = verify_pins.verify(ledger)
        self.assertTrue(report["ok"])
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["unavailable"], 1)
        self.assertEqual(report["mismatched"], 0)
        self.assertEqual(report["results"][0]["result"], "unavailable")

    def test_match_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "fake.so"
            artifact.write_text("payload", encoding="utf-8")
            ledger = _valid_ledger({
                "runtime": {
                    "name": "fake.so", "kind": "runtime",
                    "sha256": _sha256_text("payload"), "status": "verified",
                    "path": str(artifact),
                }
            })
            report = verify_pins.verify(ledger)
            self.assertTrue(report["ok"])
            self.assertEqual(report["matched"], 1)

    def test_mismatch_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "fake.so"
            artifact.write_text("payload", encoding="utf-8")
            ledger = _valid_ledger({
                "runtime": {
                    "name": "fake.so", "kind": "runtime",
                    "sha256": "b" * 64, "status": "verified",
                    "path": str(artifact),
                }
            })
            report = verify_pins.verify(ledger)
            self.assertFalse(report["ok"])
            self.assertEqual(report["exit_code"], 1)
            self.assertEqual(report["mismatched"], 1)
            self.assertEqual(report["results"][0]["result"], "mismatch")

    def test_required_artifact_that_is_missing_fails(self) -> None:
        ledger = _valid_ledger({
            "runtime": {
                "name": "gone.so", "kind": "runtime",
                "sha256": "c" * 64, "status": "verified",
                "path": "/nonexistent/gone.so",
            }
        })
        report = verify_pins.verify(ledger, require=["runtime"])
        self.assertFalse(report["ok"])
        self.assertEqual(report["exit_code"], 1)

    def test_invalid_schema_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pins.json"
            path.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")
            with self.assertRaises(verify_pins.LedgerError):
                verify_pins.load_ledger(path)

    def test_short_sha_is_rejected(self) -> None:
        ledger = _valid_ledger({
            "runtime": {
                "name": "x.so", "kind": "runtime",
                "sha256": "deadbeef", "status": "verified",
            }
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(Path(tmpdir), ledger)
            with self.assertRaises(verify_pins.LedgerError):
                verify_pins.load_ledger(path)

    def test_uppercase_sha_is_rejected(self) -> None:
        ledger = _valid_ledger({
            "runtime": {
                "name": "x.so", "kind": "runtime",
                "sha256": "A" * 64, "status": "verified",
            }
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write(Path(tmpdir), ledger)
            with self.assertRaises(verify_pins.LedgerError):
                verify_pins.load_ledger(path)

    def test_missing_ledger_file_is_an_error_not_a_crash(self) -> None:
        with self.assertRaises(verify_pins.LedgerError):
            verify_pins.load_ledger(Path("/nonexistent/pins.json"))


class CommandLineTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(VERIFY_PATH), *args],
            capture_output=True, text=True, check=False,
        )

    def test_json_output_parses_and_reports_counts(self) -> None:
        proc = self._run("--json")
        self.assertIn(proc.returncode, (0, 1), proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["checked"], len(data["results"]))
        self.assertEqual(
            data["checked"],
            data["matched"] + data["unavailable"] + data["mismatched"],
        )
        self.assertIn("unverified_pins", data)

    def test_missing_artifacts_do_not_crash_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = _valid_ledger({
                "runtime": {
                    "name": "gone.so", "kind": "runtime",
                    "sha256": "d" * 64, "status": "verified",
                    "path": "/nonexistent/gone.so",
                }
            })
            path = Path(tmpdir) / "pins.json"
            path.write_text(json.dumps(ledger), encoding="utf-8")
            proc = self._run("--json", "--ledger", str(path))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["unavailable"], 1)
            self.assertEqual(data["results"][0]["result"], "unavailable")

    def test_invalid_ledger_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pins.json"
            path.write_text("{not json", encoding="utf-8")
            proc = self._run("--json", "--ledger", str(path))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_explain_resolves_a_real_artifact(self) -> None:
        proc = self._run("--explain", "plugin_native_vulkan")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("artifact     : plugin_native_vulkan", proc.stdout)
        self.assertIn("produced by", proc.stdout)
        self.assertIn("sdk fork", proc.stdout)

    def test_explain_unknown_artifact_is_non_fatal(self) -> None:
        proc = self._run("--explain", "not_an_artifact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("unknown artifact", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
