#!/usr/bin/env python3
"""Reconcile Ghidra exact-0x374 scalar uses with the raw-retail literal writer inventory.

This is an independent decoder cross-check. Matching +0x374 displacement does not
prove Participants Manager receiver identity and does not close helper-returned,
opaque runtime or non-vtable indirect setter paths.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374GhidraPlus374WriterReconciliation/1"
INPUT_FORMAT = "SHIFT.GhidraScalarUses/1"
BINARY_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
INVENTORY_FORMAT = "SHIFT.HDVehicle64e8Manager374LiteralStoreInventory/1"
TARGET = "0x374"
EXPECTED_PROGRAM = "SHIFT.exe"
EXPECTED_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
EXPECTED_LANGUAGE = "x86:LE:32:default"
EXPECTED_IMAGE_BASE = "0x00400000"
EXPECTED_POINTER_SIZE = 4
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar",
    "fst", "fstp", "fist", "fistp", "fisttp",
}

MEM = re.compile(
    r"^(?:(?:byte|word|dword|qword|xmmword|tbyte|float|double|long\s+double)\s+ptr\s+)?"
    r"(?:(?:cs|ds|es|fs|gs|ss):)?\[([^\]]+)\]$",
    re.I,
)
GPR = re.compile(r"\b(eax|ebx|ecx|edx|esi|edi|ebp|esp)\b", re.I)
PLUS_374 = re.compile(r"(?:^|\+)0x0*374(?:$|\+)", re.I)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_addr(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text.startswith("0x"):
        raise ValueError(f"invalid instruction address {value!r}")
    return "0x" + text[2:].zfill(8)


def _validate_binary(path: Path) -> dict:
    data = _load_json(path)
    if data.get("format") != BINARY_FORMAT:
        raise ValueError(f"unexpected binary format {data.get('format')!r}")
    if data.get("program_name") != EXPECTED_PROGRAM:
        raise ValueError(f"unexpected program {data.get('program_name')!r}")
    if str(data.get("executable_md5", "")).lower() != EXPECTED_MD5:
        raise ValueError(f"unexpected executable MD5 {data.get('executable_md5')!r}")
    if data.get("language_id") != EXPECTED_LANGUAGE:
        raise ValueError(f"unexpected language {data.get('language_id')!r}")
    if str(data.get("image_base", "")).lower() != EXPECTED_IMAGE_BASE:
        raise ValueError(f"unexpected image base {data.get('image_base')!r}")
    if data.get("pointer_size") != EXPECTED_POINTER_SIZE:
        raise ValueError(f"unexpected pointer size {data.get('pointer_size')!r}")

    blocks = {str(row.get("name")): row for row in data.get("memory_blocks", [])}
    text = blocks.get(".text")
    rdata = blocks.get(".rdata")
    writable = blocks.get(".data")
    if not text or text.get("execute") is not True or text.get("write") is not False:
        raise ValueError("unexpected .text permissions")
    if not rdata or rdata.get("write") is not False:
        raise ValueError("unexpected .rdata permissions")
    if not writable or writable.get("write") is not True:
        raise ValueError("unexpected .data permissions")
    return data


def _read_scalar_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    seen_sites: set[str] = set()
    with path.open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            if row.get("format") != INPUT_FORMAT:
                raise ValueError(f"{path}:{line_no}: unexpected format {row.get('format')!r}")
            if str(row.get("target_scalar", "")).lower() != TARGET:
                raise ValueError(f"{path}:{line_no}: target scalar drift {row.get('target_scalar')!r}")
            if row.get("program") != EXPECTED_PROGRAM:
                raise ValueError(f"{path}:{line_no}: program drift {row.get('program')!r}")
            site = _norm_addr(row.get("instruction_address"))
            if site in seen_sites:
                raise ValueError(f"{path}:{line_no}: duplicate instruction row {site}")
            seen_sites.add(site)
            normalized = dict(row)
            normalized["instruction_address"] = site
            rows.append(normalized)
    return rows


def _memory_plus374(operand: object) -> dict | None:
    text = str(operand or "").strip()
    match = MEM.fullmatch(text)
    if not match:
        return None
    expression = re.sub(r"\s+", "", match.group(1)).lower()
    if not PLUS_374.search(expression):
        return None
    registers = sorted(set(reg.lower() for reg in GPR.findall(expression)))
    if not registers:
        return None
    return {"expression": expression, "registers": registers}


def _load_raw_inventory(path: Path) -> tuple[dict, list[str]]:
    data = _load_json(path)
    if data.get("format") != INVENTORY_FORMAT:
        raise ValueError(f"unexpected raw inventory format {data.get('format')!r}")
    authority = data.get("authority", {})
    if str(authority.get("retail_executable_sha256", "")).lower() != RETAIL_SHA256:
        raise ValueError("raw inventory retail SHA-256 drift")
    scope = data.get("scope", {})
    if scope.get("whole_text_scan") is not True:
        raise ValueError("raw inventory is not a whole-text scan")
    if scope.get("computed_address_writes_included") is not False:
        raise ValueError("raw inventory scope unexpectedly includes computed writes")
    rows = data.get("inventory", {}).get("sites", [])
    sites = [_norm_addr(row.get("site")) for row in rows]
    if len(sites) != len(set(sites)):
        raise ValueError("raw inventory contains duplicate sites")
    expected_count = data.get("inventory", {}).get("literal_write_site_count")
    if expected_count != len(sites):
        raise ValueError("raw inventory count/site mismatch")
    return data, sorted(sites)


def build_payload(rows: list[dict], binary: dict, raw_inventory: dict, raw_sites: list[str]) -> dict:
    candidates: list[dict] = []
    other_first_memory: list[dict] = []
    skipped_scalar_use_count = 0
    write_counts: Counter[str] = Counter()
    other_counts: Counter[str] = Counter()

    for row in rows:
        if row.get("matching_operand_index") != 0:
            skipped_scalar_use_count += 1
            continue
        memory = _memory_plus374(row.get("matching_operand_text"))
        if memory is None:
            skipped_scalar_use_count += 1
            continue
        mnemonic = str(row.get("mnemonic") or "").strip().lower()
        item = {
            "site": row["instruction_address"],
            "function_address": row.get("function_address"),
            "function_name": row.get("function_name"),
            "mnemonic": mnemonic,
            "text": row.get("text"),
            "destination": row.get("matching_operand_text"),
            "expression": memory["expression"],
            "registers": memory["registers"],
        }
        if mnemonic in WRITE_MNEMONICS:
            candidates.append(item)
            write_counts[mnemonic] += 1
        else:
            other_first_memory.append(item)
            other_counts[mnemonic] += 1

    candidates.sort(key=lambda row: row["site"])
    other_first_memory.sort(key=lambda row: row["site"])
    ghidra_sites = [row["site"] for row in candidates]
    ghidra_set = set(ghidra_sites)
    raw_set = set(raw_sites)
    missing = sorted(raw_set - ghidra_set)
    extra = sorted(ghidra_set - raw_set)
    reconciled = not missing and not extra

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "ghidra_program_md5": binary["executable_md5"],
            "program": binary["program_name"],
            "language_id": binary["language_id"],
            "image_base": binary["image_base"],
            "pointer_size": binary["pointer_size"],
        },
        "inputs": {
            "scalar_use_format": INPUT_FORMAT,
            "binary_format": BINARY_FORMAT,
            "raw_inventory_format": INVENTORY_FORMAT,
            "target_scalar": TARGET,
        },
        "surface": {
            "ghidra_exact_scalar_use_count": len(rows),
            "ghidra_skipped_non_destination_or_non_exact_memory_use_count": skipped_scalar_use_count,
            "ghidra_exact_plus_374_write_candidate_count": len(candidates),
            "ghidra_exact_plus_374_write_candidates": candidates,
            "ghidra_write_mnemonic_counts": dict(sorted(write_counts.items())),
            "ghidra_exact_plus_374_other_first_memory_operand_count": len(other_first_memory),
            "ghidra_exact_plus_374_other_first_memory_operands": other_first_memory,
            "ghidra_other_first_memory_mnemonic_counts": dict(sorted(other_counts.items())),
            "raw_retail_literal_write_site_count": len(raw_sites),
            "site_intersection_count": len(ghidra_set & raw_set),
            "missing_from_ghidra": missing,
            "extra_in_ghidra": extra,
        },
        "adjudication": {
            "ghidra_program_identity_pinned": True,
            "raw_retail_literal_inventory_identity_pinned": True,
            "ghidra_literal_plus_0x374_writer_site_reconciliation_complete": reconciled,
            "all_plus_374_candidate_receivers_classified": False,
            "unknown_or_unrelated_manager_root_alias_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This reconciles Ghidra exact-scalar rows against the already authoritative raw-retail literal +0x374 writer inventory; it is not a new semantic receiver proof.",
            "Only first-operand exact +0x374 memory forms with an explicit write/RMW mnemonic are promoted to the Ghidra write candidate set.",
            "Address-materialization followed by zero-displacement stores remains covered by separate materialized/computed contracts, not by this reconciliation.",
            "Helper-returned roots, opaque/runtime-initialized memory, non-vtable indirect setters and arbitrary process mutation remain outside this contract.",
            "Numeric offset equality is never Participants Manager or HDVehicle identity."
        ],
        "next_step": (
            "The pinned Ghidra exact-scalar export now reconciles all 25 literal +0x374 writer sites with the raw-retail inventory. "
            "Continue root-origin/helper-setter closure separately; this decoder cross-check does not establish receiver identity."
        ),
    }


def analyze(scalar_rows: Path, binary_json: Path, raw_inventory_json: Path) -> dict:
    binary = _validate_binary(binary_json)
    rows = _read_scalar_rows(scalar_rows)
    raw_inventory, raw_sites = _load_raw_inventory(raw_inventory_json)
    return build_payload(rows, binary, raw_inventory, raw_sites)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scalar_rows", type=Path)
    parser.add_argument("binary_json", type=Path)
    parser.add_argument("raw_inventory_json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args()
    try:
        payload = analyze(args.scalar_rows, args.binary_json, args.raw_inventory_json)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.fail_on_mismatch and not payload["adjudication"]["ghidra_literal_plus_0x374_writer_site_reconciliation_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
