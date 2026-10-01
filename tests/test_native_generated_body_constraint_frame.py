import json
import struct

import pytest

from native_generated_body_constraint_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_MAGIC,
    PACKET_VERSION,
    REQUIRED_PROOF_FLAGS,
    build_native_generated_body_constraint_frame,
    build_native_generated_body_constraint_frame_file,
)


def _body():
    return {
        "body_index": 0,
        "body_position": [1.0, 2.0, 3.0],
        "body_correction": [0.0, 0.0, 0.0],
        "body_axis": [0.25, 0.5, 0.75],
        "angular_state": [0.125, 0.25, 0.5],
        "linear_state": [0.5, 0.75, 1.0],
        "inverse_scalar": 1.0,
        "body_frame": [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ],
        "body_tensor": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        "scales": {
            "linear_scale": 2.0,
            "quadratic_scale": 3.0,
        },
        "row_indices": [0, 6, 12, 18, 24, 30],
        "matrix_double_count": 36,
        "joints": [{
            "position": [1.5, 2.5, 3.5],
            "scalar_base": 0,
            "side_flag": 0,
        }],
        "hinges": [{
            "angular": [1.0, 2.0, 3.0],
            "linear": [4.0, 5.0, 6.0],
            "position": [1.0, 2.0, 3.0],
            "frame_offset": [0.5, 1.0, 1.5],
            "scalar_base": 3,
            "side_flag": 0,
        }],
        "bars": [{
            "point": [2.0, 1.0, 3.0],
            "direction": [1.0, 2.0, 1.0],
            "side_bias": 0.5,
            "scalar_base": 5,
            "side_flag": 0,
        }],
    }


def _source():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "phase627-generated-body-frame-regression",
        "sample_values_ready": True,
        "body_order_ready": True,
        "row_layout_ready": True,
        "provider_absent": True,
        "body_count": 1,
        "solver_scalar_count": 6,
        "bodies": [_body()],
    }


def test_generated_frame_contains_inputs_not_contribution_values():
    report = build_native_generated_body_constraint_frame(_source())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["body_count"] == 1
    assert report["solver_scalar_count"] == 6
    assert report["solver_matrix_double_count"] == 36
    assert report["sample_counts"] == {
        "joint": 1,
        "hinge": 1,
        "bar": 1,
    }
    assert report["boundary"]["stores_generated_contribution_values"] is False
    assert report["boundary"]["derives_contributions_in_native"] is True
    assert report["boundary"]["sample_refresh_executed"] is False
    assert report["boundary"]["provider_present"] is False


@pytest.mark.parametrize(
    "proof",
    [
        "sample_values_ready",
        "body_order_ready",
        "row_layout_ready",
        "provider_absent",
    ],
)
def test_missing_generated_frame_proof_fails_closed(proof):
    source = _source()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_generated_body_constraint_frame(source)


def test_noncanonical_row_layout_is_rejected():
    source = _source()
    source["bodies"][0]["row_indices"] = [18, 0, 30, 6, 24, 12]
    with pytest.raises(ValueError, match="canonical builtin layout"):
        build_native_generated_body_constraint_frame(source)


def test_invalid_side_flag_is_rejected():
    source = _source()
    source["bodies"][0]["bars"][0]["side_flag"] = 2
    with pytest.raises(ValueError, match="side_flag must be 0 or 1"):
        build_native_generated_body_constraint_frame(source)


def test_sample_scalar_range_is_rejected_early():
    source = _source()
    source["bodies"][0]["hinges"][0]["scalar_base"] = 5
    with pytest.raises(ValueError, match="outside solver scalar domain"):
        build_native_generated_body_constraint_frame(source)


def test_generated_frame_file_writes_stable_packet(tmp_path):
    source_path = tmp_path / "input.json"
    source_path.write_text(json.dumps(_source()), encoding="utf-8")

    report = build_native_generated_body_constraint_frame_file(
        source_path,
        tmp_path / "prepared",
    )
    packet_path = (
        tmp_path / "prepared/generated_body_constraints.gbcf"
    )
    packet = packet_path.read_bytes()
    manifest = json.loads(
        (
            tmp_path
            / "prepared/generated_body_constraints_manifest.json"
        ).read_text(encoding="utf-8")
    )

    header = struct.unpack_from("<4s6I", packet, 0)
    assert header == (
        PACKET_MAGIC,
        PACKET_VERSION,
        1,
        6,
        36,
        REQUIRED_PROOF_FLAGS,
        0,
    )
    body_head = struct.unpack_from("<6I", packet, 28)
    assert body_head == (0, 1, 1, 1, 6, 0)

    assert report["packet"]["path"] == "generated_body_constraints.gbcf"
    assert manifest["packet"]["sha256"] == report["packet"]["sha256"]
    assert manifest["packet"]["size"] == len(packet)
    assert manifest["verification_scope"] == (
        "phase627-generated-body-frame-regression"
    )
