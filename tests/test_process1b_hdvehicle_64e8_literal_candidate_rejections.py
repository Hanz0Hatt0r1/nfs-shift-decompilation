import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_literal_candidate_rejections.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_candidate_counts():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8LiteralCandidateRejections/1"
    assert p["ready"] is True
    a = p["adjudication"]
    assert a["original_literal_candidate_count"] == 4
    assert a["manager2a0_candidates_rejected"] == 3
    assert a["remaining_literal_candidate_count"] == 1


def test_three_rejected_writers_resolve_receiver_through_manager2a0():
    rows = _payload()["rejections"]
    assert [row["instruction"] for row in rows] == ["0x004bb205", "0x004bca6b", "0x00d775ee"]
    assert all(row["receiver_domain"] == "manager+0x2a0 allocator-owned entry" for row in rows)
    assert all(row["receiver_equals_hdvehicle_4330"] is False for row in rows)
    assert all(any("FUN_0054ed00" in step for step in row["machine_chain"]) for row in rows)


def test_only_remaining_literal_candidate_reads_manager374():
    row = _payload()["remaining_candidate"]
    assert row["instruction"] == "0x004b86cf"
    assert row["function"] == "FUN_004b8660"
    assert "0x004b8669 mov esi,[manager+0x374]" in row["machine_chain"]
    assert row["receiver_equals_hdvehicle_4330"] == "unresolved"


def test_frontier_remains_fail_closed():
    a = _payload()["adjudication"]
    assert a["remaining_candidate_depends_on_manager_374_identity"] is True
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["alias_or_callee_writer_exhausted"] is False
    assert a["external_provider_count"] == 7


def test_coordination_pins_reduced_literal_frontier():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    slot2 = next(row for row in p13["children"] if row["id"] == "P1.3.slot2")
    assert slot2["hdvehicle_64e8_literal_candidate_count"] == 1
    assert slot2["hdvehicle_64e8_remaining_literal_candidate"] == "0x004b86cf via manager+0x374"
    assert slot2["hdvehicle_64e8_rejected_literal_candidates"] == ["0x004bb205", "0x004bca6b", "0x00d775ee"]
    assert "manager+0x374" in slot2["next"]
