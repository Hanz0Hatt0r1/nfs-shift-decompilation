import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_getproc_argument_flow.py"
PLAN = ROOT / "evidence" / "p1d_controller1_getproc_argument_worklist.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_getproc_flow", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_db(path: Path, strings: list[tuple[str, str]]) -> None:
    db = sqlite3.connect(path)
    try:
        db.execute("CREATE TABLE strings(value TEXT,address TEXT,containing_function TEXT,raw_json TEXT NOT NULL)")
        for address, value in strings:
            db.execute("INSERT INTO strings VALUES(?,?,?,?)", (value, address, "", "{}"))
        db.commit()
    finally:
        db.close()


def make_plan(path: Path, function: str, callsite: str) -> None:
    path.write_text(
        json.dumps({
            "format": "SHIFT.P1D.Controller1GetProcArgumentWorklist/1",
            "targets": [{"function": function, "getprocaddress_callsites": [callsite]}],
        }),
        encoding="utf-8",
    )


def ins(address: str, mnemonic: str, text: str, operands=None, refs=None):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "text": text,
        "operands": operands or [],
        "references": refs or [],
        "pcode": [],
    }


def make_export(path: Path, function: str, instructions: list[dict]) -> None:
    path.write_text(
        json.dumps({
            "format": "SHIFT.GhidraFunctionInstructions/2",
            "program": "SHIFT.exe",
            "requested": function,
            "found": True,
            "function": {"address": function, "name": "FUN_TEST", "size": 32, "calling_convention": "__cdecl"},
            "instruction_count": len(instructions),
            "instructions": instructions,
        }) + "\n",
        encoding="utf-8",
    )


def test_exact_literal_lp_proc_name_is_recovered(tmp_path):
    module = load_module()
    db = tmp_path / "x.sqlite"
    export = tmp_path / "instructions.jsonl"
    plan = tmp_path / "plan.json"
    make_db(db, [("0x00b384bc", "EncodePointer")])
    make_plan(plan, "0x0090aa27", "0x0090aa7b")
    make_export(export, "0x0090aa27", [
        ins("0x0090aa70", "PUSH", "PUSH 0xb384bc", ["0xb384bc"], [{"to": "0x00b384bc", "type": "DATA"}]),
        ins("0x0090aa75", "PUSH", "PUSH EAX", ["EAX"]),
        ins("0x0090aa7b", "CALL", "CALL dword ptr [GetProcAddress]", ["[GetProcAddress]"], [{"to": "0x000000c5", "type": "UNCONDITIONAL_CALL"}]),
    ])
    payload = module.analyze(export, db, plan)
    call = payload["surface"]["functions"][0]["calls"][0]
    assert call["lp_proc_name_proven"] is True
    assert call["resolved_name"] == "EncodePointer"
    assert call["apc_name"] is False
    assert payload["adjudication"]["direct_named_resolver_surface_rejected"] is True
    assert payload["adjudication"]["controller1_timing_exhaustive"] is False


def test_apc_literal_prevents_negative_surface_closure(tmp_path):
    module = load_module()
    db = tmp_path / "x.sqlite"
    export = tmp_path / "instructions.jsonl"
    plan = tmp_path / "plan.json"
    make_db(db, [("0x00b40000", "QueueUserAPC")])
    make_plan(plan, "0x0090aa27", "0x0090aa7b")
    make_export(export, "0x0090aa27", [
        ins("0x0090aa70", "PUSH", "PUSH 0xb40000", ["0xb40000"], [{"to": "0x00b40000", "type": "DATA"}]),
        ins("0x0090aa75", "PUSH", "PUSH EAX", ["EAX"]),
        ins("0x0090aa7b", "CALL", "CALL dword ptr [GetProcAddress]"),
    ])
    payload = module.analyze(export, db, plan)
    call = payload["surface"]["functions"][0]["calls"][0]
    assert call["resolved_name"] == "QueueUserAPC"
    assert call["apc_name"] is True
    assert payload["adjudication"]["direct_named_resolver_surface_rejected"] is False


def test_register_built_name_remains_unresolved(tmp_path):
    module = load_module()
    db = tmp_path / "x.sqlite"
    export = tmp_path / "instructions.jsonl"
    plan = tmp_path / "plan.json"
    make_db(db, [])
    make_plan(plan, "0x0090aa27", "0x0090aa7b")
    make_export(export, "0x0090aa27", [
        ins("0x0090aa70", "PUSH", "PUSH ESI", ["ESI"]),
        ins("0x0090aa75", "PUSH", "PUSH EAX", ["EAX"]),
        ins("0x0090aa7b", "CALL", "CALL dword ptr [GetProcAddress]"),
    ])
    payload = module.analyze(export, db, plan)
    call = payload["surface"]["functions"][0]["calls"][0]
    assert call["lp_proc_name_proven"] is False
    assert payload["adjudication"]["direct_named_resolver_surface_rejected"] is False
    assert payload["adjudication"]["hashed_or_generated_resolution_ruled_out"] is False


def test_pinned_worklist_matches_reachable_surface():
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1GetProcArgumentWorklist/1"
    assert payload["counts"] == {"function_count": 6, "getprocaddress_call_count": 11}
    assert [row["function"] for row in payload["targets"]] == [
        "0x0090748b",
        "0x0090aa27",
        "0x0090aa9e",
        "0x0090abb8",
        "0x009189cd",
        "0x0091c073",
    ]
    assert payload["execution"]["machine_instruction_export_captured"] is False
    assert payload["adjudication"]["controller1_timing_exhaustive"] is False
    assert payload["adjudication"]["external_provider_count"] == 7
