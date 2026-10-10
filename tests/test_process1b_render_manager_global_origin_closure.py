import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_render_manager_global_origin_closure.py"
EVIDENCE = ROOT / "evidence" / "p1b_render_manager_global_origin_closure.json"

spec = importlib.util.spec_from_file_location("build_p1b_render_manager_global_origin_closure", TOOL)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_reproduces_committed_evidence():
    assert m.build() == load_evidence()


def test_writer_inventory_is_exhaustive_and_unique_non_null_origin():
    data = load_evidence()
    inv = data["writer_inventory"]
    assert inv["exact_xref_count"] == 116
    assert inv["selected_function_count"] == 80
    assert inv["write_reference_count"] == 2
    assert inv["writer_function"] == "FUN_00d36210"
    assert {w["site"] for w in inv["writes"]} == {"0x00d362ec", "0x00d362f3"}
    assert data["constructor_identity"]["constructor"] == "FUN_0045ef50"
    assert data["constructor_identity"]["all_reachable_returns_eax_origin"] == "entry:ECX"


def test_candidate_global_origin_closes_but_global_unknown_memory_does_not():
    adj = load_evidence()["adjudication"]
    assert adj["candidate_global_writer_surface_complete"] is True
    assert adj["candidate_global_non_null_origin_unique"] is True
    assert adj["external_or_unknown_origin_through_candidate_global_complete"] is True
    assert adj["external_or_unknown_origin_through_candidate_global_found"] is False
    assert adj["arbitrary_unknown_memory_exact_root_alias_surface_complete"] is False
    assert adj["memory_load_opaque_runtime_reconstruction_complete"] is False
    assert adj["helper_non_vtable_setter_surface_complete"] is False


def test_global_gates_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
