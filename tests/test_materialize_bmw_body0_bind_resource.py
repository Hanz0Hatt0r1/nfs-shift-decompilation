from __future__ import annotations

import importlib.util
import json
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


def _runtime_bootstrap_fixture(
    tmp_path: Path,
    data: bytes,
    *,
    retail_ready: bool = True,
    materialized_ready: bool = True,
    manifest_source: str | None = None,
    bootstrap_sdf: Path | None = None,
) -> tuple[Path, Path, Path]:
    sdf = tmp_path / "resources" / "decoded" / "aarm_multilink.sdf"
    sdf.parent.mkdir(parents=True)
    sdf.write_bytes(data)

    manifest_path = tmp_path / "native-vehicle" / "vehicle_physics_resource_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "format": MODULE.PHYSICS_MANIFEST_FORMAT,
        "ready": materialized_ready,
        "status": "ready" if materialized_ready else "blocked",
        "blocking_reasons": [] if materialized_ready else ["materialization-blocked"],
        "materialized_resources_ready": materialized_ready,
        "entries": {
            "sdf": {
                "resource_id": "bmw-sdf-fixture",
                "path": MODULE.TARGET_RESOURCE,
                "decoded_sha256": MODULE.TARGET_RESOURCE_SHA256,
                "materialized_path": str(sdf),
                "materialized_sha256": MODULE.TARGET_RESOURCE_SHA256,
                "materialization_source": (
                    MODULE.TYPED_CLOSURE_FORMAT
                    if manifest_source is None
                    else manifest_source
                ),
            }
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    bootstrap_path = tmp_path / "runtime_bootstrap.json"
    bootstrap = {
        "format": MODULE.RUNTIME_BOOTSTRAP_FORMAT,
        "offline_build_ready": True,
        "runtime_ready": False,
        "vehicle": MODULE.TARGET_VEHICLE,
        "readiness": {
            "retail_archive_identity_ready": retail_ready,
            "vehicle_physics_materialized_resources_ready": materialized_ready,
        },
        "artifacts": {
            "vehicle_sdf": str(sdf if bootstrap_sdf is None else bootstrap_sdf),
            "vehicle_physics_manifest": str(manifest_path),
        },
    }
    bootstrap_path.write_text(json.dumps(bootstrap), encoding="utf-8")
    return bootstrap_path, manifest_path, sdf


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
    assert report["source_mode"] == "retail-bff-extraction"
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
    path.write_text(json.dumps(intake), encoding="utf-8")
    with pytest.raises(ValueError, match="entry index drift"):
        MODULE._load_intake(path)


def test_runtime_bootstrap_exact_typed_sdf_materializes_body0_without_bff(
    tmp_path,
    monkeypatch,
):
    data = _sdf_bytes(pos=(4.0, 5.0, 6.0), ori=(0.0, 0.0, 0.0))
    bootstrap, manifest, sdf = _runtime_bootstrap_fixture(tmp_path, data)
    monkeypatch.setattr(MODULE, "_sha256_bytes", lambda value: MODULE.TARGET_RESOURCE_SHA256)

    report = MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(
        bootstrap
    )

    assert report["ready"] is True
    assert report["source_mode"] == "offline-runtime-bootstrap-typed-sdf"
    assert report["retail_archive"]["input_path"] is None
    assert report["runtime_bootstrap"] == {
        "format": MODULE.RUNTIME_BOOTSTRAP_FORMAT,
        "path": str(bootstrap),
        "vehicle_physics_manifest": str(manifest.resolve()),
        "vehicle_sdf_handoff_consumed": True,
    }
    assert report["resource"]["materialized_path"] == str(sdf.resolve())
    assert report["resource"]["decoded_sha256"] == MODULE.TARGET_RESOURCE_SHA256
    assert report["body0"]["pos"] == [4.0, 5.0, 6.0]
    assert report["body0"]["ori"] == [0.0, 0.0, 0.0]
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["next_proof"]["requires_materialized_sdf"] is False
    assert report["scope"]["typed_resource_identity_rederived"] is False


def test_runtime_bootstrap_rehashes_current_sdf_bytes(tmp_path):
    data = _sdf_bytes()
    bootstrap, _, _ = _runtime_bootstrap_fixture(tmp_path, data)

    with pytest.raises(ValueError, match="current SHA-256 mismatch"):
        MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(bootstrap)


def test_runtime_bootstrap_vehicle_sdf_must_match_manifest_path(tmp_path, monkeypatch):
    data = _sdf_bytes()
    other = tmp_path / "other.sdf"
    other.write_bytes(data)
    bootstrap, _, _ = _runtime_bootstrap_fixture(
        tmp_path,
        data,
        bootstrap_sdf=other,
    )
    monkeypatch.setattr(MODULE, "_sha256_bytes", lambda value: MODULE.TARGET_RESOURCE_SHA256)

    with pytest.raises(ValueError, match="disagrees with physics manifest"):
        MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(bootstrap)


def test_runtime_bootstrap_requires_retail_identity_and_typed_materialization(
    tmp_path,
    monkeypatch,
):
    data = _sdf_bytes()
    bootstrap, _, _ = _runtime_bootstrap_fixture(
        tmp_path,
        data,
        retail_ready=False,
    )
    monkeypatch.setattr(MODULE, "_sha256_bytes", lambda value: MODULE.TARGET_RESOURCE_SHA256)

    with pytest.raises(ValueError, match="retail archive identity is not ready"):
        MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(bootstrap)

    blocked = tmp_path / "blocked"
    blocked.mkdir()
    bootstrap2, _, _ = _runtime_bootstrap_fixture(
        blocked,
        data,
        materialized_ready=False,
    )
    with pytest.raises(ValueError, match="typed physics materializations are not ready"):
        MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(bootstrap2)


def test_runtime_bootstrap_requires_typed_closure_materialization_source(
    tmp_path,
    monkeypatch,
):
    data = _sdf_bytes()
    bootstrap, _, _ = _runtime_bootstrap_fixture(
        tmp_path,
        data,
        manifest_source="guessed-path",
    )
    monkeypatch.setattr(MODULE, "_sha256_bytes", lambda value: MODULE.TARGET_RESOURCE_SHA256)

    with pytest.raises(ValueError, match="materialization source drift"):
        MODULE.materialize_bmw_body0_bind_resource_from_runtime_bootstrap(bootstrap)
