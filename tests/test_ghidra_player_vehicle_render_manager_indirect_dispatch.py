from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_indirect_dispatch.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_render_manager_indirect_dispatch", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _direct_negative() -> dict:
    return {
        "format": m.DIRECT_CA4_FORMAT,
        "ready": False,
        "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
        "provenance": {
            "targeted_direct_callee_count": 17,
            "exact_entry_pointer_ca4_access_count": 0,
            "exact_entry_pointer_ca4_read_count": 0,
        },
        "handoff": {"player_vehicle_renderables_field_runtime_access_ready": False},
    }


def _frontier() -> dict:
    transfers = [
        {
            "function": "0x0056bcd0",
            "instruction": "0x0056bcf2",
            "instruction_text": "CALL EDX",
            "call_operand": "EDX",
            "source_register": "ECX",
            "kind": "indirect-call-manager-receiver-transfer",
            "manager_receiver_identity_proven": True,
        },
        {
            "function": "0x0056bcd0",
            "instruction": "0x0056bd09",
            "instruction_text": "CALL EDX",
            "call_operand": "EDX",
            "source_register": "ECX",
            "kind": "indirect-call-manager-receiver-transfer",
            "manager_receiver_identity_proven": True,
        },
        {
            "function": "0x0056bd30",
            "instruction": "0x0056bd59",
            "instruction_text": "CALL EDX",
            "call_operand": "EDX",
            "source_register": "ECX",
            "kind": "indirect-call-manager-receiver-transfer",
            "manager_receiver_identity_proven": True,
        },
    ]
    dereferences = [
        {
            "function": "0x0056bcd0",
            "instruction": "0x0056bceb",
            "instruction_text": "MOV EAX,dword ptr [ESI]",
            "base_register": "ESI",
            "displacement": 0,
            "kind": "manager-pointer-dereference",
        },
        {
            "function": "0x0056bcd0",
            "instruction": "0x0056bd00",
            "instruction_text": "MOV EAX,dword ptr [ESI]",
            "base_register": "ESI",
            "displacement": 0,
            "kind": "manager-pointer-dereference",
        },
        {
            "function": "0x0056bd30",
            "instruction": "0x0056bd54",
            "instruction_text": "MOV EAX,dword ptr [ECX]",
            "base_register": "ECX",
            "displacement": 0,
            "kind": "manager-pointer-dereference",
        },
    ]
    return {
        "format": m.FRONTIER_FORMAT,
        "ready": True,
        "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
        "handoff": {"candidate_global_manager_indirect_dispatch_frontier_ready": True},
        "provenance": {"indirect_call_receiver_transfer_count": 3},
        "analysis": {"call_receiver_transfers": transfers, "all_sinks": dereferences},
    }


def _ins(address: str, mnemonic: str, operands: list[str]) -> dict:
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
        "text": mnemonic + (" " + ",".join(operands) if operands else ""),
        "pcode": [],
        "flows": [],
    }


