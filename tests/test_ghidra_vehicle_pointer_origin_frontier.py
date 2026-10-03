import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_pointer_origin_frontier.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_pointer_origin_frontier", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _p(opcode, text=None):
    return {"opcode": opcode, "text": text or opcode}


def _ins(address, mnemonic, operands=None, *, pcode=None, flows=None):
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


def _row(module, address, instructions, cc="__thiscall"):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions),
            "calling_convention": cc,
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path, prefix, *, cc="__thiscall", base="ESI", receiver_state="verified"):
    module = _load_module()
    caller = "0x00715700"
    parent = "0x00715000"
    source_instruction = "0x00715720"
    call_instruction = "0x00715730"
    instructions = list(prefix) + [
        _ins(
            source_instruction,
            "MOV",
            ["ECX", f"dword ptr [{base} + 0x40]"],
            pcode=[_p("LOAD")],
        ),
        _ins(
            call_instruction,
            "CALL",
            [module.UPPER_CALLER],
            pcode=[_p("CALL")],
            flows=[module.UPPER_CALLER],
        ),
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(export, [_row(module, caller, instructions, cc=cc)])

    receiver = {
        "format": module.RECEIVER_FORMAT,
        "callee": module.UPPER_CALLER,
        "callsites": [
            {
                "caller": caller,
                "call_instruction": call_instruction,
                "receiver_definition_trace": {
                    "evidence_state": receiver_state,
                    "status": "syntactic-source-resolved",
                    "source": {
                        "kind": "register-relative-load",
                        "base_register": base,
                        "displacement": 0x40,
                        "displacement_hex": "0x40",
                        "instruction": source_instruction,
                    },
                },
            }
        ],
    }
    receiver_path = tmp_path / "receiver.json"
    receiver_path.write_text(json.dumps(receiver), encoding="utf-8")

    lifecycle = {
        "format": module.LIFECYCLE_FORMAT,
        "anchors": {"upper_caller": module.UPPER_CALLER},
        "upper_direct_callers": [
            {
                "address": caller,
                "direct_incoming_calls": [
                    {
                        "from_function": parent,
                        "from_name": f"FUN_{parent[2:]}",
                        "instruction": "0x00715044",
                        "to": caller,
                        "to_name": f"FUN_{caller[2:]}",
                        "indirect": False,
                    }
                ],
            }
        ],
    }
    lifecycle_path = tmp_path / "lifecycle.json"
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")

    owner_instruction = {
        "format": module.OWNER_INSTRUCTION_FORMAT,
        "upper_caller": module.UPPER_CALLER,
        "vtable_store_candidates": [
            {
                "function": caller,
                "function_name": f"FUN_{caller[2:]}",
                "instruction": "0x00715708",
                "instruction_text": f"MOV dword ptr [{base}],0x00b10000",
                "matching_vtable_references": [
                    {"to": "0x00b10000", "type": "DATA"}
                ],
                "simple_memory_operands": [
                    {
                        "base_register": base,
                        "displacement": 0,
                        "displacement_hex": "0x0",
                    }
                ],
            }
        ],
    }
    owner_path = tmp_path / "owner_instruction.json"
    owner_path.write_text(json.dumps(owner_instruction), encoding="utf-8")

    return module, caller, parent, export, receiver_path, lifecycle_path, owner_path


def test_reaches_thiscall_entry_candidate_and_targets_direct_parent(tmp_path):
    module, caller, parent, export, receiver, lifecycle, owner = _fixture(
        tmp_path,
        [_ins("0x00715710", "MOV", ["ESI", "ECX"], pcode=[_p("COPY")])],
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    assert report["format"] == "SHIFT.VehiclePointerOriginFrontier/1"
    assert report["inferred_entry_origin_count"] == 1
    origin = report["origins"][0]
    trace = origin["base_origin_trace"]
    assert trace["evidence_state"] == "inferred"
    assert trace["status"] == "register-copy-origin-chain"
    assert trace["upstream_status"] == "function-entry-abi-receiver-candidate"
    assert trace["source"]["kind"] == "function-entry-register"
    assert trace["source"]["abi_role_candidate"] == "thiscall-receiver"
    assert origin["base_register_is_object_pointer_proven"] is False
    assert report["next_instruction_export_addresses"] == [parent]
    assert report["scope"]["direct_incoming_caller_is_owner_proof"] is False


def test_resolves_second_local_memory_origin_without_crossing_to_parent(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715710",
                "MOV",
                ["ESI", "dword ptr [EDI + 0x20]"],
                pcode=[_p("LOAD")],
            )
        ],
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    assert report["verified_origin_count"] == 1
    trace = report["origins"][0]["base_origin_trace"]
    assert trace["status"] == "local-origin-resolved"
    assert trace["source"]["base_register"] == "EDI"
    assert trace["source"]["displacement_hex"] == "0x20"
    assert report["next_instruction_export_addresses"] == []


def test_unknown_entry_register_still_targets_parent_without_inventing_abi_role(tmp_path):
    module, _, parent, export, receiver, lifecycle, owner = _fixture(
        tmp_path, [], base="ESI"
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    assert report["unknown_origin_count"] == 1
    trace = report["origins"][0]["base_origin_trace"]
    assert trace["status"] == "function-entry-register-state"
    assert trace["source"]["abi_role_candidate"] is None
    assert report["next_instruction_export_addresses"] == [parent]


def test_call_barrier_keeps_origin_ambiguous(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(
        tmp_path,
        [
            _ins("0x00715708", "MOV", ["ESI", "EDI"], pcode=[_p("COPY")]),
            _ins("0x00715710", "CALL", ["0x00710000"], pcode=[_p("CALL")], flows=["0x00710000"]),
        ],
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    assert report["ambiguous_origin_count"] == 1
    trace = report["origins"][0]["base_origin_trace"]
    assert trace["status"] == "barrier-before-origin"
    assert report["next_instruction_export_addresses"] == []


def test_unknown_first_operand_writer_is_fail_closed_clobber(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(
        tmp_path,
        [
            _ins("0x00715708", "MOV", ["ESI", "EDI"], pcode=[_p("COPY")]),
            _ins("0x00715710", "XCHG", ["ESI", "EAX"], pcode=[_p("COPY")]),
        ],
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    trace = report["origins"][0]["base_origin_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "unsupported-register-definition-or-clobber"
    assert trace["clobber"]["mnemonic"] == "XCHG"


def test_correlates_same_function_vtable_store_only_as_ambiguous_overlap(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(tmp_path, [])
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    assert report["vtable_overlap_candidate_count"] == 1
    overlap = report["origins"][0]["vtable_store_overlaps"][0]
    assert overlap["base_register"] == "ESI"
    assert overlap["evidence_state"] == "ambiguous"
    assert overlap["pointer_alias_proven"] is False
    assert overlap["vptr_store_proven"] is False


def test_nonverified_receiver_source_is_not_extended(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(
        tmp_path, [], receiver_state="ambiguous"
    )
    report = module.analyze_vehicle_pointer_origin_frontier(
        export, receiver, lifecycle, owner
    )
    origin = report["origins"][0]
    assert origin["status"] == "receiver-source-not-eligible-for-base-origin-trace"
    assert origin["base_origin_trace"] is None
    assert report["next_instruction_export_addresses"] == []


def test_fails_closed_when_receiver_source_instruction_missing(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(tmp_path, [])
    payload = json.loads(receiver.read_text(encoding="utf-8"))
    payload["callsites"][0]["receiver_definition_trace"]["source"]["instruction"] = "0x00715799"
    receiver.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="receiver source instruction absent"):
        module.analyze_vehicle_pointer_origin_frontier(
            export, receiver, lifecycle, owner
        )


def test_fails_closed_on_receiver_format_drift(tmp_path):
    module, _, _, export, receiver, lifecycle, owner = _fixture(tmp_path, [])
    payload = json.loads(receiver.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.VehicleReceiverProvenance/999"
    receiver.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=module.RECEIVER_FORMAT):
        module.analyze_vehicle_pointer_origin_frontier(
            export, receiver, lifecycle, owner
        )
