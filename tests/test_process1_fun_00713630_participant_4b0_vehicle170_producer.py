import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_vehicle170_producer.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_stale_alias_false_negative_is_corrected():
    p = _payload()
    c = p["stale_alias_frontier_correction"]
    assert c["contract"] == "SHIFT.Fun00713630Participant4b0SubobjectAliasFrontier/1"
    assert c["old_value"] is False
    assert c["correct_value"] is True
    assert p["producer"]["function"] == "FUN_007927c0"
    assert p["producer"]["effective_destination"] == "receiver+0x170"


def test_selected_participant_vehicle_alias_hits_plus_0x4b0_exactly():
    p = _payload()
    i = p["selected_participant_identity"]
    assert i["embedded_vehicle_offset"] == "0x340"
    assert i["identity_equation"] == "selected_participant+0x4b0 == embedded_vehicle+0x170"
    assert p["producer"]["participant_effective_destination"] == "selected_participant+0x4b0"


def test_runtime_manager_call_joins_record_zero_to_vehicle_subobject():
    p = _payload()
    j = p["same_manager_selected_receiver_join"]
    assert j["function"] == "FUN_00713340"
    assert "record[0] actual participant" in j["machine_join"][2]
    assert "ECX += 0x340" in j["machine_join"][3]
    assert j["machine_join"][4] == "0x007133db call FUN_007927c0"
    assert j["machine_span"]["sha256"] == "c152c879f5e44deaca237cb9379a01a3fd8eac0d5ecc1cc5e7b807293a4c97c7"


def test_runtime_message_path_keeps_lane_dynamic():
    p = _payload()
    d = p["dynamic_runtime_materialization"]
    assert d["callsite"] == "0x00710563"
    assert d["proves_not_setup_constant"] is True
    assert "runtime message payload" in d["value_path"]
    assert d["machine_span"]["sha256"] == "0c203f8e0bec8b28a61c8e664f4a4a63acbb495797cd4056ff314ea358e696d7"


def test_producer_source_and_machine_are_frozen():
    p = _payload()
    producer = p["producer"]
    assert producer["source_sha256"] == "2312ca71cc46091c33bc05b53f07642e514b1b7688ca7801cca67ff6b4c410ef"
    assert producer["machine_span"]["sha256"] == "a59b1d9832ca88d61521d66eebad9ce64f1dda0361c0e359bea86cd7961d6469"
    assert p["same_manager_selected_receiver_join"]["source_sha256"] == "b9ab67375c69afef403cc68bf07de7775a47cda737b6bc016a0e056d1cf3e835"


def test_p11a_closes_but_provider_removal_waits_for_explicit_handoff():
    p = _payload()
    join = p["p1_1a_join"]
    assert join["config_global_owner_or_alias_writer_closed"] is True
    assert join["sample_writer_selected_participant_scheduling_closed"] is True
    assert join["participant_plus_0x4b0_owner_closed"] is True
    assert join["dynamic_lane_preserved"] is True
    a = p["adjudication"]
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is True
    assert a["p1_1a_complete"] is True
    assert a["p1_1c_complete"] is True
    assert a["p1_1_complete"] is False
    assert a["explicit_process1_handoff_still_required"] is True
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
