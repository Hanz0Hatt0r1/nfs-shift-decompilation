#!/usr/bin/env python3
"""Build compact evidence for exact orphan call/return wrapper recovery."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.P1B.OrphanWrapperFunctionRecovery/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def index_rows(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed = {str(row[key]).lower(): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate {key} in evidence rows")
    return indexed


def hex_address(value: Any) -> int:
    return int(str(value), 16)


def direct_call_ref(references: list[dict[str, Any]], site: str, target: str) -> dict[str, Any] | None:
    matches = [
        row for row in references
        if str(row.get("from", "")).lower() == site.lower()
        and str(row.get("type", "")).upper() == "UNCONDITIONAL_CALL"
        and str(row.get("instruction", "")).lower().endswith(target.lower())
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate exact call references at {site} -> {target}")
    return matches[0] if matches else None


def compose_report(
    executable_sha256: str,
    previous_report: dict[str, Any],
    address_metadata_rows: list[dict[str, Any]],
    target_reference_rows: list[dict[str, Any]],
    callsite_slice_rows: list[dict[str, Any]],
    candidate_entry_metadata_rows: list[dict[str, Any]],
    candidate_entry_reference_rows: list[dict[str, Any]],
    restored_function_rows: list[dict[str, str]],
    restored_instruction_rows: list[dict[str, Any]],
    restored_target_reference_rows: list[dict[str, Any]],
    source_hashes: dict[str, str],
    copy_project_name: str,
) -> dict[str, Any]:
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError("unexpected SHIFT retail executable SHA-256")

    unresolved = previous_report["objdump_unresolved_direct_calls"]
    unmatched = unresolved["unmatched_callsites"]
    metadata = index_rows(address_metadata_rows, "requested")
    target_references = index_rows(target_reference_rows, "requested")
    candidate_metadata = index_rows(candidate_entry_metadata_rows, "requested")
    candidate_references = index_rows(candidate_entry_reference_rows, "requested")
    restored_instructions = index_rows(
        [row for row in restored_instruction_rows if row.get("found") is True],
        "requested",
    )
    slice_instructions: dict[str, dict[str, Any]] = {}
    for row in callsite_slice_rows:
        for instruction in row.get("instructions", []):
            address = str(instruction.get("address", "")).lower()
            if address:
                if address in slice_instructions and slice_instructions[address] != instruction:
                    raise ValueError(f"conflicting Ghidra instruction slices at {address}")
                slice_instructions[address] = instruction

    verified_calls = []
    unrecognized_calls = []
    for site_row in unmatched:
        site = str(site_row["callsite"]).lower()
        target = str(site_row["target"]).lower()
        site_meta = metadata.get(site)
        target_meta = metadata.get(target)
        if site_meta is None or target_meta is None:
            raise ValueError(f"missing Ghidra address metadata for {site} or {target}")
        instruction = slice_instructions.get(site)
        call_ref_row = target_references.get(target)
        refs = call_ref_row.get("references", []) if call_ref_row else []
        exact_ref = direct_call_ref(refs, site, target)
        is_call = str(site_meta.get("instruction_mnemonic") or "").upper() == "CALL"
        if is_call:
            if instruction is None or str(instruction.get("mnemonic", "")).upper() != "CALL":
                raise ValueError(f"instruction-slice export did not confirm CALL at {site}")
            slice_ref = any(
                str(ref.get("to", "")).lower() == target
                and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
                for ref in instruction.get("references", [])
            )
            if exact_ref is None or not slice_ref:
                raise ValueError(f"Ghidra did not confirm exact CALL reference at {site} -> {target}")
            if site_meta.get("function_containing") is not None:
                raise ValueError(f"orphan caller site unexpectedly has a function owner: {site}")
            function = target_meta.get("function_at")
            if not function or str(function.get("entry", "")).lower() != target:
                raise ValueError(f"direct CALL target is not an exact function entry: {target}")
            verified_calls.append({
                "callsite": site,
                "target_function": target,
                "target_function_name": function.get("name"),
                "caller_function": None,
                "instruction": instruction.get("text"),
                "instruction_bytes": instruction.get("bytes"),
            })
        else:
            if instruction is not None or exact_ref is not None:
                raise ValueError(f"non-instruction site has Ghidra instruction/reference evidence: {site}")
            if site_meta.get("instruction_mnemonic") is not None:
                raise ValueError(f"unmatched callsite resolves to a non-CALL instruction: {site}")
            unrecognized_calls.append({
                "callsite": site,
                "objdump_target": target,
                "instruction_defined_by_ghidra": False,
                "function_containing": site_meta.get("function_containing"),
                "target_in_program_memory": target_meta.get("block") is not None,
            })

    if len(verified_calls) + len(unrecognized_calls) != len(unmatched):
        raise ValueError("unresolved callsite reconciliation is incomplete")

    function_rows_by_entry = {
        str(row["entry"]).lower(): row for row in restored_function_rows
    }
    if len(function_rows_by_entry) != len(restored_function_rows):
        raise ValueError("duplicate recovered function entry")
    if set(function_rows_by_entry) != set(candidate_metadata):
        raise ValueError("candidate entry metadata does not match restored function entries")

    restored_target_refs = index_rows(restored_target_reference_rows, "requested")
    recovered_functions = []
    total_instructions = 0
    total_pcode = 0
    total_bytes = 0
    for entry, summary in sorted(function_rows_by_entry.items()):
        entry_meta = candidate_metadata[entry]
        if entry_meta.get("function_at") is not None or entry_meta.get("function_containing") is not None:
            raise ValueError(f"candidate function entry was already owned in original project: {entry}")
        block = entry_meta.get("block") or {}
        if not block.get("execute") or block.get("name") != ".text":
            raise ValueError(f"candidate entry is not in executable .text: {entry}")

        export = restored_instructions.get(entry)
        if export is None:
            raise ValueError(f"missing restored function instruction export: {entry}")
        function = export.get("function") or {}
        instructions = export.get("instructions") or []
        if str(function.get("address", "")).lower() != entry:
            raise ValueError(f"restored function export address drift: {entry}")
        if export.get("instruction_count") != len(instructions) or not instructions:
            raise ValueError(f"restored instruction count mismatch: {entry}")
        if function.get("name") != summary["function_name"]:
            raise ValueError(f"restored function name drift: {entry}")
        if int(function.get("size", 0)) != int(summary["body_bytes"]):
            raise ValueError(f"restored function size drift: {entry}")

        expected = hex_address(entry)
        callsites = []
        pcode_count = 0
        instruction_bytes = bytearray()
        for instruction in instructions:
            address = hex_address(instruction["address"])
            if address != expected:
                raise ValueError(f"non-contiguous recovered body at {entry}")
            encoded = bytes.fromhex(instruction["bytes"])
            instruction_bytes.extend(encoded)
            expected = address + len(encoded)
            pcode_count += bool(instruction.get("pcode"))
            mnemonic = str(instruction.get("mnemonic", "")).upper()
            if mnemonic.startswith(("J", "LOOP")):
                raise ValueError(f"branch in bounded wrapper body at {instruction['address']}")
            if mnemonic == "CALL":
                refs = [
                    ref for ref in instruction.get("references", [])
                    if str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
                ]
                if len(refs) != 1:
                    raise ValueError(f"expected one direct call in wrapper body: {entry}")
                callsites.append((str(instruction["address"]).lower(), str(refs[0]["to"]).lower()))
        if pcode_count != len(instructions):
            raise ValueError(f"missing P-code in recovered body: {entry}")
        if len(callsites) != 1:
            raise ValueError(f"expected exactly one call in recovered body: {entry}")
        callsite, target = callsites[0]
        if callsite != str(summary["callsite"]).lower() or target != str(summary["target"]).lower():
            raise ValueError(f"recovered callsite/target drift: {entry}")
        if str(instructions[-1]["address"]).lower() != str(summary["return"]).lower() or not str(instructions[-1].get("mnemonic", "")).upper().startswith("RET"):
            raise ValueError(f"wrapper body is not closed by its exact RET: {entry}")

        target_row = restored_target_refs.get(target)
        exact_owner_ref = [
            ref for ref in (target_row or {}).get("references", [])
            if str(ref.get("from", "")).lower() == callsite
            and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
            and str(ref.get("function_address", "")).lower() == entry
            and str(ref.get("function_name", "")) == summary["function_name"]
        ]
        if len(exact_owner_ref) != 1:
            raise ValueError(f"recovered copy does not assign callsite to exact function owner: {entry}")

        xrefs = candidate_references[entry].get("references", [])
        pointer_xrefs = [ref for ref in xrefs if str(ref.get("type", "")).upper() == "DATA"]
        entry_literal = f"0x{hex_address(entry):x}"
        if not pointer_xrefs or not any(entry_literal in str(ref.get("instruction", "")).lower() for ref in pointer_xrefs):
            raise ValueError(f"missing exact stored-address reference to function entry: {entry}")

        body_hash = hashlib.sha256(instruction_bytes).hexdigest()
        recovered_functions.append({
            "address": entry,
            "name": summary["function_name"],
            "entry_instruction": entry_meta.get("instruction_mnemonic"),
            "caller_callsite": callsite,
            "callee_function": target,
            "return_instruction": str(instructions[-1]["address"]).lower(),
            "body_bytes": len(instruction_bytes),
            "instruction_count": len(instructions),
            "pcode_instruction_count": pcode_count,
            "instruction_bytes_sha256": body_hash,
            "entry_data_reference_count": len(pointer_xrefs),
            "entry_data_references": [
                {"from": ref.get("from"), "instruction": ref.get("instruction"), "source": ref.get("source")}
                for ref in pointer_xrefs
            ],
        })
        total_instructions += len(instructions)
        total_pcode += pcode_count
        total_bytes += len(instruction_bytes)

    unique_confirmed_callees = {row["target_function"] for row in verified_calls}
    inventory_only_targets = {
        str(row["address"]).lower()
        for row in previous_report.get("inventory_only_function_body_candidates", {}).get("functions", [])
    }
    newly_callsite_confirmed_targets = unique_confirmed_callees & inventory_only_targets
    previous_corpus = previous_report["combined_function_instruction_exports"]
    noninstruction_with_owner = sum(row["function_containing"] is not None for row in unrecognized_calls)
    targets_outside_memory = sum(not row["target_in_program_memory"] for row in unrecognized_calls)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": executable_sha256,
            "retail_executable_md5": RETAIL_MD5,
            "original_ghidra_project_modified": False,
            "function_recovery_copy_project": copy_project_name,
            "ghidra_export_source_hashes": {
                name: sha256 for name, sha256 in sorted(source_hashes.items())
            },
        },
        "unresolved_callsite_reconciliation": {
            "source_unmatched_callsite_count": len(unmatched),
            "exact_ghidra_call_instruction_and_reference_count": len(verified_calls),
            "exact_callsite_caller_function_owner_count_before_recovery": 0,
            "callsite_addresses_without_ghidra_instruction_count": len(unrecognized_calls),
            "noninstruction_site_with_existing_function_owner_count": noninstruction_with_owner,
            "unrecognized_targets_outside_program_memory_count": targets_outside_memory,
            "unique_exact_callee_function_count": len(unique_confirmed_callees),
            "previously_inventory_only_callee_function_count_now_callsite_confirmed": len(newly_callsite_confirmed_targets),
            "confirmed_orphan_call_sites": verified_calls,
            "call_sites_without_ghidra_instruction": unrecognized_calls,
        },
        "recovered_orphan_wrapper_functions": {
            "function_count": len(recovered_functions),
            "instruction_count": total_instructions,
            "pcode_instruction_count": total_pcode,
            "body_byte_count": total_bytes,
            "all_function_bodies_are_contiguous_one_call_return_wrappers": True,
            "all_entries_have_exact_data_references": True,
            "all_callsites_have_function_owners_in_copy": True,
            "functions": recovered_functions,
        },
        "combined_function_instruction_exports": {
            "previous_unique_function_count": previous_corpus["unique_function_count"],
            "new_function_count": len(recovered_functions),
            "unique_function_count": previous_corpus["unique_function_count"] + len(recovered_functions),
            "previous_unique_instruction_count": previous_corpus["unique_instruction_count"],
            "new_instruction_count": total_instructions,
            "unique_instruction_count": previous_corpus["unique_instruction_count"] + total_instructions,
            "previous_unique_pcode_instruction_count": previous_corpus["unique_pcode_instruction_count"],
            "new_pcode_instruction_count": total_pcode,
            "unique_pcode_instruction_count": previous_corpus["unique_pcode_instruction_count"] + total_pcode,
        },
        "adjudication": {
            "caller_functions_added_to_original_project": False,
            "caller_functions_added_to_separate_project_copy": True,
            "automatic_semantic_renaming_performed": False,
            "p1_3_control_producer_complete": False,
        },
        "limits": [
            "All 60 caller sites are exact Ghidra CALL instructions and unconditional references, but had no caller function owner in the original project.",
            "The 15 recovered wrappers use only exact contiguous instruction boundaries, one direct CALL, a terminal RET, and an exact stored-address reference at the entry.",
            "The remaining orphan direct-call sites are not promoted to function bodies without the same boundary and entry-reference evidence.",
        ],
        "next_step": "Apply the same bounded boundary and entry-reference screen to the remaining orphan direct-call sites; preserve the original project and fail closed on ambiguous bodies.",
    }


def read_recovered_functions(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    required = {"entry", "callsite", "target", "return", "function_name", "body_bytes", "instruction_count"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("restored function summary has an unexpected TSV header")
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    executable_sha256 = sha256(args.executable)
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT retail executable SHA-256: {executable_sha256}")
    manifest = json.loads((args.ghidra_export / "manifest.json").read_text(encoding="utf-8"))
    binary = json.loads((args.ghidra_export / "binary.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "SHIFT.GhidraEvidenceDatabase/1" or binary.get("executable_md5") != RETAIL_MD5:
        raise ValueError("Ghidra export does not match PC retail 1.02")
    input_files = {
        "previous_recovery_report": args.previous_report,
        "address_metadata": args.address_metadata,
        "target_references": args.target_references,
        "callsite_slices": args.callsite_slices,
        "candidate_entry_metadata": args.candidate_entry_metadata,
        "candidate_entry_references": args.candidate_entry_references,
        "restored_functions_tsv": args.restored_functions_tsv,
        "restored_function_instructions": args.restored_function_instructions,
        "restored_target_references": args.restored_target_references,
    }
    source_hashes = {
        name: sha256(path) for name, path in input_files.items()
    }
    for name in ("manifest.json", "binary.json", "functions.jsonl", "callgraph.jsonl"):
        source_hashes[name] = sha256(args.ghidra_export / name)
    return compose_report(
        executable_sha256,
        json.loads(args.previous_report.read_text(encoding="utf-8")),
        read_jsonl(args.address_metadata),
        read_jsonl(args.target_references),
        read_jsonl(args.callsite_slices),
        read_jsonl(args.candidate_entry_metadata),
        read_jsonl(args.candidate_entry_references),
        read_recovered_functions(args.restored_functions_tsv),
        read_jsonl(args.restored_function_instructions),
        read_jsonl(args.restored_target_references),
        source_hashes,
        args.copy_project_name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("previous_report", type=Path)
    parser.add_argument("address_metadata", type=Path)
    parser.add_argument("target_references", type=Path)
    parser.add_argument("callsite_slices", type=Path)
    parser.add_argument("candidate_entry_metadata", type=Path)
    parser.add_argument("candidate_entry_references", type=Path)
    parser.add_argument("restored_functions_tsv", type=Path)
    parser.add_argument("restored_function_instructions", type=Path)
    parser.add_argument("restored_target_references", type=Path)
    parser.add_argument("--copy-project-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = report["recovered_orphan_wrapper_functions"]
    print(f"recovered caller wrapper functions: {summary['function_count']}")
    print(f"new P-code instructions: {summary['pcode_instruction_count']}")
    print(f"combined unique function bodies: {report['combined_function_instruction_exports']['unique_function_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
