from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_outer_vehicle_owner_candidate_roles.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_owner_roles", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _ins(address: str, text: str, *, mnemonic: str | None = None, flows: list[str] | None = None, operands: list[str] | None = None) -> dict:
    if mnemonic is None:
        mnemonic = text.split()[0]
    if operands is None:
        operands = []
    return {
        "address": address,
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands,
        "flows": [] if flows is None else flows,
        "pcode": [],
    }


def _call(address: str, target: str) -> dict:
    return _ins(address, f"CALL {target}", mnemonic="CALL", flows=[target], operands=[target])


def _indirect_call(address: str, register: str) -> dict:
    return _ins(address, f"CALL {register}", mnemonic="CALL", operands=[register])


def _pad(rows: list[dict], count: int, base: int) -> list[dict]:
    used = {int(row["address"], 16) for row in rows}
    cursor = base
    while len(rows) < count:
        if cursor not in used:
            rows.append(_ins(f"0x{cursor:08x}", "NOP", mnemonic="NOP"))
            used.add(cursor)
        cursor += 1
    return sorted(rows, key=lambda row: int(row["address"], 16))


def _leaf() -> list[dict]:
    return _pad(
        [
            _ins("0x007876e0", "MOV EAX,dword ptr [ECX + 0x1b0]"),
            _ins("0x007876e5", "MOV EDX,dword ptr [ECX + 0xb14]"),
            _ins("0x007876ea", "MOV EDX,dword ptr [ECX + 0xb20]"),
            _ins("0x007876ef", "MOV EDX,dword ptr [ECX + 0x8a4]"),
            _ins("0x007876f4", "MOV EDX,dword ptr [ECX + 0x8b0]"),
        ],
        MODULE.EXPECTED_COUNTS[MODULE.LEAF],
        0x00787700,
    )


def _forwarder() -> list[dict]:
    return _pad(
        [
            _ins("0x007afb60", "PUSH EBP"),
            _ins("0x007afb61", "MOV EBP,ESP", operands=["EBP", "ESP"]),
            _call("0x007afb6c", MODULE.FORWARDED_HELPER),
        ],
        MODULE.EXPECTED_COUNTS[MODULE.FORWARDER],
        0x007afb70,
    )


def _control() -> list[dict]:
    return _pad(
        [
            _ins("0x007633d1", "MOV ESI,ECX", operands=["ESI", "ECX"]),
            _ins("0x007634d1", "MOV EDX,dword ptr [ESI + 0x3fe8]", operands=["EDX", "dword ptr [ESI + 0x3fe8]"]),
            _ins("0x007634d7", "MOV ECX,dword ptr [EDX]", operands=["ECX", "dword ptr [EDX]"]),
            _ins("0x007634d9", "ADD ECX,0x340", operands=["ECX", "0x340"]),
            _call("0x007634df", MODULE.POST_TRANSFORM),
        ],
        MODULE.EXPECTED_COUNTS[MODULE.HDVEHICLE_CONTROL],
        0x007633b0,
    )


def _post_transform() -> list[dict]:
    return _pad(
        [
            _ins("0x007ac2fc", "MOV ESI,ECX", operands=["ESI", "ECX"]),
            _ins("0x007ac302", "MOV EDI,dword ptr [ESI + 0x34]", operands=["EDI", "dword ptr [ESI + 0x34]"]),
            _call("0x007ac35b", "0x007abbc0"),
            _call("0x007ac39f", "0x007aa440"),
            _call("0x007ac3cf", "0x007ab4e0"),
            _ins("0x007ac3d4", "MOV EDX,dword ptr [EDI]", operands=["EDX", "dword ptr [EDI]"]),
            _ins("0x007ac3d6", "MOV EDX,dword ptr [EDX + 0xe0]", operands=["EDX", "dword ptr [EDX + 0xe0]"]),
            _indirect_call("0x007ac3e2", "EDX"),
            _ins("0x007ac3e4", "MOV EAX,dword ptr [EDI]", operands=["EAX", "dword ptr [EDI]"]),
            _ins("0x007ac3e6", "MOV EDX,dword ptr [EAX + 0xe4]", operands=["EDX", "dword ptr [EAX + 0xe4]"]),
            _indirect_call("0x007ac3f2", "EDX"),
            _ins("0x007ac3f4", "LEA ECX,[ESI + 0x534]", operands=["ECX", "[ESI + 0x534]"]),
            _call("0x007ac3fa", "0x007a4360"),
        ],
        MODULE.EXPECTED_COUNTS[MODULE.POST_TRANSFORM],
        0x007ac310,
    )


