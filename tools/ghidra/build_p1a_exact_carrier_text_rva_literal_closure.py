#!/usr/bin/env python3
"""Derive the executable-.text exact-carrier RVA literal subset from merged P1A retail evidence.

The upstream whole-image scan is machine-authoritative for raw byte presence. This
builder only partitions its unresolved RVA diagnostics by PE section. It closes
the .text byte-literal subset when every raw exact-carrier RVA match lies outside
.text; non-text matches remain unresolved and global RVA/relocation gates stay
fail-closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AExactCarrierTextRvaLiteralClosure/1"
UPSTREAM_FORMAT = "SHIFT.P1A.P13AExactCarrierWholeImagePointerLiteralClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_TEXT_RAW_SIZE = 6_964_736
EXPECTED_WHOLE_RVA_MATCH_COUNT = 2
EXPECTED_NON_TEXT_ROWS = [
    ("FUN_0076d100", "0x0036d100", "0x006d2e3f", ".rdata", 3),
    ("FUN_0076d100", "0x0036d100", "0x00764ea7", ".rdata", 3),
]


def build(upstream: dict) -> dict:
    if upstream.get("format") != UPSTREAM_FORMAT or upstream.get("ready") is not True:
        raise ValueError("unexpected or incomplete whole-image carrier-pointer evidence")
    auth = upstream.get("authority", {})
    if auth.get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError("retail executable SHA-256 drift")
    if upstream.get("carrier_set", {}).get("count") != 16:
        raise ValueError("carrier-count drift")

    text_rows = [row for row in upstream.get("pe_sections", []) if row.get("name") == ".text"]
    if len(text_rows) != 1:
        raise ValueError("expected exactly one .text section")
    text = text_rows[0]
    if text.get("raw_size") != EXPECTED_TEXT_RAW_SIZE:
        raise ValueError(".text raw-size drift")

    diag = upstream.get("rva_diagnostics", {})
    matches = diag.get("matches", [])
    if diag.get("raw_match_count") != EXPECTED_WHOLE_RVA_MATCH_COUNT or len(matches) != EXPECTED_WHOLE_RVA_MATCH_COUNT:
        raise ValueError("whole-image RVA diagnostic count drift")
    text_matches = [row for row in matches if row.get("section") == ".text"]
    non_text_matches = [row for row in matches if row.get("section") != ".text"]
    actual_non_text = [
        (row.get("function"), row.get("rva_value"), row.get("file_offset"), row.get("section"), row.get("file_offset_mod4"))
        for row in non_text_matches
    ]
    if actual_non_text != EXPECTED_NON_TEXT_ROWS:
        raise ValueError("non-text RVA diagnostic set drift")
    if text_matches:
        raise ValueError("exact-carrier RVA byte sequence appeared in executable .text")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contract": UPSTREAM_FORMAT,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "upstream_whole_file_raw_bytes_adjudicate_literal_presence": True,
        },
        "carrier_set": upstream["carrier_set"],
        "text_surface": {
            "section": ".text",
            "section_rva": text.get("rva"),
            "raw_size": text.get("raw_size"),
            "encoding": "little-endian 32-bit RVA byte sequence",
            "exact_carrier_rva_literal_hit_count": len(text_matches),
            "hits": text_matches,
        },
        "non_text_unresolved_surface": {
            "raw_match_count": len(non_text_matches),
            "matches": non_text_matches,
            "semantic_gate": False,
        },
        "adjudication": {
            "p13a_text_exact_carrier_rva_literal_subset_complete": True,
            "p13a_text_exact_carrier_rva_literal_hit_found": False,
            "p13a_text_exact_carrier_rva_literal_hit_count": 0,
            "p13a_non_text_exact_carrier_rva_matches_remain_unresolved": True,
            "relocated_or_rva_encoded_carrier_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "incoming_indirect_entry_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only raw exact-carrier RVA byte sequences inside the on-disk executable .text section.",
            "The two merged .rdata RVA matches remain unresolved and are neither promoted to pointers nor rejected as non-pointers.",
            "Absence of a raw RVA byte sequence in .text does not exclude rel32 control transfers, relocations, encoded/reconstructed pointers, runtime registration, or copied/generated code pointers.",
            "No global callback/indirect-entry, stored-or-escaped-alias, slot0/slot1 or aggregate P1.3 gate is promoted."
        ],
        "next_step": (
            "Classify the two unresolved .rdata RVA matches by exact data/xref provenance or trace runtime-generated/relocated callback registration paths; "
            "continue selected-wheel data-pointer persistence independently."
        ),
    }


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=Path("evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(load(args.upstream))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
