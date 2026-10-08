from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_DIRECT_MACHINE_WRITE_SURFACE.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_function_range_are_pinned() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Fun00765c40DirectMachineWriteSurface/1"
    assert payload["ready"] is True
    authority = payload["authority"]
    assert authority["platform"] == "PC retail 1.02"
    assert authority["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert authority["entry"] == "0x00765c40"
    assert authority["end_exclusive"] == "0x00766510"


def test_direct_write_groups_cover_machine_backed_offsets() -> None:
    payload = _load()
    groups = payload["direct_write_groups"]
    by_kind = {}
    for row in groups:
        by_kind.setdefault(row["kind"], []).append(row)

    assert by_kind["wheel_qword_loop_a"][0]["offsets"] == [
        "+0x0a70", "+0x14f0", "+0x1f70", "+0x29f0"
    ]
    assert by_kind["wheel_qword_pair_loop_b"][0]["offsets"] == [
        "+0x0ba0", "+0x0ba8", "+0x1620", "+0x1628",
        "+0x20a0", "+0x20a8", "+0x2b20", "+0x2b28",
    ]
    assert by_kind["contact_record_pointer_array"][0]["base_offset"] == "+0x35c8"
    assert by_kind["contact_record_pointer_array"][0]["count"] == 12
    assert by_kind["contact_record_pointer_array"][0]["last_offset"] == "+0x35f4"
    assert by_kind["contact_scalar_qword_array"][0]["base_offset"] == "+0x35f8"
    assert by_kind["contact_scalar_qword_array"][0]["count"] == 12
    assert by_kind["contact_scalar_qword_array"][0]["last_offset"] == "+0x3650"

    scalar_offsets = {row.get("offset") for row in groups}
    assert {"+0x3660", "+0x3668", "+0x3670", "+0x3678", "+0x407c"} <= scalar_offsets


def test_load_positive_count_joins_closed_load_terms() -> None:
    payload = _load()
    row = next(r for r in payload["direct_write_groups"] if r["kind"] == "load_term_positive_count")
    assert row["offset"] == "+0x407c"
    assert row["inputs"] == ["+0x0b38", "+0x15b8", "+0x2038", "+0x2ab8"]
    assert "counts how many" in row["semantics"]


def test_gate_remains_fail_closed_for_callee_side_effects() -> None:
    payload = _load()
    assert payload["direct_write_surface_complete_for_machine_body"] is True
    assert payload["callee_mediated_side_effects_complete"] is False
    classified = {row["callee"] for row in payload["classified_callee_side_effects"]}
    assert {"0x00752fa0", "0x007aefb0", "0x007afd20", "0x007b0430", "0x007baa70"} <= classified
    assert payload["representative_unresolved_callees"] == ["0x007584f0"]
    gate = payload["gate"]
    assert gate["p1_2b_direct_write_inventory_closed"] is True
    assert gate["p1_2b_complete"] is False
    assert gate["fun_00765c40_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7


def test_documentation_preserves_direct_vs_callee_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.2b",
        "+0x35c8",
        "+0x35f8",
        "+0x3660",
        "+0x3668",
        "+0x3670",
        "+0x3678",
        "+0x407c",
        "callee-mediated side effects",
        "external-provider count: **7**",
        "NEXT_STEP",
    ):
        assert token in text
