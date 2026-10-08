import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_final_precluster_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_upstream_worklist():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374FinalPreclusterRejections/1"
    assert data["ready"] is True
    assert data["upstream"]["remaining_literal_site_count"] == 5
    assert data["upstream"]["remaining_sites"] == [
        "0x00865013",
        "0x0097da09",
        "0x0097daf8",
        "0x0097dc63",
        "0x0097ed06",
    ]


def test_00865013_exact_receiver_vptr_rejection():
    data = load_evidence()
    row = data["rejections"][0]
    assert row["site"] == "0x00865013"
    assert row["function"] == "FUN_00864c10"
    assert row["function_mnemonic_sha256"] == "ba7464e733ada713d37976823ad8885f95726f652e4bf569f68b46e87b8855bf"
    assert row["exact_receiver_vptr"] == "0x00b1d508"
    assert row["manager_root_vptr"] == "0x00ab9190"
    assert row["participants_subobject_vptr"] == "0x00ab916c"
    assert row["receiver_is_participants_manager"] is False
    assert row["vtable_callsites"] == [
        "0x0085b6f2 call 0x00864c10",
        "0x0085c38f call 0x00864c10",
    ]


def test_0097ed06_is_unconditional_zero_write():
    data = load_evidence()
    row = data["rejections"][1]
    assert row["site"] == "0x0097ed06"
    assert row["zero_source"] == "0x0097ecbe xor ebx,ebx"
    assert row["receiver_identity_required_for_rejection"] is False
    assert row["can_place_hdvehicle_plus_0x4330_into_manager_plus_0x374"] is False


def test_only_fun_0097d8c4_literal_cluster_remains_and_gates_stay_closed():
    data = load_evidence()
    adj = data["adjudication"]
    assert adj["closed_site_count_this_contract"] == 2
    assert adj["remaining_literal_site_count"] == 3
    assert adj["remaining_literal_sites"] == [
        "0x0097da09",
        "0x0097daf8",
        "0x0097dc63",
    ]
    assert adj["remaining_literal_function"] == "FUN_0097d8c4"
    assert adj["literal_manager_374_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
