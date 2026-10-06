from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _analyzer():
    return _load(
        ROOT
        / "tools"
        / "ghidra"
        / "analyze_fun_007682c0_owner_field_base_provenance.py",
        "analyze_fun_007682c0_owner_field_base_provenance_tested",
    )


def _fixtures():
    return _load(
        ROOT
        / "tests"
        / "test_ghidra_fun_007682c0_destination_receiver_provenance.py",
        "fun_007682c0_destination_receiver_fixture_helpers",
    )


def test_owner_field_base_is_joined_to_outer_entry_without_promoting_body0(tmp_path):
    analyzer = _analyzer()
    fixtures = _fixtures()
    upstream = fixtures._module()
    root = fixtures._retail_export(tmp_path, upstream)
    identity = fixtures._global_identity(tmp_path, upstream)
    instructions = fixtures._instruction_export(
        tmp_path,
        upstream,
        outer=fixtures._outer_owner_field(upstream),
    )

    report = analyzer.analyze_fun_007682c0_owner_field_base_provenance(
        root,
        instructions,
        identity,
    )

    assert report["format"] == analyzer.FORMAT
    assert report["ready"] is True
    assert report["status"] == "owner-field-pointer-proven-record-join-blocked"
    assert report["owner_field_offset"] == "0x339c"
    assert len(report["pass_owner_field_base_provenance"]) == 2
    for row in report["pass_owner_field_base_provenance"]:
        assert row["owner_field_origin_observed"] is True
        assert row["candidate_count"] >= 1
        assert row["all_candidate_load_bases_are_outer_entry_ECX"] is True
        assert row["owner_field_base_to_outer_entry_ECX_proven"] is True
        assert all(
            candidate["base_origins_before_load"] == ["entry:ECX"]
            for candidate in row["owner_field_load_candidates_on_paths_to_call"]
        )

    analysis = report["analysis"]
    assert analysis["both_outer_pass_owner_field_bases_are_entry_ECX"] is True
    assert analysis["outer_entry_is_proven_global_vehicle_base"] is True
    assert analysis["downstream_entry_ECX_continuity_proven"] is True
    assert analysis[
        "FUN_007682c0_receiver_is_global_vehicle_plus_0x339c_pointer"
    ] is True
    assert analysis["FUN_007682c0_receiver_is_retail_BMW_BODY0"] is False
    assert analysis[
        "owner_pointer_to_exact_delta_destination_record_join_proven"
    ] is False

    assert report["handoff"]["FUN_007682c0_owner_pointer_receiver_ready"] is True
    assert report["handoff"]["FUN_007682c0_delta_consumer_internalization_ready"] is False
    assert report["handoff"]["phase696_typed_delta_consumer_must_remain_external"] is True
    assert report["blocking_reasons"] == [
        {
            "id": "owner-pointer-to-exact-delta-destination-record-unproven",
            "evidence_state": "unknown",
            "required_evidence": (
                "join the proven global vehicle +0x339c BODY-array owner pointer "
                "to the exact record receiving FUN_007682c0 +0x50; do not equate "
                "the owner pointer with BMW BODY0 solely because BODY index 0 is selected"
            ),
        }
    ]
    assert report["scope"]["memory_displacement_alone_used_as_identity"] is False
    assert report["scope"]["BODY_owner_pointer_relabelled_as_BODY0"] is False
    assert report["scope"]["provider_semantics_promoted"] is False


def test_owner_field_offset_match_is_rejected_when_base_origin_drifts(tmp_path):
    analyzer = _analyzer()
    fixtures = _fixtures()
    upstream = fixtures._module()
    root = fixtures._retail_export(tmp_path, upstream)
    identity = fixtures._global_identity(tmp_path, upstream)
    outer = fixtures._outer_owner_field(upstream)
    outer[0] = fixtures._ins(
        "0x00770e80",
        "MOV",
        ["ESI", "EAX"],
        fallthrough="0x00770e82",
        outputs=("ESI",),
    )
    instructions = fixtures._instruction_export(
        tmp_path,
        upstream,
        outer=outer,
    )

    report = analyzer.analyze_fun_007682c0_owner_field_base_provenance(
        root,
        instructions,
        identity,
    )

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert report["analysis"]["both_outer_pass_owner_field_bases_are_entry_ECX"] is False
    assert report["analysis"][
        "FUN_007682c0_receiver_is_global_vehicle_plus_0x339c_pointer"
    ] is False
    assert report["handoff"]["FUN_007682c0_owner_pointer_receiver_ready"] is False
    assert report["blocking_reasons"][0]["id"] == (
        "owner-field-base-to-outer-entry-unproven"
    )
    candidates = [
        candidate
        for row in report["pass_owner_field_base_provenance"]
        for candidate in row["owner_field_load_candidates_on_paths_to_call"]
    ]
    assert candidates
    assert any(
        candidate["base_origins_before_load"] == ["entry:EAX"]
        for candidate in candidates
    )
    assert report["scope"]["base_register_origin_proven_on_all_candidate_loads"] is False


def test_direct_outer_receiver_does_not_masquerade_as_owner_field_pointer(tmp_path):
    analyzer = _analyzer()
    fixtures = _fixtures()
    upstream = fixtures._module()
    root = fixtures._retail_export(tmp_path, upstream)
    identity = fixtures._global_identity(tmp_path, upstream)
    instructions = fixtures._instruction_export(tmp_path, upstream)

    report = analyzer.analyze_fun_007682c0_owner_field_base_provenance(
        root,
        instructions,
        identity,
    )

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert all(
        row["owner_field_origin_observed"] is False
        for row in report["pass_owner_field_base_provenance"]
    )
    assert all(
        row["candidate_count"] == 0
        for row in report["pass_owner_field_base_provenance"]
    )
    assert report["analysis"][
        "FUN_007682c0_receiver_is_global_vehicle_plus_0x339c_pointer"
    ] is False
    assert report["blocking_reasons"][0]["id"] == (
        "owner-field-base-to-outer-entry-unproven"
    )


def test_owner_field_parser_accepts_only_simple_exact_339c_memory_operands():
    analyzer = _analyzer()

    assert analyzer._owner_field_base_register("dword ptr [ESI + 0x339c]") == "ESI"
    assert analyzer._owner_field_base_register("[ecx+0x339c]") == "ECX"
    assert analyzer._owner_field_base_register("[ESI+0x339d]") is None
    assert analyzer._owner_field_base_register("[ESI+EAX+0x339c]") is None
    assert analyzer._owner_field_base_register("[0x339c]") is None
