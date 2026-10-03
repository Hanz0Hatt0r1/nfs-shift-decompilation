import importlib.util
import json
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "analyze_vehicle_create_helper_return_provenance.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_create_helper_return_provenance", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")
    return path


def _p(opcode):
    return {"opcode": opcode, "text": opcode.lower()}


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, pcode=None):
    operands = operands or []
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + ((" " + ",".join(operands)) if operands else ""),
        "operands": operands,
        "flow_type": "FALL_THROUGH",
        "fallthrough": fallthrough,
        "flows": flows or [],
        "references": [],
        "pcode": pcode or [],
    }


def _row(module, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": module.CREATE_HELPER,
        "found": True,
        "function": {
            "address": module.CREATE_HELPER,
            "name": "FUN_00886900",
            "size": len(instructions) * 4,
            "calling_convention": "__cdecl",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _retail_instructions(module):
    return [
        _ins("0x00886900", "PUSH", ["EBP"], fallthrough="0x00886901"),
        _ins("0x00886901", "MOV", ["EBP", "ESP"], fallthrough="0x00886903", pcode=[_p("COPY")]),
        _ins("0x00886903", "MOV", ["ECX", "dword ptr [EBP+0xc]"], fallthrough="0x00886906", pcode=[_p("LOAD"), _p("COPY")]),
        _ins("0x00886906", "TEST", ["ECX", "ECX"], fallthrough="0x00886908"),
        _ins("0x00886908", "JZ", ["0x00886918"], fallthrough="0x0088690a", flows=["0x00886918"], pcode=[_p("CBRANCH")]),
        _ins("0x0088690a", "MOV", ["EAX", "dword ptr [EBP+0x10]"], fallthrough="0x0088690d", pcode=[_p("LOAD"), _p("COPY")]),
        _ins("0x0088690d", "MOV", ["EDX", "dword ptr [EBP+0x8]"], fallthrough="0x00886910", pcode=[_p("LOAD"), _p("COPY")]),
        _ins("0x00886910", "PUSH", ["EAX"], fallthrough="0x00886911"),
        _ins("0x00886911", "CALL", [module.ALLOCATION_BACKEND], fallthrough="0x00886916", flows=[module.ALLOCATION_BACKEND], pcode=[_p("CALL")]),
        _ins("0x00886916", "POP", ["EBP"], fallthrough="0x00886917"),
        _ins("0x00886917", "RET", pcode=[_p("RETURN")]),
        _ins("0x00886918", "MOV", ["EDX", "dword ptr [EBP+0x10]"], fallthrough="0x0088691b", pcode=[_p("LOAD"), _p("COPY")]),
        _ins("0x0088691b", "MOV", ["ECX", "dword ptr [EBP+0x8]"], fallthrough="0x0088691e", pcode=[_p("LOAD"), _p("COPY")]),
        _ins("0x0088691e", "POP", ["EBP"], fallthrough="0x0088691f"),
        _ins("0x0088691f", "JMP", [module.FALLBACK_BACKEND], flows=[module.FALLBACK_BACKEND], pcode=[_p("BRANCH")]),
    ]


def _fixture(tmp_path, *, instructions=None, forwarding_confirmed=True):
    module = _load_module()
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "format": module.BRIDGE_FORMAT,
            "create_bridges": [
                {
                    "descriptor": 2,
                    "class_name": "VehicleCandidate",
                    "vehicle_pointer_function": "0x00715700",
                    "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                    "stored_table_address": "0x00402200",
                    "factory_function": "0x00100000",
                    "preinitializer_helper": module.CREATE_HELPER,
                    "initializer_candidate": "0x00102000",
                    "initializer_backing_allocation_request_state": "inferred",
                    "initializer_backing_allocation_request_value": 56,
                    "machine_helper_result_to_initializer_receiver_state": "verified",
                }
            ],
        },
    )
    forwarding = _write_json(
        tmp_path / "forwarding.json",
        {
            "format": module.FORWARDING_FORMAT,
            "wrappers": [
                {
                    "address": module.CREATE_HELPER,
                    "name": "FUN_00886900",
                    "forwarding_confirmed": forwarding_confirmed,
                    "call_sites": [
                        {
                            "instruction": "0x00886911",
                            "target": module.ALLOCATION_BACKEND,
                            "transfer_kind": "call",
                            "arguments_resolved": True,
                        },
                        {
                            "instruction": "0x0088691f",
                            "target": module.FALLBACK_BACKEND,
                            "transfer_kind": "tail-call",
                            "arguments_resolved": True,
                        },
                    ],
                }
            ],
        },
    )
    backend = _write_json(
        tmp_path / "backend.json",
        {
            "format": module.BACKEND_FORMAT,
            "allocation_backend_diagnostic_proven": True,
            "functions": [
                {
                    "address": module.ALLOCATION_BACKEND,
                    "name": "FUN_00638020",
                    "role": "allocation-diagnostic-backend",
                    "calling_convention": "__fastcall",
                },
                {
                    "address": module.FALLBACK_BACKEND,
                    "name": "FUN_006382b0",
                    "role": "create-fallback-backend",
                    "calling_convention": "__fastcall",
                },
            ],
        },
    )
    export = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [_row(module, instructions or _retail_instructions(module))],
    )
    return module, bridge, forwarding, backend, export


