import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_lifetime_pointer_transfer.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_lifetime_pointer_transfer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _p(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _ins(address, mnemonic, operands=None, *, flows=None, pcode=None):
    operands = operands or []
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + ((" " + ",".join(operands)) if operands else ""),
        "operands": operands,
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _row(module, function, instructions, calling_convention="__thiscall"):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": function,
        "found": True,
        "function": {
            "address": function,
            "name": f"FUN_{function[2:]}",
            "size": max(1, len(instructions) * 4),
            "calling_convention": calling_convention,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(tmp_path, *, factory_extra=None, wrapper_extra=None, initializer_cc="__thiscall"):
    module = _load_module()
    factory = "0x00100010"
    initializer = "0x00110000"
    helper = "0x00886900"
    wrapper = "0x00120000"
    teardown = "0x00121000"
    release = "0x00886930"
    vtable = "0x00402200"
    descriptor = 7

    frontier = {
        "format": module.FRONTIER_FORMAT,
        "candidates": [
            {
                "vehicle_pointer_function": "0x00715700",
                "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                "stored_table_address": vtable,
                "descriptor": descriptor,
                "lifetime_pair_class_name": "VehicleCandidate",
                "frontier_evidence_state": "verified",
                "verified_vehicle_lifetime_pair_frontier": True,
                "factory_functions": [factory],
                "initializer_candidates": [initializer],
                "deleting_wrapper_functions": [wrapper],
                "teardown_transition_functions": [teardown],
            }
        ],
    }
    frontier_path = tmp_path / "frontier.json"
    _write_json(frontier_path, frontier)

    create_shape = {
        "class_name": "VehicleCandidate",
        "descriptor": descriptor,
        "factory_function": factory,
        "initializer_candidate": initializer,
        "immediate_preinitializer_helper": helper,
        "helper_result_flows_to_initializer": True,
        "helper_literal_arguments": [0x38, 4],
        "create_wrapper_shape": True,
        "ghidra_factory_to_helper": True,
        "ghidra_factory_to_initializer": True,
    }
    delete_shape = {
        "class_name": "VehicleCandidate",
        "descriptor": descriptor,
        "wrapper_function": wrapper,
        "teardown_transition_function": teardown,
        "release_helper": release,
        "deleting_wrapper_shape": True,
        "ghidra_teardown_edge": True,
        "ghidra_release_edge": True,
    }
    pair = {
        "format": module.PAIR_FORMAT,
        "classes": [
            {
                "class_name": "VehicleCandidate",
                "descriptor": descriptor,
                "own_vtable": int(vtable, 16),
                "paired_lifetime_shape": True,
                "ghidra_paired_lifetime_shape": True,
                "factory_functions": [factory],
                "initializer_candidates": [initializer],
                "preinitializer_helpers": [helper],
                "unambiguous_preinitializer_helper": helper,
                "deleting_wrapper_functions": [wrapper],
                "teardown_transition_functions": [teardown],
                "release_helpers": [release],
                "unambiguous_release_helper": release,
                "create_shapes": [create_shape],
                "delete_shapes": [delete_shape],
            }
        ],
    }
    pair_path = tmp_path / "pairs.json"
    _write_json(pair_path, pair)

    factory_instructions = [
        _ins("0x00100020", "CALL", [helper], flows=[helper], pcode=[_p("CALL")]),
        *(factory_extra or []),
        _ins("0x00100030", "MOV", ["ECX", "EAX"], pcode=[_p("COPY")]),
        _ins("0x00100034", "CALL", [initializer], flows=[initializer], pcode=[_p("CALL")]),
    ]
    wrapper_instructions = [
        _ins("0x00120004", "MOV", ["ESI", "ECX"], pcode=[_p("COPY")]),
        *(wrapper_extra or []),
        _ins("0x00120010", "MOV", ["ECX", "ESI"], pcode=[_p("COPY")]),
        _ins("0x00120014", "CALL", [teardown], flows=[teardown], pcode=[_p("CALL")]),
        _ins("0x00120018", "CALL", [release], flows=[release], pcode=[_p("CALL")]),
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            _row(module, factory, factory_instructions),
            _row(module, initializer, [_ins("0x00110000", "RET", pcode=[_p("RETURN")])], initializer_cc),
            _row(module, wrapper, wrapper_instructions),
            _row(module, teardown, [_ins("0x00121000", "RET", pcode=[_p("RETURN")])]),
        ],
    )
    return module, frontier_path, pair_path, export, {
        "factory": factory,
        "initializer": initializer,
        "helper": helper,
        "wrapper": wrapper,
        "teardown": teardown,
        "release": release,
    }


def test_verifies_create_and_delete_machine_value_transfer(tmp_path):
    module, frontier, pair, export, ids = _fixture(tmp_path)
    report = module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)

    assert report["format"] == "SHIFT.VehicleLifetimePointerTransfer/1"
    assert report["candidate_count"] == 1
    assert report["verified_create_machine_transfer_count"] == 1
    assert report["verified_delete_machine_transfer_count"] == 1
    row = report["candidates"][0]
    assert row["candidate_evidence_state"] == "verified"

    create = row["create_transfers"][0]
    assert create["helper_call"]["evidence_state"] == "verified"
    assert create["initializer_call"]["evidence_state"] == "verified"
    assert create["exact_helper_result_reaches_initializer_receiver_candidate"] is True
    assert create["machine_value_transfer_state"] == "verified"
    assert create["lifetime_transfer_evidence_state"] == "inferred"
    assert create["receiver_source_trace"]["source"]["kind"] == "direct-call-result-register"

    delete = row["delete_transfers"][0]
    assert delete["exact_wrapper_entry_receiver_reaches_teardown_receiver_candidate"] is True
    assert delete["machine_value_transfer_state"] == "verified"
    assert delete["lifetime_transfer_evidence_state"] == "inferred"
    assert delete["receiver_source_trace"]["source"]["kind"] == "function-entry-register"

    assert set(report["next_instruction_export_addresses"]) == {ids["helper"], ids["release"]}
    assert row["same_runtime_object_across_create_update_delete_proven"] is False


