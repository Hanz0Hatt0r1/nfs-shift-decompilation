from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "materialize_bmw_body0_bind_resource.py"
SPEC = importlib.util.spec_from_file_location("bmw_body0_resource_materializer", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _sdf_bytes(*, pos=(1.25, -2.5, 3.75), ori=(0.0, 0.0, 0.0), swap=False) -> bytes:
    names = list(MODULE.EXPECTED_BODIES)
    if swap:
        names[0], names[1] = names[1], names[0]
    lines: list[str] = []
    for index, name in enumerate(names):
        body_pos = pos if index == 0 else (0.0, 0.0, 0.0)
        body_ori = ori if index == 0 else (0.0, 0.0, 0.0)
        lines.extend(
            [
                "[BODY]",
                (
                    f"name={name} "
                    f"pos=({body_pos[0]},{body_pos[1]},{body_pos[2]}) "
                    f"ori=({body_ori[0]},{body_ori[1]},{body_ori[2]})"
                ),
            ]
        )
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    padding = 5056 - len(raw)
    assert padding >= 3
    return raw + ("//" + "x" * (padding - 3) + "\n").encode("ascii")


def _provenance() -> dict:
    return {
        "archive": "BMW_M3_E36.bff",
        "archive_sha256": MODULE.TARGET_ARCHIVE_SHA256,
        "entry_index": 1091,
        "path": MODULE.TARGET_RESOURCE,
        "compression_type": 2,
        "compressed_size": 1110,
        "uncompressed_size": 5056,
        "decoded_sha256": MODULE.TARGET_RESOURCE_SHA256,
    }


def test_materializer_reports_body0_values_and_writes_exact_sdf(tmp_path, monkeypatch):
    data = _sdf_bytes()
    monkeypatch.setattr(MODULE, "extract_target_sdf", lambda path: (data, _provenance()))
    output = tmp_path / "vehicles" / "physics" / "suspension" / "aarm_multilink.sdf"

    report = MODULE.materialize_bmw_body0_bind_resource(
        tmp_path / "BMW_M3_E36.bff",
        sdf_out=output,
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert output.read_bytes() == data
    assert report["resource"]["entry_index"] == 1091
    assert report["resource"]["materialized_path"] == str(output)
    assert report["body0"]["body_index"] == 0
    assert report["body0"]["body_name"] == "body"
    assert report["body0"]["pos"] == [1.25, -2.5, 3.75]
    assert report["body0"]["ori"] == [0.0, 0.0, 0.0]
    assert report["body0"]["ori_is_exact_zero"] is True
    assert report["body0"]["zero_orientation_identity_shortcut_eligible"] is True
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["handoff"]["construction_bind_continuity_input_ready"] is True
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is False
    assert report["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["SDF_model_frame_assumed_equal_VHF_vehicle_root"] is False


def test_nonzero_ori_is_reported_without_inventing_basis(monkeypatch, tmp_path):
    data = _sdf_bytes(ori=(0.1, 0.2, 0.3))
    monkeypatch.setattr(MODULE, "extract_target_sdf", lambda path: (data, _provenance()))

    report = MODULE.materialize_bmw_body0_bind_resource(tmp_path / "BMW_M3_E36.bff")

    assert report["body0"]["ori"] == [0.1, 0.2, 0.3]
    assert report["body0"]["ori_is_exact_zero"] is False
    assert report["body0"]["zero_orientation_identity_shortcut_eligible"] is False
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is False


def test_provenance_entry_index_drift_fails_closed(monkeypatch, tmp_path):
    data = _sdf_bytes()
    provenance = _provenance()
    provenance["entry_index"] = 1090
    monkeypatch.setattr(MODULE, "extract_target_sdf", lambda path: (data, provenance))

    with pytest.raises(ValueError, match="entry_index"):
        MODULE.materialize_bmw_body0_bind_resource(tmp_path / "BMW_M3_E36.bff")


def test_body_order_drift_fails_closed(monkeypatch, tmp_path):
    data = _sdf_bytes(swap=True)
    monkeypatch.setattr(MODULE, "extract_target_sdf", lambda path: (data, _provenance()))

    with pytest.raises(ValueError, match="BODY order/name drift"):
        MODULE.materialize_bmw_body0_bind_resource(tmp_path / "BMW_M3_E36.bff")


def test_phase404_identity_drift_fails_closed(tmp_path):
    intake = MODULE._load_intake(MODULE.DEFAULT_INTAKE)
    intake["sdf_entry"]["index"] = 1
    path = tmp_path / "intake.json"
    import json

    path.write_text(json.dumps(intake), encoding="utf-8")
    with pytest.raises(ValueError, match="entry index drift"):
        MODULE._load_intake(path)
