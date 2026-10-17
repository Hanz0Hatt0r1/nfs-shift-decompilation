import hashlib
import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "ghidra"
        / "build_p1b_orphan_function_recovery_batch3.py"
    )
    spec = importlib.util.spec_from_file_location("p1b_orphan_function_recovery_batch3", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _instruction(address, data, flow, *, flows=(), fallthrough=None, mnemonic="NOP"):
    return {
        "address": address,
        "bytes": data,
        "mnemonic": mnemonic,
        "flow_type": flow,
        "flows": list(flows),
        "fallthrough": fallthrough,
        "pcode": [{"opcode": "COPY"}],
    }


def _metadata(address, *, raw="0x90909090", block=".text", owner=None, write=False):
    return {
        "requested": address,
        "function_at": owner,
        "function_containing": owner,
        "raw_u32": raw,
        "block": {"name": block, "execute": True, "write": write},
    }


def _simple_body():
    return [
        _instruction(
            "0x00001000", "7405", "CONDITIONAL_JUMP", flows=("0x00001007",),
            fallthrough="0x00001002", mnemonic="JZ",
        ),
        _instruction(
            "0x00001002", "e8f90f0000", "UNCONDITIONAL_CALL", flows=("0x00002000",),
            fallthrough="0x00001007", mnemonic="CALL",
        ),
        _instruction("0x00001007", "c3", "TERMINATOR", mnemonic="RET"),
    ]


def _spec(body, *, external="-"):
    encoded = b"".join(bytes.fromhex(row["bytes"]) for row in body)
    return {
        "entry": "0x00001000",
        "end": "0x00001007",
        "external_flows": external,
        "instruction_count": str(len(body)),
        "pcode_instruction_count": str(len(body)),
        "call_instruction_count": "1",
        "branch_instruction_count": "1",
        "body_bytes": str(len(encoded)),
        "body_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def test_validates_exact_reachable_body_and_callsite_reference():
    module = _load_module()
    body = _simple_body()
    facts = module.body_for(
        _spec(body),
        {row["address"]: row for row in body},
        {row["address"]: _metadata(row["address"]) for row in body},
    )
    orphan = {
        "callsite": "0x00001002",
        "target_function": "0x00002000",
        "instruction_bytes": "e8f90f0000",
        "instruction": "CALL 0x00002000",
    }
    calls = module.verify_orphan_callsites(
        {"callsites": "0x00001002>0x00002000"},
        facts,
        {"0x00001002": orphan},
        [{"from": "00001002", "to": "00002000", "type": "UNCONDITIONAL_CALL"}],
    )
    assert facts["instruction_count"] == 3
    assert facts["pcode_instruction_count"] == 3
    assert calls[0]["callsite"] == "0x00001002"


def test_rejects_undocumented_external_branch():
    module = _load_module()
    body = _simple_body()
    body[0]["flows"] = ["0x00002000"]
    with pytest.raises(ValueError, match="unrecorded external CFG edge"):
        module.body_for(
            _spec(body),
            {row["address"]: row for row in body},
            {row["address"]: _metadata(row["address"]) for row in body},
        )


def test_rejects_unreachable_body_instruction():
    module = _load_module()
    body = [
        _instruction("0x00001000", "c3", "TERMINATOR", mnemonic="RET"),
        _instruction("0x00001001", "c3", "TERMINATOR", mnemonic="RET"),
    ]
    encoded = bytes.fromhex("c3c3")
    spec = {
        "entry": "0x00001000", "end": "0x00001001", "external_flows": "-",
        "instruction_count": "2", "pcode_instruction_count": "2",
        "call_instruction_count": "0", "branch_instruction_count": "0",
        "body_bytes": "2", "body_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    with pytest.raises(ValueError, match="unreachable body instruction"):
        module.body_for(
            spec,
            {row["address"]: row for row in body},
            {row["address"]: _metadata(row["address"]) for row in body},
        )


def test_validates_terminal_boundary_padding():
    module = _load_module()
    previous = _instruction("0x00000ffe", "c3", "TERMINATOR", mnemonic="RET")
    spec = {
        "entry": "0x00001000", "previous_address": "0x00000ffe",
        "previous_bytes": "c3", "previous_mnemonic": "RET", "boundary_gap_hex": "cc",
    }
    metadata = {"0x00000fff": _metadata("0x00000fff", raw="0xcccccccc")}
    assert module.verify_boundary(spec, {previous["address"]: previous}, metadata) == previous


def test_validates_read_only_data_pointer_entry_evidence():
    module = _load_module()
    row = _metadata("0x00aa8660", raw="0x00a86ca0", block=".rdata")
    result = module.verify_entry_evidence(
        {
            "entry": "0x00a86ca0",
            "entry_evidence": "RAW_U32,0x00aa8660,0x00a86ca0",
        },
        {"0x00aa8660": row},
        [],
    )
    assert result[0]["kind"] == "RAW_U32"
    row["raw_u32"] = "0x00a86c90"
    with pytest.raises(ValueError, match="raw pointer value drift"):
        module.verify_entry_evidence(
            {"entry": "0x00a86ca0", "entry_evidence": "RAW_U32,0x00aa8660,0x00a86ca0"},
            {"0x00aa8660": row},
            [],
        )
