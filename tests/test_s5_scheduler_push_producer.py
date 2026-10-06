from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_scheduler_push_producer.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_s5_scheduler_push_producer", ANALYZER
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


def _upper_instructions(*, unbound: bool = False, call_barrier: bool = False) -> list[dict]:
    instructions: list[dict] = []
    if not unbound:
        instructions.append(
            _ins(
                0x007155E9,
                "MOV",
                ["EAX", "0x3f800000"],
                [_op("COPY", "EAX = 0x3f800000", _reg("EAX"), [_const(0x3F800000)])],
            )
        )
    else:
        instructions.append(
            _ins(
                0x007155E9,
                "NOP",
                [],
                [_op("COPY", "NOP", None, [])],
            )
        )

    if call_barrier:
        instructions.append(_call(0x007155F8, 0x00400010))

    instructions.extend(
        [
            _ins(
                0x007155FC,
                "PUSH",
                ["EAX"],
                [
                    _op(
                        "INT_SUB",
                        "ESP = ESP - 4",
                        _reg("ESP"),
                        [_reg("ESP"), _const(4)],
                    ),
                    _op(
                        "STORE",
                        "STORE ram(ESP) = EAX",
                        None,
                        [_ram(), _reg("ESP"), _reg("EAX")],
                    ),
                ],
            ),
            _call(0x00715602, 0x00715380),
        ]
    )
    return instructions


def _instruction_export(
    tmp_path: Path, *, unbound: bool = False, call_barrier: bool = False
) -> Path:
    path = tmp_path / "instructions.jsonl"
    _write_jsonl(
        path,
        [
            _row(
                0x007155E9,
                "FUN_007155e9",
                _upper_instructions(unbound=unbound, call_barrier=call_barrier),
            ),
            _row(
                0x00715380,
                "FUN_00715380",
                [_ins(0x00715380, "NOP", [], [_op("COPY", "NOP", None, [])])],
            ),
            _row(
                0x00713050,
                "FUN_00713050",
                [_ins(0x00713050, "NOP", [], [_op("COPY", "NOP", None, [])])],
            ),
        ],
    )
    return path


def _surface(tmp_path: Path) -> Path:
    path = tmp_path / "surface.json"
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.SchedulerAccumulatorProducerFrontier/1",
                "ready": True,
                "exact_calls": {
                    "FUN_007155e9_to_FUN_00715380": {
                        "instruction": "0x00715602",
                        "verified": True,
                    }
                },
                "upper_to_owner_argument": {
                    "proven": True,
                    "status": "single-explicit-stack-argument-push",
                    "instruction": "0x007155fc",
                    "instruction_text": "PUSH EAX",
                    "operand": "EAX",
                    "semantic_elapsed_value_proven": False,
                },
                "handoff": {"retail_cadence_admitted": False},
            }
        ),
        encoding="utf-8",
    )
    return path


def _accumulator_value(tmp_path: Path) -> Path:
    path = tmp_path / "value.json"
    path.write_text(
        json.dumps(
            {
                "format": "SHIFT.SchedulerAccumulatorValueProvenance/1",
                "ready": True,
                "handoff": {
                    "FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven": True,
                    "FUN_007155e9_argument_producer_proven": False,
                    "retail_cadence_admitted": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_proves_exact_local_push_machine_producer_without_promoting_cadence(tmp_path):
    report = MODULE.analyze(
        _instruction_export(tmp_path),
        _surface(tmp_path),
        _accumulator_value(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "local-push-machine-producer-proven"
    assert report["callsite"]["call_instruction"] == "0x00715602"
    assert report["callsite"]["push_instruction"] == "0x007155fc"
    assert report["callsite"]["push_operand"] == "EAX"
    push = report["push_value"]
    assert push["producer_instruction"] == "0x007155e9"
    assert push["local_machine_producer_proven"] is True
    assert push["control_barriers_to_push"] == []
    assert report["handoff"]["FUN_007155e9_argument_machine_producer_proven"] is True
    assert report["handoff"]["retail_cadence_admitted"] is False
    assert report["limits"]["machine_producer_is_elapsed_time_semantics"] is False
    assert report["limits"]["physical_time_units_proven"] is False


def test_unbound_entry_register_does_not_count_as_local_machine_producer(tmp_path):
    report = MODULE.analyze(
        _instruction_export(tmp_path, unbound=True),
        _surface(tmp_path),
        _accumulator_value(tmp_path),
    )

    assert report["ready"] is False
    assert report["push_value"]["store_value_definition"] is None
    assert report["push_value"]["local_machine_producer_proven"] is False
    assert "FUN_007155e9-local-PUSH-machine-producer-not-proven" in report["blocking_reasons"]
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_call_between_value_definition_and_push_is_a_fail_closed_barrier(tmp_path):
    report = MODULE.analyze(
        _instruction_export(tmp_path, call_barrier=True),
        _surface(tmp_path),
        _accumulator_value(tmp_path),
    )

    assert report["ready"] is False
    barriers = report["push_value"]["control_barriers_to_push"]
    assert barriers
    assert barriers[0]["mnemonic"] == "CALL"
    assert "FUN_007155e9-PUSH-provenance-crosses-control-barrier" in report["blocking_reasons"]
    assert report["handoff"]["retail_cadence_admitted"] is False
