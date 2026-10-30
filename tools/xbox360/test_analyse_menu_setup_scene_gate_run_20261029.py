#!/usr/bin/env python3
"""Regression tests for the Menu Setup scene-gate run analyser.

The v107/v112/v118 frontier claims live in prose in ``docs/``. These tests pin
the machine-readable facts the prose depends on so a future trace change cannot
silently invalidate them.

Two layers:

1. Synthetic-trace contract tests, always run. They assert the analyser's
   vocabulary: state-2 counting, scene-gate set/clear classification, and the
   rule that an un-instrumented enqueue path is reported as unknown rather than
   as zero.
2. Live-run assertions, run only when the local capture directories exist. They
   reproduce the numbers quoted in
   ``docs/XBOX360_MENU_SETUP_EVENT_DEQUEUE_DOWNSTREAM_REPEAT_V112_20261029.md``
   and ``docs/P1_FRONTEND_FRONTIER_PLAN_20261030.md`` independently of the GDB
   logs being committed (they are not: only their hashes are).

Run: python3 tools/xbox360/test_analyse_menu_setup_scene_gate_run_20261029.py
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from analyse_menu_setup_scene_gate_run_20261029 import _iter_events, analyse_run

V118_NATIVE = Path(
    "/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-native-retry-20261029"
)
V118_XENOS = Path("/home/pes/work/nfs-shift-p1-menu-setup-v118-repeat-xenos-20261029")

# Fleet-wide identities quoted by the frontier docs.
XEX_SHA = "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
HOST_SHA = "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178"
RUNTIME_SHA = "693abc4814fe04a8025e41be989ac14faa31565b2786e1397f87ad9544d601cd"
NATIVE_PLUGIN_SHA = "fd615adad5febc2adcf9a46fa0b74a67c9cf28f013bc74ca8715ac9abad9c490"
XENOS_PLUGIN_SHA = "8b5abe7a0c59a8a41af5aa166df23de46fed191bfc863e183c98d6023c54e4de"


def _write_run(tmp: Path, lines: list[str], metadata: dict | None = None) -> Path:
    log = tmp / "gdb.log"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if metadata is not None:
        (tmp / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return tmp


class EventParsingTests(unittest.TestCase):
    def test_json_payload_is_parsed(self):
        stream = io.StringIO(
            'P1_STATE2_UPDATE {"elapsed_seconds": 1.5, "state": 2}\n'
            "P1_WORKER_GATE_SUMMARY\n"
            "unrelated output line\n"
        )
        events = list(_iter_events([stream]))
        self.assertEqual(events[0][0], "P1_STATE2_UPDATE")
        self.assertEqual(events[0][1]["elapsed_seconds"], 1.5)
        self.assertEqual(events[1], ("P1_WORKER_GATE_SUMMARY", {}))
        self.assertEqual(len(events), 2, "non-P1 lines must be ignored")

    def test_malformed_payload_does_not_raise(self):
        stream = io.StringIO("P1_STATE2_UPDATE {not json\n")
        events = list(_iter_events([stream]))
        self.assertEqual(events, [("P1_STATE2_UPDATE", {})])


class SyntheticContractTests(unittest.TestCase):
    def test_state2_interval_and_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = _write_run(
                Path(tmp),
                [
                    'P1_STATE2_UPDATE {"elapsed_seconds": 10.0}',
                    'P1_STATE2_UPDATE {"elapsed_seconds": 10.5}',
                    'P1_STATE2_UPDATE {"elapsed_seconds": 13.0}',
                    'P1_MAINMENU_SCENE_GATE_METHOD_CALL {"function": "sub_82DD9020", "caller_lr": "0x82fd5468"}',
                    'P1_SCENE_GATE_FIELD_WRITE {"before": 0, "after": 1, "elapsed_seconds": 9.0}',
                ],
                {"backend": "shift-native", "gdb_exit": 0},
            )
            out = analyse_run(run)
        self.assertEqual(out["state2"]["updates"], 3)
        self.assertEqual(out["state2"]["first_elapsed_seconds"], 10.0)
        self.assertEqual(out["state2"]["span_seconds"], 3.0)
        self.assertEqual(out["state2"]["max_gap_seconds"], 2.5)
        self.assertEqual(out["scene_gate"]["set_calls"], 1)
        self.assertEqual(out["scene_gate"]["clear_calls"], 0)
        self.assertEqual(out["scene_gate"]["field_writes"], 1)
        self.assertEqual(out["backend"], "shift-native")

    def test_clear_function_is_classified_as_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = _write_run(
                Path(tmp),
                [
                    'P1_MAINMENU_SCENE_GATE_METHOD_CALL {"function": "sub_82DD8FF8"}',
                    'P1_MAINMENU_SCENE_GATE_METHOD_CALL {"function": "sub_82DD9020"}',
                    'P1_STATE2_UPDATE {"elapsed_seconds": 1.0}',
                    'P1_SCENE_GATE_FIELD_WRITE {"before": 0, "after": 1}',
                ],
            )
            out = analyse_run(run)
        self.assertEqual(out["scene_gate"]["clear_calls"], 1)
        self.assertEqual(out["scene_gate"]["set_calls"], 1)

    def test_uninstrumented_enqueue_path_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = _write_run(
                Path(tmp),
                [
                    'P1_STATE2_UPDATE {"elapsed_seconds": 1.0}',
                    'P1_MAINMENU_SCENE_GATE_METHOD_CALL {"function": "sub_82DD9020"}',
                    'P1_SCENE_GATE_FIELD_WRITE {"before": 0, "after": 1}',
                    'P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS {"call_index": 1}',
                ],
            )
            out = analyse_run(run)
        gui = out["gui_queue"]
        self.assertEqual(gui["process_calls"], 1)
        self.assertEqual(gui["gui_queue_enqueue_calls"], "unknown: family not emitted")
        self.assertIn("not instrumented", gui["enqueue_evidence"])
        self.assertNotEqual(gui["gui_queue_enqueue_calls"], 0)

    def test_missing_required_families_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = _write_run(Path(tmp), ['P1_STATE2_UPDATE {"elapsed_seconds": 1.0}'])
            out = analyse_run(run)
        self.assertIn("P1_MAINMENU_SCENE_GATE_METHOD_CALL", out["missing_required_families"])
        self.assertIn("P1_SCENE_GATE_FIELD_WRITE", out["missing_required_families"])
        self.assertNotIn("P1_STATE2_UPDATE", out["missing_required_families"])

    def test_absent_run_dir_is_empty_not_an_exception(self):
        out = analyse_run(Path("/nonexistent/run-20261030"))
        self.assertEqual(out["state2"]["updates"], 0)
        self.assertIsNone(out["state2"]["first_elapsed_seconds"])
        self.assertEqual(out["scene_gate"]["set_calls"], 0)


@unittest.skipUnless(V118_NATIVE.is_dir(), "v118 native run directory not present")
class LiveNativeRunTests(unittest.TestCase):
    """Reproduce the frontier numbers from the raw run directory."""

    @classmethod
    def setUpClass(cls):
        cls.out = analyse_run(V118_NATIVE)

    def test_backend_and_readonly_invariant(self):
        self.assertEqual(self.out["backend"], "shift-native")
        self.assertEqual(self.out["gdb_exit"], 0)
        self.assertIs(self.out["guest_memory_modified_by_probe"], False)

    def test_artifact_identities_match_the_pins(self):
        hashes = self.out["artifact_hashes"]
        self.assertEqual(hashes["xex"], XEX_SHA)
        self.assertEqual(hashes["host"], HOST_SHA)
        self.assertEqual(hashes["runtime"], RUNTIME_SHA)
        self.assertEqual(hashes["plugin"], NATIVE_PLUGIN_SHA)

    def test_menu_setup_stays_in_state2_for_twenty_updates(self):
        state2 = self.out["state2"]
        self.assertEqual(state2["updates"], 20)
        self.assertAlmostEqual(state2["first_elapsed_seconds"], 77.46, places=2)
        self.assertAlmostEqual(state2["last_elapsed_seconds"], 110.168, places=2)

    def test_scene_gate_is_set_once_and_never_cleared(self):
        gate = self.out["scene_gate"]
        self.assertEqual(gate["set_calls"], 1)
        self.assertEqual(gate["clear_calls"], 0, "sub_82DD8FF8 must not be entered")
        self.assertEqual(gate["field_writes"], 1)
        write = gate["writes"][0]
        self.assertEqual((write["before"], write["after"]), (0, 1))
        self.assertAlmostEqual(write["elapsed_seconds"], 76.303, places=2)
        self.assertIn("sub_82DD9020", write["host_symbol"])

    def test_gui_queue_constructed_and_polled_without_enqueue_observability(self):
        gui = self.out["gui_queue"]
        self.assertEqual(gui["ctor_calls"], 70)
        self.assertEqual(gui["ctor_returns"], 70)
        self.assertEqual(gui["open_calls"], 9)
        self.assertEqual(gui["process_calls"], 16)
        self.assertIn("not instrumented", gui["enqueue_evidence"])

    def test_retail_input_reaches_the_predicate(self):
        self.assertEqual(self.out["input"]["predicate_samples"], 36)
        self.assertEqual(self.out["input"]["predicate_values"], ["1"])

    def test_no_required_family_is_missing(self):
        self.assertEqual(self.out["missing_required_families"], [])


@unittest.skipUnless(V118_XENOS.is_dir(), "v118 xenos run directory not present")
class LiveXenosRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = analyse_run(V118_XENOS)

    def test_backend_is_xenos_with_xenos_plugin(self):
        self.assertEqual(self.out["backend"], "xenos")
        self.assertEqual(self.out["artifact_hashes"]["plugin"], XENOS_PLUGIN_SHA)
        self.assertIs(self.out["guest_memory_modified_by_probe"], False)

    def test_matches_native_on_the_frontier_shape(self):
        native = analyse_run(V118_NATIVE) if V118_NATIVE.is_dir() else None
        self.assertEqual(self.out["state2"]["updates"], 20)
        self.assertEqual(self.out["scene_gate"]["set_calls"], 1)
        self.assertEqual(self.out["scene_gate"]["clear_calls"], 0)
        self.assertEqual(self.out["gui_queue"]["ctor_calls"], 70)
        if native is not None:
            self.assertEqual(
                self.out["state2"]["updates"], native["state2"]["updates"],
                "both backends must reach the same state-2 update count",
            )
            self.assertEqual(
                self.out["scene_gate"]["clear_calls"], native["scene_gate"]["clear_calls"],
                "neither backend may clear the scene gate in the captured window",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
