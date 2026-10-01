import json
from pathlib import Path

import relation_state_mutation_timeline_correlation_runtime as runtime


def _mutation(
    *,
    sequence: int,
    frame_index,
    frame_sequence,
    kind: str,
    slot: int = 0,
    return_address: int = 0x0076EE96,
):
    source_function = (
        "FUN_0076ed60"
        if kind == "vehicle-setup-slot"
        else "FUN_0079a050"
    )
    return {
        "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
        "ready": True,
        "callsite_ready": True,
        "runtime_event_sequence": sequence,
        "frame_index": frame_index,
        "frame_entry_runtime_event_sequence": frame_sequence,
        "component_slot": slot,
        "component_slot_name": ("FL", "FR", "RL", "RR")[slot],
        "source_branch": "wheel-rear-axle-pair",
        "caller_return_address": return_address,
        "caller_classification": {
            "format": "SHIFT.ConstraintRelationStateMutationCallsite/1",
            "ready": True,
            "known_callsite": True,
            "kind": kind,
            "source_function": source_function,
        },
    }


def _anchor(
    kind: str,
    sequence: int,
    *,
    frame_index=None,
    source=None,
):
    return {
        "kind": kind,
        "runtime_event_sequence": sequence,
        "frame_index": frame_index,
        "source": source or f"{kind}-{sequence}",
    }


def test_phase637_correlates_setup_mutation_before_first_frame_entry():
    report = runtime.correlate_relation_state_mutation_events(
        [
            _mutation(
                sequence=1,
                frame_index=None,
                frame_sequence=None,
                kind="vehicle-setup-slot",
            )
        ],
        [
            _anchor(
                "frame-entry",
                2,
                frame_index=1,
                source="frame_entry_000001.json",
            )
        ],
    )

    assert report["ready"] is True
    assert report["summary"] == {
        "vehicle_setup_mutation_count": 1,
        "runtime_threshold_mutation_count": 0,
        "unclassified_mutation_count": 0,
        "correlated_ready_count": 1,
    }
    event = report["events"][0]
    assert event["timeline_position"] == "before-first-frame-entry"
    assert event["previous_anchor"] is None
    assert event["next_anchor"]["kind"] == "frame-entry"
    assert event["anchor_window"] == "capture-start->frame-entry"


def test_phase637_correlates_runtime_mutation_between_captured_anchors():
    report = runtime.correlate_relation_state_mutation_events(
        [
            _mutation(
                sequence=11,
                frame_index=3,
                frame_sequence=10,
                kind="runtime-threshold-slot",
                slot=2,
                return_address=0x0079A5C1,
            )
        ],
        [
            _anchor(
                "frame-entry",
                10,
                frame_index=3,
                source="frame_entry_000003.json",
            ),
            _anchor(
                "scalar-reset",
                12,
                frame_index=3,
                source="scalar_reset_events.jsonl:1",
            ),
            _anchor(
                "builtin-solver-entry",
                13,
                frame_index=3,
                source="pre_solve_000003.json",
            ),
            _anchor(
                "post-solve",
                14,
                frame_index=3,
                source="post_solve_000003.json",
            ),
        ],
    )

    assert report["ready"] is True
    event = report["events"][0]
    assert event["frame_anchor_consistent"] is True
    assert event["timeline_position"] == "after-frame-entry"
    assert event["previous_anchor"]["kind"] == "frame-entry"
    assert event["next_anchor"]["kind"] == "scalar-reset"
    assert event["anchor_window"] == "frame-entry->scalar-reset"
    assert report["summary"]["runtime_threshold_mutation_count"] == 1


def test_phase637_rejects_frame_entry_sequence_mismatch():
    report = runtime.correlate_relation_state_mutation_events(
        [
            _mutation(
                sequence=11,
                frame_index=3,
                frame_sequence=9,
                kind="runtime-threshold-slot",
                return_address=0x0079A5C1,
            )
        ],
        [
            _anchor(
                "frame-entry",
                10,
                frame_index=3,
                source="frame_entry_000003.json",
            )
        ],
    )

    assert report["ready"] is False
    assert report["events"][0]["ready"] is False
    assert "mutation-frame-entry-sequence-mismatch" in report["events"][0]["errors"]


def test_phase637_rejects_unclassified_mutation_callsite():
    mutation = _mutation(
        sequence=11,
        frame_index=3,
        frame_sequence=10,
        kind="runtime-threshold-slot",
        return_address=0x00123456,
    )
    mutation["callsite_ready"] = False
    mutation["caller_classification"] = {
        "ready": False,
        "known_callsite": False,
        "kind": "unclassified",
        "source_function": None,
    }

    report = runtime.correlate_relation_state_mutation_events(
        [mutation],
        [
            _anchor(
                "frame-entry",
                10,
                frame_index=3,
                source="frame_entry_000003.json",
            )
        ],
    )

    assert report["ready"] is False
    assert "mutation-callsite-not-ready" in report["events"][0]["errors"]
    assert report["summary"]["unclassified_mutation_count"] == 1


