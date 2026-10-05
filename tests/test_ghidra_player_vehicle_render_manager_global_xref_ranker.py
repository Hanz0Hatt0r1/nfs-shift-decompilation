from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "rank_player_vehicle_render_manager_global_refs.py"
SPEC = importlib.util.spec_from_file_location("rank_player_vehicle_render_manager_global_refs", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _make_db(root: Path, *, missing_function: str | None = None):
    root.mkdir()
    _write_json(
        root / "binary.json",
        {
            "format": m.DB_FORMAT,
            "program_name": m.PROGRAM,
            "executable_md5": m.PE_MD5,
        },
    )

    rows = []
    for name, anchor in m.ANCHORS.items():
        rows.append(
            {
                "address": anchor["address"],
                "name": "FUN_" + anchor["address"][2:],
                "external": False,
                "thunk": False,
                "mnemonic_sha256": anchor["mnemonic_sha256"],
            }
        )
    for address in ("0x00410000", "0x00420000", "0x00430000"):
        if address == missing_function:
            continue
        rows.append(
            {
                "address": address,
                "name": "FUN_" + address[2:],
                "external": False,
                "thunk": False,
                "mnemonic_sha256": "synthetic",
            }
        )
    _write_jsonl(root / "functions.jsonl", rows)

    callgraph = [
        {
            "from_function": "0x00410000",
            "from_name": "FUN_00410000",
            "instruction": "0x00410010",
            "to": m.ANCHORS["car_body_CHASSIS_init"]["address"],
            "to_name": "FUN_007ac4d0",
            "indirect": False,
        },
        {
            "from_function": m.ANCHORS["vehicle_visual_LOD_setup"]["address"],
            "from_name": "FUN_007a3d60",
            "instruction": "0x007a4000",
            "to": "0x00420000",
            "to_name": "FUN_00420000",
            "indirect": False,
        },
        {
            "from_function": "0x00430000",
            "from_name": "FUN_00430000",
            "instruction": "0x00430010",
            "to": m.ANCHORS["render_manager_constructor"]["address"],
            "to_name": "FUN_0045ef50",
            "indirect": False,
        },
        {
            "from_function": "0x00430000",
            "from_name": "FUN_00430000",
            "instruction": "0x00430020",
            "to": m.ANCHORS["HDVehicle_Init"]["address"],
            "to_name": "FUN_0076df50",
            "indirect": True,
        },
    ]
    _write_jsonl(root / "callgraph.jsonl", callgraph)
    return root


def _global_row(md5: str | None = None):
    refs = [
        {
            "from": "0x00410020",
            "type": "DATA",
            "operand_index": 1,
            "primary": True,
            "function_address": "0x00410000",
            "function_name": "FUN_00410000",
            "instruction": "MOV EAX,dword ptr [0xbc185c]",
        },
        {
            "from": "0x00420020",
            "type": "DATA",
            "operand_index": 1,
            "primary": True,
            "function_address": "0x00420000",
            "function_name": "FUN_00420000",
            "instruction": "MOV ECX,dword ptr [0xbc185c]",
        },
        {
            "from": "0x00430020",
            "type": "DATA",
            "operand_index": 1,
            "primary": True,
            "function_address": "0x00430000",
            "function_name": "FUN_00430000",
            "instruction": "MOV EDX,dword ptr [0xbc185c]",
        },
    ]
    return {
        "format": m.GLOBAL_FORMAT,
        "program": m.PROGRAM,
        "executable_md5": md5 or m.PE_MD5,
        "requested": "DAT_00bc185c",
        "resolved_address": m.DEFAULT_GLOBAL,
        "found": True,
        "primary_symbol": "DAT_00bc185c",
        "data_type": "undefined4",
        "data_length": 4,
        "reference_count": len(refs),
        "function_addresses": ["0x00410000", "0x00420000", "0x00430000"],
        "references": refs,
    }


def _make_global(path: Path, md5: str | None = None):
    return _write_jsonl(path, [_global_row(md5)])


def test_ranks_exact_global_xref_functions_by_bounded_vehicle_anchor_distance(tmp_path):
    db = _make_db(tmp_path / "db")
    refs = _make_global(tmp_path / "refs.jsonl")
    report = m.rank(db, refs, limit=3, max_depth=4)

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["candidate_global"]["address"] == m.DEFAULT_GLOBAL
    assert report["candidate_global"]["runtime_manager_instance_identity_proven"] is False

    ranked = report["ranking"]["functions"]
    assert [row["function"] for row in ranked] == [
        "0x00410000",
        "0x00420000",
        "0x00430000",
    ]
    assert ranked[0]["minimum_vehicle_anchor_distance"] == 1
    assert ranked[0]["nearest_vehicle_anchor"] == "car_body_CHASSIS_init"
    assert ranked[0]["nearest_vehicle_anchor_direction"] == "forward"
    assert ranked[1]["minimum_vehicle_anchor_distance"] == 1
    assert ranked[1]["nearest_vehicle_anchor"] == "vehicle_visual_LOD_setup"
    assert ranked[1]["nearest_vehicle_anchor_direction"] == "reverse"
    assert ranked[2]["minimum_vehicle_anchor_distance"] is None
    assert ranked[2]["minimum_render_manager_constructor_distance"] == 1

    # The synthetic indirect edge from 0x00430000 to HDVehicle_Init must not
    # influence ranking.
    assert ranked[2]["anchor_distances"]["HDVehicle_Init"]["forward"] is None
    assert report["scope"]["indirect_call_edges_used_for_ranking"] is False
    assert report["handoff"]["bounded_instruction_export_worklist_ready"] is True
    assert report["handoff"]["player_vehicle_renderables_owner_join_ready"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False


def test_limit_produces_finite_instruction_export_worklist(tmp_path):
    db = _make_db(tmp_path / "db")
    refs = _make_global(tmp_path / "refs.jsonl")
    report = m.rank(db, refs, limit=2, max_depth=4)
    assert report["ranking"]["selected_instruction_export_functions"] == [
        "0x00410000",
        "0x00420000",
    ]
    assert report["ranking"]["selected_instruction_export_limit"] == 2


def test_rejects_global_export_from_wrong_executable(tmp_path):
    db = _make_db(tmp_path / "db")
    refs = _make_global(tmp_path / "refs.jsonl", "0" * 32)
    with pytest.raises(ValueError, match="executable MD5 drift"):
        m.rank(db, refs)


def test_rejects_reference_function_missing_from_saved_database(tmp_path):
    db = _make_db(tmp_path / "db", missing_function="0x00420000")
    refs = _make_global(tmp_path / "refs.jsonl")
    with pytest.raises(ValueError, match="missing from functions.jsonl"):
        m.rank(db, refs)


def test_rejects_anchor_fingerprint_drift(tmp_path):
    db = _make_db(tmp_path / "db")
    rows = [json.loads(line) for line in (db / "functions.jsonl").read_text().splitlines()]
    for row in rows:
        if row["address"] == m.ANCHORS["vehicle_visual_LOD_setup"]["address"]:
            row["mnemonic_sha256"] = "drift"
    _write_jsonl(db / "functions.jsonl", rows)
    refs = _make_global(tmp_path / "refs.jsonl")
    with pytest.raises(ValueError, match="anchor mnemonic drift"):
        m.rank(db, refs)
