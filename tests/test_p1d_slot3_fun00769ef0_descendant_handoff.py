import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_fun00769ef0_descendant_handoff.py"
BODY = ROOT / "evidence" / "fun_007682c0_body0_delta_destination.json"
CACHE = ROOT / "evidence" / "fun_007675f0_surface_probe_node_cache.json"
DISTANCE = ROOT / "evidence" / "fun_007675f0_distance_state_ownership.json"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_fun00769ef0_descendant_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_769ef0_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_pinned_handoff():
    module = load_module()
    assert module.build(BODY, CACHE, DISTANCE) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_receiver_chain_drift_fails_closed(tmp_path):
    module = load_module()
    payload = json.loads(BODY.read_text(encoding="utf-8"))
    row = next(row for row in payload["receiver_chain"] if row["function"] == "FUN_00769ef0")
    row["fact"] = "unknown receiver"
    bad = tmp_path / "bad-body.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        module.build(bad, CACHE, DISTANCE)


def test_selected_slot3_remains_disjoint_from_known_descendants():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    destinations = payload["proven_descendant_destinations"]
    assert destinations["FUN_007675f0_hdvehicle_state_offsets"] == [
        "+0x120", "+0x128", "+0x130", "+0x138", "+0x4080"
    ]
    assert destinations["FUN_007675f0_selected_slot3_overlap"] is False
    assert destinations["FUN_007682c0_destination_owner"] == "retail BMW chassis BODY0"
    assert destinations["FUN_007682c0_body_record_write_offset"] == "+0x50"
    assert destinations["FUN_007682c0_writes_selected_hdvehicle_slot3"] is False


def test_global_slot3_gates_stay_fail_closed():
    adjudication = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert adjudication["slot3_fun00769ef0_known_descendant_tranche_complete"] is True
    assert adjudication["slot3_fun00769ef0_known_descendant_writer_found"] is False
    assert adjudication["fun00769ef0_complete_write_surface_proven"] is False
    assert adjudication["fun00758810_exact_root_branch_complete"] is False
    assert adjudication["deeper_direct_aliases_ruled_out"] is False
    assert adjudication["stored_or_escaped_aliases_ruled_out"] is False
    assert adjudication["indirect_callback_aliases_ruled_out"] is False
    assert adjudication["slot3_writer_provenance_proven"] is False
    assert adjudication["p1_3d_complete"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
