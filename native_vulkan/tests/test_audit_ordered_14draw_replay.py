import bisect
import gzip
import hashlib
import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = json.loads(
    (ROOT / "evidence/process2_ordered_14draw_copy38_replay_20261028.json")
    .read_text(encoding="utf-8")
)
READBACK = json.loads(
    (ROOT / "evidence/process2_ordered_14draw_copy38_frame622_readback_20261028.json")
    .read_text(encoding="utf-8")
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OrderedRetailReplayEvidenceTests(unittest.TestCase):
    def test_p1_and_p2_streams_match_in_draw_and_copy_order(self):
        p1 = EVIDENCE["p1_capture_reference"]["operation_sequence"]
        p2 = EVIDENCE["p2_replay"]["renderer_log"]["operation_sequence"]
        self.assertEqual(p1["draw_packets"], list(range(14)))
        self.assertEqual(p2["draw_packets"], list(range(14)))
        self.assertEqual(p1["copy_packet"], 38)
        self.assertEqual(p2["copy_packet"], 38)
        self.assertEqual(EVIDENCE["p2_replay"]["renderer_log"]["ordered_operation_count"], 15)
        self.assertTrue(EVIDENCE["result"]["ordered_retail_operation_stream_submitted"])

    def test_selected_raw_shader_pair_matches_tracked_retail_fixtures(self):
        pair = EVIDENCE["p2_replay"]["selected_shader_pair"]
        vertex = ROOT / pair["tracked_vs_fixture"]
        pixel = ROOT / pair["tracked_ps_fixture"]
        self.assertEqual(vertex.stat().st_size, pair["raw_vs_bytes"])
        self.assertEqual(pixel.stat().st_size, pair["raw_ps_bytes"])
        self.assertEqual(sha256(vertex), pair["raw_vs_sha256"])
        self.assertEqual(sha256(pixel), pair["raw_ps_sha256"])

    def test_evidence_does_not_claim_pixel_parity_or_clean_trace(self):
        result = EVIDENCE["result"]
        run = EVIDENCE["p2_replay"]["run_metadata"]
        self.assertFalse(result["retail_image_readback_captured"])
        self.assertFalse(result["intermediate_pixel_correctness_established"])
        self.assertFalse(result["retail_pixel_parity_established"])
        self.assertEqual(run["event_capture_status"], "partial_log_recovery")
        self.assertEqual(run["gdb_exit"], 1)
        self.assertIn("binary-to-that-exact-P1-instance", EVIDENCE["limitations"][0])

    def test_frame622_readback_matches_the_captured_copy_conversion(self):
        operations = READBACK["operation_stream"]
        self.assertEqual(operations["draw_packets"], list(range(14)))
        self.assertEqual(operations["copy_packet"], 38)
        self.assertEqual(operations["ordered_operation_count"], 15)
        readback = READBACK["readback"]
        presenter = readback["presenter"]
        source = readback["pre_copy_source"]
        presenter_archive = ROOT / "evidence" / presenter["raw_archive"]
        source_archive = ROOT / "evidence" / source["raw_archive"]
        image = ROOT / "evidence" / presenter["decoded_png"]
        self.assertEqual(sha256(presenter_archive), presenter["raw_archive_sha256"])
        self.assertEqual(sha256(source_archive), source["raw_archive_sha256"])
        self.assertEqual(sha256(image), presenter["decoded_png_sha256"])

        with gzip.open(source_archive, "rb") as stream:
            source_bytes = stream.read()
        with gzip.open(presenter_archive, "rb") as stream:
            presenter_bytes = stream.read()
        self.assertEqual(len(source_bytes), source["bytes"])
        self.assertEqual(len(presenter_bytes), presenter["bytes"])

        exact_pixels = 0
        max_error = 0
        pixel_count = 0
        source_pixels = struct.iter_unpack("<4H", source_bytes)
        presenter_pixels = struct.iter_unpack("<I", presenter_bytes)
        for (red, green, blue, _), (packed,) in zip(source_pixels, presenter_pixels):
            expected = []
            for value in (red, green, blue):
                unorm8 = (value * 255 + 32767) // 65535
                expected.append((unorm8 * 1023 + 127) // 255)
            actual = (packed & 1023, (packed >> 10) & 1023, (packed >> 20) & 1023)
            pixel_error = max(abs(a - b) for a, b in zip(actual, expected))
            exact_pixels += pixel_error == 0
            max_error = max(max_error, pixel_error)
            pixel_count += 1

        check = READBACK["source_to_presenter_check"]
        self.assertEqual(pixel_count, check["pixels"])
        self.assertEqual(exact_pixels, check["exact_pixels"])
        self.assertEqual(max_error, check["max_per_pixel_channel_error_10bit_codes"])
        self.assertTrue(READBACK["result"]["retail_presenter_readback_captured"])
        self.assertFalse(READBACK["result"]["full_edram_transition_correctness_established"])
        self.assertFalse(READBACK["result"]["xenos_pixel_parity_established"])

    def test_frame622_source1_interrupt_trace_preserves_ring_dispatch_evidence(self):
        trace = READBACK["pm4_interrupt_trace"]
        archive = ROOT / "evidence" / trace["archive"]
        archive_bytes = archive.read_bytes()
        self.assertEqual(
            hashlib.sha256(archive_bytes).hexdigest(), trace["archive_sha256"]
        )
        records_bytes = gzip.decompress(archive_bytes)
        self.assertEqual(
            hashlib.sha256(records_bytes).hexdigest(), trace["uncompressed_sha256"]
        )
        records = [json.loads(line) for line in records_bytes.splitlines()]
        self.assertEqual(len(records), trace["records"])
        self.assertEqual(
            [record["ordinal"] for record in records],
            list(
                range(
                    trace["interrupt_ordinal_range"][0],
                    trace["interrupt_ordinal_range"][1] + 1,
                )
            ),
        )

        rptr_wraps = 0
        wptr_wraps = 0
        for index, record in enumerate(records):
            with self.subTest(interrupt_ordinal=record["ordinal"]):
                self.assertEqual(record["source"], trace["source"])
                self.assertEqual(record["ring_guest"], int(trace["ring_guest"], 16))
                self.assertEqual(record["generation"], trace["ring_generation"])
                self.assertEqual(record["cpu_mask"], 0x04)
                self.assertEqual(record["dispatched_cpu_mask"], 0x04)
                self.assertEqual(record["callbacks"], [
                    {
                        "cpu": trace["dispatch_per_interrupt"]["cpu"],
                        "callback": int(
                            trace["dispatch_per_interrupt"]["callback"], 16
                        ),
                        "data": int(trace["dispatch_per_interrupt"]["data"], 16),
                        "status": trace["dispatch_per_interrupt"]["status"],
                    }
                ])
                self.assertLess(record["batch_rptr"], trace["ring_size_dwords"])
                self.assertLess(record["batch_wptr"], trace["ring_size_dwords"])
                self.assertGreater(
                    (record["batch_wptr"] - record["batch_rptr"])
                    % trace["ring_size_dwords"],
                    0,
                )
                if index:
                    rptr_wraps += record["batch_rptr"] < records[index - 1]["batch_rptr"]
                    wptr_wraps += record["batch_wptr"] < records[index - 1]["batch_wptr"]

        self.assertEqual(
            [min(record["packet_ordinal"] for record in records),
             max(record["packet_ordinal"] for record in records)],
            trace["packet_ordinal_range"],
        )
        self.assertEqual(
            [min(record["batch_rptr"] for record in records),
             max(record["batch_rptr"] for record in records)],
            trace["batch_rptr_dword_range"],
        )
        self.assertEqual(
            [min(record["batch_wptr"] for record in records),
             max(record["batch_wptr"] for record in records)],
            trace["batch_wptr_dword_range"],
        )
        self.assertEqual(rptr_wraps, trace["rptr_wraps"])
        self.assertEqual(wptr_wraps, trace["wptr_wraps"])

        callbacks = trace["recovered_guest_source1_callbacks"]
        callback_archive = ROOT / "evidence" / callbacks["archive"]
        callback_archive_bytes = callback_archive.read_bytes()
        self.assertEqual(
            hashlib.sha256(callback_archive_bytes).hexdigest(),
            callbacks["archive_sha256"],
        )
        callback_bytes = gzip.decompress(callback_archive_bytes)
        self.assertEqual(
            hashlib.sha256(callback_bytes).hexdigest(),
            callbacks["uncompressed_sha256"],
        )
        callback_records = [json.loads(line) for line in callback_bytes.splitlines()]
        self.assertEqual(len(callback_records), callbacks["records"])
        self.assertEqual(
            [record["entry_ordinal"] for record in callback_records],
            list(
                range(
                    callbacks["entry_ordinal_range"][0],
                    callbacks["entry_ordinal_range"][1] + 1,
                )
            ),
        )
        self.assertEqual(
            {
                f"0x{function:08X}": sum(
                    record["callback_function"] == function
                    for record in callback_records
                )
                for function in (0x823A4758, 0x823B8C60)
            },
            callbacks["callback_function_counts"],
        )
        self.assertTrue(
            all(record["source"] == callbacks["source"] for record in callback_records)
        )
        self.assertTrue(
            all(
                record["callback_mask"] == 0x04
                and record["thread_name"] == callbacks["thread"]
                for record in callback_records
            )
        )

        candidates = callbacks["pm4_nearest_timestamp_candidates"]
        candidate_archive = ROOT / "evidence" / candidates["archive"]
        candidate_archive_bytes = candidate_archive.read_bytes()
        self.assertEqual(
            hashlib.sha256(candidate_archive_bytes).hexdigest(),
            candidates["archive_sha256"],
        )
        candidate_bytes = gzip.decompress(candidate_archive_bytes)
        self.assertEqual(
            hashlib.sha256(candidate_bytes).hexdigest(),
            candidates["uncompressed_sha256"],
        )
        candidate_records = [json.loads(line) for line in candidate_bytes.splitlines()]
        self.assertEqual(len(candidate_records), candidates["records"])
        interrupt_timestamps = [record["timestamp_epoch_ms"] for record in records]
        candidate_ordinals = []
        signed_deltas = []
        ties = 0
        for callback, candidate in zip(callback_records, candidate_records):
            timestamp = callback["wall_clock_epoch_ms"]
            insertion = bisect.bisect_left(interrupt_timestamps, timestamp)
            nearest = [
                index
                for index in (insertion - 1, insertion)
                if 0 <= index < len(records)
            ]
            nearest_index = min(
                nearest, key=lambda index: abs(interrupt_timestamps[index] - timestamp)
            )
            interrupt = records[nearest_index]
            delta = interrupt["timestamp_epoch_ms"] - timestamp
            tie = len(nearest) == 2 and abs(
                interrupt_timestamps[nearest[0]] - timestamp
            ) == abs(interrupt_timestamps[nearest[1]] - timestamp)
            self.assertEqual(candidate["guest_entry_ordinal"], callback["entry_ordinal"])
            self.assertEqual(
                candidate["pm4_interrupt_ordinal"], interrupt["ordinal"]
            )
            self.assertEqual(candidate["packet_ordinal"], interrupt["packet_ordinal"])
            self.assertEqual(candidate["pm4_minus_guest_callback_ms"], delta)
            self.assertEqual(candidate["candidate_tie"], tie)
            candidate_ordinals.append(interrupt["ordinal"])
            signed_deltas.append(delta)
            ties += tie

        multiplicities = {}
        for ordinal in candidate_ordinals:
            multiplicities[ordinal] = multiplicities.get(ordinal, 0) + 1
        multiplicity_counts = {
            count: sum(value == count for value in multiplicities.values())
            for count in set(multiplicities.values())
        }
        absolute_deltas = sorted(abs(delta) for delta in signed_deltas)
        first_candidate, last_candidate = candidates[
            "candidate_interrupt_ordinal_range"
        ]
        self.assertTrue(
            all(left <= right for left, right in zip(candidate_ordinals, candidate_ordinals[1:]))
        )
        self.assertEqual(
            [min(candidate_ordinals), max(candidate_ordinals)],
            candidates["candidate_interrupt_ordinal_range"],
        )
        self.assertEqual(len(multiplicities), candidates["unique_candidate_interrupts"])
        self.assertEqual(multiplicity_counts, {1: 469, 2: 134})
        self.assertEqual(
            last_candidate - first_candidate + 1 - len(multiplicities),
            candidates["interrupts_without_candidate_in_range"],
        )
        self.assertEqual(ties, candidates["candidate_ties"])
        self.assertEqual(
            [min(signed_deltas), max(signed_deltas)], candidates["signed_delta_ms_range"]
        )
        self.assertEqual(absolute_deltas[len(absolute_deltas) // 2], 8)
        self.assertEqual(absolute_deltas[-1], candidates["absolute_delta_ms_max"])
        self.assertEqual(sum(delta <= 50 for delta in absolute_deltas), 735)
        self.assertIn("do not establish semantic", candidates["interpretation"])
        self.assertFalse(callbacks["joined_one_to_one_with_pm4_interrupts"])
        self.assertEqual(trace["trace_capture_status"], "partial_log_recovery")


if __name__ == "__main__":
    unittest.main()
