#!/usr/bin/env python3
"""Build conservative ABI-shape evidence for the retail memory wrapper cluster.

This layer intentionally trusts Ghidra's function boundaries, calling convention,
parameter storage and direct-call edges more than recovered semantic parameter
types.  Auto-types such as ``AptFrameStack *`` are retained for audit only and
never participate in promotion decisions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-WRAPPER-FAMILY/1"
MEMORY_FORMAT = "SHIFT-MEMORY-HELPER-SEMANTICS/1"

WRAPPER_SPECS: tuple[dict[str, Any], ...] = (
    {
        "address": "0x008868c0",
        "name": "FUN_008868c0",
        "side": "create",
        "ordinal": 0,
        "calling_convention": "__cdecl",
        "parameter_storage": ["Stack[0x4]:4"],
        "required_direct_callees": ["0x006382b0"],
    },
    {
        "address": "0x008868d0",
        "name": "FUN_008868d0",
        "side": "create",
        "ordinal": 1,
        "calling_convention": "__cdecl",
        "parameter_storage": ["Stack[0x4]:4", "Stack[0x8]:4"],
        "required_direct_callees": ["0x00638020", "0x006382b0"],
    },
    {
        "address": "0x00886900",
        "name": "FUN_00886900",
        "side": "create",
        "ordinal": 2,
        "calling_convention": "__cdecl",
        "parameter_storage": ["Stack[0x4]:4", "Stack[0x8]:4", "Stack[0xc]:4"],
        "required_direct_callees": ["0x00638020", "0x006382b0"],
        "diagnostic_anchor": "create_helper",
    },
    {
        "address": "0x00886930",
        "name": "FUN_00886930",
        "side": "release",
        "ordinal": 0,
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "DL:1", "Stack[0x4]:4"],
        "required_direct_callees": ["0x0064f4c0"],
        "diagnostic_anchor": "release_helper",
    },
    {
        "address": "0x00886950",
        "name": "FUN_00886950",
        "side": "release",
        "ordinal": 1,
        "calling_convention": "__fastcall",
        "parameter_storage": ["ECX:4", "DL:1", "Stack[0x4]:4", "Stack[0x8]:4"],
        "required_direct_callees": ["0x0064f260", "0x0064f4c0"],
    },
)


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


def _load_memory_semantics(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("format") != MEMORY_FORMAT:
        raise ValueError(f"{path}: expected {MEMORY_FORMAT}")
    return report


def _load_ghidra(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    functions_path = root / "functions.jsonl"
    callgraph_path = root / "callgraph.jsonl"
    missing = [path.name for path in (functions_path, callgraph_path) if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(functions_path):
        address = row.get("address")
        if isinstance(address, str):
            functions[address] = row

    outgoing: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(callgraph_path):
        source = row.get("from_function")
        target = row.get("to")
        if (
            row.get("indirect") is False
            and isinstance(source, str)
            and isinstance(target, str)
        ):
            outgoing.setdefault(source, []).append(
                {
                    "instruction": row.get("instruction"),
                    "target": target,
                    "target_name": row.get("to_name"),
                }
            )
    for rows in outgoing.values():
        rows.sort(key=lambda row: (row.get("instruction") or "", row["target"]))
    return functions, outgoing


def _storage_list(function: dict[str, Any] | None) -> list[str]:
    if function is None:
        return []
    return [
        str(parameter.get("storage"))
        for parameter in (function.get("parameters") or [])
        if isinstance(parameter, dict) and parameter.get("storage") is not None
    ]


def _type_list(function: dict[str, Any] | None) -> list[str]:
    if function is None:
        return []
    return [
        str(parameter.get("type"))
        for parameter in (function.get("parameters") or [])
        if isinstance(parameter, dict) and parameter.get("type") is not None
    ]


def _diagnostic_anchor_state(memory: dict[str, Any]) -> dict[str, bool]:
    create = False
    release = False
    paired = False
    for family in memory.get("families") or []:
        if not isinstance(family, dict):
            continue
        if family.get("create_helper") != "FUN_00886900":
            continue
        if family.get("release_helper") != "FUN_00886930":
            continue
        create = family.get("pool_allocation_path_evidence") is True
        release = family.get("pool_free_path_evidence") is True
        paired = family.get("diagnostic_backed_pool_lifetime_family") is True
        break
    return {
        "create_anchor_pool_path": create,
        "release_anchor_pool_path": release,
        "anchor_pair_diagnostic_backed": paired,
    }


def _inspect_wrapper(
    spec: dict[str, Any],
    functions: dict[str, dict[str, Any]],
    outgoing: dict[str, list[dict[str, Any]]],
    anchors: dict[str, bool],
) -> dict[str, Any]:
    address = spec["address"]
    function = functions.get(address)
    storage = _storage_list(function)
    types = _type_list(function)
    expected_storage = list(spec["parameter_storage"])
    expected_callees = set(spec["required_direct_callees"])
    edges = outgoing.get(address, [])
    direct_targets = {row["target"] for row in edges}

    present = function is not None
    cc_match = bool(present and function.get("calling_convention") == spec["calling_convention"])
    storage_match = bool(present and storage == expected_storage)
    callee_match = expected_callees.issubset(direct_targets)
    abi_shape = bool(present and cc_match and storage_match)
    backend_shape = bool(present and callee_match)
    wrapper_shape = bool(abi_shape and backend_shape)

    anchor_key = spec.get("diagnostic_anchor")
    diagnostic_anchor_confirmed: bool | None = None
    if anchor_key == "create_helper":
        diagnostic_anchor_confirmed = anchors["create_anchor_pool_path"]
    elif anchor_key == "release_helper":
        diagnostic_anchor_confirmed = anchors["release_anchor_pool_path"]

    return {
        "address": address,
        "name": spec["name"],
        "side": spec["side"],
        "ordinal": spec["ordinal"],
        "function_present": present,
        "size": function.get("size") if function else None,
        "thunk": function.get("thunk") if function else None,
        "calling_convention": function.get("calling_convention") if function else None,
        "expected_calling_convention": spec["calling_convention"],
        "calling_convention_match": cc_match,
        "parameter_count": len(storage),
        "parameter_storage": storage,
        "expected_parameter_storage": expected_storage,
        "parameter_storage_match": storage_match,
        "reported_parameter_types": types,
        "reported_signature": function.get("signature") if function else None,
        "semantic_parameter_types_used_for_promotion": False,
        "required_direct_callees": sorted(expected_callees),
        "direct_callees": edges,
        "required_direct_callees_present": callee_match,
        "abi_shape_confirmed": abi_shape,
        "backend_shape_confirmed": backend_shape,
        "wrapper_shape_confirmed": wrapper_shape,
        "diagnostic_anchor": anchor_key,
        "diagnostic_anchor_confirmed": diagnostic_anchor_confirmed,
    }


def _side_progression(rows: list[dict[str, Any]], side: str) -> dict[str, Any]:
    side_rows = sorted(
        (row for row in rows if row["side"] == side),
        key=lambda row: int(row["ordinal"]),
    )
    counts = [int(row["parameter_count"]) for row in side_rows]
    expected = list(range(counts[0], counts[0] + len(counts))) if counts else []
    storage_prefix_growth = True
    for previous, current in zip(side_rows, side_rows[1:]):
        prev_storage = previous["parameter_storage"]
        cur_storage = current["parameter_storage"]
        if cur_storage[: len(prev_storage)] != prev_storage or len(cur_storage) != len(prev_storage) + 1:
            storage_prefix_growth = False
            break
    return {
        "side": side,
        "members": [row["name"] for row in side_rows],
        "parameter_counts": counts,
        "one_parameter_growth": counts == expected,
        "storage_prefix_growth": storage_prefix_growth,
        "all_wrapper_shapes_confirmed": all(row["wrapper_shape_confirmed"] for row in side_rows),
    }


def build_memory_wrapper_family(
    memory_semantics_path: Path,
    ghidra_export: Path,
) -> dict[str, Any]:
    memory = _load_memory_semantics(memory_semantics_path)
    functions, outgoing = _load_ghidra(ghidra_export)
    anchors = _diagnostic_anchor_state(memory)
    wrappers = [
        _inspect_wrapper(spec, functions, outgoing, anchors)
        for spec in WRAPPER_SPECS
    ]
    create_progression = _side_progression(wrappers, "create")
    release_progression = _side_progression(wrappers, "release")

    all_shapes = all(row["wrapper_shape_confirmed"] for row in wrappers)
    family_candidate = bool(
        all_shapes
        and create_progression["one_parameter_growth"]
        and create_progression["storage_prefix_growth"]
        and release_progression["one_parameter_growth"]
        and release_progression["storage_prefix_growth"]
        and anchors["anchor_pair_diagnostic_backed"]
    )

    return {
        "format": FORMAT,
        "memory_helper_semantics": str(memory_semantics_path),
        "ghidra_export": str(ghidra_export),
        "wrapper_count": len(wrappers),
        "confirmed_wrapper_shape_count": sum(
            row["wrapper_shape_confirmed"] is True for row in wrappers
        ),
        "diagnostic_anchor_pair_confirmed": anchors["anchor_pair_diagnostic_backed"],
        "memory_wrapper_family_candidate": family_candidate,
        "wrappers": wrappers,
        "progressions": {
            "create": create_progression,
            "release": release_progression,
        },
        "scope": {
            "function_boundaries_used": True,
            "calling_conventions_used": True,
            "physical_parameter_storage_used": True,
            "direct_call_edges_used": True,
            "ghidra_semantic_parameter_types_trusted": False,
            "argument_roles_proven": False,
            "return_value_semantics_proven": False,
            "allocator_abi_proven": False,
            "release_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "note": (
                "The family candidate records regular wrapper ABI/storage and direct "
                "backend shapes around diagnostic-backed pool-path anchors. Ghidra's "
                "semantic parameter types are preserved only for audit and do not "
                "participate in promotion. Argument roles and allocator/free ABI remain "
                "unresolved until instruction-level forwarding is recovered."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memory_semantics", type=Path)
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_memory_wrapper_family(args.memory_semantics, args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"wrappers: {report['wrapper_count']}")
    print(f"confirmed wrapper shapes: {report['confirmed_wrapper_shape_count']}")
    print(f"memory wrapper family candidate: {report['memory_wrapper_family_candidate']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
