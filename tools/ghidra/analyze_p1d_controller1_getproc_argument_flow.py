#!/usr/bin/env python3
"""Adjudicate direct worker-reachable GetProcAddress name arguments.

Consumes targeted SHIFT.GhidraFunctionInstructions/2 rows plus the Ghidra SQLite
index and a pinned P1D worklist.  The analysis is deliberately conservative:
it only promotes a resolver name when the lpProcName argument is recovered as an
exact literal string address from the two PUSH arguments immediately feeding a
GetProcAddress call.  Register/generated/stack-built names remain unresolved.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

INPUT_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
PLAN_FORMAT = "SHIFT.P1D.Controller1GetProcArgumentWorklist/1"
FORMAT = "SHIFT.P1D.Controller1GetProcArgumentFlow/1"
APC_NAMES = {
    "QueueUserAPC",
    "NtQueueApcThread",
    "NtQueueApcThreadEx",
    "ZwQueueApcThread",
    "RtlQueueApcWow64Thread",
    "SetWaitableTimerEx",
}
HEX_RE = re.compile(r"0x[0-9a-fA-F]+")


def norm_hex(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return f"0x{int(value, 16):08x}"
    except ValueError:
        return value.lower()


def load_plan(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != PLAN_FORMAT:
        raise ValueError(f"unexpected plan format: {payload.get('format')!r}")
    return payload


def load_instruction_export(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        rec = json.loads(raw)
        if rec.get("format") != INPUT_FORMAT:
            raise ValueError(f"{path}:{line_no}: unexpected format {rec.get('format')!r}")
        if not rec.get("found"):
            raise ValueError(f"{path}:{line_no}: requested function not found")
        fn = rec.get("function") or {}
        address = norm_hex(fn.get("address"))
        if not address:
            raise ValueError(f"{path}:{line_no}: missing function address")
        rows[address] = rec
    return rows


def load_strings(db_path: Path) -> dict[str, list[str]]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        cols = {row[1] for row in db.execute("PRAGMA table_info(strings)")}
        if not {"address", "value"}.issubset(cols):
            raise ValueError("SQLite strings table lacks address/value columns")
        out: dict[str, list[str]] = {}
        for row in db.execute("SELECT address,value FROM strings"):
            address = norm_hex(row["address"])
            if not address:
                continue
            value = str(row["value"] or "")
            if value and value not in out.setdefault(address, []):
                out[address].append(value)
        return out
    finally:
        db.close()


def literal_addresses(ins: dict) -> list[str]:
    values: list[str] = []
    for ref in ins.get("references", []):
        target = norm_hex(ref.get("to"))
        if target and target not in values:
            values.append(target)
    for operand in ins.get("operands", []):
        for token in HEX_RE.findall(str(operand)):
            target = norm_hex(token)
            if target and target not in values:
                values.append(target)
    return values


def classify_push(ins: dict, strings_by_address: dict[str, list[str]]) -> dict:
    addresses = literal_addresses(ins)
    hits = []
    for address in addresses:
        for value in strings_by_address.get(address, []):
            hits.append({"address": address, "value": value})
    unique = {(hit["address"], hit["value"]) for hit in hits}
    return {
        "instruction_address": norm_hex(ins.get("address")),
        "text": ins.get("text"),
        "literal_addresses": addresses,
        "string_hits": [
            {"address": address, "value": value}
            for address, value in sorted(unique)
        ],
    }


def adjudicate_call(function_row: dict, callsite: str, strings_by_address: dict[str, list[str]]) -> dict:
    instructions = function_row.get("instructions", [])
    target = norm_hex(callsite)
    call_index = next(
        (i for i, ins in enumerate(instructions) if norm_hex(ins.get("address")) == target),
        None,
    )
    if call_index is None:
        return {
            "callsite": target,
            "call_instruction_found": False,
            "lp_proc_name_proven": False,
            "resolved_name": None,
            "apc_name": False,
            "reason": "callsite missing from targeted instruction export",
        }

    call_ins = instructions[call_index]
    if not str(call_ins.get("mnemonic", "")).upper().startswith("CALL"):
        return {
            "callsite": target,
            "call_instruction_found": True,
            "lp_proc_name_proven": False,
            "resolved_name": None,
            "apc_name": False,
            "reason": "expected callsite is not a CALL instruction",
            "call_text": call_ins.get("text"),
        }

    pushes: list[dict] = []
    lower = max(0, call_index - 16)
    for i in range(call_index - 1, lower - 1, -1):
        ins = instructions[i]
        mnemonic = str(ins.get("mnemonic", "")).upper()
        if mnemonic.startswith("CALL") or mnemonic.startswith("RET"):
            break
        if mnemonic == "PUSH":
            pushes.append(classify_push(ins, strings_by_address))
            if len(pushes) == 2:
                break

    if len(pushes) < 2:
        return {
            "callsite": target,
            "call_instruction_found": True,
            "call_text": call_ins.get("text"),
            "lp_proc_name_proven": False,
            "resolved_name": None,
            "apc_name": False,
            "argument_pushes_nearest_first": pushes,
            "reason": "fewer than two bounded PUSH arguments recovered",
        }

    # Win32 stdcall: GetProcAddress(hModule, lpProcName) arguments are pushed
    # right-to-left, so nearest PUSH is hModule and second-nearest is lpProcName.
    name_push = pushes[1]
    hits = name_push["string_hits"]
    if len(hits) != 1:
        return {
            "callsite": target,
            "call_instruction_found": True,
            "call_text": call_ins.get("text"),
            "lp_proc_name_proven": False,
            "resolved_name": None,
            "apc_name": False,
            "argument_pushes_nearest_first": pushes,
            "reason": "lpProcName PUSH does not resolve to exactly one indexed literal string",
        }

    name = hits[0]["value"]
    return {
        "callsite": target,
        "call_instruction_found": True,
        "call_text": call_ins.get("text"),
        "lp_proc_name_proven": True,
        "resolved_name": name,
        "resolved_name_address": hits[0]["address"],
        "apc_name": name in APC_NAMES,
        "argument_pushes_nearest_first": pushes,
        "reason": "exact literal lpProcName recovered from bounded stdcall PUSH sequence",
    }


def analyze(instructions_path: Path, db_path: Path, plan_path: Path) -> dict:
    plan = load_plan(plan_path)
    rows = load_instruction_export(instructions_path)
    strings = load_strings(db_path)

    functions = []
    all_calls = []
    for target in plan.get("targets", []):
        fn_addr = norm_hex(target.get("function"))
        function_row = rows.get(fn_addr)
        call_results = []
        if function_row is None:
            for callsite in target.get("getprocaddress_callsites", []):
                call_results.append({
                    "callsite": norm_hex(callsite),
                    "call_instruction_found": False,
                    "lp_proc_name_proven": False,
                    "resolved_name": None,
                    "apc_name": False,
                    "reason": "function missing from targeted instruction export",
                })
        else:
            for callsite in target.get("getprocaddress_callsites", []):
                call_results.append(adjudicate_call(function_row, callsite, strings))
        all_calls.extend(call_results)
        functions.append({
            "function": fn_addr,
            "expected_callsites": [norm_hex(x) for x in target.get("getprocaddress_callsites", [])],
            "export_present": function_row is not None,
            "calls": call_results,
        })

    expected_count = sum(len(x.get("getprocaddress_callsites", [])) for x in plan.get("targets", []))
    proven = [x for x in all_calls if x.get("lp_proc_name_proven")]
    unresolved = [x for x in all_calls if not x.get("lp_proc_name_proven")]
    apc = [x for x in proven if x.get("apc_name")]
    complete = len(all_calls) == expected_count and not unresolved

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "input_format": INPUT_FORMAT,
        "plan_format": PLAN_FORMAT,
        "surface": {
            "expected_function_count": len(plan.get("targets", [])),
            "expected_getprocaddress_call_count": expected_count,
            "recovered_literal_name_count": len(proven),
            "unresolved_name_count": len(unresolved),
            "apc_name_call_count": len(apc),
            "functions": functions,
        },
        "adjudication": {
            "all_expected_direct_resolver_calls_have_exact_literal_names": complete,
            "all_proven_direct_literal_names_are_non_apc": bool(proven) and not apc,
            "direct_named_resolver_surface_rejected": complete and not apc,
            "register_generated_or_nonliteral_names_ruled_out": False,
            "indirect_resolver_calls_ruled_out": False,
            "hashed_or_generated_resolution_ruled_out": False,
            "manual_export_walk_ruled_out": False,
            "native_or_syscall_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Only the pinned worker-reachable direct GetProcAddress callsites are analyzed.",
            "Only exact literal lpProcName PUSH arguments are promoted; register, stack-built, decoded or generated names remain unresolved.",
            "A non-APC direct named resolver result does not rule out manual export walking, indirect resolution or native/syscall APC injection.",
        ],
        "next_step": (
            "If every direct call resolves to a non-APC literal, close only the direct named-resolver sub-surface; "
            "continue manual-export/native primitive adjudication and Controller #1 target-thread joins."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.instructions, args.database, args.plan)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
