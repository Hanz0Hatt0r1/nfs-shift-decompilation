import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_s5_scheduler_timing_argument_producer.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "analyze_s5_scheduler_timing_argument_producer", ANALYZER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vn(text, space, offset, *, size=4, constant=False, register=False, unique=False):
    return {
        "text": text,
        "space": space,
        "offset": offset,
        "size": size,
        "constant": constant,
        "register": register,
        "unique": unique,
    }


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
        "pcode": [] if pcode is None else pcode,
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


def _fixture(tmp_path, *, barrier=False, direct_constant=False, preclaim=False):
    eax = _vn("EAX", "register", "0x0", register=True)
    esp = _vn("ESP", "register", "0x10", register=True)
    ram = _vn("RAM", "const", "0x1", constant=True)
    constant = _vn("0x3f800000", "const", "0x3f800000", constant=True)

    upper = [_ins(0x007155E9)]
    if direct_constant:
        push_operand = "0x3f800000"
        push_value = constant
    else:
        upper.append(
            _ins(
                0x007155F6,
                "MOV",
                ["EAX", "0x3f800000"],
                [
                    {
                        "opcode": "COPY",
                        "text": "EAX = COPY 0x3f800000",
                        "output": eax,
                        "inputs": [constant],
                    }
                ],
            )
        )
        push_operand = "EAX"
        push_value = eax
    if barrier:
        upper.append(_call(0x007155FA, 0x00400010))
    upper.append(
        _ins(
            0x007155FC,
            "PUSH",
            [push_operand],
            [
                {
                    "opcode": "STORE",
                    "text": "STORE ram(ESP), value",
                    "output": None,
                    "inputs": [ram, esp, push_value],
                }
            ],
        )
    )
    upper.append(_call(0x00715602, 0x00715380))

    export = tmp_path / "instructions.jsonl"
    _write_jsonl(
        export,
        [
            _row(0x007155E9, "FUN_007155e9", upper),
            _row(0x00715380, "FUN_00715380", [_ins(0x00715380)]),
            _row(0x00713050, "FUN_00713050", [_ins(0x00713050)]),
        ],
    )

    surface = tmp_path / "surface.json"
    surface.write_text(
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
                    "instruction": "0x007155fc",
                    "operand": push_operand,
                },
                "handoff": {"retail_cadence_admitted": False},
            }
        ),
        encoding="utf-8",
    )

    value = tmp_path / "value.json"
    value.write_text(
        json.dumps(
            {
                "format": "SHIFT.SchedulerAccumulatorValueProvenance/1",
                "ready": True,
                "stored_value_depends_on_FUN_00715380_param1_proven": True,
                "handoff": {
                    "FUN_00715380_param1_to_this_plus_0x348_value_dependency_proven": True,
                    "FUN_007155e9_argument_producer_proven": preclaim,
                    "retail_cadence_admitted": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return export, surface, value


def test_register_value_slice_reaches_exact_constant_root(tmp_path):
    module = _load_module()
    export, surface, value = _fixture(tmp_path)
    report = module.analyze(export, surface, value)

    assert report["format"] == "SHIFT.SchedulerTimingArgumentProducerFrontier/1"
    assert report["ready"] is True
    assert report["status"] == "upper-argument-value-slice-ready"
    assert report["callsite"]["instruction"] == "0x00715602"
    assert report["argument_push"]["instruction"] == "0x007155fc"
    assert report["argument_push"]["operand"] == "EAX"
    assert report["value_slice"]["dependency_opcodes"] == ["COPY"]
    roots = report["value_slice"]["terminal_roots"]
    assert len(roots) == 1
    assert roots[0]["root_kind"] == "constant"
    assert roots[0]["offset"] == "0x3f800000"
    assert report["handoff"]["FUN_007155e9_argument_value_slice_ready"] is True
    assert report["handoff"]["FUN_007155e9_argument_producer_semantics_proven"] is False
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_direct_constant_push_is_a_valid_machine_root_but_not_time_semantics(tmp_path):
    module = _load_module()
    export, surface, value = _fixture(tmp_path, direct_constant=True)
    report = module.analyze(export, surface, value)

    assert report["ready"] is True
    assert report["value_slice"]["dependency_slice"] == []
    assert report["value_slice"]["terminal_root_kinds"] == ["constant"]
    assert report["limits"]["terminal_machine_root_is_semantic_time_source"] is False
    assert report["limits"]["physical_time_units_proven"] is False


def test_call_barrier_inside_value_slice_fails_closed(tmp_path):
    module = _load_module()
    export, surface, value = _fixture(tmp_path, barrier=True)
    report = module.analyze(export, surface, value)

    assert report["ready"] is False
    assert report["value_slice"]["control_barriers_before_push"]
    assert "control-barrier-inside-upper-argument-value-slice" in report["blocking_reasons"]
    assert "FUN_007155e9-pushed-value-local-provenance-slice-not-proven" in report["blocking_reasons"]
    assert report["handoff"]["retail_cadence_admitted"] is False


def test_stale_parent_preclaim_is_rejected(tmp_path):
    module = _load_module()
    export, surface, value = _fixture(tmp_path, preclaim=True)

    try:
        module.analyze(export, surface, value)
    except ValueError as exc:
        assert "unexpectedly preclaims the upper argument producer" in str(exc)
    else:
        raise AssertionError("stale parent preclaim must fail closed")
