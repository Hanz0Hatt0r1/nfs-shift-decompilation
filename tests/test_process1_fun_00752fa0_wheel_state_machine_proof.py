from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "evidence/fun_00752fa0_wheel_state_machine_proof.json"
FRONTIER = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00752FA0_WHEEL_STATE_MACHINE_PROOF.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_callee_body_and_authority_are_pinned() -> None:
    proof = _load(PROOF)
    assert proof["format"] == "SHIFT.Fun00752fa0WheelStateMachineProof/1"
    assert proof["ready"] is True
    assert proof["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert proof["authority"]["callee_entry"] == "0x00752fa0"
    assert proof["callee_body"] == [
        "0x00752fa3: mov eax,[ebp+0x8]",
        "0x00752fa6: fld qword [ebp+0xc]",
        "0x00752fa9: fstp qword [ecx+0xa00]",
        "0x00752faf: mov dword [ecx+0x9f8],eax",
        "0x00752fb6: ret 0xc",
    ]


def test_caller_join_and_vehicle_offsets_are_exact() -> None:
    proof = _load(PROOF)
    join = proof["caller_join"]
    assert join["caller"] == "FUN_00765c40"
    assert join["call_site"] == "0x00765ec1"
    assert join["receiver_first"] == "HDVehicle+0x400"
    assert join["receiver_count"] == 4
    assert join["receiver_stride"] == "0x0a80"
    assert join["index_argument"] == "0..3"
    assert join["qword_argument_source"] == "HDVehicle+0x98"

    writes = proof["vehicle_relative_writes"]
    assert writes["index_dword_offsets"] == ["+0x0df8", "+0x1878", "+0x22f8", "+0x2d78"]
    assert writes["qword_offsets"] == ["+0x0e00", "+0x1880", "+0x2300", "+0x2d80"]
    assert writes["per_wheel_offsets"] == ["+0x9f8 dword", "+0xa00 qword"]


def test_frontier_keeps_callee_classified_after_full_p1_2_closure() -> None:
    frontier = _load(FRONTIER)
    classified = frontier["classified_callee_side_effects"]
    assert any(row["callee"] == "0x00752fa0" for row in classified)
    assert "0x00752fa0" not in frontier["representative_unresolved_callees"]
    assert frontier["representative_unresolved_callees"] == []
    assert frontier["callee_mediated_side_effects_complete"] is True
    gate = frontier["gate"]
    assert gate["p1_2b_complete"] is True
    assert gate["fun_00765c40_provider_removal_authorized"] is True
    assert gate["external_provider_count_before_process_2_consumption"] == 7


def test_documentation_keeps_semantics_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "0x00752fa0",
        "0x00765ec1",
        "+0x9f8",
        "+0xa00",
        "HDVehicle+0x98",
        "semantic field name",
        "P1.2b complete: **false**",
        "external-provider count: **7**",
        "NEXT_STEP",
    ):
        assert token in text
