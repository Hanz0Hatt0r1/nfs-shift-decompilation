import json
import struct

import pytest

from native_post_solve_body_projection import (
    FORMAT,
    INPUT_FORMAT,
    PACKET_MAGIC,
    PACKET_VERSION,
    REQUIRED_PROOF_FLAGS,
    build_native_post_solve_body_projection,
    build_native_post_solve_body_projection_file,
)


def _source():
    return {
        "format": INPUT_FORMAT,
        "version": 1,
        "verification_scope": "synthetic-post-solve-regression",
        "solved_vector_ready": True,
        "body_state_ready": True,
        "constraint_rows_ready": True,
        "bodies": [
            {"angular": [0, 0, 0], "linear": [0, 0, 0]},
            {"angular": [1, 2, 3], "linear": [4, 5, 6]},
            {"angular": [0, 0, 0], "linear": [0, 0, 0]},
        ],
        "solver_vector": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        "joints": [{
            "positive_body": 0,
            "negative_body": 1,
            "scalar_base": 0,
            "positive_lever_arm": [1, 0, 0],
            "negative_lever_arm": [0, 1, 0],
        }],
        "hinges": [{
            "positive_body": 1,
            "negative_body": 2,
            "scalar_base": 3,
            "positive_angular_row": [1, 0, 0],
            "positive_linear_row": [0, 1, 0],
            "negative_angular_row": [0, 0, 1],
            "negative_linear_row": [1, 0, 0],
        }],
        "bars": [{
            "positive_body": 2,
            "negative_body": 0,
            "scalar_base": 5,
            "positive_lever_arm": [0, 0, 1],
            "negative_lever_arm": [1, 0, 0],
            "direction": [1, 2, 0],
        }],
    }


def test_prepared_post_solve_projection_matches_python_source_oracle():
    report = build_native_post_solve_body_projection(_source())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["source_function"] == "FUN_007b4110"
    assert report["body_count"] == 3
    assert report["scalar_count"] == 6
    assert report["constraint_counts"] == {
        "JOINT": 1,
        "HINGE": 1,
        "BAR": 1,
    }
    assert report["proofs"] == {
        "solved_vector_ready": True,
        "body_state_ready": True,
        "constraint_rows_ready": True,
    }
    assert report["boundary"]["derives_solved_vector"] is False
    assert report["boundary"]["fixed_step_runtime_integration"] is False

    bodies = report["oracle"]["bodies"]
    assert bodies[0]["linear"] == pytest.approx([-5.0, -10.0, 4.0])
    assert bodies[0]["angular"] == pytest.approx([0.0, 0.0, -7.0])
    assert bodies[1]["linear"] == pytest.approx([2.0, 2.0, 2.0])
    assert bodies[1]["angular"] == pytest.approx([6.0, 8.0, 1.0])
    assert bodies[2]["linear"] == pytest.approx([7.0, 14.0, 0.0])
    assert bodies[2]["angular"] == pytest.approx([-14.0, 7.0, -5.0])


@pytest.mark.parametrize(
    "proof",
    ["solved_vector_ready", "body_state_ready", "constraint_rows_ready"],
)
def test_missing_projection_proof_fails_closed(proof):
    source = _source()
    source[proof] = False
    with pytest.raises(ValueError, match=proof):
        build_native_post_solve_body_projection(source)


def test_projection_rejects_out_of_range_scalar_slice():
    source = _source()
    source["bars"][0]["scalar_base"] = len(source["solver_vector"])
    with pytest.raises(ValueError, match="scalar range"):
        build_native_post_solve_body_projection(source)


def test_projection_file_writes_binary_packet_and_manifest(tmp_path):
    source = tmp_path / "post.json"
    source.write_text(json.dumps(_source()), encoding="utf-8")

    report = build_native_post_solve_body_projection_file(
        source, tmp_path / "prepared"
    )
    packet = (tmp_path / "prepared/post_solve.sbps").read_bytes()
    manifest = json.loads(
        (tmp_path / "prepared/post_solve_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    header = struct.unpack_from("<4s8I", packet, 0)
    assert header[0] == PACKET_MAGIC
    assert header[1] == PACKET_VERSION
    assert header[2] == 3
    assert header[3] == 6
    assert header[4:7] == (1, 1, 1)
    assert header[7] == REQUIRED_PROOF_FLAGS
    assert header[8] == 0
    assert report["packet"]["path"] == "post_solve.sbps"
    assert manifest["packet"]["sha256"] == report["packet"]["sha256"]
