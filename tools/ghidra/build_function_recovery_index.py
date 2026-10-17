#!/usr/bin/env python3
"""Build a hash-locked, non-renaming function-name candidate index for SHIFT."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discover_method_name_anchors import discover_method_name_anchors

FORMAT = "SHIFT.GhidraFunctionRecoveryIndex/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
MANAGER_GETTER = "0x00489ad0"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compose_index(
    functions: list[dict],
    calls: list[dict],
    anchors: dict,
    source_hashes: dict[str, str],
    executable_sha256: str,
) -> dict:
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError("unexpected SHIFT retail executable SHA-256")

    function_by_address = {row.get("address", "").lower(): row for row in functions}
    anchor_by_address = {
        row.get("address", "").lower(): row for row in anchors.get("functions", [])
    }
    callers: dict[str, set[str]] = {}
    for row in calls:
        if row.get("indirect") is True or str(row.get("to", "")).lower() != MANAGER_GETTER:
            continue
        address = str(row.get("from_function", "")).lower()
        if address:
            callers.setdefault(address, set()).add(str(row.get("instruction", "")).lower())

    caller_rows = []
    for address, sites in sorted(callers.items()):
        function = function_by_address.get(address)
        if function is None:
            raise ValueError(f"callgraph caller missing from function inventory: {address}")
        anchor = anchor_by_address.get(address, {})
        candidate = anchor.get("unique_method_name_candidate")
        caller_rows.append(
            {
                "address": address,
                "ghidra_name": function.get("name"),
                "size": function.get("size"),
                "mnemonic_sha256": function.get("mnemonic_sha256"),
                "direct_call_sites": sorted(site for site in sites if site),
                "method_name_candidate": candidate,
                "method_name_status": anchor.get("status", "no-method-name-anchor"),
                "method_anchors": anchor.get("method_anchors", []),
            }
        )

    recovery_rows = []
    for address, anchor in sorted(anchor_by_address.items()):
        function = function_by_address.get(address)
        if function is None:
            raise ValueError(f"method-anchor function missing from inventory: {address}")
        recovery_rows.append(
            {
                "address": address,
                "ghidra_name": function.get("name"),
                "size": function.get("size"),
                "mnemonic_sha256": function.get("mnemonic_sha256"),
                "method_name_candidate": anchor.get("unique_method_name_candidate"),
                "method_name_status": anchor.get("status"),
                "method_anchors": anchor.get("method_anchors", []),
                "anchor_string_addresses": anchor.get("anchor_string_addresses", []),
                "manager_getter_call_sites": sorted(callers.get(address, set())),
            }
        )

    named_callers = sum(row["method_name_candidate"] is not None for row in caller_rows)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": executable_sha256,
            "retail_executable_md5": RETAIL_MD5,
            "ghidra_export_source_hashes": source_hashes,
        },
        "method_name_recovery": {
            "anchor_format": anchors.get("format"),
            "function_inventory_count": anchors.get("function_inventory_count"),
            "method_string_anchor_count": anchors.get("method_string_anchor_count"),
            "unique_method_name_candidate_count": anchors.get("unique_method_name_candidate_count"),
            "ambiguous_method_anchor_function_count": anchors.get("ambiguous_method_anchor_function_count"),
            "automatic_function_renaming_performed": False,
            "candidates": recovery_rows,
        },
        "manager_root_getter_callers": {
            "getter_function": MANAGER_GETTER,
            "direct_callgraph_callsite_count": sum(len(row["direct_call_sites"]) for row in caller_rows),
            "unique_caller_count": len(caller_rows),
            "caller_with_unique_method_name_candidate_count": named_callers,
            "callers": caller_rows,
        },
        "scope": {
            "method_string_xref_is_candidate_not_function_identity_proof": True,
            "direct_getter_callgraph_is_not_all_pointer_origins": True,
            "manager_374_to_hdvehicle_4330_identity_proven": False,
            "p1_3_control_producer_complete": False,
        },
        "limits": [
            "A unique exact method string is a recovered-name candidate; it does not prove the full function contract and is not applied as a Ghidra rename.",
            "The getter slice includes only direct callgraph references to FUN_00489ad0; indirect calls and independently synthesized roots are outside it.",
            "This index does not complete the manager+0x374 -> HDVehicle+0x4330 identity join or P1.3.",
        ],
    }


def build(executable: Path, export: Path) -> dict:
    executable_hash = sha256(executable)
    if executable_hash != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT retail executable SHA-256: {executable_hash}")
    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    binary = json.loads((export / "binary.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "SHIFT.GhidraEvidenceDatabase/1":
        raise ValueError("unsupported Ghidra evidence database format")
    if binary.get("executable_md5") != RETAIL_MD5:
        raise ValueError("Ghidra export does not match PC retail 1.02")
    source_files = ["manifest.json", "binary.json", "functions.jsonl", "callgraph.jsonl", "strings_xrefs.jsonl"]
    source_hashes = {name: sha256(export / name) for name in source_files}
    anchors = discover_method_name_anchors(export)
    return compose_index(
        read_jsonl(export / "functions.jsonl"),
        read_jsonl(export / "callgraph.jsonl"),
        anchors,
        source_hashes,
        executable_hash,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.executable, args.ghidra_export)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"recovered-name candidates: {report['method_name_recovery']['unique_method_name_candidate_count']}")
    print(f"manager getter callers: {report['manager_root_getter_callers']['unique_caller_count']}")
    print(f"named getter callers: {report['manager_root_getter_callers']['caller_with_unique_method_name_candidate_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
