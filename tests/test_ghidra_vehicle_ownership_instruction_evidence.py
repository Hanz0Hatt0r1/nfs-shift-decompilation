import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_ownership_instruction_evidence.py"
    )
    spec = importlib.util.spec_from_file_location(
        "analyze_vehicle_ownership_instruction_evidence", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic, operands, *, flows=None, refs=None, pcode=None):
    text = mnemonic
    if operands:
        text += " " + ",".join(operands)
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands,
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows or [],
        "references": refs or [],
        "pcode": pcode or [],
    }


def _p(opcode, text=None):
    return {"opcode": opcode, "text": text or opcode}


def _row(module, address, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _fixture(tmp_path):
    module = _load_module()
    caller_a = "0x00715700"
    caller_b = "0x00715800"
    lifecycle = "0x00715900"
    upper_vtable = "0x00b10000"
    alternate_vtable = "0x00b20000"

    frontier = {
        "format": module.FRONTIER_FORMAT,
        "anchors": {
            "upper_caller": module.UPPER_CALLER,
            "alternate_caller": module.ALTERNATE_CALLER,
        },
        "upper_direct_callers": [
            {"address": caller_a, "direct_call_count_to_upper": 1},
            {"address": caller_b, "direct_call_count_to_upper": 1},
        ],
        "upper_vtable_memberships": [
            {"vtable_address": upper_vtable}
        ],
        "alternate_vtable_memberships": [
            {"vtable_address": alternate_vtable}
        ],
        "instruction_export_addresses": [
            module.UPPER_CALLER,
            module.ALTERNATE_CALLER,
            caller_a,
            caller_b,
            lifecycle,
        ],
    }
    frontier_path = tmp_path / "frontier.json"
    frontier_path.write_text(json.dumps(frontier), encoding="utf-8")

    caller_a_instructions = [
        _ins(
            "0x00715710",
            "MOV",
            ["EAX", "dword ptr [ECX + 0x20]"],
            pcode=[_p("LOAD")],
        ),
        _ins(
            "0x00715720",
            "MOV",
            ["dword ptr [ECX]", upper_vtable],
            refs=[{"to": upper_vtable, "type": "DATA"}],
            pcode=[_p("STORE")],
        ),
        _ins(
            "0x00715730",
            "CALL",
            [module.UPPER_CALLER],
            flows=[module.UPPER_CALLER],
            refs=[{"to": module.UPPER_CALLER, "type": "UNCONDITIONAL_CALL"}],
            pcode=[_p("CALL")],
        ),
    ]
    caller_b_instructions = [
        _ins(
            "0x00715810",
            "MOV",
            ["EDX", "dword ptr [ESI + 0x30]"],
            pcode=[_p("LOAD")],
        ),
        _ins(
            "0x00715820",
            "CALL",
            [module.UPPER_CALLER],
            flows=[module.UPPER_CALLER],
            refs=[{"to": module.UPPER_CALLER, "type": "UNCONDITIONAL_CALL"}],
            pcode=[_p("CALL")],
        ),
    ]
    upper_instructions = [
        _ins(
            "0x007155f0",
            "MOV",
            ["EAX", "dword ptr [ECX + 0x10]"],
            pcode=[_p("LOAD")],
        )
    ]
    alternate_instructions = [
        _ins(
            "0x0079b2e0",
            "MOV",
            ["EAX", "dword ptr [ECX + 0x234]"],
            pcode=[_p("LOAD")],
        )
    ]
    lifecycle_instructions = [
        _ins(
            "0x00715910",
            "MOV",
            ["dword ptr [EDI + 0x4]", alternate_vtable],
            refs=[{"to": alternate_vtable, "type": "DATA"}],
            pcode=[_p("STORE")],
        ),
        _ins(
            "0x00715920",
            "MOV",
            ["EAX", "dword ptr [EDI + 0x40]"],
            pcode=[_p("LOAD")],
        ),
    ]

    export_path = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export_path,
        [
            _row(module, caller_a, caller_a_instructions),
            _row(module, caller_b, caller_b_instructions),
            _row(module, module.UPPER_CALLER, upper_instructions),
            _row(module, module.ALTERNATE_CALLER, alternate_instructions),
            _row(module, lifecycle, lifecycle_instructions),
        ],
    )

    return {
        "module": module,
        "frontier": frontier_path,
        "export": export_path,
        "caller_a": caller_a,
        "caller_b": caller_b,
        "lifecycle": lifecycle,
        "upper_vtable": upper_vtable,
        "alternate_vtable": alternate_vtable,
    }


