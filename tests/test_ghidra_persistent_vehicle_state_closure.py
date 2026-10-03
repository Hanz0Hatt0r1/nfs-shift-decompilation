import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_persistent_vehicle_state_closure.py"
    )
    spec = importlib.util.spec_from_file_location(
        "build_persistent_vehicle_state_closure", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _edge(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _fixture(tmp_path):
    module = _load_module()

    schedule = {
        "format": module.BODY_SCHEDULE_FORMAT,
        "outer_update": {"function": module.OUTER_UPDATE},
        "physics_pass": {"function": module.PHYSICS_PASS},
        "recovered": {
            "between_pass_bridge": {"address": module.HALF_STEP_ORCHESTRATOR}
        },
        "body_integration": {
            "array_loop": module.BODY_ARRAY_LOOP,
            "persistent_integrator": module.BODY_INTEGRATOR,
            "semantic_contract": module.BODY_INTEGRATION_CONTRACT,
            "schedule_link_proven": True,
        },
    }

    caller_a, caller_b = module.DIRECT_CALLERS
    caller_frontier = {
        "format": module.CALLER_FRONTIER_FORMAT,
        "outer_update_anchor": module.OUTER_UPDATE,
        "direct_callers": [
            {
                "address": caller_a,
                "direct_incoming_count": 3,
                "direct_incoming_calls": [
                    _edge(module.UPSTREAM_BATCH, "0x00713112", caller_a),
                    _edge(module.UPSTREAM_BATCH, "0x00713135", caller_a),
                    _edge(module.UPSTREAM_BATCH, "0x007131b5", caller_a),
                ],
                "ordered_direct_calls": [
                    _edge(caller_a, "0x00794a6e", module.OUTER_UPDATE),
                    _edge(caller_a, "0x00794a80", "0x0078ef00"),
                ],
            },
            {
                "address": caller_b,
                "direct_incoming_count": 0,
                "direct_incoming_calls": [],
                "ordered_direct_calls": [
                    _edge(caller_b, "0x0079b310", module.OUTER_UPDATE),
                    _edge(caller_b, "0x0079b320", "0x0078ef00"),
                ],
            },
        ],
    }

    outer_callsite = {
        "format": module.OUTER_CALLSITE_FORMAT,
        "outer_update": {
            "function": module.OUTER_UPDATE,
            "receiver_at_callsites": module.OUTER_RECEIVER,
            "channel_a_parameter": "param_1",
            "channel_a_receiver_offset": "0x98",
            "channel_b_parameter": "param_2",
            "channel_b_receiver_offset": "0xa0",
            "mode_flag_parameter": "param_3",
            "physics_pass_target": module.PHYSICS_PASS,
            "physics_pass_count": 2,
        },
        "direct_callsites": [
            {
                "caller": caller_a,
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_written_from_function_arguments_before_call": True,
                "gate": ["param_5 != 0", "caller +0x234 == 0"],
                "outer_mode_argument": 0,
            },
            {
                "caller": caller_b,
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_read_from_caller_object": True,
                "gate": ["caller +0x34 != 0", "switch(caller +0x234) case 0"],
                "outer_mode_argument": 1,
                "direct_incoming_call_count": 0,
            },
        ],
        "upstream_batch_path": {
            "function": module.UPSTREAM_BATCH,
            "record_pointer_array_offset": "0x140",
            "record_count_offset": "0x144",
            "record_stride": "0x1fa0",
            "child_object_pointer_adjustment": "0x340",
            "accumulator_offset": "0x348",
            "channel_a_seed_offset": "0x160",
            "first_caller_source_call_count": 3,
        },
        "upstream_owner_path": {
            "function": module.UPSTREAM_OWNER,
            "direct_call": _edge(
                module.UPSTREAM_OWNER,
                "0x00715434",
                module.UPSTREAM_BATCH,
            ),
        },
    }

    schedule_path = tmp_path / "schedule.json"
    caller_path = tmp_path / "callers.json"
    callsite_path = tmp_path / "callsite.json"
    _write(schedule_path, schedule)
    _write(caller_path, caller_frontier)
    _write(callsite_path, outer_callsite)
    return module, schedule_path, caller_path, callsite_path


def test_builds_closed_persistent_motion_graph_and_open_upper_frontier(tmp_path):
    module, schedule, callers, callsite = _fixture(tmp_path)
    report = module.build_persistent_vehicle_state_closure(
        schedule, callers, callsite
    )

    assert report["format"] == "SHIFT.PersistentVehicleStateClosure/1"
    assert report["closure"]["persistent_body_motion_path"] == "proven"
    assert report["closure"]["outer_update_call_abi"] == "verified"
    assert report["closure"]["input_control_ownership"] == "unknown"
    assert report["closure"]["alternate_caller_owner"] == "unknown"
    assert report["closure"]["rendered_frame_cadence"] == "unknown"
    assert report["closure"]["body_integrator_native_handoff_ready"] is True
    assert report["closure"]["full_input_to_next_frame_handoff_ready"] is False

    assert report["targeted_export_addresses"] == [
        "0x0079b2d0",
        "0x00715380",
        "0x00713050",
        "0x00794a30",
    ]
    assert {row["evidence_state"] for row in report["graph"]} <= module.EVIDENCE_STATES
    assert all(row["evidence_state"] in module.EVIDENCE_STATES for row in report["candidates"])

    by_address = {row["address"]: row for row in report["candidates"]}
    assert by_address["0x00794a30"]["write_offsets"] == ["0x1aa8", "0x1ab0"]
    assert by_address["0x0079b2d0"]["read_offsets"] == [
        "0x34",
        "0x234",
        "0x1aa8",
        "0x1ab0",
    ]
    assert by_address["0x0079b2d0"]["evidence_state"] == "ambiguous"
    assert by_address["0x00713050"]["read_offsets"] == [
        "0x140",
        "0x144",
        "0x160",
        "0x348",
    ]
    assert report["scope"]["offset_pattern_is_object_identity"] is False
    assert report["scope"]["rendered_frame_schedule_inferred"] is False


def test_fails_closed_when_body_schedule_is_not_linked(tmp_path):
    module, schedule, callers, callsite = _fixture(tmp_path)
    payload = json.loads(schedule.read_text(encoding="utf-8"))
    payload["body_integration"]["schedule_link_proven"] = False
    _write(schedule, payload)

    with pytest.raises(ValueError, match="schedule link is not proven"):
        module.build_persistent_vehicle_state_closure(schedule, callers, callsite)


def test_fails_closed_when_caller_sets_disagree(tmp_path):
    module, schedule, callers, callsite = _fixture(tmp_path)
    payload = json.loads(callsite.read_text(encoding="utf-8"))
    payload["direct_callsites"] = payload["direct_callsites"][:1]
    _write(callsite, payload)

    with pytest.raises(ValueError, match="disagree"):
        module.build_persistent_vehicle_state_closure(schedule, callers, callsite)


def test_fails_closed_if_ownerless_caller_acquires_direct_owner(tmp_path):
    module, schedule, callers, callsite = _fixture(tmp_path)
    payload = json.loads(callers.read_text(encoding="utf-8"))
    payload["direct_callers"][1]["direct_incoming_count"] = 1
    payload["direct_callers"][1]["direct_incoming_calls"] = [
        _edge("0x00800000", "0x00800010", module.DIRECT_CALLERS[1])
    ]
    _write(callers, payload)

    with pytest.raises(ValueError, match="ownership frontier must be re-audited"):
        module.build_persistent_vehicle_state_closure(schedule, callers, callsite)


def test_fails_closed_on_format_drift(tmp_path):
    module, schedule, callers, callsite = _fixture(tmp_path)
    payload = json.loads(schedule.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.GhidraBodyUpdateScheduleFrontier/999"
    _write(schedule, payload)

    with pytest.raises(ValueError, match=module.BODY_SCHEDULE_FORMAT):
        module.build_persistent_vehicle_state_closure(schedule, callers, callsite)
