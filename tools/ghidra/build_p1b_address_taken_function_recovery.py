#!/usr/bin/env python3
"""Build hash-pinned evidence for bounded address-taken orphan function recovery."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.P1B.AddressTakenOrphanFunctionRecovery/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

FUNCTIONS = (
    {
        "entry": "0x00910aa5",
        "end": "0x00911394",
        "terminator": "RET",
        "tail_target": None,
        "previous": {"address": "0x00910aa4", "mnemonic": "RET", "target": None},
        "entry_data_reference_sources": ["0x009080a0", "0x0090296c"],
        "orphan_callsites": [
            {"address": "0x00910d62", "target": "0x009113b5"},
            {"address": "0x009112e7", "target": "0x009113b5"},
        ],
        "instruction_count": 703,
        "call_instruction_count": 26,
        "body_bytes": 2288,
        "body_sha256": "8d0dcdc80a86283c6d8c10881894eced65b326b1897c4e93f123919daaba02b6",
    },
    {
        "entry": "0x00a9a86e",
        "end": "0x00a9a873",
        "terminator": "JMP",
        "tail_target": "0x0092e065",
        "previous": {"address": "0x00a9a86d", "mnemonic": "RET", "target": None},
        "entry_data_reference_sources": ["0x00aa98dc"],
        "orphan_callsites": [],
        "instruction_count": 2,
        "call_instruction_count": 0,
        "body_bytes": 10,
        "body_sha256": "ab67469d1bf994dc09f572e70f516762513da2b4aedbf001005f01748bf7c88f",
    },
    {
        "entry": "0x00a9a878",
        "end": "0x00a9a88d",
        "terminator": "RET",
        "tail_target": None,
        "previous": {"address": "0x00a9a873", "mnemonic": "JMP", "target": "0x0092e065"},
        "entry_data_reference_sources": ["0x00aa98e0"],
        "orphan_callsites": [{"address": "0x00a9a87d", "target": "0x0092ba44"}],
        "instruction_count": 6,
        "call_instruction_count": 2,
        "body_bytes": 22,
        "body_sha256": "a300be326f8c70402c66a1221a43fb14d36e560614457b17b8ce1021e6f58568",
    },
)


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


def instruction_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        for instruction in row.get("instructions", []):
            address = str(instruction.get("address", "")).lower()
            if not address:
                continue
            prior = indexed.get(address)
            if prior is not None and prior != instruction:
                raise ValueError(f"conflicting instruction evidence at {address}")
            indexed[address] = instruction
    return indexed


def hex_address(value: Any) -> int:
    return int(str(value), 16)


def validate_body(
    spec: dict[str, Any],
    instructions_by_address: dict[str, dict[str, Any]],
    metadata_by_address: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entry = hex_address(spec["entry"])
    end = hex_address(spec["end"])
    body = [
        row for address, row in sorted(instructions_by_address.items(), key=lambda item: hex_address(item[0]))
        if entry <= hex_address(address) <= end
    ]
    if not body or body[0]["address"].lower() != spec["entry"] or body[-1]["address"].lower() != spec["end"]:
        raise ValueError(f"missing exact instruction boundary for {spec['entry']}")

    expected = entry
    body_bytes = bytearray()
    call_count = 0
    branch_count = 0
    pcode_count = 0
    for instruction in body:
        address = str(instruction["address"]).lower()
        encoded = bytes.fromhex(instruction["bytes"])
        if hex_address(address) != expected:
            raise ValueError(f"non-contiguous function body at {spec['entry']}")
        metadata = metadata_by_address.get(address)
        if metadata is None:
            raise ValueError(f"missing original-project metadata for {address}")
        if metadata.get("function_at") is not None or metadata.get("function_containing") is not None:
            raise ValueError(f"instruction already had an original-project owner: {address}")
        block = metadata.get("block") or {}
        if block.get("name") != ".text" or not block.get("execute"):
            raise ValueError(f"function instruction is outside executable .text: {address}")
        if not instruction.get("pcode"):
            raise ValueError(f"missing P-code for {address}")
        pcode_count += 1
        flow = str(instruction.get("flow_type", "")).upper()
        if "CALL" in flow:
            call_count += 1
        if "JUMP" in flow:
            branch_count += 1
            flows = [str(value).lower() for value in instruction.get("flows", []) if value]
            if not flows:
                raise ValueError(f"jump has no recorded destination at {address}")
            for target in flows:
                if entry <= hex_address(target) <= end:
                    continue
                if address == spec["end"] and target == spec.get("tail_target"):
                    continue
                raise ValueError(f"branch leaves bounded body at {address} -> {target}")
        expected += len(encoded)
        body_bytes.extend(encoded)

    if not body[-1].get("mnemonic", "").upper().startswith(spec["terminator"]):
        raise ValueError(f"unexpected terminal instruction for {spec['entry']}")
    digest = hashlib.sha256(body_bytes).hexdigest()
    if (
        len(body) != spec["instruction_count"]
        or pcode_count != spec["instruction_count"]
        or len(body_bytes) != spec["body_bytes"]
        or call_count != spec["call_instruction_count"]
        or digest != spec["body_sha256"]
    ):
        raise ValueError(f"function body count/hash drift at {spec['entry']}")
    return {
        "instructions": body,
        "instruction_count": len(body),
        "pcode_instruction_count": pcode_count,
        "call_instruction_count": call_count,
        "branch_instruction_count": branch_count,
        "body_bytes": len(body_bytes),
        "body_sha256": digest,
    }


def verify_entry_reference(spec: dict[str, Any], reference_row: dict[str, Any]) -> list[dict[str, Any]]:
    expected_sources = {str(source).lower() for source in spec["entry_data_reference_sources"]}
    matching = [
        row for row in reference_row.get("references", [])
        if str(row.get("type", "")).upper() == "DATA"
        and str(row.get("from", "")).lower() in expected_sources
    ]
    if {str(row.get("from", "")).lower() for row in matching} != expected_sources:
        raise ValueError(f"missing exact address-taken data reference for {spec['entry']}")
    return matching


def verify_preceding_boundary(
    spec: dict[str, Any], instructions_by_address: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    previous_spec = spec["previous"]
    previous = instructions_by_address.get(previous_spec["address"].lower())
    if previous is None:
        raise ValueError(f"missing preceding instruction for {spec['entry']}")
    previous_bytes = bytes.fromhex(previous["bytes"])
    if hex_address(previous["address"]) + len(previous_bytes) != hex_address(spec["entry"]):
        raise ValueError(f"entry does not follow its terminal instruction: {spec['entry']}")
    if not str(previous.get("mnemonic", "")).upper().startswith(previous_spec["mnemonic"]):
        raise ValueError(f"unexpected preceding boundary for {spec['entry']}")
    targets = [str(value).lower() for value in previous.get("flows", []) if value]
    if previous_spec.get("target") and targets != [previous_spec["target"]]:
        raise ValueError(f"preceding transfer target drift for {spec['entry']}")
    return previous


def compose_report(
    executable_sha256: str,
    manifest: dict[str, Any],
    binary: dict[str, Any],
    previous_report: dict[str, Any],
    special_slice_rows: list[dict[str, Any]],
    boundary_slice_rows: list[dict[str, Any]],
    entry_metadata_rows: list[dict[str, Any]],
    entry_reference_rows: list[dict[str, Any]],
    original_body_metadata_rows: list[dict[str, Any]],
    original_target_reference_rows: list[dict[str, Any]],
    recovered_function_rows: list[dict[str, str]],
    recovered_instruction_rows: list[dict[str, Any]],
    recovered_target_reference_rows: list[dict[str, Any]],
    source_hashes: dict[str, str],
    copy_project_name: str,
    function_specs: tuple[dict[str, Any], ...] = FUNCTIONS,
) -> dict[str, Any]:
    if executable_sha256 != RETAIL_SHA256 or binary.get("executable_md5") != RETAIL_MD5:
        raise ValueError("unexpected SHIFT retail executable")
    if manifest.get("format") != "SHIFT.GhidraEvidenceDatabase/1":
        raise ValueError("unexpected Ghidra evidence database format")

    prior_unresolved = previous_report["unresolved_callsite_reconciliation"]
    exact_calls = prior_unresolved["confirmed_orphan_call_sites"]
    if len(exact_calls) != prior_unresolved["exact_ghidra_call_instruction_and_reference_count"]:
        raise ValueError("prior exact orphan callsite count drift")
    exact_by_site = {str(row["callsite"]).lower(): row for row in exact_calls}
    if len(exact_by_site) != len(exact_calls):
        raise ValueError("duplicate exact orphan callsite in prior evidence")

    prior_wrappers = previous_report["recovered_orphan_wrapper_functions"]["functions"]
    prior_wrapper_sites = {str(row["caller_callsite"]).lower() for row in prior_wrappers}
    instruction_rows = instruction_index(special_slice_rows)
    boundary_instructions = instruction_index(boundary_slice_rows)
    original_metadata = index_rows(original_body_metadata_rows, "requested")
    entry_metadata = index_rows(entry_metadata_rows, "requested")
    entry_references = index_rows(entry_reference_rows, "requested")
    original_target_references = index_rows(original_target_reference_rows, "requested")
    recovered_exports = index_rows(
        [row for row in recovered_instruction_rows if row.get("found") is True], "requested"
    )
    recovered_target_references = index_rows(recovered_target_reference_rows, "requested")
    recovered_summaries = {str(row["entry"]).lower(): row for row in recovered_function_rows}
    if len(recovered_summaries) != len(recovered_function_rows):
        raise ValueError("duplicate recovered function summary")
    if set(recovered_summaries) != {str(spec["entry"]).lower() for spec in function_specs}:
        raise ValueError("recovered function summary entries do not match the plan")

    recovered_functions = []
    newly_owned_sites: set[str] = set()
    total_instructions = total_pcode = total_bytes = 0
    for spec in function_specs:
        entry = str(spec["entry"]).lower()
        entry_row = entry_metadata.get(entry)
        if entry_row is None or entry_row.get("function_at") is not None or entry_row.get("function_containing") is not None:
            raise ValueError(f"candidate entry already had an original-project owner: {entry}")
        if (entry_row.get("block") or {}).get("name") != ".text" or not (entry_row.get("block") or {}).get("execute"):
            raise ValueError(f"candidate entry is outside executable .text: {entry}")
        if spec.get("tail_target"):
            tail_metadata = entry_metadata.get(str(spec["tail_target"]).lower())
            if (
                tail_metadata is None
                or tail_metadata.get("function_at") is not None
                or tail_metadata.get("function_containing") is not None
            ):
                raise ValueError(f"tail-transfer destination unexpectedly has a Ghidra function owner: {spec['entry']}")

        previous = verify_preceding_boundary(spec, boundary_instructions)
        body = validate_body(spec, instruction_rows, original_metadata)
        entry_refs = verify_entry_reference(spec, entry_references.get(entry, {}))
        export = recovered_exports.get(entry)
        if export is None:
            raise ValueError(f"missing recovered Ghidra function export: {entry}")
        function = export.get("function") or {}
        summary = recovered_summaries[entry]
        if (
            str(function.get("address", "")).lower() != entry
            or function.get("name") != summary.get("function_name")
            or int(function.get("size", 0)) != body["body_bytes"]
            or export.get("instruction_count") != body["instruction_count"]
        ):
            raise ValueError(f"recovered function export drift at {entry}")
        exported = export.get("instructions") or []
        if [(x.get("address", "").lower(), x.get("bytes")) for x in exported] != [
            (x["address"].lower(), x["bytes"]) for x in body["instructions"]
        ]:
            raise ValueError(f"recovered function body differs from original Ghidra instructions: {entry}")
        if sum(bool(x.get("pcode")) for x in exported) != body["instruction_count"]:
            raise ValueError(f"recovered function is missing P-code: {entry}")
        if (
            str(summary.get("body_sha256")) != body["body_sha256"]
            or int(summary.get("body_bytes", 0)) != body["body_bytes"]
            or int(summary.get("instruction_count", 0)) != body["instruction_count"]
            or int(summary.get("pcode_instruction_count", 0)) != body["pcode_instruction_count"]
        ):
            raise ValueError(f"recovery plan summary drift at {entry}")

        sites = []
        for call in spec["orphan_callsites"]:
            site = str(call["address"]).lower()
            target = str(call["target"]).lower()
            original = exact_by_site.get(site)
            if original is None or str(original.get("target_function", "")).lower() != target:
                raise ValueError(f"callsite is not in the confirmed orphan set: {site}")
            target_row = original_target_references.get(target)
            if target_row is None or not any(
                str(ref.get("from", "")).lower() == site
                and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
                and str(ref.get("instruction", "")).lower().endswith(target)
                for ref in target_row.get("references", [])
            ):
                raise ValueError(f"original Ghidra call reference is missing: {site} -> {target}")
            if site in newly_owned_sites or site in prior_wrapper_sites:
                raise ValueError(f"duplicate recovered orphan callsite: {site}")
            recovered_refs = [
                ref for ref in recovered_target_references.get(target, {}).get("references", [])
                if str(ref.get("from", "")).lower() == site
                and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
                and str(ref.get("function_address", "")).lower() == entry
                and str(ref.get("function_name", "")) == function.get("name")
            ]
            if len(recovered_refs) != 1:
                raise ValueError(f"isolated copy did not assign exact caller owner: {site}")
            newly_owned_sites.add(site)
            sites.append({
                "callsite": site,
                "target_function": target,
                "instruction": original.get("instruction"),
            })

        recovered_functions.append({
            "address": entry,
            "name": function.get("name"),
            "end": str(spec["end"]).lower(),
            "preceding_instruction": {
                "address": str(previous["address"]).lower(),
                "mnemonic": previous.get("mnemonic"),
                "flow_target": (previous.get("flows") or [None])[0],
            },
            "terminator": body["instructions"][-1].get("text"),
            "terminator_target": spec.get("tail_target"),
            "instruction_count": body["instruction_count"],
            "pcode_instruction_count": body["pcode_instruction_count"],
            "call_instruction_count": body["call_instruction_count"],
            "branch_instruction_count": body["branch_instruction_count"],
            "body_bytes": body["body_bytes"],
            "body_sha256": body["body_sha256"],
            "entry_data_references": [
                {"from": ref.get("from"), "type": ref.get("type"), "source": ref.get("source"), "instruction": ref.get("instruction")}
                for ref in entry_refs
            ],
            "orphan_callsites": sites,
        })
        total_instructions += body["instruction_count"]
        total_pcode += body["pcode_instruction_count"]
        total_bytes += body["body_bytes"]

    if not prior_wrapper_sites.issubset(exact_by_site):
        raise ValueError("prior recovered wrapper site is not an exact Ghidra orphan call")
    exact_call_count = len(exact_calls)
    previously_owned = len(prior_wrapper_sites)
    remaining = exact_call_count - previously_owned - len(newly_owned_sites)
    prior_corpus = previous_report["combined_function_instruction_exports"]
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
            "ghidra_export_source_hashes": {name: value for name, value in sorted(source_hashes.items())},
        },
        "recovered_address_taken_functions": {
            "function_count": len(recovered_functions),
            "instruction_count": total_instructions,
            "pcode_instruction_count": total_pcode,
            "body_byte_count": total_bytes,
            "all_instruction_bytes_match_original_project": True,
            "all_body_instructions_unowned_in_original_project": True,
            "all_entries_have_exact_data_references": True,
            "all_orphan_callsites_have_exact_copy_owners": True,
            "functions": recovered_functions,
        },
        "unresolved_callsite_reconciliation": {
            "source_exact_orphan_callsite_count": exact_call_count,
            "prior_wrapper_owned_callsite_count": previously_owned,
            "newly_owned_callsite_count": len(newly_owned_sites),
            "remaining_exact_orphan_callsite_count": remaining,
            "newly_owned_callsites": sorted(newly_owned_sites),
        },
        "combined_function_instruction_exports": {
            "previous_unique_function_count": prior_corpus["unique_function_count"],
            "new_function_count": len(recovered_functions),
            "unique_function_count": prior_corpus["unique_function_count"] + len(recovered_functions),
            "previous_unique_instruction_count": prior_corpus["unique_instruction_count"],
            "new_instruction_count": total_instructions,
            "unique_instruction_count": prior_corpus["unique_instruction_count"] + total_instructions,
            "previous_unique_pcode_instruction_count": prior_corpus["unique_pcode_instruction_count"],
            "new_pcode_instruction_count": total_pcode,
            "unique_pcode_instruction_count": prior_corpus["unique_pcode_instruction_count"] + total_pcode,
        },
        "adjudication": {
            "caller_functions_added_to_original_project": False,
            "caller_functions_added_to_separate_project_copy": True,
            "automatic_semantic_renaming_performed": False,
            "p1_3_control_producer_complete": False,
        },
        "limits": [
            f"{remaining} exact orphan direct-call sites still have no recovered caller owner.",
            "The 0x00a9a86e body ends in a direct JMP to 0x0092e065, which remains an unowned code address.",
            "No game-specific semantic names or behavior claims were added.",
        ],
    }


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def build(args: argparse.Namespace) -> dict[str, Any]:
    if sha256(args.executable) != RETAIL_SHA256:
        raise ValueError("unexpected SHIFT retail executable SHA-256")
    manifest_path = args.ghidra_export / "manifest.json"
    binary_path = args.ghidra_export / "binary.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binary = json.loads(binary_path.read_text(encoding="utf-8"))
    raw = args.raw_dir
    previous_report = json.loads(args.previous_report.read_text(encoding="utf-8"))

    files = {
        "previous_recovery_report": args.previous_report,
        "special_pointer_slices": raw / "special-pointer-candidates.jsonl",
        "entry_boundary_slices": raw / "function-910aa5-entry-context.jsonl",
        "expanded_orphan_callsite_slices": raw / "orphan-callsite-slices-expanded-0x500.jsonl",
        "entry_metadata": raw / "orphan-boundary-candidate-metadata-expanded.jsonl",
        "entry_references": raw / "orphan-boundary-candidate-references-expanded.jsonl",
        "adjacent_entry_metadata": raw / "adjacent-tailcall-candidates-metadata.jsonl",
        "adjacent_entry_references": raw / "adjacent-tailcall-candidates-references.jsonl",
        "large_body_original_metadata": raw / "function-910aa5-full-address-metadata.jsonl",
        "small_body_original_metadata": raw / "address-taken-small-body-original-metadata.jsonl",
        "original_target_references": raw / "target-references-mapped.jsonl",
        "recovered_function_plan": raw / "address-taken-recovered-functions.tsv",
        "recovered_function_instructions": raw / "address-taken-recovered-function-instructions.jsonl",
        "recovered_target_references": raw / "address-taken-recovered-target-references.jsonl",
        "manifest.json": manifest_path,
        "binary.json": binary_path,
        "functions.jsonl": args.ghidra_export / "functions.jsonl",
        "callgraph.jsonl": args.ghidra_export / "callgraph.jsonl",
    }
    source_hashes = {name: sha256(path) for name, path in files.items()}
    source_hashes["recovery_script.java"] = sha256(
        Path(__file__).with_name("RecoverP1bAddressTakenFunctions.java")
    )
    source_hashes["report_builder.py"] = sha256(Path(__file__))

    entry_metadata_rows = [
        row for row in read_jsonl(files["entry_metadata"])
        if str(row.get("requested", "")).lower() == "0x00910aa5"
    ] + read_jsonl(files["adjacent_entry_metadata"])
    entry_reference_rows = [
        row for row in read_jsonl(files["entry_references"])
        if str(row.get("requested", "")).lower() == "0x00910aa5"
    ] + read_jsonl(files["adjacent_entry_references"])
    body_metadata_rows = read_jsonl(files["large_body_original_metadata"]) + read_jsonl(files["small_body_original_metadata"])
    boundary_slice_rows = read_jsonl(files["entry_boundary_slices"]) + read_jsonl(files["expanded_orphan_callsite_slices"])
    return compose_report(
        sha256(args.executable),
        manifest,
        binary,
        previous_report,
        read_jsonl(files["special_pointer_slices"]),
        boundary_slice_rows,
        entry_metadata_rows,
        entry_reference_rows,
        body_metadata_rows,
        read_jsonl(files["original_target_references"]),
        read_tsv(files["recovered_function_plan"]),
        read_jsonl(files["recovered_function_instructions"]),
        read_jsonl(files["recovered_target_references"]),
        source_hashes,
        args.copy_project_name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--previous-report", type=Path, required=True)
    parser.add_argument("--copy-project-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    recovered = report["recovered_address_taken_functions"]
    counts = report["combined_function_instruction_exports"]
    print(f"recovered address-taken orphan functions: {recovered['function_count']}")
    print(f"new instructions/P-code rows: {recovered['instruction_count']}/{recovered['pcode_instruction_count']}")
    print(f"combined unique function bodies: {counts['unique_function_count']}")
    print(f"remaining exact orphan callsites: {report['unresolved_callsite_reconciliation']['remaining_exact_orphan_callsite_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
