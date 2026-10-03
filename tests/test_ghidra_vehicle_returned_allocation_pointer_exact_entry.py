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
        "vehicle_returned_pointer_exact_entry", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exact_target_entry_instruction_is_required(tmp_path):
    module = _load_module()
    target = "0x00639000"
    boundary = tmp_path / "boundary.json"
    boundary.write_text(
        json.dumps(
            {
                "format": module.BOUNDARY_FORMAT,
                "return_origin_targets": [target],
                "required_instruction_targets": [target],
                "returned_allocation_pointer_role_state": "unknown",
                "returned_allocation_pointer_role_proven": False,
                "vehicle_create_bridges": [
                    {
                        "descriptor": 2,
                        "returned_allocation_pointer_role_state": "unknown",
                    }
                ],
                "blockers": [module.EXPECTED_BLOCKER],
            }
        ),
        encoding="utf-8",
    )

    instructions = tmp_path / "instructions.jsonl"
    instructions.write_text(
        json.dumps(
            {
                "format": module.INSTRUCTION_FORMAT,
                "found": True,
                "requested": target,
                "function": {"address": target, "name": "FUN_00639000"},
                "instructions": [
                    {
                        "address": "0x00639005",
                        "mnemonic": "RET",
                        "operands": [],
                        "flows": [],
                        "fallthrough": None,
                        "pcode": [{"opcode": "RETURN"}],
                        "text": "RET",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exact function entry instruction missing"):
        module.analyze_vehicle_returned_allocation_pointer_return_provenance(
            boundary, instructions
        )
