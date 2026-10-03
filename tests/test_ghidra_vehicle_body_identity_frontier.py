import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_body_identity_frontier.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_body_identity_frontier", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _fixture(tmp_path, *, lifetime_rows=None):
    module = _load_module()
    lifetime_rows = lifetime_rows or [
        {
            "descriptor": 2,
            "class_name": "VehicleCandidate",
            "vehicle_pointer_function": "0x00715700",
            "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
            "stored_table_address": "0x00abcdef",
            "same_runtime_object_as_vehicle_update_proven": False,
        }
    ]
    lifetime = {
        "format": module.LIFETIME_FORMAT,
        "create_bridges": lifetime_rows,
        "scope": {"same_runtime_object_as_vehicle_update_proven": False},
    }
    outer = {
        "format": module.OUTER_FORMAT,
        "outer_update": {
            "function": module.OUTER_UPDATE,
            "receiver_at_callsites": module.OUTER_RECEIVER,
            "channel_a_receiver_offset": "0x98",
            "channel_b_receiver_offset": "0xa0",
        },
        "direct_callsites": [
            {
                "caller": module.FIRST_CALLER,
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_written_from_function_arguments_before_call": True,
                "promoted": False,
            },
            {
                "caller": "0x0079b2d0",
                "caller_channel_a_offset": "0x1aa8",
                "caller_channel_b_offset": "0x1ab0",
                "channels_read_from_caller_object": True,
                "promoted": False,
            },
        ],
        "upstream_batch_path": {
            "function": module.UPSTREAM_BATCH,
            "record_pointer_array_offset": "0x140",
            "record_count_offset": "0x144",
            "record_stride": "0x1fa0",
            "child_object_pointer_adjustment": "0x340",
            "first_caller_source_call_count": 3,
        },
        "scope": {"vehicle_class_identity_proven": False},
    }
    persistent = {
        "format": module.PERSISTENT_FORMAT,
        "anchors": {
            "outer_update": module.OUTER_UPDATE,
            "physics_pass": "0x0076d100",
            "half_step_orchestrator": module.HALF_STEP,
            "body_array_loop": module.BODY_ARRAY_LOOP,
            "body_integrator": module.BODY_INTEGRATOR,
            "outer_receiver": module.OUTER_RECEIVER,
        },
        "closure": {"persistent_body_motion_path": "proven"},
        "scope": {"offset_pattern_is_object_identity": False},
    }
    body = {
        "format": module.BODY_FORMAT,
        "functions": {
            "FUN_00765470": {"address": module.HALF_STEP, "promoted_name": False},
            "FUN_007b2270": {
                "address": module.BODY_ARRAY_LOOP,
                "body_count_offset": "0x10",
                "body_array_offset": "0x14",
                "body_stride": "0x170",
                "callee": "FUN_007bab70",
                "promoted_name": False,
            },
            "FUN_007bab70": {
                "address": module.BODY_INTEGRATOR,
                "promoted_name": False,
            },
        },
        "closed_boundaries": {"body_array_stride_and_count": True},
    }
    return (
        module,
        _write(tmp_path / "lifetime.json", lifetime),
        _write(tmp_path / "outer.json", outer),
        _write(tmp_path / "persistent.json", persistent),
        _write(tmp_path / "body.json", body),
    )


def _build(fixture):
    module, lifetime, outer, persistent, body = fixture
    return module, module.build_vehicle_body_identity_frontier(
        lifetime, outer, persistent, body
    )


