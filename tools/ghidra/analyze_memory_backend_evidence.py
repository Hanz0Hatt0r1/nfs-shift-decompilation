#!/usr/bin/env python3
"""Cross-check targeted memory-backend instructions with retail Ghidra evidence.

This analyzer intentionally stops before assigning semantic parameter names. It
joins a narrow instruction export for the known allocation/release backend
cluster with direct callgraph edges and pool diagnostics from the full Ghidra
export. The resulting artifact proves backend coverage, diagnostic-reference
sites and bounded backend chains without inferring allocator ABI, ownership or
argument roles such as size/pool/alignment/delete flag.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/1"

TARGETS: tuple[tuple[str, str], ...] = (
    ("0x00638020", "allocation-diagnostic-backend"),
    ("0x006382b0", "create-fallback-backend"),
    ("0x0064f260", "release-branch-backend"),
    ("0x0064f4c0", "release-thunk"),
    ("0x0064f3a0", "release-backend"),
    ("0x00657c30", "free-diagnostic-backend"),
)
TARGET_ADDRESSES = {address for address, _ in TARGETS}
ALLOC_DIAGNOSTIC = re.compile(
    r"Unable to allocate .*bytes of memory from the pool", re.IGNORECASE
)
FREE_DIAGNOSTIC = re.compile(r"Error freeing .* from pool", re.IGNORECASE)


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _load_instruction_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != INSTRUCTION_FORMAT:
            raise ValueError(f"{path}: expected {INSTRUCTION_FORMAT}")
        if row.get("found") is not True:
            raise ValueError(f"{path}: unresolved requested function {row.get('requested')}")
        function = row.get("function")
        if not isinstance(function, dict):
            raise ValueError(f"{path}: missing function metadata")
        address = _norm_address(function.get("address"))
        if address is None:
            raise ValueError(f"{path}: invalid function address {function.get('address')!r}")
        rows[address] = row
    missing = sorted(TARGET_ADDRESSES - set(rows))
    if missing:
        raise ValueError("instruction export missing backend targets: " + ", ".join(missing))
    return rows


def _diagnostic_kind(value: str) -> str | None:
    if ALLOC_DIAGNOSTIC.search(value):
        return "pool-allocation-diagnostic"
    if FREE_DIAGNOSTIC.search(value):
        return "pool-free-diagnostic"
    return None


def _load_diagnostics(root: Path) -> list[dict[str, Any]]:
    path = root / "strings_xrefs.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    rows: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        kind = _diagnostic_kind(value)
        if kind is None:
            continue
        functions = [
            normalized
            for item in (row.get("functions") or [])
            if (normalized := _norm_address(item)) is not None
        ]
        xrefs = [
            normalized
            for item in (row.get("xrefs") or [])
            if (normalized := _norm_address(item)) is not None
        ]
        rows.append(
            {
                "kind": kind,
                "string_address": _norm_address(row.get("address")),
                "value": value,
                "functions": functions,
                "xrefs": xrefs,
            }
        )
    rows.sort(key=lambda row: (row["kind"], row.get("string_address") or ""))
    return rows


def _load_callgraph(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path}")
    edges: list[dict[str, Any]] = []
    adjacency: dict[str, list[str]] = {}
    for row in _read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        source = _norm_address(row.get("from_function"))
        target = _norm_address(row.get("to"))
        if source is None or target is None:
            continue
        edge = {
            "from": source,
            "instruction": _norm_address(row.get("instruction")),
            "to": target,
            "to_name": row.get("to_name"),
        }
        edges.append(edge)
        adjacency.setdefault(source, []).append(target)
    for values in adjacency.values():
        values.sort()
    edges.sort(key=lambda row: (row["from"], row.get("instruction") or "", row["to"]))
    return edges, adjacency


def _shortest_path(adjacency: dict[str, list[str]], start: str, end: str, max_depth: int = 4) -> list[str]:
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == end:
            return path
        if len(path) - 1 >= max_depth:
            continue
        for target in adjacency.get(node, ()): 
            if target in seen:
                continue
            seen.add(target)
            queue.append((target, path + [target]))
    return []


def _instruction_target(instruction: dict[str, Any]) -> str | None:
    for ref in instruction.get("references") or []:
        if not isinstance(ref, dict):
            continue
        ref_type = str(ref.get("type") or "").upper()
        if "CALL" not in ref_type and "JUMP" not in ref_type:
            continue
        target = _norm_address(ref.get("to"))
        if target is not None:
            return target
    for value in instruction.get("flows") or []:
        target = _norm_address(value)
        if target is not None:
            return target
    return None


def _function_record(
    address: str,
    role: str,
    row: dict[str, Any],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    instructions = [item for item in (row.get("instructions") or []) if isinstance(item, dict)]
    instruction_addresses = {
        normalized
        for item in instructions
        if (normalized := _norm_address(item.get("address"))) is not None
    }
    direct_transfers: list[dict[str, Any]] = []
    for instruction in instructions:
        mnemonic = str(instruction.get("mnemonic") or "").upper()
        if mnemonic not in {"CALL", "JMP"}:
            continue
        target = _instruction_target(instruction)
        if target is None:
            continue
        direct_transfers.append(
            {
                "instruction": _norm_address(instruction.get("address")),
                "transfer_kind": "tail-call" if mnemonic == "JMP" else "call",
                "target": target,
                "target_in_backend_cluster": target in TARGET_ADDRESSES,
            }
        )

    diagnostic_refs: list[dict[str, Any]] = []
    for diagnostic in diagnostics:
        if address not in diagnostic["functions"]:
            continue
        matched_xrefs = [xref for xref in diagnostic["xrefs"] if xref in instruction_addresses]
        diagnostic_refs.append(
            {
                **diagnostic,
                "instruction_export_xrefs": matched_xrefs,
                "xref_instruction_covered": bool(matched_xrefs),
            }
        )

    function = row.get("function") or {}
    return {
        "address": address,
        "name": function.get("name"),
        "role": role,
        "calling_convention": function.get("calling_convention"),
        "instruction_count": len(instructions),
        "direct_transfers": direct_transfers,
        "diagnostic_references": diagnostic_refs,
        "diagnostic_reference_count": len(diagnostic_refs),
        "all_diagnostic_xrefs_instruction_covered": bool(diagnostic_refs)
        and all(item["xref_instruction_covered"] for item in diagnostic_refs),
    }


def analyze_memory_backend_evidence(instruction_export: Path, ghidra_export: Path) -> dict[str, Any]:
    rows = _load_instruction_rows(instruction_export)
    diagnostics = _load_diagnostics(ghidra_export)
    callgraph_edges, adjacency = _load_callgraph(ghidra_export)

    functions = [
        _function_record(address, role, rows[address], diagnostics)
        for address, role in TARGETS
    ]
    by_address = {row["address"]: row for row in functions}

    allocation_diagnostic = any(
        item["kind"] == "pool-allocation-diagnostic"
        for item in by_address["0x00638020"]["diagnostic_references"]
    )
    free_diagnostic = any(
        item["kind"] == "pool-free-diagnostic"
        for item in by_address["0x00657c30"]["diagnostic_references"]
    )
    release_path = _shortest_path(adjacency, "0x0064f4c0", "0x00657c30", max_depth=4)

    cluster_edges = [
        edge for edge in callgraph_edges
        if edge["from"] in TARGET_ADDRESSES and edge["to"] in TARGET_ADDRESSES
    ]

    return {
        "format": FORMAT,
        "instruction_export": str(instruction_export),
        "ghidra_export": str(ghidra_export),
        "target_count": len(TARGETS),
        "all_targets_present": len(functions) == len(TARGETS),
        "functions": functions,
        "diagnostic_inventory": diagnostics,
        "cluster_callgraph_edges": cluster_edges,
        "allocation_backend_diagnostic_proven": allocation_diagnostic,
        "free_backend_diagnostic_proven": free_diagnostic,
        "release_thunk_to_free_diagnostic_path": release_path,
        "release_thunk_to_free_diagnostic_path_proven": bool(release_path),
        "scope": {
            "backend_instruction_bodies_exported": True,
            "diagnostic_reference_sites_crosschecked": True,
            "direct_backend_callgraph_used": True,
            "allocation_size_role_proven": False,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "allocator_abi_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "This artifact proves targeted backend instruction coverage, retail pool "
                "diagnostic xref sites and bounded direct backend chains. It does not yet "
                "prove which physical backend argument supplies a diagnostic %d/%s/%p "
                "field, so semantic parameter roles remain unassigned."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_memory_backend_evidence(args.instruction_export, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"backend targets: {report['target_count']}")
    print(f"allocation diagnostic proven: {report['allocation_backend_diagnostic_proven']}")
    print(f"free diagnostic proven: {report['free_backend_diagnostic_proven']}")
    print(
        "release thunk -> free diagnostic path proven: "
        f"{report['release_thunk_to_free_diagnostic_path_proven']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
