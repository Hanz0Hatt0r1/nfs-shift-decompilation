import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_scheduler_accumulator_slice.py"
RUNNER = ROOT / "tools/ghidra/run_s5_scheduler_accumulator_slice.sh"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_s5_scheduler_accumulator_slice", ANALYZER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ins(address, mnemonic="NOP", operands=None, pcode=None, flows=None):
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
        "pcode": pcode
        or [{"opcode": "COPY", "text": "COPY", "output": None, "inputs": []}],
    }


def _call(address, target):
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
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _fixture(tmp_path, *, owner_offset=0x348, argument_barrier=False, abi_drift=False):
    upper_instructions = [
        _ins(0x007155E9),
        _ins(0x007155FC, "PUSH", ["EAX"]),
    ]
    if argument_barrier:
        upper_instructions.append(_call(0x007155FE, 0x00400010))
    upper_instructions.append(_call(0x00715602, 0x00715380))

    owner_instructions = [
        _ins(0x00715380),
        _ins(
            0x00715390,
            "MOV",
            [f"dword ptr [ECX + 0x{owner_offset:x}]", "EAX"],
            [{"opcode": "STORE", "text": "STORE", "output": None, "inputs": []}],
        ),
        _call(0x00715434, 0x00713050),
    ]

    batch_instructions = [
        _ins(0x00713050),
        _ins(
            0x00713060,
            "MOV",
            ["EAX", "dword ptr [ECX + 0x348]"],
            [{"opcode": "LOAD", "text": "LOAD", "output": None, "inputs": []}],
        ),
    ]

    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            _row(0x007155E9, "FUN_007155e9", upper_instructions),
            _row(0x00715380, "FUN_00715380", owner_instructions),
            _row(0x00713050, "FUN_00713050", batch_instructions),
        ],
    )

    owner_argument_storage = "Stack[0x8]:4" if abi_drift else "Stack[0x4]:4"
    functions = tmp_path / "functions.jsonl"
    _write_jsonl(
        functions,
        [
            {
                "address": "0x007155e9",
                "name": "FUN_007155e9",
                "calling_convention": "__fastcall",
                "parameters": [
                    {"name": "param_1", "type": "LONG *", "storage": "ECX:4"}
                ],
            },
            {
                "address": "0x00715380",
                "name": "FUN_00715380",
                "calling_convention": "__thiscall",
                "parameters": [
                    {"name": "this", "type": "void *", "storage": "ECX:4 (auto)"},
                    {
                        "name": "param_1",
                        "type": "float",
                        "storage": owner_argument_storage,
                    },
                ],
            },
            {
                "address": "0x00713050",
                "name": "FUN_00713050",
                "calling_convention": "__thiscall",
                "parameters": [
                    {"name": "this", "type": "void *", "storage": "ECX:4 (auto)"},
                    {"name": "param_1", "type": "int *", "storage": "Stack[0x4]:4"},
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
                "handoff": {"exact_direct_chain_to_FUN_00713050_proven": True},
            }
        ),
        encoding="utf-8",
    )
    return export, functions, owner


def test_positive_writer_surface_keeps_value_and_cadence_closed(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path)
    report = module.analyze(export, functions, owner)

    assert report["format"] == "SHIFT.SchedulerAccumulatorProducerFrontier/1"
    assert report["ready"] is True
    assert report["status"] == "accumulator-writer-surface-ready"
    assert report["exact_calls"]["FUN_007155e9_to_FUN_00715380"]["verified"] is True
    assert report["exact_calls"]["FUN_00715380_to_FUN_00713050"]["verified"] is True
    assert report["upper_to_owner_argument"]["proven"] is True
    accumulator = report["accumulator"]
    assert accumulator["unique_owner_writer_surface_proven"] is True
    assert accumulator["batch_reader_surface_proven"] is True
    assert accumulator["stored_value_from_FUN_00715380_param1_proven"] is False
    assert (
        "FUN_00715380-param1-to-this-plus-0x348-stored-value-provenance-not-proven"
        in report["blocking_reasons"]
    )
    assert "retail-cadence-dynamic-multiplicity-not-proven" in report["blocking_reasons"]
    assert report["handoff"]["scheduler_entry_elapsed_or_accumulator_input_proven"] is False
    assert report["handoff"]["retail_cadence_admitted"] is False
    assert report["limits"]["host_fixed_step_substitution_allowed"] is False
    assert report["limits"]["rendered_frame_equivalence_proven"] is False


def test_wrong_owner_displacement_fails_closed(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path, owner_offset=0x344)
    report = module.analyze(export, functions, owner)

    assert report["ready"] is False
    assert report["accumulator"]["unique_owner_writer_surface_proven"] is False
    assert "unique-FUN_00715380-this-plus-0x348-writer-not-proven" in report["blocking_reasons"]
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_call_barrier_between_argument_push_and_owner_call_fails_closed(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path, argument_barrier=True)
    report = module.analyze(export, functions, owner)

    assert report["ready"] is False
    assert report["upper_to_owner_argument"]["proven"] is False
    assert report["upper_to_owner_argument"]["status"] == "barrier-before-explicit-argument"
    assert (
        "FUN_007155e9-to-FUN_00715380-explicit-argument-setup-not-proven"
        in report["blocking_reasons"]
    )


def test_owner_abi_drift_is_rejected(tmp_path):
    module = _load_module()
    export, functions, owner = _fixture(tmp_path, abi_drift=True)

    try:
        module.analyze(export, functions, owner)
    except ValueError as exc:
        assert "FUN_00715380 physical parameter storage drift" in str(exc)
    else:
        raise AssertionError("ABI drift must fail closed")


def test_runner_scope_is_static_and_exactly_three_functions():
    source = RUNNER.read_text(encoding="utf-8")
    assert "run_shift_function_instructions.sh" in source
    assert source.count("FUN_007155e9") == 1
    assert source.count("FUN_00715380") == 1
    assert source.count("FUN_00713050") == 1
    assert "shift_d3d9_capture" not in source.lower()
    assert "wine" not in source.lower()
    assert "runtime execution" in source.lower()