def test_joins_call_access_and_vtable_store_evidence_without_promotion(tmp_path):
    fx = _fixture(tmp_path)
    report = fx["module"].analyze_vehicle_ownership_instruction_evidence(
        fx["export"], fx["frontier"]
    )

    assert report["format"] == "SHIFT.VehicleOwnershipInstructionEvidence/1"
    assert len(report["upper_caller_reports"]) == 2
    callers = {row["address"]: row for row in report["upper_caller_reports"]}

    a = callers[fx["caller_a"]]
    assert a["call_count_crosscheck_state"] == "verified"
    assert a["direct_calls_to_required_target"][0]["instruction"] == "0x00715730"
    assert any(
        group["base_register"] == "ECX"
        and group["displacement_hex"] == "0x20"
        and group["read_count"] == 1
        for group in a["register_relative_access_groups"]
    )
    assert a["vtable_reference_instructions"][0]["has_store"] is True
    assert a["vtable_reference_instructions"][0]["vptr_store_proven"] is False
    assert a["same_base_overlaps"][0]["base_register"] == "ECX"
    assert set(a["same_base_overlaps"][0]["access_displacements"]) == {"0x0", "0x20"}
    assert a["same_base_overlaps"][0]["object_identity_proven"] is False

    assert report["vtable_store_candidate_count"] == 2
    assert report["same_base_overlap_candidate_count"] == 2
    assert set(report["relevant_heuristic_vtables"]) == {
        fx["upper_vtable"],
        fx["alternate_vtable"],
    }
    assert report["scope"]["same_base_register_is_pointer_alias_proof"] is False
    assert report["scope"]["owner_identity_proven"] is False


def test_fails_closed_when_expected_target_is_missing(tmp_path):
    fx = _fixture(tmp_path)
    rows = [
        row
        for row in fx["export"].read_text(encoding="utf-8").splitlines()
        if fx["lifecycle"] not in row
    ]
    fx["export"].write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing ownership target"):
        fx["module"].analyze_vehicle_ownership_instruction_evidence(
            fx["export"], fx["frontier"]
        )


def test_fails_closed_when_call_count_drifts(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["function"]["address"] == fx["caller_a"]:
            row["instructions"].append(
                _ins(
                    "0x00715740",
                    "CALL",
                    [fx["module"].UPPER_CALLER],
                    flows=[fx["module"].UPPER_CALLER],
                    refs=[
                        {
                            "to": fx["module"].UPPER_CALLER,
                            "type": "UNCONDITIONAL_CALL",
                        }
                    ],
                    pcode=[_p("CALL")],
                )
            )
            row["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    with pytest.raises(ValueError, match="expected 1 direct CALL"):
        fx["module"].analyze_vehicle_ownership_instruction_evidence(
            fx["export"], fx["frontier"]
        )


def test_fails_closed_when_flow_to_upper_lacks_call_pcode(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["function"]["address"] == fx["caller_b"]:
            for instruction in row["instructions"]:
                if fx["module"].UPPER_CALLER in instruction["flows"]:
                    instruction["pcode"] = [_p("BRANCH")]
    _write_jsonl(fx["export"], rows)

    with pytest.raises(ValueError, match="lacks CALL p-code"):
        fx["module"].analyze_vehicle_ownership_instruction_evidence(
            fx["export"], fx["frontier"]
        )


def test_records_complex_memory_operand_as_blocker_without_guessing(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["function"]["address"] == fx["caller_b"]:
            row["instructions"].insert(
                0,
                _ins(
                    "0x00715808",
                    "MOV",
                    ["EAX", "dword ptr [ESI + EDX*4 + 0x20]"],
                    pcode=[_p("LOAD")],
                ),
            )
            row["instruction_count"] += 1
    _write_jsonl(fx["export"], rows)

    report = fx["module"].analyze_vehicle_ownership_instruction_evidence(
        fx["export"], fx["frontier"]
    )
    assert report["unparsed_memory_operand_count"] == 1
    assert report["blockers"][3]["evidence_state"] == "ambiguous"
    assert report["scope"]["register_name_is_object_identity_proof"] is False


def test_fails_closed_on_instruction_format_drift(tmp_path):
    fx = _fixture(tmp_path)
    rows = [json.loads(line) for line in fx["export"].read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(fx["export"], rows)

    with pytest.raises(ValueError, match=fx["module"].INSTRUCTION_FORMAT):
        fx["module"].analyze_vehicle_ownership_instruction_evidence(
            fx["export"], fx["frontier"]
        )
