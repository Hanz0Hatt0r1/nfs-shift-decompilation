from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOIN = ROOT / "evidence/fun_00765c40_callee_classification_join.json"
FRONTIER = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
PHASE392 = ROOT / "docs/PHASE392_BODY_IMPULSE_PRIMITIVES.md"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_CALLEE_CLASSIFICATION_JOIN.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authority_and_caller_sites_are_pinned() -> None:
    payload = _load(JOIN)
    assert payload["format"] == "SHIFT.Fun00765c40CalleeClassificationJoin/1"
    assert payload["ready"] is True
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    rows = {row["callee"]: row for row in payload["classified"]}
    assert rows["0x007aefb0"]["caller_sites"] == ["0x00765e0c", "0x007663f6"]
    assert rows["0x007afd20"]["caller_sites"] == ["0x007660be"]
    assert rows["0x007b0430"]["caller_sites"] == ["0x007661e5"]
    assert rows["0x007baa70"]["caller_sites"] == ["0x00766365", "0x007664f2"]


def test_output_helpers_do_not_mutate_receiver() -> None:
    rows = {row["callee"]: row for row in _load(JOIN)["classified"]}
    for callee in ("0x007aefb0", "0x007afd20", "0x007b0430"):
        assert rows[callee]["receiver_mutated"] is False
        assert rows[callee]["output_mutated"] is True


def test_fun_007baa70_joins_existing_body_accumulator_contract() -> None:
    rows = {row["callee"]: row for row in _load(JOIN)["classified"]}
    row = rows["0x007baa70"]
    assert row["receiver_mutated"] is True
    assert row["side_effect_surface_closed"] is True
    assert row["receiver_provenance"] == "edi = [HDVehicle+0x33a0] selected BODY0"
    assert row["accumulator_offsets"] == ["+0x48", "+0x50", "+0x58", "+0x60", "+0x68", "+0x70"]
    assert row["exact_update"] == "linear += v; angular += r x v"
    phase = PHASE392.read_text(encoding="utf-8")
    assert "FUN_007baa70" in phase
    assert "+0x48/+0x50/+0x58" in phase
    assert "+0x60/+0x68/+0x70" in phase
    assert "linear += v" in phase


def test_only_fun_007584f0_remains_unresolved() -> None:
    join = _load(JOIN)
    assert join["adjudication"]["remaining_potentially_mutating_callees"] == ["0x007584f0"]
    assert join["adjudication"]["p1_2b_complete"] is False
    assert join["adjudication"]["fun_00765c40_provider_removal_authorized"] is False
    assert join["adjudication"]["external_provider_count"] == 7

    frontier = _load(FRONTIER)
    assert frontier["representative_unresolved_callees"] == ["0x007584f0"]
    classified = {row["callee"] for row in frontier["classified_callee_side_effects"]}
    assert {"0x00752fa0", "0x007aefb0", "0x007afd20", "0x007b0430", "0x007baa70"} <= classified
    assert frontier["callee_mediated_side_effects_complete"] is False


def test_documentation_is_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "0x007aefb0",
        "0x007afd20",
        "0x007b0430",
        "0x007baa70",
        "0x007584f0",
        "+0x48/+0x50/+0x58",
        "+0x60/+0x68/+0x70",
        "P1.2b complete: **false**",
        "external-provider count: **7**",
        "NEXT_STEP",
    ):
        assert token in text
