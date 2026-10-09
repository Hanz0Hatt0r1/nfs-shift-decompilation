import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_p13b_0070f62d_vptr_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_is_owned_by_p13b_and_pins_exact_site():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374P13B0070f62dVptrRejection/1"
    assert data["owner_shard"] == "P1.3B"
    assert data["site"]["address"] == "0x0070f62d"
    assert data["site"]["materializer"] == "lea ecx,[esi+0x374]"
    assert data["site"]["callee"] == "FUN_006310c0"


def test_exact_receiver_vptr_rejects_participants_manager_identity():
    data = load_evidence()
    assert data["receiver_class"]["vptr"] == "0x00b04524"
    assert data["receiver_class"]["vptr_store"] == "0x0070f5a0 mov [esi],0x00b04524"
    assert data["participants_manager_identity"]["root_vptr"] == "0x00ab9190"
    assert data["participants_manager_identity"]["subobject_vptr"] == "0x00ab916c"
    assert data["site"]["can_target_participants_manager_plus_0x374"] is False


def test_only_one_p13b_computed_path_is_closed_and_gates_stay_fail_closed():
    data = load_evidence()
    a = data["adjudication"]
    assert a["p13b_site_0x0070f62d_complete"] is True
    assert a["p13b_site_0x005f6eda_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
    assert any("P1.3D" in limit for limit in data["limits"])
