#!/usr/bin/env python3
"""Close the branch-equivalent FUN_00765c40 wheel+0x678 interior aliases.

The selected-object identity comes from the merged FUN_00765c40 P1D handoff.
This pass pins two finite PC-retail machine windows that walk four wheel
interiors with the 0xa80 stride, store the interior pointer only in a stack
local, read the wheel+0x420 child pointer, and write wheel+0x670/+0x678.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40WheelInteriorAliasClosure/1"
HANDOFF_FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

WINDOWS = {
    "branch_a": (0x00765CDE, 0x00765D67, 43, 137, "121f38a8c68794ca54bbae3e21f06628e002bc35f06c4803f77358d8e8c37012"),
    "branch_b": (0x00765D67, 0x00765DF2, 44, 139, "397e90320df096bfb209a003e4bed7e8b4354a8640dc81b971728874e07ce887"),
    "scalar_callee_prefix": (0x00758AD0, 0x00758ADE, 6, 14, "890d669a54d968f9d24ea7ab54bbe8d3ff20317bedb966ffc346250654629882"),
}

ANCHORS = {
    "branch_a": {
        0x00765CDE: ("lea", "eax,[esi+0xa78]"),
        0x00765CE4: ("mov", "DWORD PTR [ebp-0xc],eax"),
        0x00765CF7: ("fstp", "QWORD PTR [eax-0x8]"),
        0x00765CFC: ("mov", "eax,DWORD PTR [eax-0x258]"),
        0x00765D08: ("mov", "ecx,esi"),
        0x00765D3B: ("fstp", "DWORD PTR [esp]"),
        0x00765D3E: ("call", "0x758ad0"),
        0x00765D43: ("mov", "ecx,DWORD PTR [ebp-0xc]"),
        0x00765D46: ("fstp", "QWORD PTR [ecx]"),
        0x00765D55: ("add", "eax,0xa80"),
        0x00765D5D: ("mov", "DWORD PTR [ebp-0xc],eax"),
    },
    "branch_b": {
        0x00765D67: ("lea", "ecx,[esi+0xa78]"),
        0x00765D6D: ("mov", "DWORD PTR [ebp-0xc],ecx"),
        0x00765D83: ("mov", "eax,DWORD PTR [ecx-0x258]"),
        0x00765D9C: ("fstp", "QWORD PTR [ecx-0x8]"),
        0x00765DA4: ("push", "ecx"),
        0x00765DA8: ("mov", "ecx,esi"),
        0x00765DC9: ("fstp", "DWORD PTR [esp]"),
        0x00765DCC: ("call", "0x758ad0"),
        0x00765DD1: ("mov", "edx,DWORD PTR [ebp-0xc]"),
        0x00765DD4: ("mov", "ecx,DWORD PTR [ebp-0xc]"),
        0x00765DD7: ("fstp", "QWORD PTR [edx]"),
        0x00765DE4: ("add", "ecx,0xa80"),
        0x00765DED: ("mov", "DWORD PTR [ebp-0xc],ecx"),
    },
    "scalar_callee_prefix": {
        0x00758AD0: ("push", "ebp"),
        0x00758AD1: ("mov", "ebp,esp"),
        0x00758AD3: ("fld", "DWORD PTR [ebp+0x8]"),
        0x00758AD6: ("sub", "esp,0x8"),
        0x00758AD9: ("fabs", ""),
        0x00758ADB: ("lea", "ecx,[ebp+0x8]"),
    },
}

INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def norm(text: str) -> str:
    return " ".join(text.split()).lower()


def load_handoff(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != HANDOFF_FORMAT or not payload.get("ready"):
        raise ValueError("unexpected or unready FUN_00765c40 handoff contract")
    if payload.get("authority", {}).get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("FUN_00765c40 handoff retail identity drift")
    carrier = payload.get("carrier", {})
    if (
        carrier.get("function") != "FUN_00765c40"
        or carrier.get("entry") != "0x00765c40"
        or carrier.get("receiver_domain") != "HDVehicle"
    ):
        raise ValueError("FUN_00765c40 carrier identity drift")
    if payload.get("selected_slot3", {}).get("absolute_target") != "HDVehicle+0x28b8":
        raise ValueError("selected slot3 target drift")
    if payload.get("adjudication", {}).get("fun00765c40_exact_hdvehicle_carrier_handoff_complete") is not True:
        raise ValueError("FUN_00765c40 exact-HDVehicle handoff is not complete")
    return payload


def disassemble(executable: Path, start: int, stop: int, objdump: str) -> list[dict]:
    proc = subprocess.run(
        [objdump, "-d", "-Mintel", f"--start-address=0x{start:x}", f"--stop-address=0x{stop:x}", str(executable)],
        text=True,
        capture_output=True,
        errors="replace",
    )
    if proc.returncode:
        raise ValueError(f"objdump failed: {proc.stderr.strip()}")
    rows = []
    for line in proc.stdout.splitlines():
        match = INSN_RE.match(line)
        if not match:
            continue
        rows.append(
            {
                "address": int(match.group(1), 16),
                "bytes": bytes.fromhex(match.group(2)),
                "mnemonic": match.group(3).lower(),
                "operands": match.group(4).strip(),
            }
        )
    return rows


def verify_window(name: str, rows: list[dict]) -> dict[int, dict]:
    start, stop, expected_count, expected_bytes, expected_sha = WINDOWS[name]
    blob = b"".join(row["bytes"] for row in rows)
    actual_sha = hashlib.sha256(blob).hexdigest()
    if len(rows) != expected_count or len(blob) != expected_bytes or actual_sha != expected_sha:
        raise ValueError(
            f"{name} machine-window drift: count={len(rows)} bytes={len(blob)} sha={actual_sha}"
        )
    by_address = {row["address"]: row for row in rows}
    for address, (mnemonic, operands) in ANCHORS[name].items():
        row = by_address.get(address)
        if row is None:
            raise ValueError(f"{name} missing anchor 0x{address:08x}")
        if row["mnemonic"] != mnemonic or norm(row["operands"]) != norm(operands):
            raise ValueError(f"{name} anchor drift at 0x{address:08x}: {row}")
    return by_address


def analyze(executable: Path, handoff_path: Path, objdump: str = "objdump") -> dict:
    load_handoff(handoff_path)
    digest = sha256(executable)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")

    verified = {}
    window_rows = {}
    for name, (start, stop, _, _, _) in WINDOWS.items():
        rows = disassemble(executable, start, stop, objdump)
        window_rows[name] = rows
        verified[name] = verify_window(name, rows)

    # Both branches materialize wheel+0x678 and advance by the exact wheel stride.
    interior_offsets = [0xA78 + index * 0xA80 for index in range(4)]
    if interior_offsets != [0xA78, 0x14F8, 0x1F78, 0x29F8]:
        raise ValueError("wheel+0x678 interior receiver arithmetic drift")
    wheel_bases = [0x400 + index * 0xA80 for index in range(4)]
    if any(interior - wheel != 0x678 for interior, wheel in zip(interior_offsets, wheel_bases)):
        raise ValueError("interior aliases no longer normalize to wheel+0x678")

    selected_wheel = wheel_bases[3]
    selected_interior = interior_offsets[3]
    if selected_wheel != 0x2380 or selected_interior != 0x29F8:
        raise ValueError("selected slot3 interior identity drift")

    selected_writes = [selected_interior - 8, selected_interior]
    if selected_writes != [0x29F0, 0x29F8]:
        raise ValueError("selected slot3 interior write normalization drift")
    target_start, target_end = 0x28B8, 0x28BF
    write_ranges = [(selected_writes[0], selected_writes[0] + 7), (selected_writes[1], selected_writes[1] + 7)]
    if any(start <= target_end and end >= target_start for start, end in write_ranges):
        raise ValueError("wheel+0x678 interior writes unexpectedly overlap selected target")

    # The child load is interior-0x258 == wheel+0x420 in both branches.
    if 0x678 - 0x258 != 0x420:
        raise ValueError("wheel child-load normalization drift")
    selected_child_field = selected_wheel + 0x420
    if selected_child_field != 0x27A0:
        raise ValueError("selected child-field absolute offset drift")

    # Branch B briefly pushes ECX while it is the interior alias, but the exact
    # top stack word is overwritten with the scalar argument before the call.
    branch_b = verified["branch_b"]
    if not (
        branch_b[0x00765DA4]["mnemonic"] == "push"
        and norm(branch_b[0x00765DA4]["operands"]) == "ecx"
        and branch_b[0x00765DC9]["mnemonic"] == "fstp"
        and norm(branch_b[0x00765DC9]["operands"]) == "dword ptr [esp]"
        and branch_b[0x00765DCC]["mnemonic"] == "call"
    ):
        raise ValueError("transient stack-alias overwrite proof drift")

    # Before that call ECX is set to the exact HDVehicle root. FUN_00758ad0
    # reads only its stack argument and overwrites ECX at 0x758adb before any
    # incoming-ECX use can occur.
    scalar_prefix = verified["scalar_callee_prefix"]
    first_ecx_rows = [row for row in window_rows["scalar_callee_prefix"] if re.search(r"\becx\b", row["operands"], re.I)]
    if len(first_ecx_rows) != 1 or first_ecx_rows[0]["address"] != 0x00758ADB:
        raise ValueError("FUN_00758ad0 incoming-ECX kill surface drift")
    if scalar_prefix[0x00758ADB]["mnemonic"] != "lea":
        raise ValueError("FUN_00758ad0 no longer overwrites ECX before use")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "upstream_contracts": [HANDOFF_FORMAT],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "machine_transfer_adjudicates": True,
        },
        "scope": {
            "branch_a": {
                "start": "0x00765cde",
                "end_exclusive": "0x00765d67",
                "instruction_count": 43,
                "machine_byte_count": 137,
                "machine_bytes_sha256": WINDOWS["branch_a"][4],
            },
            "branch_b": {
                "start": "0x00765d67",
                "end_exclusive": "0x00765df2",
                "instruction_count": 44,
                "machine_byte_count": 139,
                "machine_bytes_sha256": WINDOWS["branch_b"][4],
            },
            "scalar_callee_prefix": {
                "function": "FUN_00758ad0",
                "start": "0x00758ad0",
                "end_exclusive": "0x00758ade",
                "instruction_count": 6,
                "machine_byte_count": 14,
                "machine_bytes_sha256": WINDOWS["scalar_callee_prefix"][4],
            },
        },
        "wheel_interior_alias": {
            "per_wheel_offset": "+0x678",
            "vehicle_relative_offsets": ["+0x0a78", "+0x14f8", "+0x1f78", "+0x29f8"],
            "selected_slot3_receiver": "HDVehicle+0x29f8 = wheel+0x678",
            "stack_local_slot": "[ebp-0xc]",
            "stack_local_pointer_store_sites": ["0x00765ce4", "0x00765d5d", "0x00765d6d", "0x00765ded"],
            "persistent_or_nonlocal_pointer_store_found": False,
            "selected_slot3_write_offsets": ["HDVehicle+0x29f0 = wheel+0x670 qword", "HDVehicle+0x29f8 = wheel+0x678 qword"],
            "selected_target_overlap": False,
        },
        "child_pointer_load": {
            "expression": "[wheel+0x678-0x258] = [wheel+0x420]",
            "branch_a_site": "0x00765cfc",
            "branch_b_site": "0x00765d83",
            "selected_slot3_child_field": "HDVehicle+0x27a0 = wheel+0x420",
            "child_pointer_forward_to_call_found": False,
            "child_pointer_store_found": False,
        },
        "transient_stack_alias": {
            "site": "0x00765da4",
            "instruction": "push ecx",
            "value_at_site": "wheel+0x678 interior pointer",
            "overwrite_site": "0x00765dc9",
            "overwrite_instruction": "fstp DWORD PTR [esp]",
            "next_call_site": "0x00765dcc",
            "callee": "FUN_00758ad0",
            "pointer_reaches_callee_stack_argument": False,
            "persistent_escape": False,
        },
        "scalar_call_ecx": {
            "caller_sites": ["0x00765d08", "0x00765da8"],
            "caller_value": "ECX=ESI=HDVehicle",
            "callee": "FUN_00758ad0",
            "callee_incoming_ecx_read_before_overwrite": False,
            "callee_ecx_overwrite_site": "0x00758adb",
            "callee_ecx_overwrite": "lea ecx,[ebp+0x8]",
            "hdvehicle_pointer_consumed_as_object_receiver": False,
        },
        "adjudication": {
            "fun00765c40_wheel_678_interior_alias_subset_complete": True,
            "fun00765c40_selected_slot3_interior_alias_reached": True,
            "fun00765c40_selected_slot3_interior_persistent_escape_found": False,
            "fun00765c40_selected_slot3_child_pointer_forward_found": False,
            "fun00765c40_transient_stack_pointer_copy_found": True,
            "fun00765c40_transient_stack_pointer_copy_reaches_callee": False,
            "fun00758ad0_consumes_hdvehicle_receiver": False,
            "other_fun00765c40_derived_aliases_ruled_out": False,
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
            "This closes only the two branch-equivalent wheel+0x678 interior-pointer loops in FUN_00765c40 and the immediate scalar-call boundary.",
            "The branch-B push of the interior pointer is a transient stack scratch copy that is overwritten before FUN_00758ad0; it is recorded rather than silently discarded.",
            "Other FUN_00765c40 derived pointers, runtime/generated pointers, callbacks, indirect entry and callee-created aliases remain open.",
        ],
        "next_step": "Inventory the remaining FUN_00765c40 LEA-derived pointer families after 0x00765df2 and classify which are wheel-relative, HDVehicle-local, BODY-child, stack-only, or callee-facing before composing the carrier-level register/storage gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.handoff, args.objdump)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
