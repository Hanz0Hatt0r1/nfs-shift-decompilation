from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_player_vehicle_render_manager_receiver_transfer_frontier.py"
SPEC = importlib.util.spec_from_file_location("build_player_vehicle_render_manager_receiver_transfer_frontier", TOOL)
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


def _identity(path: Path, *, ready=True):
    return _write_json(
        path,
        {
            "format": m.IDENTITY_FORMAT,
            "ready": ready,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
                "all_write_xrefs_accounted_for": True,
                "non_null_values_are_FUN_0045ef50_receivers": True,
            },
            "inputs": {
                "root_pose_rank": {
                    "format": m.RANK_FORMAT,
                    "ranked_function_count": 1,
                    "selected_function_count": 1,
                    "candidate_global_write_xrefs_exhaustive": True,
                }
            },
            "handoff": {
                "candidate_global_render_manager_class_identity_ready": True,
                "candidate_global_non_null_FUN_0045ef50_receiver_ready": True,
                "constructor_player_vehicle_renderables_layout_anchor_ready": True,
                "player_vehicle_renderables_field_runtime_access_ready": False,
                "player_vehicle_renderables_owner_join_ready": False,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
                "BODY0_bind_frame_proof_ready": False,
            },
        },
    )


def _rank(path: Path):
    return _write_json(
        path,
        {
            "format": m.RANK_FORMAT,
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
                "runtime_manager_instance_identity_proven": False,
            },
            "handoff": {
                "root_pose_positive_anchor_ranking_ready": True,
                "collision_wheel_LOD_anchor_removed_from_positive_render_score": True,
            },
            "ranking": {
                "ranked_function_count": 1,
                "selected_instruction_export_functions": ["0x00410000"],
                "functions": [
                    {
                        "function": "0x00410000",
                        "reference_sites": [
                            {
                                "type": "READ",
                                "from": "0x00410000",
                                "instruction": "MOV ESI,[0xbc185c]",
                            }
                        ],
                    }
                ],
            },
        },
    )


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
        )
    ]


def _inputs(tmp_path: Path, instructions, *, identity_ready=True):
    identity = _identity(tmp_path / "identity.json", ready=identity_ready)
    rank = _rank(tmp_path / "rank.json")
    export = _write_jsonl(
        tmp_path / "instructions.jsonl",
        [_function_row("0x00410000", instructions)],
    )
    return identity, rank, export


def test_builds_direct_manager_method_worklist(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x00410006",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x00410008",
            pcode=[_pcode("COPY", "ECX = ESI", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410008",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x0041000d",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins("0x0041000d", "RET", [], flow_type="TERMINATOR"),
    ]
    identity, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(identity, rank, export)

    assert report["ready"] is True
    assert report["status"] == "direct-manager-method-worklist-ready"
    assert report["provenance"]["seedable_global_read_count"] == 1
    assert report["provenance"]["direct_call_receiver_transfer_count"] == 1
    transfer = report["analysis"]["call_receiver_transfers"][0]
    assert transfer["source_register"] == "ECX"
    assert transfer["direct_target"] == "0x00600000"
    assert transfer["manager_receiver_identity_proven"] is True
    assert transfer["callee_ca4_access_proven"] is False
    assert report["targeted_instruction_worklist"]["functions"] == ["0x00600000"]
    assert report["targeted_instruction_worklist"]["neighbors_added"] is False
    assert report["handoff"]["candidate_global_manager_direct_method_worklist_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_records_indirect_receiver_dispatch_without_inventing_target(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x00410006",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x00410008",
            pcode=[_pcode("COPY", "ECX = ESI", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410008",
            "MOV",
            ["EAX", "dword ptr [ECX]"],
            fallthrough="0x0041000a",
            pcode=[
                _pcode(
                    "LOAD",
                    "EAX = LOAD ram(ECX)",
                    output={"text": "EAX", "register": True},
                )
            ],
        ),
        _ins(
            "0x0041000a",
            "CALL",
            ["dword ptr [EAX + 0x10]"],
            flows=[],
            fallthrough="0x0041000f",
            flow_type="COMPUTED_CALL",
            pcode=[_pcode("CALLIND", "CALLIND EAX")],
        ),
        _ins("0x0041000f", "RET", [], flow_type="TERMINATOR"),
    ]
    identity, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(identity, rank, export)

    assert report["ready"] is True
    assert report["status"] == "indirect-manager-dispatch-frontier-ready"
    assert report["targeted_instruction_worklist"]["functions"] == []
    assert report["handoff"]["candidate_global_manager_indirect_dispatch_frontier_ready"] is True
    transfer = report["analysis"]["call_receiver_transfers"][0]
    assert transfer["kind"] == "indirect-call-manager-receiver-transfer"
    assert transfer["direct_target"] is None
    assert transfer["callee_method_identity_proven"] is False


def test_cfg_merge_does_not_promote_ambiguous_ecx_receiver(tmp_path):
    instructions = _base_prefix() + [
        _ins(
            "0x00410006",
            "JZ",
            ["0x0041000e"],
            flows=["0x0041000e"],
            fallthrough="0x00410008",
            flow_type="CONDITIONAL_JUMP",
        ),
        _ins(
            "0x00410008",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x0041000a",
            pcode=[_pcode("COPY", "ECX = ESI", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x0041000a",
            "JMP",
            ["0x00410012"],
            flows=["0x00410012"],
            flow_type="UNCONDITIONAL_JUMP",
        ),
        _ins(
            "0x0041000e",
            "XOR",
            ["ECX", "ECX"],
            fallthrough="0x00410012",
            pcode=[_pcode("INT_XOR", "ECX = ECX ^ ECX", output={"text": "ECX", "register": True})],
        ),
        _ins(
            "0x00410012",
            "CALL",
            ["0x00600000"],
            flows=["0x00600000"],
            fallthrough="0x00410017",
            flow_type="UNCONDITIONAL_CALL",
            pcode=[_pcode("CALL", "CALL 0x00600000")],
        ),
        _ins("0x00410017", "RET", [], flow_type="TERMINATOR"),
    ]
    identity, rank, export = _inputs(tmp_path, instructions)
    report = m.build_frontier(identity, rank, export)

    assert report["ready"] is False
    assert report["analysis"]["call_receiver_transfers"] == []
    assert report["targeted_instruction_worklist"]["functions"] == []


def test_rejects_non_positive_constructor_identity(tmp_path):
    instructions = _base_prefix() + [_ins("0x00410006", "RET", [], flow_type="TERMINATOR")]
    identity, rank, export = _inputs(tmp_path, instructions, identity_ready=False)
    with pytest.raises(ValueError, match="expected ready"):
        m.build_frontier(identity, rank, export)
