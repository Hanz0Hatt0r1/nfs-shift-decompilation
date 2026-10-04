from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_body0_construction_target_identity.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_construction_target_identity", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path: Path, *, values_ready: bool = True):
    m = _module()
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_json(
        ghidra / "binary.json",
        {"program_name": m.PROGRAM, "executable_md5": m.PE_MD5},
    )
    _write_jsonl(
        ghidra / "functions.jsonl",
        [
            {
                "address": address,
                "name": f"FUN_{address[2:]}",
                "external": False,
                "thunk": False,
                "mnemonic_sha256": digest,
            }
            for address, digest in m.TARGETS.items()
        ],
    )
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            {
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "indirect": False,
            }
            for source, instruction, target in m.REQUIRED_EDGES
        ],
    )

    intake = tmp_path / "intake.json"
    _write_json(
        intake,
        {
            "format": m.INTAKE_FORMAT,
            "archive": {
                "filename": "BMW_M3_E36.bff",
                "sha256": "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70",
            },
            "sdf_entry": {"path": "vehicles/physics/suspension/aarm_multilink.sdf"},
            "structure": {"body_count": len(m.EXPECTED_BMW_BODIES)},
            "bodies": list(m.EXPECTED_BMW_BODIES),
        },
    )

    pose = tmp_path / "pose.json"
    _write_json(
        pose,
        {
            "format": m.POSE_FORMAT,
            "source": {"program": m.PROGRAM, "executable_md5": m.PE_MD5},
            "analysis": {
                "structural_blockers": [],
                "object_base_pose_store_candidates": [
                    {
                        "function": m.BODY_BUILDER,
                        "instruction": "0x007b3797",
                        "pose_fields_touched": ["origin+0x0"],
                        "persistent_BODY_target_identity_proven": False,
                        "BODY0_identity_proven": False,
                    }
                ],
            },
            "handoff": {
                "construction_pose_store_discovery_complete": True,
                "construction_pose_store_candidate_found": True,
                "BODY0_pointer_at_construction_pose_write_ready": False,
                "BODY0_bind_frame_proof_ready": False,
            },
        },
    )

    continuity = tmp_path / "continuity.json"
    _write_json(
        continuity,
        {
            "format": m.CONTINUITY_FORMAT,
            "ready": True,
            "retail_identity": {"program_name": m.PROGRAM, "executable_md5": m.PE_MD5},
            "handoff": {
                "BODY_descriptor_pos_ori_semantics_ready": True,
                "construction_origin_continuity_ready": True,
                "construction_basis_continuity_ready": True,
                "BODY0_local_to_SDF_model_bind_pose_ready": values_ready,
                "BODY0_bind_frame_proof_ready": False,
            },
        },
    )
    return m, ghidra, intake, pose, continuity


def test_proves_first_persistent_body_is_bmw_body0(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    report = m.build_bmw_body0_construction_target_identity(
        ghidra, intake, pose, continuity
    )

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["target_identity"]["persistent_BODY_record_stride"] == 0x170
    assert report["target_identity"]["first_BODY_ordinal"] == 0
    assert report["target_identity"]["first_BODY_name"] == "body"
    assert report["target_identity"]["origin_writer_target_is_BODY0"] is True
    assert report["target_identity"]["basis_writer_target_is_BODY0"] is True
    assert report["handoff"]["persistent_BODY_target_identity_proven"] is True
    assert report["handoff"]["BODY0_pointer_at_construction_pose_write_ready"] is True
    assert report["handoff"]["BODY0_bind_origin_basis_values_ready"] is True
    assert report["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False


def test_keeps_numeric_bind_values_false_when_continuity_has_no_resource_values(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path, values_ready=False)
    report = m.build_bmw_body0_construction_target_identity(
        ghidra, intake, pose, continuity
    )
    assert report["handoff"]["BODY0_pointer_at_construction_pose_write_ready"] is True
    assert report["handoff"]["BODY0_bind_origin_basis_values_ready"] is False
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_rejects_function_fingerprint_drift(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    rows = [json.loads(line) for line in (ghidra / "functions.jsonl").read_text().splitlines()]
    rows[0]["mnemonic_sha256"] = "0" * 64
    _write_jsonl(ghidra / "functions.jsonl", rows)
    with pytest.raises(ValueError, match="fingerprint drift"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)


def test_rejects_bmw_body_order_drift(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    payload = json.loads(intake.read_text())
    payload["bodies"][0], payload["bodies"][1] = payload["bodies"][1], payload["bodies"][0]
    _write_json(intake, payload)
    with pytest.raises(ValueError, match="BODY order/name drift"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)


def test_rejects_incomplete_pose_store_discovery(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    payload = json.loads(pose.read_text())
    payload["handoff"]["construction_pose_store_discovery_complete"] = False
    _write_json(pose, payload)
    with pytest.raises(ValueError, match="discovery is incomplete"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)


def test_rejects_non_builder_origin_candidate(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    payload = json.loads(pose.read_text())
    candidate = payload["analysis"]["object_base_pose_store_candidates"][0]
    candidate["function"] = m.ORI_HELPER
    _write_json(pose, payload)
    with pytest.raises(ValueError, match="BODY builder origin pose-store candidate is missing"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)


def test_rejects_builder_candidate_without_origin_store(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    payload = json.loads(pose.read_text())
    payload["analysis"]["object_base_pose_store_candidates"][0]["pose_fields_touched"] = ["basis+0xd4"]
    _write_json(pose, payload)
    with pytest.raises(ValueError, match="BODY builder origin pose-store candidate is missing"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)


def test_rejects_upstream_final_bind_preclaim(tmp_path: Path):
    m, ghidra, intake, pose, continuity = _fixture(tmp_path)
    payload = json.loads(continuity.read_text())
    payload["handoff"]["BODY0_bind_frame_proof_ready"] = True
    _write_json(continuity, payload)
    with pytest.raises(ValueError, match="must not preclaim"):
        m.build_bmw_body0_construction_target_identity(ghidra, intake, pose, continuity)
