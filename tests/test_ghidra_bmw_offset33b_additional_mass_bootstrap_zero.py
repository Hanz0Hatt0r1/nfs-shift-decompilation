from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_bmw_offset33b_additional_mass_bootstrap_zero.py"
SPEC = importlib.util.spec_from_file_location("bmw_offset33b_additional_mass_frontier", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _retail_root(tmp_path: Path, *, md5: str | None = None) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps(
            {
                "program_name": MODULE.PROGRAM,
                "executable_md5": MODULE.PE_MD5 if md5 is None else md5,
            }
        ),
        encoding="utf-8",
    )
    return root


def test_retracts_manager_record_zero_claim_and_fails_closed(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(_retail_root(tmp_path))

    assert report["format"] == "SHIFT.BMWOffset33bAdditionalMassActualObjectFrontier/1"
    assert report["ready"] is False
    assert report["status"] == "additional-mass-actual-object-producer-unresolved"

    correction = report["correction"]
    assert correction["retracted_contract"] == "SHIFT.BMWOffset33bAdditionalMassBootstrapZero/1"
    assert correction["manager_record_and_actual_participant_are_distinct_objects"] is True
    assert correction["manager_record_stride"] == 0x1FA0
    assert correction["actual_participant_allocation_size"] == 0x2B90
    assert correction["manager_record_allocator_path"]["actual_object_constructor"] == "FUN_0072ed20"
    assert correction["actual_object_vehicle_construction"]["vehicle_constructor"] == "FUN_0079c1c0"
    assert correction["actual_object_vehicle_construction"]["vehicle_argument"] == "actual_participant + 0x340"
    assert correction["source_backed_consumer"]["actual_participant_storage"] == "actual_participant+0xba0"
    assert correction["source_backed_consumer"]["vehicle_alias_storage"] == "Vehicle+0x860"
    assert correction["manager_record_zero_helper_proves_target_value"] is False
    assert correction["additional_mass_zero_value_proven"] is False

    gates = report["gates"]
    assert gates["offset33b_additional_mass_bootstrap_zero_ready"] is False
    assert gates["offset33b_additional_mass_term_can_be_elided_for_first_bootstrap"] is False
    assert gates["BMW_numeric_offset33b_ready"] is False
    assert gates["BODY0_to_outer_vehicle_root_numeric_matrix_ready"] is False
    assert gates["BODY0_bind_frame_proof_ready"] is False
    assert gates["vehicle_world_transform_ready"] is False


def test_target_alias_arithmetic_is_actual_object_relative(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(_retail_root(tmp_path))
    consumer = report["correction"]["source_backed_consumer"]

    assert MODULE.PARTICIPANT_ADDITIONAL_MASS_OFFSET - MODULE.VEHICLE_EMBEDDED_OFFSET == MODULE.VEHICLE_ADDITIONAL_MASS_OFFSET
    assert consumer["source_expression"] == "*(float *)(*record + 0xba0)"
    assert "record+0xba0" not in consumer["actual_participant_storage"]


def test_next_proof_targets_actual_object_not_manager_record(tmp_path: Path) -> None:
    report = MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(_retail_root(tmp_path))
    next_proof = report["next_proof"]

    assert next_proof["target"] == "actual PhysicsParticipant+0xba0 / embedded Vehicle+0x860 producer"
    assert any("FUN_0072ed20" in item for item in next_proof["constructor_chain"])
    assert any("FUN_0079c1c0" in item for item in next_proof["constructor_chain"])
    assert report["blockers"] == [
        "actual-participant+0xba0 / Vehicle+0x860 producer remains unresolved"
    ]


def test_rejects_wrong_retail_binary(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unexpected retail executable identity"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(
            _retail_root(tmp_path, md5="0" * 32)
        )


def test_rejects_wrong_program_name(tmp_path: Path) -> None:
    root = _retail_root(tmp_path)
    (root / "binary.json").write_text(
        json.dumps({"program_name": "OTHER.exe", "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unexpected retail program name"):
        MODULE.analyze_bmw_offset33b_additional_mass_bootstrap_zero(root)
