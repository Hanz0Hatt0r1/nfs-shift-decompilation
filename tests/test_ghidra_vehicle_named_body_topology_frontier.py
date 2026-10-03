import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_vehicle_named_body_topology_frontier.py"
    spec = importlib.util.spec_from_file_location("vehicle_named_body_topology_v2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _identity(m):
    return {
        "format": m.IDENTITY_FORMAT,
        "handoff": {"persistent_BODY_pose_available": True, "vehicle_BODY_selection_ready": False, "selected_BODY_index": None},
        "scope": {"update_child_to_BODY_identity_proven": False},
    }


def _body_abi(m):
    return {
        "format": m.BODY_ABI_FORMAT,
        "vehicle_topology": {
            "component_slots": {
                "count": 4, "base": 0x400, "stride": 0xA80,
                "component_offsets": [0x400, 0xE80, 0x1900, 0x2380],
                "wheel_body_pointer_relative": 0x420,
                "spindle_body_pointer_relative": 0x424,
                "wheel_body_pointer_absolute": [0x820, 0x12A0, 0x1D20, 0x27A0],
                "spindle_body_pointer_absolute": [0x824, 0x12A4, 0x1D24, 0x27A4],
            },
            "rear_axle_body_pointer": 0x2E00,
        },
    }


def _manifest(m, digest=None):
    digest = digest or m.BMW_SDF_SHA256
    return {
        "format": m.BMW_MANIFEST_FORMAT,
        "source_archive": m.BMW_ARCHIVE,
        "archive_entry_points": [{
            "path": m.BMW_SDF_PATH, "entry_index": 1091,
            "uncompressed_size": 5056, "sha256": digest,
        }],
        "sdf": {"sha256": digest, "body_count": 11, "body_stride": "0x170"},
    }


def _bodies():
    return [
        "body", "fl_spindle", "fr_spindle", "fl_wheel", "fr_wheel",
        "rl_spindle", "rr_spindle", "rl_wheel", "rr_wheel", "fuel_tank", "driver_head",
    ]


def _phase404(m, digest=None, bodies=None):
    digest = digest or m.BMW_SDF_SHA256
    return {
        "format": m.PHASE404_FORMAT,
        "archive": {"filename": m.BMW_ARCHIVE, "size_bytes": 18934688, "sha256": "c" * 64},
        "sdf_entry": {
            "index": 1091, "path": m.BMW_SDF_PATH, "compression_type": 2,
            "compressed_size": 1110, "uncompressed_size": 5056, "decoded_sha256": digest,
        },
        "structure": {"body_count": 11},
        "bodies": list(bodies or _bodies()),
        "status": "decoded-from-user-supplied-bff",
    }


def _fixture(tmp_path, m, *, digest=None, bodies=None):
    identity = tmp_path / "identity.json"
    body = tmp_path / "body.json"
    manifest = tmp_path / "manifest.json"
    phase404 = tmp_path / "phase404.json"
    _write(identity, _identity(m)); _write(body, _body_abi(m))
    _write(manifest, _manifest(m, digest)); _write(phase404, _phase404(m, digest, bodies))
    return identity, body, manifest, phase404


def test_phase404_exact_order_maps_eight_names_and_keeps_rear_axle_separate(tmp_path):
    m = _module()
    identity, body, manifest, phase404 = _fixture(tmp_path, m)
    report = m.build_vehicle_named_body_topology_frontier(
        identity, body, manifest, phase404_evidence_path=phase404
    )
    assert report["format"] == "SHIFT.VehicleNamedBodyTopologyFrontier/2"
    assert report["retail_sdf"]["body_name_order_state"] == "verified-archive-derived-phase404"
    assert [row["name"] for row in report["retail_sdf"]["body_rows"]] == _bodies()
    join = report["exact_name_join"]
    assert join["exact_sdf_BODY_name_order_ready"] is True
    assert join["exact_non_wheel_spindle_BODY_rows"] == [
        {"index": 0, "name": "body"},
        {"index": 9, "name": "fuel_tank"},
        {"index": 10, "name": "driver_head"},
    ]
    assert join["rear_axle_is_exact_sdf_name"] is False
    assert join["rear_axle_runtime_BODY_index"] is None
    matches = {row["name"]: row["runtime_BODY_index"] for row in join["exact_named_BODY_matches"]}
    assert matches == {
        "fl_wheel": 3, "fl_spindle": 1,
        "fr_wheel": 4, "fr_spindle": 2,
        "rl_wheel": 7, "rl_spindle": 5,
        "rr_wheel": 8, "rr_spindle": 6,
    }
    setup = report["vehicle_solver_setup"]
    assert setup["vehicle_BODY_field_role_count"] == 9
    assert setup["exact_sdf_name_mapped_field_count"] == 8
    assert setup["semantic_only_field_count"] == 1
    rear = [row for row in setup["BODY_fields"] if row["name"] == "rear_axle"][0]
    assert rear["sdf_name_state"] == "not-an-exact-retail-sdf-name"
    assert rear["runtime_BODY_index"] is None
    assert report["handoff"]["phase698_positive_selection_admissible"] is False


def test_phase404_provenance_must_match_manifest_hash(tmp_path):
    m = _module()
    identity, body, manifest, phase404 = _fixture(tmp_path, m)
    value = json.loads(phase404.read_text())
    value["sdf_entry"]["decoded_sha256"] = "0" * 64
    _write(phase404, value)
    with pytest.raises(ValueError, match="Phase 404 SDF SHA-256 drift"):
        m.build_vehicle_named_body_topology_frontier(
            identity, body, manifest, phase404_evidence_path=phase404
        )


def test_phase404_duplicate_BODY_name_fails_closed(tmp_path):
    m = _module()
    bodies = _bodies(); bodies[-1] = "fuel_tank"
    identity, body, manifest, phase404 = _fixture(tmp_path, m, bodies=bodies)
    with pytest.raises(ValueError, match="duplicate BODY name"):
        m.build_vehicle_named_body_topology_frontier(
            identity, body, manifest, phase404_evidence_path=phase404
        )


def test_rear_axle_is_not_required_as_exact_sdf_name(tmp_path):
    m = _module()
    identity, body, manifest, phase404 = _fixture(tmp_path, m)
    report = m.build_vehicle_named_body_topology_frontier(
        identity, body, manifest, phase404_evidence_path=phase404
    )
    names = {row["name"] for row in report["retail_sdf"]["body_rows"]}
    assert "rear_axle" not in names
    assert report["scope"]["rear_axle_semantic_role_is_sdf_name"] is False
    assert any(row["id"] == "rear-axle-field-role-to-SDF-index" for row in report["blockers"])


def test_raw_sdf_optional_crosscheck_must_match_phase404_order(tmp_path):
    m = _module()
    lines = []
    for name in _bodies():
        lines.append(f"[BODY]\nname={name} mass=1 inertia=(1,1,1)")
    text = "\n".join(lines) + "\n"
    digest = hashlib.sha256(text.encode()).hexdigest()
    identity, body, manifest, phase404 = _fixture(tmp_path, m, digest=digest)
    sdf = tmp_path / "aarm_multilink.sdf"; sdf.write_text(text, encoding="utf-8")
    report = m.build_vehicle_named_body_topology_frontier(
        identity, body, manifest, phase404_evidence_path=phase404,
        sdf_source_path=sdf, expected_sdf_sha256=digest,
    )
    assert report["inputs"]["raw_sdf_crosscheck"] == str(sdf)


def test_vehicle_topology_drift_fails_closed(tmp_path):
    m = _module()
    identity, body, manifest, phase404 = _fixture(tmp_path, m)
    value = json.loads(body.read_text())
    value["vehicle_topology"]["rear_axle_body_pointer"] = 0x2DF0
    _write(body, value)
    with pytest.raises(ValueError, match="topology drift"):
        m.build_vehicle_named_body_topology_frontier(
            identity, body, manifest, phase404_evidence_path=phase404
        )
