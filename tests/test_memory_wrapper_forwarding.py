import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "analyze_memory_wrapper_forwarding.py"
    spec = importlib.util.spec_from_file_location("analyze_memory_wrapper_forwarding", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _function(address, name, cc, storages, types=None):
    if types is None:
        types = ["bogus-auto-type"] * len(storages)
    return {
        "address": address,
        "name": name,
        "calling_convention": cc,
        "parameters": [
            {"name": f"param_{index}", "type": type_name, "storage": storage}
            for index, (storage, type_name) in enumerate(zip(storages, types), 1)
        ],
    }


def _ins(address, mnemonic, operands=None, target=None):
    refs = []
    flows = []
    if target is not None:
        refs.append({"to": target, "type": "UNCONDITIONAL_CALL"})
        flows.append(target)
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ",".join(operands or []) if operands else ""),
        "operands": operands or [],
        "flow_type": "CALL" if target else "FALL_THROUGH",
        "fallthrough": None,
        "flows": flows,
        "references": refs,
    }


def _instruction_row(address, name, instructions):
    return {
        "format": "SHIFT.GhidraFunctionInstructions/1",
        "program": "SHIFT.exe",
        "requested": address,
        "found": True,
        "function": {"address": address, "name": name, "size": 32, "calling_convention": "unknown"},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _fixture(tmp_path):
    family = tmp_path / "family.json"
    _write_json(
        family,
        {
            "format": "SHIFT-MEMORY-WRAPPER-FAMILY/1",
            "wrappers": [
                {
                    "address": "0x00001000",
                    "name": "FUN_00001000",
                    "side": "create",
                    "required_direct_callees": ["0x00002000"],
                    "wrapper_shape_confirmed": True,
                },
                {
                    "address": "0x00001100",
                    "name": "FUN_00001100",
                    "side": "release",
                    "required_direct_callees": ["0x00002100"],
                    "wrapper_shape_confirmed": True,
                },
            ],
        },
    )

    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "functions.jsonl",
        [
            _function(
                "0x00001000",
                "FUN_00001000",
                "__cdecl",
                ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
                ["uint", "AptFrameStack *", "definitely-wrong-type"],
            ),
            _function(
                "0x00002000",
                "FUN_00002000",
                "__fastcall",
                ["ECX:4", "EDX:4", "Stack[0x4]:4"],
            ),
            _function(
                "0x00001100",
                "FUN_00001100",
                "__fastcall",
                ["ECX:4", "DL:1", "Stack[0x4]:4"],
            ),
            _function(
                "0x00002100",
                "FUN_00002100",
                "__fastcall",
                ["ECX:4", "DL:1"],
            ),
        ],
    )

    instructions = tmp_path / "instructions.jsonl"
    _write_jsonl(
        instructions,
        [
            _instruction_row(
                "0x00001000",
                "FUN_00001000",
                [
                    _ins("0x00001000", "MOV", ["ECX", "dword ptr [ESP + 0x4]"]),
                    _ins("0x00001004", "MOV", ["EDX", "dword ptr [ESP + 0x8]"]),
                    _ins("0x00001008", "PUSH", ["dword ptr [ESP + 0xc]"]),
                    _ins("0x0000100c", "CALL", ["FUN_00002000"], "0x00002000"),
                    _ins("0x00001011", "RET"),
                ],
            ),
            _instruction_row(
                "0x00001100",
                "FUN_00001100",
                [
                    _ins("0x00001100", "CALL", ["FUN_00002100"], "0x00002100"),
                    _ins("0x00001105", "RET", ["0x4"]),
                ],
            ),
        ],
    )
    return family, instructions, ghidra


def test_recovers_create_stack_to_fastcall_forwarding(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)

    create = next(row for row in report["wrappers"] if row["address"] == "0x00001000")
    assert create["exact_forwarding_candidate"] is True
    assert create["forwarded_wrapper_inputs"] == [1, 2, 3]
    assert create["unforwarded_declared_inputs"] == []
    bindings = create["backend_calls"][0]["target_parameter_bindings"]
    assert [binding["source_input_indices"] for binding in bindings] == [[1], [2], [3]]
    assert bindings[0]["reported_type"] == "bogus-auto-type"
    assert create["scope"]["semantic_parameter_types_used"] is False


def test_release_register_forwarding_can_leave_aux_stack_input_unforwarded(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)

    release = next(row for row in report["wrappers"] if row["address"] == "0x00001100")
    assert release["exact_forwarding_candidate"] is True
    assert release["forwarded_wrapper_inputs"] == [1, 2]
    assert release["unforwarded_declared_inputs"] == [3]
    bindings = release["backend_calls"][0]["target_parameter_bindings"]
    assert [binding["source_input_indices"] for binding in bindings] == [[1], [2]]


def test_frame_pointer_stack_access_is_resolved(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text().splitlines()]
    rows[0]["instructions"] = [
        _ins("0x00001000", "PUSH", ["EBP"]),
        _ins("0x00001001", "MOV", ["EBP", "ESP"]),
        _ins("0x00001003", "MOV", ["ECX", "dword ptr [EBP + 0x8]"]),
        _ins("0x00001007", "MOV", ["EDX", "dword ptr [EBP + 0xc]"]),
        _ins("0x0000100b", "PUSH", ["dword ptr [EBP + 0x10]"]),
        _ins("0x0000100f", "CALL", ["FUN_00002000"], "0x00002000"),
        _ins("0x00001014", "LEAVE"),
        _ins("0x00001015", "RET"),
    ]
    rows[0]["instruction_count"] = len(rows[0]["instructions"])
    _write_jsonl(instructions, rows)

    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)
    create = next(row for row in report["wrappers"] if row["address"] == "0x00001000")
    assert create["exact_forwarding_candidate"] is True
    assert create["forwarded_wrapper_inputs"] == [1, 2, 3]


def test_control_flow_branch_fails_closed(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text().splitlines()]
    rows[0]["instructions"].insert(2, _ins("0x00001006", "JNZ", ["0x00001020"]))
    rows[0]["instruction_count"] = len(rows[0]["instructions"])
    _write_jsonl(instructions, rows)

    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)
    create = next(row for row in report["wrappers"] if row["address"] == "0x00001000")
    assert create["nonlinear_control_flow"] is True
    assert create["exact_forwarding_candidate"] is False
    assert any("control-flow:JNZ" in blocker for blocker in create["blockers"])


def test_unmodeled_state_mutation_fails_closed(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    rows = [json.loads(line) for line in instructions.read_text().splitlines()]
    rows[0]["instructions"].insert(2, _ins("0x00001006", "IMUL", ["ECX", "EDX"]))
    rows[0]["instruction_count"] = len(rows[0]["instructions"])
    _write_jsonl(instructions, rows)

    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)
    create = next(row for row in report["wrappers"] if row["address"] == "0x00001000")
    assert create["exact_forwarding_candidate"] is False
    assert any("unmodeled-instruction:IMUL" in blocker for blocker in create["blockers"])


def test_scope_does_not_promote_argument_roles_or_allocator_abi(tmp_path):
    module = _load_module()
    family, instructions, ghidra = _fixture(tmp_path)
    report = module.analyze_memory_wrapper_forwarding(family, instructions, ghidra)
    assert report["all_family_wrappers_exact"] is True
    assert report["scope"]["argument_forwarding_proven_when_exact"] is True
    assert report["scope"]["argument_roles_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False
    assert report["scope"]["operator_new_identity_proven"] is False
