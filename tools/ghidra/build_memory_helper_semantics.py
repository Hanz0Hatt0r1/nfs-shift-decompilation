#!/usr/bin/env python3
"""Cross-check recurring lifetime helpers against memory-pool diagnostics.

The analyzer uses only direct Ghidra callgraph edges plus defined string xrefs.
It records concrete bounded paths from create/release helpers to functions which
reference retail pool-allocation/free diagnostics.  This is stronger than helper
recurrence alone but still does not claim compiler allocator ABI or ownership.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-HELPER-SEMANTICS/1"
FAMILY_FORMAT = "SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1"

ALLOC_PATTERNS = (
    re.compile(r"Unable to allocate .*bytes of memory from the pool", re.IGNORECASE),
)
FREE_PATTERNS = (
    re.compile(r"Error freeing .* from pool", re.IGNORECASE),
)


def _load_json(path: Path, expected: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return report


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


def _address(function: str | None) -> str | None:
    if not isinstance(function, str) or not function.startswith("FUN_"):
        return None
    try:
        return f"0x{int(function[4:], 16):08x}"
    except ValueError:
        return None


def _diagnostic_kind(value: str) -> str | None:
    if any(pattern.search(value) for pattern in ALLOC_PATTERNS):
        return "pool-allocation-diagnostic"
    if any(pattern.search(value) for pattern in FREE_PATTERNS):
        return "pool-free-diagnostic"
    return None


def _load_ghidra(root: Path) -> dict[str, Any]:
    callgraph_path = root / "callgraph.jsonl"
    strings_path = root / "strings_xrefs.jsonl"
    missing = [
        path.name for path in (callgraph_path, strings_path) if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "missing required Ghidra files: " + ", ".join(missing)
        )

    adjacency: dict[str, list[dict[str, Any]]] = {}
    temp: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(callgraph_path):
        source = row.get("from_function")
        target = row.get("to")
        if (
            row.get("indirect") is False
            and isinstance(source, str)
            and isinstance(target, str)
        ):
            temp.setdefault(source, []).append(
                {
                    "instruction": row.get("instruction"),
                    "target": target,
                    "target_name": row.get("to_name"),
                }
            )
    for source, rows in temp.items():
        adjacency[source] = sorted(
            rows,
            key=lambda row: (row.get("instruction") or "", row["target"]),
        )

    diagnostics_by_function: dict[str, list[dict[str, Any]]] = {}
    all_diagnostics: list[dict[str, Any]] = []
    for row in _read_jsonl(strings_path):
        value = row.get("value")
        if not isinstance(value, str):
            continue
        kind = _diagnostic_kind(value)
        if kind is None:
            continue
        diagnostic = {
            "kind": kind,
            "string_address": row.get("address"),
            "value": value,
            "xrefs": row.get("xrefs") or [],
            "functions": [
                function
                for function in (row.get("functions") or [])
                if isinstance(function, str)
            ],
        }
        all_diagnostics.append(diagnostic)
        for function in diagnostic["functions"]:
            diagnostics_by_function.setdefault(function, []).append(diagnostic)

    return {
        "adjacency": adjacency,
        "diagnostics_by_function": diagnostics_by_function,
        "diagnostics": all_diagnostics,
    }


def _find_paths(
    start: str,
    ghidra: dict[str, Any],
    wanted_kind: str,
    max_depth: int,
    max_nodes: int,
) -> list[dict[str, Any]]:
    """Return shortest bounded direct-call paths to matching diagnostics."""
    queue = deque([(start, [start], [])])
    best_depth: dict[str, int] = {start: 0}
    visited_nodes = 0
    hits: list[dict[str, Any]] = []
    best_hit_depth: int | None = None

    while queue:
        function, path, edges = queue.popleft()
        depth = len(path) - 1
        visited_nodes += 1
        if visited_nodes > max_nodes:
            break
        if best_hit_depth is not None and depth > best_hit_depth:
            break

        for diagnostic in ghidra["diagnostics_by_function"].get(function, ()):
            if diagnostic["kind"] == wanted_kind:
                best_hit_depth = depth if best_hit_depth is None else best_hit_depth
                hits.append(
                    {
                        "diagnostic": diagnostic,
                        "function_path": path,
                        "edge_path": edges,
                        "depth": depth,
                    }
                )

        if depth >= max_depth or best_hit_depth is not None:
            continue

        for edge in ghidra["adjacency"].get(function, ()):
            target = edge["target"]
            next_depth = depth + 1
            previous = best_depth.get(target)
            if previous is not None and previous < next_depth:
                continue
            best_depth[target] = next_depth
            queue.append((target, path + [target], edges + [edge]))

    hits.sort(
        key=lambda row: (
            row["depth"],
            row["diagnostic"].get("string_address") or "",
            tuple(row["function_path"]),
        )
    )
    return hits


def build_memory_helper_semantics(
    family_path: Path,
    ghidra_export: Path,
    max_depth: int = 4,
    max_nodes: int = 5000,
) -> dict[str, Any]:
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")
    if max_nodes < 1:
        raise ValueError("max_nodes must be >= 1")

    families = _load_json(family_path, FAMILY_FORMAT)
    ghidra = _load_ghidra(ghidra_export)
    rows: list[dict[str, Any]] = []

    for family in families.get("families") or []:
        create_helper = family.get("create_helper")
        release_helper = family.get("release_helper")
        if not isinstance(create_helper, str) or not isinstance(release_helper, str):
            continue
        create_address = _address(create_helper)
        release_address = _address(release_helper)
        allocation_paths = (
            _find_paths(
                create_address,
                ghidra,
                "pool-allocation-diagnostic",
                max_depth,
                max_nodes,
            )
            if create_address is not None
            else []
        )
        free_paths = (
            _find_paths(
                release_address,
                ghidra,
                "pool-free-diagnostic",
                max_depth,
                max_nodes,
            )
            if release_address is not None
            else []
        )
        allocation_backed = bool(allocation_paths)
        free_backed = bool(free_paths)
        rows.append(
            {
                "create_helper": create_helper,
                "release_helper": release_helper,
                "class_count": family.get("class_count"),
                "classes": family.get("classes") or [],
                "descriptors": family.get("descriptors") or [],
                "recurrent_helper_pair": family.get("recurrent_helper_pair") is True,
                "crosschecked_recurrent_helper_family_candidate": (
                    family.get("crosschecked_recurrent_helper_family_candidate") is True
                ),
                "pool_allocation_path_evidence": allocation_backed,
                "pool_free_path_evidence": free_backed,
                "diagnostic_backed_pool_lifetime_family": bool(
                    allocation_backed and free_backed
                ),
                "allocation_diagnostic_paths": allocation_paths,
                "free_diagnostic_paths": free_paths,
            }
        )

    rows.sort(
        key=lambda row: (
            row["diagnostic_backed_pool_lifetime_family"] is not True,
            row["crosschecked_recurrent_helper_family_candidate"] is not True,
            -int(row.get("class_count") or 0),
            row["create_helper"],
            row["release_helper"],
        )
    )

    return {
        "format": FORMAT,
        "helper_families": str(family_path),
        "ghidra_export": str(ghidra_export),
        "max_depth": max_depth,
        "max_nodes": max_nodes,
        "diagnostic_inventory": ghidra["diagnostics"],
        "family_count": len(rows),
        "allocation_path_family_count": sum(
            row["pool_allocation_path_evidence"] is True for row in rows
        ),
        "free_path_family_count": sum(
            row["pool_free_path_evidence"] is True for row in rows
        ),
        "diagnostic_backed_pool_lifetime_family_count": sum(
            row["diagnostic_backed_pool_lifetime_family"] is True for row in rows
        ),
        "families": rows,
        "scope": {
            "pool_allocation_path_proven": True,
            "pool_free_path_proven": True,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "A positive family has a concrete bounded direct-call path from its "
                "create helper to a function referencing the retail pool-allocation "
                "diagnostic and a corresponding path from its release helper to a "
                "pool-free diagnostic. This proves participation in those memory-pool "
                "paths, not compiler allocator ABI or ownership semantics."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("families", type=Path, help="SHIFT-CLASS-LIFETIME-HELPER-FAMILIES/1 JSON")
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-nodes", type=int, default=5000)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_memory_helper_semantics(
        args.families,
        args.ghidra_export,
        args.max_depth,
        args.max_nodes,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"families: {report['family_count']}")
    print(
        "diagnostic-backed pool lifetime families: "
        f"{report['diagnostic_backed_pool_lifetime_family_count']}"
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
