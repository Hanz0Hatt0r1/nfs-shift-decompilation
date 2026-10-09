import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_ordinary_mov_zero_init_handoff.py"
UPSTREAM = ROOT / "evidence" / "p1a_p13a_slot01_ordinary_mov_zero_init_machine_closure.json"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_ordinary_mov_zero_init_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_zero_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_checked_handoff():
    module = load_module()
    assert module.build(UPSTREAM) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_zero_init_candidate_set_is_exact():
    module = load_module()
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    assert upstream["inventory"]["candidate_functions"] == module.EXPECTED
    assert len(module.EXPECTED) == 6
    assert all(row["rejected"] for row in upstream["candidate_adjudication"])


def test_handoff_closes_only_ordinary_mov_zero_init():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    surface = data["ordinary_mov_zero_init_surface"]
    assert surface["candidate_count"] == 6
    assert surface["rejected_count"] == 6
    assert surface["selected_slot3_writer_found"] is False
    classes = {row["function"]: row["class"] for row in surface["candidate_rejections"]}
    assert classes["FUN_0087aa00"] == "hdvehicle-plus-0x6730-service-subobject-clear"
    assert classes["FUN_0070fae0"] == "physics-manager-singleton-constructor"

    adj = data["adjudication"]
    assert adj["slot3_shallow_ordinary_mov_zero_init_depth4_subset_complete"] is True
    assert adj["slot3_x87_zero_init_surface_complete"] is False
    assert adj["slot3_sse_vector_zero_init_surface_complete"] is False
    assert adj["slot3_deeper_direct_alias_paths_complete"] is False
    assert adj["slot3_indirect_callback_alias_paths_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
