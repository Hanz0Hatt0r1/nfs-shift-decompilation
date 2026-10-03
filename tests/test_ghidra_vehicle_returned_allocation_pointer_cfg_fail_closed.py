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
        / "analyze_vehicle_returned_allocation_pointer_return_provenance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "vehicle_returned_pointer_cfg_fail_closed", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _boundary(path, module, target="0x00639000"):
    path.write_text(
        json.dumps(
            {
                "format": module.BOUNDARY_FORMAT,
                "return_origin_targets": [target],
                "required_instruction_targets": [target],
                "returned_allocation_pointer_role_state": "unknown",
                "returned_allocation_pointer_role_proven": False,
                "vehicle_create_bridges": [{"descriptor": 2}],
                "blockers": [module.EXPECTED_BLOCKER],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_row(path, module, target, instructions, requested=None):
    path.write_text(
        json.dumps(
            {
                "format": module.INSTRUCTION_FORMAT,
                "found": True,
                "requested": requested or target,
                "function": {"address": target, "name": "FUN_00639000"},
                "instructions": instructions,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _ins(address, mnemonic, *, flows=None, fallthrough=None, pcode=None, operands=None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands or [],
        "flows": flows or [],
        "fallthrough": fallthrough,
        "pcode": [{"opcode": opcode} for opcode in (pcode or [])],
        "text": mnemonic,
    }


def test_malformed_flow_target_is_rejected(tmp_path):
    module = _load_module()
    target = "0x00639000"
    boundary = _boundary(tmp_path / "boundary.json", module, target)
    instructions = _write_row(
        tmp_path / "instructions.jsonl",
        module,
        target,
        [
            _ins(
                target,
                "CALL",
                flows=["not-an-address"],
                fallthrough="0x00639005",
                pcode=["CALL"],
            ),
            _ins("0x00639005", "RET", pcode=["RETURN"]),
        ],
    )

    with pytest.raises(ValueError, match="invalid flow target"):
        module.analyze_vehicle_returned_allocation_pointer_return_provenance(
            boundary, instructions
        )


def test_requested_function_identity_drift_is_rejected(tmp_path):
    module = _load_module()
    target = "0x00639000"
    boundary = _boundary(tmp_path / "boundary.json", module, target)
    instructions = _write_row(
        tmp_path / "instructions.jsonl",
        module,
        target,
        [_ins(target, "RET", pcode=["RETURN"])],
        requested="0x0063a000",
    )

    with pytest.raises(ValueError, match="requested/function identity drift"):
        module.analyze_vehicle_returned_allocation_pointer_return_provenance(
            boundary, instructions
        )


def test_internal_jmp_without_branch_pcode_cannot_emit_next_frontier(tmp_path):
    module = _load_module()
    target = "0x00639000"
    boundary = _boundary(tmp_path / "boundary.json", module, target)
    instructions = _write_row(
        tmp_path / "instructions.jsonl",
        module,
        target,
        [
            _ins(
                target,
                "JMP",
                flows=["0x00639005"],
                pcode=["COPY"],
            ),
            _ins(
                "0x00639005",
                "CALL",
                flows=["0x00650000"],
                fallthrough="0x0063900a",
                pcode=["CALL"],
                operands=["FUN_00650000"],
            ),
            _ins("0x0063900a", "RET", pcode=["RETURN"]),
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    assert report["next_return_origin_targets"] == []
    assert report["targets"][0]["next_return_origin_targets"] == []
    assert {row["id"] for row in report["targets"][0]["blockers"]} == {
        "jmp-pcode-branch-missing"
    }


def test_ret_pcode_blocker_clears_otherwise_verified_call_frontier(tmp_path):
    module = _load_module()
    target = "0x00639000"
    boundary = _boundary(tmp_path / "boundary.json", module, target)
    instructions = _write_row(
        tmp_path / "instructions.jsonl",
        module,
        target,
        [
            _ins(
                target,
                "CALL",
                flows=["0x00650000"],
                fallthrough="0x00639005",
                pcode=["CALL"],
                operands=["FUN_00650000"],
            ),
            _ins("0x00639005", "RET", pcode=["COPY"]),
        ],
    )

    report = module.analyze_vehicle_returned_allocation_pointer_return_provenance(
        boundary, instructions
    )

    assert report["all_target_machine_return_origins_resolved"] is False
    assert report["next_return_origin_targets"] == []
    assert report["targets"][0]["next_return_origin_targets"] == []
    assert {row["id"] for row in report["targets"][0]["blockers"]} == {
        "ret-pcode-return-missing"
    }
