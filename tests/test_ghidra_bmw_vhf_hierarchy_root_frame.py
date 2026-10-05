from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_vhf_hierarchy_root_frame.py"
SPEC = importlib.util.spec_from_file_location("bmw_vhf_hierarchy_root_frame", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _vhf(
    *,
    root_name: str = "Root",
    root_matrix: str = "7",
    duplicate_hierarchy: bool = False,
    missing_matrix: bool = False,
    cycle: bool = False,
) -> bytes:
    extra_hierarchy = (
        '<NODE type="HIERARCHY" Name="Other" MatrixNumber="8" />'
        if duplicate_hierarchy
        else ""
    )
    if missing_matrix:
        matrices = '<MATRIX id="2" Offset="1 2 3" Orientation="0 0 0 1" />'
    elif cycle:
        matrices = (
            '<MATRIX id="7" parent="2" Offset="4 5 6" Orientation="0 0 0 1" />'
            '<MATRIX id="2" parent="7" Offset="1 2 3" Orientation="0 0 0 1" />'
        )
    else:
        matrices = (
            '<MATRIX id="2" Offset="1 2 3" Orientation="0 0 0 1" />'
            '<MATRIX id="7" parent="2" Offset="4 5 6" Orientation="0 0 0 1" />'
            '<MATRIX id="8" Offset="0 0 0" Orientation="0 0 0 1" />'
        )
    return (
        '<CAR Name="BMW_M3_E36">'
        f'<NODE type="HIERARCHY" Name="{root_name}" MatrixNumber="{root_matrix}" />'
        f'{extra_hierarchy}'
        f'{matrices}'
        '</CAR>'
    ).encode("utf-8")


def _join(payload: bytes, *, preclaim: bool = False) -> dict:
    return {
        "format": MODULE.RESOURCE_JOIN_FORMAT,
        "version": 1,
        "ready": True,
        "retail": {"program": MODULE.PROGRAM, "md5": MODULE.PE_MD5},
        "canonical_bmw_vhf_resource": {
            "resolved_path": MODULE.CANONICAL_VHF,
            "archive": "BMW_M3_E36.bff",
            "archive_sha256": "a" * 64,
            "entry_index": 1083,
            "decoded_sha256": hashlib.sha256(payload).hexdigest(),
            "root_tag": "CAR",
            "root_name": MODULE.VEHICLE_NAME,
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


def test_positive_root_frame_resolves_exact_parent_chain_without_outer_identity():
    payload = _vhf()
    report = MODULE.analyze_decoded_vhf(_join(payload), payload)

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "canonical-bmw-vhf-hierarchy-root-frame-proven"
    frame = report["vehicle_root_frame"]
    assert frame["node_type"] == "HIERARCHY"
    assert frame["node_name"] == "Root"
    assert frame["matrix_number"] == "7"
    assert frame["matrix_parent_chain_ids"] == ["2", "7"]
    assert frame["local_offset_xyz"] == [4.0, 5.0, 6.0]
    assert frame["world_matrix_column_vector"][3] == pytest.approx(5.0)
    assert frame["world_matrix_column_vector"][7] == pytest.approx(7.0)
    assert frame["world_matrix_column_vector"][11] == pytest.approx(9.0)
    assert frame["world_matrix_row_vector"][12:15] == pytest.approx([5.0, 7.0, 9.0])
    assert frame["world_matrix_is_identity"] is False
    assert report["handoff"]["canonical_BMW_VHF_hierarchy_root_frame_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["limits"]["resource_identity_is_frame_identity"] is False


def test_identity_root_matrix_still_does_not_promote_outer_vehicle_identity():
    payload = (
        '<CAR Name="BMW_M3_E36">'
        '<NODE type="HIERARCHY" Name="Root" MatrixNumber="0" />'
        '<MATRIX id="0" Offset="0 0 0" Orientation="0 0 0 1" />'
        '</CAR>'
    ).encode("utf-8")
    report = MODULE.analyze_decoded_vhf(_join(payload), payload)

    assert report["vehicle_root_frame"]["world_matrix_is_identity"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["limits"]["root_identity_matrix_implies_outer_vehicle_identity"] is False


def test_rejects_decoded_vhf_sha_mismatch():
    payload = _vhf()
    join = _join(payload)
    with pytest.raises(ValueError, match="decoded BMW VHF SHA-256 disagrees"):
        MODULE.analyze_decoded_vhf(join, payload + b"\n")


def test_rejects_duplicate_direct_hierarchy_roots():
    payload = _vhf(duplicate_hierarchy=True)
    with pytest.raises(ValueError, match="exactly one direct canonical BMW VHF HIERARCHY root"):
        MODULE.analyze_decoded_vhf(_join(payload), payload)


def test_rejects_root_name_drift():
    payload = _vhf(root_name="Vehicle")
    with pytest.raises(ValueError, match="HIERARCHY root name drift"):
        MODULE.analyze_decoded_vhf(_join(payload), payload)


def test_rejects_missing_root_matrix_record():
    payload = _vhf(missing_matrix=True)
    with pytest.raises(ValueError, match="references missing MATRIX id"):
        MODULE.analyze_decoded_vhf(_join(payload), payload)


def test_rejects_matrix_parent_cycle():
    payload = _vhf(cycle=True)
    with pytest.raises(ValueError, match="MATRIX parent cycle"):
        MODULE.analyze_decoded_vhf(_join(payload), payload)


def test_rejects_resource_join_that_preclaims_frame_identity():
    payload = _vhf()
    with pytest.raises(ValueError, match="preclaims outer/VHF frame identity"):
        MODULE.analyze_decoded_vhf(_join(payload, preclaim=True), payload)
