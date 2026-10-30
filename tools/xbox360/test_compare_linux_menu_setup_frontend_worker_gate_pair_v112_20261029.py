#!/usr/bin/env python3
"""Focused tests for state-aligned v112 Menu Setup backend comparisons."""

from __future__ import annotations

import json
import unittest

from compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029 import (
    _counter,
    _event_scalar_words,
    _return_signature,
    _zero_nonzero,
    compare_runs,
)


def _run(plugin_sha: str) -> dict:
    return {
        "xex_sha256": "xex", "host_sha256": "host", "runtime_sha256": "runtime",
        "runner_sha256": "runner", "trace_sha256": "trace",
        "game_data_root": "/game", "input_pulses": [("Start", 5, 17)],
        "plugin_sha256": plugin_sha,
        "input_edges": [{
            "button": "Start", "state2_index": 5,
            "event_code": "0x30010400", "event_fields": [0x8212E850, 0x30010400],
            "predicate_fields": [0x8212E5B8, 1],
        }],
        "action_consumer_signatures": [{
            "button": "Start", "function": "sub_822EF7B0", "return_signature": "1",
        }],
        "successful_dequeue_signatures": [{
            "return_r3": "0x1", "event_type": 2, "event_scalar_words": [0, 4, 0, 0, 2],
            "r28_plus_0x10": 0,
        }],
        "dequeue_context_r3_writes": [{
            "before": "0x1", "after": "0x5", "guest_lr": "0x822fdf88",
            "guest_memory_modified_by_probe": False, "r28_plus_0x10": 0,
        }],
        "event_handler_call_count": 1,
        "nested_callback_semantics": [(2, (0, 4, 0, 0, 2), "sub_822E8678")],
        "nested_callback_return_signatures": ["zero"],
        "scene_gate_initialization": {"before": 0, "after": 1},
        "gui_event_queue_summary": {"enqueue_calls": 0, "direct_append_calls": 0},
        "gui_event_queue_processing_counts": {"process_parent_calls": 1},
        "successful_dequeue_events": [{}],
        "nested_callback_signatures": [{}],
    }


class PairComparisonTests(unittest.TestCase):
    def test_matching_semantic_traces_ignore_raw_pointer_diagnostics(self) -> None:
        xenos = _run("xenos-plugin")
        native = _run("native-plugin")
        xenos["action_consumer_outcomes_raw"] = [{"receiver": "0xa0000000"}]
        native["action_consumer_outcomes_raw"] = [{"receiver": "0xb0000000"}]
        result = compare_runs_from_captures(xenos, native)
        self.assertTrue(result["result"]["semantic_trace_fields_match"])
        self.assertFalse(result["result"]["backend_specific_cause_established"])

    def test_semantic_difference_is_reported_without_gpu_causality_claim(self) -> None:
        xenos = _run("xenos-plugin")
        native = _run("native-plugin")
        native["successful_dequeue_signatures"][0]["event_type"] = 3
        result = compare_runs_from_captures(xenos, native)
        self.assertIn("successful_dequeue_signatures",
                      result["result"]["semantic_difference_fields"])
        self.assertTrue(result["result"]["difference_requires_repeat_before_attribution"])
        self.assertFalse(result["result"]["backend_specific_cause_established"])

    def test_input_object_field_change_is_reported(self) -> None:
        xenos = _run("xenos-plugin")
        native = _run("native-plugin")
        native["input_edges"][0]["event_fields"][1] = 0x30010C00
        result = compare_runs_from_captures(xenos, native)
        self.assertIn("input_edges", result["result"]["semantic_difference_fields"])
        self.assertFalse(result["result"]["backend_specific_cause_established"])

    def test_pointer_slots_are_not_treated_as_event_scalar_fields(self) -> None:
        first = [0xA0000000, 0, 0xA1000000, 0xA1000010, 4, 0, 0, 0, 0, 0, 0, 0, 0, 2]
        second = [0xB0000000, 0, 0xB1000000, 0xB1000010, 4, 0, 0, 0, 0, 0, 0, 0, 0, 2]
        self.assertEqual(_event_scalar_words(first), _event_scalar_words(second))

    def test_returns_and_counter_have_json_safe_semantics(self) -> None:
        self.assertEqual(_return_signature("sub_822F7EC8", "0xa0000000"),
                         "non-null guest pointer")
        self.assertEqual(_zero_nonzero("0x0"), "zero")
        rendered = json.dumps(_counter([
            {"button": "A", "status": "1"}, {"button": "A", "status": "1"},
        ], ("button", "status")))
        self.assertIn('"count": 2', rendered)


def compare_runs_from_captures(xenos: dict, native: dict) -> dict:
    """Exercise the comparison reducer without fabricating debugger log files."""
    from unittest.mock import patch

    with patch(
        "compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029._capture",
        side_effect=[xenos, native],
    ):
        # compare_runs only consumes the already validated normalized captures here.
        from compare_linux_menu_setup_frontend_worker_gate_pair_v112_20261029 import (
            compare_runs as reducer,
        )

        return reducer(None, None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
