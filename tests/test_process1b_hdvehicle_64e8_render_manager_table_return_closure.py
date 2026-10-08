import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_table_return_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_table_identity_and_callbacks_are_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerTableReturnedRootClosure/1"
    table = data["table_identity"]
    assert table["table_base"] == "0x00abec20"
    assert table["constructor"]["function"] == "FUN_004b7250"
    assert table["constructor"]["mnemonic_sha256"] == "ac4ff277d6e87ceee2f677e45fe5c0173bc3c3109202caf50af5cbd25f553ce2"
    assert [(c["slot_offset"], c["target"]) for c in table["callbacks"]] == [
        ("+0xe0", "FUN_004b7350"),
        ("+0xe4", "FUN_004b73c0"),
    ]


def test_owner_registration_chain_is_pinned():
    reg = load_evidence()["ownership_and_registration"]
    assert reg["allocation_owner"]["owner_store"] == "0x004c2ecf [owner+0x118]=constructed table object"
    assert reg["registration_path"]["load"] == "0x004c65fb eax=[owner+0x118]"
    assert reg["service_registration"]["service_store"] == "0x006e8c87 [service+0x424]=table object"
    assert reg["service_registration"]["global_stores"] == [
        "0x006e8c99 [0x00c0f808]=table object",
        "0x006e8c9f [0x00c0f7f4]=table object",
    ]


def test_exact_four_dispatches_ignore_conditional_eax_residue():
    surface = load_evidence()["dispatch_surface"]
    assert surface["function"] == "FUN_006f28c0"
    assert surface["mnemonic_sha256"] == "0dd380adcd034da39100d2bc4206b80b986d7c4e4003f81cd7a4857627b7357f"
    calls = surface["calls"]
    assert [(c["callsite"].split()[0], c["slot_offset"], c["target"]) for c in calls] == [
        ("0x006f2933", "+0xe4", "FUN_004b73c0"),
        ("0x006f29aa", "+0xe4", "FUN_004b73c0"),
        ("0x006f2a35", "+0xe0", "FUN_004b7350"),
        ("0x006f2a7c", "+0xe0", "FUN_004b7350"),
    ]
    assert all(c["exact_eax_residue_consumed"] is False for c in calls)
    assert all(c["exact_eax_residue_persisted"] is False for c in calls)


def test_returned_root_surface_closes_but_p13_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["table_object_identity_closed"] is True
    assert adj["registration_to_0x00c0f808_closed"] is True
    assert adj["slot_e0_dispatch_surface_complete"] is True
    assert adj["slot_e4_dispatch_surface_complete"] is True
    assert adj["table_only_returned_root_consumer_surface_complete"] is True
    assert adj["table_only_returned_root_can_persist_or_dispatch_exact_root"] is False
    assert adj["returned_root_consumer_surface_complete"] is True
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
