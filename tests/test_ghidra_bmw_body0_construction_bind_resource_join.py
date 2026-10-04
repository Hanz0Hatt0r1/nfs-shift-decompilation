from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_body0_construction_bind_resource_join.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_construction_bind_resource_join", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path: Path):
    m = _module()
    c = m._continuity
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": c.PROGRAM, "executable_md5": c.PE_MD5}),
        encoding="utf-8",
    )
    _write_jsonl(
        root / "functions.jsonl",
        [
            {
                "address": address,
                "name": expected["name"],
                "thunk": False,
                "external": False,
                "mnemonic_sha256": expected["mnemonic_sha256"],
            }
            for address, expected in c.TARGETS.items()
        ],
    )
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": source,
                "instruction": instruction,
                "to": target,
                "indirect": False,
            }
            for source, instruction, target in c.REQUIRED_DIRECT_EDGES
        ],
    )
    intake = {
        "format": c.INTAKE_FORMAT,
        "version": 1,
        "archive": {
            "filename": m.ARCHIVE_FILENAME,
            "size_bytes": m.ARCHIVE_SIZE,
            "sha256": m.ARCHIVE_SHA256,
        },
        "sdf_entry": {
            "index": m.RESOURCE_ENTRY_INDEX,
            "path": m.RESOURCE_PATH,
            "compression_type": m.RESOURCE_COMPRESSION_TYPE,
            "compressed_size": m.RESOURCE_COMPRESSED_SIZE,
            "uncompressed_size": m.RESOURCE_UNCOMPRESSED_SIZE,
            "decoded_sha256": m.RESOURCE_SHA256,
        },
        "structure": {"body_count": len(c.EXPECTED_BMW_BODIES)},
        "bodies": list(c.EXPECTED_BMW_BODIES),
        "status": "decoded-from-user-supplied-bff",
    }
    intake_path = tmp_path / "intake.json"
    intake_path.write_text(json.dumps(intake), encoding="utf-8")

    evidence = json.loads(m.DEFAULT_RESOURCE_VALUES.read_text(encoding="utf-8"))
    evidence_path = tmp_path / "resource_values.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    return m, root, intake_path, evidence_path


def test_exact_retail_values_promote_local_sdf_bind_only(tmp_path: Path) -> None:
    m, root, intake, evidence = _fixture(tmp_path)
    report = m.build_bmw_body0_construction_bind_resource_join(root, intake, evidence)

    assert report["status"] == "body0-local-to-sdf-model-bind-proven"
    local = report["BODY0_local_to_SDF_model"]
    assert local["origin"] == [0.0, 0.0, 0.0]
    assert local["orientation"] == [0.0, 0.0, 0.0]
    assert local["basis"] == [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    assert local["row_matrix"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    assert local["matrix_is_exact_identity"] is True
    assert report["handoff"]["BODY0_resource_pos_ori_values_ready"] is True
    assert report["handoff"]["BODY0_local_to_SDF_model_bind_pose_ready"] is True
    assert report["handoff"]["SDF_model_to_VHF_vehicle_root_frame_relation_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert [row["id"] for row in report["blockers"]] == [
        "SDF-model-to-VHF-vehicle-root-frame-relation-unproven"
    ]


def test_resource_hash_drift_fails_closed(tmp_path: Path) -> None:
    m, root, intake, evidence = _fixture(tmp_path)
    value = json.loads(evidence.read_text(encoding="utf-8"))
    value["source"]["resource_sha256"] = "0" * 64
    evidence.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="resource source resource_sha256 drift"):
        m.build_bmw_body0_construction_bind_resource_join(root, intake, evidence)


def test_body0_numeric_value_drift_fails_closed(tmp_path: Path) -> None:
    m, root, intake, evidence = _fixture(tmp_path)
    value = json.loads(evidence.read_text(encoding="utf-8"))
    value["body0"]["pos"] = [0.0, 0.25, 0.0]
    evidence.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="BODY0 pos derived value drift"):
        m.build_bmw_body0_construction_bind_resource_join(root, intake, evidence)


def test_intake_and_derived_resource_must_name_same_sdf(tmp_path: Path) -> None:
    m, root, intake, evidence = _fixture(tmp_path)
    value = json.loads(intake.read_text(encoding="utf-8"))
    value["sdf_entry"]["decoded_sha256"] = "f" * 64
    intake.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="intake SDF SHA-256 drift"):
        m.build_bmw_body0_construction_bind_resource_join(root, intake, evidence)


def test_scope_cannot_promote_vhf_or_commit_raw_game_bytes(tmp_path: Path) -> None:
    m, root, intake, evidence = _fixture(tmp_path)
    value = json.loads(evidence.read_text(encoding="utf-8"))
    value["scope"]["raw_resource_committed"] = True
    evidence.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="raw_resource_committed=false"):
        m.build_bmw_body0_construction_bind_resource_join(root, intake, evidence)
