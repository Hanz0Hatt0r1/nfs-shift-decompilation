from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_renderables_runtime_alias.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_renderables_runtime_alias", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _pcode(opcode: str, text: str, output=None):
    row = {"opcode": opcode, "text": text}
    if output is not None:
        row["output"] = output
    return row


def _ins(address, mnemonic, operands=None, *, fallthrough=None, flows=None, flow_type="FALL_THROUGH", pcode=None):
    operands = [] if operands is None else operands
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "flow_type": flow_type,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _function_row(address: str, instructions):
    return {
        "format": m.INSTRUCTION_FORMAT,
        "program": m.PROGRAM,
        "requested": address,
        "found": True,
        "function": {
            "address": address,
            "name": "FUN_" + address[2:],
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _rank(path: Path, selected=None):
    selected = ["0x00410000"] if selected is None else selected
    functions = []
    for index, function in enumerate(selected):
        functions.append(
            {
                "function": function,
                "minimum_vehicle_anchor_distance": 1 if index == 0 else None,
            }
        )
    return _write_json(
        path,
        {
            "format": m.RANK_FORMAT,
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": "0x00bc185c",
                "runtime_manager_instance_identity_proven": False,
            },
            "ranking": {
                "selected_instruction_export_functions": selected,
                "functions": functions,
            },
        },
    )


def _positive_instructions(path: Path):
    instructions = [
        _ins(
            "0x00410000",
            "MOV",
            ["ESI", "dword ptr [0xbc185c]"],
            fallthrough="0x00410006",
            pcode=[
                _pcode(
                    "LOAD",
                    "ESI = LOAD ram(0xbc185c)",
                    output={"text": "ESI", "register": True},
                )
            ],
        ),
        _ins(
            "0x00410006",
            "MOV",
            ["EAX", "dword ptr [ESI + 0xca4]"],
            fallthrough="0x0041000c",
            pcode=[
                _pcode(
                    "LOAD",
                    "EAX = LOAD ram(ESI + 0xca4)",
                    output={"text": "EAX", "register": True},
                )
            ],
        ),
        _ins("0x0041000c", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    return _write_jsonl(path, [_function_row("0x00410000", instructions)])


def test_proves_exact_global_value_as_ca4_field_base_without_class_identity(tmp_path):
    rank = _rank(tmp_path / "rank.json")
    instructions = _positive_instructions(tmp_path / "instructions.jsonl")
    report = m.analyze(rank, instructions)

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["analysis"]["pcode_backed_ca4_access_count"] == 1
    assert report["analysis"]["exact_candidate_global_value_alias_count"] == 1
    assert report["analysis"]["exact_alias_with_bounded_vehicle_callgraph_proximity_count"] == 1

    access = report["analysis"]["field_accesses"][0]
    assert access["base_register"] == "ESI"
    assert access["field_offset_hex"] == "+0xca4"
    assert access["base_origins_before_access"] == ["memory:dword ptr [0xbc185c]"]
    assert access["exact_single_candidate_global_value_as_field_base"] is True
    assert access["semantic_manager_class_identity_proven"] is False
    assert access["semantic_player_vehicle_renderables_identity_proven"] is False

    assert report["handoff"]["candidate_global_to_ca4_runtime_field_base_alias_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is True
    assert report["handoff"]["candidate_global_render_manager_class_identity_ready"] is False
    assert report["handoff"]["player_vehicle_renderables_owner_join_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_accepts_DAT_symbol_rendering_for_global_origin(tmp_path):
    rank = _rank(tmp_path / "rank.json")
    rows = [json.loads(line) for line in _positive_instructions(tmp_path / "instructions.jsonl").read_text().splitlines()]
    first = rows[0]["instructions"][0]
    first["operands"][1] = "dword ptr [DAT_00bc185c]"
    first["text"] = "MOV ESI,dword ptr [DAT_00bc185c]"
    _write_jsonl(tmp_path / "instructions.jsonl", rows)
    report = m.analyze(rank, tmp_path / "instructions.jsonl")
    assert report["ready"] is True
    assert report["analysis"]["field_accesses"][0]["candidate_global_memory_origins"] == [
        "memory:dword ptr [dat_00bc185c]"
    ]


def test_call_clobber_blocks_ecx_alias(tmp_path):
    rank = _rank(tmp_path / "rank.json")
    instructions = [
        _ins(
            "0x00410000",
            "MOV",
            ["ECX", "dword ptr [0xbc185c]"],
            fallthrough="0x00410006",
            pcode=[
                _pcode(
                    "LOAD",
                    "ECX = LOAD ram(0xbc185c)",
                    output={"text": "ECX", "register": True},
                )
            ],
        ),
        _ins(
            "0x00410006",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x0041000b",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins(
            "0x0041000b",
            "MOV",
            ["EAX", "dword ptr [ECX + 0xca4]"],
            fallthrough="0x00410011",
            pcode=[
                _pcode(
                    "LOAD",
                    "EAX = LOAD ram(ECX + 0xca4)",
                    output={"text": "EAX", "register": True},
                )
            ],
        ),
        _ins("0x00410011", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    export = _write_jsonl(tmp_path / "instructions.jsonl", [_function_row("0x00410000", instructions)])
    report = m.analyze(rank, export)
    assert report["ready"] is False
    access = report["analysis"]["field_accesses"][0]
    assert access["exact_single_candidate_global_value_as_field_base"] is False
    assert access["base_origins_before_access"] == ["unknown:ECX@0x00410006:call-clobber"]


def test_rejects_instruction_target_set_drift(tmp_path):
    rank = _rank(tmp_path / "rank.json", selected=["0x00410000", "0x00420000"])
    instructions = _positive_instructions(tmp_path / "instructions.jsonl")
    with pytest.raises(ValueError, match="target set disagrees"):
        m.analyze(rank, instructions)


def test_ca4_operand_without_pcode_load_store_does_not_enter_alias_set(tmp_path):
    rank = _rank(tmp_path / "rank.json")
    rows = [json.loads(line) for line in _positive_instructions(tmp_path / "instructions.jsonl").read_text().splitlines()]
    rows[0]["instructions"][1]["pcode"] = []
    export = _write_jsonl(tmp_path / "instructions.jsonl", rows)
    report = m.analyze(rank, export)
    assert report["ready"] is False
    assert report["analysis"]["pcode_backed_ca4_access_count"] == 0
    assert report["analysis"]["exact_candidate_global_value_alias_count"] == 0
