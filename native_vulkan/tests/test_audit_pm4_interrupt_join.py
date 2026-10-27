#!/usr/bin/env python3
"""Regression coverage for contiguous PM4-to-guest callback alignment."""

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "tools/audit_pm4_interrupt_join.py"
SPEC = importlib.util.spec_from_file_location("audit_pm4_interrupt_join", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


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
