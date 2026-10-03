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


def _write_callgraph(path: Path, edges: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for source, target in edges:
            handle.write(
                json.dumps(
                    {
                        "from_function": source,
                        "instruction": source,
                        "to": target,
                        "to_name": None,
                        "indirect": False,
                    }
                )
                + "\n"
            )


def _source_text() -> str:
    return r'''
undefined FUN_00100000(int param_1)
{
  void *p;
  void *q;
  p = FUN_008868c0(0xe4);
  q = FUN_008868d0(param_1 * 4, FUN_00112233(param_1, 7));
  FUN_00886930(p, '\0', 4);
}

undefined FUN_00110000(int flags)
{
  void *p;
  p = FUN_00886900(0x38, 4, 0x10);
  FUN_00886950(p, 1, flags, (void *)0);
  FUN_008868c0(sizeof(int[3]));
}
'''


def _call(report, caller, wrapper, occurrence=0):
    return next(
        row
        for row in report["callsites"]
        if row["caller"] == caller
        and row["wrapper"] == wrapper
        and row["occurrence"] == occurrence
    )


def _summary(report, wrapper):
    return next(row for row in report["wrappers"] if row["wrapper"] == wrapper)


def test_extracts_nested_arguments_literals_and_ghidra_edges(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(_source_text(), encoding="utf-8")
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_callgraph(
        ghidra / "callgraph.jsonl",
        [
            ("0x00100000", "0x008868c0"),
            ("0x00100000", "0x008868d0"),
            ("0x00100000", "0x00886930"),
            ("0x00110000", "0x00886900"),
            ("0x00110000", "0x00886950"),
            ("0x00110000", "0x008868c0"),
        ],
    )

    report = module.extract_memory_wrapper_callsites(source, ghidra)
    assert report["format"] == "SHIFT-MEMORY-WRAPPER-CALLSITE-EVIDENCE/1"
    assert report["callsite_count"] == 6
    assert report["caller_count"] == 2
    assert report["parsed_callsite_count"] == 6
    assert report["unparsed_callsite_count"] == 0
    assert report["ghidra_confirmed_callsite_count"] == 6
    assert report["ghidra_rejected_callsite_count"] == 0

    nested = _call(report, "FUN_00100000", "FUN_008868d0")
    assert nested["argument_count"] == 2
    assert nested["arguments"][0]["expression"] == "param_1 * 4"
    assert nested["arguments"][0]["integer_literals"] == [4]
    assert nested["arguments"][0]["is_exact_integer_literal"] is False
    assert nested["arguments"][1]["expression"] == "FUN_00112233(param_1, 7)"
    assert nested["arguments"][1]["integer_literals"] == [7]
    assert nested["arguments"][1]["is_exact_integer_literal"] is False

    create = _call(report, "FUN_00110000", "FUN_00886900")
    assert [arg["exact_integer_value"] for arg in create["arguments"]] == [0x38, 4, 0x10]
    assert all(arg["is_exact_integer_literal"] for arg in create["arguments"])

    release = _call(report, "FUN_00100000", "FUN_00886930")
    assert release["arguments"][0]["is_simple_identifier"] is True
    assert release["arguments"][1]["is_exact_integer_literal"] is False
    assert release["arguments"][2]["exact_integer_value"] == 4

    cast_zero = _call(report, "FUN_00110000", "FUN_00886950")
    assert cast_zero["arguments"][3]["expression"] == "(void *)0"
    assert cast_zero["arguments"][3]["integer_literals"] == [0]
    assert cast_zero["arguments"][3]["is_exact_integer_literal"] is False

    summary = _summary(report, "FUN_00886900")
    assert summary["argument_count_histogram"] == [{"argument_count": 3, "callsite_count": 1}]
    assert [row["distinct_integer_literals"] for row in summary["literal_positions"]] == [
        [0x38],
        [4],
        [0x10],
    ]
    assert report["scope"]["argument_roles_proven"] is False
    assert report["scope"]["allocator_abi_proven"] is False


def test_preserves_multiple_occurrences_and_optional_ghidra_state(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        """
undefined FUN_00120000(void)
{
  FUN_008868c0(16);
  FUN_008868c0(32);
}
""",
        encoding="utf-8",
    )

    report = module.extract_memory_wrapper_callsites(source)
    rows = [row for row in report["callsites"] if row["wrapper"] == "FUN_008868c0"]
    assert [row["occurrence"] for row in rows] == [0, 1]
    assert [row["arguments"][0]["exact_integer_value"] for row in rows] == [16, 32]
    assert all(row["ghidra_direct_edge"] is None for row in rows)
    assert report["ghidra_crosscheck_available"] is False

    summary = _summary(report, "FUN_008868c0")
    assert summary["callsite_count"] == 2
    assert summary["caller_count"] == 1
    assert summary["literal_positions"][0]["distinct_integer_literals"] == [16, 32]
    assert summary["literal_positions"][0]["callsite_count_with_exact_integer_literal"] == 2


def test_ghidra_mismatch_is_preserved_not_silently_repaired(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        """
undefined FUN_00130000(void)
{
  FUN_00886900(0x20, 4, 9);
}
""",
        encoding="utf-8",
    )
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    _write_callgraph(ghidra / "callgraph.jsonl", [("0x00130000", "0x008868c0")])

    report = module.extract_memory_wrapper_callsites(source, ghidra)
    row = report["callsites"][0]
    assert row["ghidra_direct_edge"] is False
    assert report["ghidra_confirmed_callsite_count"] == 0
    assert report["ghidra_rejected_callsite_count"] == 1
    summary = _summary(report, "FUN_00886900")
    assert summary["ghidra_rejected_callsite_count"] == 1


def test_missing_ghidra_callgraph_fails_when_crosscheck_was_requested(tmp_path):
    module = _load_module()
    source = tmp_path / "SHIFT.exe.c"
    source.write_text(
        """
undefined FUN_00140000(void)
{
  FUN_008868c0(4);
}
""",
        encoding="utf-8",
    )
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()

    try:
        module.extract_memory_wrapper_callsites(source, ghidra)
    except FileNotFoundError as exc:
        assert "missing Ghidra callgraph" in str(exc)
    else:
        raise AssertionError("requested Ghidra cross-check must require callgraph.jsonl")
