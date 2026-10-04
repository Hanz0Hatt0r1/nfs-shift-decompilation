from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_body0_construction_bind_continuity.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_construction_bind_continuity", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _sdf_bytes(m, *, body0_pos=(1.0, 2.0, 3.0), body0_ori=(0.0, 0.0, 0.0)) -> bytes:
    rows: list[str] = []
    for index, name in enumerate(m.EXPECTED_BMW_BODIES):
        pos = body0_pos if index == 0 else (0.0, 0.0, 0.0)
        ori = body0_ori if index == 0 else (0.0, 0.0, 0.0)
        rows.extend(
            [
                "[BODY]",
                (
                    f"name={name} mass=(1) inertia=(1,1,1) "
                    f"pos=({pos[0]},{pos[1]},{pos[2]}) "
                    f"ori=({ori[0]},{ori[1]},{ori[2]}) "
                    "vel=(0,0,0) rot=(0,0,0)"
                ),
            ]
        )
    return ("\n".join(rows) + "\n").encode("utf-8")


def _fixture(
    tmp_path: Path,
    *,
    raw_sdf: bytes | None = None,
    fingerprint_drift: bool = False,
    missing_edge: tuple[str, str, str] | None = None,
    wrong_sdf_sha: bool = False,
) -> tuple[Path, Path, Path | None]:
    m = _module()
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": m.PROGRAM, "executable_md5": m.PE_MD5}),
        encoding="utf-8",
    )

    functions = []
    for address, expected in m.TARGETS.items():
        digest = expected["mnemonic_sha256"]
        if fingerprint_drift and address == "0x007b3670":
            digest = "0" * 64
        functions.append(
            {
                "address": address,
                "name": expected["name"],
                "thunk": False,
                "external": False,
                "mnemonic_sha256": digest,
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    callgraph = []
    for source, instruction, target in m.REQUIRED_DIRECT_EDGES:
        if missing_edge == (source, instruction, target):
            continue
        callgraph.append(
            {
                "from_function": source,
                "from_name": m.TARGETS.get(source, {}).get("name"),
                "instruction": instruction,
                "to": target,
                "to_name": m.TARGETS.get(target, {}).get("name"),
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", callgraph)

    digest = "f" * 64
    sdf_path = None
    if raw_sdf is not None:
        sdf_path = tmp_path / "aarm_multilink.sdf"
        sdf_path.write_bytes(raw_sdf)
        digest = hashlib.sha256(raw_sdf).hexdigest()
    if wrong_sdf_sha:
        digest = "0" * 64

    intake = {
        "format": m.INTAKE_FORMAT,
        "version": 1,
        "archive": {
            "filename": "BMW_M3_E36.bff",
            "size_bytes": 18934688,
            "sha256": "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70",
        },
        "sdf_entry": {
            "index": 1091,
            "path": "vehicles/physics/suspension/aarm_multilink.sdf",
            "compression_type": 2,
            "compressed_size": 1110,
            "uncompressed_size": 5056,
            "decoded_sha256": digest,
        },
        "structure": {"body_count": len(m.EXPECTED_BMW_BODIES)},
        "bodies": list(m.EXPECTED_BMW_BODIES),
        "status": "decoded-from-user-supplied-bff",
    }
    intake_path = tmp_path / "intake.json"
    intake_path.write_text(json.dumps(intake), encoding="utf-8")
    return root, intake_path, sdf_path


def test_static_continuity_is_ready_without_preclaiming_bind_matrix(tmp_path: Path) -> None:
    m = _module()
    root, intake, _ = _fixture(tmp_path)
    report = m.build_bmw_body0_construction_bind_continuity(root, intake)

    assert report["status"] == "static-continuity-proven"
    assert report["handoff"]["BODY_descriptor_pos_ori_semantics_ready"] is True
    assert report["handoff"]["construction_origin_continuity_ready"] is True
    assert report["handoff"]["construction_basis_continuity_ready"] is True
    assert report["source_static_proof"]["phase424_group_resolution"] == {
        "group_a": "BODY.ori",
        "group_b": "BODY.rot",
    }
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is False
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is False
    assert report["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["identity_matrix_assumed"] is False


def test_zero_ori_materializes_exact_sdf_model_pose_but_not_vhf_bind(tmp_path: Path) -> None:
    m = _module()
    raw = _sdf_bytes(m, body0_pos=(1.25, -2.0, 3.5), body0_ori=(0.0, 0.0, 0.0))
    root, intake, sdf_path = _fixture(tmp_path, raw_sdf=raw)
    assert sdf_path is not None
    report = m.build_bmw_body0_construction_bind_continuity(root, intake, sdf_path)

    resource = report["resource_BODY0"]
    assert resource["pos"] == [1.25, -2.0, 3.5]
    assert resource["ori"] == [0.0, 0.0, 0.0]
    assert resource["basis"] == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    assert resource["body0_local_to_sdf_model_row_matrix"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        1.25, -2.0, 3.5, 1.0,
    ]
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is True
    assert report["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert [row["id"] for row in report["blockers"]] == [
        "SDF-model-to-VHF-vehicle-root-frame-relation-unproven"
    ]


def test_nonzero_ori_keeps_exact_basis_materialization_blocked(tmp_path: Path) -> None:
    m = _module()
    raw = _sdf_bytes(m, body0_ori=(0.0, 0.125, 0.0))
    root, intake, sdf_path = _fixture(tmp_path, raw_sdf=raw)
    assert sdf_path is not None
    report = m.build_bmw_body0_construction_bind_continuity(root, intake, sdf_path)

    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["resource_BODY0"]["basis_ready"] is False
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is False
    assert any(
        row["id"] == "nonzero-BODY0-ori-retail-basis-evaluation-not-materialized"
        for row in report["blockers"]
    )
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_retail_function_fingerprint_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root, intake, _ = _fixture(tmp_path, fingerprint_drift=True)
    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        m.build_bmw_body0_construction_bind_continuity(root, intake)


def test_missing_direct_edge_fails_closed(tmp_path: Path) -> None:
    m = _module()
    missing = ("0x007bbb10", "0x007bbb3a", "0x007b00a0")
    root, intake, _ = _fixture(tmp_path, missing_edge=missing)
    with pytest.raises(ValueError, match="missing required direct call edge"):
        m.build_bmw_body0_construction_bind_continuity(root, intake)


def test_wrong_decoded_sdf_sha_fails_closed(tmp_path: Path) -> None:
    m = _module()
    raw = _sdf_bytes(m)
    root, intake, sdf_path = _fixture(tmp_path, raw_sdf=raw, wrong_sdf_sha=True)
    assert sdf_path is not None
    with pytest.raises(ValueError, match="decoded BMW SDF SHA-256 mismatch"):
        m.build_bmw_body0_construction_bind_continuity(root, intake, sdf_path)


def test_body0_name_order_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    raw = _sdf_bytes(m)
    root, intake, sdf_path = _fixture(tmp_path, raw_sdf=raw)
    assert sdf_path is not None
    value = json.loads(intake.read_text(encoding="utf-8"))
    value["bodies"][0] = "wrong"
    intake.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="BODY order/name drift"):
        m.build_bmw_body0_construction_bind_continuity(root, intake, sdf_path)
