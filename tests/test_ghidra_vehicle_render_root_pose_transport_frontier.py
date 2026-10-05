from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_vehicle_render_root_pose_transport_frontier.py"
SPEC = importlib.util.spec_from_file_location("vehicle_render_root_pose_transport_frontier", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _retail_root(
    tmp_path: Path,
    *,
    drop_function: str | None = None,
    fingerprint_drift: str | None = None,
    drop_edge: tuple[str, str, str] | None = None,
) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )

    functions = []
    for address, expected in MODULE.TARGETS.items():
        if address == drop_function:
            continue
        functions.append(
            {
                "address": address,
                "name": expected["name"],
                "namespace": "Global",
                "size": expected["size"],
                "thunk": False,
                "external": False,
                "calling_convention": expected["calling_convention"],
                "signature": "undefined fixture(void)",
                "parameters": [],
                "mnemonic_sha256": "0" * 64 if fingerprint_drift == address else expected["mnemonic_sha256"],
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    calls = []
    for source, instruction, target in MODULE.REQUIRED_EDGES:
        if (source, instruction, target) == drop_edge:
            continue
        calls.append(
            {
                "from_function": source,
                "from_name": MODULE.TARGETS[source]["name"],
                "instruction": instruction,
                "to": target,
                "to_name": MODULE.TARGETS[target]["name"],
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", calls)
    return root


def test_frontier_freezes_parallel_sms_root_pose_transport(tmp_path):
    report = MODULE.build_vehicle_render_root_pose_transport_frontier(_retail_root(tmp_path))
    assert report["format"] == MODULE.FORMAT
    assert report["status"] == "frontier-ready"
    assert report["ready"] is True
    assert report["proven"]["vehicle_slot_snapshot_reader_reaches_extended_snapshot_copy"] is True
    assert report["proven"]["participant_render_tick_reaches_vehicle_hierarchy_node_update_lane"] is True
    assert report["proven"]["vehicle_world_affine_consumer_reaches_vehicle_render_model_world_point_consumer"] is True
    assert report["targeted_instruction_worklist"]["functions"] == list(MODULE.TARGETED_INSTRUCTION_WORKLIST)


def test_decompiler_offsets_are_explicitly_non_gating(tmp_path):
    report = MODULE.build_vehicle_render_root_pose_transport_frontier(_retail_root(tmp_path))
    observed = report["non_gating_decompiler_observations"]
    assert observed["participant_render_snapshot_byte_offset"] == "0xa00"
    assert observed["render_root_position_byte_offsets"] == ["0xa10", "0xa14", "0xa18"]
    assert observed["vehicle_render_model_byte_offset"] == "0x1340"
    assert observed["admissibility"] == "instruction-proof-pending"
    assert observed["used_to_open_readiness_gates"] is False
    assert report["scope"]["decompiler_offsets_promoted_to_proof"] is False


def test_frame_identity_gates_remain_closed(tmp_path):
    report = MODULE.build_vehicle_render_root_pose_transport_frontier(_retail_root(tmp_path))
    handoff = report["handoff"]
    assert handoff["sms_vehicle_root_pose_transport_callgraph_frontier_ready"] is True
    for key in (
        "sms_vehicle_root_pose_offsets_instruction_proof_ready",
        "sms_vehicle_world_affine_instruction_proof_ready",
        "sms_vehicle_world_affine_RenderHierarchy_owner_join_ready",
        "outer_vehicle_root_to_SMS_snapshot_semantic_join_ready",
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "outer_vehicle_root_to_VHF_fixed_affine_delta_ready",
        "BODY0_bind_frame_proof_ready",
        "vehicle_world_transform_ready",
    ):
        assert handoff[key] is False


def test_missing_retail_function_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="missing required retail function"):
        MODULE.build_vehicle_render_root_pose_transport_frontier(
            _retail_root(tmp_path, drop_function="0x00480700")
        )


def test_fingerprint_drift_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="0x004848bc: mnemonic_sha256 drift"):
        MODULE.build_vehicle_render_root_pose_transport_frontier(
            _retail_root(tmp_path, fingerprint_drift="0x004848bc")
        )


def test_required_edge_drift_fails_closed(tmp_path):
    missing = ("0x00480700", "0x0048074f", "0x004a8c20")
    with pytest.raises(ValueError, match="required call edge drift"):
        MODULE.build_vehicle_render_root_pose_transport_frontier(
            _retail_root(tmp_path, drop_edge=missing)
        )