def test_separates_pointer_domains_and_blocks_vehicle_body_selection(tmp_path):
    module, report = _build(_fixture(tmp_path))

    assert report["format"] == "SHIFT.VehicleBodyIdentityFrontier/1"
    domains = report["pointer_domains"]
    assert domains["lifetime_vehicle_pointers"][0]["vehicle_pointer_function"] == "0x00715700"
    assert domains["update_child_receiver"]["source_rule"] == "*record + 0x340"
    assert domains["outer_physics_receiver"]["source_expression"] == "&DAT_00c13700"
    assert domains["body_array_owner"]["array_pointer_offset"] == "0x14"
    assert domains["body_array_owner"]["body_stride"] == "0x170"

    receiver_transfer = report["transfer_facts"][0]
    assert receiver_transfer["from"] == "update_child_receiver"
    assert receiver_transfer["to"] == "outer_physics_receiver"
    assert receiver_transfer["evidence_state"] == "verified"
    assert receiver_transfer["pointer_forwarded"] is False
    assert receiver_transfer["runtime_pointer_inequality_proven"] is False

    channel_transfer = report["transfer_facts"][1]
    assert channel_transfer["pointer_identity_transfer"] is False
    assert channel_transfer["channel_a"] == {
        "caller_offset": "0x1aa8",
        "outer_receiver_offset": "0x98",
    }
    assert channel_transfer["channel_b"] == {
        "caller_offset": "0x1ab0",
        "outer_receiver_offset": "0xa0",
    }

    assert report["handoff"]["persistent_BODY_pose_available"] is True
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["selected_BODY_index"] is None
    assert report["handoff"]["selected_BODY_pointer"] is None
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["handoff"]["critical_next_join"] == "update_child_receiver -> BODY index/pointer"
    assert report["scope"]["normal_outer_call_forwards_vehicle_receiver_pointer"] is False
    assert report["scope"]["runtime_pointer_inequality_between_update_child_and_outer_receiver_proven"] is False
    assert report["scope"]["update_child_to_BODY_identity_proven"] is False
    assert report["next_instruction_targets"] == [
        "0x00713050",
        "0x00765470",
        "0x00794a30",
        "0x007b2270",
    ]


def test_retains_multiple_lifetime_domains_without_collapsing_identity(tmp_path):
    rows = [
        {
            "descriptor": 2,
            "class_name": "CandidateA",
            "vehicle_pointer_function": "0x00715700",
            "vehicle_pointer_source_node": "memory-source:a",
            "stored_table_address": "0x1000",
            "same_runtime_object_as_vehicle_update_proven": False,
        },
        {
            "descriptor": 7,
            "class_name": "CandidateB",
            "vehicle_pointer_function": "0x00715800",
            "vehicle_pointer_source_node": "memory-source:b",
            "stored_table_address": "0x2000",
            "same_runtime_object_as_vehicle_update_proven": False,
        },
    ]
    _, report = _build(_fixture(tmp_path, lifetime_rows=rows))
    domains = report["pointer_domains"]["lifetime_vehicle_pointers"]
    assert [row["descriptor"] for row in domains] == [2, 7]
    assert all(row["same_runtime_object_as_update_child_state"] == "unknown" for row in domains)
    assert all(row["same_runtime_object_as_BODY_state"] == "unknown" for row in domains)


def test_rejects_lifetime_bridge_preclaiming_update_identity(tmp_path):
    fixture = _fixture(tmp_path)
    module, lifetime, outer, persistent, body = fixture
    payload = json.loads(lifetime.read_text(encoding="utf-8"))
    payload["create_bridges"][0]["same_runtime_object_as_vehicle_update_proven"] = True
    lifetime.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="preclaims vehicle-update identity"):
        module.build_vehicle_body_identity_frontier(lifetime, outer, persistent, body)


def test_rejects_outer_receiver_drift(tmp_path):
    fixture = _fixture(tmp_path)
    module, lifetime, outer, persistent, body = fixture
    payload = json.loads(outer.read_text(encoding="utf-8"))
    payload["outer_update"]["receiver_at_callsites"] = "DAT_00dead00"
    outer.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="outer-update receiver drift"):
        module.build_vehicle_body_identity_frontier(lifetime, outer, persistent, body)


def test_rejects_child_adjustment_drift(tmp_path):
    fixture = _fixture(tmp_path)
    module, lifetime, outer, persistent, body = fixture
    payload = json.loads(outer.read_text(encoding="utf-8"))
    payload["upstream_batch_path"]["child_object_pointer_adjustment"] = "0x344"
    outer.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="child pointer adjustment drift"):
        module.build_vehicle_body_identity_frontier(lifetime, outer, persistent, body)


def test_rejects_body_array_topology_drift(tmp_path):
    fixture = _fixture(tmp_path)
    module, lifetime, outer, persistent, body = fixture
    payload = json.loads(body.read_text(encoding="utf-8"))
    payload["functions"]["FUN_007b2270"]["body_stride"] = "0x174"
    body.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="BODY stride drift"):
        module.build_vehicle_body_identity_frontier(lifetime, outer, persistent, body)


def test_rejects_persistent_closure_that_promotes_offset_identity(tmp_path):
    fixture = _fixture(tmp_path)
    module, lifetime, outer, persistent, body = fixture
    payload = json.loads(persistent.read_text(encoding="utf-8"))
    payload["scope"]["offset_pattern_is_object_identity"] = True
    persistent.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="offsets as object identity"):
        module.build_vehicle_body_identity_frontier(lifetime, outer, persistent, body)