def test_unrelated_call_between_helper_and_receiver_breaks_create_transfer(tmp_path):
    module, frontier, pair, export, _ = _fixture(
        tmp_path,
        factory_extra=[
            _ins("0x00100028", "CALL", ["0x00999900"], flows=["0x00999900"], pcode=[_p("CALL")])
        ],
    )
    report = module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)
    create = report["candidates"][0]["create_transfers"][0]
    assert create["machine_value_transfer_state"] == "ambiguous"
    assert create["exact_helper_result_reaches_initializer_receiver_candidate"] is False
    assert create["receiver_source_trace"]["status"] == "register-copy-chain"
    assert create["receiver_source_trace"]["upstream_status"] == "call-barrier-before-source"


def test_wrapper_receiver_clobber_breaks_delete_transfer(tmp_path):
    module, frontier, pair, export, _ = _fixture(
        tmp_path,
        wrapper_extra=[_ins("0x00120008", "XOR", ["ESI", "ESI"], pcode=[_p("INT_XOR")])],
    )
    report = module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)
    delete = report["candidates"][0]["delete_transfers"][0]
    assert delete["machine_value_transfer_state"] == "ambiguous"
    assert delete["exact_wrapper_entry_receiver_reaches_teardown_receiver_candidate"] is False
    assert delete["receiver_source_trace"]["upstream_status"] == "unsupported-register-definition-or-clobber"


def test_multiple_initializer_calls_are_not_chosen_by_order(tmp_path):
    module, frontier, pair, export, ids = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    factory = next(row for row in rows if row["function"]["address"] == ids["factory"])
    factory["instructions"].append(
        _ins("0x00100040", "CALL", [ids["initializer"]], flows=[ids["initializer"]], pcode=[_p("CALL")])
    )
    factory["instruction_count"] = len(factory["instructions"])
    _write_jsonl(export, rows)

    report = module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)
    create = report["candidates"][0]["create_transfers"][0]
    assert create["initializer_call"]["evidence_state"] == "ambiguous"
    assert create["initializer_call"]["status"] == "multiple-direct-calls"
    assert create["machine_value_transfer_state"] == "unknown"


def test_non_thiscall_initializer_keeps_receiver_role_unknown(tmp_path):
    module, frontier, pair, export, _ = _fixture(tmp_path, initializer_cc="__cdecl")
    report = module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)
    create = report["candidates"][0]["create_transfers"][0]
    assert create["initializer_receiver_register_candidate"] is None
    assert create["initializer_receiver_abi_state"] == "unknown"
    assert create["machine_value_transfer_state"] == "unknown"
    assert create["lifetime_transfer_evidence_state"] == "unknown"


def test_frontier_pair_function_set_drift_fails_closed(tmp_path):
    module, frontier, pair, export, _ = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["classes"][0]["initializer_candidates"] = ["FUN_00abcdef"]
    _write_json(pair, payload)
    with pytest.raises(ValueError, match="lifetime frontier/pair drift"):
        module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)


def test_duplicate_descriptor_vtable_pair_fails_closed(tmp_path):
    module, frontier, pair, export, _ = _fixture(tmp_path)
    payload = json.loads(pair.read_text(encoding="utf-8"))
    payload["classes"].append(dict(payload["classes"][0]))
    _write_json(pair, payload)
    with pytest.raises(ValueError, match="must map to exactly one class lifetime pair"):
        module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)


def test_instruction_format_drift_fails_closed(tmp_path):
    module, frontier, pair, export, _ = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="requires SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_vehicle_lifetime_pointer_transfer(frontier, pair, export)
