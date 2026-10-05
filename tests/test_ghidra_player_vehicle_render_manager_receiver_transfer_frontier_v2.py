from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_player_vehicle_render_manager_receiver_transfer_frontier_v2.py"
SPEC = importlib.util.spec_from_file_location(
    "build_player_vehicle_render_manager_receiver_transfer_frontier_v2", TOOL
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


def _identity(path: Path) -> Path:
    return _write_json(
        path,
        {
            "format": m._v1.IDENTITY_FORMAT,
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
                "all_write_xrefs_accounted_for": True,
                "non_null_values_are_FUN_0045ef50_receivers": True,
            },
            "inputs": {
                "root_pose_rank": {
                    "format": m._v1.RANK_FORMAT,
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


def _rank(path: Path, instruction_text: str = "MOV ESI,dword ptr [0x00bc185c]") -> Path:
    return _write_json(
        path,
        {
            "format": m._v1.RANK_FORMAT,
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
                                "instruction": instruction_text,
                            }
                        ],
                    }
                ],
            },
        },
    )


def _ins(
    address: str,
    mnemonic: str,
    operands: list[str],
    *,
    fallthrough: str | None = None,
    flows: list[str] | None = None,
    flow_type: str = "FALL_THROUGH",
    pcode: list[dict] | None = None,
) -> dict:
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ",".join(operands) if operands else ""),
        "operands": operands,
        "flow_type": flow_type,
        "fallthrough": fallthrough,
        "flows": [] if flows is None else flows,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _row(instructions: list[dict]) -> dict:
    return {
        "format": m._v1.INSTRUCTION_FORMAT,
        "program": m.PROGRAM,
        "requested": "0x00410000",
        "found": True,
        "function": {
            "address": "0x00410000",
            "name": "FUN_00410000",
            "size": len(instructions),
            "calling_convention": "__thiscall",
        },
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _inputs(tmp_path: Path, first_instruction: dict) -> tuple[Path, Path, Path]:
    identity = _identity(tmp_path / "identity.json")
    rank = _rank(tmp_path / "rank.json", first_instruction["text"])
    instructions = [
        first_instruction,
        _ins(
            "0x00410006",
            "MOV",
            ["ECX", "ESI"],
            fallthrough="0x00410008",
        ),
        _ins(
            "0x00410008",
            "CALL",
            ["0x00600000"],
            fallthrough="0x0041000d",
            flows=["0x00600000"],
            flow_type="UNCONDITIONAL_CALL",
        ),
        _ins("0x0041000d", "RET", [], flow_type="TERMINATOR"),
    ]
    export = _write_jsonl(tmp_path / "instructions.jsonl", [_row(instructions)])
    return identity, rank, export


def _machine_load(source: str = "dword ptr [0x00bc185c]", *, mnemonic: str = "MOV") -> dict:
    return _ins(
        "0x00410000",
        mnemonic,
        ["ESI", source],
        fallthrough="0x00410006",
        # Deliberately no matching raw LOAD p-code: this is the retail failure
        # mode that v2 must admit from machine evidence rather than p-code shape.
        pcode=[],
    )


def test_machine_backed_exact_global_read_seeds_without_raw_load_shape(tmp_path):
    identity, rank, export = _inputs(tmp_path, _machine_load())
    report = m.build_frontier(identity, rank, export)

    assert report["format"] == "SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2"
    assert report["ready"] is True
    assert report["status"] == "direct-manager-method-worklist-ready"
    assert report["provenance"]["exact_global_read_xref_count"] == 1
    assert report["provenance"]["seedable_global_read_count"] == 1
    assert report["provenance"]["direct_call_receiver_transfer_count"] == 1
    assert report["targeted_instruction_worklist"]["functions"] == ["0x00600000"]

    seed = report["analysis"]["seeds"][0]
    assert seed["destination_register"] == "ESI"
    assert seed["exact_rank_global_read_xref"] is True
    assert seed["exact_machine_MOV_absolute_global_load"] is True
    assert seed["all_path_single_global_origin_after_read"] is True
    assert seed["raw_pcode_load_shape_matches_destination"] is False
    assert seed["raw_pcode_load_shape_required_for_seed"] is False


def test_rank_read_cannot_seed_wrong_absolute_memory_source(tmp_path):
    identity, rank, export = _inputs(tmp_path, _machine_load("dword ptr [0x00bc1860]"))
    report = m.build_frontier(identity, rank, export)
    assert report["ready"] is False
    assert report["provenance"]["seedable_global_read_count"] == 0
    assert report["analysis"]["skipped_reads"][0]["reason"] == (
        "read-does-not-yield-one-exact-machine-backed-tracked-register"
    )


def test_rank_read_cannot_seed_base_relative_operand_with_matching_displacement(tmp_path):
    identity, rank, export = _inputs(tmp_path, _machine_load("dword ptr [EAX + 0x00bc185c]"))
    report = m.build_frontier(identity, rank, export)
    assert report["ready"] is False
    assert report["provenance"]["seedable_global_read_count"] == 0


def test_rank_read_cannot_seed_non_mov_address_materialization(tmp_path):
    identity, rank, export = _inputs(tmp_path, _machine_load("[0x00bc185c]", mnemonic="LEA"))
    report = m.build_frontier(identity, rank, export)
    assert report["ready"] is False
    assert report["provenance"]["seedable_global_read_count"] == 0


def test_direct_absolute_memory_parser_accepts_retail_spellings_only():
    expected = int(m.CANDIDATE_GLOBAL, 16)
    assert m._direct_absolute_memory_address("[0x00bc185c]") == expected
    assert m._direct_absolute_memory_address("dword ptr [0x00bc185c]") == expected
    assert m._direct_absolute_memory_address("[DAT_00bc185c]") == expected
    assert m._direct_absolute_memory_address("[EAX + 0x00bc185c]") is None
    assert m._direct_absolute_memory_address("0x00bc185c") is None


def test_v1_seed_function_is_restored_after_v2_build(tmp_path):
    original = m._v1._seed_from_read
    identity, rank, export = _inputs(tmp_path, _machine_load())
    m.build_frontier(identity, rank, export)
    assert m._v1._seed_from_read is original


def test_rejects_invalid_target_cap(tmp_path):
    identity, rank, export = _inputs(tmp_path, _machine_load())
    with pytest.raises(ValueError, match="max_direct_targets must be positive"):
        m.build_frontier(identity, rank, export, max_direct_targets=0)
