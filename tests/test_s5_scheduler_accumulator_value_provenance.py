from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_scheduler_accumulator_value_provenance.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_s5_scheduler_accumulator_value_provenance", ANALYZER
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

_REG_OFFSETS = {
    "EAX": "0x0",
    "ECX": "0x4",
    "EDX": "0x8",
    "EBX": "0xc",
    "ESP": "0x10",
    "EBP": "0x14",
    "ESI": "0x18",
    "EDI": "0x1c",
}


def _varnode(
    text: str,
    *,
    space: str,
    offset: str,
    size: int,
    constant: bool = False,
    register: bool = False,
    unique: bool = False,
) -> dict:
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


def _reg(name: str) -> dict:
    return _varnode(
        name,
        space="register",
        offset=_REG_OFFSETS[name],
        size=4,
        register=True,
    )


def _const(value: int, size: int = 4, *, text: str | None = None) -> dict:
    return _varnode(
        text or f"0x{value:x}",
        space="const",
        offset=f"0x{value:x}",
        size=size,
        constant=True,
    )


def _unique(value: int, size: int) -> dict:
    return _varnode(
        f"u_{value:x}",
        space="unique",
        offset=f"0x{value:x}",
        size=size,
        unique=True,
    )


def _ram() -> dict:
    return _const(0, 4, text="RAM")


def _op(opcode: str, text: str, output, inputs: list[dict]) -> dict:
    return {
        "opcode": opcode,
        "text": text,
        "output": output,
        "inputs": inputs,
    }


def _ins(address: int, mnemonic: str, operands: list[str], pcode: list[dict]) -> dict:
    return {
        "address": f"0x{address:08x}",
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "references": [],
        "flows": [],
        "flow_type": "FALL_THROUGH",
        "fallthrough": None,
        "pcode": pcode,
    }


def _call(address: int, target: int) -> dict:
    row = _ins(
        address,
        "CALL",
        [f"0x{target:08x}"],
        [_op("CALL", "CALL", None, [_const(target)])],
    )
    row["flows"] = [f"0x{target:08x}"]
    row["flow_type"] = "CALL"
    return row


