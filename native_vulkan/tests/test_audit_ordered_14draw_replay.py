import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = json.loads(
    (ROOT / "evidence/process2_ordered_14draw_copy38_replay_20261028.json")
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


if __name__ == "__main__":
    unittest.main()
