from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_bmw_vhf_runtime_owner_affine_join.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_bmw_vhf_runtime_owner_affine_join", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _bridge(*, preclaim: bool = False, owner_field: str = "participant+0x1340") -> dict:
    return {
        "format": MODULE.BRIDGE_FORMAT,
        "ready": True,
        "status": "outer-render-snapshot-affine-bridge-proven-vhf-delta-join-pending",
        "retail": {
            "program": MODULE.PROGRAM,
            "md5": MODULE.PE_MD5,
            "source_sha256": MODULE.CANONICAL_SOURCE_SHA256,
        },
        "handoff": {
            "outer_vehicle_render_snapshot_slot_identity_ready": True,
            "outer_vehicle_to_render_root_symbolic_affine_ready": True,
            "render_root_translation_delta_producer_bounded": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": preclaim,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "slot_identity": {"physical_slot_producer_consumer_bridge_ready": True},
        "render_participant_relation": {
            "vehicle_render_model": owner_field,
            "derived_rotation_matrix": "participant+0x1028",
            "root_translation": [
                "participant+0xa10",
                "participant+0xa14",
                "participant+0xa18",
            ],
            "world_affine_consumed_by": "FUN_004a8c20",
            "world_affine_translation_slots": [12, 13, 14],
            "node_local_FUN_004ae150_promoted_to_root_setter": False,
        },
        "snapshot_relation": {
            "translation_formula": "P_snapshot = P_outer + R_outer * delta_local",
            "independent_rotation_source_present": False,
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
            "vehicle_name": "BMW_M3_E36",
            "property_name": "Vehicle Render Model",
            "property_value": MODULE.VEHICLE_RENDER_MODEL,
            "selected_BMW_vehicle_render_model_value_ready": True,
        },
        "canonical_bmw_vhf_resource": {
            "resolved_path": canonical_path or MODULE.CANONICAL_VHF,
            "decoded_sha256": "e" * 64,
            "root_tag": "CAR",
            "root_name": "BMW_M3_E36",
            "root_node_type": "HIERARCHY",
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


def test_positive_join_proves_runtime_owner_affine_but_not_vhf_root_identity():
    report = MODULE.analyze(_bridge(), _bmw_join())

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    join = report["same_participant_executable_join"]
    assert join["same_participant_affine_and_render_model_owner_ready"] is True
    assert join["render_model_owner"] == "participant+0x1340"
    assert join["selected_runtime_render_model_resource"] == MODULE.CANONICAL_VHF
    assert report["claim"]["outer_vehicle_affine_reaches_exact_bmw_vhf_runtime_owner"] is True
    assert report["claim"]["resource_local_vhf_hierarchy_root_affine_applied_or_identity"] is False
    assert report["handoff"]["outer_vehicle_affine_to_canonical_BMW_VHF_runtime_owner_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["limits"]["FUN_004ae150_promoted_to_root_setter"] is False
    assert report["limits"]["callgraph_adjacency_is_ownership"] is False


def test_rejects_bridge_participant_owner_field_drift():
    with pytest.raises(ValueError, match="render participant relation drift: vehicle_render_model"):
        MODULE.analyze(_bridge(owner_field="participant+0x133c"), _bmw_join())


def test_rejects_bridge_frame_identity_preclaim():
    with pytest.raises(ValueError, match="preclaims downstream gate"):
        MODULE.analyze(_bridge(preclaim=True), _bmw_join())


def test_rejects_bmw_resource_frame_identity_preclaim():
    with pytest.raises(ValueError, match="preclaims downstream gate"):
        MODULE.analyze(_bridge(), _bmw_join(preclaim=True))


def test_rejects_noncanonical_bmw_vhf_resource():
    with pytest.raises(ValueError, match="canonical BMW VHF resource path drift"):
        MODULE.analyze(
            _bridge(),
            _bmw_join(canonical_path="vehicles/bmw_m3_e36/bmw_m3_e36_cockpit.vhf"),
        )


def test_rejects_bridge_decompiler_source_identity_drift():
    bridge = _bridge()
    bridge["retail"]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="decompiler-source identity drift"):
        MODULE.analyze(bridge, _bmw_join())


def test_rejects_node_local_helper_promotion():
    bridge = _bridge()
    bridge["render_participant_relation"]["node_local_FUN_004ae150_promoted_to_root_setter"] = True
    with pytest.raises(ValueError, match="promotes FUN_004ae150"):
        MODULE.analyze(bridge, _bmw_join())


def test_rejects_physical_slot_continuity_loss():
    bridge = _bridge()
    bridge["slot_identity"]["physical_slot_producer_consumer_bridge_ready"] = False
    with pytest.raises(ValueError, match="physical slot continuity"):
        MODULE.analyze(bridge, _bmw_join())
