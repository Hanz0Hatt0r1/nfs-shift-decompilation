import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_lifetime_callsite_transfer.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_lifetime_callsite_transfer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _pcode(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _ins(address, mnemonic, operands, *, flows=None, pcode=None):
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": f"{mnemonic} " + ",".join(operands),
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _call(address, target):
    return _ins(address, "CALL", [target], flows=[target], pcode=[_pcode("CALL")])


def _row(module, address, cc, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions) * 4,
            "calling_convention": cc,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(tmp_path):
    module = _load_module()
    factory = "0x00100000"
    helper = "0x00101000"
    initializer = "0x00102000"
    wrapper = "0x00103000"
    teardown = "0x00104000"
    release = "0x00105000"

    frontier = {
        "format": module.FRONTIER_FORMAT,
        "candidate_count": 1,
        "verified_frontier_count": 1,
        "candidates": [
            {
                "vehicle_pointer_function": initializer,
                "stored_table_address": "0x00402200",
                "descriptor": 2,
                "lifetime_pair_class_name": "Child",
                "frontier_evidence_state": "verified",
                "factory_functions": [factory],
                "initializer_candidates": [initializer],
                "deleting_wrapper_functions": [wrapper],
                "teardown_transition_functions": [teardown],
            }
        ],
    }
    frontier_path = tmp_path / "frontier.json"
    _write_json(frontier_path, frontier)

    create = {
        "format": module.CREATE_FORMAT,
        "links": [
            {
                "class_name": "Child",
                "descriptor": 2,
                "factory_function": "FUN_00100000",
                "initializer_candidate": "FUN_00102000",
                "immediate_preinitializer_helper": "FUN_00101000",
                "helper_result_flows_to_initializer": True,
                "source_create_wrapper_shape": True,
                "ghidra_factory_to_initializer": True,
                "ghidra_factory_to_helper": True,
                "create_wrapper_shape": True,
            }
        ],
    }
    create_path = tmp_path / "create.json"
    _write_json(create_path, create)

    delete = {
        "format": module.DELETE_FORMAT,
        "wrappers": [
            {
                "class_name": "Child",
                "descriptor": 2,
                "wrapper_function": "FUN_00103000",
                "teardown_transition_function": "FUN_00104000",
                "release_helper": "FUN_00105000",
                "teardown_before_release": True,
                "bit0_delete_guard": True,
                "ghidra_teardown_edge": True,
                "ghidra_release_edge": True,
                "deleting_wrapper_shape": True,
            }
        ],
    }
    delete_path = tmp_path / "delete.json"
    _write_json(delete_path, delete)

    factory_instructions = [
        _call("0x00100010", helper),
        _ins("0x00100015", "MOV", ["ESI", "EAX"], pcode=[_pcode("COPY")]),
        _ins("0x00100018", "MOV", ["ECX", "ESI"], pcode=[_pcode("COPY")]),
        _call("0x0010001d", initializer),
    ]
    wrapper_instructions = [
        _ins("0x00103004", "MOV", ["ESI", "ECX"], pcode=[_pcode("COPY")]),
        _ins("0x00103008", "MOV", ["ECX", "ESI"], pcode=[_pcode("COPY")]),
        _call("0x0010300c", teardown),
        _ins("0x00103011", "TEST", ["EAX", "EAX"], pcode=[_pcode("INT_EQUAL")]),
        _call("0x00103015", release),
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            _row(module, factory, "__cdecl", factory_instructions),
            _row(module, initializer, "__thiscall", [_ins("0x00102000", "NOP", [])]),
            _row(module, wrapper, "__thiscall", wrapper_instructions),
            _row(module, teardown, "__thiscall", [_ins("0x00104000", "NOP", [])]),
        ],
    )
    return {
        "module": module,
        "frontier": frontier_path,
        "create": create_path,
        "delete": delete_path,
        "export": export,
        "factory": factory,
        "helper": helper,
        "initializer": initializer,
        "wrapper": wrapper,
        "teardown": teardown,
        "release": release,
    }


def _run(fx):
    return fx["module"].analyze_vehicle_lifetime_callsite_transfer(
        fx["frontier"], fx["create"], fx["delete"], fx["export"]
    )


def test_verifies_machine_create_and_teardown_register_paths(tmp_path):
    fx = _fixture(tmp_path)
    report = _run(fx)

    assert report["format"] == "SHIFT.VehicleLifetimeCallsiteTransfer/1"
    assert report["create_transfer_count"] == 1
    assert report["delete_transfer_count"] == 1

    create = report["create_transfers"][0]
    assert create["machine_receiver_value_path_state"] == "verified"
    assert create["machine_receiver_value_path"]["status"] == "initializer-receiver-reaches-helper-return-register"
    assert create["machine_receiver_value_path"]["helper_return_register"] == "EAX"
    assert create["create_value_transfer_state"] == "inferred"
    assert create["allocation_semantics_proven"] is False
    assert create["constructor_semantics_proven"] is False

    delete = report["delete_transfers"][0]
    assert delete["machine_wrapper_entry_to_teardown_receiver_state"] == "verified"
    assert delete["machine_wrapper_entry_to_teardown_receiver"]["source"] == {
        "kind": "function-entry-register",
        "register": "ECX",
    }
    assert delete["teardown_call_order_state"] == "verified"
    assert delete["teardown_value_transfer_state"] == "inferred"
    assert delete["release_argument_value_transfer_state"] == "unknown"
    assert delete["destructor_semantics_proven"] is False

    assert set(report["next_instruction_export_addresses"]) == {
        fx["helper"],
        fx["release"],
    }


