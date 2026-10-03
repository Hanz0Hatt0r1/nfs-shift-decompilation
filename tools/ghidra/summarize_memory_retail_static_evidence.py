#!/usr/bin/env python3
"""Summarize retail static memory-wrapper/backend evidence without source C output.

This report intentionally distinguishes proved physical roles from unresolved
semantic roles. It consumes the independent wrapper-forwarding, backend,
diagnostic-slice, release-pointer-chain and release-byte behavior artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT-MEMORY-RETAIL-STATIC-SUMMARY/1"
EXPECTED = {
    "forwarding": "SHIFT-MEMORY-WRAPPER-FORWARDING/1",
    "backend": "SHIFT-MEMORY-BACKEND-EVIDENCE/1",
    "allocation_slice": "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1",
    "free_slice": "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1",
    "release_chain": "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1",
    "release_byte": "SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1",
}


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def summarize_memory_retail_static_evidence(
    forwarding_path: Path,
    backend_path: Path,
    allocation_slice_path: Path,
    free_slice_path: Path,
    release_chain_path: Path,
    release_byte_path: Path,
) -> dict[str, Any]:
    forwarding = _load(forwarding_path, EXPECTED["forwarding"])
    backend = _load(backend_path, EXPECTED["backend"])
    allocation_slice = _load(allocation_slice_path, EXPECTED["allocation_slice"])
    free_slice = _load(free_slice_path, EXPECTED["free_slice"])
    release_chain = _load(release_chain_path, EXPECTED["release_chain"])
    release_byte = _load(release_byte_path, EXPECTED["release_byte"])

    allocation_size_proven = allocation_slice.get("allocation_size_role_proven") is True
    free_pointer_local_proven = free_slice.get("free_pointer_role_proven") is True
    released_pointer_wrapper_proven = (
        release_chain.get("release_pointer_to_wrapper_storage_proven") is True
    )
    wrapper_forwarding_proven = forwarding.get("all_wrapper_forwarding_confirmed") is True

    allocation_storage = (
        allocation_slice.get("allocation_size_entry_storage")
        if allocation_size_proven
        else None
    )
    free_storage = free_slice.get("free_pointer_entry_storage") if free_pointer_local_proven else None
    released_wrapper_storage = sorted(
        {
            str(row.get("wrapper_input_storage"))
            for row in (release_chain.get("wrapper_paths") or [])
            if isinstance(row, dict)
            and row.get("released_pointer_path_proven") is True
            and row.get("wrapper_input_storage")
        }
    )

    diagnostic_inventory = backend.get("diagnostics")
    if diagnostic_inventory is None:
        diagnostic_inventory = backend.get("diagnostic_inventory") or []

    dl_behavior = {
        "analysis_complete": release_byte.get("analysis_complete") is True,
        "thunk_forwarded_to_release_backend": (
            release_byte.get("thunk_entry_dl_forwarded_to_release_backend") is True
        ),
        "release_backend_observed": release_byte.get("release_backend_entry_dl_observed") is True,
        "controls_conditional_branch": (
            release_byte.get("release_backend_entry_dl_controls_conditional_branch") is True
        ),
        "bitwise_transformed": (
            release_byte.get("release_backend_entry_dl_bitwise_transformed") is True
        ),
    }

    blockers: list[str] = []
    if not wrapper_forwarding_proven:
        blockers.append("wrapper_forwarding_not_fully_proven")
    if not allocation_size_proven:
        blockers.append("allocation_size_backend_storage_not_proven")
    if not free_pointer_local_proven:
        blockers.append("free_pointer_diagnostic_storage_not_proven")
    if not released_pointer_wrapper_proven:
        blockers.append("released_pointer_wrapper_storage_not_proven")
    if not dl_behavior["analysis_complete"]:
        blockers.append("release_byte_behavior_incomplete")

    return {
        "format": FORMAT,
        "inputs": {
            "forwarding": str(forwarding_path),
            "backend": str(backend_path),
            "allocation_slice": str(allocation_slice_path),
            "free_slice": str(free_slice_path),
            "release_chain": str(release_chain_path),
            "release_byte": str(release_byte_path),
        },
        "wrapper_forwarding": {
            "wrapper_count": forwarding.get("wrapper_count"),
            "confirmed_wrapper_forwarding_count": forwarding.get(
                "confirmed_wrapper_forwarding_count"
            ),
            "all_wrapper_forwarding_confirmed": wrapper_forwarding_proven,
        },
        "backend_diagnostics": {
            "allocation_path_proven": bool(
                backend.get("allocation_diagnostic_xref_covered") is True
                or backend.get("scope", {}).get("allocation_diagnostic_xref_covered") is True
            ),
            "free_path_proven": bool(
                backend.get("release_diagnostic_path_proven") is True
                or backend.get("scope", {}).get("release_diagnostic_path_proven") is True
            ),
            "diagnostic_inventory": diagnostic_inventory,
        },
        "proven_physical_roles": {
            "allocation_size": {
                "proven": allocation_size_proven,
                "function": "FUN_00638020",
                "entry_storage": allocation_storage,
                "semantic_anchor": "allocation diagnostic `%d`",
            },
            "free_pointer_local": {
                "proven": free_pointer_local_proven,
                "function": "FUN_00657c30",
                "entry_storage": free_storage,
                "semantic_anchor": "pool-free diagnostic `%p`",
            },
            "released_pointer_wrapper": {
                "proven": released_pointer_wrapper_proven,
                "wrapper_input_storage": released_wrapper_storage,
                "semantic_anchor": "instruction chain to pool-free diagnostic `%p`",
            },
        },
        "release_byte_behavior": dl_behavior,
        "ready_for_source_semantic_join": bool(
            wrapper_forwarding_proven
            and allocation_size_proven
            and released_pointer_wrapper_proven
        ),
        "blockers": blockers,
        "scope": {
            "retail_instruction_evidence_used": True,
            "full_ghidra_string_callgraph_evidence_used": True,
            "source_decompiler_output_required": False,
            "allocation_size_physical_role_proven": allocation_size_proven,
            "released_pointer_physical_role_proven": released_pointer_wrapper_proven,
            "release_byte_behavior_observed": release_byte.get("scope", {}).get(
                "entry_dl_behavior_observed"
            ) is True,
            "pool_selector_role_proven": False,
            "alignment_role_proven": False,
            "release_flag_role_proven": False,
            "delete_kind_role_proven": False,
            "allocator_abi_proven": False,
            "operator_new_identity_proven": False,
            "operator_delete_identity_proven": False,
            "ownership_semantics_proven": False,
            "note": (
                "This summary consolidates static retail evidence only. Positive physical "
                "roles are inherited from diagnostic-backed instruction traces; unresolved "
                "semantic roles remain false regardless of argument position or apparent use."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forwarding", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True)
    parser.add_argument("--allocation-slice", type=Path, required=True)
    parser.add_argument("--free-slice", type=Path, required=True)
    parser.add_argument("--release-chain", type=Path, required=True)
    parser.add_argument("--release-byte", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = summarize_memory_retail_static_evidence(
        args.forwarding,
        args.backend,
        args.allocation_slice,
        args.free_slice,
        args.release_chain,
        args.release_byte,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(
        "wrapper forwarding: "
        f"{report['wrapper_forwarding']['confirmed_wrapper_forwarding_count']}/"
        f"{report['wrapper_forwarding']['wrapper_count']}"
    )
    print(
        "allocation-size physical role proven: "
        f"{report['proven_physical_roles']['allocation_size']['proven']}"
    )
    print(
        "released-pointer wrapper role proven: "
        f"{report['proven_physical_roles']['released_pointer_wrapper']['proven']}"
    )
    print(f"ready for source semantic join: {report['ready_for_source_semantic_join']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
