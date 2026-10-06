import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_bmanager_dispatch_slice.py"
RUNNER = ROOT / "tools/ghidra/run_s5_bmanager_dispatch_slice.sh"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_s5_bmanager_dispatch_slice", ANALYZER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic="NOP", operands=None, flows=None):
    return {
        "address": f"0x{address:08x}",
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands or []) if operands else ""),
        "operands": operands or [],
        "references": [],
        "flows": [f"0x{value:08x}" for value in (flows or [])],
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "pcode": [],
    }


def _call(address, target):
    return _ins(address, "CALL", [f"0x{target:08x}"], [target])


def _row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "requested": name,
        "found": True,
        "function": {"address": f"0x{address:08x}", "name": name},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path, *, default_slot_operand="dword ptr [EAX + 0x18]"):
    module = _load_module()
    rows = [
        _row(
            0x00D36000,
            "FUN_00d36000",
            [
                _call(0x00D36051, 0x0070FE90),
                _ins(0x00D36068, "MOV", ["ECX", "EAX"]),
                _call(0x00D3606A, 0x006485B0),
            ],
        ),
        _row(
            0x006485B0,
            "FUN_006485b0",
            [
                _ins(0x006485B5, "MOV", ["EDI", "ECX"]),
                _call(0x006485D4, 0x0065B840),
                _ins(0x006485D9, "MOV", ["ESI", "EAX"]),
                _ins(0x00648603, "MOV", ["EDX", "EDI"]),
                _ins(0x00648605, "MOV", ["ECX", "ESI"]),
                _call(0x00648607, 0x00662600),
            ],
        ),
        _row(
            0x00662600,
            "FUN_00662600",
            [
                _ins(0x00662605, "MOV", ["EBX", "EDX"]),
                _ins(0x0066260D, "LEA", ["EDI", "[ECX + 0x58]"]),
                _ins(0x00662630, "CMP", ["EBX", "dword ptr [ESI + 0xc]"]),
                _ins(0x0066264C, "MOV", ["EDX", "EBX"]),
                _ins(0x0066264E, "MOV", ["ECX", "EDI"]),
                _call(0x00662650, 0x004F5E60),
            ],
        ),
        _row(
            0x006626A0,
            "FUN_006626a0",
            [
                _ins(0x006626A8, "CMP", ["dword ptr [ESI + 0x98]", "0x6"]),
                _ins(0x006626B2, "LEA", ["EAX", "[ESI + 0x58]"]),
                _ins(0x006626B5, "PUSH", ["EAX"]),
                _call(0x006626BD, 0x0065B8B0),
            ],
        ),
        _row(
            0x0065B8B0,
            "FUN_0065b8b0",
            [
                _ins(0x0065B8E0, "MOV", ["ECX", "dword ptr [ESI + 0xc]"]),
                _call(0x0065B8FC, 0x00647EF0),
            ],
        ),
        _row(
            0x00647EF0,
            "FUN_00647ef0",
            [
                _ins(0x00647FA2, "MOV", ["EAX", "dword ptr [ESI + 0xe8]"]),
                _call(0x00647FBD, 0x00647D80),
            ],
        ),
        _row(
            0x00647D80,
            "FUN_00647d80",
            [
                _ins(0x00647D88, "CMP", ["byte ptr [EAX + 0x529]", "0x0"]),
                _ins(0x00647D96, "MOV", ["EDX", "dword ptr [EAX + 0x1c]"]),
                _ins(0x00647D99, "JMP", ["EDX"]),
                _ins(0x00647D9B, "MOV", ["EDX", default_slot_operand]),
                _ins(0x00647D9E, "JMP", ["EDX"]),
            ],
        ),
        _row(
            0x00662880,
            "FUN_00662880",
            [
                _call(0x006629FC, 0x006626A0),
                _ins(0x00662A76, "MOV", ["DL", "0x1"]),
                _ins(0x00662A7E, "MOV", ["ECX", "0xa"]),
                _call(0x00662A83, 0x00649780),
                _ins(0x00662A8C, "JZ", ["0x006628e8"], [0x006628E8]),
            ],
        ),
        _row(0x0070FE90, "FUN_0070fe90", [_ins(0x0070FE90, "RET")]),
    ]

    export = tmp_path / "instructions.jsonl"
    _write_jsonl(export, rows)

    functions = tmp_path / "functions.jsonl"
    _write_jsonl(
        functions,
        [
            {
                "address": "0x006485b0",
                "calling_convention": "__thiscall",
                "parameters": [
                    {"storage": "ECX:4 (auto)"},
                    {"storage": "Stack[0x4]:4"},
                ],
            },
            {
                "address": "0x00662600",
                "calling_convention": "__fastcall",
                "parameters": [
                    {"storage": "ECX:4"},
                    {"storage": "EDX:4"},
                ],
            },
            {
                "address": "0x0065b8b0",
                "calling_convention": "__stdcall",
                "parameters": [{"storage": "Stack[0x4]:4"}],
            },
        ],
    )

    owner = tmp_path / "owner.json"
    owner.write_text(
        json.dumps(
            {
                "format": module.OWNER_FORMAT,
                "ready": True,
                "scheduler_entry": {
                    "owner_proven": True,
                    "slot_offset": 0x18,
                    "target_address": "0x00711b50",
                },
            }
        ),
        encoding="utf-8",
    )
    return module, export, functions, owner


