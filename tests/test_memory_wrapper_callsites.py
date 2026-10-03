import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    tool_dir = Path(__file__).resolve().parents[1] / "tools" / "shift_live_dump"
    sys.path.insert(0, str(tool_dir))
    try:
        path = tool_dir / "extract_memory_wrapper_callsites.py"
        spec = importlib.util.spec_from_file_location("extract_memory_wrapper_callsites", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _write_source(path: Path) -> None:
    path.write_text(
        r'''
void FUN_00100000(void) {
    void *p;
    p = FUN_008868c0(0xe4);
    FUN_008868d0(count * 4, FUN_00111111(a,b));
    FUN_00886900((uint)(count * 0x10), pool_id, 4);
}

void FUN_00100010(void) {
    FUN_00886930(p,1,0);
    FUN_00886950(p,1,0,context);
}

void FUN_00100020(void) {
    // Preserve a decompiler/source arity disagreement instead of fixing it.
    FUN_00886900(0x20,4);
}
''',
        encoding="utf-8",
    )


def _edge(source: str, target: str) -> dict:
    return {
        "from_function": source,
        "from_name": "caller",
        "instruction": source,
        "to": target,
        "to_name": "callee",
        "indirect": False,
    }


def _write_ghidra(root: Path) -> None:
    root.mkdir()
    rows = [
        _edge("0x00100000", "0x008868c0"),
        _edge("0x00100000", "0x008868d0"),
        _edge("0x00100000", "0x00886900"),
        _edge("0x00100010", "0x00886930"),
        _edge("0x00100010", "0x00886950"),
        # Deliberately omit FUN_00100020 -> FUN_00886900.
    ]
    with (root / "callgraph.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _calls(report, wrapper):
    return [row for row in report["callsites"] if row["wrapper"] == wrapper]


def test_inventory_preserves_raw_arguments_arity_and_ghidra_edges(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    _write_source(source)
    ghidra = tmp_path / "ghidra"
    _write_ghidra(ghidra)

    report = module.extract_memory_wrapper_callsites(source, ghidra)

    assert report["format"] == "SHIFT-MEMORY-WRAPPER-CALLSITES/1"
    assert report["function_count"] == 3
    assert report["callsite_count"] == 6
    assert report["ghidra_checked_callsite_count"] == 6
    assert report["ghidra_confirmed_callsite_count"] == 5
    assert report["ghidra_mismatch_callsite_count"] == 1
    assert report["arity_match_callsite_count"] == 5
    assert len(report["source_sha256"]) == 64

    c0 = _calls(report, "FUN_008868c0")[0]
    assert c0["assigned_local"] == "p"
    assert c0["observed_argument_count"] == 1
    assert c0["arguments"][0]["simple_integer_value"] == 0xE4
    assert c0["arguments"][0]["kind"] == "integer-literal"
    assert c0["ghidra_direct_edge"] is True

    d0 = _calls(report, "FUN_008868d0")[0]
    assert d0["observed_argument_count"] == 2
    assert d0["arguments"][0]["expression"] == "count * 4"
    assert d0["arguments"][0]["kind"] == "arithmetic-expression"
    assert d0["arguments"][1]["expression"] == "FUN_00111111(a,b)"
    assert d0["arguments"][1]["kind"] == "call-expression"

    f900 = _calls(report, "FUN_00886900")
    assert len(f900) == 2
    assert f900[0]["observed_argument_count"] == 3
    assert f900[0]["arity_matches_physical_parameter_count"] is True
    assert [arg["expression"] for arg in f900[0]["arguments"]] == [
        "(uint)(count * 0x10)",
        "pool_id",
        "4",
    ]
    assert f900[1]["observed_argument_count"] == 2
    assert f900[1]["arity_matches_physical_parameter_count"] is False
    assert f900[1]["ghidra_direct_edge"] is False

    wrapper = next(row for row in report["wrappers"] if row["wrapper"] == "FUN_008868c0")
    assert wrapper["first_argument_simple_integer_values"] == [{"value": 0xE4, "count": 1}]
    assert report["scope"]["argument_semantic_roles_proven"] is False
    assert report["scope"]["allocation_size_role_proven"] is False


def test_without_ghidra_keeps_direct_edge_unknown(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    _write_source(source)

    report = module.extract_memory_wrapper_callsites(source)

    assert report["ghidra_checked_callsite_count"] == 0
    assert report["ghidra_confirmed_callsite_count"] == 0
    assert report["ghidra_mismatch_callsite_count"] == 0
    assert all(row["ghidra_direct_edge"] is None for row in report["callsites"])


def test_argument_splitter_handles_nested_delimiters_and_strings():
    module = _load_module()
    raw = 'calc(a,b), "pool,a", table[index(a,b)], (x + y)'
    assert module._split_arguments(raw) == [
        "calc(a,b)",
        '"pool,a"',
        "table[index(a,b)]",
        "(x + y)",
    ]
