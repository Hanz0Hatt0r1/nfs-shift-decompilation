from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_player_vehicle_renderables_owner_transfer_frontier.py"
SPEC = importlib.util.spec_from_file_location("build_player_vehicle_renderables_owner_transfer_frontier", TOOL)
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
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _rank(path: Path, selected=None, *, current=True):
    selected = ["0x00410000"] if selected is None else selected
    fmt = m.RANK_FORMAT if current else m._alias.RANK_FORMAT
    payload = {
        "format": fmt,
        "ready": True,
        "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
        "candidate_global": {
            "address": "0x00bc185c",
            "runtime_manager_instance_identity_proven": False,
        },
        "ranking": {
            "selected_instruction_export_functions": selected,
            "functions": [
                {"function": function, "minimum_vehicle_anchor_distance": 1}
                for function in selected
            ],
        },
    }
    if current:
        payload["handoff"] = {
            "root_pose_positive_anchor_ranking_ready": True,
            "collision_wheel_LOD_anchor_removed_from_positive_render_score": True,
        }
    return _write_json(path, payload)


def _base_prefix():
    return [
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
    ]


def _inputs(tmp_path: Path, instructions, *, current_rank=True):
    rank = _rank(tmp_path / "rank.json", current=current_rank)
    export = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [_function_row("0x00410000", instructions)],
    )
    alias_report = m._alias.analyze(rank, export)
    assert alias_report["ready"] is True
    alias_path = _write_json(tmp_path / "alias.json", alias_report)
    return alias_path, rank, export


def test_extracts_exact_direct_receiver_transfer_and_deduped_worklist(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x0041000c",
            "MOV",
            ["EBX", "EAX"],
            fallthrough="0x0041000e",
            pcode=[_pcode("COPY", "EBX = EAX", output={"text": "EBX", "register": True})],
        ),
        _ins(
            "0x0041000e",
            "MOV",
            ["ECX", "EBX"],
            fallthrough="0x00410010",
            pcode=[_pcode("COPY", "ECX = EBX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410010",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x00410015",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins(
            "0x00410015",
            "MOV",
            ["ECX", "EBX"],
            fallthrough="0x00410017",
            pcode=[_pcode("COPY", "ECX = EBX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410017",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x0041001c",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins("0x0041001c", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(alias_path, rank, export)

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["provenance"]["seedable_pointer_load_count"] == 1
    calls = [
        sink
        for sink in report["analysis"]["all_sinks"]
        if sink["kind"] == "direct-call-register-transfer"
    ]
    assert [sink["instruction"] for sink in calls] == ["0x00410010", "0x00410017"]
    assert all(sink["source_register"] == "ECX" for sink in calls)
    assert all(sink["direct_target"] == "0x00600000" for sink in calls)
    assert report["targeted_instruction_worklist"]["functions"] == ["0x00600000"]
    assert report["targeted_instruction_worklist"]["neighbors_added"] is False
    assert report["handoff"]["player_vehicle_renderables_direct_transfer_worklist_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_owner_join_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_cfg_merge_does_not_promote_ambiguous_ecx_to_exact_receiver(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x0041000c",
            "JZ",
            ["0x00410014"],
            flows=["0x00410014"],
            fallthrough="0x0041000e",
            flow_type="CONDITIONAL_JUMP",
            pcode=[],
        ),
        _ins(
            "0x0041000e",
            "MOV",
            ["ECX", "EAX"],
            fallthrough="0x00410012",
            pcode=[_pcode("COPY", "ECX = EAX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410012",
            "JMP",
            ["0x00410018"],
            flows=["0x00410018"],
            flow_type="UNCONDITIONAL_JUMP",
            pcode=[],
        ),
        _ins(
            "0x00410014",
            "XOR",
            ["ECX", "ECX"],
            fallthrough="0x00410018",
            pcode=[_pcode("INT_XOR", "ECX = ECX ^ ECX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410018",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x0041001d",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins("0x0041001d", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(alias_path, rank, export)
    calls = [
        sink
        for sink in report["analysis"]["all_sinks"]
        if sink["kind"] == "direct-call-register-transfer"
    ]
    assert calls == []
    assert report["targeted_instruction_worklist"]["functions"] == []
    assert report["ready"] is False


def test_caller_saved_clobber_kills_field_value_before_later_transfer(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x0041000c",
            "CALL",
            ["0x00500000"],
            flows=["0x00500000"],
            fallthrough="0x00410011",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00500000")],
        ),
        _ins(
            "0x00410011",
            "MOV",
            ["ECX", "EAX"],
            fallthrough="0x00410013",
            pcode=[_pcode("COPY", "ECX = EAX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410013",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x00410018",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins("0x00410018", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(alias_path, rank, export)
    assert report["ready"] is False
    assert report["targeted_instruction_worklist"]["functions"] == []


def test_records_memory_store_without_promoting_destination_owner(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x0041000c",
            "MOV",
            ["dword ptr [EDI + 0x24]", "EAX"],
            fallthrough="0x00410012",
            pcode=[_pcode("STORE", "STORE ram(EDI + 0x24) = EAX")],
        ),
        _ins("0x00410012", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(alias_path, rank, export)
    stores = [sink for sink in report["analysis"]["all_sinks"] if sink["kind"] == "memory-store"]
    assert len(stores) == 1
    assert stores[0]["destination_base_register"] == "EDI"
    assert stores[0]["destination_displacement_hex"] == "0x24"
    assert stores[0]["destination_object_identity_proven"] is False
    assert report["ready"] is True
    assert report["targeted_instruction_worklist"]["functions"] == []


def test_rejects_alias_proof_rooted_in_legacy_rank(tmp_path):
    instructions = _base_prefix() + [
        _ins("0x0041000c", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions, current_rank=False)
    with pytest.raises(ValueError, match="not rooted in the current root-pose-aware rank"):
        m.build_frontier(alias_path, rank, export)


def test_direct_target_cap_is_fail_closed(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x0041000c",
            "MOV",
            ["EBX", "EAX"],
            fallthrough="0x0041000e",
            pcode=[_pcode("COPY", "EBX = EAX", output={"text": "EBX", "register": True})],
        ),
        _ins(
            "0x0041000e",
            "MOV",
            ["ECX", "EBX"],
            fallthrough="0x00410010",
            pcode=[_pcode("COPY", "ECX = EBX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410010",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x00410015",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins(
            "0x00410015",
            "MOV",
            ["ECX", "EBX"],
            fallthrough="0x00410017",
            pcode=[_pcode("COPY", "ECX = EBX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410017",
            "CALL",
            ["0x00610000"],
            flows=["0x00610000"],
            fallthrough="0x0041001c",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00610000")],
        ),
        _ins("0x0041001c", "RET", [], flow_type="TERMINATOR", pcode=[]),
    ]
    alias_path, rank, export = _inputs(tmp_path, instructions)
    with pytest.raises(ValueError, match="exceeding cap 1"):
        m.build_frontier(alias_path, rank, export, max_direct_targets=1)
