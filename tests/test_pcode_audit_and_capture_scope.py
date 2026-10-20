"""Asset-free regressions for verified Ghidra export and retail D3D9 scope tools."""
from __future__ import annotations

import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/ghidra"))

import audit_pcode_corpus as pcode  # noqa: E402
import d3d9_capture_scope as scope  # noqa: E402


def instruction(addr, data, mnemonic="MOV", flow="FALL_THROUGH"):
    return {
        "address": f"0x{addr:08x}", "bytes": data,
        "mnemonic": mnemonic, "flow_type": flow,
    }


def function_row(addr, instructions):
    return {
        "format": "REVENGINSTR.GhidraFunctionInstructions/1",
        "found": True,
        "function": {"address": f"0x{addr:08x}", "size": 256},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def write_corpus(path, rows):
    lines = "".join(json.dumps(row) + "\n" for row in rows)
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as output:
            output.write(lines)
    else:
        path.write_text(lines, encoding="utf-8")


class PcodeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.required = {0x0050f010: {0x0050f47d: "5e", 0x0050f481: "c3"}}

    def test_incomplete_verified_epilogue_fails_before_retail_boot(self):
        path = self.folder / "frozen.jsonl.gz"
        row = function_row(0x0050f010, [
            instruction(0x0050f010, "55", "PUSH"),
            instruction(0x0050f3f3, "90", "NOP"),
        ])
        write_corpus(path, [row])
        result = pcode.audit(path, self.required)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["counters"]["required_failures"], 2)
        self.assertEqual(result["counters"]["no_observed_return"], 1)
        self.assertTrue(all(
            issue["kind"] == "verified_instruction_mismatch"
            for issue in result["problem_samples"]
        ))

    def test_complete_verified_epilogue_passes(self):
        path = self.folder / "corrected.jsonl"
        row = function_row(0x0050f010, [
            instruction(0x0050f010, "55", "PUSH"),
            instruction(0x0050f47d, "5e", "POP"),
            instruction(0x0050f481, "c3", "RET", "TERMINATOR"),
        ])
        write_corpus(path, [row])
        self.assertEqual(pcode.audit(path, self.required)["status"], "passed")

    def test_legitimate_tail_call_is_only_a_warning(self):
        path = self.folder / "tail.jsonl"
        write_corpus(path, [function_row(0x00400000, [
            instruction(0x00400000, "e900000000", "JMP", "UNCONDITIONAL_JUMP")
        ])])
        result = pcode.audit(path, {})
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["counters"]["no_observed_return"], 1)

    def test_overlap_is_hard_failure(self):
        path = self.folder / "overlap.jsonl"
        write_corpus(path, [function_row(0x00400000, [
            instruction(0x00400000, "8be5"),
            instruction(0x00400001, "c3", "RET", "TERMINATOR"),
        ])])
        result = pcode.audit(path, {})
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["counters"]["overlapping_instructions"], 1)

    def test_missing_required_function_is_hard_failure(self):
        path = self.folder / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        result = pcode.audit(path, self.required)
        self.assertEqual(result["counters"]["missing_required_functions"], 1)
        self.assertEqual(result["status"], "blocked")

    def test_pe_reader_maps_real_section_header_offsets(self):
        image = bytearray(0x400)
        image[:2] = b"MZ"
        struct.pack_into("<I", image, 0x3c, 0x80)
        image[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<H", image, 0x80 + 6, 1)
        struct.pack_into("<H", image, 0x80 + 20, 0xe0)
        opt = 0x80 + 24
        struct.pack_into("<H", image, opt, 0x10b)
        struct.pack_into("<I", image, opt + 28, 0x00400000)
        section = opt + 0xe0
        struct.pack_into("<IIII", image, section + 8, 0x100, 0x1000, 0x100, 0x200)
        image[0x220:0x223] = bytes.fromhex("8be5c3")
        path = self.folder / "fixture.exe"
        path.write_bytes(image)
        actual = pcode.pe_bytes(path, [(0x00401020, bytes.fromhex("8be5c3"))])
        self.assertEqual(actual[0x00401020].hex(), "8be5c3")
        with self.assertRaises(ValueError):
            pcode.pe_bytes(path, [(0x00403020, b"\xc3")])

    def test_manifest_parse_and_cli_rejects_missing_epilogue(self):
        corpus = self.folder / "frozen.jsonl"
        write_corpus(corpus, [function_row(0x0050f010, [
            instruction(0x0050f010, "c3", "RET", "TERMINATOR")
        ])])
        manifest = self.folder / "expected.json"
        manifest.write_text(json.dumps({
            "format": pcode.REQUIREMENTS_FORMAT,
            "functions": {"0x0050f010": [
                {"address": "0x0050f481", "bytes": "c3"}
            ]},
        }))
        out = self.folder / "audit.json"
        completed = subprocess.run([
            sys.executable, str(ROOT / "tools/ghidra/audit_pcode_corpus.py"),
            "--corpus", str(corpus), "--requirements", str(manifest),
            "--output", str(out),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(json.loads(out.read_text())["status"], "blocked")


class CaptureScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_committed_retail_capture_is_draw_observed_but_not_translated(self):
        path = ROOT / "evidence/retail_frontier_20261018/d3d9_race_window_capture.json"
        counts = scope.read_audit(path)
        self.assertEqual(counts["draw_indexed_primitive"], 13069)
        result = scope.inventory(counts)
        self.assertEqual(result["status"], "capture-inventory")
        self.assertEqual(result["first_draw_command_counts"]["draw_indexed_primitive"], 13069)
        self.assertIn("draw_indexed_primitive", result["first_draw_commands_not_yet_vulkan_verified"])
        self.assertFalse(result["retail_draw_translation_proven"])
        self.assertEqual(result["known_vulkan_submission_scope"], ["clear", "present_result"])

    def test_bounded_state_inventory_and_malformed_line_detection(self):
        path = self.folder / "trace.jsonl"
        path.write_text(
            '{"event":"set_render_state","state":168,"value":15}\n'
            '{"event":"set_render_state","state":"0xa8"}\n'
            '{"event":"set_sampler_state","state":4}\n'
            '{"event":"draw_indexed_primitive","primitive_count":2}\n'
            'not-json\n',
            encoding="utf-8"
        )
        counts, states, malformed = scope.read_capture(path)
        self.assertEqual(counts["draw_indexed_primitive"], 1)
        self.assertEqual(states["set_render_state"], [168])
        self.assertEqual(states["set_sampler_state"], [4])
        self.assertEqual(malformed, 1)

    def test_capture_vs_audit_mismatch_fails_closed(self):
        capture = self.folder / "trace.jsonl"
        capture.write_text('{"event":"clear"}\n', encoding="utf-8")
        audit = self.folder / "audit.json"
        audit.write_text(json.dumps({"audit": {"event_counts": {"clear": 2}}}))
        result = subprocess.run([
            sys.executable, str(ROOT / "tools/d3d9_capture_scope.py"),
            "--audit", str(audit), "--capture", str(capture),
            "--output", str(self.folder / "result.json")
        ], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
