#!/usr/bin/env python3
"""Index Ghidra-confirmed direct callees missed by objdump's linear decode."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_p1b_manager374_helper_returned_materialized_targets import (  # noqa: E402
    analyze_helper,
    disassemble,
    normalize_prefixed_instruction,
    parse_direct_target,
    norm,
)

FORMAT = "SHIFT.P1B.HelperReturnGhidraTargetRecovery/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def address(value: Any) -> int:
    return int(str(value), 16)


def normalize_ghidra_operands(operands: list[str]) -> str:
    text = ",".join(operands)
    text = re.sub(r"\s*\+\s*-", "-", text)
    text = re.sub(r"\s*-\s*-", "+", text)
    return norm(text)


def instruction_rows(function_export: dict[str, Any]) -> list[tuple[int, str, str]]:
    result = []
    for instruction in function_export.get("instructions", []):
        result.append(
            (
                address(instruction["address"]),
                str(instruction["mnemonic"]).lower(),
                normalize_ghidra_operands(instruction.get("operands", [])),
            )
        )
    return result


def compose_report(
    unresolved_callsites: list[tuple[int, int]],
    callgraph: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    target_exports: list[dict[str, Any]],
    prior_exports: list[dict[str, Any]],
    source_hashes: dict[str, str],
    target_export_sha256: str,
    prior_export_sha256: str,
    executable_sha256: str,
    unconfirmed_target_exports: list[dict[str, Any]] | None = None,
    unconfirmed_export_sha256: str | None = None,
) -> dict[str, Any]:
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError("unexpected SHIFT retail executable SHA-256")

    function_by_address = {address(row["address"]): row for row in functions}
    direct_edges = {
        (address(row["instruction"]), address(row["to"])): row
        for row in callgraph
        if row.get("indirect") is not True
    }
    confirmed_sites = []
    unmatched_sites = []
    target_sites: dict[int, set[int]] = defaultdict(set)
    for site, target in sorted(set(unresolved_callsites)):
        edge = direct_edges.get((site, target))
        if edge is None:
            unmatched_sites.append(
                {"callsite": f"0x{site:08x}", "target": f"0x{target:08x}"}
            )
            continue
        function = function_by_address.get(target)
        if function is None:
            raise ValueError(f"Ghidra callgraph target missing from function inventory: 0x{target:08x}")
        target_sites[target].add(site)
        confirmed_sites.append(
            {
                "callsite": f"0x{site:08x}",
                "caller_function": str(edge["from_function"]).lower(),
                "target_function": f"0x{target:08x}",
            }
        )

    unresolved_targets = {target for _, target in unresolved_callsites}
    confirmed_targets = set(target_sites)
    unconfirmed_targets = unresolved_targets - confirmed_targets
    export_by_address: dict[int, dict[str, Any]] = {}
    for row in target_exports:
        if row.get("found") is not True:
            raise ValueError(f"Ghidra function body missing for {row.get('requested')}")
        function = row.get("function") or {}
        entry = address(function.get("address"))
        if entry in export_by_address:
            raise ValueError(f"duplicate Ghidra function body export: 0x{entry:08x}")
        export_by_address[entry] = row
    if set(export_by_address) != confirmed_targets:
        raise ValueError("Ghidra instruction export does not match confirmed target function set")

    candidate_entries = unconfirmed_targets.intersection(function_by_address)
    candidate_export_by_address: dict[int, dict[str, Any]] = {}
    for row in unconfirmed_target_exports or []:
        if row.get("found") is not True:
            raise ValueError(f"Ghidra candidate function body missing for {row.get('requested')}")
        function = row.get("function") or {}
        entry = address(function.get("address"))
        if entry in candidate_export_by_address:
            raise ValueError(f"duplicate Ghidra candidate function export: 0x{entry:08x}")
        candidate_export_by_address[entry] = row
    if set(candidate_export_by_address) != candidate_entries:
        raise ValueError("candidate instruction export does not match unconfirmed Ghidra function entries")

    termination_counts: Counter[str] = Counter()
    recovered_functions = []
    total_instructions = 0
    total_pcode_instructions = 0
    for entry in sorted(confirmed_targets):
        function = function_by_address[entry]
        exported = export_by_address[entry]
        instructions = exported.get("instructions", [])
        rows = instruction_rows(exported)
        total_instructions += len(instructions)
        total_pcode_instructions += sum(bool(item.get("pcode")) for item in instructions)
        entry_index = next((i for i, row in enumerate(rows) if row[0] == entry), None)
        if entry_index is None:
            raise ValueError(f"Ghidra function entry instruction missing: 0x{entry:08x}")
        result = analyze_helper(rows, entry_index)
        termination_counts[result.get("termination", "unknown")] += 1
        recovered_functions.append(
            {
                "address": f"0x{entry:08x}",
                "ghidra_name": function.get("name"),
                "size": function.get("size"),
                "mnemonic_sha256": function.get("mnemonic_sha256"),
                "direct_unresolved_callsite_count": len(target_sites[entry]),
                "instruction_count": len(instructions),
                "helper_return_probe": {
                    "termination": result.get("termination"),
                    "instruction_count": result.get("instruction_count"),
                    "qualified_entry_argument_plus_0x374": bool(result.get("qualified")),
                    "return_argument_channel": result.get("return_argument_channel"),
                    "return_site": result.get("return_site"),
                },
            }
        )

    prior_addresses = {
        address((row.get("function") or {}).get("address"))
        for row in prior_exports
        if row.get("found") is True
    }
    all_target_exports = {**export_by_address, **candidate_export_by_address}
    all_target_addresses = set(all_target_exports)
    prior_instruction_counts = {
        address(row["function"]["address"]): int(row.get("instruction_count", 0))
        for row in prior_exports
        if row.get("found") is True
    }
    prior_pcode_counts = {
        address(row["function"]["address"]): sum(
            bool(item.get("pcode")) for item in row.get("instructions", [])
        )
        for row in prior_exports
        if row.get("found") is True
    }
    prior_by_address = {
        address(row["function"]["address"]): row
        for row in prior_exports
        if row.get("found") is True
    }
    for entry in prior_addresses & all_target_addresses:
        if prior_by_address[entry].get("instructions") != all_target_exports[entry].get("instructions"):
            raise ValueError(f"overlapping Ghidra function bodies differ: 0x{entry:08x}")
    prior_instruction_count = sum(
        prior_instruction_counts.values()
    )
    prior_pcode_instruction_count = sum(prior_pcode_counts.values())
    new_only_instruction_count = sum(
        len(all_target_exports[entry].get("instructions", []))
        for entry in all_target_addresses - prior_addresses
    )
    new_only_pcode_instruction_count = sum(
        sum(bool(item.get("pcode")) for item in all_target_exports[entry].get("instructions", []))
        for entry in all_target_addresses - prior_addresses
    )

    qualified_helpers = sum(
        row["helper_return_probe"]["qualified_entry_argument_plus_0x374"]
        for row in recovered_functions
    )
    candidate_termination_counts: Counter[str] = Counter()
    candidate_functions = []
    candidate_instruction_count = 0
    candidate_pcode_instruction_count = 0
    unconfirmed_site_counts = Counter(target for _, target in unresolved_callsites)
    for entry in sorted(candidate_entries):
        function = function_by_address[entry]
        exported = candidate_export_by_address[entry]
        instructions = exported.get("instructions", [])
        rows = instruction_rows(exported)
        candidate_instruction_count += len(instructions)
        candidate_pcode_instruction_count += sum(bool(item.get("pcode")) for item in instructions)
        entry_index = next((i for i, row in enumerate(rows) if row[0] == entry), None)
        if entry_index is None:
            raise ValueError(f"Ghidra candidate entry instruction missing: 0x{entry:08x}")
        result = analyze_helper(rows, entry_index)
        candidate_termination_counts[result.get("termination", "unknown")] += 1
        candidate_functions.append(
            {
                "address": f"0x{entry:08x}",
                "ghidra_name": function.get("name"),
                "size": function.get("size"),
                "mnemonic_sha256": function.get("mnemonic_sha256"),
                "unconfirmed_objdump_callsite_count": unconfirmed_site_counts[entry],
                "instruction_count": len(instructions),
                "helper_return_probe": {
                    "termination": result.get("termination"),
                    "instruction_count": result.get("instruction_count"),
                    "qualified_entry_argument_plus_0x374": bool(result.get("qualified")),
                    "return_argument_channel": result.get("return_argument_channel"),
                    "return_site": result.get("return_site"),
                },
            }
        )
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": executable_sha256,
            "retail_executable_md5": RETAIL_MD5,
            "ghidra_export_source_hashes": source_hashes,
        },
        "objdump_unresolved_direct_calls": {
            "callsite_count": len(set(unresolved_callsites)),
            "unique_target_count": len(unresolved_targets),
            "exact_ghidra_direct_callgraph_match_count": len(confirmed_sites),
            "unique_confirmed_target_function_count": len(confirmed_targets),
            "unmatched_callsite_count": len(set(unresolved_callsites)) - len(confirmed_sites),
            "unconfirmed_target_count": len(unconfirmed_targets),
            "unconfirmed_target_function_entry_count": len(candidate_entries),
            "exact_callgraph_matches": confirmed_sites,
            "unmatched_callsites": unmatched_sites,
            "unconfirmed_target_addresses": [
                f"0x{target:08x}" for target in sorted(unconfirmed_targets)
            ],
        },
        "function_body_recovery": {
            "instruction_export_format": "SHIFT.GhidraFunctionInstructions/2",
            "target_function_count": len(recovered_functions),
            "instruction_count": total_instructions,
            "pcode_instruction_count": total_pcode_instructions,
            "pcode_available_for_every_instruction": total_instructions == total_pcode_instructions,
            "instruction_export_sha256": target_export_sha256,
            "recovered_functions": recovered_functions,
            "helper_return_probe_termination_counts": dict(sorted(termination_counts.items())),
            "qualified_entry_argument_plus_0x374_function_count": qualified_helpers,
        },
        "inventory_only_function_body_candidates": {
            "callgraph_confirmed_callsite_count": 0,
            "function_entry_count": len(candidate_functions),
            "instruction_count": candidate_instruction_count,
            "pcode_instruction_count": candidate_pcode_instruction_count,
            "pcode_available_for_every_instruction": candidate_instruction_count == candidate_pcode_instruction_count,
            "instruction_export_sha256": unconfirmed_export_sha256,
            "helper_return_probe_termination_counts": dict(sorted(candidate_termination_counts.items())),
            "qualified_entry_argument_plus_0x374_function_count": sum(
                row["helper_return_probe"]["qualified_entry_argument_plus_0x374"]
                for row in candidate_functions
            ),
            "functions": candidate_functions,
        },
        "combined_function_instruction_exports": {
            "prior_export_sha256": prior_export_sha256,
            "prior_function_count": len(prior_addresses),
            "prior_instruction_count": prior_instruction_count,
            "prior_pcode_instruction_count": prior_pcode_instruction_count,
            "overlap_function_count": len(prior_addresses & all_target_addresses),
            "new_function_count": len(all_target_addresses - prior_addresses),
            "unique_function_count": len(prior_addresses | all_target_addresses),
            "unique_instruction_count": prior_instruction_count + new_only_instruction_count,
            "unique_pcode_instruction_count": prior_pcode_instruction_count + new_only_pcode_instruction_count,
        },
        "adjudication": {
            "confirmed_objdump_unresolved_direct_call_subset_recovered": True,
            "all_unresolved_direct_call_targets_classified": False,
            "helper_returned_materialized_address_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "p1_3_control_producer_complete": False,
            "automatic_function_renaming_performed": False,
        },
        "limits": [
            "Ghidra callgraph edge matches confirm only the listed direct callsite/target pairs; unmatched objdump calls and targets remain unresolved.",
            "The 96-instruction helper probe starts at each exact Ghidra function entry and stops at the first call, branch/trap, return, unsupported stack adjustment, or probe bound.",
            "A negative helper probe result does not exclude alternate control-flow paths, persisted return values, indirect callees, or other address-construction patterns.",
            "Exported assembly/P-code bodies do not by themselves establish function names, receiver identity, or manager+0x374 -> HDVehicle+0x4330 identity.",
        ],
        "next_step": "Continue the independent opaque/external manager-root search and exact manager+0x374 -> HDVehicle+0x4330 identity join; adjudicate slot2 only from that join.",
    }


def build(
    executable: Path,
    ghidra_export: Path,
    instruction_export: Path,
    unconfirmed_instruction_export: Path,
    prior_instruction_export: Path,
) -> dict[str, Any]:
    executable_sha256 = sha256(executable)
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT retail executable SHA-256: {executable_sha256}")
    manifest = json.loads((ghidra_export / "manifest.json").read_text(encoding="utf-8"))
    binary = json.loads((ghidra_export / "binary.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "SHIFT.GhidraEvidenceDatabase/1":
        raise ValueError("unsupported Ghidra evidence database format")
    if binary.get("executable_md5") != RETAIL_MD5:
        raise ValueError("Ghidra export does not match PC retail 1.02")
    source_files = ["manifest.json", "binary.json", "functions.jsonl", "callgraph.jsonl"]
    source_hashes = {name: sha256(ghidra_export / name) for name in source_files}

    rows = disassemble(executable)
    instruction_addresses = {row[0] for row in rows}
    unresolved_callsites = []
    for site, mnemonic, raw_operands in rows:
        mnemonic, operands, _ = normalize_prefixed_instruction(mnemonic, raw_operands)
        if mnemonic != "call":
            continue
        target = parse_direct_target(operands)
        if target is not None and target not in instruction_addresses:
            unresolved_callsites.append((site, target))

    return compose_report(
        unresolved_callsites,
        read_jsonl(ghidra_export / "callgraph.jsonl"),
        read_jsonl(ghidra_export / "functions.jsonl"),
        read_jsonl(instruction_export),
        read_jsonl(prior_instruction_export),
        source_hashes,
        sha256(instruction_export),
        sha256(prior_instruction_export),
        executable_sha256,
        read_jsonl(unconfirmed_instruction_export),
        sha256(unconfirmed_instruction_export),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("unconfirmed_instruction_export", type=Path)
    parser.add_argument("prior_instruction_export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(
            args.executable,
            args.ghidra_export,
            args.instruction_export,
            args.unconfirmed_instruction_export,
            args.prior_instruction_export,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"confirmed unresolved callsites: {report['objdump_unresolved_direct_calls']['exact_ghidra_direct_callgraph_match_count']}")
    print(f"recovered target functions: {report['function_body_recovery']['target_function_count']}")
    print(f"inventory-only function candidates: {report['inventory_only_function_body_candidates']['function_entry_count']}")
    print(f"new unique function bodies: {report['combined_function_instruction_exports']['new_function_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
