#!/usr/bin/env python3
"""Extend the pinned P1D exact-entry-root source-storage subset from 15 to 16 carriers.

The 15-carrier source contract remains authoritative for its original set. This
builder consumes the merged FUN_00765c40 carrier handoff and scans only the new
carrier body in the same pinned SHIFT.exe.c export with the same direct root-
assignment grammar. It deliberately does not claim universal derived-alias or
machine-level pointer escape closure.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40SourceStorageReplay/1"
BASE_FORMAT = "SHIFT.P1D.Slot3DirectExactRootStorageSource/1"
HANDOFF_FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SIGNATURE = "void __thiscall FUN_00765c40(void *this,char param_1)"
ROOT = "this"
EXPECTED_EXISTING_ASSIGNMENTS = [
    {"function":"FUN_00758b50","root":"param_1","lhs":"local_2c","text":"local_2c = param_1;","storage":"stack-local"},
    {"function":"FUN_00763570","root":"this","lhs":"local_4c","text":"local_4c = this;","storage":"stack-local"},
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path, expected: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != expected or not payload.get("ready"):
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def extract(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise ValueError(f"missing carrier signature: {signature}")
    tail = text[start + len(signature):]
    match = re.search(r"\n\n[^\n;]*\bFUN_[0-9a-fA-F]+\([^\n]*\)\s*\n\n\{", tail)
    return text[start:] if match is None else text[start:start + len(signature) + match.start()]


def direct_root_assignments(body: str, root: str) -> list[dict]:
    pattern = re.compile(r"^\s*([^=]+?)=\s*(?:\([^;=()]+\)\s*)*" + re.escape(root) + r"\s*;\s*$")
    found = []
    for line in body.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        lhs = match.group(1).strip()
        storage = "stack-local" if lhs.startswith("local_") else "nonlocal-or-unknown"
        found.append({"function":"FUN_00765c40","root":root,"lhs":lhs,"text":line.strip(),"storage":storage})
    return found


def analyze(source: Path, base_path: Path, handoff_path: Path) -> dict:
    digest = sha256(source)
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe.c SHA-256: {digest}")
    base = load(base_path, BASE_FORMAT)
    handoff = load(handoff_path, HANDOFF_FORMAT)

    if base.get("carrier_set", {}).get("count") != 15:
        raise ValueError("base source-storage carrier count drift")
    base_rows = base.get("direct_exact_root_assignments", {}).get("rows")
    if base_rows != EXPECTED_EXISTING_ASSIGNMENTS:
        raise ValueError("base direct exact-root assignment surface drift")
    if base.get("direct_exact_root_assignments", {}).get("persistent_or_unknown_count") != 0:
        raise ValueError("base source-storage subset now has persistent/unknown assignment")
    if base.get("adjudication", {}).get("source_direct_exact_entry_root_assignment_subset_complete") is not True:
        raise ValueError("base source-storage subset is no longer complete")

    carrier = handoff.get("carrier", {})
    if carrier.get("function") != "FUN_00765c40" or carrier.get("entry") != "0x00765c40":
        raise ValueError("FUN_00765c40 handoff identity drift")
    if carrier.get("previous_p1d_exact_carrier_count") != 15 or carrier.get("expanded_p1d_exact_carrier_count") != 16:
        raise ValueError("FUN_00765c40 carrier expansion drift")
    if handoff.get("adjudication", {}).get("p1d_exact_carrier_set_expanded_to_16") is not True:
        raise ValueError("16-carrier expansion is not proven upstream")

    text = source.read_text(encoding="utf-8", errors="replace")
    body = extract(text, SIGNATURE)
    new_rows = direct_root_assignments(body, ROOT)
    if new_rows:
        raise ValueError(f"FUN_00765c40 direct exact-root assignment surface is not empty: {new_rows!r}")

    combined_rows = list(base_rows) + new_rows
    persistent = [row for row in combined_rows if row["storage"] != "stack-local"]
    if persistent:
        raise ValueError(f"persistent/unknown direct exact-root assignment found: {persistent!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [BASE_FORMAT, HANDOFF_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_decompiler_source_sha256": digest,
            "source_is_navigation_crosscheck": True,
            "machine_handoff_owns_fun00765c40_object_identity": True,
        },
        "carrier_expansion": {
            "previous_count": 15,
            "new_count": 16,
            "added_function": "FUN_00765c40",
            "added_entry": "0x00765c40",
        },
        "fun00765c40_source_replay": {
            "signature": SIGNATURE,
            "entry_root": ROOT,
            "direct_exact_root_assignment_count": 0,
            "direct_exact_root_assignments": [],
            "persistent_or_unknown_direct_root_assignment_count": 0,
        },
        "combined_direct_exact_root_assignments": {
            "count": len(combined_rows),
            "rows": combined_rows,
            "persistent_or_unknown_count": len(persistent),
            "persistent_or_unknown_rows": persistent,
        },
        "adjudication": {
            "source_direct_exact_entry_root_assignment_16_carrier_subset_complete": True,
            "fun00765c40_direct_exact_entry_root_assignment_found": False,
            "fun00765c40_direct_exact_entry_root_persistent_store_found": False,
            "source_storage_replay_for_16_carriers_complete": True,
            "derived_alias_storage_ruled_out": False,
            "machine_register_alias_storage_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The completed 16-carrier source-storage replay is exactly the direct exact-entry-root assignment syntax owned by the original 15-carrier contract plus FUN_00765c40; it is not a universal pointer-storage proof.",
            "FUN_00765c40 contains derived addresses such as this+offset assigned to locals; those are outside this exact-root grammar and remain governed by machine side-effect/alias evidence.",
            "Runtime/generated/copied pointers, callee-created aliases, callbacks and indirect entry remain open.",
        ],
        "next_step": "Consume the parallel 16-carrier CALLIND/static-pointer refresh, then trace callee-created/runtime aliases and indirect-entry joins before changing the global stored/escaped-alias gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("base", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.source, args.base, args.handoff)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