def test_retail_helper_all_reachable_exits_are_exact_backend_sourced(tmp_path):
    module, bridge, forwarding, backend, export = _fixture(tmp_path)
    report = module.analyze_vehicle_create_helper_return_provenance(
        bridge, forwarding, backend, export
    )

    assert report["format"] == "SHIFT.VehicleCreateHelperReturnProvenance/1"
    assert report["exit_count"] == 2
    assert report["verified_backend_exit_count"] == 2
    assert report["all_reachable_helper_exits_backend_sourced"] is True
    assert report["allocation_diagnostic_backend_exit_present"] is True
    assert report["create_fallback_backend_exit_present"] is True

    ret = next(row for row in report["exits"] if row["kind"] == "ret")
    assert ret["backend_target"] == module.ALLOCATION_BACKEND
    assert ret["verified_backend_eax_origin"] is True
    assert ret["machine_exit_provenance_state"] == "verified"

    tail = next(row for row in report["exits"] if row["kind"] == "tail-call")
    assert tail["backend_target"] == module.FALLBACK_BACKEND
    assert tail["machine_exit_provenance_state"] == "verified"

    joined = report["vehicle_create_bridges"][0]
    assert joined["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert joined["allocation_request_value"] == 56
    assert joined["helper_machine_exit_provenance_state"] == "verified"
    assert joined["helper_return_value_semantics_state"] == "inferred"
    assert joined["helper_return_is_allocated_pointer_proven"] is False
    assert report["scope"]["allocation_diagnostic_proves_returned_pointer"] is False


def test_eax_clobber_after_backend_call_breaks_ret_provenance(tmp_path):
    module = _load_module()
    instructions = _retail_instructions(module)
    insert_at = next(i for i, row in enumerate(instructions) if row["address"] == "0x00886916")
    instructions[insert_at - 1]["fallthrough"] = "0x00886914"
    instructions.insert(
        insert_at,
        _ins("0x00886914", "XOR", ["EAX", "EAX"], fallthrough="0x00886916", pcode=[_p("INT_XOR")]),
    )
    module, bridge, forwarding, backend, export = _fixture(tmp_path, instructions=instructions)
    report = module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)
    ret = next(row for row in report["exits"] if row["kind"] == "ret")
    assert ret["verified_backend_eax_origin"] is False
    assert ret["machine_exit_provenance_state"] == "ambiguous"
    assert report["all_reachable_helper_exits_backend_sourced"] is False
    assert any(row["id"] == "ret-eax-origin-not-uniquely-create-backend" for row in report["blockers"])


def test_unexpected_external_tail_target_stays_unknown(tmp_path):
    module = _load_module()
    instructions = _retail_instructions(module)
    tail = next(row for row in instructions if row["address"] == "0x0088691f")
    tail["operands"] = ["0x00777777"]
    tail["flows"] = ["0x00777777"]
    module, bridge, forwarding, backend, export = _fixture(tmp_path, instructions=instructions)
    report = module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)
    assert report["all_reachable_helper_exits_backend_sourced"] is False
    assert any(row["id"] == "external-tail-target-not-create-backend" for row in report["blockers"])


def test_forwarding_transfer_kind_drift_is_ambiguous(tmp_path):
    module, bridge, forwarding, backend, export = _fixture(tmp_path)
    payload = json.loads(forwarding.read_text(encoding="utf-8"))
    payload["wrappers"][0]["call_sites"][1]["transfer_kind"] = "call"
    _write_json(forwarding, payload)
    report = module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)
    tail = next(row for row in report["exits"] if row["kind"] == "tail-call")
    assert tail["machine_exit_provenance_state"] == "ambiguous"
    assert any(row["id"] == "tail-backend-forwarding-site-drift" for row in report["blockers"])


def test_unconfirmed_wrapper_forwarding_fails_closed(tmp_path):
    module, bridge, forwarding, backend, export = _fixture(tmp_path, forwarding_confirmed=False)
    with pytest.raises(ValueError, match="memory forwarding is not confirmed"):
        module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)


def test_missing_backend_evidence_fails_closed(tmp_path):
    module, bridge, forwarding, backend, export = _fixture(tmp_path)
    payload = json.loads(backend.read_text(encoding="utf-8"))
    payload["functions"] = [payload["functions"][0]]
    _write_json(backend, payload)
    with pytest.raises(ValueError, match="missing create backend"):
        module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)


def test_call_without_pcode_call_breaks_backend_origin(tmp_path):
    module = _load_module()
    instructions = _retail_instructions(module)
    call = next(row for row in instructions if row["address"] == "0x00886911")
    call["pcode"] = []
    module, bridge, forwarding, backend, export = _fixture(tmp_path, instructions=instructions)
    report = module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)
    ret = next(row for row in report["exits"] if row["kind"] == "ret")
    assert ret["verified_backend_eax_origin"] is False


def test_instruction_format_drift_fails_closed(tmp_path):
    module, bridge, forwarding, backend, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_vehicle_create_helper_return_provenance(bridge, forwarding, backend, export)
