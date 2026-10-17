#!/usr/bin/env python3
"""Build hash-pinned evidence for the second P1B address-taken recovery batch."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.P1B.AddressTakenOrphanFunctionRecoveryBatch2/1"
PLAN_FORMAT = "SHIFT.P1B.OrphanAddressTakenFunctionRecoveryPlan/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


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


def number(value: Any) -> int:
    return int(str(value), 16)


def _flow_targets(instruction: dict[str, Any]) -> list[str]:
    return [str(value).lower() for value in instruction.get("flows", []) if value]


def validate_body(
    spec: dict[str, Any],
    instructions_by_address: dict[str, dict[str, Any]],
    metadata_by_address: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entry = number(spec["entry"])
    end = number(spec["end"])
    body = [instructions_by_address[str(address).lower()] for address in spec["body_instruction_addresses"]]
    if not body or body[0]["address"].lower() != str(spec["entry"]).lower():
        raise ValueError(f"missing exact instruction boundary for {spec['entry']}")

    expected = entry
    body_bytes = bytearray()
    body_addresses = {str(row["address"]).lower() for row in body}
    external_transfers = {
        str(row["at"]).lower(): str(row["target"]).lower()
        for row in spec.get("external_tail_transfers", [])
    }
    call_count = branch_count = pcode_count = 0
    for instruction in body:
        address = str(instruction["address"]).lower()
        encoded = bytes.fromhex(instruction["bytes"])
        if number(address) != expected:
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
        call_count += "CALL" in flow
        branch_count += "JUMP" in flow
        targets = _flow_targets(instruction)
        if "JUMP" in flow:
            if not targets:
                raise ValueError(f"jump has no recorded destination at {address}")
            for target in targets:
                if target in body_addresses:
                    continue
                if address == str(spec["end"]).lower() and target == str(spec.get("terminal_target") or "").lower():
                    continue
                raise ValueError(f"branch leaves bounded body at {address} -> {target}")
        elif flow == "CALL_TERMINATOR":
            if external_transfers.get(address) is None or targets != [external_transfers[address]]:
                raise ValueError(f"unrecorded tail transfer at {address}")
        expected += len(encoded)
        body_bytes.extend(encoded)

    if number(str(body[-1]["address"])) != end:
        raise ValueError(f"unexpected terminal instruction address for {spec['entry']}")
    if not str(body[-1].get("mnemonic", "")).upper().startswith(str(spec["terminator"]).upper()):
        raise ValueError(f"unexpected terminal instruction for {spec['entry']}")
    if spec.get("terminal_target"):
        if _flow_targets(body[-1]) != [str(spec["terminal_target"]).lower()]:
            raise ValueError(f"terminal transfer target drift at {spec['entry']}")
    digest = hashlib.sha256(body_bytes).hexdigest()
    facts = {
        "instructions": body,
        "instruction_count": len(body),
        "pcode_instruction_count": pcode_count,
        "call_instruction_count": call_count,
        "branch_instruction_count": branch_count,
        "body_bytes": len(body_bytes),
        "body_sha256": digest,
    }
    for key in ("instruction_count", "pcode_instruction_count", "call_instruction_count", "branch_instruction_count", "body_bytes", "body_sha256"):
        if facts[key] != spec[key]:
            raise ValueError(f"function body {key} drift at {spec['entry']}")

    reachable = {str(spec["entry"]).lower()}
    pending = [str(spec["entry"]).lower()]
    by_address = {str(row["address"]).lower(): row for row in body}
    while pending:
        instruction = by_address[pending.pop()]
        flow = str(instruction.get("flow_type", "")).upper()
        successors: list[str] = []
        if "CONDITIONAL_JUMP" in flow:
            successors.extend(_flow_targets(instruction))
            if instruction.get("fallthrough"):
                successors.append(str(instruction["fallthrough"]).lower())
        elif "JUMP" in flow or flow == "CALL_TERMINATOR":
            successors.extend(_flow_targets(instruction))
        elif "TERMINATOR" not in flow and instruction.get("fallthrough"):
            successors.append(str(instruction["fallthrough"]).lower())
        for successor in successors:
            if successor in by_address and successor not in reachable:
                reachable.add(successor)
                pending.append(successor)
    if reachable != body_addresses:
        missing = sorted(body_addresses - reachable, key=number)
        raise ValueError(f"unreachable instruction(s) in bounded body at {spec['entry']}: {missing[:3]}")
    return facts


def verify_boundary(
    spec: dict[str, Any],
    instructions_by_address: dict[str, dict[str, Any]],
    gap_metadata_by_address: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    previous_spec = spec.get("previous_instruction")
    if previous_spec is None:
        earlier = [row for address, row in instructions_by_address.items() if number(address) < number(spec["entry"])]
        nearest = max(earlier, key=lambda row: number(row["address"])) if earlier else None
        if nearest is not None and number(nearest["address"]) + len(bytes.fromhex(nearest["bytes"])) - 1 + 0x20 >= number(spec["entry"]):
            raise ValueError(f"unexpected nearby instruction before address-taken entry: {spec['entry']}")
        if spec.get("boundary_gap_hex"):
            raise ValueError(f"entry without a predecessor has an unexpected boundary gap: {spec['entry']}")
        return None

    previous = instructions_by_address.get(str(previous_spec["address"]).lower())
    if previous is None:
        raise ValueError(f"missing preceding instruction for {spec['entry']}")
    previous_bytes = bytes.fromhex(previous["bytes"])
    if previous_bytes.hex() != str(previous_spec["bytes"]).lower():
        raise ValueError(f"preceding instruction bytes drift at {spec['entry']}")
    if not str(previous.get("mnemonic", "")).upper().startswith(str(previous_spec["mnemonic"]).upper()):
        raise ValueError(f"unexpected preceding instruction at {spec['entry']}")
    if not previous["mnemonic"].upper().startswith(("RET", "JMP")):
        raise ValueError(f"preceding instruction is not a terminal boundary at {spec['entry']}")
    previous_target = _flow_targets(previous)
    expected_target = previous_spec.get("flow_target")
    if (previous_target[0] if previous_target else None) != expected_target:
        raise ValueError(f"preceding transfer target drift at {spec['entry']}")
    gap_start = number(previous["address"]) + len(previous_bytes)
    gap_size = number(spec["entry"]) - gap_start
    if gap_size < 0:
        raise ValueError(f"preceding instruction overlaps function entry: {spec['entry']}")
    encoded_gap = bytearray()
    for offset in range(0, gap_size, 4):
        address = gap_start + offset
        metadata = gap_metadata_by_address.get(f"0x{address:08x}")
        if metadata is None:
            raise ValueError(f"missing boundary-gap metadata at {hex(address)}")
        block = metadata.get("block") or {}
        if block.get("name") != ".text" or not block.get("execute"):
            raise ValueError(f"boundary gap is outside executable .text at {hex(address)}")
        if metadata.get("function_at") is not None or metadata.get("function_containing") is not None:
            raise ValueError(f"boundary gap unexpectedly has an original function owner at {hex(address)}")
        value = int(str(metadata["raw_u32"]), 16)
        encoded_gap.extend(value.to_bytes(4, "little")[: min(4, gap_size - offset)])
    if encoded_gap.hex() != str(spec.get("boundary_gap_hex") or "").lower():
        raise ValueError(f"boundary gap bytes drift at {spec['entry']}")
    return previous


def verify_entry_reference(spec: dict[str, Any], reference_row: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {str(row["from"]).lower() for row in spec["entry_data_references"]}
    matching = [
        row for row in reference_row.get("references", [])
        if str(row.get("type", "")).upper() == "DATA" and str(row.get("from", "")).lower() in expected
    ]
    if {str(row.get("from", "")).lower() for row in matching} != expected:
        raise ValueError(f"missing exact address-taken data reference for {spec['entry']}")
    if len(matching) != spec["entry_data_reference_count"]:
        raise ValueError(f"entry reference count drift at {spec['entry']}")
    return matching


def verify_callsite(
    site: str,
    target: str,
    entry: str,
    function_name: str,
    exact_orphans: dict[str, dict[str, Any]],
    original_references: dict[str, dict[str, Any]],
    recovered_references: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    site, target, entry = site.lower(), target.lower(), entry.lower()
    orphan = exact_orphans.get(site)
    if orphan is None or str(orphan.get("target_function", "")).lower() != target:
        raise ValueError(f"callsite is not in the confirmed orphan set: {site}")
    original = [
        ref for ref in original_references.get(target, {}).get("references", [])
        if str(ref.get("from", "")).lower() == site
        and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
        and str(ref.get("instruction", "")).lower().endswith(target)
    ]
    if len(original) != 1:
        raise ValueError(f"original Ghidra call reference is missing or duplicated: {site} -> {target}")
    recovered = [
        ref for ref in recovered_references.get(target, {}).get("references", [])
        if str(ref.get("from", "")).lower() == site
        and str(ref.get("type", "")).upper() == "UNCONDITIONAL_CALL"
        and str(ref.get("function_address", "")).lower() == entry
        and str(ref.get("function_name", "")) == function_name
    ]
    if len(recovered) != 1:
        raise ValueError(f"isolated copy did not assign one exact caller owner: {site}")
    return {
        "callsite": site,
        "target_function": target,
        "instruction": orphan.get("instruction"),
    }


def validate_plan_rows(specs: list[dict[str, Any]], rows: list[dict[str, str]]) -> None:
    if len(specs) != len(rows) or not specs:
        raise ValueError("checked-in plan row count differs from the Ghidra plan")
    expected = {str(row["entry"]).lower(): row for row in specs}
    actual = {str(row["entry"]).lower(): row for row in rows}
    if len(expected) != len(specs) or len(actual) != len(rows) or expected.keys() != actual.keys():
        raise ValueError("checked-in plan entries differ from the Ghidra plan")
    for entry, spec in expected.items():
        previous = spec.get("previous_instruction") or {}
        refs = [str(row["from"]).lower() for row in spec["entry_data_references"]]
        calls = spec["orphan_callsites"]
        wanted = {
            "end": str(spec["end"]).lower(),
            "terminator": str(spec["terminator"]).upper(),
            "terminal_target": str(spec.get("terminal_target") or "-" ).lower(),
            "previous_address": str(previous.get("address") or "-" ).lower(),
            "previous_mnemonic": str(previous.get("mnemonic") or "-" ).upper(),
            "previous_bytes": str(previous.get("bytes") or "-" ).lower(),
            "previous_target": str(previous.get("flow_target") or "-" ).lower(),
            "boundary_gap_hex": str(spec.get("boundary_gap_hex") or "-" ).lower(),
            "entry_reference_sources": ";".join(refs),
            "callsites": ";".join(str(call["address"]).lower() for call in calls),
            "targets": ";".join(str(call["target"]).lower() for call in calls),
            "instruction_count": str(spec["instruction_count"]),
            "pcode_instruction_count": str(spec["pcode_instruction_count"]),
            "call_instruction_count": str(spec["call_instruction_count"]),
            "branch_instruction_count": str(spec["branch_instruction_count"]),
            "body_bytes": str(spec["body_bytes"]),
            "body_sha256": str(spec["body_sha256"]).lower(),
        }
        for key, value in wanted.items():
            if str(actual[entry].get(key, "")).lower() != value.lower():
                raise ValueError(f"checked-in plan {key} drift at {entry}")


def compose_report(
    executable_sha256: str,
    executable_md5: str,
    plan_document: dict[str, Any],
    plan_rows: list[dict[str, str]],
    wrapper_report: dict[str, Any],
    previous_report: dict[str, Any],
    body_slice_rows: list[dict[str, Any]],
    boundary_slice_rows: list[dict[str, Any]],
    body_metadata_rows: list[dict[str, Any]],
    gap_metadata_rows: list[dict[str, Any]],
    entry_reference_rows: list[dict[str, Any]],
    original_target_reference_rows: list[dict[str, Any]],
    recovered_summary_rows: list[dict[str, str]],
    recovered_instruction_rows: list[dict[str, Any]],
    recovered_target_reference_rows: list[dict[str, Any]],
    source_hashes: dict[str, str],
    copy_project_name: str,
) -> dict[str, Any]:
    if executable_sha256 != RETAIL_SHA256 or executable_md5.lower() != RETAIL_MD5:
        raise ValueError("unexpected SHIFT retail executable")
    if plan_document.get("format") != PLAN_FORMAT:
        raise ValueError("unexpected P1B plan format")
    specs = plan_document.get("functions") or []
    validate_plan_rows(specs, plan_rows)

    exact_rows = wrapper_report["unresolved_callsite_reconciliation"]["confirmed_orphan_call_sites"]
    exact_orphans = index_rows(exact_rows, "callsite")
    if len(exact_orphans) != 60:
        raise ValueError("confirmed exact orphan callsite source count drift")
    wrapper_functions = wrapper_report["recovered_orphan_wrapper_functions"]["functions"]
    wrapper_sites = {str(row["caller_callsite"]).lower() for row in wrapper_functions}
    prior_functions = previous_report["recovered_address_taken_functions"]["functions"]
    prior_sites = {str(call["callsite"]).lower() for row in prior_functions for call in row["orphan_callsites"]}
    prior_exact = previous_report["unresolved_callsite_reconciliation"]
    if len(wrapper_sites) != 15 or len(prior_sites) != 3:
        raise ValueError("prior recovered caller-site totals drift")
    if prior_exact["remaining_exact_orphan_callsite_count"] != 42:
        raise ValueError("prior unresolved callsite count drift")
    for site in wrapper_sites | prior_sites:
        if site not in exact_orphans:
            raise ValueError(f"previously recovered site is not an exact orphan call: {site}")
    if wrapper_sites & prior_sites:
        raise ValueError("prior wrapper and address-taken callsites overlap")

    body_instructions = instruction_index(body_slice_rows)
    boundary_instructions = instruction_index(boundary_slice_rows)
    metadata = index_rows(body_metadata_rows, "requested")
    gap_metadata = index_rows(gap_metadata_rows, "requested")
    entry_references = index_rows(entry_reference_rows, "requested")
    original_references = index_rows(original_target_reference_rows, "requested")
    recovered_instructions = index_rows(
        [row for row in recovered_instruction_rows if row.get("found") is True], "requested"
    )
    recovered_references = index_rows(recovered_target_reference_rows, "requested")
    recovered_summaries = index_rows(recovered_summary_rows, "entry")
    wanted_entries = {str(row["entry"]).lower() for row in specs}
    if set(recovered_summaries) != wanted_entries or set(recovered_instructions) != wanted_entries:
        raise ValueError("recovered function exports do not match the plan entries")

    recovered_functions = []
    newly_owned_sites: set[str] = set()
    total_instructions = total_pcode = total_bytes = 0
    for spec in specs:
        entry = str(spec["entry"]).lower()
        boundary = verify_boundary(spec, boundary_instructions, gap_metadata)
        body = validate_body(spec, body_instructions, metadata)
        entry_refs = verify_entry_reference(spec, entry_references.get(entry, {}))
        export = recovered_instructions[entry]
        function = export.get("function") or {}
        summary = recovered_summaries[entry]
        if (
            str(function.get("address", "")).lower() != entry
            or function.get("name") != summary.get("function_name")
            or int(function.get("size", 0)) != body["body_bytes"]
            or int(export.get("instruction_count", 0)) != body["instruction_count"]
        ):
            raise ValueError(f"recovered function export drift at {entry}")
        exported = export.get("instructions") or []
        expected_bytes = [(row["address"].lower(), row["bytes"]) for row in body["instructions"]]
        if [(row["address"].lower(), row["bytes"]) for row in exported] != expected_bytes:
            raise ValueError(f"recovered function bytes differ from original Ghidra: {entry}")
        if [row.get("pcode") for row in exported] != [row.get("pcode") for row in body["instructions"]]:
            raise ValueError(f"recovered function P-code differs from original Ghidra: {entry}")
        if sum(bool(row.get("pcode")) for row in exported) != body["instruction_count"]:
            raise ValueError(f"recovered function is missing P-code: {entry}")
        for key in ("body_sha256", "body_bytes", "instruction_count", "pcode_instruction_count", "call_instruction_count", "branch_instruction_count"):
            if str(summary.get(key)) != str(body[key]):
                raise ValueError(f"recovery summary {key} drift at {entry}")

        sites = []
        for call in spec["orphan_callsites"]:
            site = str(call["address"]).lower()
            target = str(call["target"]).lower()
            if site in newly_owned_sites or site in wrapper_sites or site in prior_sites:
                raise ValueError(f"duplicate recovered orphan callsite: {site}")
            instruction = next((row for row in body["instructions"] if row["address"].lower() == site), None)
            if instruction is None or "CALL" not in str(instruction.get("flow_type", "")).upper() or target not in _flow_targets(instruction):
                raise ValueError(f"planned callsite is not an exact body call: {site} -> {target}")
            orphan = exact_orphans.get(site) or {}
            if str(orphan.get("instruction_bytes", "")).lower() != str(instruction.get("bytes", "")).lower():
                raise ValueError(f"callsite instruction bytes differ from the exact orphan inventory: {site}")
            sites.append(verify_callsite(
                site, target, entry, str(function["name"]), exact_orphans,
                original_references, recovered_references,
            ))
            newly_owned_sites.add(site)

        recovered_functions.append({
            "address": entry,
            "name": function["name"],
            "end": str(spec["end"]).lower(),
            "preceding_instruction": None if boundary is None else {
                "address": str(boundary["address"]).lower(),
                "mnemonic": boundary.get("mnemonic"),
                "flow_target": (_flow_targets(boundary) or [None])[0],
            },
            "boundary_gap_hex": str(spec.get("boundary_gap_hex") or ""),
            "terminator": body["instructions"][-1].get("text"),
            "terminator_target": spec.get("terminal_target"),
            "external_tail_transfers": spec.get("external_tail_transfers", []),
            "instruction_count": body["instruction_count"],
            "pcode_instruction_count": body["pcode_instruction_count"],
            "call_instruction_count": body["call_instruction_count"],
            "branch_instruction_count": body["branch_instruction_count"],
            "body_bytes": body["body_bytes"],
            "body_sha256": body["body_sha256"],
            "entry_data_references": [
                {"from": row.get("from"), "type": row.get("type"), "source": row.get("source"), "instruction": row.get("instruction")}
                for row in entry_refs
            ],
            "orphan_callsites": sites,
        })
        total_instructions += body["instruction_count"]
        total_pcode += body["pcode_instruction_count"]
        total_bytes += body["body_bytes"]

    previously_owned = len(wrapper_sites | prior_sites)
    remaining = len(exact_orphans) - previously_owned - len(newly_owned_sites)
    if len(newly_owned_sites) != 34 or remaining != 8:
        raise ValueError("batch 2 orphan callsite reconciliation drift")
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
            "ghidra_export_source_hashes": dict(sorted(source_hashes.items())),
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
            "all_body_instructions_reachable_in_cfg": True,
            "functions": recovered_functions,
        },
        "unresolved_callsite_reconciliation": {
            "source_exact_orphan_callsite_count": len(exact_orphans),
            "prior_wrapper_owned_callsite_count": len(wrapper_sites),
            "prior_address_taken_owned_callsite_count": len(prior_sites),
            "previously_owned_callsite_count": previously_owned,
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
            f"{remaining} exact orphan direct-call sites remain without a recovered caller owner.",
            "No game-specific semantic names or behavior claims were added.",
        ],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    executable = args.executable
    raw = args.raw_dir
    callsites = args.callsite_raw_dir
    artifacts = {
        "executable": executable,
        "batch2_plan_tsv": args.plan_tsv,
        "batch2_plan_json": raw / "p1b-address-taken-batch2-plan.json",
        "original_pointer_candidate_slices": raw / "near-orphan-pointer-candidate-slices.jsonl",
        "original_callsite_slices": callsites / "orphan-callsite-slices-expanded-0x500.jsonl",
        "all_data_code_target_metadata": raw / "all-data-code-targets-metadata.jsonl",
        "original_body_metadata": raw / "batch2-original-body-metadata.jsonl",
        "boundary_gap_metadata": raw / "candidate-boundary-gap-metadata.jsonl",
        "entry_references": raw / "batch2-entry-references.jsonl",
        "original_target_references": callsites / "target-references-mapped.jsonl",
        "original_function_index": raw / "shift.functions.tsv.gz",
        "original_xref_index": raw / "shift.xrefs.tsv.gz",
        "recovered_function_plan": raw / "batch2-recovered-functions.tsv",
        "recovered_function_instructions": raw / "batch2-recovered-function-instructions.jsonl",
        "recovered_target_references": raw / "batch2-recovered-target-references.jsonl",
        "wrapper_recovery_evidence": args.wrapper_report,
        "previous_address_taken_evidence": args.previous_report,
        "recovery_script.java": Path(__file__).with_name("RecoverP1bAddressTakenFunctionsBatch2.java"),
        "recovery_runner.sh": Path(__file__).with_name("run_p1b_address_taken_recovery_batch2.sh"),
        "report_builder.py": Path(__file__),
    }
    missing = [str(path) for path in artifacts.values() if not path.is_file()]
    if missing:
        raise ValueError(f"missing evidence input(s): {', '.join(missing)}")
    executable_hash = sha256(executable)
    executable_md5 = hashlib.md5(executable.read_bytes()).hexdigest()
    plan_document = read_json(artifacts["batch2_plan_json"])
    return compose_report(
        executable_hash,
        executable_md5,
        plan_document,
        read_tsv(args.plan_tsv),
        read_json(args.wrapper_report),
        read_json(args.previous_report),
        read_jsonl(artifacts["original_pointer_candidate_slices"]),
        read_jsonl(artifacts["original_callsite_slices"]),
        read_jsonl(artifacts["original_body_metadata"]),
        read_jsonl(artifacts["boundary_gap_metadata"]),
        read_jsonl(artifacts["entry_references"]),
        read_jsonl(artifacts["original_target_references"]),
        read_tsv(artifacts["recovered_function_plan"]),
        read_jsonl(artifacts["recovered_function_instructions"]),
        read_jsonl(artifacts["recovered_target_references"]),
        {name: sha256(path) for name, path in artifacts.items()},
        args.copy_project_name,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--plan-tsv", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--callsite-raw-dir", type=Path, required=True)
    parser.add_argument("--wrapper-report", type=Path, required=True)
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
    print(f"recovered address-taken orphan functions: {recovered['function_count']}")
    print(f"new instructions/P-code rows: {recovered['instruction_count']}/{recovered['pcode_instruction_count']}")
    print(f"newly owned exact orphan callsites: {report['unresolved_callsite_reconciliation']['newly_owned_callsite_count']}")
    print(f"remaining exact orphan callsites: {report['unresolved_callsite_reconciliation']['remaining_exact_orphan_callsite_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
