import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_vehicle_named_body_topology_frontier.py"
    spec = importlib.util.spec_from_file_location("vehicle_named_body_topology", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _identity(module):
    return {
        "format": module.IDENTITY_FORMAT,
        "handoff": {
            "persistent_BODY_pose_available": True,
            "vehicle_BODY_selection_ready": False,
            "selected_BODY_index": None,
        },
        "scope": {"update_child_to_BODY_identity_proven": False},
    }


def _body_abi(module):
    return {
        "format": module.BODY_ABI_FORMAT,
        "vehicle_topology": {
            "component_slots": {
                "count": 4,
                "base": 0x400,
                "stride": 0xA80,
                "component_offsets": [0x400, 0xE80, 0x1900, 0x2380],
                "wheel_body_pointer_relative": 0x420,
                "spindle_body_pointer_relative": 0x424,
                "wheel_body_pointer_absolute": [0x820, 0x12A0, 0x1D20, 0x27A0],
                "spindle_body_pointer_absolute": [0x824, 0x12A4, 0x1D24, 0x27A4],
            },
            "rear_axle_body_pointer": 0x2E00,
        },
    }


def _manifest(module, digest=None):
    digest = digest or module.BMW_SDF_SHA256
    return {
        "format": module.BMW_MANIFEST_FORMAT,
        "source_archive": module.BMW_ARCHIVE,
        "archive_entry_points": [
            {
                "path": module.BMW_SDF_PATH,
                "entry_index": 1091,
                "uncompressed_size": 5056,
                "sha256": digest,
            }
        ],
        "sdf": {
            "sha256": digest,
            "body_count": module.BMW_SDF_BODY_COUNT,
            "body_stride": "0x170",
        },
    }


def _fixture(tmp_path, module, *, digest=None):
    identity = tmp_path / "identity.json"
    body = tmp_path / "body.json"
    manifest = tmp_path / "manifest.json"
    _write(identity, _identity(module))
    _write(body, _body_abi(module))
    _write(manifest, _manifest(module, digest))
    return identity, body, manifest


def _sdf_text(module, names=None):
    names = names or [
        "body",
        "fl_wheel", "fl_spindle", "fr_wheel", "fr_spindle",
        "rl_wheel", "rl_spindle", "rr_wheel", "rr_spindle",
        "rear_axle", "driver_head",
    ]
    assert len(names) == module.BMW_SDF_BODY_COUNT
    return "\n".join(f"[BODY]\nname={name} mass=1 inertia=(1,1,1)" for name in names) + "\n"


def test_cardinality_difference_remains_nonsemantic_without_exact_sdf(tmp_path):
    module = _module()
    identity, body, manifest = _fixture(tmp_path, module)
    report = module.build_vehicle_named_body_topology_frontier(identity, body, manifest)

    assert report["format"] == "SHIFT.VehicleNamedBodyTopologyFrontier/1"
    card = report["cardinality_frontier"]
    assert card["retail_sdf_BODY_record_count"] == 11
    assert card["named_vehicle_BODY_field_role_count"] == 9
    assert card["arithmetic_difference"] == 2
    assert card["arithmetic_difference_is_exact_residual_candidate_count"] is False
    assert card["exact_residual_BODY_count"] is None
    assert report["scope"]["nine_named_roles_plus_eleven_body_records_proves_two_candidates_without_exact_sdf"] is False
    assert report["handoff"]["vehicle_BODY_selection_ready"] is False
    assert report["handoff"]["selected_BODY_index"] is None
    assert report["next_instruction_targets"] == ["0x00713050", "0x00794a30", "0x007615c0"]


def test_exact_hash_matched_sdf_closes_name_order_and_residual_rows(tmp_path):
    module = _module()
    text = _sdf_text(module)
    digest = hashlib.sha256(text.encode()).hexdigest()
    identity, body, manifest = _fixture(tmp_path, module, digest=digest)
    sdf = tmp_path / "aarm_multilink.sdf"
    sdf.write_text(text, encoding="utf-8")

    report = module.build_vehicle_named_body_topology_frontier(
        identity, body, manifest, sdf_source_path=sdf, expected_sdf_sha256=digest
    )
    card = report["cardinality_frontier"]
    assert card["exact_sdf_BODY_name_order_ready"] is True
    assert card["arithmetic_difference_is_exact_residual_candidate_count"] is True
    assert card["exact_residual_BODY_count"] == 2
    assert card["exact_residual_BODY_rows"] == [
        {"index": 0, "name": "body"},
        {"index": 10, "name": "driver_head"},
    ]
    matches = {row["name"]: row["runtime_BODY_index"] for row in card["exact_named_BODY_matches"]}
    assert matches["fl_wheel"] == 1
    assert matches["rear_axle"] == 9
    assert report["scope"]["named_body_roles_are_distinct_runtime_indices"] is True
    assert report["handoff"]["main_chassis_BODY_selected"] is False


def test_exact_sdf_hash_mismatch_fails_closed(tmp_path):
    module = _module()
    identity, body, manifest = _fixture(tmp_path, module)
    sdf = tmp_path / "aarm_multilink.sdf"
    sdf.write_text(_sdf_text(module), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        module.build_vehicle_named_body_topology_frontier(identity, body, manifest, sdf_source_path=sdf)


def test_missing_named_body_in_exact_sdf_fails_closed(tmp_path):
    module = _module()
    names = [
        "body",
        "not_fl_wheel", "fl_spindle", "fr_wheel", "fr_spindle",
        "rl_wheel", "rl_spindle", "rr_wheel", "rr_spindle",
        "rear_axle", "driver_head",
    ]
    text = _sdf_text(module, names)
    digest = hashlib.sha256(text.encode()).hexdigest()
    identity, body, manifest = _fixture(tmp_path, module, digest=digest)
    sdf = tmp_path / "aarm_multilink.sdf"
    sdf.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="fl_wheel"):
        module.build_vehicle_named_body_topology_frontier(
            identity, body, manifest, sdf_source_path=sdf, expected_sdf_sha256=digest
        )


def test_vehicle_BODY_topology_drift_fails_closed(tmp_path):
    module = _module()
    identity, body, manifest = _fixture(tmp_path, module)
    value = json.loads(body.read_text())
    value["vehicle_topology"]["component_slots"]["wheel_body_pointer_absolute"][0] = 0x818
    _write(body, value)
    with pytest.raises(ValueError, match="topology drift"):
        module.build_vehicle_named_body_topology_frontier(identity, body, manifest)


def test_upstream_BODY_preselection_is_rejected(tmp_path):
    module = _module()
    identity, body, manifest = _fixture(tmp_path, module)
    value = json.loads(identity.read_text())
    value["handoff"]["vehicle_BODY_selection_ready"] = True
    value["handoff"]["selected_BODY_index"] = 0
    _write(identity, value)
    with pytest.raises(ValueError, match="already selects BODY"):
        module.build_vehicle_named_body_topology_frontier(identity, body, manifest)
