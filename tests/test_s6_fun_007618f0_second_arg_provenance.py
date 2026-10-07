from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools/ghidra/build_fun_007618f0_second_arg_worklist.py"
ANALYZER_PATH = ROOT / "tools/ghidra/analyze_fun_007618f0_second_arg_provenance.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load(BUILDER_PATH, "phase738_builder")
analyzer = _load(ANALYZER_PATH, "phase738_analyzer")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _insn(address: str, mnemonic: str, operands: list[str], *, fallthrough: str | None, flows: list[str] | None = None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
        "flows": [] if flows is None else flows,
        "flow_type": "CALL" if mnemonic == "CALL" else "FALL_THROUGH",
        "fallthrough": fallthrough,
        "pcode": [],
    }


def _instruction_row(caller: str, instructions: list[dict]) -> dict:
    return {
        "format": analyzer.INSTRUCTION_FORMAT,
        "found": True,
        "function": {"address": caller, "name": "FUN_00100000"},
        "instruction_count": len(instructions),
        "instructions": instructions,
    }


def _worklist(caller: str = "0x00100000", callsite: str = "0x00100009") -> dict:
    return {
        "format": analyzer.WORKLIST_FORMAT,
        "target": analyzer.TARGET,
        "direct_calls": [
            {
                "caller": caller,
                "caller_name": "FUN_00100000",
                "callsite": callsite,
                "target": analyzer.TARGET,
            }
        ],
    }


def test_worklist_builder_selects_only_direct_callers(tmp_path: Path) -> None:
    (tmp_path / "binary.json").write_text(
        json.dumps({"program_name": builder.PROGRAM, "executable_md5": builder.PE_MD5}),
        encoding="utf-8",
    )
    _write_jsonl(
        tmp_path / "functions.jsonl",
        [
            {"address": builder.TARGET, "name": builder.TARGET_NAME},
            {"address": "0x00100000", "name": "FUN_00100000"},
            {"address": "0x00200000", "name": "FUN_00200000"},
        ],
    )
    _write_jsonl(
        tmp_path / "callgraph.jsonl",
        [
            {
                "from_function": "0x00100000",
                "from_name": "FUN_00100000",
                "instruction": "0x00100009",
                "to": builder.TARGET,
                "to_name": builder.TARGET_NAME,
                "indirect": False,
            },
            {
                "from_function": "0x00200000",
                "instruction": "0x00200010",
                "to": builder.TARGET,
                "indirect": True,
            },
        ],
    )
    report = builder.build_worklist(tmp_path)
    assert report["ready"] is True
    assert report["direct_call_count"] == 1
    assert report["direct_caller_count"] == 1
    assert report["instruction_export_targets"] == ["0x00100000"]
    assert report["semantic_owner_claimed"] is False


def test_analyzer_resolves_register_push_to_exact_memory_origin() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "MOV", ["ESI", "ECX"], fallthrough="0x00100002"),
        _insn("0x00100002", "MOV", ["EAX", "[ESI+0x1234]"], fallthrough="0x00100008"),
        _insn("0x00100008", "PUSH", ["EAX"], fallthrough="0x00100009"),
        _insn("0x00100009", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["explicit_argument_push_ready"] is True
    assert call["explicit_argument_push"] == "0x00100008"
    assert call["explicit_argument_operand"] == "EAX"
    assert call["explicit_argument_origins"] == ["memory:[esi+0x1234]"]
    assert call["explicit_argument_flags"]["exact_single_physical_origin"] is True
    assert report["all_callsites_argument_physically_resolved"] is True
    assert report["semantic_owner_claimed"] is False


def test_analyzer_preserves_entry_register_origin() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "MOV", ["ESI", "ECX"], fallthrough="0x00100005"),
        _insn("0x00100005", "PUSH", ["ESI"], fallthrough="0x00100009"),
        _insn("0x00100009", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["explicit_argument_origins"] == ["entry:ECX"]
    assert call["explicit_argument_flags"]["exact_single_physical_origin"] is True


def test_analyzer_fails_closed_when_argument_is_not_immediate_pre_call_push() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["ESI"], fallthrough="0x00100004"),
        _insn("0x00100004", "MOV", ["EAX", "EBX"], fallthrough="0x00100009"),
        _insn("0x00100009", "CALL", [analyzer.TARGET], fallthrough=None, flows=[analyzer.TARGET]),
    ]
    report = analyzer.analyze(_worklist(), {caller: instructions})
    call = report["callsites"][0]
    assert call["explicit_argument_push_ready"] is False
    assert call["explicit_argument_origins"] == []
    assert report["all_callsites_argument_physically_resolved"] is False
    assert report["ready_for_semantic_owner_join"] is False


def test_analyzer_rejects_callsite_target_drift() -> None:
    caller = "0x00100000"
    instructions = [
        _insn("0x00100000", "PUSH", ["ESI"], fallthrough="0x00100009"),
        _insn("0x00100009", "CALL", ["0x00760000"], fallthrough=None, flows=["0x00760000"]),
    ]
    try:
        analyzer.analyze(_worklist(), {caller: instructions})
    except ValueError as exc:
        assert "no longer targets" in str(exc)
    else:
        raise AssertionError("target drift must fail closed")
