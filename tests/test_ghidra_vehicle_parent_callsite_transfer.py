import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_parent_callsite_transfer.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_parent_callsite_transfer", path)
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


def _function(address):
    return {
        "address": address,
        "name": f"FUN_{address[2:]}",
        "size": 128,
        "external": False,
        "thunk": False,
        "calling_convention": "__thiscall",
        "signature": f"undefined FUN_{address[2:]}(void)",
    }


def _call(source, instruction, target):
    return {
        "from_function": source,
        "from_name": f"FUN_{source[2:]}",
        "instruction": instruction,
        "to": target,
        "to_name": f"FUN_{target[2:]}",
        "indirect": False,
    }


def _fixture(tmp_path, prefix, *, entry_register="ECX", parent_cc="__thiscall"):
    module = _load_module()
    child = "0x00715700"
    parent = "0x00715000"
    grandparent = "0x00714000"
    call_address = "0x00715050"

    (tmp_path / "functions.jsonl").write_text(
        "".join(
            json.dumps(_function(address)) + "\n"
            for address in (child, parent, grandparent)
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            _call(parent, call_address, child),
            _call(grandparent, "0x00714040", parent),
        ],
    )

    parent_instructions = list(prefix) + [
        _ins(
            call_address,
            "CALL",
            [child],
            pcode=[_p("CALL")],
            flows=[child],
        )
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(export, [_row(module, parent, parent_instructions, cc=parent_cc)])

    pointer = {
        "format": module.POINTER_FORMAT,
        "origins": [
            {
                "caller": child,
                "direct_incoming_callers": [parent],
                "base_origin_trace": {
                    "evidence_state": "inferred" if entry_register == "ECX" else "unknown",
                    "status": "function-entry-abi-receiver-candidate" if entry_register == "ECX" else "function-entry-register-state",
                    "source": {
                        "kind": "function-entry-register",
                        "register": entry_register,
                    },
                },
            }
        ],
    }
    pointer_path = tmp_path / "pointer.json"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    return module, child, parent, grandparent, call_address, export, pointer_path


def test_verifies_register_transfer_and_local_parent_source(tmp_path):
    module, child, parent, _, call, export, pointer = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715020",
                "MOV",
                ["ECX", "dword ptr [ESI + 0x20]"],
                pcode=[_p("LOAD")],
            )
        ],
    )
    report = module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
    assert report["format"] == "SHIFT.VehicleParentCallsiteTransfer/1"
    assert report["verified_register_transfer_count"] == 1
    transfer = report["transfers"][0]
    assert transfer["parent"] == parent
    assert transfer["child"] == child
    assert transfer["call_instruction"] == call
    assert transfer["entry_register"] == "ECX"
    assert transfer["register_transfer_state"] == "verified"
    source = transfer["parent_register_source_trace"]
    assert source["evidence_state"] == "verified"
    assert source["source"]["kind"] == "register-relative-load"
    assert source["source"]["base_register"] == "ESI"
    assert source["source"]["displacement_hex"] == "0x20"
    assert transfer["object_identity_proven"] is False
    assert report["next_instruction_export_addresses"] == []


def test_parent_entry_receiver_boundary_targets_grandparent(tmp_path):
    module, _, parent, grandparent, _, export, pointer = _fixture(tmp_path, [])
    report = module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
    trace = report["transfers"][0]["parent_register_source_trace"]
    assert trace["evidence_state"] == "inferred"
    assert trace["status"] == "function-entry-abi-receiver-candidate"
    assert report["next_instruction_export_addresses"] == [grandparent]
    assert report["scope"]["direct_parent_is_owner_proof"] is False


def test_unknown_parent_entry_register_still_extends_frontier(tmp_path):
    module, _, _, grandparent, _, export, pointer = _fixture(
        tmp_path, [], entry_register="EAX"
    )
    report = module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
    trace = report["transfers"][0]["parent_register_source_trace"]
    assert trace["evidence_state"] == "unknown"
    assert trace["status"] == "function-entry-register-state"
    assert report["next_instruction_export_addresses"] == [grandparent]


def test_esp_entry_transfer_is_ambiguous_because_call_changes_esp(tmp_path):
    module, _, _, _, _, export, pointer = _fixture(
        tmp_path, [], entry_register="ESP"
    )
    report = module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
    transfer = report["transfers"][0]
    assert transfer["register_transfer_state"] == "ambiguous"
    assert transfer["parent_register_source_trace"]["status"] == "esp-mutated-by-call"
    assert report["ambiguous_register_transfer_count"] == 1
    assert report["scope"]["esp_transfer_treated_as_unchanged"] is False


def test_intervening_parent_call_blocks_source_trace_but_not_transfer_boundary(tmp_path):
    module, _, _, _, _, export, pointer = _fixture(
        tmp_path,
        [
            _ins("0x00715010", "MOV", ["ECX", "ESI"], pcode=[_p("COPY")]),
            _ins("0x00715020", "CALL", ["0x00710000"], pcode=[_p("CALL")], flows=["0x00710000"]),
        ],
    )
    report = module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
    transfer = report["transfers"][0]
    assert transfer["register_transfer_state"] == "verified"
    trace = transfer["parent_register_source_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "barrier-before-origin"


def test_fails_closed_when_raw_parent_set_changes(tmp_path):
    module, child, _, _, _, export, pointer = _fixture(tmp_path, [])
    extra_parent = "0x00713000"
    with (tmp_path / "functions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_function(extra_parent)) + "\n")
    with (tmp_path / "callgraph.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_call(extra_parent, "0x00713050", child)) + "\n")
    with pytest.raises(ValueError, match="raw callgraph parent set changed"):
        module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)


def test_fails_closed_when_exact_call_instruction_loses_flow(tmp_path):
    module, child, parent, _, call, export, pointer = _fixture(tmp_path, [])
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["function"]["address"] == parent:
            for instruction in row["instructions"]:
                if instruction["address"] == call:
                    instruction["flows"] = []
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="no longer flows"):
        module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)


def test_fails_closed_when_parent_instruction_export_missing(tmp_path):
    module, _, _, _, _, export, pointer = _fixture(tmp_path, [])
    export.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty instruction export"):
        module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)


def test_fails_closed_on_pointer_format_drift(tmp_path):
    module, _, _, _, _, export, pointer = _fixture(tmp_path, [])
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.VehiclePointerOriginFrontier/999"
    pointer.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=module.POINTER_FORMAT):
        module.analyze_vehicle_parent_callsite_transfer(tmp_path, export, pointer)
