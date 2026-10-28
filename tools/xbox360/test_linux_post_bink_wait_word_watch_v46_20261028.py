#!/usr/bin/env python3
"""Regression checks for the read-only guest WAIT_REG_MEM word watch."""

from __future__ import annotations

import re
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / "tools/xbox360/trace_linux_post_bink_worker_route_v46_wait_word_watch_20261028.gdb"
RUNNER = ROOT / "tools/xbox360/capture_linux_post_bink_worker_route_v46_wait_word_watch_20261028.py"
JOIN_EVIDENCE = ROOT / "evidence/xbox360_linux_native_660_callback_wait_join_20261028.json"
FRONTIER_EVIDENCE = ROOT / "evidence/xbox360_linux_native_wait_reg_mem_frontier_20261028.json"
PAIRED_EVIDENCE = ROOT / "evidence/xbox360_linux_gpu_backend_comparison_process1_20261028.json"


def python_blocks(script: str) -> list[str]:
    blocks = []
    lines = script.splitlines()
    index = 0
    while index < len(lines):
        if lines[index] != "python":
            index += 1
            continue
        index += 1
        block = []
        while index < len(lines) and lines[index] != "end":
            block.append(lines[index])
            index += 1
        if index == len(lines):
            raise AssertionError("unterminated GDB Python block")
        blocks.append(textwrap.dedent("\n".join(block)))
        index += 1
    return blocks


class WaitWordWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.trace = TRACE.read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_gdb_python_blocks_compile(self) -> None:
        blocks = python_blocks(self.trace)
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            compile(block, str(TRACE), "exec")

    def test_runner_uses_the_v46_trace_and_records_its_identity(self) -> None:
        self.assertIn(
            '"tools/xbox360/trace_linux_post_bink_worker_route_v46_wait_word_watch_20261028.gdb"',
            self.runner,
        )
        self.assertIn('str(SCRIPT)', self.runner)

    def test_watch_is_armed_after_bink_and_uses_a_write_watchpoint(self) -> None:
        self.assertIn('arm_wait_word_watch(base, "bink_complete")', self.trace)
        self.assertIn('os.environ.get("SHIFT_QUEUE_TRACE_WAIT_WORD_WATCH") != "1"', self.trace)
        self.assertIn('guest_address = 0x1B964004', self.trace)
        self.assertIn('gdb.BP_WATCHPOINT', self.trace)
        self.assertIn('wp_class=gdb.WP_WRITE', self.trace)
        self.assertIn('"before": self.previous', self.trace)
        self.assertIn('"after": after', self.trace)

    def test_watch_records_the_final_value_and_does_not_write_guest_memory(self) -> None:
        self.assertIn('"fixed_guest_word_watch": fixed_guest_word_watch', self.trace)
        self.assertIn('fixed_guest_word_watch["final_value"]', self.trace)
        helper = self.trace.split("def arm_wait_word_watch", 1)[1].split(
            "class SceneFunction", 1
        )[0]
        self.assertNotRegex(helper, re.compile(r"write_memory|memory\.write|set\s+\*", re.I))

    def test_source0_callbacks_are_sampled_around_wait_word_changes(self) -> None:
        self.assertIn('if source == 0:', self.trace)
        self.assertIn('self.record_source0_sample(context, base, ppc_reg(context, 4))', self.trace)
        self.assertIn('"source0_callback_events": []', self.trace)
        self.assertIn('"wait_word_value_sampled": wait_value', self.trace)
        self.assertIn('"gpu_dispatch_id": sample_gpu_dispatch_id()', self.trace)
        self.assertIn('state["source0_callback_capture_until"] = now + 0.300', self.trace)
        self.assertIn('now - state["source0_callback_last_sample_monotonic"] < 0.200', self.trace)

    def test_source0_entry_return_probe_is_rate_limited_and_captures_inflight_calls(self) -> None:
        self.assertIn('event["wait_word_value_sampled"] == 1', self.trace)
        self.assertIn('>= 1.0):', self.trace)
        self.assertIn('Source0CallbackFinish(gdb.newest_frame(), entry)', self.trace)
        self.assertIn('"duration_seconds": round(duration, 3)', self.trace)
        self.assertIn('snapshot["active_source0_callbacks"]', self.trace)
        self.assertIn('"source0_callback_return_events"', self.trace)

    def test_native_dispatch_join_and_wait_target_are_consistent(self) -> None:
        import json

        evidence = json.loads(JOIN_EVIDENCE.read_text(encoding="utf-8"))
        join = evidence["matched_source1_dispatch"]
        wait = evidence["subsequent_wait_reg_mem"]
        self.assertTrue(join["matched"])
        self.assertEqual(join["p1_gpu_dispatch_id_decimal"], int(join["p2_dispatch_id"], 16))
        self.assertEqual(join["p2_packet_ordinal"], 246)
        self.assertEqual(join["p2_source_ib_offset"], 11924)
        self.assertTrue(wait["same_root_batch"])
        self.assertTrue(wait["same_source_ib"])
        self.assertEqual(wait["packet_ordinal"], 250)
        self.assertEqual(wait["guest_address"], "0x1B964004")
        self.assertEqual(wait["poll_address"], "0x1B964006")
        self.assertEqual(wait["decoded_value"], "0x00000001")
        self.assertEqual(wait["reference"], "0x00000000")
        self.assertFalse(wait["predicate"])

    def test_shutdown_tail_writes_are_not_mistaken_for_wait_word_release(self) -> None:
        import json

        evidence = json.loads(FRONTIER_EVIDENCE.read_text(encoding="utf-8"))
        writes = evidence["shutdown_tail_packet_observations"]
        self.assertEqual([item["event_id"] for item in writes], [2741, 2743])
        self.assertEqual([item["guest_address"] for item in writes], [
            "0x17af4000", "0x17af4000",
        ])
        self.assertEqual(
            [(item["guest_value_before"], item["guest_value_after"]) for item in writes],
            [(2735, 2737), (2737, 2739)],
        )
        self.assertNotEqual(writes[0]["guest_address"], "0x1b964004")
        self.assertEqual(
            evidence["process2_source_review_report"]["source_commit"],
            "7aa414ab9e246765220ae802d8c2b25f7f344e04",
        )

    def test_candidate_expansions_do_not_claim_the_late_wait_word_writer(self) -> None:
        import json

        evidence = json.loads(JOIN_EVIDENCE.read_text(encoding="utf-8"))
        audit = evidence["p2_memory_write_candidate_audit"]
        self.assertEqual(audit["memory_write_candidate_record_count"], 48)
        self.assertEqual(audit["candidate_record_lines_containing_wait_word_address"], 0)
        self.assertEqual(audit["scratch_reg1_writeback_target_record_count"], 3)
        self.assertEqual(
            [row["guest_value_after"] for row in audit["scratch_reg1_writeback_records"]],
            ["0x00000001"] * 3,
        )
        self.assertIn("late 1->0 writer", audit["interpretation_limit"])

    def test_v46_captures_source0_context_without_claiming_causation(self) -> None:
        import json

        evidence = json.loads(JOIN_EVIDENCE.read_text(encoding="utf-8"))
        burst = evidence["source0_vblank_gap_and_catchup"]
        self.assertEqual(burst["catchup_interrupt_count"], 5123)
        self.assertEqual(burst["catchup_dispatch_ids"], ["0x0E78", "0x227B"])
        self.assertEqual(burst["completion_gap_minus_wait_ms"], 40)
        self.assertTrue(burst["vblank_trace_limit_reached"])
        self.assertIn("cannot distinguish them", burst["interpretation_limit"])
        probe = evidence["next_capture_source0_entry_return_probe"]
        self.assertEqual(probe["max_tracked_callbacks_per_second"], 1)
        self.assertEqual(probe["wait_word_value"], "0x00000001")
        self.assertFalse(probe["modifies_guest_state"])
        self.assertIn("source0_callback_events", self.trace)

    def test_p2_vblank_timing_plugin_is_pinned_and_trace_only(self) -> None:
        import json

        evidence = json.loads(JOIN_EVIDENCE.read_text(encoding="utf-8"))
        candidate = evidence["next_capture_source0_timing_plugin_candidate"]
        self.assertFalse(candidate["used_in_this_capture"])
        self.assertEqual(candidate["source_commit"], "96169b712c1edb679b9309b54efc8ff7ff17b613")
        self.assertEqual(candidate["linux_x86_64_plugin"]["sha256"],
                         "27f44ab0437b8030967522746618ad43f3c251b4e031a750b22d8821ffb061f6")
        self.assertEqual(candidate["source0_trace_fields"], [
            "tick_lag_intervals", "dispatch_gap_ns", "dispatch_elapsed_ns",
        ])
        self.assertIn("synchronous DispatchGuestInterrupt",
                      candidate["interpretation_guide"]["long_dispatch_elapsed_ns"])
        self.assertIn("does not by itself prove OS descheduling",
                      candidate["interpretation_guide"]["long_dispatch_gap_ns_and_high_tick_lag"])
        self.assertIn("no VBlank or interrupt behavior change", candidate["change_from_prior_plugin"])

    def test_next_xenos_comparison_artifact_matches_the_paired_capture(self) -> None:
        import json

        evidence = json.loads(JOIN_EVIDENCE.read_text(encoding="utf-8"))
        candidate = evidence["next_capture_xenos_plugin_candidate"]
        paired = json.loads(PAIRED_EVIDENCE.read_text(encoding="utf-8"))
        self.assertFalse(candidate["used_in_this_capture"])
        self.assertTrue(candidate["used_in_previous_paired_capture"])
        self.assertEqual(candidate["sha256"], paired["identity"]["xenos_plugin"]["sha256"])
        self.assertEqual(candidate["build_id"], paired["identity"]["xenos_plugin"]["build_id"])


if __name__ == "__main__":
    unittest.main()
