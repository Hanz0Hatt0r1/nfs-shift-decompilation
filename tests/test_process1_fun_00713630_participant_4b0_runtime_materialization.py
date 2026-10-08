import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_runtime_materialization.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_storage_and_materializer_are_joined():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0RuntimeMaterialization/1"
    s = p["exact_storage"]
    assert s["identity"] == "participant+0x4b0 == (participant+0x340)+0x170"
    assert s["type"] == "f32"
    m = p["canonical_materializer"]
    assert m["function"] == "FUN_007927c0"
    assert m["target_machine_store"] == "0x007927ee fstp dword [eax+4]"
    assert m["machine_span"]["sha256"] == "814751910e5b5db792c6b57e0689d5e95e02297514b9c52d84b96527403e3f88"
    assert m["source_sha256"] == "f75b15c2a0eb0496dcdf54c0af522d02704bb7d1a6efa784c8bd374cb2e4a8d8"


def test_selected_runtime_manager_path_materializes_before_consumer():
    p = _payload()
    r = p["selected_runtime_manager_materialization"]
    assert r["function"] == "FUN_00713340"
    assert r["actual_participant_pointer"] == "record[0]"
    assert r["materializer_receiver"] == "actual_participant+0x340"
    assert r["second_float3_input"] == [0.0, 0.0, 0.0]
    assert r["materialized_target_on_this_path"] == "actual_participant+0x4b0 = +0.0f"
    assert r["machine_callsite"] == "0x007133db call FUN_007927c0"
    assert r["machine_span"]["sha256"] == "593dace066f40faef0049c1216d043f8f85be3717ed427674ab82eedf1a71809"
    order = p["pre_consumer_order"]
    assert order["ordered_calls"] == [
        "0x0071556f call FUN_00713340",
        "0x00715576 call FUN_007135b0",
        "0x0071557d call FUN_007144a0",
    ]
    assert order["materializer_runs_before_cadence_consumer"] is True
    assert order["machine_span"]["sha256"] == "b95729403b1504e6dfd1386765cfda3e1df644dc57224ffb1d533e1921129422"


def test_field_is_dynamic_and_zero_path_is_not_promoted_to_constant():
    p = _payload()
    d = p["dynamic_nonconstant_proof"]
    assert d["function"] == "FUN_0074ddc3"
    assert d["case4_receiver"] == "actual_participant+0x340"
    assert d["participant_plus_0x4b0_source_on_case4"] == "restart input +0x38"
    assert d["case4_machine_span"]["sha256"] == "60ab47c8a60f9d0c389c919180175fc4be77ae1892360640b422f9b1674cd730"
    assert p["adjudication"]["participant_plus_0x4b0_is_dynamic_not_setup_constant"] is True
    assert "must not be frozen" in p["handoff"]["instruction"]


def test_p11_closes_without_process1_reducing_provider_count():
    p = _payload()
    assert p["closed_prior_inputs"]["seven_config_runtime_owners_materialized"] is True
    assert p["closed_prior_inputs"]["sample_history_writer_selected_participant_scheduling_closed"] is True
    a = p["adjudication"]
    assert a["participant_plus_0x4b0_storage_identity_closed"] is True
    assert a["participant_plus_0x4b0_materializer_closed"] is True
    assert a["participant_plus_0x4b0_selected_runtime_path_closed"] is True
    assert a["participant_plus_0x4b0_preconsumer_order_closed"] is True
    assert a["p1_1a_complete"] is True
    assert a["p1_1c_complete"] is True
    assert a["p1_1_complete"] is True
    assert a["contact_response_provider_removal_authorized"] is True
    assert a["external_provider_count"] == 7
    assert a["target_external_provider_count_after_process_2_consumption"] == 6
    assert p["handoff"]["provider_removal_owner"] == "Process 2"
    assert p["handoff"]["process_1_must_not_reduce_provider_count"] is True
