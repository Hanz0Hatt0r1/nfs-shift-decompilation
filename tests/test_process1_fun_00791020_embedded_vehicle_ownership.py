from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00791020_embedded_vehicle_ownership.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_EMBEDDED_VEHICLE_OWNERSHIP.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_owner_join_reuses_existing_participant_contract() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.Fun00791020EmbeddedVehicleOwnership/1"
    assert "SHIFT.BMWOffset33bActualAdditionalMassBootstrapZero/1" in payload["upstream_contracts"]
    owner = payload["owner_join"]
    assert owner["manager_record_offset0"] == "actual PhysicsParticipant pointer"
    assert owner["actual_participant_size"] == "0x2b90"
    assert owner["embedded_vehicle_offset"] == "0x340"
    assert owner["fun_00791020_receiver"] == "embedded Vehicle"


def test_writer_is_vehicle_not_hdvehicle() -> None:
    payload = _payload()
    writer = payload["writer_surface"]
    assert writer["machine_write_sites"] == ["0x007910f8", "0x0079113e"]
    assert writer["normalized_storage"] == "embedded Vehicle+0x938"
    assert writer["same_as_hdvehicle_plus_0x938"] is False
    adjudication = payload["adjudication"]
    assert adjudication["fun_00791020_embedded_vehicle_receiver_proven"] is True
    assert adjudication["fun_00791020_vehicle_plus_0x938_writer_proven"] is True
    assert adjudication["fun_00791020_hdvehicle_plus_0x938_writer_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_doc_keeps_control_semantics_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "actual PhysicsParticipant",
        "embedded Vehicle",
        "Vehicle+0x938",
        "not writes to `HDVehicle+0x938`",
        "No new semantic meaning",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
