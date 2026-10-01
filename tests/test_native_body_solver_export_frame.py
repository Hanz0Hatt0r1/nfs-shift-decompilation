import json
import struct

import pytest

from native_body_solver_export_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_MAGIC,
    PACKET_VERSION,
    REQUIRED_PROOF_FLAGS,
    build_native_body_solver_export_frame,
    build_native_body_solver_export_frame_file,
)


def _source():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "synthetic-body-export-regression",
        "contribution_values_ready": True,
        "body_order_ready": True,
        "destination_shape_ready": True,
        "body_count": 3,
        "solver_scalar_count": 6,
        "bodies": [
            {
                "body_index": 0,
                "solver_vector": [1.0, 2.0, 3.0],
                "solver_matrix": [1.0, 2.0, 3.0, 4.0],
            },
            {
                "body_index": 1,
                "solver_vector": [-1.0, 0.5],
                "solver_matrix": [0.5, -2.0],
            },
            {
                "body_index": 2,
                "solver_vector": [0.0, 0.0, 4.0, 5.0],
                "solver_matrix": [1.5],
            },
        ],
    }


def test_prepared_body_export_frame_accumulates_in_body_order():
    report = build_native_body_solver_export_frame(_source())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["source_function"] == "FUN_007ba570"
    assert report["body_count"] == 3
    assert report["solver_scalar_count"] == 6
    assert report["solver_matrix_double_count"] == 36
    assert report["oracle"]["solver_vector"] == pytest.approx(
        [0.0, 2.5, 7.0, 5.0, 0.0, 0.0]
    )
    assert report["oracle"]["solver_matrix"][:4] == pytest.approx(
        [3.0, 0.0, 3.0, 4.0]
    )
    assert report["oracle"]["solver_matrix"][4:] == pytest.approx(
        [0.0] * 32
    )
    assert report["boundary"]["derives_body_contributions"] is False
    assert report["boundary"]["fixed_step_runtime_integration"] is False


@pytest.mark.parametrize(
    "proof",
    [
        "contribution_values_ready",
        "body_order_ready",
        "destination_shape_ready",
    ],
)
def test_missing_export_frame_proof_fails_closed(proof):
    source = _source()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_body_solver_export_frame(source)


def test_noncontiguous_body_order_is_rejected():
    source = _source()
    source["bodies"][1]["body_index"] = 7
    with pytest.raises(ValueError, match="BODY order"):
        build_native_body_solver_export_frame(source)


def test_contribution_larger_than_destination_is_rejected():
    source = _source()
    source["bodies"][0]["solver_vector"] = [1.0] * 7
    with pytest.raises(ValueError, match="exceeds destination length"):
        build_native_body_solver_export_frame(source)


def test_nonfinite_contribution_is_rejected():
    source = _source()
    source["bodies"][0]["solver_matrix"][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        build_native_body_solver_export_frame(source)


def test_body_export_frame_file_writes_stable_packet(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(_source()), encoding="utf-8")
    report = build_native_body_solver_export_frame_file(
        source,
        tmp_path / "prepared",
    )

    packet_path = tmp_path / "prepared/body_solver_export.sbex"
    manifest_path = (
        tmp_path / "prepared/body_solver_export_manifest.json"
    )
    packet = packet_path.read_bytes()
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    header = struct.unpack_from("<4s6I", packet, 0)
    assert header[0] == PACKET_MAGIC
    assert header[1] == PACKET_VERSION
    assert header[2] == 3
    assert header[3] == 6
    assert header[4] == 36
    assert header[5] == REQUIRED_PROOF_FLAGS
    assert header[6] == 0

    assert report["packet"]["path"] == "body_solver_export.sbex"
    assert manifest["packet"]["sha256"] == report["packet"]["sha256"]
    assert manifest["packet"]["size"] == len(packet)
    assert manifest["verification_scope"] == (
        "synthetic-body-export-regression"
    )
