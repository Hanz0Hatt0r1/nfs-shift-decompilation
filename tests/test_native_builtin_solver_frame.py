import json
import struct

import pytest

from native_builtin_solver_frame import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_MAGIC,
    PACKET_VERSION,
    REQUIRED_PROOF_FLAGS,
    build_native_builtin_solver_frame,
    build_native_builtin_solver_frame_file,
)
from sdf_builtin_sparse_solver_runtime import build_dense_solver_graph


def _source():
    forward, reverse = build_dense_solver_graph(3)
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "synthetic-regression-fixture",
        "provider_absent_proven": True,
        "matrix_rhs_ready": True,
        "reset_selection_ready": True,
        "sparse_graph_ready": True,
        "matrix": [
            [4.0, 1.0, 1.0],
            [1.0, 3.0, 0.0],
            [1.0, 0.0, 2.0],
        ],
        "rhs": [9.0, 7.0, 7.0],
        "reset_nodes": [2],
        "forward_records": forward,
        "reverse_records": reverse,
    }


def test_prepared_solver_frame_executes_reset_then_builtin_solver():
    report = build_native_builtin_solver_frame(_source())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["scalar_count"] == 3
    assert report["reset_nodes"] == [2]
    assert report["proofs"] == {
        "provider_absent_proven": True,
        "matrix_rhs_ready": True,
        "reset_selection_ready": True,
        "sparse_graph_ready": True,
    }
    assert report["dispatch"]["execution_order"] == [
        "FUN_007b2210",
        "FUN_007b0f20",
    ]
    assert report["oracle"]["solution"] == pytest.approx(
        [1.8181818181818181, 1.7272727272727273, 0.0],
        rel=1e-12,
        abs=1e-12,
    )
    assert report["boundary"]["derives_provider_absence"] is False
    assert report["boundary"]["fixed_step_runtime_integration"] is False


@pytest.mark.parametrize(
    "proof",
    [
        "provider_absent_proven",
        "matrix_rhs_ready",
        "reset_selection_ready",
        "sparse_graph_ready",
    ],
)
def test_missing_runtime_proof_fails_closed(proof):
    source = _source()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_builtin_solver_frame(source)


def test_solver_frame_rejects_invalid_sparse_graph():
    source = _source()
    source["forward_records"][1]["items"][0]["dependencies"] = [1]
    with pytest.raises(ValueError, match="invalid pivot dependency"):
        build_native_builtin_solver_frame(source)


def test_solver_frame_rejects_nonfinite_matrix():
    source = _source()
    source["matrix"][0][0] = float("nan")
    with pytest.raises(ValueError, match="must be finite"):
        build_native_builtin_solver_frame(source)


def test_solver_frame_file_writes_packet_and_manifest(tmp_path):
    source = tmp_path / "frame.json"
    source.write_text(json.dumps(_source()), encoding="utf-8")

    report = build_native_builtin_solver_frame_file(
        source,
        tmp_path / "prepared",
    )

    packet_path = tmp_path / "prepared/solver_frame.sbfr"
    manifest_path = tmp_path / "prepared/solver_frame_manifest.json"
    packet = packet_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    header = struct.unpack_from("<4s7I", packet, 0)
    assert header[0] == PACKET_MAGIC
    assert header[1] == PACKET_VERSION
    assert header[2] == 3
    assert header[3] == 1
    assert header[4] == 4
    assert header[5] == 3
    assert header[6] == REQUIRED_PROOF_FLAGS
    assert header[7] == 0

    assert report["packet"]["path"] == "solver_frame.sbfr"
    assert manifest["packet"]["sha256"] == report["packet"]["sha256"]
    assert manifest["packet"]["size"] == len(packet)
    assert manifest["verification_scope"] == "synthetic-regression-fixture"
