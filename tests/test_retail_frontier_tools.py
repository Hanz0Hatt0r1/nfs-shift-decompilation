"""Regression tests for retail frontier automation and D3D9 comparison.

Runs without SHIFT.exe, retail data, a display, Vulkan, or a multi-GB P-code ELF.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import retail_frontier as frontier  # noqa: E402
import compare_shift_d3d9 as d3d9  # noqa: E402


class RetailFrontierTests(unittest.TestCase):
    def test_real_v173_diagnostic(self):
        log = ROOT / "evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log"
        result = frontier.inspect_log(log.read_text(encoding="utf-8"), 1)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["dispatches"], 49065)
        self.assertEqual(result["unique_functions"], 1249)
        self.assertEqual(result["return_address"], "0x00839b53")
        self.assertIn("D3DXCreateTexture", result["blocker"])
        self.assertFalse(result["retail_rendering_proven"])

    def test_frame_loop_is_not_retail_rendering(self):
        data = {
            "format": "SHIFT.NativeRuntimeFrameLoop/1",
            "frames_rendered": 1800,
            "validation_errors": 0,
            "recompiled_pe_image_loaded": True,
            "recompiled_pcode_functions_dispatched": 342703,
            "recompiled_pcode_unique_functions_dispatched": 1417,
        }
        report = frontier.inspect_log(json.dumps(data) + "\n", 0)
        self.assertEqual(report["status"], "host-frame-loop")
        self.assertEqual(report["frames_rendered"], 1800)
        self.assertFalse(report["retail_rendering_proven"])

    def test_comparison_advancement_and_regression(self):
        old = {"status": "blocked", "dispatches": 49065,
               "unique_functions": 1249, "blocker": "D3DXCreateTexture"}
        improved = dict(old, dispatches=50000, unique_functions=1270)
        self.assertEqual(frontier.compare(improved, old)["result"], "advanced")
        self.assertEqual(frontier.compare(old, old)["result"], "unchanged")
        degraded = dict(old, dispatches=48000)
        self.assertEqual(frontier.compare(degraded, old)["result"], "regressed")
        invalid = dict(old, status="timeout")
        self.assertEqual(frontier.compare(invalid, old)["result"], "unverified")
        validation = dict(old, validation_errors=1)
        self.assertEqual(frontier.compare(validation, old)["result"], "regressed")
        changed = dict(old, blocker="unknown other error")
        self.assertEqual(frontier.compare(changed, old)["result"], "changed")

    def test_cli_inspect_and_json_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            log = folder / "failed.log"
            log.write_text(
                "Loaded PE32 image into P-code guest RAM\n"
                "shift_runtime: recompiled PE32 entry point 0x0090488a failed "
                "after 12 P-code function dispatches across 7 unique functions: "
                "unimplemented PE import d3d9.dll!GetDeviceCaps;\n",
                encoding="utf-8",
            )
            output = folder / "frontier.json"
            cmd = [sys.executable, str(ROOT / "tools/retail_frontier.py"),
                   "inspect", "--log", str(log), "--output", str(output)]
            subprocess.run(cmd, check=True, capture_output=True)
            baseline = folder / "baseline.json"
            baseline.write_text(output.read_text(encoding="utf-8"), encoding="utf-8")
            proc = subprocess.run(cmd + ["--baseline", str(baseline)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(output.read_text())["comparison"]["result"],
                             "unchanged")
            wrong = folder / "wrong-baseline.json"
            wrong.write_text('{"format":"unrelated"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                frontier.load_frontier(wrong)


class D3D9ComparisonTests(unittest.TestCase):
    def test_pointer_identity_does_not_pollute_contract(self):
        a = {"event": "create_texture", "texture_ptr": "0xaaaa",
             "width": 1024, "height": 4096, "levels": 1, "usage": 1,
             "format": 21, "pool": 0}
        b = dict(a, texture_ptr="0xbbbb", width="0x400")
        self.assertEqual(d3d9.event_contract(a), d3d9.event_contract(b))

    def test_failed_import_is_request_only(self):
        log = (
            "shift_runtime: failed after 49065 P-code function dispatches across "
            "1249 unique functions: unimplemented PE import "
            "d3dx9_41.dll!D3DXCreateTexture; called from 0x008391b0 "
            "args=[0x2001b3f4,0x00000400,0x00001000,0x00000001,"
            "0x00000001,0x00000015,0x00000000,0x27f4a898]"
        )
        events = d3d9.linux_failure_request(log)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["fields"]["width"], 1024)
        self.assertEqual(events[0]["fields"]["height"], 4096)
        self.assertEqual(events[0]["observation"], "request-only")

    def test_subsequence_and_missing(self):
        texture = d3d9.event_contract({
            "event": "create_texture", "width": 1024, "height": 4096,
            "levels": 1, "usage": 1, "format": 21, "pool": 0,
        })
        other = {"event": "clear", "fields": {"clear_flags": 1}}
        matched = d3d9.compare([other, texture], [texture], "jsonl")
        self.assertEqual(matched["status"], "matched-subsequence")
        request = dict(texture, observation="request-only")
        self.assertEqual(d3d9.compare([texture], [request], "probe-diagnostic")["status"],
                         "request-only-match")
        missing = d3d9.compare([other], [texture], "jsonl")
        self.assertEqual(missing["status"], "not-found")
        self.assertEqual(d3d9.compare([], [texture], "jsonl")["status"],
                         "insufficient-evidence")
        self.assertFalse(matched["semantic_parity_proven"])

    def test_cli_parses_retained_v173_log_against_proxy_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proxy = root / "proxy.jsonl"
            proxy.write_text(json.dumps({
                "event": "create_texture", "width": 1024, "height": 4096,
                "levels": 1, "usage": 1, "format": 21, "pool": 0,
                "texture_ptr": "0xdeadbeef",
            }) + "\n", encoding="utf-8")
            candidate = ROOT / "evidence/retail_frontier_20261019/shift-probe-v173-d3dx-device-map.log"
            output = root / "result.json"
            cmd = [sys.executable, str(ROOT / "tools/compare_shift_d3d9.py"),
                   "--reference", str(proxy), "--candidate", str(candidate),
                   "--output", str(output), "--strict"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "request-only-match")
            self.assertFalse(data["semantic_parity_proven"])
            proxy.write_text('{"event":"create_texture","width":4}\n', encoding="utf-8")
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
