import hashlib
import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_p1b_address_taken_function_recovery_batch2.py"
    )
    spec = importlib.util.spec_from_file_location("p1b_address_taken_function_recovery_batch2", path)
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


def test_validates_reachable_contiguous_body_and_pcode():
    module = _load_module()
    instructions = [
        {"address": "0x1000", "bytes": "7406", "mnemonic": "JZ", "flow_type": "CONDITIONAL_JUMP", "flows": ["0x1008"], "fallthrough": "0x1002", "pcode": [{}]},
        {"address": "0x1002", "bytes": "e8f90f0000", "mnemonic": "CALL", "flow_type": "UNCONDITIONAL_CALL", "flows": ["0x2000"], "fallthrough": "0x1007", "pcode": [{}]},
        {"address": "0x1007", "bytes": "90", "mnemonic": "NOP", "flow_type": "FALL_THROUGH", "flows": [], "fallthrough": "0x1008", "pcode": [{}]},
        {"address": "0x1008", "bytes": "c3", "mnemonic": "RET", "flow_type": "TERMINATOR", "flows": [], "fallthrough": None, "pcode": [{}]},
    ]
    body = bytes.fromhex("7406e8f90f000090c3")
    spec = {
        "entry": "0x1000",
        "end": "0x1008",
        "body_instruction_addresses": [row["address"] for row in instructions],
        "terminator": "RET",
        "terminal_target": None,
        "external_tail_transfers": [],
        "instruction_count": 4,
        "pcode_instruction_count": 4,
        "call_instruction_count": 1,
        "branch_instruction_count": 1,
        "body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
    }

    result = module.validate_body(
        spec,
        {row["address"]: row for row in instructions},
        {row["address"]: _metadata(row["address"]) for row in instructions},
    )

    assert result["instruction_count"] == 4
    assert result["pcode_instruction_count"] == 4
    assert result["call_instruction_count"] == 1
    assert result["branch_instruction_count"] == 1


def test_rejects_unreachable_body_instruction():
    module = _load_module()
    instructions = [
        {"address": "0x1000", "bytes": "c3", "mnemonic": "RET", "flow_type": "TERMINATOR", "flows": [], "pcode": [{}]},
        {"address": "0x1001", "bytes": "c3", "mnemonic": "RET", "flow_type": "TERMINATOR", "flows": [], "pcode": [{}]},
    ]
    spec = {
        "entry": "0x1000",
        "end": "0x1001",
        "body_instruction_addresses": [row["address"] for row in instructions],
        "terminator": "RET",
        "terminal_target": None,
        "external_tail_transfers": [],
        "instruction_count": 2,
        "pcode_instruction_count": 2,
        "call_instruction_count": 0,
        "branch_instruction_count": 0,
        "body_bytes": 2,
        "body_sha256": hashlib.sha256(bytes.fromhex("c3c3")).hexdigest(),
    }

    with pytest.raises(ValueError, match="unreachable instruction"):
        module.validate_body(
            spec,
            {row["address"]: row for row in instructions},
            {row["address"]: _metadata(row["address"]) for row in instructions},
        )


def test_verifies_boundary_padding_and_exact_call_owner():
    module = _load_module()
    spec = {
        "entry": "0x00001000",
        "boundary_gap_hex": "cc",
        "previous_instruction": {"address": "0x00000ffe", "bytes": "c3", "mnemonic": "RET", "flow_target": None},
    }
    previous = {"address": "0x00000ffe", "bytes": "c3", "mnemonic": "RET", "flow_type": "TERMINATOR", "flows": []}
    gap = _metadata("0x00000fff")
    gap["raw_u32"] = "0xcccccccc"
    assert module.verify_boundary(spec, {previous["address"]: previous}, {gap["requested"]: gap}) == previous

    result = module.verify_callsite(
        "0x00001002", "0x00002000", "0x00001000", "FUN_00001000",
        {"0x00001002": {"callsite": "0x00001002", "target_function": "0x00002000", "instruction": "CALL 0x00002000"}},
        {"0x00002000": {"references": [{"from": "0x00001002", "type": "UNCONDITIONAL_CALL", "instruction": "CALL 0x00002000"}]}},
        {"0x00002000": {"references": [{"from": "0x00001002", "type": "UNCONDITIONAL_CALL", "function_address": "0x00001000", "function_name": "FUN_00001000"}]}},
    )
    assert result["callsite"] == "0x00001002"
