from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_player_vehicle_render_manager_method_ca4_access.py"
SPEC = importlib.util.spec_from_file_location("analyze_player_vehicle_render_manager_method_ca4_access", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _identity(path: Path):
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


def _frontier(path: Path, *, entry_register="ECX", target="0x00600000"):
    role = "this/arg-ecx" if entry_register == "ECX" else "arg-edx"
    return _write_json(
        path,
        {
            "format": m.FRONTIER_FORMAT,
            "version": 2,
            "status": "direct-manager-method-worklist-ready",
            "ready": True,
            "retail": {"program": m.PROGRAM, "md5": m.PE_MD5},
            "candidate_global": {
                "address": m.CANDIDATE_GLOBAL,
                "render_manager_class_identity_proven": True,
                "non_null_FUN_0045ef50_receiver_proven": True,
            },
            "inputs": {
                "constructor_identity": {"format": m._v1.IDENTITY_FORMAT, "ready": True}
            },
            "provenance": {
                "direct_call_receiver_transfer_count": 1,
            },
            "analysis": {
                "call_receiver_transfers": [
                    {
                        "kind": "direct-call-manager-receiver-transfer",
                        "function": "0x00410000",
                        "instruction": "0x00410010",
                        "source_register": entry_register,
                        "register_role": role,
                        "direct_target": target,
                        "manager_receiver_identity_proven": True,
                        "callee_method_identity_proven": True,
                    }
                ]
            },
            "targeted_instruction_worklist": {
                "functions": [target],
                "function_count": 1,
                "max_functions": 64,
                "neighbors_added": False,
            },
            "handoff": {
                "candidate_global_manager_receiver_transfer_frontier_ready": True,
                "candidate_global_manager_direct_method_worklist_ready": True,
                "candidate_global_manager_indirect_dispatch_frontier_ready": False,
                "player_vehicle_renderables_field_runtime_access_ready": False,
                "player_vehicle_renderables_owner_join_ready": False,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
                "BODY0_bind_frame_proof_ready": False,
                "vehicle_world_transform_ready": False,
            },
        },
    )


def _ins(address, mnemonic, operands=None, *, fallthrough=None, pcode=None, flow_type="FALL_THROUGH"):
    operands = [] if operands is None else operands
    return {
        "address": address,
        "bytes": "90",
        "mnemonic": mnemonic,
        "text": mnemonic + (" " + ", ".join(operands) if operands else ""),
        "operands": operands,
        "fallthrough": fallthrough,
        "flows": [],
        "flow_type": flow_type,
        "references": [],
        "pcode": [] if pcode is None else pcode,
    }


def _row(address: str, instructions):
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


def _read_lane(entry_register="ECX"):
    source = entry_register
    return [
        _ins("0x00600000", "MOV", ["ESI", source], fallthrough="0x00600002"),
        _ins(
            "0x00600002",
            "MOV",
            ["EAX", "dword ptr [ESI + 0xca4]"],
            fallthrough="0x00600008",
            pcode=[{"opcode": "LOAD", "text": "LOAD manager_plus_ca4"}],
        ),
        _ins("0x00600008", "RET", [], flow_type="TERMINATOR"),
    ]


def _inputs(tmp_path: Path, instructions, *, entry_register="ECX", target="0x00600000"):
    identity = _identity(tmp_path / "identity.json")
    frontier = _frontier(tmp_path / "frontier.json", entry_register=entry_register, target=target)
    export = _write_jsonl(tmp_path / "callees.jsonl", [_row(target, instructions)])
    return identity, frontier, export


def test_proves_ecx_entry_pointer_ca4_read(tmp_path):
    identity, frontier, export = _inputs(tmp_path, _read_lane("ECX"))
    report = m.analyze(identity, frontier, export)

    assert report["ready"] is True
    assert report["status"] == "manager-method-ca4-read-ready"
    assert report["provenance"]["exact_entry_pointer_ca4_access_count"] == 1
    assert report["provenance"]["exact_entry_pointer_ca4_read_count"] == 1
    proof = report["analysis"]["proven_ca4_reads"][0]
    assert proof["base_origins_before_access"] == ["entry:ECX"]
    assert proof["matching_manager_entry_registers"] == ["ECX"]
    assert proof["player_vehicle_renderables_field_identity_proven"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_owner_join_ready"] is False
    assert report["owner_trace_worklist"]["functions"] == ["0x00600000"]


def test_proves_edx_entry_pointer_ca4_read(tmp_path):
    identity, frontier, export = _inputs(
        tmp_path,
        _read_lane("EDX"),
        entry_register="EDX",
    )
    report = m.analyze(identity, frontier, export)

    assert report["ready"] is True
    proof = report["analysis"]["proven_ca4_reads"][0]
    assert proof["base_origins_before_access"] == ["entry:EDX"]
    assert proof["matching_manager_entry_registers"] == ["EDX"]


def test_rejects_ca4_access_from_wrong_entry_register(tmp_path):
    identity, frontier, export = _inputs(
        tmp_path,
        _read_lane("ECX"),
        entry_register="EDX",
    )
    report = m.analyze(identity, frontier, export)

    assert report["ready"] is False
    assert report["status"] == "manager-method-ca4-access-not-found"
    assert report["provenance"]["ca4_syntactic_pcode_backed_access_count"] == 1
    assert report["provenance"]["exact_entry_pointer_ca4_access_count"] == 0
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is False


def test_write_only_ca4_relation_does_not_admit_owner_trace(tmp_path):
    instructions = [
        _ins("0x00600000", "MOV", ["ESI", "ECX"], fallthrough="0x00600002"),
        _ins(
            "0x00600002",
            "MOV",
            ["dword ptr [ESI + 0xca4]", "EAX"],
            fallthrough="0x00600008",
            pcode=[{"opcode": "STORE", "text": "STORE manager_plus_ca4"}],
        ),
        _ins("0x00600008", "RET", [], flow_type="TERMINATOR"),
    ]
    identity, frontier, export = _inputs(tmp_path, instructions)
    report = m.analyze(identity, frontier, export)

    assert report["ready"] is False
    assert report["status"] == "manager-method-ca4-write-only"
    assert report["provenance"]["exact_entry_pointer_ca4_access_count"] == 1
    assert report["provenance"]["exact_entry_pointer_ca4_read_count"] == 0
    assert report["handoff"]["candidate_global_manager_method_ca4_access_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] is False
    assert report["owner_trace_worklist"]["functions"] == []


def test_rejects_targeted_instruction_set_drift(tmp_path):
    identity = _identity(tmp_path / "identity.json")
    frontier = _frontier(tmp_path / "frontier.json", target="0x00600000")
    export = _write_jsonl(
        tmp_path / "callees.jsonl",
        [_row("0x00600010", _read_lane("ECX"))],
    )
    with pytest.raises(ValueError, match="instruction target set disagrees"):
        m.analyze(identity, frontier, export)


def test_rejects_frontier_downstream_preclaim(tmp_path):
    identity = _identity(tmp_path / "identity.json")
    frontier_path = _frontier(tmp_path / "frontier.json")
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    frontier["handoff"]["player_vehicle_renderables_field_runtime_access_ready"] = True
    frontier_path.write_text(json.dumps(frontier) + "\n", encoding="utf-8")
    export = _write_jsonl(tmp_path / "callees.jsonl", [_row("0x00600000", _read_lane("ECX"))])

    with pytest.raises(ValueError, match="unexpectedly preclaims downstream gate"):
        m.analyze(identity, frontier_path, export)
