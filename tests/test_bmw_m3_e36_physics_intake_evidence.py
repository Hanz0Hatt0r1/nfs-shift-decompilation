import json
from pathlib import Path


EVIDENCE = Path(__file__).parents[1] / "evidence" / "bmw_m3_e36_physics_intake_phase404.json"


def test_bmw_m3_physics_intake_evidence_is_self_consistent():
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["archive"]["filename"] == "BMW_M3_E36.bff"
    assert report["archive"]["size_bytes"] == 18934688
    assert len(report["archive"]["sha256"]) == 64
    assert report["sdf_entry"]["index"] == 1091
    assert report["sdf_entry"]["path"] == (
        "vehicles/physics/suspension/aarm_multilink.sdf"
    )
    assert report["sdf_entry"]["compression_type"] == 2
    assert report["sdf_entry"]["compressed_size"] == 1110
    assert report["sdf_entry"]["uncompressed_size"] == 5056
    assert len(report["sdf_entry"]["decoded_sha256"]) == 64


def test_bmw_m3_physics_scalar_domain_is_40():
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    structure = report["structure"]
    assert structure["body_count"] == 11
    assert structure["joint_hinge_count"] == 4
    assert structure["bar_count"] == 20
    assert structure["solver_scalar_count"] == (
        4 * structure["joint_scalar_width"]
        + 4 * structure["hinge_scalar_width"]
        + 20 * structure["bar_scalar_width"]
    )
    assert structure["solver_scalar_count"] == 40


def test_bmw_m3_joint_axis_evidence_matches_four_wheel_connections():
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["joint_axes"] == [
        [-1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [-1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]


def test_bmw_m3_physics_evidence_is_explicitly_archive_derived():
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert report["status"] == "decoded-from-user-supplied-bff"


def test_bmw_m3_real_solver_domain_materializes_to_retail_storage_shape():
    from sdf_constraint_matrix_assembly_runtime import (
        build_retail_matrix_storage,
        validate_retail_matrix_storage,
    )

    layout = build_retail_matrix_storage(40, matrix_base_address=0x5000)
    assert layout["matrix_double_count"] == 1600
    assert layout["matrix_bytes"] == 12800
    assert layout["row_pointer_bytes"] == 160
    assert layout["row_indices"][39] == 1560
    assert layout["row_pointers"][39] == 0x80C0

    matrix = [[0.0 for _ in range(40)] for _ in range(40)]
    validation = validate_retail_matrix_storage(matrix, layout)
    assert validation["ready"] is True
    assert validation["errors"] == []
