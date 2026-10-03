import importlib.util
import json
from pathlib import Path

import pytest


PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "ghidra"
    / "analyze_provider_dispatch_callsites.py"
)
SPEC = importlib.util.spec_from_file_location("analyze_provider_dispatch_callsites", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _instruction(address, text, operands, mnemonic="MOV", pcode=None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands,
        "pcode": pcode or [{"opcode": "COPY", "text": "tmp = tmp"}],
    }


def _call(address, register, slot, pcode_opcode="CALLIND"):
    operand = f"dword ptr [{register} + 0x{slot:x}]"
    return _instruction(
        address,
        f"CALL {operand}",
        [operand],
        mnemonic="CALL",
        pcode=[{"opcode": pcode_opcode, "text": f"{pcode_opcode} ({register})"}],
    )


def _row(function, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "found": True,
        "requested": f"0x{function:08x}",
        "function": {"address": f"0x{function:08x}", "name": f"FUN_{function:08x}"},
        "instructions": instructions,
    }


def _write_export(path, include_solve=True, solve_opcode="CALLIND"):
    rows = [
        _row(
            0x007B3820,
            [
                _instruction(
                    "0x007b3830",
                    "MOV EAX,dword ptr [ECX + 0x48]",
                    ["EAX", "dword ptr [ECX + 0x48]"],
                ),
                _call("0x007b3840", "EDX", 0x14),
            ],
        ),
        _row(
            0x007B2210,
            [
                _instruction(
                    "0x007b2220",
                    "MOV EAX,dword ptr [ECX + 0x48]",
                    ["EAX", "dword ptr [ECX + 0x48]"],
                ),
                _call("0x007b2230", "EDX", 0x1C),
            ],
        ),
        _row(
            0x007B3F40,
            [
                _call("0x007b3f60", "EAX", 0x20),
                _instruction("0x007b3f70", "MOV EAX,EAX", ["EAX", "EAX"]),
                *(
                    [_call("0x007b3f80", "EDX", 0x18, pcode_opcode=solve_opcode)]
                    if include_solve
                    else []
                ),
            ],
        ),
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_freezes_four_expected_indirect_slot_callsites(tmp_path):
    export = tmp_path / "provider.jsonl"
    _write_export(export)

    result = MODULE.analyze(export, context_before=2)

    assert result["ready"] is True
    assert result["callsite_count"] == 4
    assert result["blockers"] == []
    assert result["ambiguities"] == []
    assert [item["role"] for item in result["callsites"]] == [
        "acceptance",
        "per-scalar-reset",
        "cleanup",
        "solve",
    ]
    assert all(item["slot_evidence_state"] == "verified" for item in result["callsites"])
    assert all(item["provider_identity_state"] == "unknown" for item in result["callsites"])


def test_missing_expected_callsite_fails_closed(tmp_path):
    export = tmp_path / "provider.jsonl"
    _write_export(export, include_solve=False)

    result = MODULE.analyze(export)

    assert result["ready"] is False
    assert result["callsite_count"] == 3
    assert result["blockers"] == [
        {
            "function": "0x007b3f40",
            "vtable_slot": "0x18",
            "role": "solve",
            "state": "unknown",
            "reason": "expected indirect CALL not found in targeted instruction export",
        }
    ]


def test_missing_function_export_is_rejected(tmp_path):
    export = tmp_path / "provider.jsonl"
    rows = [
        _row(0x007B3820, [_call("0x007b3840", "EDX", 0x14)]),
        _row(0x007B2210, [_call("0x007b2230", "EDX", 0x1C)]),
    ]
    export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required function export"):
        MODULE.analyze(export)


def test_duplicate_same_slot_is_ambiguous(tmp_path):
    export = tmp_path / "provider.jsonl"
    _write_export(export)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    rows[-1]["instructions"].append(_call("0x007b3f90", "ECX", 0x18))
    export.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    result = MODULE.analyze(export)

    assert result["ready"] is False
    assert result["ambiguities"][0]["state"] == "ambiguous"
    assert result["ambiguities"][0]["vtable_slot"] == "0x18"


def test_memory_call_without_callind_pcode_is_blocked(tmp_path):
    export = tmp_path / "provider.jsonl"
    _write_export(export, solve_opcode="CALL")

    result = MODULE.analyze(export)

    assert result["ready"] is False
    assert result["callsite_count"] == 3
    assert any(
        blocker.get("reason") == "memory CALL lacks CALLIND p-code"
        and blocker.get("vtable_slot") == "0x18"
        for blocker in result["blockers"]
    )