def _write_export(path: Path, *, mutate=None) -> None:
    all_rows = {
        MODULE.LEAF: _leaf(),
        MODULE.FORWARDER: _forwarder(),
        MODULE.POST_TRANSFORM: _post_transform(),
        MODULE.HDVEHICLE_CONTROL: _control(),
    }
    if mutate is not None:
        mutate(all_rows)
    with path.open("w", encoding="utf-8") as f:
        for address in MODULE.REQUIRED:
            instructions = all_rows[address]
            f.write(
                json.dumps(
                    {
                        "format": MODULE.INSTRUCTION_FORMAT,
                        "program": "SHIFT.exe",
                        "requested": address,
                        "found": True,
                        "function": {
                            "address": address,
                            "name": MODULE.EXPECTED_NAMES[address],
                            "size": 1,
                            "calling_convention": "__thiscall",
                        },
                        "instruction_count": len(instructions),
                        "instructions": instructions,
                    }
                )
                + "\n"
            )


def test_narrows_owner_candidates_without_claiming_frame_identity(tmp_path: Path):
    path = tmp_path / "owners.jsonl"
    _write_export(path)
    report = MODULE.analyze(path)

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    roles = {row["function"]: row for row in report["roles"]}
    assert roles[MODULE.LEAF]["excluded_from_next_owner_join"] is True
    assert roles[MODULE.FORWARDER]["entry_receiver_forwarded_unchanged"] is True
    assert roles[MODULE.FORWARDER]["next_owner_join_target"] == MODULE.FORWARDED_HELPER
    assert roles[MODULE.HDVEHICLE_CONTROL]["nested_receiver_expression"] == "*(*(HDVehicle_control+0x3fe8))+0x340"
    assert roles[MODULE.POST_TRANSFORM]["interface_pointer_field"] == "+0x34"
    assert roles[MODULE.POST_TRANSFORM]["interface_virtual_slots_called"] == ["+0xe0", "+0xe4"]
    assert roles[MODULE.POST_TRANSFORM]["embedded_subobject_offset"] == "+0x534"
    assert report["next_static_export"]["functions"] == [
        MODULE.HDVEHICLE_INIT,
        MODULE.CHASSIS_INIT,
        MODULE.FORWARDED_HELPER,
    ]
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["callgraph_adjacency_promoted_to_frame_identity"] is False
    assert report["scope"]["plus_0x340_pattern_promoted_to_object_identity"] is False


def test_rejects_changed_nested_0x340_chain(tmp_path: Path):
    path = tmp_path / "owners.jsonl"

    def mutate(rows):
        for ins in rows[MODULE.HDVEHICLE_CONTROL]:
            if ins["address"] == "0x007634d9":
                ins["text"] = "ADD ECX,0x344"
                ins["operands"] = ["ECX", "0x344"]

    _write_export(path, mutate=mutate)
    with pytest.raises(ValueError, match="0x340"):
        MODULE.analyze(path)


def test_rejects_extra_forwarder_call(tmp_path: Path):
    path = tmp_path / "owners.jsonl"

    def mutate(rows):
        for index, ins in enumerate(rows[MODULE.FORWARDER]):
            if ins["mnemonic"] == "NOP":
                rows[MODULE.FORWARDER][index] = _call(ins["address"], "0x00700000")
                break

    _write_export(path, mutate=mutate)
    with pytest.raises(ValueError, match="direct-call inventory drift"):
        MODULE.analyze(path)
