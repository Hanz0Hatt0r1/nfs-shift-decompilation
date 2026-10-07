#!/usr/bin/env python3
"""Build a finite retail caller worklist for FUN_007618f0 second-argument proof.

This stage consumes only direct Ghidra observations from the full SHIFT evidence
export.  It discovers every direct caller/callsite of FUN_007618f0 and emits the
caller addresses required by ShiftFunctionInstructionExporter.java.

Callgraph membership is discovery evidence only.  No semantic identity is
assigned to the explicit stack argument by this stage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.Fun007618f0SecondArgumentWorklist/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
TARGET = "0x007618f0"
TARGET_NAME = "FUN_007618f0"


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _address(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: missing address")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _load_binary(root: Path) -> dict[str, Any]:
    path = root / "binary.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    if value.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected program: {value.get('program_name')!r}")
    if value.get("executable_md5") != PE_MD5:
        raise ValueError(
            f"unexpected executable MD5: expected {PE_MD5}, got {value.get('executable_md5')!r}"
        )
    return value


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        result[address] = row
    if TARGET not in result:
        raise ValueError(f"required target {TARGET_NAME} ({TARGET}) absent from functions export")
    return result


def build_worklist(root: Path) -> dict[str, Any]:
    binary = _load_binary(root)
    functions = _load_functions(root)
    callgraph_path = root / "callgraph.jsonl"

    calls: list[dict[str, Any]] = []
    malformed_direct_edges: list[dict[str, Any]] = []
    for line_no, row in enumerate(_read_jsonl(callgraph_path), 1):
        if row.get("indirect") is not False:
            continue
        try:
            target = _address(row.get("to"), field="callgraph.to")
        except ValueError as exc:
            malformed_direct_edges.append({"line": line_no, "reason": str(exc)})
            continue
        if target != TARGET:
            continue
        try:
            caller = _address(row.get("from_function"), field="callgraph.from_function")
            callsite = _address(row.get("instruction"), field="callgraph.instruction")
        except ValueError as exc:
            malformed_direct_edges.append({"line": line_no, "reason": str(exc)})
            continue
        if caller not in functions:
            raise ValueError(f"direct caller {caller} missing from functions export")
        calls.append(
            {
                "caller": caller,
                "caller_name": row.get("from_name") or functions[caller].get("name"),
                "callsite": callsite,
                "target": TARGET,
                "target_name": row.get("to_name") or TARGET_NAME,
            }
        )

    calls.sort(key=lambda row: (int(row["caller"], 0), int(row["callsite"], 0)))
    seen_calls: set[tuple[str, str]] = set()
    for row in calls:
        key = (row["caller"], row["callsite"])
        if key in seen_calls:
            raise ValueError(f"duplicate direct call edge: {key[0]} {key[1]}")
        seen_calls.add(key)

    targets = sorted({row["caller"] for row in calls}, key=lambda value: int(value, 0))
    return {
        "format": FORMAT,
        "version": 1,
        "program": PROGRAM,
        "executable_md5": binary.get("executable_md5"),
        "target": TARGET,
        "target_name": TARGET_NAME,
        "direct_call_count": len(calls),
        "direct_caller_count": len(targets),
        "direct_calls": calls,
        "instruction_export_targets": targets,
        "malformed_direct_edges": malformed_direct_edges,
        "ready": bool(calls),
        "semantic_owner_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_root", type=Path)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--targets-out", type=Path, required=True)
    args = parser.parse_args()

    report = build_worklist(args.evidence_root)
    if not report["ready"]:
        raise SystemExit("no direct FUN_007618f0 callers found; refusing empty instruction worklist")
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.targets_out.parent.mkdir(parents=True, exist_ok=True)
    args.targets_out.write_text(
        "".join(f"{target}\n" for target in report["instruction_export_targets"]),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
