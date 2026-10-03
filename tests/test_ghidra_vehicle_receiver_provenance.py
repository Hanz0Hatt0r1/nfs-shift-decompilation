import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_receiver_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_receiver_provenance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _p(opcode, text=None):
    return {"opcode": opcode, "text": text or opcode}


def _ins(address, mnemonic, operands=None, *, flows=None, pcode=None, flow_type=None):
    operands = operands or []
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + ((" " + ",".join(operands)) if operands else ""),
        "operands": operands,
        "flow_type": flow_type or ("CALL" if mnemonic == "CALL" else "FALL_THROUGH"),
        "fallthrough": None,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _row(module, address, instructions, *, cc="__thiscall"):
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


def _owner_evidence(module, caller, call_address):
    return {
        "format": module.OWNER_EVIDENCE_FORMAT,
        "upper_caller": module.UPPER_CALLER,
        "upper_caller_reports": [
            {
                "address": caller,
                "direct_calls_to_required_target": [
                    {"instruction": call_address, "evidence_state": "verified"}
                ],
            }
        ],
    }


def _fixture(tmp_path, caller_instructions, *, upper_cc="__thiscall"):
    module = _load_module()
    caller = "0x00715700"
    call_address = "0x00715730"
    caller_instructions = list(caller_instructions) + [
        _ins(
            call_address,
            "CALL",
            [module.UPPER_CALLER],
            flows=[module.UPPER_CALLER],
            pcode=[_p("CALL")],
        )
    ]
    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            _row(module, caller, caller_instructions),
            _row(module, module.UPPER_CALLER, [_ins("0x007155f0", "RET", pcode=[_p("RETURN")])], cc=upper_cc),
        ],
    )
    evidence = tmp_path / "owner_evidence.json"
    evidence.write_text(
        json.dumps(_owner_evidence(module, caller, call_address)), encoding="utf-8"
    )
    return module, caller, call_address, export, evidence


def test_resolves_simple_register_relative_load_source(tmp_path):
    module, caller, call, export, evidence = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715710",
                "MOV",
                ["ECX", "dword ptr [ESI + 0x40]"],
                pcode=[_p("LOAD")],
            )
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    assert report["abi_receiver_register_candidate"] == "ECX"
    assert report["abi_receiver_register_state"] == "inferred"
    assert report["verified_syntactic_source_count"] == 1
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "verified"
    assert trace["source"]["kind"] == "register-relative-load"
    assert trace["source"]["base_register"] == "ESI"
    assert trace["source"]["displacement_hex"] == "0x40"
    assert report["callsites"][0]["receiver_object_identity_proven"] is False
    assert report["scope"]["ecx_is_this_proven"] is False


def test_resolves_lea_address_source_without_load(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715710",
                "LEA",
                ["ECX", "[EDI + 0x20]"],
                pcode=[_p("INT_ADD")],
            )
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    source = report["callsites"][0]["receiver_definition_trace"]["source"]
    assert source["kind"] == "register-relative-address"
    assert source["base_register"] == "EDI"
    assert source["displacement_hex"] == "0x20"


def test_follows_explicit_register_copy_chain(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715708",
                "MOV",
                ["EAX", "dword ptr [ESI + 0x44]"],
                pcode=[_p("LOAD")],
            ),
            _ins("0x00715710", "MOV", ["ECX", "EAX"], pcode=[_p("COPY")]),
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "verified"
    assert trace["status"] == "register-copy-chain"
    assert [row["destination_register"] for row in trace["chain"]] == ["ECX", "EAX"]
    assert trace["source"]["base_register"] == "ESI"
    assert trace["source"]["displacement_hex"] == "0x44"


def test_call_barrier_blocks_earlier_definition(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715708",
                "MOV",
                ["ECX", "dword ptr [ESI + 0x40]"],
                pcode=[_p("LOAD")],
            ),
            _ins("0x00715710", "CALL", ["0x00710000"], flows=["0x00710000"], pcode=[_p("CALL")]),
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "barrier-before-definition"
    assert "CALL" in trace["barrier"]["reason"]


def test_branch_barrier_blocks_earlier_definition(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [
            _ins("0x00715708", "MOV", ["ECX", "ESI"], pcode=[_p("COPY")]),
            _ins(
                "0x00715710",
                "JNZ",
                ["0x00715720"],
                flows=["0x00715720"],
                pcode=[_p("CBRANCH")],
                flow_type="CONDITIONAL_JUMP",
            ),
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "barrier-before-definition"
    assert "CBRANCH" in trace["barrier"]["reason"]


def test_unsupported_register_clobber_stops_trace(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [
            _ins(
                "0x00715708",
                "MOV",
                ["ECX", "dword ptr [ESI + 0x40]"],
                pcode=[_p("LOAD")],
            ),
            _ins("0x00715710", "XOR", ["ECX", "ECX"], pcode=[_p("INT_XOR")]),
        ],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "ambiguous"
    assert trace["status"] == "unsupported-register-clobber"
    assert trace["clobber"]["mnemonic"] == "XOR"


def test_missing_local_definition_stays_unknown(tmp_path):
    module, _, _, export, evidence = _fixture(
        tmp_path,
        [_ins("0x00715710", "NOP", [], pcode=[_p("COPY")])],
    )
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    trace = report["callsites"][0]["receiver_definition_trace"]
    assert trace["evidence_state"] == "unknown"
    assert trace["status"] == "no-local-definition-before-call"


def test_non_thiscall_callee_does_not_invent_receiver_register(tmp_path):
    module, _, _, export, evidence = _fixture(tmp_path, [], upper_cc="__cdecl")
    report = module.analyze_vehicle_receiver_provenance(export, evidence)
    assert report["abi_receiver_register_candidate"] is None
    assert report["abi_receiver_register_state"] == "unknown"
    assert report["callsites"][0]["receiver_definition_trace"]["status"] == "abi-receiver-register-unknown"


def test_fails_closed_when_expected_callsite_loses_flow(tmp_path):
    module, caller, call_address, export, evidence = _fixture(tmp_path, [])
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["function"]["address"] == caller:
            for instruction in row["instructions"]:
                if instruction["address"] == call_address:
                    instruction["flows"] = []
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="no longer flows"):
        module.analyze_vehicle_receiver_provenance(export, evidence)


def test_fails_closed_on_instruction_format_drift(tmp_path):
    module, _, _, export, evidence = _fixture(tmp_path, [])
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match=module.INSTRUCTION_FORMAT):
        module.analyze_vehicle_receiver_provenance(export, evidence)
