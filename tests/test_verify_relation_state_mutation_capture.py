import json

import tools.verify_relation_state_mutation_capture as tool


def _write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path, values):
    path.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def _mutation_event():
    vehicle = 0x10000000
    return {
        "format": "SHIFT.ConstraintRelationStateMutationCaptureRuntime/1",
        "version": 1,
        "status": "captured",
        "ready": True,
        "capture_errors": [],
        "body_pointer_capture_skipped": False,
        "source_function": "FUN_00757d2c",
        "source_address": 0x00757D2C,
        "vehicle_pointer": vehicle,
        "component_offset": 0,
        "component_slot": 0,
        "component_slot_name": "FL",
        "component_block_pointer": vehicle + 0x400,
        "wheel_body_pointer": 0x20000000,
        "spindle_body_pointer": 0,
        "rear_axle_body_pointer": 0x30000000,
        "spindle_body_present": False,
        "source_branch": "wheel-rear-axle-pair",
        "caller_return_address": 0x0076EE00,
        "call_index": 1,
        "runtime_event_sequence": 3,
        "frame_index": 1,
        "frame_entry_runtime_event_sequence": 1,
        "frame_physics_system": 0x5000,
        "registers": {
            "eax": 0,
            "ecx": vehicle,
            "esp": 0x12000000,
            "eip": 0x00757D2C,
        },
    }


def _prepare_ready_capture(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    _write_jsonl(
        capture / "relation_state_mutation_events.jsonl",
        [_mutation_event()],
    )
    _write_json(
        capture / "frame_entry_000001.json",
        {
            "capture_kind": "frame_entry_backend",
            "runtime_event_sequence": 1,
            "frame_index": 1,
            "physics_system": 0x5000,
        },
    )
    _write_jsonl(
        capture / "scalar_reset_events.jsonl",
        [{
            "source_function": "FUN_007b2210",
            "runtime_event_sequence": 2,
            "frame_index": 1,
            "physics_system": 0x5000,
        }],
    )
    _write_json(
        capture / "pre_solve_000001.json",
        {
            "capture_kind": "pre_solve_builtin_solver",
            "runtime_event_sequence": 4,
            "frame_index": 1,
            "physics_system": 0x5000,
        },
    )
    _write_json(
        capture / "post_solve_000001.json",
        {
            "capture_kind": "post_solve",
            "runtime_event_sequence": 5,
            "frame_index": 1,
            "physics_system": 0x5000,
        },
    )
    return capture


def test_cli_builds_ready_mutation_timeline_manifest(tmp_path, capsys):
    capture = _prepare_ready_capture(tmp_path)
    output = tmp_path / "mutation_evidence.json"

    code = tool.main([
        str(capture),
        "-o",
        str(output),
    ])

    assert code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ready"] is True
    assert report["event_count"] == 1
    assert report["correlated_event_count"] == 1
    assert report["placements"][0]["timing_class"] == "pre-solve"
    assert report["inputs"]["scalar_reset_event_count"] == 1
    assert '"ready": true' in capsys.readouterr().out


def test_cli_blocks_missing_mutation_stream(tmp_path, capsys):
    capture = tmp_path / "capture"
    capture.mkdir()

    code = tool.main([str(capture)])

    assert code == 2
    output = capsys.readouterr().out
    assert "missing-mutation-events" in output


def test_cli_blocks_malformed_anchor_json(tmp_path, capsys):
    capture = _prepare_ready_capture(tmp_path)
    (capture / "post_solve_000001.json").write_text(
        "{not-json}\n",
        encoding="utf-8",
    )

    code = tool.main([str(capture)])

    assert code == 2
    assert "capture-read-failed" in capsys.readouterr().out
