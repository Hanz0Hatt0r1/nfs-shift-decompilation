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
        / "analyze_vehicle_returned_allocation_pointer_target_returns.py"
    )
    spec = importlib.util.spec_from_file_location("vehicle_returned_pointer_target_returns", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def _row(module, address, instructions):
    return {
        "format": module.INSTRUCTION_FORMAT,
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": f"FUN_{address[2:]}",
            "size": len(instructions) * 4,
            "calling_convention": "__fastcall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")
    return path


def _boundary(module, targets=None):
    targets = ["0x00639000", "0x0063a000"] if targets is None else targets
    return {
        "format": module.BOUNDARY_FORMAT,
        "required_instruction_targets": targets,
        "return_origin_targets": targets,
        "returned_allocation_pointer_role_state": "unknown",
        "returned_allocation_pointer_role_proven": False,
        "vehicle_create_bridges": [
            {
                "descriptor": 2,
                "vehicle_pointer_source_node": "memory-source:0x00715700:0x00715730:ESI:64",
                "allocation_request_value": 56,
                "returned_allocation_pointer_role_state": "unknown",
            }
        ],
        "blockers": [module.EXPECTED_BLOCKER],
    }


def _default_first(module):
    return [
        _ins(
            "0x00639000",
            "CALL",
            ["0x00639100"],
            fallthrough="0x00639005",
            flows=["0x00639100"],
            pcode=[_p("CALL")],
        ),
        _ins("0x00639005", "RET", pcode=[_p("RETURN")]),
    ]


def _default_second(module):
    return [
        _ins(
            "0x0063a000",
            "JMP",
            ["0x0063b000"],
            flows=["0x0063b000"],
            pcode=[_p("BRANCH")],
        )
    ]


def _fixture(tmp_path, *, first=None, second=None, targets=None):
    module = _load_module()
    targets = ["0x00639000", "0x0063a000"] if targets is None else targets
    boundary = _write_json(tmp_path / "boundary.json", _boundary(module, targets))
    rows = []
    for target in targets:
        if target == "0x00639000":
            instructions = first if first is not None else _default_first(module)
        elif target == "0x0063a000":
            instructions = second if second is not None else _default_second(module)
        else:
            instructions = [_ins(target, "RET", pcode=[_p("RETURN")])]
        rows.append(_row(module, target, instructions))
    export = _write_jsonl(tmp_path / "instructions.jsonl", rows)
    return module, boundary, export


def test_exact_call_result_and_tail_transfer_produce_next_finite_frontier(tmp_path):
    module, boundary, export = _fixture(tmp_path)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(
        boundary, export
    )

    assert report["format"] == "SHIFT.VehicleReturnedAllocationPointerTargetReturnAudit/1"
    assert report["target_count"] == 2
    assert report["verified_target_return_origin_count"] == 2
    assert report["all_target_machine_return_origins_resolved"] is True
    assert report["next_instruction_targets"] == ["0x00639100", "0x0063b000"]
    assert report["return_origin_cycles"] == []
    assert report["returned_allocation_pointer_role_proven"] is False

    first = report["targets"][0]
    assert first["exits"][0]["unique_eax_origin"] == {
        "kind": "direct-call-result",
        "target": "0x00639100",
        "instruction": "0x00639000",
        "detail": None,
    }
    second = report["targets"][1]
    assert second["exits"][0]["target"] == "0x0063b000"

    joined = report["vehicle_create_bridges"][0]
    assert joined["vehicle_pointer_source_node"] == "memory-source:0x00715700:0x00715730:ESI:64"
    assert joined["returned_pointer_target_return_audit_state"] == "verified"
    assert joined["returned_pointer_next_instruction_targets"] == ["0x00639100", "0x0063b000"]
    assert joined["returned_allocation_pointer_role_proven"] is False


def test_terminal_constant_is_machine_resolved_but_not_semantic_proof(tmp_path):
    module = _load_module()
    first = [
        _ins(
            "0x00639000",
            "XOR",
            ["EAX", "EAX"],
            fallthrough="0x00639002",
            pcode=[_p("INT_XOR")],
        ),
        _ins("0x00639002", "RET", pcode=[_p("RETURN")]),
    ]
    module, boundary, export = _fixture(tmp_path, first=first)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    first_row = report["targets"][0]
    assert first_row["machine_return_origins_resolved"] is True
    assert first_row["terminal_machine_origins"] == [
        {
            "kind": "constant",
            "target": None,
            "instruction": "0x00639000",
            "detail": "0x0",
        }
    ]
    assert "0x00639100" not in report["next_instruction_targets"]
    assert report["returned_allocation_pointer_role_state"] == "unknown"


def test_cfg_merge_with_two_call_results_is_ambiguous(tmp_path):
    module = _load_module()
    first = [
        _ins(
            "0x00639000",
            "JZ",
            ["0x00639020"],
            fallthrough="0x00639005",
            flows=["0x00639020"],
            pcode=[_p("CBRANCH")],
        ),
        _ins(
            "0x00639005",
            "CALL",
            ["0x00639100"],
            fallthrough="0x00639030",
            flows=["0x00639100"],
            pcode=[_p("CALL")],
        ),
        _ins(
            "0x00639020",
            "CALL",
            ["0x00639200"],
            fallthrough="0x00639030",
            flows=["0x00639200"],
            pcode=[_p("CALL")],
        ),
        _ins("0x00639030", "RET", pcode=[_p("RETURN")]),
    ]
    module, boundary, export = _fixture(tmp_path, first=first)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    first_row = report["targets"][0]
    assert first_row["machine_return_origins_resolved"] is False
    assert first_row["exits"][0]["machine_return_origin_state"] == "ambiguous"
    assert len(first_row["exits"][0]["eax_origins"]) == 2
    assert report["all_target_machine_return_origins_resolved"] is False


def test_partial_eax_write_after_call_is_ambiguous(tmp_path):
    module = _load_module()
    first = [
        _ins(
            "0x00639000",
            "CALL",
            ["0x00639100"],
            fallthrough="0x00639005",
            flows=["0x00639100"],
            pcode=[_p("CALL")],
        ),
        _ins(
            "0x00639005",
            "MOV",
            ["AL", "1"],
            fallthrough="0x00639007",
            pcode=[_p("COPY")],
        ),
        _ins("0x00639007", "RET", pcode=[_p("RETURN")]),
    ]
    module, boundary, export = _fixture(tmp_path, first=first)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    origin = report["targets"][0]["exits"][0]["unique_eax_origin"]
    assert origin["kind"] == "partial-eax-write"
    assert report["targets"][0]["machine_return_origins_resolved"] is False


def test_missing_call_pcode_breaks_direct_call_origin(tmp_path):
    module = _load_module()
    first = [
        _ins(
            "0x00639000",
            "CALL",
            ["0x00639100"],
            fallthrough="0x00639005",
            flows=["0x00639100"],
            pcode=[],
        ),
        _ins("0x00639005", "RET", pcode=[_p("RETURN")]),
    ]
    module, boundary, export = _fixture(tmp_path, first=first)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    origin = report["targets"][0]["exits"][0]["unique_eax_origin"]
    assert origin["kind"] == "ambiguous-call-result"
    assert report["targets"][0]["machine_return_origins_resolved"] is False


def test_return_origin_cycle_to_current_target_is_explicit_blocker(tmp_path):
    module = _load_module()
    first = [
        _ins(
            "0x00639000",
            "CALL",
            ["0x0063a000"],
            fallthrough="0x00639005",
            flows=["0x0063a000"],
            pcode=[_p("CALL")],
        ),
        _ins("0x00639005", "RET", pcode=[_p("RETURN")]),
    ]
    second = [
        _ins(
            "0x0063a000",
            "JMP",
            ["0x00639000"],
            flows=["0x00639000"],
            pcode=[_p("BRANCH")],
        )
    ]
    module, boundary, export = _fixture(tmp_path, first=first, second=second)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    assert report["return_origin_cycles"] == ["0x00639000", "0x0063a000"]
    assert report["all_target_machine_return_origins_resolved"] is False
    assert sum(row["id"] == "return-origin-cycle-to-current-target" for row in report["blockers"]) == 2


def test_export_must_match_exact_boundary_target_set(tmp_path):
    module, boundary, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    _write_jsonl(export, rows[:1])
    with pytest.raises(ValueError, match="missing boundary target"):
        module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)

    rows.append(
        _row(module, "0x0063c000", [_ins("0x0063c000", "RET", pcode=[_p("RETURN")])])
    )
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="non-boundary target"):
        module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)


