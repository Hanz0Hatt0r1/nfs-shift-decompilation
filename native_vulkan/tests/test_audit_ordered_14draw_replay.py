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


if __name__ == "__main__":
    unittest.main()
