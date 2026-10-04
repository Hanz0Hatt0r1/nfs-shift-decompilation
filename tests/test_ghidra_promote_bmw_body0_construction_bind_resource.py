from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "promote_bmw_body0_construction_bind_resource.py"
STATIC = ROOT / "evidence" / "bmw_body0_construction_bind_continuity.json"
RESOURCE = ROOT / "evidence" / "bmw_body0_bind_resource_materialization.json"
POSITIVE = ROOT / "evidence" / "bmw_body0_construction_bind_continuity_resource_join.json"


def _module():
    spec = importlib.util.spec_from_file_location("promote_body0_resource", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_retail_resource_promotes_exact_identity_sdf_bind() -> None:
    m = _module()
    report = m.promote(STATIC, RESOURCE)

    assert report["resource_BODY0"]["pos"] == [0.0, 0.0, 0.0]
    assert report["resource_BODY0"]["ori"] == [0.0, 0.0, 0.0]
    assert report["resource_BODY0"]["basis"] == [
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    ]
    assert report["resource_BODY0"]["body0_local_to_sdf_model_row_matrix"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    handoff = report["handoff"]
    assert handoff["BODY0_resource_pos_ori_values_ready"] is True
    assert handoff["BODY0_local_to_SDF_model_bind_pose_ready"] is True
    assert handoff["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert handoff["BODY0_bind_frame_proof_ready"] is False
    assert handoff["vehicle_world_transform_ready"] is False
    assert [row["id"] for row in report["blockers"]] == [
        "SDF-model-to-VHF-vehicle-root-frame-relation-unproven"
    ]


def test_committed_positive_evidence_matches_promoted_semantics() -> None:
    m = _module()
    promoted = m.promote(STATIC, RESOURCE)
    committed = json.loads(POSITIVE.read_text(encoding="utf-8"))

    assert committed["format"] == m.CONTINUITY_FORMAT
    assert committed["resource_BODY0"] == promoted["resource_BODY0"]
    assert committed["handoff"] == promoted["handoff"]
    assert committed["blockers"] == promoted["blockers"]
    assert committed["scope"]["raw_retail_archive_committed"] is False
    assert committed["scope"]["raw_decoded_sdf_committed"] is False


def test_resource_identity_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(RESOURCE.read_text(encoding="utf-8"))
    value["resource"]["decoded_sha256"] = "0" * 64
    path = tmp_path / "resource.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="SDF identity drift"):
        m.promote(STATIC, path)


def test_zero_orientation_flags_must_match_numeric_values(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(RESOURCE.read_text(encoding="utf-8"))
    value["body0"]["ori"] = [0.0, 0.25, 0.0]
    path = tmp_path / "resource.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="exact-zero orientation flag drift"):
        m.promote(STATIC, path)
