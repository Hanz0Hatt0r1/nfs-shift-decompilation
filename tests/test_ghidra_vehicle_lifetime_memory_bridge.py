import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_vehicle_lifetime_memory_bridge.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_lifetime_memory_bridge", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture(tmp_path, *, helper_arguments="56, 4, 0", contract_status="source-joined-semantic-roles", release_transport="unknown"):
    module = _load_module()
    descriptor = 2
    factory = "0x00100000"
    initializer = "0x00102000"
    wrapper = "0x00103000"
    teardown = "0x00104000"
    create_helper = "0x00886900"
    release_helper = "0x00886930"

    frontier = _write(
        tmp_path / "frontier.json",
        {
            "format": module.FRONTIER_FORMAT,
            "candidates": [
                {
                    "descriptor": descriptor,
                    "verified_vehicle_lifetime_pair_frontier": True,
                    "frontier_evidence_state": "verified",
                    "vehicle_pointer_function": "0x00715700",
                    "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                    "stored_table_address": "0x00402200",
                    "lifetime_pair_class_name": "VehicleCandidate",
                    "factory_functions": [factory],
                    "initializer_candidates": [initializer],
                    "deleting_wrapper_functions": [wrapper],
                    "teardown_transition_functions": [teardown],
                }
            ],
        },
    )

    callsite = _write(
        tmp_path / "callsite.json",
        {
            "format": module.CALLSITE_FORMAT,
            "create_transfers": [
                {
                    "descriptor": descriptor,
                    "class_name": "VehicleCandidate",
                    "factory_function": factory,
                    "preinitializer_helper": create_helper,
                    "initializer_candidate": initializer,
                    "machine_receiver_value_path_state": "verified",
                    "create_value_transfer_state": "inferred",
                    "verified_machine_register_path": True,
                }
            ],
            "delete_transfers": [
                {
                    "descriptor": descriptor,
                    "class_name": "VehicleCandidate",
                    "deleting_wrapper_function": wrapper,
                    "teardown_transition_function": teardown,
                    "release_helper": release_helper,
                    "release_argument_value_transfer_state": release_transport,
                    "release_argument_value_transfer_proven": release_transport in {"verified", "proven"},
                }
            ],
        },
    )

    create = _write(
        tmp_path / "create.json",
        {
            "format": module.CREATE_FORMAT,
            "links": [
                {
                    "descriptor": descriptor,
                    "class_name": "VehicleCandidate",
                    "factory_function": "FUN_00100000",
                    "initializer_candidate": "FUN_00102000",
                    "immediate_preinitializer_helper": "FUN_00886900",
                    "helper_arguments": helper_arguments,
                    "helper_result_flows_to_initializer": True,
                    "create_wrapper_shape": True,
                }
            ],
        },
    )

    memory = _write(
        tmp_path / "memory.json",
        {
            "format": module.MEMORY_FORMAT,
            "runtime_contract_status": contract_status,
            "wrappers": [
                {
                    "address": create_helper,
                    "name": "FUN_00886900",
                    "forwarding_confirmed": True,
                    "parameters": [
                        {
                            "source_argument_index": 0,
                            "entry_storage": "Stack[0x4]:4",
                            "name": "allocation_size",
                            "semantic_role": "allocation-size",
                            "semantic_role_proven": True,
                        },
                        {
                            "source_argument_index": 1,
                            "entry_storage": "Stack[0x8]:4",
                            "name": "arg1",
                            "semantic_role": None,
                            "semantic_role_proven": False,
                        },
                    ],
                },
                {
                    "address": release_helper,
                    "name": "FUN_00886930",
                    "forwarding_confirmed": True,
                    "parameters": [
                        {
                            "source_argument_index": 0,
                            "entry_storage": "ECX:4",
                            "name": "arg0",
                            "semantic_role": None,
                            "semantic_role_proven": False,
                        },
                        {
                            "source_argument_index": 1,
                            "entry_storage": "DL:1",
                            "name": "arg1",
                            "semantic_role": None,
                            "semantic_role_proven": False,
                        },
                        {
                            "source_argument_index": 2,
                            "entry_storage": "Stack[0x4]:4",
                            "name": "released_pointer",
                            "semantic_role": "released-pointer",
                            "semantic_role_proven": True,
                        },
                    ],
                },
            ],
        },
    )
    return module, frontier, callsite, create, memory


