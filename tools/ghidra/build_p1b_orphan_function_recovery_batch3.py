#!/usr/bin/env python3
"""Build fail-closed evidence for the third verified P1B orphan recovery batch."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.P1B.OrphanCallerRecoveryBatch3/1"
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


def norm(value: Any) -> str:
    text = str(value or "").lower()
    return text if text.startswith("0x") else f"0x{text}" if text else ""


def number(value: Any) -> int:
    return int(str(value), 16)


def index_jsonl(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = norm(row.get(key))
        if not value or value in indexed:
            raise ValueError(f"missing or duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def instruction_index(slices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for slice_row in slices:
        for instruction in slice_row.get("instructions", []):
            address = norm(instruction.get("address"))
            prior = result.get(address)
            if prior is not None and prior != instruction:
                raise ValueError(f"conflicting instruction exports at {address}")
            result[address] = instruction
    return result


def load_xrefs(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def xref_matches(
    rows: list[dict[str, str]], source: str, target: str, ref_type: str
) -> list[dict[str, str]]:
    return [
        row for row in rows
        if norm(row.get("from")) == norm(source)
        and norm(row.get("to")) == norm(target)
        and str(row.get("type", "")).upper() == ref_type.upper()
    ]


def parse_pairs(value: str, separator: str, fields: int) -> list[list[str]]:
    if value in {"", "-"}:
        return []
    parsed = []
    for item in value.split(";"):
        row = item.split(separator)
        if len(row) != fields:
            raise ValueError(f"malformed plan value: {item}")
        parsed.append(row)
    return parsed


def body_for(
    spec: dict[str, str], instructions: dict[str, dict[str, Any]], metadata: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    entry, end = norm(spec["entry"]), norm(spec["end"])
    low, high = number(entry), number(end)
    body = [instructions[f"0x{address:08x}"] for address in sorted(
        (number(key) for key in instructions if low <= number(key) <= high)
    )]
    if not body or norm(body[0].get("address")) != entry or norm(body[-1].get("address")) != end:
        raise ValueError(f"missing exact function boundaries for {entry}")

    expected = low
    encoded = bytearray()
    body_addresses = {norm(row.get("address")) for row in body}
    external = {
        (norm(source), norm(target)): (kind, norm(owner))
        for source, target, kind, owner in parse_pairs(spec["external_flows"], ",", 4)
    }
    call_count = branch_count = pcode_count = 0
    for instruction in body:
        address = norm(instruction["address"])
        raw = bytes.fromhex(str(instruction["bytes"]))
        if number(address) != expected:
            raise ValueError(f"non-contiguous body at {entry}: expected {expected:#x}, found {address}")
        expected += len(raw)
        encoded.extend(raw)
        meta = metadata.get(address)
        if meta is None:
            raise ValueError(f"missing original Ghidra metadata at {address}")
        if meta.get("function_at") is not None or meta.get("function_containing") is not None:
            raise ValueError(f"instruction already had an original owner at {address}")
        block = meta.get("block") or {}
        if block.get("name") != ".text" or not block.get("execute"):
            raise ValueError(f"instruction is outside executable .text at {address}")
        if not instruction.get("pcode"):
            raise ValueError(f"missing P-code at {address}")
        pcode_count += 1
        flow = str(instruction.get("flow_type", "")).upper()
        call_count += "CALL" in flow
        branch_count += "JUMP" in flow
        if "JUMP" in flow or flow == "CALL_TERMINATOR":
            targets = [norm(target) for target in instruction.get("flows", []) if target]
            if not targets:
                raise ValueError(f"jump has no flow target at {address}")
            for target in targets:
                if target not in body_addresses and (address, target) not in external:
                    raise ValueError(f"unrecorded external CFG edge at {address} -> {target}")

    reachable: set[str] = set()
    pending = [entry]
    by_address = {norm(row["address"]): row for row in body}
    while pending:
        address = pending.pop()
        if address in reachable:
            continue
        row = by_address.get(address)
        if row is None:
            raise ValueError(f"CFG reached a non-body instruction at {address}")
        reachable.add(address)
        flow = str(row.get("flow_type", "")).upper()
        if "JUMP" in flow:
            for target_value in row.get("flows", []):
                target = norm(target_value)
                if target in by_address:
                    pending.append(target)
                elif (address, target) not in external:
                    raise ValueError(f"CFG leaves body without evidence at {address} -> {target}")
            if "CONDITIONAL" in flow and row.get("fallthrough"):
                pending.append(norm(row["fallthrough"]))
        elif flow == "CALL_TERMINATOR":
            for target_value in row.get("flows", []):
                if (address, norm(target_value)) not in external:
                    raise ValueError(f"unrecorded tail transfer at {address}")
        elif "TERMINATOR" not in flow and row.get("fallthrough"):
            pending.append(norm(row["fallthrough"]))
    if reachable != body_addresses:
        missing = sorted(body_addresses - reachable)
        raise ValueError(f"unreachable body instruction(s) at {entry}: {missing[:5]}")

    facts = {
        "instructions": body,
        "instruction_count": len(body),
        "pcode_instruction_count": pcode_count,
        "call_instruction_count": call_count,
        "branch_instruction_count": branch_count,
        "body_bytes": len(encoded),
        "body_sha256": hashlib.sha256(encoded).hexdigest(),
        "external_flows": external,
    }
    for key in (
        "instruction_count", "pcode_instruction_count", "call_instruction_count",
        "branch_instruction_count", "body_bytes", "body_sha256",
    ):
        if str(facts[key]).lower() != str(spec[key]).lower():
            raise ValueError(f"{key} drift at {entry}")
    return facts


def verify_boundary(
    spec: dict[str, str], instructions: dict[str, dict[str, Any]], metadata: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    address = norm(spec["previous_address"])
    previous = instructions.get(address)
    if previous is None:
        raise ValueError(f"missing previous instruction at {address}")
    if bytes.fromhex(previous["bytes"]).hex() != spec["previous_bytes"].lower():
        raise ValueError(f"previous instruction bytes drift at {spec['entry']}")
    if not str(previous.get("mnemonic", "")).upper().startswith(spec["previous_mnemonic"].upper()):
        raise ValueError(f"previous instruction mnemonic drift at {spec['entry']}")
    if not str(previous.get("mnemonic", "")).upper().startswith(("RET", "JMP")):
        raise ValueError(f"preceding instruction is not terminal at {spec['entry']}")
    gap_start = number(address) + len(bytes.fromhex(previous["bytes"]))
    gap_size = number(spec["entry"]) - gap_start
    if gap_size < 0:
        raise ValueError(f"previous instruction overlaps entry {spec['entry']}")
    gap = bytearray()
    for gap_address in range(gap_start, gap_start + gap_size):
        key = f"0x{gap_address:08x}"
        row = metadata.get(key)
        if row is None:
            raise ValueError(f"missing boundary metadata at {key}")
        block = row.get("block") or {}
        if block.get("name") != ".text" or not block.get("execute"):
            raise ValueError(f"boundary byte is outside executable .text at {key}")
        if row.get("function_at") is not None or row.get("function_containing") is not None:
            raise ValueError(f"boundary byte has an original owner at {key}")
        gap.append(int(str(row["raw_u32"]), 16) & 0xff)
    if gap.hex() != spec["boundary_gap_hex"].lower() or any(value != 0xcc for value in gap):
        raise ValueError(f"boundary padding drift at {spec['entry']}")
    return previous


def verify_entry_evidence(
    spec: dict[str, str], metadata: dict[str, dict[str, Any]], xrefs: list[dict[str, str]]
) -> list[dict[str, Any]]:
    evidence = []
    for kind, source, target in parse_pairs(spec["entry_evidence"], ",", 3):
        source, target = norm(source), norm(target)
        if target != norm(spec["entry"]):
            raise ValueError(f"entry evidence points elsewhere at {spec['entry']}")
        if kind == "RAW_U32":
            row = metadata.get(source)
            block = (row or {}).get("block") or {}
            if row is None or block.get("name") != ".rdata" or block.get("write"):
                raise ValueError(f"raw pointer source is not read-only .rdata at {source}")
            if number(row.get("raw_u32")) != number(target):
                raise ValueError(f"raw pointer value drift at {source}")
            evidence.append({"kind": kind, "from": source, "target": target, "raw_u32": row["raw_u32"]})
            continue
        ref_type = "DATA" if kind == "DATA" else "UNCONDITIONAL_JUMP" if kind == "JUMP" else None
        if ref_type is None:
            raise ValueError(f"unsupported entry evidence kind: {kind}")
        matches = xref_matches(xrefs, source, target, ref_type)
        if len(matches) != 1:
            raise ValueError(f"missing or duplicate {ref_type} entry reference at {source} -> {target}")
        evidence.append({"kind": kind, "from": source, "target": target, "type": ref_type})
    if not evidence:
        raise ValueError(f"function has no entry evidence: {spec['entry']}")
    return evidence


def verify_orphan_callsites(
    spec: dict[str, str],
    facts: dict[str, Any],
    orphan_index: dict[str, dict[str, Any]],
    xrefs: list[dict[str, str]],
) -> list[dict[str, str]]:
    by_address = {norm(row["address"]): row for row in facts["instructions"]}
    calls = []
    for address, target in parse_pairs(spec["callsites"], ">", 2):
        address, target = norm(address), norm(target)
        orphan = orphan_index.get(address)
        instruction = by_address.get(address)
        if orphan is None or norm(orphan.get("target_function")) != target:
            raise ValueError(f"callsite is absent from exact orphan inventory: {address}")
        if instruction is None or "CALL" not in str(instruction.get("flow_type", "")).upper():
            raise ValueError(f"planned callsite is not in recovered body: {address}")
        if target not in [norm(value) for value in instruction.get("flows", [])]:
            raise ValueError(f"planned call target drift at {address}")
        if str(orphan.get("instruction_bytes", "")).lower() != str(instruction.get("bytes", "")).lower():
            raise ValueError(f"callsite bytes differ from exact orphan inventory at {address}")
        refs = xref_matches(xrefs, address, target, "UNCONDITIONAL_CALL")
        if len(refs) != 1:
            raise ValueError(f"missing or duplicate original call xref at {address}")
        calls.append({"callsite": address, "target_function": target, "instruction": orphan.get("instruction")})
    if not calls:
        raise ValueError(f"no orphan callsites recovered for {spec['entry']}")
    return calls


def compose_report(args: argparse.Namespace) -> dict[str, Any]:
    source_paths = {
        "executable": args.executable,
        "plan_tsv": args.plan_tsv,
        "original_address_metadata": args.metadata_jsonl,
        "original_4b_instruction_slice": args.fourb_slice,
        "original_small_instruction_slice": args.small_slice,
        "original_pointer_candidate_slice": args.pointer_slice,
        "original_boundary_instruction_slice": args.boundary_slice,
        "original_xref_index": args.xref_tsv_gz,
        "wrapper_orphan_inventory": args.wrapper_report,
        "previous_address_taken_evidence": args.previous_report,
        "batch1_address_taken_evidence": args.prior_report,
        "recovered_function_plan": args.recovered_plan_tsv,
        "recovered_function_instructions": args.recovered_instructions_jsonl,
        "recovered_target_reference_owners": args.recovered_references_tsv,
        "recovery_script_java": Path(__file__).with_name("RecoverP1bOrphanFunctionsBatch3.java"),
        "recovery_runner": Path(__file__).with_name("run_p1b_orphan_function_recovery_batch3.sh"),
        "report_builder": Path(__file__),
    }
    missing = [str(path) for path in source_paths.values() if not path.is_file()]
    if missing:
        raise ValueError(f"missing evidence input(s): {', '.join(missing)}")
    md5 = hashlib.md5(args.executable.read_bytes()).hexdigest()
    if md5.lower() != RETAIL_MD5:
        raise ValueError("executable MD5 differs from the pinned SHIFT retail build")
    executable_hash = sha256(args.executable)

    plan = read_tsv(args.plan_tsv)
    if len(plan) != 3:
        raise ValueError("batch 3 plan must contain exactly three functions")
    metadata = index_jsonl(read_jsonl(args.metadata_jsonl), "requested")
    source_slices = (
        read_jsonl(args.fourb_slice)
        + read_jsonl(args.small_slice)
        + read_jsonl(args.pointer_slice)
        + read_jsonl(args.boundary_slice)
    )
    instructions = instruction_index(source_slices)
    xrefs = load_xrefs(args.xref_tsv_gz)
    wrapper = read_json(args.wrapper_report)
    previous = read_json(args.previous_report)
    prior = read_json(args.prior_report)
    exact_orphans = wrapper["unresolved_callsite_reconciliation"]["confirmed_orphan_call_sites"]
    orphan_index = index_jsonl(exact_orphans, "callsite")
    if len(orphan_index) != 60:
        raise ValueError("confirmed exact orphan callsite inventory drift")

    prior_wrapper_sites = {
        norm(row["caller_callsite"])
        for row in wrapper["recovered_orphan_wrapper_functions"]["functions"]
    }
    prior_batch1_sites = {
        norm(call["callsite"])
        for function in prior["recovered_address_taken_functions"]["functions"]
        for call in function["orphan_callsites"]
    }
    prior_batch2_sites = {
        norm(site)
        for site in previous["unresolved_callsite_reconciliation"]["newly_owned_callsites"]
    }
    previously_owned = prior_wrapper_sites | prior_batch1_sites | prior_batch2_sites
    if len(previously_owned) != 52 or previous["unresolved_callsite_reconciliation"]["remaining_exact_orphan_callsite_count"] != 8:
        raise ValueError("prior recovery totals drift before batch 3")

    recovered_plan = index_jsonl(read_tsv(args.recovered_plan_tsv), "entry")
    recovered_instructions = index_jsonl(read_jsonl(args.recovered_instructions_jsonl), "requested")
    recovered_refs = read_tsv(args.recovered_references_tsv)
    if set(recovered_plan) != {norm(row["entry"]) for row in plan}:
        raise ValueError("isolated recovery plan differs from checked-in batch 3 plan")
    if set(recovered_instructions) != set(recovered_plan):
        raise ValueError("isolated function instruction exports differ from plan")

    functions = []
    newly_owned: set[str] = set()
    total_instructions = total_pcode = total_bytes = 0
    for spec in plan:
        entry = norm(spec["entry"])
        facts = body_for(spec, instructions, metadata)
        previous_instruction = verify_boundary(spec, instructions, metadata)
        entry_evidence = verify_entry_evidence(spec, metadata, xrefs)
        calls = verify_orphan_callsites(spec, facts, orphan_index, xrefs)
        recovered = recovered_instructions[entry]
        function = recovered.get("function") or {}
        summary = recovered_plan[entry]
        exported = recovered.get("instructions") or []
        if recovered.get("found") is not True or norm(function.get("address")) != entry:
            raise ValueError(f"isolated Ghidra copy did not create {entry}")
        if function.get("name") != summary.get("function_name") or int(function.get("size", 0)) != facts["body_bytes"]:
            raise ValueError(f"recovered function identity/size drift at {entry}")
        if int(recovered.get("instruction_count", 0)) != facts["instruction_count"]:
            raise ValueError(f"recovered instruction count drift at {entry}")
        expected_bytes = [(norm(row["address"]), row["bytes"].lower()) for row in facts["instructions"]]
        actual_bytes = [(norm(row["address"]), str(row["bytes"]).lower()) for row in exported]
        if actual_bytes != expected_bytes:
            raise ValueError(f"recovered instruction bytes differ from original at {entry}")
        if [row.get("pcode") for row in exported] != [row.get("pcode") for row in facts["instructions"]]:
            raise ValueError(f"recovered P-code differs from original at {entry}")
        if not all(row.get("pcode") for row in exported):
            raise ValueError(f"recovered export has missing P-code at {entry}")
        for key in ("body_bytes", "instruction_count", "pcode_instruction_count", "call_instruction_count", "branch_instruction_count", "body_sha256"):
            if str(summary[key]).lower() != str(facts[key]).lower():
                raise ValueError(f"recovered summary {key} drift at {entry}")

        function_calls = []
        for call in calls:
            site, target = norm(call["callsite"]), norm(call["target_function"])
            if site in newly_owned or site in previously_owned:
                raise ValueError(f"duplicate callsite ownership at {site}")
            refs = [
                row for row in recovered_refs
                if norm(row.get("target_address")) == target
                and norm(row.get("reference_from")) == site
                and row.get("reference_type") == "UNCONDITIONAL_CALL"
                and norm(row.get("containing_function_entry")) == entry
                and row.get("containing_function_name") == function.get("name")
            ]
            if len(refs) != 1:
                raise ValueError(f"isolated copy did not assign exact caller ownership at {site}")
            newly_owned.add(site)
            function_calls.append(call)

        external_rows = []
        for source, target, kind, owner in parse_pairs(spec["external_flows"], ",", 4):
            source, target, owner = norm(source), norm(target), norm(owner)
            instruction = next((row for row in facts["instructions"] if norm(row["address"]) == source), None)
            if instruction is None or target not in [norm(value) for value in instruction.get("flows", [])]:
                raise ValueError(f"external flow facts drift at {source}")
            target_meta = metadata.get(target)
            target_owner = (target_meta or {}).get("function_containing") or {}
            if target_meta is None or norm((target_owner or {}).get("entry")) != owner:
                raise ValueError(f"external CFG target owner drift at {target}")
            flow_type = str(instruction.get("flow_type", "")).upper()
            if kind == "TAIL" and flow_type != "CALL_TERMINATOR":
                raise ValueError(f"tail flow is not a CALL_TERMINATOR at {source}")
            if kind == "SHARED_BRANCH" and "CONDITIONAL_JUMP" not in flow_type:
                raise ValueError(f"shared exit is not conditional at {source}")
            external_rows.append({"source": source, "target": target, "kind": kind, "target_function_entry": owner})

        functions.append({
            "address": entry,
            "name": function["name"],
            "end": norm(spec["end"]),
            "preceding_instruction": {
                "address": norm(previous_instruction["address"]),
                "mnemonic": previous_instruction.get("mnemonic"),
                "bytes": previous_instruction.get("bytes"),
            },
            "boundary_gap_hex": spec["boundary_gap_hex"].lower(),
            "instruction_count": facts["instruction_count"],
            "pcode_instruction_count": facts["pcode_instruction_count"],
            "call_instruction_count": facts["call_instruction_count"],
            "branch_instruction_count": facts["branch_instruction_count"],
            "body_bytes": facts["body_bytes"],
            "body_sha256": facts["body_sha256"],
            "entry_evidence": entry_evidence,
            "external_cfg_flows": external_rows,
            "orphan_callsites": function_calls,
        })
        total_instructions += facts["instruction_count"]
        total_pcode += facts["pcode_instruction_count"]
        total_bytes += facts["body_bytes"]

    remaining_sites = sorted(set(orphan_index) - previously_owned - newly_owned)
    if len(newly_owned) != 7 or remaining_sites != ["0x00d38db6"]:
        raise ValueError("batch 3 callsite reconciliation drift")
    combined = previous["combined_function_instruction_exports"]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": executable_hash,
            "retail_executable_md5": RETAIL_MD5,
            "original_ghidra_project_modified": False,
            "function_recovery_copy_project": args.copy_project_name,
            "ghidra_export_source_hashes": {name: sha256(path) for name, path in sorted(source_paths.items())},
        },
        "recovered_orphan_functions": {
            "function_count": len(functions),
            "instruction_count": total_instructions,
            "pcode_instruction_count": total_pcode,
            "body_byte_count": total_bytes,
            "all_body_instructions_unowned_in_original_project": True,
            "all_instruction_bytes_match_original_project": True,
            "all_pcode_rows_match_original_project": True,
            "all_body_instructions_reachable_in_bounded_cfg": True,
            "functions": functions,
        },
        "unresolved_callsite_reconciliation": {
            "source_exact_orphan_callsite_count": len(orphan_index),
            "previously_owned_callsite_count": len(previously_owned),
            "newly_owned_callsite_count": len(newly_owned),
            "remaining_exact_orphan_callsite_count": len(remaining_sites),
            "remaining_exact_orphan_callsites": remaining_sites,
            "newly_owned_callsites": sorted(newly_owned),
        },
        "combined_function_instruction_exports": {
            "previous_unique_function_count": combined["unique_function_count"],
            "unique_function_count": combined["unique_function_count"] + len(functions),
            "unique_instruction_count": combined["unique_instruction_count"] + total_instructions,
            "unique_pcode_instruction_count": combined["unique_pcode_instruction_count"] + total_pcode,
        },
        "limitations": [
            "One recovered body has two explicitly evidenced control-flow exits into existing functions, including a shared epilogue.",
            "The remaining .secu callsite at 0x00d38db6 is not assigned an owner because its containing body boundary is unresolved.",
            "No game-specific semantic names or behavior claims were added.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "executable", "plan-tsv", "metadata-jsonl", "fourb-slice", "small-slice", "pointer-slice",
        "boundary-slice", "xref-tsv-gz", "wrapper-report", "previous-report", "prior-report",
        "recovered-plan-tsv", "recovered-instructions-jsonl", "recovered-references-tsv",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--copy-project-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = compose_report(args)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    recovered = report["recovered_orphan_functions"]
    reconciliation = report["unresolved_callsite_reconciliation"]
    print(f"recovered functions: {recovered['function_count']}")
    print(f"new instructions/P-code rows: {recovered['instruction_count']}/{recovered['pcode_instruction_count']}")
    print(f"newly owned exact orphan callsites: {reconciliation['newly_owned_callsite_count']}")
    print(f"remaining exact orphan callsites: {reconciliation['remaining_exact_orphan_callsite_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