def _instruction_row(function: str, instructions: list[dict]) -> dict:
    return {
        "format": m.INSTRUCTION_FORMAT,
        "program": m.PROGRAM,
        "requested": function,
        "found": True,
        "function": {"address": function, "name": f"FUN_{function[2:]}"},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _constructor_rows(primary: str = "0xab5644") -> list[dict]:
    writer = _instruction_row(
        m.WRITER,
        [_ins("0x00d36210", "PUSH", ["EBP"]), _ins("0x00d36211", "RET", [])],
    )
    constructor = _instruction_row(
        m.CONSTRUCTOR,
        [
            _ins(m.CTOR_RECEIVER_SAVE, "MOV", ["ESI", "ECX"]),
            _ins(m.CTOR_PRIMARY_TABLE_STORE, "MOV", ["dword ptr [ESI]", primary]),
            _ins("0x0045ef7e", "RET", []),
        ],
    )
    return [writer, constructor]


def _caller_rows(*, wrong_slot_base: bool = False, branch_inside: bool = False) -> list[dict]:
    first_slot = "dword ptr [EBX + 0x8]" if wrong_slot_base else "dword ptr [EAX + 0x8]"
    first_middle = [_ins("0x0056bcee", "JZ", ["0x0056bcf2"])] if branch_inside else []
    bcd0 = _instruction_row(
        "0x0056bcd0",
        [
            _ins("0x0056bce1", "MOV", ["ESI", "dword ptr [0x00bc185c]"]),
            _ins("0x0056bceb", "MOV", ["EAX", "dword ptr [ESI]"]),
            *first_middle,
            _ins("0x0056bcef", "MOV", ["EDX", first_slot]),
            _ins("0x0056bcf1", "MOV", ["ECX", "ESI"]),
            _ins("0x0056bcf2", "CALL", ["EDX"]),
            _ins("0x0056bd00", "MOV", ["EAX", "dword ptr [ESI]"]),
            _ins("0x0056bd03", "MOV", ["EDX", "dword ptr [EAX + 0xc]"]),
            _ins("0x0056bd06", "MOV", ["ECX", "ESI"]),
            _ins("0x0056bd09", "CALL", ["EDX"]),
            _ins("0x0056bd0b", "RET", []),
        ],
    )
    bd30 = _instruction_row(
        "0x0056bd30",
        [
            _ins("0x0056bd3c", "MOV", ["ECX", "dword ptr [0x00bc185c]"]),
            _ins("0x0056bd54", "MOV", ["EAX", "dword ptr [ECX]"]),
            _ins("0x0056bd56", "MOV", ["EDX", "dword ptr [EAX + 0x10]"]),
            _ins("0x0056bd59", "CALL", ["EDX"]),
            _ins("0x0056bd5b", "RET", []),
        ],
    )
    return [bcd0, bd30]


def _static_rows(*, omit_last: bool = False) -> list[dict]:
    targets = [
        (m.PRIMARY_TABLE + 0x8, 0x00411110),
        (m.PRIMARY_TABLE + 0xC, 0x00422220),
        (m.PRIMARY_TABLE + 0x10, 0x00433330),
    ]
    if omit_last:
        targets.pop()
    rows = []
    for address, target in targets:
        rows.append(
            {
                "address": f"0x{address:08x}",
                "block": ".rdata",
                "data_type": "undefined *",
                "length": 4,
                "components": 0,
                "raw_hex": target.to_bytes(4, "little").hex(),
                "raw_truncated": False,
            }
        )
    return rows


def _paths(tmp_path: Path, *, direct=None, frontier=None, constructor=None, callers=None, static=None):
    direct_path = tmp_path / "direct.json"
    frontier_path = tmp_path / "frontier.json"
    constructor_path = tmp_path / "constructor.jsonl"
    static_path = tmp_path / "static.jsonl"
    callers_path = tmp_path / "callers.jsonl"
    _write_json(direct_path, direct if direct is not None else _direct_negative())
    _write_json(frontier_path, frontier if frontier is not None else _frontier())
    _write_jsonl(constructor_path, constructor if constructor is not None else _constructor_rows())
    _write_jsonl(static_path, static if static is not None else _static_rows())
    _write_jsonl(callers_path, callers if callers is not None else _caller_rows())
    return direct_path, frontier_path, constructor_path, static_path, callers_path


def test_resolves_three_frozen_indirect_dispatches(tmp_path: Path) -> None:
    report = m.analyze(*_paths(tmp_path))
    assert report["ready"] is True
    assert report["status"] == "indirect-manager-method-worklist-ready"
    assert report["provenance"]["resolved_indirect_call_count"] == 3
    resolved = report["analysis"]["resolved_indirect_calls"]
    assert [item["slot_index"] for item in resolved] == [2, 3, 4]
    assert report["targeted_instruction_worklist"]["functions"] == [
        "0x00411110",
        "0x00422220",
        "0x00433330",
    ]
    assert report["handoff"]["candidate_global_manager_indirect_dispatch_resolved"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is False


def test_rejects_non_negative_direct_branch(tmp_path: Path) -> None:
    direct = _direct_negative()
    direct["ready"] = True
    with pytest.raises(ValueError, match="direct \+0xca4 branch is not negative"):
        m.analyze(*_paths(tmp_path, direct=direct))


def test_rejects_constructor_primary_table_drift(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="constructor primary table drift"):
        m.analyze(*_paths(tmp_path, constructor=_constructor_rows("0xab5000")))


def test_rejects_slot_load_from_unproven_base(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="EDX is not loaded from the proven primary-table register EAX"):
        m.analyze(*_paths(tmp_path, callers=_caller_rows(wrong_slot_base=True)))


def test_rejects_control_flow_inside_dispatch_window(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="control-flow boundary inside dispatch window"):
        m.analyze(*_paths(tmp_path, callers=_caller_rows(branch_inside=True)))


def test_rejects_missing_static_slot_pointer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="static pointer missing"):
        m.analyze(*_paths(tmp_path, static=_static_rows(omit_last=True)))


def test_rejects_caller_target_set_drift(tmp_path: Path) -> None:
    callers = _caller_rows()[:1]
    with pytest.raises(ValueError, match="target set drift"):
        m.analyze(*_paths(tmp_path, callers=callers))
