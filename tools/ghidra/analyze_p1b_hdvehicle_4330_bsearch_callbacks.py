#!/usr/bin/env python3
"""Hash-locked machine analyzer for the two retail _bsearch comparator registrations."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330BsearchCallbackClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
BSEARCH = 0x0090421D
CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}


def parse_pe(blob: bytes):
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE image")
    nsec = struct.unpack_from("<H", blob, pe + 6)[0]
    opt_size = struct.unpack_from("<H", blob, pe + 20)[0]
    opt = pe + 24
    image_base = struct.unpack_from("<I", blob, opt + 28)[0]
    sec = opt + opt_size
    sections = []
    for i in range(nsec):
        off = sec + i * 40
        name = blob[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
        vsize, rva, raw_size, raw_off = struct.unpack_from("<IIII", blob, off + 8)
        sections.append({"name": name, "rva": rva, "span": max(vsize, raw_size), "raw_off": raw_off, "raw_size": raw_size})
    return image_base, sections


def va_to_off(va: int, image_base: int, sections):
    rva = va - image_base
    for sec in sections:
        if sec["rva"] <= rva < sec["rva"] + sec["raw_size"]:
            return sec["raw_off"] + (rva - sec["rva"])
    raise ValueError(f"VA not file-backed: 0x{va:08x}")


def off_to_va(off: int, image_base: int, sections):
    for sec in sections:
        if sec["raw_off"] <= off < sec["raw_off"] + sec["raw_size"]:
            return image_base + sec["rva"] + (off - sec["raw_off"])
    return None


def require_bytes(blob, image_base, sections, va, expected_hex):
    expected = bytes.fromhex(expected_hex)
    off = va_to_off(va, image_base, sections)
    actual = blob[off:off + len(expected)]
    if actual != expected:
        raise ValueError(f"byte drift at 0x{va:08x}: {actual.hex()} != {expected.hex()}")


def build(exe: Path) -> dict:
    blob = exe.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != RETAIL_SHA256:
        raise ValueError(f"retail hash mismatch: {sha}")
    image_base, sections = parse_pe(blob)

    calls = []
    for off in range(len(blob) - 5):
        if blob[off] != 0xE8:
            continue
        site = off_to_va(off, image_base, sections)
        if site is None:
            continue
        rel = struct.unpack_from("<i", blob, off + 1)[0]
        if site + 5 + rel == BSEARCH:
            calls.append(site)
    if calls != [0x0053C2DA, 0x00A5DF75]:
        raise ValueError(f"_bsearch callsite drift: {[hex(x) for x in calls]}")

    # Weird decompiler site: FUN_0053c2c0 establishes EBP, tail-jumps to a thunk
    # that pre-pushes comparator 0x0053c280, then tail-jumps into the bsearch body.
    require_bytes(blob, image_base, sections, 0x0053C2C0, "55 8b ec")
    require_bytes(blob, image_base, sections, 0x0053C2CD, "e9 b4 db ee ff")
    require_bytes(blob, image_base, sections, 0x00429E86, "68 80 c2 53 00 eb 0b")
    require_bytes(blob, image_base, sections, 0x00429E98, "e9 35 24 11 00")
    require_bytes(blob, image_base, sections, 0x0053C2D2, "6a 04 50 51 8d 45 08 50 e8 3e 7f 3c 00")
    require_bytes(blob, image_base, sections, 0x0053C280, "55 8b ec 8b 4d 0c 8b 45 08")

    # Conventional fixed comparator site.
    require_bytes(blob, image_base, sections, 0x00A5DF62, "68 20 df a5 00")
    require_bytes(blob, image_base, sections, 0x00A5DF69, "6a 04 51 83 c0 10 50 8d 54 24 24 52 e8 a3 62 ea ff")
    require_bytes(blob, image_base, sections, 0x00A5DF20, "8b 44 24 04 8b 4c 24 08 0f b7 00 0f b7 11 2b c2 c3")

    comparators = [0x0053C280, 0x00A5DF20]
    hits = sorted(set(comparators) & CARRIERS)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": RETAIL_SHA256,
            "evidence_kind": "whole-PE rel32 call scan plus exact machine-byte provenance",
        },
        "bsearch": {"target": f"0x{BSEARCH:08x}", "physical_callsite_count": len(calls), "callsites": [f"0x{x:08x}" for x in calls]},
        "registrations": [
            {
                "callsite": "0x0053c2da",
                "comparator": "0x0053c280",
                "provenance": [
                    "0x0053c2c0 push ebp; mov ebp,esp",
                    "0x0053c2cd tail-jmp 0x00429e86",
                    "0x00429e86 push 0x0053c280",
                    "0x00429e98 tail-jmp 0x0053c2d2",
                    "0x0053c2d2 pushes size/nmemb/base/key then calls _bsearch",
                ],
                "decompiler_unaff_retaddr_is_artifact": True,
            },
            {
                "callsite": "0x00a5df75",
                "comparator": "0x00a5df20",
                "provenance": ["0x00a5df62 push 0x00a5df20", "0x00a5df69..0x00a5df74 push size/nmemb/base/key"],
                "comparator_behavior": "unsigned 16-bit key minus unsigned 16-bit element",
            },
        ],
        "canonical_p1b_carriers": [f"0x{x:08x}" for x in sorted(CARRIERS)],
        "exact_carrier_comparator_hits": [f"0x{x:08x}" for x in hits],
        "adjudication": {
            "bsearch_physical_callsite_surface_complete": True,
            "bsearch_physical_callsite_count": 2,
            "bsearch_comparator_provenance_complete": True,
            "bsearch_comparator_count": 2,
            "bsearch_exact_p1b_carrier_hit_found": bool(hits),
            "bsearch_exact_p1b_carrier_hit_count": len(hits),
            "remaining_callback_api_families_ruled_out": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two retail _bsearch comparator registrations.",
            "Other callback families and generic/runtime-generated function-pointer paths remain outside this contract.",
            "No function identity is inferred from decompiler calling-convention guesses; exact retail bytes adjudicate the comparator provenance.",
        ],
        "next_step": "Compose _bsearch into the runtime callback aggregate, then continue remaining callback families and runtime-generated/copied/encoded exact-carrier pointer paths.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    result = build(args.exe)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