def test_intervening_call_blocks_create_register_path(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    factory = rows[0]
    factory["instructions"].insert(3, _call("0x0010001a", "0x00109900"))
    factory["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    create = report["create_transfers"][0]
    assert create["machine_receiver_value_path_state"] == "ambiguous"
    assert create["machine_receiver_value_path"]["status"] == "barrier-between-helper-and-initializer"
    assert create["create_value_transfer_state"] == "ambiguous"


def test_partial_register_write_blocks_create_path(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[0]["instructions"].insert(
        3,
        _ins("0x0010001a", "MOV", ["CL", "AL"], pcode=[_pcode("SUBPIECE")]),
    )
    rows[0]["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    create = report["create_transfers"][0]
    assert create["machine_receiver_value_path_state"] == "ambiguous"
    assert create["machine_receiver_value_path"]["status"] == "partial-register-write"


def test_non_thiscall_initializer_keeps_receiver_transfer_unknown(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[1]["function"]["calling_convention"] = "__cdecl"
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    create = report["create_transfers"][0]
    assert create["machine_receiver_value_path_state"] == "unknown"
    assert create["machine_receiver_value_path"]["status"] == "initializer-receiver-register-not-statically-fixed"
    assert create["create_value_transfer_state"] == "unknown"


def test_multiple_helper_machine_calls_remain_ambiguous(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[0]["instructions"].insert(0, _call("0x00100008", fx["helper"]))
    rows[0]["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    create = report["create_transfers"][0]
    assert create["machine_receiver_value_path_state"] == "ambiguous"
    assert create["machine_receiver_value_path"]["status"] == "create-callsite-not-unique"
    assert create["machine_receiver_value_path"]["helper_call_count"] == 2


def test_intervening_call_blocks_wrapper_entry_to_teardown(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    wrapper = rows[2]
    wrapper["instructions"].insert(2, _call("0x0010300a", "0x00109900"))
    wrapper["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    delete = report["delete_transfers"][0]
    assert delete["machine_wrapper_entry_to_teardown_receiver_state"] == "ambiguous"
    assert delete["machine_wrapper_entry_to_teardown_receiver"]["status"] == "barrier-before-entry"
    assert delete["teardown_value_transfer_state"] == "ambiguous"


def test_non_thiscall_wrapper_keeps_teardown_transfer_unknown(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[2]["function"]["calling_convention"] = "__cdecl"
    _write_jsonl(fx["export"], rows)

    report = _run(fx)
    delete = report["delete_transfers"][0]
    assert delete["machine_wrapper_entry_to_teardown_receiver_state"] == "unknown"
    assert delete["machine_wrapper_entry_to_teardown_receiver"]["status"] == "wrapper-or-teardown-not-thiscall"


def test_weak_source_edges_do_not_become_verified(tmp_path):
    fx = _fixture(tmp_path)
    create = json.loads(fx["create"].read_text(encoding="utf-8"))
    create["links"][0]["ghidra_factory_to_helper"] = None
    _write_json(fx["create"], create)
    delete = json.loads(fx["delete"].read_text(encoding="utf-8"))
    delete["wrappers"][0]["ghidra_release_edge"] = None
    _write_json(fx["delete"], delete)

    report = _run(fx)
    assert report["create_transfers"][0]["source_create_wrapper_state"] == "inferred"
    assert report["create_transfers"][0]["create_value_transfer_state"] == "inferred"
    assert report["delete_transfers"][0]["source_deleting_wrapper_state"] == "inferred"


def test_missing_required_target_export_fails_closed(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows = [row for row in rows if row["function"]["address"] != fx["initializer"]]
    _write_jsonl(fx["export"], rows)

    with pytest.raises(ValueError, match="instruction export missing create target"):
        _run(fx)


def test_frontier_mismatch_is_reported_without_guessing(tmp_path):
    fx = _fixture(tmp_path)
    frontier = json.loads(fx["frontier"].read_text(encoding="utf-8"))
    frontier["candidates"][0]["factory_functions"] = ["0x00109999"]
    _write_json(fx["frontier"], frontier)

    report = _run(fx)
    assert report["create_transfer_count"] == 0
    assert any(item["id"] == "create-frontier-match-not-unique" for item in report["blockers"])


def test_instruction_format_drift_fails_closed(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(fx["export"], rows)

    with pytest.raises(ValueError, match="expected only SHIFT.GhidraFunctionInstructions/2"):
        _run(fx)