def test_corrected_dispatch_registration_frontier_keeps_cadence_separate(tmp_path):
    module, export, functions, owner = _fixture(tmp_path)
    report = module.analyze(export, functions, owner)

    assert report["format"] == "SHIFT.BManagerPhysicsManagerDispatchFrontier/2"
    assert report["ready"] is True
    assert report["status"] == "dispatch-registration-ready"
    assert report["registration"]["accessor_return_becomes_controller_api_this_ECX"] is True
    assert report["registration"]["accessor_return_is_stack_argument"] is False
    assert report["active_dispatch"]["controller_list_offset"] == "0x58"
    assert report["active_dispatch"]["default_slot_offset"] == "0x18"
    assert report["active_dispatch"]["alternate_slot_offset"] == "0x1c"
    assert report["worker_loop"]["poll_sleep_ms"] == 10
    assert report["worker_loop"]["poll_sleep_promoted_to_physics_cadence"] is False
    assert report["handoff"]["dispatch_registration_ready"] is True
    assert report["handoff"]["retail_cadence_admitted"] is False
    assert report["corrections"]["FUN_00647da0_plus_0x18_rejected"] is True
    assert report["corrections"]["FUN_00647da0_actual_indirect_slot"] == "0x20"


def test_wrong_default_slot_fails_closed(tmp_path):
    module, export, functions, owner = _fixture(
        tmp_path, default_slot_operand="dword ptr [EAX + 0x14]"
    )
    with pytest.raises(ValueError, match="operand drift"):
        module.analyze(export, functions, owner)


def test_wrong_accessor_transfer_model_fails_closed(tmp_path):
    module, export, functions, owner = _fixture(tmp_path)
    rows = [json.loads(line) for line in export.read_text(encoding="utf-8").splitlines()]
    registration = next(row for row in rows if row["function"]["name"] == "FUN_00d36000")
    registration["instructions"][1]["operands"] = ["EDX", "EAX"]
    _write_jsonl(export, rows)
    with pytest.raises(ValueError, match="operand drift"):
        module.analyze(export, functions, owner)


def test_runner_uses_only_corrected_targeted_slice_and_no_runtime_capture():
    source = RUNNER.read_text(encoding="utf-8")
    assert "run_shift_function_instructions.sh" in source
    for target in (
        "FUN_00647d80",
        "FUN_00647ef0",
        "FUN_0065b8b0",
        "FUN_006626a0",
        "FUN_00662880",
        "FUN_00d36000",
        "FUN_006485b0",
        "FUN_00662600",
        "FUN_0070fe90",
    ):
        assert target in source
    for retired in (
        "FUN_00647b70",
        "FUN_00647c60",
        "FUN_00647cf0",
        "FUN_00647da0",
        "FUN_0065bb50",
    ):
        assert retired not in source
    assert "runtime capture" not in source.lower()
    assert "wine" not in source.lower()
