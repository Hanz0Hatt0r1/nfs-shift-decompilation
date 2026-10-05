from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "classify_outer_vehicle_collision_lod_branch.py"
SPEC = importlib.util.spec_from_file_location("classify_outer_vehicle_collision_lod_branch", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _upstream(path: Path) -> Path:
    return _write_json(
        path,
        {
            "format": m.UPSTREAM_FORMAT,
            "ready": True,
            "chassis_init": {
                "function": m.CHASSIS_INIT,
                "embedded_owner_edges": [
                    {"offset": "+0x534", "callees": ["0x0049f980", "0x007a5a40", m.COLLISION_LOD]}
                ],
            },
            "handoff": {
                "HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain": True,
                "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            },
        },
    )


def _db(tmp_path: Path, *, string_override=None, omit_call=None) -> Path:
    root = tmp_path / "db"
    root.mkdir()
    _write_json(
        root / "binary.json",
        {"format": m.DB_FORMAT, "program_name": m.PROGRAM, "executable_md5": m.PE_MD5},
    )
    functions = []
    for address, fingerprint in m.FUNCTION_FINGERPRINTS.items():
        functions.append(
            {
                "address": address,
                "name": "thunk_FUN_00d5bf10" if address == m.RESOLVER_THUNK else "FUN_" + address[2:],
                "mnemonic_sha256": fingerprint,
                "calling_convention": "__thiscall",
                "thunk": address == m.RESOLVER_THUNK,
            }
        )
    _write_jsonl(root / "functions.jsonl", functions)

    strings = []
    for address, (value, xref) in m.STRING_WITNESSES.items():
        if string_override and address == string_override[0]:
            value = string_override[1]
        strings.append(
            {"address": address, "value": value, "xrefs": [xref], "functions": [m.COLLISION_LOD]}
        )
    _write_jsonl(root / "strings_xrefs.jsonl", strings)

    calls = []
    for edge in m.REQUIRED_CALLS:
        if omit_call == edge:
            continue
        src, ins, dst = edge
        calls.append(
            {
                "from_function": src,
                "instruction": ins,
                "to": dst,
                "indirect": False,
            }
        )
    _write_jsonl(root / "callgraph.jsonl", calls)
    return root


def test_retires_wheel_lod_branch_without_promoting_vhf(tmp_path):
    report = m.analyze(_db(tmp_path), _upstream(tmp_path / "upstream.json"))
    assert report["ready"] is True
    assert report["status"] == "collision-lod-vhf-candidate-retired"
    assert report["evidence"]["collision_format_string_proven"] is True
    assert report["evidence"]["rubber_tyre_material_string_proven"] is True
    assert report["negative_classification"]["branch_removed_from_outer_vehicle_to_VHF_search"] is True
    assert report["negative_classification"]["FUN_007a3d60_is_admissible_VHF_root_candidate"] is False
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["handoff"]["next_frontier"] == "SHIFT.VehicleRenderRootPoseTransportFrontier/1"


def test_rejects_collision_format_string_drift(tmp_path):
    db = _db(tmp_path, string_override=("0x00b0c3cc", "VISUAL_%s"))
    with pytest.raises(ValueError, match="string witness drift"):
        m.analyze(db, _upstream(tmp_path / "upstream.json"))


def test_rejects_missing_collision_helper_edge(tmp_path):
    edge = (m.COLLISION_LOD, "0x007a3ffe", m.COLLISION_ENTRY_HELPER)
    db = _db(tmp_path, omit_call=edge)
    with pytest.raises(ValueError, match="required call edge drift"):
        m.analyze(db, _upstream(tmp_path / "upstream.json"))


def test_rejects_upstream_vhf_preclaim(tmp_path):
    upstream_path = _upstream(tmp_path / "upstream.json")
    upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
    upstream["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] = True
    upstream_path.write_text(json.dumps(upstream) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="preclaims VHF-root identity"):
        m.analyze(_db(tmp_path), upstream_path)


def test_does_not_claim_absence_of_all_outer_vehicle_vhf_paths(tmp_path):
    report = m.analyze(_db(tmp_path), _upstream(tmp_path / "upstream.json"))
    assert report["scope"]["absence_of_any_outer_vehicle_to_VHF_path_claimed"] is False
    assert report["scope"]["direct_and_indirect_render_manager_ca4_branches_reopened"] is False
