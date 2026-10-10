import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_slot3_exact_root_persistence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_exact_root_persistence", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_export(path: Path, module, mutate=None):
    rows = []
    for index, (name, (address, register, start, end)) in enumerate(module.EXPECTED.items()):
        uses = []
        counts = {
            "root_mention_count": 1,
            "call_boundary_count": 0,
            "memory_store_root_count": 0,
            "push_root_count": 0,
            "register_copy_root_count": 0,
            "derived_address_root_count": 0,
        }
        if name == "FUN_00755950":
            uses = [{
                "instruction_address": "0x00755960",
                "mnemonic": "mov",
                "text": "mov DWORD PTR [eax],edx",
                "exact_root_register_mentioned": True,
                "candidate_kinds": ["memory-store-root"],
                "pcode_ops": ["STORE"],
            }]
            counts["memory_store_root_count"] = 1
        elif name == "FUN_00755f80":
            uses = [{
                "instruction_address": "0x00755fa0",
                "mnemonic": "push",
                "text": "push esi",
                "exact_root_register_mentioned": True,
                "candidate_kinds": ["push-root"],
                "pcode_ops": ["COPY"],
            }]
            counts["push_root_count"] = 1
        else:
            uses = [{
                "instruction_address": f"0x{int(start, 16):08x}",
                "mnemonic": "mov",
                "text": f"mov eax,DWORD PTR [{register}+0x20]",
                "exact_root_register_mentioned": True,
                "candidate_kinds": ["root-based-memory-source"],
                "pcode_ops": ["LOAD"],
            }]
        row = {
            "format": module.INPUT_FORMAT,
            "program": "SHIFT.exe",
            "function_address": address,
            "function_name": name,
            "root_register": register,
            "window_start": start,
            "window_end_exclusive": end,
            "identity_note": "synthetic pinned window",
            **counts,
            "uses": uses,
        }
        if mutate is not None:
            mutate(index, row)
        rows.append(row)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_analyzer_ranks_store_and_push_without_promoting_global_gates(tmp_path):
    module = load_module()
    source = tmp_path / "persistence.jsonl"
    write_export(source, module)
    payload = module.analyze(source)

    assert payload["format"] == "SHIFT.P1D.Slot3ExactRootPersistenceFrontier/1"
    assert payload["counts"]["carrier_windows"] == 6
    assert payload["counts"]["memory_store_root"] == 1
    assert payload["counts"]["push_root"] == 1
    assert payload["ranked_candidates"][0]["candidate_kinds"] == ["memory-store-root"]
    assert payload["ranked_candidates"][0]["score"] == 100
    assert payload["ranked_candidates"][1]["candidate_kinds"] == ["push-root"]
    assert payload["ranked_candidates"][1]["score"] == 90
    a = payload["adjudication"]
    assert a["bounded_exact_root_window_inventory_complete"] is True
    assert a["persistence_candidates_ranked"] is True
    assert a["exact_root_persistent_store_proven"] is False
    assert a["exact_root_escape_to_stack_or_argument_proven"] is False
    assert a["stored_or_escaped_aliases_ruled_out"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_analyzer_requires_every_pinned_exact_root_window(tmp_path):
    module = load_module()
    source = tmp_path / "persistence.jsonl"
    write_export(source, module)
    lines = source.read_text(encoding="utf-8").splitlines()
    source.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    try:
        module.analyze(source)
    except ValueError as exc:
        assert "missing exact-root carrier windows" in str(exc)
    else:
        raise AssertionError("missing carrier window must fail closed")


def test_analyzer_rejects_root_window_drift(tmp_path):
    module = load_module()
    source = tmp_path / "persistence.jsonl"

    def mutate(index, row):
        if index == 0:
            row["root_register"] = "eax"

    write_export(source, module, mutate=mutate)
    try:
        module.analyze(source)
    except ValueError as exc:
        assert "exact-root window drift" in str(exc)
    else:
        raise AssertionError("root-register drift must fail closed")
