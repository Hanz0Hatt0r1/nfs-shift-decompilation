#!/usr/bin/env python3
"""Verify a portable SHIFT function export against its full Ghidra inventory."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, TextIO

FORMAT = "SHIFT.FullFunctionInstructionCorpusCoverage/1"
GENERIC_FORMAT = "REVENGINSTR.GhidraFunctionInstructions/1"
CORPUS_FORMAT = "REVENGINSTR.GhidraFunctionInstructionCorpus/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RETAIL_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
_ADDRESS = re.compile(r"^(?:0x)?([0-9a-f]+)$", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_text(path: Path) -> TextIO:
    return gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")


def normalize_address(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid address: {value!r}")
    match = _ADDRESS.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"invalid address: {value!r}")
    return f"0x{int(match.group(1), 16):08x}"


def read_inventory(path: Path) -> list[tuple[str, int]]:
    with open_text(path) as handle:
        header = next(handle, "").rstrip("\n").split("\t")
        if "entry" not in header or "address_count" not in header:
            raise ValueError("function inventory requires entry and address_count columns")
        entry_index = header.index("entry")
        size_index = header.index("address_count")
        addresses = []
        for line_no, line in enumerate(handle, 2):
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= max(entry_index, size_index):
                raise ValueError(f"function inventory line {line_no} is truncated")
            addresses.append((normalize_address(fields[entry_index]), int(fields[size_index])))
    ordered = sorted(set(addresses), key=lambda row: int(row[0], 16))
    if not addresses or addresses != ordered:
        raise ValueError("function inventory must contain unique ascending entries")
    return addresses


def build(executable: Path, inventory: Path, corpus: Path, manifest_path: Path) -> dict[str, Any]:
    executable_sha256 = sha256(executable)
    if executable_sha256 != RETAIL_SHA256:
        raise ValueError(f"unexpected PC retail 1.02 executable SHA-256: {executable_sha256}")
    executable_md5 = hashlib.md5(executable.read_bytes()).hexdigest()
    if executable_md5 != RETAIL_MD5:
        raise ValueError(f"unexpected PC retail 1.02 executable MD5: {executable_md5}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != CORPUS_FORMAT:
        raise ValueError("unsupported generic function corpus manifest")
    if manifest.get("program") != "SHIFT.exe" or manifest.get("executable_md5") != RETAIL_MD5:
        raise ValueError("corpus manifest does not identify PC retail SHIFT.exe")
    if not str(manifest.get("language_id", "")).startswith("x86:LE:32"):
        raise ValueError("corpus is not x86-32 little-endian")
    if manifest.get("gzip") is not True or not manifest.get("complete"):
        raise ValueError("corpus manifest does not describe a complete gzip export")
    if manifest.get("function_offset") != 0:
        raise ValueError("corpus export does not start at function ordinal 0")
    if manifest.get("exported_function_count") != manifest.get("function_count"):
        raise ValueError("corpus export does not cover the full Ghidra function count")
    corpus_sha256 = sha256(corpus)
    if manifest.get("output_sha256") != corpus_sha256:
        raise ValueError("corpus SHA-256 does not match its manifest")

    expected = read_inventory(inventory)
    expected_addresses = [address for address, _size in expected]
    expected_sizes = dict(expected)
    if manifest.get("function_count") != len(expected_addresses):
        raise ValueError("Ghidra inventory count does not match the corpus manifest")

    observed: list[str] = []
    machine_instructions = 0
    pcode_instructions = 0
    pcode_operations = 0
    pcode_empty_mnemonics: Counter[str] = Counter()
    with gzip.open(corpus, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("format") != GENERIC_FORMAT or row.get("found") is not True:
                raise ValueError(f"corpus line {line_no} is not a resolved generic function row")
            function = row.get("function")
            if not isinstance(function, dict):
                raise ValueError(f"corpus line {line_no} has no function metadata")
            address = normalize_address(function.get("address"))
            if normalize_address(row.get("resolved_address")) != address:
                raise ValueError(f"corpus line {line_no} has mismatched resolved function address")
            if normalize_address(row.get("requested")) != address:
                raise ValueError(f"corpus line {line_no} has mismatched requested function address")
            if function.get("size") != expected_sizes.get(address):
                raise ValueError(f"corpus line {line_no} has mismatched function body size")
            if row.get("program") != "SHIFT.exe":
                raise ValueError(f"corpus line {line_no} belongs to a different program")
            if observed and int(address, 16) <= int(observed[-1], 16):
                raise ValueError(f"corpus function entries are duplicated or out of order at {address}")
            observed.append(address)

            instructions = row.get("instructions")
            if not isinstance(instructions, list) or not instructions or row.get("instruction_count") != len(instructions):
                raise ValueError(f"corpus line {line_no} has inconsistent instruction rows")
            previous_instruction = -1
            entry_found = False
            for instruction in instructions:
                if not isinstance(instruction, dict):
                    raise ValueError(f"corpus line {line_no} contains an invalid instruction")
                instruction_address = normalize_address(instruction.get("address"))
                if int(instruction_address, 16) <= previous_instruction:
                    raise ValueError(f"instructions are duplicated or out of order in {address}")
                previous_instruction = int(instruction_address, 16)
                entry_found = entry_found or instruction_address == address
                pcode = instruction.get("pcode")
                if not isinstance(pcode, list):
                    raise ValueError(f"instruction {instruction_address} has no P-code list")
                machine_instructions += 1
                pcode_instructions += bool(pcode)
                pcode_operations += len(pcode)
                if not pcode:
                    pcode_empty_mnemonics[str(instruction.get("mnemonic", "<missing>"))] += 1
            if instructions and not entry_found:
                raise ValueError(f"corpus function {address} has no instruction at its entry")

    if observed != expected_addresses:
        raise ValueError(
            f"corpus function entries differ from Ghidra inventory: "
            f"expected {len(expected_addresses)}, observed {len(observed)}"
        )
    if machine_instructions != manifest.get("instruction_count"):
        raise ValueError("machine instruction count does not match the corpus manifest")
    if observed[0] != manifest.get("first_function_address") or observed[-1] != manifest.get("last_function_address"):
        raise ValueError("corpus entry range does not match its manifest")

    return {
        "format": FORMAT,
        "validated": True,
        "authority": {
            "platform": "PC retail 1.02",
            "executable_sha256": executable_sha256,
            "executable_md5": executable_md5,
            "ghidra_function_inventory_sha256": sha256(inventory),
            "portable_function_corpus_sha256": corpus_sha256,
            "corpus_manifest_sha256": sha256(manifest_path),
            "ghidra_program": manifest["program"],
            "language_id": manifest["language_id"],
        },
        "coverage": {
            "ghidra_function_count": len(expected_addresses),
            "exported_function_count": len(observed),
            "full_function_inventory_covered": True,
            "machine_instruction_count": machine_instructions,
            "pcode_instruction_count": pcode_instructions,
            "pcode_operation_count": pcode_operations,
            "instructions_without_pcode": machine_instructions - pcode_instructions,
            "pcode_empty_instruction_mnemonic_counts": dict(sorted(pcode_empty_mnemonics.items())),
            "full_pcode_instruction_coverage": machine_instructions == pcode_instructions,
        },
        "limits": [
            "This portable machine-instruction/P-code corpus is not decompiled C or project source.",
            "It does not alone establish a recompilable source reconstruction or behavioral equivalence.",
            "Function boundaries reflect the supplied analyzed Ghidra project and are validated against its function index.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("function_inventory", type=Path)
    parser.add_argument("portable_function_corpus", type=Path)
    parser.add_argument("corpus_manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.executable, args.function_inventory, args.portable_function_corpus, args.corpus_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coverage = report["coverage"]
    print(f"functions: {coverage['exported_function_count']}/{coverage['ghidra_function_count']}")
    print(f"machine instructions: {coverage['machine_instruction_count']}")
    print(f"P-code operations: {coverage['pcode_operation_count']}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
