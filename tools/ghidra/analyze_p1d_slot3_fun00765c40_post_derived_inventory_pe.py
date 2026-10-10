#!/usr/bin/env python3
"""Inventory post-wheel derived pointer families in FUN_00765c40 and the +0x6730 callees."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40PostDerivedInventory/1"
HANDOFF_FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")
WINDOWS = {
    "manager_6730": (0x00765ED4, 0x00765F29, 22, 85, "76663fd72c8ed75e938e5383e383130c146af33296e50993382a7c37f6f1f579"),
    "local_12": (0x00766081, 0x007663C0, 236, 831, "57c0b69ac7b952b42b82fdd2fd5e6be5f113b8cbfa653570ac0f08b24afa8bf5"),
    "local_4": (0x007663C0, 0x00766505, 84, 325, "f8c0651194f031f12f8739b964e426a64c08417f5ebd49dac066cb1143607ece"),
    "a62940": (0x00A62940, 0x00A62B39, 158, 501, "01cc38b6fe9f5cd1cbc061a0c8516ee9425141476870319a6468d12ea0a45e75"),
    "a628a0": (0x00A628A0, 0x00A6293A, 53, 152, "832eb82f6465cad7cdbfe0bab1b33bee970d424634d470136f6c2a68850ab96b"),
}
ANCHORS = {
    0x00765ED8: ("lea", "ecx,[esi+0x6730]"),
    0x00765EE6: ("call", "0xa62940"),
    0x00765EF5: ("lea", "ecx,[esi+0x6730]"),
    0x00765EFB: ("call", "0xa628a0"),
    0x00766081: ("lea", "edi,[esi+0x35c8]"),
    0x00766089: ("lea", "eax,[esi+0x35f8]"),
    0x00766091: ("lea", "ecx,[esi+0x3430]"),
    0x00766099: ("mov", "DWORD PTR [ebp-0xc],edi"),
    0x0076609C: ("mov", "DWORD PTR [ebp-0x14],eax"),
    0x0076609F: ("mov", "DWORD PTR [ebp-0x10],ecx"),
    0x007663CD: ("lea", "ecx,[esi+0x36e0]"),
    0x007663D3: ("mov", "DWORD PTR [ebp-0xc],ecx"),
    0x00A62947: ("mov", "edi,ecx"),
    0x00A62A20: ("mov", "DWORD PTR [eax+0x24],edi"),
    0x00A62A63: ("mov", "DWORD PTR [esi+0x34],edi"),
    0x00A628A5: ("mov", "esi,ecx"),
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def norm(text: str) -> str:
    return " ".join(text.split()).lower()

def disassemble(executable: Path, start: int, stop: int, objdump: str) -> list[dict]:
    proc = subprocess.run([objdump, "-d", "-Mintel", f"--start-address=0x{start:x}", f"--stop-address=0x{stop:x}", str(executable)], text=True, capture_output=True, errors="replace")
    if proc.returncode:
        raise ValueError(f"objdump failed: {proc.stderr.strip()}")
    rows = []
    for line in proc.stdout.splitlines():
        m = INSN_RE.match(line)
        if m:
            rows.append({"address": int(m.group(1), 16), "bytes": bytes.fromhex(m.group(2)), "mnemonic": m.group(3).lower(), "operands": m.group(4).strip()})
    return rows

def verify(rows: list[dict], spec: tuple, label: str) -> None:
    _, _, count, byte_count, digest = spec
    blob = b"".join(row["bytes"] for row in rows)
    actual = hashlib.sha256(blob).hexdigest()
    if (len(rows), len(blob), actual) != (count, byte_count, digest):
        raise ValueError(f"{label} drift: count={len(rows)} bytes={len(blob)} sha={actual}")

def analyze(executable: Path, handoff: Path, objdump: str = "objdump") -> dict:
    contract = json.loads(handoff.read_text(encoding="utf-8"))
    if contract.get("format") != HANDOFF_FORMAT or not contract.get("ready"):
        raise ValueError("unexpected FUN_00765c40 handoff")
    if contract.get("authority", {}).get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("handoff retail identity drift")
    digest = sha256(executable)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")

    rows_by_window = {}
    all_rows = {}
    for label, spec in WINDOWS.items():
        rows = disassemble(executable, spec[0], spec[1], objdump)
        verify(rows, spec, label)
        rows_by_window[label] = rows
        all_rows.update({row["address"]: row for row in rows})
    for address, (mnemonic, operands) in ANCHORS.items():
        row = all_rows.get(address)
        if not row or row["mnemonic"] != mnemonic or norm(row["operands"]) != norm(operands):
            raise ValueError(f"anchor drift at 0x{address:08x}: {row}")

    # After ESI becomes the +0x6730 receiver in FUN_00a628a0, it is never stored/pushed as a value.
    a628a0 = rows_by_window["a628a0"]
    later_esi_value_uses = [row for row in a628a0 if row["address"] > 0x00A628A5 and (re.search(r",\s*esi\b", row["operands"], re.I) or (row["mnemonic"] == "push" and norm(row["operands"]) == "esi"))]
    if later_esi_value_uses:
        raise ValueError(f"unexpected +0x6730 receiver value escape in FUN_00a628a0: {later_esi_value_uses}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [HANDOFF_FORMAT, "SHIFT.P1D.Slot3Fun00765c40Wheel7a8AliasClosure/1"],
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest, "machine_bytes_adjudicate": True},
        "scope": {label: {"start": f"0x{spec[0]:08x}", "end_exclusive": f"0x{spec[1]:08x}", "instruction_count": spec[2], "decoded_byte_count": spec[3], "machine_bytes_sha256": spec[4]} for label, spec in WINDOWS.items()},
        "families": {
            "hdvehicle_6730": {
                "identity": "HDVehicle+0x6730 local manager/subobject; not a wheel root or wheel-relative alias",
                "caller_sites": ["0x00765ed8 -> FUN_00a62940", "0x00765ef5 -> FUN_00a628a0"],
                "fun00a62940_receiver_alias": "EDI=ECX at 0x00a62947",
                "runtime_created_node_backpointer_stores": ["0x00a62a20 [node+0x24]=HDVehicle+0x6730", "0x00a62a63 [node+0x34]=HDVehicle+0x6730"],
                "fun00a628a0_receiver_alias": "ESI=ECX at 0x00a628a5",
                "fun00a628a0_receiver_value_store_or_push_found": False,
                "selected_slot3_pointer_identity": False,
            },
            "hdvehicle_local_arrays_12": {
                "bases": ["HDVehicle+0x3430", "HDVehicle+0x35c8", "HDVehicle+0x35f8"],
                "materialization_sites": ["0x00766091", "0x00766081", "0x00766089"],
                "stack_cursor_slots": ["[ebp-0x10]", "[ebp-0xc]", "[ebp-0x14]"],
                "iteration_count": 12,
                "strides": ["+0x18", "+0x4", "+0x8"],
                "selected_slot3_pointer_identity": False,
                "callee_lifetime_fully_closed": False,
            },
            "hdvehicle_local_array_4": {
                "base": "HDVehicle+0x36e0",
                "materialization_site": "0x007663cd",
                "stack_cursor_slot": "[ebp-0xc]",
                "iteration_count": 4,
                "stride": "+0x18",
                "selected_slot3_pointer_identity": False,
                "callee_lifetime_fully_closed": False,
            },
        },
        "adjudication": {
            "fun00765c40_post_derived_family_inventory_complete": True,
            "fun00765c40_hdvehicle_6730_nested_receiver_subset_complete": True,
            "fun00765c40_hdvehicle_6730_runtime_backpointer_store_found": True,
            "fun00765c40_hdvehicle_6730_is_selected_slot3_alias": False,
            "fun00765c40_post_derived_selected_slot3_alias_found": False,
            "other_fun00765c40_derived_aliases_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The +0x6730 runtime back-pointer persistence is proven for a distinct HDVehicle-local manager/subobject; it is not promoted to wheel identity by numeric proximity.",
            "The +0x3430/+0x35c8/+0x35f8 and +0x36e0 families are classified as HDVehicle-local array cursors in FUN_00765c40, but their callee-facing lifetimes remain separate work.",
            "Runtime/generated selected-wheel pointers, aggregate copies, callbacks and indirect entry remain open.",
        ],
        "next_step": "Trace the callee-facing lifetimes of the +0x3430/+0x35c8/+0x35f8/+0x36e0 array cursors (FUN_007afd20/FUN_007baa70/FUN_00747b90/FUN_007aefb0) and reject or prove any nonlocal pointer persistence before changing global alias gates.",
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("executable", type=Path)
    p.add_argument("handoff", type=Path)
    p.add_argument("--objdump", default="objdump")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.executable, a.handoff, a.objdump)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
