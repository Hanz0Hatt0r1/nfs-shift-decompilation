import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_bmanager_dispatch_slice.py"
RUNNER = ROOT / "tools/ghidra/run_s5_bmanager_dispatch_slice.sh"


def _load_module():
    spec = importlib.util.spec_from_file_location("analyze_s5_bmanager_dispatch_slice", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic="NOP", operands=None, pcode=None, flows=None):
    return {
        "address": f"0x{address:08x}",
        "bytes": "90" if mnemonic != "CALL" else "ff10",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands or []) if operands else ""),
        "operands": operands or [],
        "references": [],
        "flows": [f"0x{value:08x}" for value in (flows or [])],
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": None,
        "pcode": pcode or [{"opcode": "COPY", "text": "COPY", "output": None, "inputs": []}],
    }


def _call(address, target=None, operand=None, indirect=False):
    if indirect:
        return _ins(
            address,
            "CALL",
            [operand or "dword ptr [EAX]"],
            [{"opcode": "CALLIND", "text": "CALLIND", "output": None, "inputs": []}],
            [],
        )
    assert target is not None
    return _ins(
        address,
        "CALL",
        [f"0x{target:08x}"],
        [{"opcode": "CALL", "text": "CALL", "output": None, "inputs": []}],
        [target],
    )


def _row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "requested": f"0x{address:08x}",
        "found": True,
        "function": {"address": f"0x{address:08x}", "name": name},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path, candidate_operand="dword ptr [EAX + 0x18]", clobber_eax=False):
    rows = [
        _row(0x00647B70, "FUN_00647b70", [_ins(0x00647B70), _call(0x00647C0C, operand="dword ptr [EAX + 0xc]", indirect=True)]),
        _row(0x00647C60, "FUN_00647c60", [_ins(0x00647C60), _call(0x00647C87, operand="dword ptr [EAX + 0x10]", indirect=True)]),
        _row(0x00647CF0, "FUN_00647cf0", [_ins(0x00647CF0), _call(0x00647D47, operand="dword ptr [EAX + 0x14]", indirect=True)]),
        _row(0x00647DA0, "FUN_00647da0", [_ins(0x00647DA0), _call(0x00647E23, operand=candidate_operand, indirect=True)]),
        _row(0x0065BB50, "FUN_0065bb50", [_ins(0x0065BB50), _call(0x0065BB96, target=0x00647DA0)]),
    ]

    registration = [
        _ins(0x00D36000),
        _call(0x00D36020, target=0x0070FE90),
    ]
    if clobber_eax:
        registration.append(_ins(0x00D36025, "MOV", ["EAX", "EBX"]))
    registration.extend(
        [
            _ins(0x00D36027, "PUSH", ["EAX"]),
            _ins(0x00D36028, "MOV", ["ECX", "ESI"]),
            _call(0x00D36030, target=0x006485B0),
        ]
    )
    rows.append(_row(0x00D36000, "FUN_00d36000", registration))
    rows.extend(
        [
            _row(0x006485B0, "FUN_006485b0", [_ins(0x006485B0), _call(0x00648607, target=0x00662600)]),
            _row(0x00662600, "FUN_00662600", [_ins(0x00662600), _ins(0x00662601, "RET")]),
            _row(
                0x0070FE90,
                "FUN_0070fe90",
                [
                    _ins(0x0070FE90, "MOV", ["EAX", "dword ptr [0x00bb0000]"]),
                    _ins(0x0070FE97, "RET"),
                ],
            ),
        ]
    )

    export = tmp_path / "instructions.jsonl"
    _write_jsonl(export, rows)

    functions = tmp_path / "functions.jsonl"
    _write_jsonl(
        functions,
        [
            {
                "address": "0x0070fe90",
                "name": "FUN_0070fe90",
                "calling_convention": "__stdcall",
                "parameters": [],
            },
            {
                "address": "0x006485b0",
                "name": "FUN_006485b0",
                "calling_convention": "__thiscall",
                "parameters": [
                    {"name": "this", "storage": "ECX:4 (auto)"},
                    {"name": "param_1", "storage": "Stack[0x4]:4"},
                ],
            },
            {
                "address": "0x00662600",
                "name": "FUN_00662600",
                "calling_convention": "__fastcall",
                "parameters": [
                    {"name": "param_1", "storage": "ECX:4"},
                    {"name": "param_2", "storage": "EDX:4"},
                ],
            },
        ],
    )

    owner = tmp_path / "owner.json"
    owner.write_text(
        json.dumps(
            {
                "format": "SHIFT.PhysicsManagerSchedulerEntryOwner/1",
                "ready": True,
                "scheduler_entry": {
                    "owner_proven": True,
                    "slot_offset": 0x18,
                    "target": "FUN_00711b50",
                },
            }
        ),
        encoding="utf-8",
    )
    return export, functions, owner


def test_positive_dispatch_registration_frontier_keeps_cadence_closed(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path)
    report = module.analyze(export, functions, owner)

    assert report["format"] == "SHIFT.BManagerPhysicsManagerDispatchFrontier/1"
    assert report["ready"] is True
    assert report["status"] == "dispatch-registration-ready"
    assert report["slot_join"]["FUN_00647da0_matches_source_backed_cPhysicsManager_slot"] is True
    assert report["slot_join"]["semantic_name_tick_promoted"] is False
    assert report["controller_dispatch"]["calls_FUN_00647da0"] is True
    assert report["physics_manager_registration"]["registration_api_argument_proven"] is True
    assert report["handoff"]["dispatch_registration_ready"] is True
    assert report["handoff"]["scheduler_entry_elapsed_or_accumulator_input_proven"] is False
    assert report["handoff"]["retail_cadence_admitted"] is False
    assert report["blocking_reasons"] == ["scheduler-entry-elapsed-or-accumulator-producer-not-proven"]


def test_wrong_candidate_slot_fails_closed(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path, candidate_operand="dword ptr [EAX + 0x14]")
    report = module.analyze(export, functions, owner)

    assert report["ready"] is False
    assert report["slot_join"]["FUN_00647da0_matches_source_backed_cPhysicsManager_slot"] is False
    assert "FUN_00647da0-indirect-call-not-proven-to-use-cPhysicsManager-owner-slot-plus-0x18" in report["blocking_reasons"]
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_accessor_return_clobber_fails_registration_alias(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path, clobber_eax=True)
    report = module.analyze(export, functions, owner)

    assert report["ready"] is False
    transfer = report["physics_manager_registration"]["value_transfer"]
    assert transfer["accessor_return_passed_as_stack_argument_to_controller_api"] is False
    assert "physics-manager-accessor-return-to-controller-api-manager-argument-not-proven" in report["blocking_reasons"]


def test_runner_uses_only_targeted_instruction_export_and_no_runtime_capture():
    source = RUNNER.read_text(encoding="utf-8")
    assert "run_shift_function_instructions.sh" in source
    for target in (
        "FUN_00647b70",
        "FUN_00647c60",
        "FUN_00647cf0",
        "FUN_00647da0",
        "FUN_0065bb50",
        "FUN_00d36000",
        "FUN_006485b0",
        "FUN_00662600",
        "FUN_0070fe90",
    ):
        assert target in source
    assert "SHIFT.exe" in source
    assert "runtime capture" not in source.lower()
    assert "wine" not in source.lower()
