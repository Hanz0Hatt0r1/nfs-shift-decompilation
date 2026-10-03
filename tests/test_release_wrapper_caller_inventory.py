import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_release_wrapper_caller_inventory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_release_wrapper_caller_inventory", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _edge(caller, instruction, target, name, *, indirect=False):
    return {
        "from_function": caller,
        "instruction": instruction,
        "to": target,
        "to_name": name,
        "indirect": indirect,
    }


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_inventory_selects_only_direct_release_wrapper_callers(tmp_path):
    module = _load_module()
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            _edge("0x00100000", "0x00100020", "0x00886930", "FUN_00886930"),
            _edge("0x00100000", "0x00100040", "0x00886950", "FUN_00886950"),
            _edge("0x00200000", "0x00200010", "0x00886930", "FUN_00886930"),
            _edge("0x00300000", "0x00300010", "0x00886930", "FUN_00886930", indirect=True),
            _edge("0x00400000", "0x00400010", "0x00638020", "FUN_00638020"),
        ],
    )

    report = module.build_release_wrapper_caller_inventory(ghidra)

    assert report["total_caller_count"] == 2
    assert report["selected_caller_count"] == 2
    assert report["total_direct_edge_count"] == 3
    assert report["caller_targets"] == ["0x00100000", "0x00200000"]
    first = report["callers"][0]
    assert first["call_count"] == 2
    assert [row["wrapper"] for row in first["calls"]] == [
        "FUN_00886930",
        "FUN_00886950",
    ]
    assert report["scope"]["caller_instruction_arguments_proven"] is False


def test_inventory_truncates_deterministically(tmp_path):
    module = _load_module()
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_jsonl(
        ghidra / "callgraph.jsonl",
        [
            _edge("0x00300000", "0x00300010", "0x00886930", "FUN_00886930"),
            _edge("0x00100000", "0x00100010", "0x00886930", "FUN_00886930"),
            _edge("0x00200000", "0x00200010", "0x00886950", "FUN_00886950"),
        ],
    )

    report = module.build_release_wrapper_caller_inventory(ghidra, max_callers=2)

    assert report["truncated"] is True
    assert report["total_caller_count"] == 3
    assert report["selected_caller_count"] == 2
    assert report["caller_targets"] == ["0x00100000", "0x00200000"]
    assert report["selected_direct_edge_count"] == 2


def test_inventory_requires_callgraph(tmp_path):
    module = _load_module()
    try:
        module.build_release_wrapper_caller_inventory(tmp_path)
    except FileNotFoundError as exc:
        assert "callgraph.jsonl" in str(exc)
    else:
        raise AssertionError("missing callgraph must fail")


def test_inventory_rejects_nonpositive_limit(tmp_path):
    module = _load_module()
    try:
        module.build_release_wrapper_caller_inventory(tmp_path, max_callers=0)
    except ValueError as exc:
        assert "max_callers" in str(exc)
    else:
        raise AssertionError("nonpositive max_callers must fail")