def test_phase637_rejects_duplicate_runtime_event_sequence():
    report = runtime.correlate_relation_state_mutation_events(
        [
            _mutation(
                sequence=10,
                frame_index=3,
                frame_sequence=10,
                kind="runtime-threshold-slot",
                return_address=0x0079A5C1,
            )
        ],
        [
            _anchor(
                "frame-entry",
                10,
                frame_index=3,
                source="frame_entry_000003.json",
            )
        ],
    )

    assert report["ready"] is False
    assert any(
        error.startswith("duplicate-runtime-event-sequence:10")
        for error in report["events"][0]["errors"]
    )
    assert "mutation-not-after-frame-entry" in report["events"][0]["errors"]


def test_phase637_rejects_mutation_without_frame_anchor_after_frames_started():
    report = runtime.correlate_relation_state_mutation_events(
        [
            _mutation(
                sequence=12,
                frame_index=None,
                frame_sequence=None,
                kind="vehicle-setup-slot",
            )
        ],
        [
            _anchor(
                "frame-entry",
                10,
                frame_index=1,
                source="frame_entry_000001.json",
            )
        ],
    )

    assert report["ready"] is False
    assert (
        "mutation-without-frame-anchor-after-frame-start"
        in report["events"][0]["errors"]
    )


def test_phase637_directory_loader_reads_phase635_capture_files(tmp_path: Path):
    mutation = _mutation(
        sequence=1,
        frame_index=None,
        frame_sequence=None,
        kind="vehicle-setup-slot",
    )
    (tmp_path / "relation_state_mutation_events.jsonl").write_text(
        json.dumps(mutation) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 2,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pre_solve_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 3,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "post_solve_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 4,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )

    report = runtime.analyze_relation_state_mutation_capture_directory(
        tmp_path
    )

    assert report["ready"] is True
    assert report["mutation_event_count"] == 1
    assert report["timeline_anchor_count"] == 3
    assert report["frame_entry_count"] == 1
    assert report["capture_directory"] == str(tmp_path)


def test_phase637_directory_loader_reads_provider_sequence_from_metadata(
    tmp_path: Path,
):
    mutation = _mutation(
        sequence=2,
        frame_index=1,
        frame_sequence=1,
        kind="runtime-threshold-slot",
        return_address=0x0079A5C1,
    )
    (tmp_path / "relation_state_mutation_events.jsonl").write_text(
        json.dumps(mutation) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 1,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "provider_pre_0_000001.json").write_text(
        json.dumps(
            {
                "frame_index": 1,
                "metadata": {
                    "runtime_event_sequence": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    report = runtime.analyze_relation_state_mutation_capture_directory(
        tmp_path
    )

    assert report["ready"] is True
    event = report["events"][0]
    assert event["next_anchor"]["kind"] == "provider-solver-entry"
    assert event["anchor_window"] == "frame-entry->provider-solver-entry"


def test_phase637_missing_mutation_stream_fails_closed(tmp_path: Path):
    (tmp_path / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 1,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )

    report = runtime.analyze_relation_state_mutation_capture_directory(
        tmp_path
    )

    assert report["ready"] is False
    assert "missing-relation-state-mutation-events" in report["errors"]
    assert "no-relation-state-mutation-events" in report["errors"]


def _load_phase637_cli_module():
    import importlib.util

    path = Path("tools/analyze_relation_state_mutation_timeline.py")
    spec = importlib.util.spec_from_file_location(
        "phase637_mutation_timeline_cli",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase637_cli_writes_ready_report(tmp_path: Path):
    mutation = _mutation(
        sequence=1,
        frame_index=None,
        frame_sequence=None,
        kind="vehicle-setup-slot",
    )
    (tmp_path / "relation_state_mutation_events.jsonl").write_text(
        json.dumps(mutation) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "frame_entry_000001.json").write_text(
        json.dumps(
            {
                "runtime_event_sequence": 2,
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "correlation.json"
    cli = _load_phase637_cli_module()
    assert cli.main([str(tmp_path), "-o", str(output)]) == 0

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == runtime.FORMAT
    assert report["ready"] is True
    assert report["evidence_boundary"]["native_scheduler_admission"] is False


def test_phase637_cli_returns_two_for_blocked_capture(tmp_path: Path):
    cli = _load_phase637_cli_module()
    assert cli.main([str(tmp_path)]) == 2
