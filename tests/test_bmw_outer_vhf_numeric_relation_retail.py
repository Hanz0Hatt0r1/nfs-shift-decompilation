from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "evaluate_bmw_outer_vhf_numeric_relation.py"
SPEC = importlib.util.spec_from_file_location("bmw_outer_vhf_numeric_retail", TOOL)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_retained_exact_retail_root_frame_reproduces_positive_numeric_relation():
    semantic = _load("evidence/process1_outer_vehicle_bmw_vhf_root_relation.json")
    delta = _load("evidence/bmw_primary_player_first_bootstrap_render_root_delta.json")
    root = _load("evidence/bmw_vhf_hierarchy_root_frame_retail.json")
    expected = _load("evidence/bmw_outer_vhf_numeric_relation.json")

    assert root["source"]["archive"] == "BMW_M3_E36.bff"
    assert root["source"]["archive_sha256"] == "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
    assert root["source"]["entry_index"] == 1083
    assert root["source"]["decoded_sha256"] == "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"

    frame = root["vehicle_root_frame"]
    assert frame["matrix_number"] == "0"
    assert frame["matrix_parent_chain_ids"] == ["0"]
    assert frame["matrix_parent_chain"][0]["parent"] is None
    assert frame["matrix_parent_chain"][0]["offset_xyz"] == [0.0, 0.0, 0.0]
    assert frame["matrix_parent_chain"][0]["orientation_xyzw"] == [0.0, 0.0, 0.0, 1.0]
    assert frame["world_matrix_is_identity"] is True

    report = MODULE.evaluate(semantic, delta, root)
    assert report == expected
    assert report["handoff"]["outer_vehicle_root_to_VHF_relation_numeric_matrix_ready"] is True
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["limits"]["identity_semantics_inferred_from_numeric_identity"] is False
