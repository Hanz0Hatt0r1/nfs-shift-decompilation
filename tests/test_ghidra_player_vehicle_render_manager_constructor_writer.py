from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_constructor_writer.py"
SPEC = importlib.util.spec_from_file_location(
    "analyze_player_vehicle_render_manager_constructor_writer", TOOL
)
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


def _ins(
    address,
    mnemonic,
    operands=None,
    *,
    fallthrough=None,
    flows=None,
    flow_type="FALL_THROUGH",
    pcode=None,
):
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
            "calling_convention": "__fastcall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _alias(path: Path, *, count=80, exact_alias_count=0, ca4_count=0):
    return _write_json(
        path,
        {
            "format": m.ALIAS_FORMAT,
            "ready": False,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
                "runtime_manager_class_identity_proven": False,
            },
            "analysis": {
                "selected_function_count": count,
                "exact_candidate_global_value_alias_count": exact_alias_count,
                "pcode_backed_ca4_access_count": ca4_count,
                "field_accesses": [],
            },
        },
    )


def _rank(path: Path, *, selected_count=80, extra_write=None):
    selected = [m.WRITER]
    for index in range(selected_count - 1):
        selected.append(f"0x{0x00500000 + index * 0x10:08x}")
    functions = [
        {
            "function": m.WRITER,
            "reference_sites": [
                {
                    "from": m.WRITER_GLOBAL_STORE,
                    "type": "WRITE",
                    "instruction": "MOV [0x00bc185c],EAX",
                },
                {
                    "from": m.WRITER_NULL_STORE,
                    "type": "WRITE",
                    "instruction": "MOV dword ptr [0x00bc185c],ESI",
                },
            ],
        }
    ]
    functions.extend(
        {"function": address, "reference_sites": []}
        for address in selected[1:]
    )
    if extra_write is not None:
        functions[1]["reference_sites"] = [
            {
                "from": extra_write,
                "type": "WRITE",
                "instruction": "MOV [0x00bc185c],EAX",
            }
        ]
    return _write_json(
        path,
        {
            "format": m.RANK_FORMAT,
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {"address": m.CANDIDATE_GLOBAL},
            "ranking": {
                "ranked_function_count": 80,
                "selected_instruction_export_functions": selected,
                "functions": functions,
            },
        },
    )


def _constructor_instructions(*, return_receiver=True):
    final_source = "ESI" if return_receiver else "EBX"
    return [
        _ins(m.CONSTRUCTOR, "NOP", [], fallthrough=m.CTOR_RECEIVER_SAVE),
        _ins(
            m.CTOR_RECEIVER_SAVE,
            "MOV",
            ["ESI", "ECX"],
            fallthrough=m.CTOR_LABEL_PUSH,
            pcode=[
                _pcode(
                    "COPY",
                    "ESI = ECX",
                    output={"text": "ESI", "register": True},
                )
            ],
        ),
        _ins(m.CTOR_LABEL_PUSH, "PUSH", [m.CTOR_LABEL_ADDRESS], fallthrough=m.CTOR_CAPACITY_PUSH),
        _ins(m.CTOR_CAPACITY_PUSH, "PUSH", ["0x400"], fallthrough=m.CTOR_ALLOC_CALL_1),
        _ins(
            m.CTOR_ALLOC_CALL_1,
            "CALL",
            ["0x00695e30"],
            fallthrough=m.CTOR_ALLOC_CALL_2,
            flows=["0x00695e30"],
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00695e30")],
        ),
        _ins(
            m.CTOR_ALLOC_CALL_2,
            "CALL",
            ["0x00695f10"],
            fallthrough=m.CTOR_ALLOC_CALL_3,
            flows=["0x00695f10"],
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00695f10")],
        ),
        _ins(
            m.CTOR_ALLOC_CALL_3,
            "CALL",
            ["0x0068a700"],
            fallthrough=m.CTOR_FIELD_STORE,
            flows=["0x0068a700"],
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x0068a700")],
        ),
        _ins(
            m.CTOR_FIELD_STORE,
            "MOV",
            ["dword ptr [ESI + 0xca4]", "EAX"],
            fallthrough="0x0045f5e0",
            pcode=[_pcode("STORE", "STORE [ESI + 0xca4] = EAX")],
        ),
        _ins(
            "0x0045f5e0",
            "MOV",
            ["EAX", final_source],
            fallthrough="0x0045f5e2",
            pcode=[
                _pcode(
                    "COPY",
                    f"EAX = {final_source}",
                    output={"text": "EAX", "register": True},
                )
            ],
        ),
        _ins("0x0045f5e2", "RET", [], flow_type="TERMINATOR"),
    ]


