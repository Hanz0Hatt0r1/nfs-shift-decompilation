#!/usr/bin/env python3
"""Regression checks for the EVENT_WRITE_SHD provenance audit."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "tools/audit_event_write_shd_trace.py"
SPEC = importlib.util.spec_from_file_location("audit_event_write_shd_trace", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def trace_line(event, before, after, packet_value, source_match="true"):
    return (
        "[2026-10-28 15:01:37.830] [info] [core] [t373621] "
        "shift-native: ring trace EVENT_WRITE_SHD "
        f"event={event} monotonic_ns=721 batch=3 generation=1 "
        "batch_rptr=28 batch_wptr=31 ring_guest=09752580 packet=104 "
        "source_ib=095D0120 source_offset=1304 depth=1 "
        "raw_words=[c0025800,00000003,17af4002," 
        f"{packet_value:08x}] expanded_words=[c0025800,00000003,"
        f"17af4002,{packet_value:08x}] source_bytes_match={source_match} "
        "initiator=00000003 encoded_address=17AF4002 "
        "guest_physical=17AF4000 destination_host=0x217af4000 endian=2 "
        f"value_mode=literal packet_value={packet_value:08X} swap_counter=0 "
        f"decoded_value={packet_value:08X} raw_store={packet_value:08X} "
        f"guest_value={before:08X}->{after:08X}"
    )


class EventWriteAuditTests(unittest.TestCase):
    def test_parses_provenance_and_head_regression(self):
        row = AUDIT.parse_line(trace_line(2, 3381, 3375, 3375))

        self.assertEqual(row["guest_physical"], 0x17AF4000)
        self.assertEqual(row["source_ib"], 0x095D0120)
        self.assertEqual(row["raw_words"][3], 3375)
        self.assertTrue(row["source_bytes_match"])

    def test_rejects_raw_value_that_disagrees_with_decoded_fields(self):
        line = trace_line(2, 3381, 3375, 3375).replace(
            "raw_words=[c0025800,00000003,17af4002,00000d2f]",
            "raw_words=[c0025800,00000003,17af4002,00000d2e]",
        )

        with self.assertRaisesRegex(ValueError, "value disagrees with raw packet"):
            AUDIT.parse_line(line)

    def test_reports_mutated_source_bytes_without_calling_it_a_renderer_fix(self):
        rows = [
            AUDIT.parse_line(trace_line(0, 3379, 3381, 3381)),
            AUDIT.parse_line(trace_line(1, 3381, 3375, 3375, "false")),
        ]
        self.assertEqual(
            sum(not row["source_bytes_match"] for row in rows), 1
        )
        self.assertEqual(
            sum(row["guest_value_after"] < row["guest_value_before"] for row in rows),
            1,
        )

    def test_audits_target_head_order_and_source_mismatch(self):
        lines = [
            trace_line(0, 3379, 3381, 3381),
            trace_line(1, 3381, 3375, 3375, "false"),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "ring.log"
            path.write_text("\n".join(lines) + "\n")
            result = AUDIT.audit([path], 0x17AF4000)

        self.assertEqual(result["summary"]["target_write_count"], 2)
        self.assertEqual(result["summary"]["target_regression_count"], 1)
        self.assertEqual(
            result["summary"]["expanded_to_execution_byte_mismatches"], 1
        )
        self.assertEqual(result["summary"]["missing_event_sequence_ids"], [])


if __name__ == "__main__":
    unittest.main()
