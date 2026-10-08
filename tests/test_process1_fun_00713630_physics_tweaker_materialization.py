import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00713630_physics_tweaker_materialization.json"
UPSTREAM = ROOT / "evidence/fun_00713630_upstream_direct_surface.json"
CADENCE = ROOT / "evidence/s5_retail_outer_update_cadence_completion.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00713630_PHYSICS_TWEAKER_MATERIALIZATION.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_and_fail_closed_gate():
    p = _load(EVIDENCE)
    assert p["format"] == "SHIFT.Fun00713630PhysicsTweakerMaterialization/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    a = p["adjudication"]
    assert a["seven_config_field_owner_closed"] is True
    assert a["actual_selected_participant_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_seven_inputs_are_exact_physics_tweaker_offsets():
    p = _load(EVIDENCE)
    assert p["object_root"]["base_address"] == "0x00c12c40"
    assert p["object_root"]["constructor"] == "FUN_00748280"
    rows = p["fun_00713630_config_fields"]
    assert [r["offset"] for r in rows] == ["0x2a0", "0x2a4", "0x2a8", "0x2ac", "0x2b0", "0x2b4", "0x2c4"]
    assert [r["absolute"] for r in rows] == ["0x00c12ee0", "0x00c12ee4", "0x00c12ee8", "0x00c12eec", "0x00c12ef0", "0x00c12ef4", "0x00c12f04"]
    assert p["default_materialization"]["all_seven_written_by_fun_00748280_on_fixed_physics_tweaker_receiver"] is True


def test_runtime_registration_matches_all_seven_offsets():
    r = _load(EVIDENCE)["runtime_registration"]
    assert r["function"] == "FUN_00749a60"
    assert r["registration_helper"] == "FUN_0063a280"
    assert r["field_offsets"] == ["0x2a0", "0x2a4", "0x2a8", "0x2ac", "0x2b0", "0x2b4", "0x2c4"]
    assert len(r["helper_callsites"]) == 7
    cadence = _load(CADENCE)
    source = cadence["physics_rate_source"]
    assert source["tweaker"] == "Physics Tweaker"
    assert source["xml"] == "PhysicsTweaker.xml"
    assert source["tweaker_base"] == "DAT_00c12c40"
    assert source["verified"] is True


def test_old_plus_4b0_candidate_is_rejected_by_receiver_identity():
    p = _load(EVIDENCE)
    r = p["plus_0x4b0_candidate_rejection"]
    assert r["candidate_store"] == "0x00748956 fstp dword [esi+0x4b0]"
    assert r["receiver_at_function_entry"] == "fixed PhysicsTweaker object DAT_00c12c40"
    assert r["direct_selected_participant_writer"] is False
    assert r["numeric_offset_equality_used_as_identity"] is False
    upstream = _load(UPSTREAM)
    assert upstream["participant_scalar_candidate"]["candidate_function"] == "FUN_00748280"
    assert upstream["participant_scalar_candidate"]["same_object_identity_as_FUN_00713630_participant_proven"] is False
    assert "actual selected-participant `+0x4b0` writer: **open**" in DOC.read_text(encoding="utf-8")


def test_pinned_machine_spans():
    p = _load(EVIDENCE)
    assert p["object_root"]["machine_span"]["sha256"] == "9be7c4863f3e1a8980e5d29121dacdebc88a2f1466eb1452b3ff048732a7bf4e"
    assert p["default_materialization"]["machine_span"]["sha256"] == "2b8fac1e576ca6f2c2ecfb17d89dd104f41e4d6c2ab2768115a5a953d48096e7"
    assert p["runtime_registration"]["machine_span"]["sha256"] == "4f0c42d6c002dc61c07a9ffe85844abe79e7bd0c200eceeffdd852ff17dd6e45"
    assert p["plus_0x4b0_candidate_rejection"]["machine_span"]["sha256"] == "b3c0a85cc2ae736aec9696cb6c7d64deba0445f1682379b65dfd8ca359fe7719"
