from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "prove_bmw_body0_bind_pose_writer_direct_role.py"


def _module():
    spec = importlib.util.spec_from_file_location("body0_bind_pose_writer_direct_role", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    m = _module()
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps(
            {
                "program_name": m.PROGRAM,
                "executable_md5": m.PE_MD5,
                "language_id": "x86:LE:32:default",
                "pointer_size": 4,
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(
        root / "functions.jsonl",
        [
            {
                "address": address,
                "name": f"FUN_{address[2:]}",
                "external": False,
                "thunk": False,
                "mnemonic_sha256": digest,
            }
            for address, digest in m.FINGERPRINTS.items()
        ],
    )
    edges = [
        (m.OUTER_UPDATE, m.RELATION_REFRESH, "0x00770fb7"),
        (m.OUTER_UPDATE, m.RELATION_REFRESH, "0x00770fe7"),
        (m.RELATION_REFRESH, m.SYSTEM_LOCATION_RECOVERY, "0x007b8816"),
        (m.SYSTEM_LOCATION_RECOVERY, m.POSE_WRITER_WRAPPER, "0x007b8729"),
        (m.POSE_WRITER_WRAPPER, m.POSE_WRITER, "0x007b82f4"),
        (m.POSE_WRITER, m.POSE_WRITER, "0x007b7d75"),
        (m.SDF_LOADER, m.BODY_BUILDER, "0x007b6e8f"),
        (m.BODY_BUILDER, "0x007bba90", "0x007b3792"),
        (m.BODY_BUILDER, "0x007bbb10", "0x007b37c8"),
        (m.BODY_BUILDER, "0x007bbb60", "0x007b380b"),
    ]
    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": source,
                "from_name": f"FUN_{source[2:]}",
                "instruction": callsite,
                "to": target,
                "to_name": f"FUN_{target[2:]}",
                "indirect": False,
            }
            for source, target, callsite in edges
        ],
    )
    return root


def test_positive_direct_role_rejection(tmp_path: Path) -> None:
    m = _module()
    report = m.prove_bmw_body0_bind_pose_writer_direct_role(_fixture(tmp_path))

    assert report["format"] == m.FORMAT
    assert report["proof"]["all_resolved_direct_nonrecursive_pose_writer_calls_are_outer_update_descendants"] is True
    assert report["proof"]["resolved_direct_construction_call_to_pose_writer_exists"] is False
    assert report["proof"]["FUN_007b7840_direct_construction_bind_initializer_role"] == "rejected"
    assert report["proof"]["FUN_007b7840_any_possible_bind_role"] == "unknown"
    assert report["proof"]["indirect_or_address_taken_invocations_absence_proven"] is False
    assert report["handoff"]["continue_FUN_007b7840_resolved_direct_bind_value_provenance"] is False
    assert report["handoff"]["follow_BODY_construction_writer_now"] is True
    assert report["handoff"]["next_static_targets"] == [
        m.BODY_BUILDER,
        "0x007bba90",
        "0x007bbb10",
        "0x007bbb60",
    ]
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_extra_direct_pose_writer_caller_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root = _fixture(tmp_path)
    with (root / "callgraph.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "from_function": m.BODY_BUILDER,
                    "from_name": "FUN_007b3670",
                    "instruction": "0x007b380f",
                    "to": m.POSE_WRITER,
                    "to_name": "FUN_007b7840",
                    "indirect": False,
                }
            )
            + "\n"
        )

    with pytest.raises(ValueError, match="exact direct incoming set drift"):
        m.prove_bmw_body0_bind_pose_writer_direct_role(root)


def test_missing_outer_update_link_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root = _fixture(tmp_path)
    rows = [
        json.loads(line)
        for line in (root / "callgraph.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [row for row in rows if row["instruction"] != "0x00770fe7"]
    _write_jsonl(root / "callgraph.jsonl", rows)

    with pytest.raises(ValueError, match="exact direct incoming set drift"):
        m.prove_bmw_body0_bind_pose_writer_direct_role(root)


def test_function_fingerprint_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    root = _fixture(tmp_path)
    rows = [json.loads(line) for line in (root / "functions.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        if row["address"] == m.POSE_WRITER:
            row["mnemonic_sha256"] = "0" * 64
    _write_jsonl(root / "functions.jsonl", rows)

    with pytest.raises(ValueError, match="mnemonic fingerprint drift"):
        m.prove_bmw_body0_bind_pose_writer_direct_role(root)


def test_indirect_edges_do_not_get_promoted(tmp_path: Path) -> None:
    m = _module()
    root = _fixture(tmp_path)
    with (root / "callgraph.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "from_function": m.BODY_BUILDER,
                    "from_name": "FUN_007b3670",
                    "instruction": "0x007b3810",
                    "to": m.POSE_WRITER,
                    "to_name": "FUN_007b7840",
                    "indirect": True,
                }
            )
            + "\n"
        )

    report = m.prove_bmw_body0_bind_pose_writer_direct_role(root)
    assert report["proof"]["FUN_007b7840_direct_construction_bind_initializer_role"] == "rejected"
    assert report["proof"]["FUN_007b7840_any_possible_bind_role"] == "unknown"
    assert report["scope"]["pose_writer_any_bind_role_disproven"] is False
