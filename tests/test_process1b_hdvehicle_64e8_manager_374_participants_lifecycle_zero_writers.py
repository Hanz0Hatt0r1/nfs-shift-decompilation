import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_participants_lifecycle_zero_writers.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_participants_manager_vptr_is_pinned():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374ParticipantsLifecycleZeroWriters/1"
    assert p["ready"] is True
    assert p["constructor_vptr"]["participants_vptr_store"] == "0x00488dfb mov [manager+0x20],0x00ab916c"
    assert p["constructor_vptr"]["vptr"] == "0x00ab916c"


def test_lifecycle_slots_resolve_to_exact_callbacks():
    slots = _payload()["participants_vtable"]["slots"]
    assert slots["+0x08"] == "FUN_004871f0"
    assert slots["+0x0c"] == "FUN_0048a7f0"
    assert slots["+0x10"] == "FUN_00488a10"
    assert slots["+0x14"] == "FUN_00488970"
    assert slots["+0x18"] == "FUN_0048ade0"
    assert slots["+0x1c"] == "FUN_0048aee0"
    assert slots["+0x20"] == "0x0048b9a0"


def test_only_exact_literal_target_writers_clear_manager_374():
    rows = _payload()["exact_target_writers"]
    assert [row["function"] for row in rows] == ["FUN_004871f0", "FUN_00488970"]
    assert all(row["written_value"] == 0 for row in rows)
    assert "0x00487203 xor eax,eax" in rows[0]["instructions"]
    assert "0x0048720b mov [esi+0x354],eax" in rows[0]["instructions"]
    assert "0x004889ac xor ebx,ebx" in rows[1]["instructions"]
    assert "0x004889b4 mov [esi+0x354],ebx" in rows[1]["instructions"]


def test_other_direct_callbacks_do_not_have_literal_target_store():
    scan = _payload()["other_direct_callback_scan"]
    assert scan["direct_literal_target_surface_nonzero_writer_found"] is False
    assert len(scan["callbacks_without_literal_plus_0x354_store"]) == 5


def test_adjudication_stays_fail_closed_for_other_writer_surfaces():
    a = _payload()["adjudication"]
    assert a["participants_lifecycle_reaches_manager_374"] is True
    assert a["participants_lifecycle_direct_target_writers_are_zero_only"] is True
    assert a["participants_lifecycle_nonzero_manager_374_writer_proven"] is False
    assert a["participants_lifecycle_establishes_hdvehicle_4330_identity"] is False
    assert a["unrelated_computed_or_non_vtable_writer_surface_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["external_provider_count"] == 7


def test_coordination_advances_participants_surface_to_zero_only():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    assert node["status"] == "participants-lifecycle-zero-writers-proven-other-indirect-open"
    assert node["manager_plus_0x20_lifecycle_target_reaches_0x374"] is True
    assert node["manager_plus_0x20_lifecycle_target_writes_zero_only"] is True
    assert any(item.startswith("FUN_004871f0 ") for item in node["participants_lifecycle_zero_writers"])
    assert any(item.startswith("FUN_00488970 ") for item in node["participants_lifecycle_zero_writers"])
    assert "computed" in node["next"].lower()
