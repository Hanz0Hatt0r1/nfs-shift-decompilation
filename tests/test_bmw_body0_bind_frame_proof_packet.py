from __future__ import annotations

import importlib.util
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src/physics/bmw_body0_bind_frame_proof_packet.py"


def _module():
    spec = importlib.util.spec_from_file_location("bmw_body0_bind_frame_proof_packet", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof() -> dict[str, object]:
    return {
        "format": "SHIFT.BMWBody0BindFrameProof/1",
        "ready": True,
        "status": "ready",
        "evidence_state": "proven-static",
        "body_index": 0,
        "body_name": "body",
        "frame_relation": "BODY0-local-to-VHF-vehicle-root",
        "matrix_convention": "row-major D3D row-vector affine",
        "provenance": {
            "source_targets": [
                "FUN_007b3670",
                "FUN_007bba90",
                "FUN_007bbb10",
                "FUN_007bbb60",
            ]
        },
        "scope": {
            "identity_matrix_assumed": False,
            "original_game_executed": False,
            "new_runtime_capture_used": False,
        },
        "body0_local_to_vhf_vehicle_root_row_matrix": [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            1.25, -0.5, 2.0, 1.0,
        ],
    }


def test_positive_proof_builds_deterministic_packet(tmp_path: Path) -> None:
    module = _module()
    proof = _proof()
    packet = module.build_packet(proof)
    assert packet == module.build_packet(proof)

    magic, version, body_index, target_count, target_bytes, *matrix = module.HEADER.unpack_from(packet)
    assert magic == b"BBFP"
    assert version == 1
    assert body_index == 0
    assert target_count == 4
    assert target_bytes == len(packet) - module.HEADER.size
    assert matrix[12:15] == pytest.approx([1.25, -0.5, 2.0])

    input_path = tmp_path / "proof.json"
    output_path = tmp_path / "proof.bbfp"
    input_path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
    report = module.build_from_path(input_path, output_path)
    assert report["format"] == "SHIFT.NativeBMWBody0BindFrameProofPacketBuild/1"
    assert report["ready"] is True
    assert report["source_contract"] == "SHIFT.BMWBody0BindFrameProof/1"
    assert report["packet_format"] == "SHIFT.NativeBMWBody0BindFrameProofPacket/1"
    assert report["source_target_count"] == 4
    assert report["retail_world_transform_admitted"] is False
    assert output_path.read_bytes() == packet


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda p: p.__setitem__("format", "SHIFT.BMWBody0BindFrameProof/0"), "expected SHIFT.BMWBody0BindFrameProof/1"),
        (lambda p: p.__setitem__("ready", False), "not ready"),
        (lambda p: p.__setitem__("status", "blocked"), "status is not ready"),
        (lambda p: p.__setitem__("evidence_state", "inferred"), "not proven-static"),
        (lambda p: p.__setitem__("body_index", 1), "index drift"),
        (lambda p: p.__setitem__("body_name", "wheel"), "name drift"),
        (lambda p: p.__setitem__("frame_relation", "BODY0-local-to-MEB-object"), "frame relation drift"),
        (lambda p: p.__setitem__("matrix_convention", "column-major"), "matrix convention drift"),
        (lambda p: p["provenance"].__setitem__("source_targets", []), "source target count"),
        (lambda p: p["scope"].__setitem__("identity_matrix_assumed", True), "identity BODY0 bind assumption"),
        (lambda p: p["scope"].__setitem__("original_game_executed", True), "original-game execution"),
        (lambda p: p["scope"].__setitem__("new_runtime_capture_used", True), "runtime capture"),
        (lambda p: p["body0_local_to_vhf_vehicle_root_row_matrix"].__setitem__(3, 1.0), "not D3D row-vector affine"),
        (lambda p: p["body0_local_to_vhf_vehicle_root_row_matrix"].__setitem__(0, 0.0), "linear block is singular"),
    ],
)
def test_packet_builder_rejects_non_positive_or_malformed_proof(mutator, message: str) -> None:
    module = _module()
    proof = _proof()
    mutator(proof)
    with pytest.raises(ValueError, match=message):
        module.build_packet(proof)


def test_packet_preserves_source_target_table() -> None:
    module = _module()
    proof = _proof()
    packet = module.build_packet(proof)
    _, _, _, count, blob_size, *_ = module.HEADER.unpack_from(packet)
    blob = memoryview(packet)[module.HEADER.size :]
    assert len(blob) == blob_size
    cursor = 0
    targets: list[str] = []
    for _ in range(count):
        length = struct.unpack_from("<I", blob, cursor)[0]
        cursor += 4
        targets.append(bytes(blob[cursor : cursor + length]).decode("utf-8"))
        cursor += length
    assert cursor == len(blob)
    assert targets == proof["provenance"]["source_targets"]
