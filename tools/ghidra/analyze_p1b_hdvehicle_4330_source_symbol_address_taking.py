#!/usr/bin/env python3
"""Bound source-visible address-taking/value use of P1B exact HDVehicle+0x4330 carrier symbols."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330SourceSymbolAddressTaking/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXPECTED_OCCURRENCES = {
    "FUN_00769520": 2,
    "FUN_0076b130": 1,
    "FUN_0076df50": 3,
    "FUN_00768a4d": 2,
    "FUN_00756050": 4,
    "FUN_00772200": 3,
    "FUN_00772570": 2,
    "FUN_007c3b00": 7,
    "FUN_0076b280": 2,
    "FUN_007618f0": 2,
    "FUN_00769640": 2,
    "FUN_007567a0": 2,
    "FUN_00756bb0": 2,
    "FUN_00771db0": 4,
    "FUN_00771e10": 2,
}
EXPECTED_TOTAL_OCCURRENCES = 40


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(source: Path) -> dict:
    digest = sha256(source)
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected source SHA-256: {digest}")
    text = source.read_text(encoding="utf-8", errors="strict")

    rows = []
    total = 0
    noncall_value_uses = []
    for symbol, expected_count in EXPECTED_OCCURRENCES.items():
        matches = list(re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", text, re.IGNORECASE))
        if len(matches) != expected_count:
            raise ValueError(f"{symbol} occurrence drift: {len(matches)} != {expected_count}")
        call_form_count = 0
        lines = []
        for match in matches:
            line = text.count("\n", 0, match.start()) + 1
            lines.append(line)
            j = match.end()
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] == "(":
                call_form_count += 1
            else:
                noncall_value_uses.append({
                    "symbol": symbol,
                    "line": line,
                    "following_text": text[j:j + 32],
                })
        if call_form_count != expected_count:
            raise ValueError(f"{symbol} gained non-call-form source reference")
        rows.append({
            "symbol": symbol,
            "occurrence_count": expected_count,
            "call_or_definition_form_count": call_form_count,
            "noncall_symbol_value_use_count": 0,
            "source_lines": lines,
        })
        total += expected_count

    if total != EXPECTED_TOTAL_OCCURRENCES:
        raise ValueError(f"total carrier symbol occurrence drift: {total}")
    if noncall_value_uses:
        raise ValueError(f"exact carrier symbol used as source-visible value: {noncall_value_uses!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "shift_exe_c_sha256": digest,
            "ghidra_c_export_is_source_visible_reference_surface": True,
        },
        "surface": {
            "exact_carrier_symbol_count": len(EXPECTED_OCCURRENCES),
            "total_exact_carrier_symbol_occurrence_count": total,
            "call_or_definition_form_occurrence_count": total,
            "source_visible_noncall_symbol_value_use_count": 0,
            "source_visible_address_taken_carrier_symbol_count": 0,
            "symbols": rows,
        },
        "adjudication": {
            "source_visible_exact_carrier_symbol_reference_surface_complete": True,
            "source_visible_exact_carrier_symbol_address_taken_found": False,
            "source_visible_exact_carrier_symbol_value_store_found": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only references emitted under the exact carrier function symbols in the hash-pinned Ghidra C export.",
            "Every one of the 40 symbol occurrences is immediately followed by '(' after whitespace, consistent with a definition/direct invocation rather than source-visible symbol-as-value use.",
            "Computed, encoded, copied, reconstructed, table-derived, address-literal, or decompiler-unresolved function pointers remain outside this subset."
        ],
        "next_step": "Compose this with existing whole-image literal/static-table negatives, then continue machine-level generic function-pointer stores/copies and reconstructed pointer creation."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = analyze(args.source)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