def test_joins_allocation_request_and_released_pointer_parameter(tmp_path):
    module, frontier, callsite, create, memory = _fixture(tmp_path)
    report = module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)

    assert report["format"] == "SHIFT.VehicleLifetimeMemoryBridge/1"
    assert report["create_bridge_count"] == 1
    assert report["delete_bridge_count"] == 1

    create_row = report["create_bridges"][0]
    assert create_row["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert create_row["allocation_size_role_state"] == "verified"
    assert create_row["allocation_size_argument_expression"] == "56"
    assert create_row["allocation_size_argument_literal_value"] == 56
    assert create_row["allocation_size_argument_literal_state"] == "verified"
    assert create_row["initializer_backing_allocation_request_state"] == "inferred"
    assert create_row["initializer_backing_allocation_request_value"] == 56
    assert create_row["object_size_proven"] is False
    assert create_row["helper_return_is_allocated_pointer_proven"] is False

    delete_row = report["delete_bridges"][0]
    assert delete_row["released_pointer_parameter_role_state"] == "verified"
    assert delete_row["released_pointer_parameter"]["source_argument_index"] == 2
    assert delete_row["released_pointer_entry_storage"] == "Stack[0x4]:4"
    assert delete_row["released_pointer_entry_storage_state"] == "verified"
    assert delete_row["release_argument_transport_state"] == "unknown"
    assert delete_row["release_argument_value_transfer_proven"] is False

    assert set(report["next_instruction_export_addresses"]) == {
        "0x00103000",
        "0x00886900",
    }
    blocker_ids = {row["id"] for row in report["blockers"]}
    assert "helper-return-allocation-pointer-semantics-open" in blocker_ids
    assert "release-pointer-call-argument-transport-open" in blocker_ids
    assert "same-runtime-object-create-update-delete-continuity-open" in blocker_ids


def test_nonliteral_allocation_argument_stays_unknown(tmp_path):
    module, frontier, callsite, create, memory = _fixture(
        tmp_path, helper_arguments="size + 4, 4, 0"
    )
    report = module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)
    row = report["create_bridges"][0]
    assert row["allocation_size_role_state"] == "verified"
    assert row["allocation_size_argument_expression"] == "size + 4"
    assert row["allocation_size_argument_literal_value"] is None
    assert row["allocation_size_argument_literal_state"] == "unknown"
    assert row["initializer_backing_allocation_request_state"] == "unknown"


def test_argument_split_preserves_nested_commas(tmp_path):
    module, frontier, callsite, create, memory = _fixture(
        tmp_path, helper_arguments="0x38, combine(a, b), \"x,y\""
    )
    report = module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)
    row = report["create_bridges"][0]
    assert row["allocation_size_argument_literal_value"] == 0x38
    assert row["allocation_size_argument_literal_state"] == "verified"


def test_memory_contract_status_gate_prevents_semantic_role_promotion(tmp_path):
    module, frontier, callsite, create, memory = _fixture(
        tmp_path, contract_status="instruction-diagnostic-backed-physical-roles"
    )
    report = module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)
    assert report["create_bridges"][0]["allocation_size_role_state"] == "unknown"
    assert report["delete_bridges"][0]["released_pointer_parameter_role_state"] == "unknown"


def test_verified_upstream_release_transport_is_preserved_not_reinvented(tmp_path):
    module, frontier, callsite, create, memory = _fixture(
        tmp_path, release_transport="verified"
    )
    report = module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)
    row = report["delete_bridges"][0]
    assert row["upstream_release_argument_value_transfer_state"] == "verified"
    assert row["release_argument_transport_state"] == "verified"
    assert row["release_argument_value_transfer_proven"] is True
    assert not any(
        blocker["id"] == "release-pointer-call-argument-transport-open"
        for blocker in report["blockers"]
    )


def test_duplicate_memory_helper_identity_fails_closed(tmp_path):
    module, frontier, callsite, create, memory = _fixture(tmp_path)
    payload = json.loads(memory.read_text(encoding="utf-8"))
    payload["wrappers"].append(dict(payload["wrappers"][0]))
    _write(memory, payload)
    with pytest.raises(ValueError, match="duplicate helper"):
        module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)


def test_duplicate_create_source_row_fails_closed(tmp_path):
    module, frontier, callsite, create, memory = _fixture(tmp_path)
    payload = json.loads(create.read_text(encoding="utf-8"))
    payload["links"].append(dict(payload["links"][0]))
    _write(create, payload)
    with pytest.raises(ValueError, match="exactly one create-wrapper source row"):
        module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)


def test_callsite_frontier_function_drift_fails_closed(tmp_path):
    module, frontier, callsite, create, memory = _fixture(tmp_path)
    payload = json.loads(callsite.read_text(encoding="utf-8"))
    payload["create_transfers"][0]["factory_function"] = "0x00abcdef"
    _write(callsite, payload)
    with pytest.raises(ValueError, match="exactly one verified lifetime frontier"):
        module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)


def test_format_drift_fails_closed(tmp_path):
    module, frontier, callsite, create, memory = _fixture(tmp_path)
    payload = json.loads(callsite.read_text(encoding="utf-8"))
    payload["format"] = "WRONG"
    _write(callsite, payload)
    with pytest.raises(ValueError, match="SHIFT.VehicleLifetimeCallsiteTransfer/1"):
        module.build_vehicle_lifetime_memory_bridge(frontier, callsite, create, memory)
