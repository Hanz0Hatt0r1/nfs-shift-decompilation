import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_candidate_table_dispatch.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_candidate_table_dispatch", path)
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


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(
    tmp_path,
    *,
    between_store_load=None,
    between_load_call=None,
    load_operand="dword ptr [ESI]",
    call_operand="dword ptr [EAX + 0x8]",
    call_pcode="CALLIND",
    alias_state="verified",
    table_present=True,
    slot_present=True,
):
    module = _load_module()
    function = "0x00715700"
    store_instruction = "0x00715710"
    load_instruction = "0x00715730"
    call_instruction = "0x00715750"
    table = "0x00b10000"
    slot_target = "0x007155e9"

    (tmp_path / "binary.json").write_text(
        json.dumps(
            {
                "program_name": "SHIFT.exe",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    vtable_rows = []
    if table_present:
        slots = [
            {"slot": 0, "target": "0x00710000", "name": "slot0"},
            {"slot": 1, "target": "0x00710010", "name": "slot1"},
        ]
        if slot_present:
            slots.append({"slot": 2, "target": slot_target, "name": "slot2"})
        vtable_rows.append(
            {
                "address": table,
                "block": ".rdata",
                "slot_count": len(slots),
                "slots": slots,
                "function_xrefs": [function],
            }
        )
    (tmp_path / "vtables.json").write_text(
        json.dumps(
            {
                "format": module.VTABLE_FORMAT,
                "status": "heuristic-candidates",
                "vtables": vtable_rows,
            }
        ),
        encoding="utf-8",
    )

    instructions = [
        _ins(
            store_instruction,
            "MOV",
            ["dword ptr [ESI]", table],
            pcode=[_p("STORE")],
        ),
        *(between_store_load or []),
        _ins(
            load_instruction,
            "MOV",
            ["EAX", load_operand],
            pcode=[_p("LOAD")],
        ),
        *(between_load_call or []),
        _ins(
            call_instruction,
            "CALL",
            [call_operand],
            pcode=[_p(call_pcode)],
        ),
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            {
                "format": module.INSTRUCTION_FORMAT,
                "program": "SHIFT.exe",
                "requested": function,
                "found": True,
                "function": {
                    "address": function,
                    "name": f"FUN_{function[2:]}",
                    "size": len(instructions),
                    "calling_convention": "__thiscall",
                },
                "instruction_count": len(instructions),
                "instructions": instructions,
            }
        ],
    )

    alias = {
        "format": module.ALIAS_FORMAT,
        "candidates": [
            {
                "function": function,
                "function_name": f"FUN_{function[2:]}",
                "vtable_store_instruction": store_instruction,
                "store_shape": {
                    "instruction": store_instruction,
                    "evidence_state": "verified",
                    "status": "exact-literal-heuristic-table-address-store",
                    "destination_base_register": "ESI",
                    "destination_displacement": 0,
                    "destination_displacement_hex": "0x0",
                    "stored_address": table,
                    "stored_address_matches_reference": True,
                },
                "same_pointer_table_store_state": alias_state,
                "same_pointer_offset_zero_table_store_verified": alias_state == "verified",
                "heuristic_table_identity_state": "ambiguous",
            }
        ],
    }
    alias_path = tmp_path / "alias.json"
    alias_path.write_text(json.dumps(alias), encoding="utf-8")
    return {
        "module": module,
        "function": function,
        "table": table,
        "slot_target": slot_target,
        "store": store_instruction,
        "load": load_instruction,
        "call": call_instruction,
        "export": export,
        "alias": alias_path,
    }


def test_verifies_store_load_callind_candidate_slot_consistency(tmp_path):
    fx = _fixture(
        tmp_path,
        between_store_load=[_ins("0x00715720", "NOP", [], pcode=[])],
        between_load_call=[_ins("0x00715740", "NOP", [], pcode=[])],
    )
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    assert report["format"] == "SHIFT.VehicleCandidateTableDispatch/1"
    assert report["verified_alias_function_count"] == 1
    assert report["dispatch_candidate_count"] == 1
    assert report["verified_dispatch_consistency_count"] == 1
    row = report["dispatches"][0]
    assert row["store_instruction"] == fx["store"]
    assert row["table_load_instruction"] == fx["load"]
    assert row["indirect_call_instruction"] == fx["call"]
    assert row["callind_pcode_state"] == "verified"
    assert row["candidate_slot"]["slot_index"] == 2
    assert row["candidate_slot"]["slot_present"] is True
    assert row["candidate_slot"]["candidate_target"] == fx["slot_target"]
    assert row["dispatch_consistency_state"] == "verified"
    assert row["runtime_target_identity_proven"] is False
    assert row["class_identity_proven"] is False
    assert report["scope"]["candidate_slot_target_is_runtime_target_proof"] is False


def test_missing_callind_pcode_keeps_dispatch_ambiguous(tmp_path):
    fx = _fixture(tmp_path, call_pcode="CALL")
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    row = report["dispatches"][0]
    assert row["callind_pcode_state"] == "unknown"
    assert row["dispatch_consistency_state"] == "ambiguous"


def test_missing_candidate_slot_keeps_dispatch_ambiguous(tmp_path):
    fx = _fixture(tmp_path, slot_present=False)
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    row = report["dispatches"][0]
    assert row["candidate_slot"]["slot_index"] == 2
    assert row["candidate_slot"]["slot_present"] is False
    assert row["dispatch_consistency_state"] == "ambiguous"


def test_misaligned_slot_displacement_keeps_dispatch_ambiguous(tmp_path):
    fx = _fixture(tmp_path, call_operand="dword ptr [EAX + 0x6]")
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    row = report["dispatches"][0]
    assert row["candidate_slot"]["aligned"] is False
    assert row["candidate_slot"]["slot_index"] is None
    assert row["dispatch_consistency_state"] == "ambiguous"


def test_wrong_object_table_offset_produces_missing_load_blocker(tmp_path):
    fx = _fixture(tmp_path, load_operand="dword ptr [ESI + 0x4]")
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    assert report["dispatch_candidate_count"] == 0
    assert report["blocker_count"] == 1
    assert report["blockers"][0]["id"] == "candidate-table-pointer-load-not-found"


def test_object_base_clobber_prevents_closed_chain(tmp_path):
    fx = _fixture(
        tmp_path,
        between_store_load=[
            _ins("0x00715720", "MOV", ["ESI", "EDI"], pcode=[_p("COPY")])
        ],
    )
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    assert report["dispatch_candidate_count"] == 0
    assert report["blockers"][0]["id"] == "candidate-table-dispatch-chain-not-closed"


def test_table_register_clobber_keeps_dispatch_ambiguous(tmp_path):
    fx = _fixture(
        tmp_path,
        between_load_call=[
            _ins("0x00715740", "XOR", ["EAX", "EAX"], pcode=[_p("INT_XOR")])
        ],
    )
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    row = report["dispatches"][0]
    assert row["table_register_continuity"]["evidence_state"] == "ambiguous"
    assert row["dispatch_consistency_state"] == "ambiguous"


def test_unverified_alias_candidate_is_not_used_for_dispatch(tmp_path):
    fx = _fixture(tmp_path, alias_state="ambiguous")
    report = fx["module"].analyze_vehicle_candidate_table_dispatch(
        tmp_path, fx["export"], fx["alias"]
    )
    assert report["verified_alias_function_count"] == 0
    assert report["dispatch_candidate_count"] == 0
    assert report["blocker_count"] == 0


def test_verified_alias_table_must_exist_in_heuristic_inventory(tmp_path):
    fx = _fixture(tmp_path, table_present=False)
    with pytest.raises(ValueError, match="absent from heuristic vtable inventory"):
        fx["module"].analyze_vehicle_candidate_table_dispatch(
            tmp_path, fx["export"], fx["alias"]
        )


def test_fails_closed_on_vtable_status_drift(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads((tmp_path / "vtables.json").read_text(encoding="utf-8"))
    payload["status"] = "promoted-vtables"
    (tmp_path / "vtables.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="heuristic-candidates status"):
        fx["module"].analyze_vehicle_candidate_table_dispatch(
            tmp_path, fx["export"], fx["alias"]
        )


def test_fails_closed_on_alias_format_drift(tmp_path):
    fx = _fixture(tmp_path)
    payload = json.loads(fx["alias"].read_text(encoding="utf-8"))
    payload["format"] = "SHIFT.VehicleVtablePointerAlias/999"
    fx["alias"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=fx["module"].ALIAS_FORMAT):
        fx["module"].analyze_vehicle_candidate_table_dispatch(
            tmp_path, fx["export"], fx["alias"]
        )
