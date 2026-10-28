#!/usr/bin/env python3
"""Regression coverage for contiguous PM4-to-guest callback alignment."""

import importlib.util
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "tools/audit_pm4_interrupt_join.py"
SPEC = importlib.util.spec_from_file_location("audit_pm4_interrupt_join", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
RETAIL_EVIDENCE = (
    Path(__file__).parents[2]
    / "evidence/process2_gpu_backend_resolvepr2_source1_interrupt_join_20261028.json"
)
QUEUE_WAIT_R2_EVIDENCE = (
    Path(__file__).parents[2]
    / "evidence/process2_p1_native_queuewait_r2_source1_interrupt_join_20261028.json"
)


def p1_callback(timestamp):
    return {
        "wall_clock_epoch_ms": timestamp,
        "callback_function": 0x823B8C60,
        "callback_object": 0xFB963000,
        "callback_data": 0xC9684880,
        "callback_mask": 0x04,
    }


def p2_interrupt(interrupt_id, timestamp):
    return {
        "id": interrupt_id,
        "timestamp_ms": timestamp,
        "generation": 1,
        "rptr": interrupt_id * 4,
        "wptr": interrupt_id * 4 + 3,
        "ring": 0x09752580,
        "ordinal": interrupt_id % 400,
        "packet_source": 0x09600000,
        "packet_offset": 0x1200,
        "mask": 0x04,
        "dispatched": 0x04,
        "callbacks": [
            {
                "cpu": 2,
                "callback": 0x823B37B8,
                "data": 0xB7365F00,
                "status": "invoked",
            }
        ],
    }


class InterruptJoinTests(unittest.TestCase):
    def test_captured_source1_interrupt_join_is_internally_consistent(self):
        evidence = json.loads(RETAIL_EVIDENCE.read_text())
        capture = evidence["capture"]
        audit = evidence["audit"]
        summary = audit["summary"]
        rows = audit["rows"]
        first_id, last_id = summary["p2_interrupt_id_range"]
        shader_capture = json.loads(
            (
                RETAIL_EVIDENCE.parent
                / "process2_selected_shader_state_dump_20261028.json"
            ).read_text()
        )

        self.assertFalse(capture["guest_memory_modified_by_probe"])
        self.assertEqual(capture["ring_trace_malformed_record_count"], 0)
        self.assertEqual(
            capture["p1_run"]["native_wall_clock_utc"],
            ["2026-10-28T01:15:34.928Z", "2026-10-28T01:17:52.902Z"],
        )
        self.assertEqual(
            capture["xex_sha256"],
            shader_capture["retail_target"]["capture_identity"]["xex_sha256"],
        )
        self.assertNotEqual(
            capture["plugin_sha256"],
            shader_capture["retail_target"]["capture_identity"]["plugin_sha256"],
        )
        self.assertEqual(len(rows), summary["joined_rows"])
        self.assertEqual(
            [row["p1_callback_index"] for row in rows], list(range(len(rows)))
        )
        self.assertEqual(
            [row["p2_pm4_interrupt_id"] for row in rows],
            list(range(first_id, last_id + 1)),
        )
        self.assertEqual(len(rows), last_id - first_id + 1)
        for row in rows:
            with self.subTest(interrupt_id=row["p2_pm4_interrupt_id"]):
                self.assertEqual(row["source"], 1)
                self.assertEqual(row["ring_generation"], 1)
                self.assertLess(row["batch_rptr"], 8192)
                self.assertLess(row["batch_wptr"], 8192)
                self.assertGreater(
                    (row["batch_wptr"] - row["batch_rptr"]) % 8192, 0
                )
                self.assertEqual(row["p1_cpu_mask"], "0x04")
                self.assertEqual(row["cpu_mask"], row["p1_cpu_mask"])
                self.assertEqual(row["dispatched_cpu_mask"], row["cpu_mask"])
                self.assertEqual(row["dispatch_cpu"], 2)
                self.assertEqual(row["dispatch_status"], "invoked")
                self.assertEqual(row["outer_callback_wrapper"], "0x823b37b8")
                self.assertLessEqual(
                    abs(row["timestamp_delta_ms_p2_minus_p1"]), 93
                )

        self.assertEqual(
            summary["p1_registered_callback_targets"],
            {"0x823A4758": 375, "0x823B8C60": 688},
        )
        self.assertIn("timestamp/order join", audit["interpretation"])
        self.assertIn("does not prove", audit["interpretation"])

    def test_same_run_native_queue_wait_interrupt_join_replays_from_archived_inputs(self):
        evidence = json.loads(QUEUE_WAIT_R2_EVIDENCE.read_text())
        capture = evidence["source_run"]
        audit = evidence["audit"]
        archive = (
            QUEUE_WAIT_R2_EVIDENCE.parent / evidence["join_input_archive"]["path"]
        )
        archive_bytes = archive.read_bytes()
        self.assertEqual(
            hashlib.sha256(archive_bytes).hexdigest(),
            evidence["join_input_archive"]["sha256"],
        )
        raw = gzip.decompress(archive_bytes)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            evidence["join_input_archive"]["uncompressed_sha256"],
        )
        inputs = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual(len(inputs), evidence["join_input_archive"]["records"])
        p1_callbacks = sorted(
            (row for row in inputs if row["type"] == "guest_callback"),
            key=lambda row: row["entry_ordinal"],
        )
        raw_interrupts = sorted(
            (row for row in inputs if row["type"] == "pm4_interrupt"),
            key=lambda row: row["ordinal"],
        )
        self.assertEqual(len(p1_callbacks), audit["guest_callback_entries"])
        self.assertEqual(len(raw_interrupts), audit["source1_pm4_interrupt_records"])
        self.assertEqual(capture["gdb_exit"], 0)
        self.assertFalse(capture["guest_memory_modified_by_probe"])
        self.assertEqual(capture["ring_trace_malformed_records"], 0)
        self.assertEqual(
            capture["plugin_build_id"],
            "0fb71ebd09a498fc0515de313289b39ccfc22300",
        )
        for row in raw_interrupts:
            self.assertEqual(row["source"], 1)
            self.assertEqual(row["generation"], 1)
            self.assertEqual(row["ring_guest"], 0x09752580)
            self.assertEqual(row["cpu_mask"], 0x04)
            self.assertEqual(row["dispatched_cpu_mask"], 0x04)
            self.assertEqual(
                row["callbacks"],
                [
                    {
                        "cpu": 2,
                        "callback": 0x823B37B8,
                        "data": 0xB7365F00,
                        "status": "invoked",
                    }
                ],
            )
            self.assertLess(row["batch_rptr"], 8192)
            self.assertLess(row["batch_wptr"], 8192)
            self.assertGreater((row["batch_wptr"] - row["batch_rptr"]) % 8192, 0)

        ring_reuse = audit["ring_reuse_observation"]
        interrupt_ids = [row["ordinal"] for row in raw_interrupts]
        locations = Counter(
            (row["source_ib"], row["source_ib_byte_offset"])
            for row in raw_interrupts
        )
        rptr_values = Counter(row["batch_rptr"] for row in raw_interrupts)
        wptr_values = Counter(row["batch_wptr"] for row in raw_interrupts)
        self.assertEqual(interrupt_ids, list(range(1574)))
        self.assertEqual(
            ring_reuse["interrupt_id_range"], [interrupt_ids[0], interrupt_ids[-1]]
        )
        self.assertEqual(len(set(row["packet_ordinal"] for row in raw_interrupts)), 60)
        self.assertEqual(len(locations), ring_reuse["distinct_source_ib_locations"])
        self.assertEqual(
            sum(count > 1 for count in locations.values()),
            ring_reuse["source_ib_locations_with_repeats"],
        )
        self.assertEqual(
            sum(count - 1 for count in locations.values()),
            ring_reuse["extra_source_ib_location_occurrences"],
        )
        self.assertEqual(len(rptr_values), ring_reuse["distinct_batch_rptr_values"])
        self.assertEqual(
            sum(count - 1 for count in rptr_values.values()),
            ring_reuse["extra_batch_rptr_occurrences"],
        )
        self.assertEqual(len(wptr_values), ring_reuse["distinct_batch_wptr_values"])
        self.assertEqual(
            sum(count - 1 for count in wptr_values.values()),
            ring_reuse["extra_batch_wptr_occurrences"],
        )

        p2_interrupts = [
            {
                "id": row["ordinal"],
                "timestamp_ms": row["timestamp_epoch_ms"],
                "generation": row["generation"],
                "rptr": row["batch_rptr"],
                "wptr": row["batch_wptr"],
                "ring": row["ring_guest"],
                "ordinal": row["packet_ordinal"],
                "packet_source": row["source_ib"],
                "packet_offset": row["source_ib_byte_offset"],
                "mask": row["cpu_mask"],
                "dispatched": row["dispatched_cpu_mask"],
                "callbacks": row["callbacks"],
            }
            for row in raw_interrupts
        ]
        joined = AUDIT.join_callbacks(p1_callbacks, p2_interrupts, 120)
        self.assertEqual(joined, audit["rows"])
        self.assertEqual(len(joined), 853)
        self.assertEqual(
            [joined[0]["p2_pm4_interrupt_id"], joined[-1]["p2_pm4_interrupt_id"]],
            audit["interrupt_id_range"],
        )
        self.assertEqual(audit["interrupt_id_range"], [699, 1551])
        self.assertEqual(
            audit["absolute_timestamp_delta_ms_min_median_max"], [0, 21, 79]
        )
        self.assertEqual(
            audit["p1_registered_callback_targets"],
            {"0x823A4758": 320, "0x823B8C60": 533},
        )
        self.assertIn("does not prove", evidence["interpretation"])

    def test_selects_unique_contiguous_window_with_callback_order(self):
        p1 = [p1_callback(1000), p1_callback(1100), p1_callback(1200)]
        p2 = [
            p2_interrupt(7, 0),
            p2_interrupt(8, 200),
            p2_interrupt(9, 500),
            p2_interrupt(10, 1002),
            p2_interrupt(11, 1101),
            p2_interrupt(12, 1210),
            p2_interrupt(13, 4000),
        ]

        rows = AUDIT.join_callbacks(p1, p2, 200)

        self.assertEqual([row["p2_pm4_interrupt_id"] for row in rows], [10, 11, 12])
        self.assertEqual(
            [row["timestamp_delta_ms_p2_minus_p1"] for row in rows], [2, 1, 10]
        )
        self.assertEqual([row["dispatch_cpu"] for row in rows], [2, 2, 2])

    def test_rejects_when_no_contiguous_window_meets_tolerance(self):
        p1 = [p1_callback(1000), p1_callback(1100)]
        p2 = [p2_interrupt(10, 1000), p2_interrupt(12, 1100)]

        with self.assertRaisesRegex(ValueError, "no continuous P2 interrupt window"):
            AUDIT.join_callbacks(p1, p2, 120)

    def test_rejects_multiple_valid_windows_even_when_one_is_nearer(self):
        p1 = [p1_callback(1000)]
        p2 = [p2_interrupt(10, 1000), p2_interrupt(11, 1005)]

        with self.assertRaisesRegex(ValueError, "ambiguously match 2"):
            AUDIT.join_callbacks(p1, p2, 10)


if __name__ == "__main__":
    unittest.main()
