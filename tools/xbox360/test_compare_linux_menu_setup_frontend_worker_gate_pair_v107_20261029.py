from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from compare_linux_menu_setup_frontend_worker_gate_pair_v107_20261029 import (
    compare_runs,
)


PULSES = [
    {"button": "Start", "observed_down_state2_index": 5,
     "observed_up_state2_index": 17},
    {"button": "A", "observed_down_state2_index": 21,
     "observed_up_state2_index": 33},
    {"button": "Start", "observed_down_state2_index": 37,
     "observed_up_state2_index": 49},
]


def fixture_run(root: Path, backend: str, watch_after: str = "0x5") -> Path:
    run = root / backend
    run.mkdir()
    lines = ["P1_STATE2_UPDATE " + json.dumps({"state": 2, "state2_index": i})
             for i in range(1, 50)]
    call = {
        "function": "sub_822E1910", "call_index": 1,
        "button": "Start", "caller_lr": "0x822fdf88",
        "args_r3_r10": ["0xbb9c6570", "0x701efdb0"],
        "input": {"buttons": "0x10", "host_buttons": "0x10",
                  "previous": "0x0", "start_edge": "0xc0", "a_edge": "0x0"},
        "last_state2_index_seen": 5,
    }
    returned = {
        "function": "sub_822E1910", "call_index": 1,
        "return_r3": "0x1", "live_context_gpr3": "0x1",
        "live_context_matches_saved": True,
        "host_symbol_after_return": "sub_822FDCE0 + 2952 in section .ltext of /run/bin/nfs_shift",
    }
    watch = {
        "context_r3_before": "0x1", "context_r3_after": watch_after,
        "context_guest_lr": "0x822fdf88",
        "host_symbol": "sub_822FDCE0 + 3271 in section .ltext of /run/bin/nfs_shift",
        "guest_memory_modified_by_probe": False,
    }
    lines.extend((
        "P1_WORKER_GATE_CALL " + json.dumps(call),
        "P1_WORKER_GATE_RETURN " + json.dumps(returned),
        "P1_CONTEXT_R3_WRITE_WATCH " + json.dumps(watch),
        "P1_CONTEXT_R3_WATCH_SUMMARY " + json.dumps({"watchpoints": 1}),
    ))
    log = run / "gdb.log"
    log.write_text("\n".join(lines) + "\n")
    pulses = [{**row, "target_down_state2_index": row["observed_down_state2_index"],
               "target_up_state2_index": row["observed_up_state2_index"]}
              for row in PULSES]
    metadata = {
        "backend": backend, "gdb_exit": 0,
        "guest_memory_modified_by_probe": False,
        "controller_pulses": pulses, "events_log": str(log),
        "events_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "duration_seconds": 130, "game_data_root": "/game-data",
        "runner_sha256": "runner", "trace_sha256": "trace",
        "hashes": {"xex": "xex", "host": "host", "runtime": "runtime",
                   "plugin": "xenos" if backend == "xenos" else "native"},
    }
    (run / "run_metadata.json").write_text(json.dumps(metadata))
    return run


class WorkerGatePairV107Tests(unittest.TestCase):
    def test_matching_live_context_and_r3_watch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = compare_runs(fixture_run(root, "xenos"),
                                  fixture_run(root, "shift-native"))
        self.assertTrue(result["result"]["live_context_r3_matches_return_value"])
        self.assertTrue(result["result"]["context_r3_write_outcome_matches"])
        self.assertFalse(result["result"]["backend_specific_cause_established"])

    def test_different_r3_write_is_reported_as_backend_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = compare_runs(fixture_run(root, "xenos"),
                                  fixture_run(root, "shift-native", "0x7"))
        self.assertFalse(result["result"]["context_r3_write_outcome_matches"])
        self.assertTrue(result["result"]["backend_specific_cause_established"])


if __name__ == "__main__":
    unittest.main()
