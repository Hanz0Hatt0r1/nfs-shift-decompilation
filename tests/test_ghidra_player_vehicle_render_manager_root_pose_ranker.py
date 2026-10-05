from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "rank_player_vehicle_render_manager_root_pose_refs.py"
SPEC = importlib.util.spec_from_file_location("rank_player_vehicle_render_manager_root_pose_refs", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _make_db(root: Path, *, collision_hash: str | None = None) -> Path:
    root.mkdir()
    _write_json(
        root / "binary.json",
        {
            "format": m._base.DB_FORMAT,
            "program_name": m.PROGRAM,
            "executable_md5": m.PE_MD5,
        },
    )
    functions = []
    for name, anchor in m.POSITIVE_ANCHORS.items():
        functions.append(
            {
                "address": anchor["address"],
                "name": "FUN_" + anchor["address"][2:],
                "external": False,
                "thunk": False,
                "mnemonic_sha256": anchor["mnemonic_sha256"],
            }
        )
    functions.append(
        {
            "address": m.COLLISION_WHEEL_ANCHOR["address"],
            "name": "FUN_007a3d60",
            "external": False,
            "thunk": False,
            "mnemonic_sha256": collision_hash or m.COLLISION_WHEEL_ANCHOR["mnemonic_sha256"],
        }
    )
    for address in ("0x00410000", "0x00420000", "0x00430000"):
        functions.append(
            {
                "address": address,
                "name": "FUN_" + address[2:],
                "external": False,
                "thunk": False,
                "mnemonic_sha256": "synthetic",
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    _write_jsonl(
        root / "callgraph.jsonl",
        [
            {
                "from_function": "0x00410000",
                "from_name": "FUN_00410000",
                "instruction": "0x00410010",
                "to": m.COLLISION_WHEEL_ANCHOR["address"],
                "to_name": "FUN_007a3d60",
                "indirect": False,
            },
            {
                "from_function": "0x00420000",
                "from_name": "FUN_00420000",
                "instruction": "0x00420010",
                "to": m.POSITIVE_ANCHORS["sms_vehicle_world_affine_consumer"]["address"],
                "to_name": "FUN_00480700",
                "indirect": False,
            },
            {
                "from_function": "0x00430000",
                "from_name": "FUN_00430000",
                "instruction": "0x00430010",
                "to": m.POSITIVE_ANCHORS["render_manager_constructor"]["address"],
                "to_name": "FUN_0045ef50",
                "indirect": False,
            },
        ],
    )
    return root


def _make_global(path: Path) -> Path:
    refs = []
    for index, function in enumerate(("0x00410000", "0x00420000", "0x00430000")):
        refs.append(
            {
                "from": f"0x{int(function, 16) + 0x20:08x}",
                "type": "DATA",
                "operand_index": 1,
                "primary": True,
                "function_address": function,
                "function_name": "FUN_" + function[2:],
                "instruction": "MOV EAX,dword ptr [0xbc185c]",
            }
        )
    row = {
        "format": m._base.GLOBAL_FORMAT,
        "program": m.PROGRAM,
        "executable_md5": m.PE_MD5,
        "requested": "DAT_00bc185c",
        "resolved_address": m.DEFAULT_GLOBAL,
        "found": True,
        "primary_symbol": "DAT_00bc185c",
        "data_type": "undefined4",
        "data_length": 4,
        "reference_count": len(refs),
        "function_addresses": [row["function_address"] for row in refs],
        "references": refs,
    }
    return _write_jsonl(path, [row])


def test_collision_lane_no_longer_scores_as_positive_render_anchor(tmp_path):
    report = m.rank(_make_db(tmp_path / "db"), _make_global(tmp_path / "refs.jsonl"), limit=3, max_depth=4)
    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["handoff"]["root_pose_positive_anchor_ranking_ready"] is True
    assert report["handoff"]["collision_wheel_LOD_anchor_removed_from_positive_render_score"] is True

    by_function = {row["function"]: row for row in report["ranking"]["functions"]}
    collision_near = by_function["0x00410000"]
    assert collision_near["collision_wheel_anchor_distance"] == 1
    assert collision_near["minimum_vehicle_anchor_distance"] is None
    assert collision_near["collision_proximity_used_as_positive_render_signal"] is False

    root_pose_near = by_function["0x00420000"]
    assert root_pose_near["minimum_vehicle_anchor_distance"] == 1
    assert root_pose_near["nearest_vehicle_anchor"] == "sms_vehicle_world_affine_consumer"
    assert report["ranking"]["selected_instruction_export_functions"][0] == "0x00420000"


def test_negative_control_is_fingerprint_gated(tmp_path):
    with pytest.raises(ValueError, match="collision negative-control mnemonic drift"):
        m.rank(
            _make_db(tmp_path / "db", collision_hash="0" * 64),
            _make_global(tmp_path / "refs.jsonl"),
            limit=3,
            max_depth=4,
        )


def test_frame_and_owner_gates_remain_closed(tmp_path):
    report = m.rank(_make_db(tmp_path / "db"), _make_global(tmp_path / "refs.jsonl"), limit=3, max_depth=4)
    assert report["negative_control_anchor"]["used_for_ranking_score"] is False
    assert report["handoff"]["collision_wheel_LOD_negative_classification_instruction_proof_ready"] is False
    assert report["handoff"]["render_manager_owner_to_SMS_root_pose_owner_join_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["vehicle_world_transform_ready"] is False
    assert report["scope"]["wheel_collision_LOD_proximity_promoted_to_render_identity"] is False


def test_wrapper_restores_base_ranker_globals(tmp_path):
    original_anchors = m._base.ANCHORS
    original_names = m._base.VEHICLE_ANCHOR_NAMES
    m.rank(_make_db(tmp_path / "db"), _make_global(tmp_path / "refs.jsonl"), limit=3, max_depth=4)
    assert m._base.ANCHORS is original_anchors
    assert m._base.VEHICLE_ANCHOR_NAMES is original_names