def _writer_instructions(*, ctor_target=None):
    ctor_target = m.CONSTRUCTOR if ctor_target is None else ctor_target
    return [
        _ins(m.WRITER, "NOP", [], fallthrough=m.WRITER_ZERO_ESI),
        _ins(
            m.WRITER_ZERO_ESI,
            "XOR",
            ["ESI", "ESI"],
            fallthrough=m.WRITER_ALLOC_SIZE,
            pcode=[
                _pcode(
                    "INT_XOR",
                    "ESI = ESI XOR ESI",
                    output={"text": "ESI", "register": True},
                )
            ],
        ),
        _ins(m.WRITER_ALLOC_SIZE, "PUSH", ["0x46e0"], fallthrough=m.WRITER_ALLOC_CALL),
        _ins(
            m.WRITER_ALLOC_CALL,
            "CALL",
            [m.ALLOCATOR],
            fallthrough=m.WRITER_NULL_CMP,
            flows=[m.ALLOCATOR],
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", f"CALL {m.ALLOCATOR}")],
        ),
        _ins(m.WRITER_NULL_CMP, "CMP", ["EAX", "ESI"], fallthrough=m.WRITER_NULL_BRANCH),
        _ins(
            m.WRITER_NULL_BRANCH,
            "JZ",
            [m.WRITER_NULL_STORE],
            fallthrough=m.WRITER_RECEIVER_MOVE,
            flows=[m.WRITER_NULL_STORE],
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins(
            m.WRITER_RECEIVER_MOVE,
            "MOV",
            ["ECX", "EAX"],
            fallthrough=m.WRITER_CTOR_CALL,
            pcode=[
                _pcode(
                    "COPY",
                    "ECX = EAX",
                    output={"text": "ECX", "register": True},
                )
            ],
        ),
        _ins(
            m.WRITER_CTOR_CALL,
            "CALL",
            [ctor_target],
            fallthrough=m.WRITER_POST_CTOR_JUMP,
            flows=[ctor_target],
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", f"CALL {ctor_target}")],
        ),
        _ins(
            m.WRITER_POST_CTOR_JUMP,
            "JMP",
            [m.WRITER_GLOBAL_STORE],
            flows=[m.WRITER_GLOBAL_STORE],
            flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins(
            m.WRITER_GLOBAL_STORE,
            "MOV",
            ["[0x00bc185c]", "EAX"],
            fallthrough="0x00d362f1",
            pcode=[_pcode("COPY", "ram(0xbc185c) = EAX")],
        ),
        _ins("0x00d362f1", "RET", [], flow_type="TERMINATOR"),
        _ins(
            m.WRITER_NULL_STORE,
            "MOV",
            ["dword ptr [0x00bc185c]", "ESI"],
            fallthrough="0x00d362f9",
            pcode=[_pcode("COPY", "ram(0xbc185c) = ESI")],
        ),
        _ins("0x00d362f9", "RET", [], flow_type="TERMINATOR"),
    ]


def _instructions(path: Path, *, return_receiver=True, ctor_target=None, extra_row=False):
    rows = [
        _function_row(m.WRITER, _writer_instructions(ctor_target=ctor_target)),
        _function_row(m.CONSTRUCTOR, _constructor_instructions(return_receiver=return_receiver)),
    ]
    if extra_row:
        rows.append(_function_row("0x00400000", [_ins("0x00400000", "RET", [], flow_type="TERMINATOR")]))
    return _write_jsonl(path, rows)


def test_proves_all_non_null_global_writes_are_constructor_receivers(tmp_path):
    alias = _alias(tmp_path / "alias.json")
    rank = _rank(tmp_path / "rank.json")
    instructions = _instructions(tmp_path / "instructions.jsonl")

    report = m.analyze(alias, rank, instructions)

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["candidate_global"]["all_write_xrefs_accounted_for"] is True
    assert report["candidate_global"]["write_xref_count"] == 2
    assert report["candidate_global"]["non_null_values_are_FUN_0045ef50_receivers"] is True

    constructor = report["analysis"]["constructor"]
    assert constructor["field_anchor"]["field_offset"] == "+0xca4"
    assert constructor["field_anchor"]["allocation_label"] == "mPlayerVehicleRenderables"
    assert constructor["all_reachable_returns_entry_receiver"] is True
    assert constructor["reachable_returns"] == [
        {
            "instruction": "0x0045f5e2",
            "eax_origins_before_return": ["entry:ECX"],
            "returns_entry_ecx_receiver": True,
        }
    ]

    writer = report["analysis"]["writer"]
    assert writer["receiver_is_same_physical_allocator_result"] is True
    assert writer["null_store_esi_origins"] == ["immediate:0"]
    assert writer["null_store_is_zero"] is True
    assert writer["constructor_result_to_global_continuity_ready"] is True

    handoff = report["handoff"]
    assert handoff["candidate_global_render_manager_class_identity_ready"] is True
    assert handoff["candidate_global_non_null_FUN_0045ef50_receiver_ready"] is True
    assert handoff["constructor_player_vehicle_renderables_layout_anchor_ready"] is True
    assert handoff["candidate_global_to_ca4_runtime_field_base_alias_ready"] is False
    assert handoff["player_vehicle_renderables_field_runtime_access_ready"] is False
    assert handoff["player_vehicle_renderables_owner_join_ready"] is False
    assert handoff["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert handoff["BODY0_bind_frame_proof_ready"] is False
    assert handoff["vehicle_world_transform_ready"] is False


def test_constructor_return_must_be_entry_receiver_on_all_reachable_returns(tmp_path):
    report = m.analyze(
        _alias(tmp_path / "alias.json"),
        _rank(tmp_path / "rank.json"),
        _instructions(tmp_path / "instructions.jsonl", return_receiver=False),
    )
    assert report["ready"] is False
    assert report["analysis"]["constructor"]["all_reachable_returns_entry_receiver"] is False
    assert report["handoff"]["candidate_global_render_manager_class_identity_ready"] is False
    blocker_ids = {item["id"] for item in report["blockers"]}
    assert "render-manager-constructor-return-receiver-identity-unproven" in blocker_ids


def test_rejects_writer_constructor_target_drift(tmp_path):
    with pytest.raises(ValueError, match="constructor target drift"):
        m.analyze(
            _alias(tmp_path / "alias.json"),
            _rank(tmp_path / "rank.json"),
            _instructions(tmp_path / "instructions.jsonl", ctor_target="0x0045f640"),
        )


def test_rejects_non_exhaustive_alias_input(tmp_path):
    with pytest.raises(ValueError, match="exhaustive 80-function"):
        m.analyze(
            _alias(tmp_path / "alias.json", count=24),
            _rank(tmp_path / "rank.json"),
            _instructions(tmp_path / "instructions.jsonl"),
        )


def test_rejects_additional_candidate_global_writer(tmp_path):
    with pytest.raises(ValueError, match="WRITE-xref set drift"):
        m.analyze(
            _alias(tmp_path / "alias.json"),
            _rank(tmp_path / "rank.json", extra_write="0x00500008"),
            _instructions(tmp_path / "instructions.jsonl"),
        )


def test_rejects_instruction_target_set_drift(tmp_path):
    with pytest.raises(ValueError, match="target set drift"):
        m.analyze(
            _alias(tmp_path / "alias.json"),
            _rank(tmp_path / "rank.json"),
            _instructions(tmp_path / "instructions.jsonl", extra_row=True),
        )
