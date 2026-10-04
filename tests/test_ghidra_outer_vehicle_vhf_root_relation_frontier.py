from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_outer_vehicle_vhf_root_relation_frontier.py"
SPEC = importlib.util.spec_from_file_location("outer_vehicle_vhf_root_frontier", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _relation(tmp_path: Path, *, vhf_ready: bool = False) -> Path:
    path = tmp_path / "symbolic.json"
    outer = MODULE.TARGETS[MODULE.OUTER_SETTER]
    path.write_text(
        json.dumps(
            {
                "format": MODULE.SYMBOLIC_FORMAT,
                "status": "symbolic-ready",
                "ready": True,
                "retail": {
                    "functions": [
                        {
                            "address": MODULE.OUTER_SETTER,
                            "name": outer["name"],
                            "mnemonic_sha256": outer["mnemonic_sha256"],
                        }
                    ]
                },
                "gates": {
                    "retail_vehicle_transform_to_HDVehicle_spawn_bridge_ready": True,
                    "BODY0_to_outer_vehicle_root_symbolic_matrix_ready": True,
                    "outer_vehicle_root_to_VHF_vehicle_root_ready": vhf_ready,
                    "BODY0_bind_frame_proof_ready": False,
                },
                "scope": {
                    "outer_vehicle_root_equated_to_VHF_root": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _retail_root(
    tmp_path: Path,
    *,
    drop_restart_call: str | None = None,
    extra_outer_call: bool = False,
    drop_label: str | None = None,
    fingerprint_drift: str | None = None,
) -> Path:
    root = tmp_path / "ghidra"
    root.mkdir()
    (root / "binary.json").write_text(
        json.dumps({"program_name": MODULE.PROGRAM, "executable_md5": MODULE.PE_MD5}),
        encoding="utf-8",
    )

    functions = []
    for address, expected in MODULE.TARGETS.items():
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
                "mnemonic_sha256": (
                    "0" * 64 if fingerprint_drift == address else expected["mnemonic_sha256"]
                ),
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    calls = []
    for callsite in MODULE.RESTART_TO_OUTER_CALLS:
        if callsite == drop_restart_call:
            continue
        calls.append(
            {
                "from_function": MODULE.RESTART,
                "from_name": MODULE.TARGETS[MODULE.RESTART]["name"],
                "instruction": callsite,
                "to": MODULE.OUTER_SETTER,
                "to_name": MODULE.TARGETS[MODULE.OUTER_SETTER]["name"],
                "indirect": False,
            }
        )
    for instruction, callee in MODULE.OUTER_SETTER_CALLS:
        calls.append(
            {
                "from_function": MODULE.OUTER_SETTER,
                "from_name": MODULE.TARGETS[MODULE.OUTER_SETTER]["name"],
                "instruction": instruction,
                "to": callee,
                "to_name": MODULE.TARGETS[callee]["name"],
                "indirect": False,
            }
        )
    if extra_outer_call:
        calls.append(
            {
                "from_function": MODULE.OUTER_SETTER,
                "from_name": MODULE.TARGETS[MODULE.OUTER_SETTER]["name"],
                "instruction": "0x007928fa",
                "to": "0x00700000",
                "to_name": "FUN_00700000",
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", calls)

    strings = []
    for expected in MODULE.RESTART_LABELS:
        if expected["address"] == drop_label:
            continue
        strings.append(
            {
                "address": expected["address"],
                "value": expected["value"],
                "length": len(expected["value"]) + 1,
                "xrefs": [expected["xref"]],
                "functions": [MODULE.RESTART],
            }
        )
    _write_jsonl(root / "strings_xrefs.jsonl", strings)
    return root


def test_frontier_freezes_restart_spawn_and_outer_setter_fanout(tmp_path):
    report = MODULE.build_outer_vehicle_vhf_root_relation_frontier(
        _retail_root(tmp_path),
        _relation(tmp_path),
    )

    assert report["format"] == MODULE.FORMAT
    assert report["ready"] is True
    assert report["status"] == "frontier-ready"
    assert report["proven"]["spawn_path_reaches_outer_vehicle_transform_setter"] is True
    assert report["proven"]["all_restart_to_outer_setter_direct_calls_frozen"] is True
    assert report["proven"]["outer_vehicle_setter_direct_fanout_frozen"] is True
    assert len(report["retail"]["restart_to_outer_vehicle_setter_calls"]) == 4
    assert len(report["retail"]["outer_vehicle_setter_direct_calls"]) == 7
    assert len(report["candidate_transform_state_sinks"]) == 4
    assert report["targeted_instruction_worklist"]["functions"] == list(
        MODULE.TARGETED_INSTRUCTION_WORKLIST
    )
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_fixed_affine_delta_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["callgraph_adjacency_used_as_frame_identity"] is False
    assert report["scope"]["outer_vehicle_root_equated_to_VHF_root"] is False


def test_restart_source_labels_are_exact_retail_anchors(tmp_path):
    report = MODULE.build_outer_vehicle_vhf_root_relation_frontier(
        _retail_root(tmp_path), _relation(tmp_path)
    )
    labels = report["retail"]["restart_source_labels"]
    assert [row["value"] for row in labels] == [row["value"] for row in MODULE.RESTART_LABELS]
    assert labels[1]["value"] == "MWL::Core::PhysicsParticipant::Restart"


def test_missing_restart_branch_call_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="Restart -> outer setter callsite drift"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path, drop_restart_call="0x0074df62"),
            _relation(tmp_path),
        )


def test_extra_outer_setter_direct_call_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="outer Vehicle setter direct-call fan-out drift"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path, extra_outer_call=True),
            _relation(tmp_path),
        )


def test_missing_restart_source_label_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="missing Restart source label"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path, drop_label="0x00b086cc"),
            _relation(tmp_path),
        )


def test_retail_callee_fingerprint_drift_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="0x007876e0: mnemonic_sha256 drift"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path, fingerprint_drift="0x007876e0"),
            _relation(tmp_path),
        )


def test_symbolic_relation_must_not_preclaim_vhf_root_identity(tmp_path):
    with pytest.raises(ValueError, match="unexpectedly preclaims outer Vehicle -> VHF root"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path),
            _relation(tmp_path, vhf_ready=True),
        )


def test_symbolic_relation_outer_setter_fingerprint_drift_fails_closed(tmp_path):
    relation = json.loads(_relation(tmp_path).read_text(encoding="utf-8"))
    relation["retail"]["functions"][0]["mnemonic_sha256"] = "0" * 64
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(relation), encoding="utf-8")
    with pytest.raises(ValueError, match="outer Vehicle setter anchor drift"):
        MODULE.build_outer_vehicle_vhf_root_relation_frontier(
            _retail_root(tmp_path), path
        )