def test_boundary_cannot_preclaim_allocated_pointer_semantics(tmp_path):
    module, boundary, export = _fixture(tmp_path)
    payload = json.loads(boundary.read_text(encoding="utf-8"))
    payload["returned_allocation_pointer_role_state"] = "verified"
    payload["returned_allocation_pointer_role_proven"] = True
    boundary.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="must be unknown"):
        module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)


def test_instruction_format_drift_fails_closed(tmp_path):
    module, boundary, export = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[0]["format"] = "SHIFT.GhidraFunctionInstructions/1"
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="SHIFT.GhidraFunctionInstructions/2"):
        module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)


def test_no_further_targets_is_explicit_nonsemantic_terminal_boundary(tmp_path):
    module = _load_module()
    first = [
        _ins("0x00639000", "MOV", ["EAX", "ECX"], fallthrough="0x00639002", pcode=[_p("COPY")]),
        _ins("0x00639002", "RET", pcode=[_p("RETURN")]),
    ]
    second = [
        _ins("0x0063a000", "XOR", ["EAX", "EAX"], fallthrough="0x0063a002", pcode=[_p("INT_XOR")]),
        _ins("0x0063a002", "RET", pcode=[_p("RETURN")]),
    ]
    module, boundary, export = _fixture(tmp_path, first=first, second=second)
    report = module.analyze_vehicle_returned_allocation_pointer_target_returns(boundary, export)
    assert report["all_target_machine_return_origins_resolved"] is True
    assert report["next_instruction_targets"] == []
    assert any(row["id"] == "no-further-call-or-tail-targets" for row in report["blockers"])
    assert report["returned_allocation_pointer_role_proven"] is False
