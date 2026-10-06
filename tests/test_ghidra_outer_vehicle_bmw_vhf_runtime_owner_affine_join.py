from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_bmw_vhf_runtime_owner_affine_join.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_bmw_vhf_runtime_owner_affine_join", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _source(tmp_path: Path, *, owner_field: str = "0x1340") -> Path:
    path = tmp_path / "SHIFT.exe.c"
    path.write_text(
        """
void FUN_00480700(int param_1)
{
  undefined4 local_50[16];
  undefined4 local_20;
  undefined4 local_1c;
  undefined4 local_18;
  FUN_0042fc90(local_50,(undefined4 *)(param_1 + 0x1028));
  local_20=*(undefined4 *)(param_1 + 0xa10);
  local_1c=*(undefined4 *)(param_1 + 0xa14);
  local_18=*(undefined4 *)(param_1 + 0xa18);
  FUN_004a8c20(param_1 + %s,local_50);
}
""" % owner_field,
        encoding="utf-8",
    )
    MODULE.EXPECTED_SOURCE_SHA256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def _bridge(source_sha: str, *, preclaim: bool = False, owner_field: str = "participant+0x1340") -> dict:
    return {
        "format": MODULE.BRIDGE_FORMAT,
        "ready": True,
        "status": "outer-render-snapshot-affine-bridge-proven-vhf-delta-join-pending",
        "retail": {
            "program": MODULE.PROGRAM,
            "md5": MODULE.PE_MD5,
            "source_sha256": source_sha,
        },
        "handoff": {
            "outer_vehicle_render_snapshot_slot_identity_ready": True,
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "render_root_translation_delta_producer_bounded": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "render_participant_relation": {
            "vehicle_render_model": owner_field,
            "derived_rotation_matrix": "participant+0x1028",
            "root_translation": [
                "participant+0xa10",
                "participant+0xa14",
                "participant+0xa18",
            ],
            "world_affine_consumed_by": "FUN_004a8c20",
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local"
        },
    }


def _bmw_join(*, preclaim: bool = False, canonical_path: str | None = None) -> dict:
    return {
        "format": MODULE.BMW_RESOURCE_FORMAT,
        "ready": True,
        "retail": {"program": MODULE.PROGRAM, "md5": MODULE.PE_MD5},
        "input_owner_proof": {
            "format": MODULE.OWNER_FORMAT,
            "source_commit": "4fcb9e2223592928d5e8a0d2f578f269b195bdc3",
            "vehicle_render_hierarchy_owner_ready": True,
            "vehicle_render_model_property_name": "Vehicle Render Model",
            "vehicle_render_model_property_field": "+0x54",
        },
        "selected_vehicle_descriptor": {
            "property_value": MODULE.VEHICLE_RENDER_MODEL,
            "selected_BMW_vehicle_render_model_value_ready": True,
        },
        "canonical_bmw_vhf_resource": {
            "resolved_path": canonical_path or MODULE.CANONICAL_VHF,
            "decoded_sha256": "e" * 64,
            "canonical_BMW_VHF_resource_join_ready": True,
        },
        "handoff": {
            "vehicle_render_hierarchy_owner_ready": True,
            "selected_BMW_vehicle_render_model_value_ready": True,
            "canonical_BMW_VHF_resource_join_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
            "BODY0_bind_frame_proof_ready": False,
        },
    }


def _paths(tmp_path: Path, *, bridge_preclaim: bool = False, bmw_preclaim: bool = False):
    source = _source(tmp_path)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    bridge = _write_json(tmp_path / "bridge.json", _bridge(source_sha, preclaim=bridge_preclaim))
    bmw = _write_json(tmp_path / "bmw.json", _bmw_join(preclaim=bmw_preclaim))
    return bridge, bmw, source


def test_positive_join_proves_runtime_owner_affine_but_not_vhf_root_identity(tmp_path):
    bridge, bmw, source = _paths(tmp_path)
    report = MODULE.analyze(bridge, bmw, source)

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["same_participant_executable_join"]["same_participant_receiver_proven"] is True
    assert report["same_participant_executable_join"]["root_affine_and_render_model_owner_meet_at_direct_call"] is True
    assert report["claim"]["outer_vehicle_affine_reaches_exact_bmw_vhf_runtime_owner"] is True
    assert report["claim"]["canonical_bmw_vhf_runtime_render_model_owner"] == MODULE.CANONICAL_VHF
    assert report["claim"]["resource_local_vhf_hierarchy_root_affine_applied_or_identity"] is False
    assert report["handoff"]["outer_vehicle_affine_to_canonical_BMW_VHF_runtime_owner_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["limits"]["FUN_004ae150_promoted_to_root_setter"] is False
    assert report["limits"]["callgraph_adjacency_is_ownership"] is False


def test_rejects_world_consumer_source_without_exact_render_model_owner_operand(tmp_path):
    source = _source(tmp_path, owner_field="0x133c")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    bridge = _write_json(tmp_path / "bridge.json", _bridge(source_sha))
    bmw = _write_json(tmp_path / "bmw.json", _bmw_join())

    with pytest.raises(ValueError, match="required source fact drift"):
        MODULE.analyze(bridge, bmw, source)


def test_rejects_bridge_participant_owner_field_drift(tmp_path):
    source = _source(tmp_path)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    bridge = _write_json(
        tmp_path / "bridge.json",
        _bridge(source_sha, owner_field="participant+0x133c"),
    )
    bmw = _write_json(tmp_path / "bmw.json", _bmw_join())

    with pytest.raises(ValueError, match="Vehicle Render Model field drift"):
        MODULE.analyze(bridge, bmw, source)


def test_rejects_upstream_frame_identity_preclaim(tmp_path):
    bridge, bmw, source = _paths(tmp_path, bridge_preclaim=True)
    with pytest.raises(ValueError, match="preclaims outer/VHF root identity"):
        MODULE.analyze(bridge, bmw, source)


def test_rejects_bmw_resource_frame_identity_preclaim(tmp_path):
    bridge, bmw, source = _paths(tmp_path, bmw_preclaim=True)
    with pytest.raises(ValueError, match="preclaims outer/VHF root identity"):
        MODULE.analyze(bridge, bmw, source)


def test_rejects_noncanonical_bmw_vhf_resource(tmp_path):
    source = _source(tmp_path)
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    bridge = _write_json(tmp_path / "bridge.json", _bridge(source_sha))
    bmw = _write_json(
        tmp_path / "bmw.json",
        _bmw_join(canonical_path="vehicles/bmw_m3_e36/bmw_m3_e36_cockpit.vhf"),
    )

    with pytest.raises(ValueError, match="canonical BMW VHF resource path drift"):
        MODULE.analyze(bridge, bmw, source)


def test_rejects_decompiler_source_hash_not_pinned_by_bridge(tmp_path):
    bridge, bmw, source = _paths(tmp_path)
    bridge_doc = json.loads(bridge.read_text(encoding="utf-8"))
    bridge_doc["retail"]["source_sha256"] = "0" * 64
    bridge.write_text(json.dumps(bridge_doc), encoding="utf-8")

    with pytest.raises(ValueError, match="bridge source SHA-256"):
        MODULE.analyze(bridge, bmw, source)