def _row(address: int, name: str, instructions: list[dict]) -> dict:
    return {
        "format": "SHIFT.GhidraFunctionInstructions/2",
        "requested": f"0x{address:08x}",
        "found": True,
        "function": {"address": f"0x{address:08x}", "name": name},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _owner_instructions(
    *,
    parameter_frame_offset: int = 8,
    call_barrier: bool = False,
    constant_store: bool = False,
) -> tuple[list[dict], str]:
    u_addr = _unique(0x100, 4)
    u_value4 = _unique(0x104, 4)
    u_value8 = _unique(0x108, 8)
    u_store_addr = _unique(0x10C, 4)

    instructions = [
        _ins(
            0x00715380,
            "PUSH",
            ["EBP"],
            [
                _op("INT_SUB", "ESP = ESP - 4", _reg("ESP"), [_reg("ESP"), _const(4)]),
                _op("STORE", "STORE ram(ESP) = EBP", None, [_ram(), _reg("ESP"), _reg("EBP")]),
            ],
        ),
        _ins(
            0x00715381,
            "MOV",
            ["EBP", "ESP"],
            [_op("COPY", "EBP = ESP", _reg("EBP"), [_reg("ESP")])],
        ),
    ]
    if call_barrier:
        instructions.append(_call(0x00715383, 0x00400010))

    instructions.extend(
        [
            _ins(
                0x00715388,
                "FLD",
                [f"dword ptr [EBP + 0x{parameter_frame_offset:x}]"],
                [
                    _op(
                        "INT_ADD",
                        f"u_100 = EBP + 0x{parameter_frame_offset:x}",
                        u_addr,
                        [_reg("EBP"), _const(parameter_frame_offset)],
                    ),
                    _op("LOAD", "u_104 = LOAD ram(u_100)", u_value4, [_ram(), u_addr]),
                    _op(
                        "FLOAT_FLOAT2FLOAT",
                        "u_108 = FLOAT_FLOAT2FLOAT u_104",
                        u_value8,
                        [u_value4],
                    ),
                ],
            ),
            _ins(
                0x00715390,
                "FSTP",
                ["qword ptr [ECX + 0x348]"],
                [
                    _op(
                        "INT_ADD",
                        "u_10c = ECX + 0x348",
                        u_store_addr,
                        [_reg("ECX"), _const(0x348)],
                    ),
                    _op(
                        "STORE",
                        "STORE ram(u_10c) = value",
                        None,
                        [
                            _ram(),
                            u_store_addr,
                            _const(0x3FF0000000000000, 8) if constant_store else u_value8,
                        ],
                    ),
                ],
            ),
            _call(0x00715434, 0x00713050),
        ]
    )
    return instructions, "0x00715390"


def _instruction_export(
    tmp_path: Path,
    *,
    parameter_frame_offset: int = 8,
    call_barrier: bool = False,
    constant_store: bool = False,
) -> tuple[Path, str]:
    owner, writer_address = _owner_instructions(
        parameter_frame_offset=parameter_frame_offset,
        call_barrier=call_barrier,
        constant_store=constant_store,
    )
    path = tmp_path / "instructions.jsonl"
    _write_jsonl(
        path,
        [
            _row(
                0x007155E9,
                "FUN_007155e9",
                [_ins(0x007155E9, "NOP", [], [_op("COPY", "NOP", None, [])])],
            ),
            _row(0x00715380, "FUN_00715380", owner),
            _row(
                0x00713050,
                "FUN_00713050",
                [_ins(0x00713050, "NOP", [], [_op("COPY", "NOP", None, [])])],
            ),
        ],
    )
    return path, writer_address


def _surface(tmp_path: Path, writer_address: str, *, preclaim: bool = False) -> Path:
    path = tmp_path / "surface.json"
    blocker = MODULE._EXPECTED_PARENT_BLOCKER
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.SchedulerAccumulatorProducerFrontier/1",
                "ready": True,
                "status": "accumulator-writer-surface-ready",
                "abi": {
                    "owner": {
                        "address": "0x00715380",
                        "calling_convention": "__thiscall",
                        "this_storage": "ECX:4 (auto)",
                        "explicit_argument_storage": "Stack[0x4]:4",
                        "explicit_argument_type": "float",
                    }
                },
                "accumulator": {
                    "displacement": 0x348,
                    "unique_owner_writer_surface_proven": True,
                    "stored_value_from_FUN_00715380_param1_proven": preclaim,
                    "owner_accesses": [
                        {
                            "instruction": writer_address,
                            "instruction_text": "FSTP qword ptr [ECX + 0x348]",
                            "base_register": "ECX",
                            "displacement": 0x348,
                            "access": "write",
                            "this_relative_access_proven": True,
                        }
                    ],
                },
                "blocking_reasons": [] if preclaim else [blocker],
                "handoff": {
                    "scheduler_accumulator_writer_surface_ready": True,
                    "retail_cadence_admitted": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_proves_entry_stack_param_dependency_through_frame_pointer_and_float_transform(tmp_path):
    export, writer_address = _instruction_export(tmp_path)
    report = MODULE.analyze(export, _surface(tmp_path, writer_address))

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "owner-param1-dependency-proven"
    assert report["stored_value_depends_on_FUN_00715380_param1_proven"] is True
    assert report["stored_value_equals_FUN_00715380_param1_proven"] is False
    assert report["proven_stack_parameter_dependency_count"] == 1
    load = next(
        row
        for row in report["stack_parameter_load_candidates"]
        if row["dependency_to_store_proven"] is True
    )
    assert load["load_width"] == 4
    assert load["address_expression"]["entry_register"] == "ESP"
    assert load["address_expression"]["offset"] == 4
    assert load["control_barriers_to_store"] == []
    assert "FLOAT_FLOAT2FLOAT" in report["value_slice"]["dependency_opcodes"]
    assert report["handoff"]["FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven"] is True
    assert report["handoff"]["FUN_007155e9_argument_producer_proven"] is False
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_wrong_stack_slot_keeps_param_dependency_blocked(tmp_path):
    export, writer_address = _instruction_export(tmp_path, parameter_frame_offset=12)
    report = MODULE.analyze(export, _surface(tmp_path, writer_address))

    assert report["ready"] is False
    assert report["proven_stack_parameter_dependency_count"] == 0
    assert report["stack_parameter_load_candidates"][0]["address_expression"]["offset"] == 8
    assert (
        "FUN_00715380-Stack-0x4-param1-dependency-to-plus-0x348-STORE-not-proven"
        in report["blocking_reasons"]
    )
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_call_between_frame_definition_and_parameter_load_is_a_barrier(tmp_path):
    export, writer_address = _instruction_export(tmp_path, call_barrier=True)
    report = MODULE.analyze(export, _surface(tmp_path, writer_address))

    assert report["ready"] is False
    candidate = report["stack_parameter_load_candidates"][0]
    assert candidate["matches_entry_Stack_0x4_size4"] is True
    assert candidate["dependency_to_store_proven"] is False
    assert candidate["control_barriers_to_store"][0]["mnemonic"] == "CALL"


def test_constant_store_does_not_inherit_param_semantics_from_nearby_load(tmp_path):
    export, writer_address = _instruction_export(tmp_path, constant_store=True)
    report = MODULE.analyze(export, _surface(tmp_path, writer_address))

    assert report["ready"] is False
    assert report["stack_parameter_load_candidates"] == []
    assert report["stored_value_depends_on_FUN_00715380_param1_proven"] is False


def test_parent_surface_that_preclaims_value_provenance_is_rejected(tmp_path):
    export, writer_address = _instruction_export(tmp_path)
    with pytest.raises(ValueError, match="unexpectedly preclaims param1 value provenance"):
        MODULE.analyze(export, _surface(tmp_path, writer_address, preclaim=True))
