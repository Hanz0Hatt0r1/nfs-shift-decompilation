import hashlib
import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_p1b_address_taken_function_recovery.py"
    )
    spec = importlib.util.spec_from_file_location("p1b_address_taken_function_recovery", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _metadata(address):
    return {
        "requested": address,
        "function_at": None,
        "function_containing": None,
        "block": {"name": ".text", "execute": True},
    }


def test_validates_contiguous_unowned_body_with_pcode():
    module = _load_module()
    instructions = [
        {"address": "0x1000", "bytes": "55", "mnemonic": "PUSH", "flow_type": "FALL_THROUGH", "flows": [], "pcode": [{}]},
        {"address": "0x1001", "bytes": "c3", "mnemonic": "RET", "flow_type": "TERMINATOR", "flows": [], "pcode": [{}]},
    ]
    spec = {
        "entry": "0x1000",
        "end": "0x1001",
        "terminator": "RET",
        "tail_target": None,
        "instruction_count": 2,
        "call_instruction_count": 0,
        "body_bytes": 2,
        "body_sha256": hashlib.sha256(bytes.fromhex("55c3")).hexdigest(),
    }

    result = module.validate_body(
        spec,
        module.instruction_index([{"instructions": instructions}]),
        {"0x1000": _metadata("0x1000"), "0x1001": _metadata("0x1001")},
    )

    assert result["instruction_count"] == 2
    assert result["pcode_instruction_count"] == 2
    assert result["body_bytes"] == 2


def test_rejects_body_branching_outside_its_bounds():
    module = _load_module()
    instruction = {
        "address": "0x1000",
        "bytes": "e9fb0f0000",
        "mnemonic": "JMP",
        "flow_type": "UNCONDITIONAL_JUMP",
        "flows": ["0x2000"],
        "pcode": [{}],
    }
    spec = {
        "entry": "0x1000",
        "end": "0x1000",
        "terminator": "JMP",
        "tail_target": None,
        "instruction_count": 1,
        "call_instruction_count": 0,
        "body_bytes": 5,
        "body_sha256": hashlib.sha256(bytes.fromhex(instruction["bytes"])).hexdigest(),
    }

    with pytest.raises(ValueError, match="branch leaves bounded body"):
        module.validate_body(
            spec,
            module.instruction_index([{"instructions": [instruction]}]),
            {"0x1000": _metadata("0x1000")},
        )


def test_requires_every_exact_address_taken_reference():
    module = _load_module()
    spec = {"entry": "0x1000", "entry_data_reference_sources": ["0x2000", "0x3000"]}

    with pytest.raises(ValueError, match="missing exact address-taken data reference"):
        module.verify_entry_reference(
            spec,
            {"references": [{"from": "0x2000", "type": "DATA"}]},
        )
