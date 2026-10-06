from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_body0_bind_frame_proof.py"
PACKET_TOOL = ROOT / "src" / "physics" / "bmw_body0_bind_frame_proof_packet.py"
SYMBOLIC = ROOT / "evidence" / "bmw_body0_vehicle_root_bind_relation.json"
SELECTOR = ROOT / "evidence" / "bmw_offset33b_native_silverstone_session.json"
OUTER_VHF = ROOT / "evidence" / "bmw_outer_vhf_numeric_relation.json"
PROOF = ROOT / "evidence" / "bmw_body0_bind_frame_proof.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_module(TOOL, "build_bmw_body0_bind_frame_proof")
PACKET = _load_module(PACKET_TOOL, "bmw_body0_bind_frame_proof_packet")


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_committed_positive_proof_is_exact_deterministic_composition() -> None:
    report = MODULE.build_from_paths(SYMBOLIC, SELECTOR, OUTER_VHF)
    committed = _json(PROOF)
    assert report == committed

    expected = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, -0.004956085581085581, -0.01147086247086247, 1.0,
    ]
    assert report["body0_local_to_vhf_vehicle_root_row_matrix"] == pytest.approx(expected)
    assert report["handoff"]["BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready"] is True
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is True
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["identity_matrix_assumed"] is False
    assert report["scope"]["outer_VHF_semantic_identity_inferred"] is False


def test_row_vector_composition_order_is_locked_by_noncommuting_fixture() -> None:
    body_to_outer = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.0, 0.0, 0.0, 1.0,
    ]
    outer_to_vhf = [
        0.0, 1.0, 0.0, 0.0,
        -1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    composed = MODULE.mul4(body_to_outer, outer_to_vhf)
    reversed_order = MODULE.mul4(outer_to_vhf, body_to_outer)
    assert composed != pytest.approx(reversed_order)
    assert composed[12:15] == pytest.approx([0.0, 1.0, 0.0])
    assert reversed_order[12:15] == pytest.approx([1.0, 0.0, 0.0])


def test_rejects_selected_translation_that_is_not_negative_offset33b() -> None:
    symbolic = _json(SYMBOLIC)
    selector = _json(SELECTOR)
    outer = _json(OUTER_VHF)
    selector["selected_numeric"]["BODY0_to_outer_vehicle_root_translation"][1] = 0.25
    with pytest.raises(ValueError, match="matrix translation disagrees"):
        MODULE.build_proof(symbolic, selector, outer)


def test_rejects_outer_vhf_numeric_gate_regression() -> None:
    symbolic = _json(SYMBOLIC)
    selector = _json(SELECTOR)
    outer = _json(OUTER_VHF)
    outer["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] = False
    with pytest.raises(ValueError, match="numeric matrix gate not ready"):
        MODULE.build_proof(symbolic, selector, outer)


def test_rejects_outer_vhf_matrix_convention_drift() -> None:
    symbolic = _json(SYMBOLIC)
    selector = _json(SELECTOR)
    outer = _json(OUTER_VHF)
    outer["numeric"]["matrix_convention"] = "column-vector"
    with pytest.raises(ValueError, match="matrix convention drift"):
        MODULE.build_proof(symbolic, selector, outer)


def test_existing_positive_only_bbfp_consumer_accepts_committed_proof() -> None:
    proof = _json(PROOF)
    matrix, targets = PACKET.validate_positive_proof(proof)
    assert matrix[12:15] == pytest.approx([0.0, -0.004956085581085581, -0.01147086247086247])
    assert "FUN_007633b0" in targets
    assert "FUN_0076b280" in targets
    packet = PACKET.build_packet(proof)
    assert packet[:4] == b"BBFP"
    assert proof["handoff"]["vehicle_world_transform_ready"] is False
