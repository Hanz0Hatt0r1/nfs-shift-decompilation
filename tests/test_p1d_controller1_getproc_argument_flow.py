import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_getproc_argument_flow.py"
PE_TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_getproc_retail_pe.py"
PLAN = ROOT / "evidence" / "p1d_controller1_getproc_argument_worklist.json"
MACHINE = ROOT / "evidence" / "p1d_controller1_getproc_retail_machine_proof.json"


def load_module(path=TOOL, name="p1d_getproc_flow"):
    spec = importlib.util.spec_from_file_location(name, path)
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


def test_stack_slot_reuse_lp_proc_name_is_recovered(tmp_path):
    module = load_module()
    db = tmp_path / "x.sqlite"
    export = tmp_path / "instructions.jsonl"
    plan = tmp_path / "plan.json"
    make_db(db, [("0x00b42138", "GetActiveWindow")])
    make_plan(plan, "0x0091c073", "0x0091c0d9")
    make_export(export, "0x0091c073", [
        ins("0x0091c0c7", "CALL", "CALL 0x90aa27", ["0x90aa27"]),
        ins("0x0091c0cc", "MOV", "MOV dword ptr [ESP],0xb42138", ["dword ptr [ESP]", "0xb42138"], [{"to": "0x00b42138", "type": "DATA"}]),
        ins("0x0091c0d3", "PUSH", "PUSH EDI", ["EDI"]),
        ins("0x0091c0d4", "MOV", "MOV [0xc329fc],EAX", ["[0xc329fc]", "EAX"]),
        ins("0x0091c0d9", "CALL", "CALL ESI", ["ESI"]),
    ])
    payload = module.analyze(export, db, plan)
    call = payload["surface"]["functions"][0]["calls"][0]
    assert call["lp_proc_name_proven"] is True
    assert call["resolved_name"] == "GetActiveWindow"
    assert call["apc_name"] is False


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


def test_pinned_worklist_matches_reachable_surface_and_machine_closure():
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
    assert payload["execution"]["direct_retail_pe_machine_proof_captured"] is True
    assert payload["execution"]["exact_lpProcName_flow_adjudicated"] is True
    assert payload["adjudication"]["direct_named_resolver_surface_rejected"] is True
    assert payload["adjudication"]["controller1_timing_exhaustive"] is False
    assert payload["adjudication"]["external_provider_count"] == 7


def test_retail_machine_evidence_closes_only_direct_named_surface():
    payload = json.loads(MACHINE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1GetProcRetailMachineProof/1"
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert payload["resolver_import"] == {
        "iat_va": "0x00aa62fc",
        "dll": "KERNEL32.dll",
        "name": "GetProcAddress",
        "getprocaddress_identity_proven": True,
    }
    assert payload["surface"]["function_count"] == 6
    assert payload["surface"]["call_count"] == 11
    assert payload["surface"]["apc_name_call_count"] == 0
    assert payload["surface"]["resolved_names"] == [
        "CorExitProcess",
        "EncodePointer",
        "DecodePointer",
        "EncodePointer",
        "DecodePointer",
        "InitializeCriticalSectionAndSpinCount",
        "MessageBoxA",
        "GetActiveWindow",
        "GetLastActivePopup",
        "GetUserObjectInformationA",
        "GetProcessWindowStation",
    ]
    adj = payload["adjudication"]
    assert adj["all_11_machine_windows_match"] is True
    assert adj["getprocaddress_iat_identity_proven"] is True
    assert adj["all_11_exact_names_non_apc"] is True
    assert adj["direct_worker_reachable_named_getproc_apc_surface_rejected"] is True
    assert adj["hashed_or_generated_resolution_ruled_out"] is False
    assert adj["manual_export_walk_ruled_out"] is False
    assert adj["native_or_syscall_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_retail_pe_tool_constants_match_pinned_evidence():
    module = load_module(PE_TOOL, "p1d_getproc_retail_pe")
    payload = json.loads(MACHINE.read_text(encoding="utf-8"))
    assert module.RETAIL_SHA256 == payload["authority"]["retail_executable_sha256"]
    assert module.GETPROC_IAT_VA == int(payload["resolver_import"]["iat_va"], 16)
    assert [(x["callsite"], x["name"]) for x in module.CALLS] == [
        (x["callsite"], x["name"]) for x in payload["surface"]["calls"]
    ]
