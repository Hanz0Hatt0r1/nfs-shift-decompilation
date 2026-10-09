#!/usr/bin/env python3
"""Verify the exact selected-wheel direct-carrier subset rooted in FUN_00770e80.

PC retail 1.02 machine code is semantic authority. This tool deliberately closes
only two exact selected-wheel paths: FUN_00770e80 -> FUN_00755a60 ->
FUN_00752fc0 and FUN_00770e80 -> FUN_00760b50. It does not claim that all
interprocedural or indirect aliases are exhausted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

FUNCTIONS = {
    "FUN_00770e80": (0x00770E80, 1183),
    "FUN_00755a60": (0x00755A60, 1297),
    "FUN_00760b50": (0x00760B50, 531),
    "FUN_00752fc0": (0x00752FC0, 37),
}

ANCHORS = {
    0x00770EA1: "mov    esi,ecx",
    0x007710A4: "lea    edi,[esi+0x740]",
    0x007710C9: "lea    ecx,[edi-0x340]",
    0x007710CF: "call   0x755a60",
    0x007710DA: "add    edi,0xa80",
    0x007710E0: "cmp    eax,0x4",
    0x00771177: "lea    ecx,[esi+0x2380]",
    0x00771180: "call   0x760b50",
    0x00755A73: "mov    esi,ecx",
    0x00755C04: "lea    ecx,[esi+0x7c8]",
    0x00755DB3: "mov    ecx,esi",
    0x00755DB5: "call   0x752fc0",
    0x00760B6A: "mov    esi,ecx",
    0x00760D02: "mov    ecx,DWORD PTR [esi+0x420]",
    0x00752FC0: "fld    QWORD PTR [ecx+0x7d0]",
    0x00752FE4: "ret",
}

WRITE_SITES = {
    "FUN_00755a60": {
        0x00755C63: 0x7B0, 0x00755C89: 0x7B0, 0x00755CB4: 0x7B0,
        0x00755CD7: 0x7B8, 0x00755CFC: 0x7B8, 0x00755D22: 0x7B8,
        0x00755D42: 0x7C0, 0x00755D68: 0x7C0, 0x00755D91: 0x7C0,
        0x00755CBC: 0x7C8, 0x00755D2A: 0x7C8, 0x00755D99: 0x7C8,
        0x00755E2E: 0x850, 0x00755E5B: 0x7F8, 0x00755E6F: 0x7F8,
        0x00755F64: 0x800,
    },
    "FUN_00760b50": {
        0x00760C44: 0x8B0, 0x00760C8A: 0x8B0,
        0x00760C90: 0x868, 0x00760CC7: 0x868, 0x00760CEE: 0x868,
        0x00760D12: 0x888, 0x00760D56: 0x368,
    },
    "FUN_00752fc0": {0x00752FCC: 0x7D8, 0x00752FDE: 0x5B8},
}

TARGET_LOCAL = 0x538
TARGET_WIDTH = 8

INS_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
CALL_RE = re.compile(r"^call\s+(0x[0-9a-fA-F]+)\b")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def disassemble(executable: Path, start: int, size: int, objdump: str) -> dict[int, str]:
    proc = subprocess.run(
        [objdump, "-d", "-Mintel", f"--start-address=0x{start:x}", f"--stop-address=0x{start+size:x}", str(executable)],
        text=True, capture_output=True, errors="replace",
    )
    if proc.returncode != 0:
        raise ValueError(f"objdump failed: {proc.stderr.strip()}")
    out: dict[int, str] = {}
    for line in proc.stdout.splitlines():
        match = INS_RE.match(line)
        if match:
            out[int(match.group(1), 16)] = match.group(2).strip()
    return out


def norm(text: str) -> str:
    return " ".join(text.split())


def require_anchor(all_ins: dict[int, str], address: int, expected: str) -> None:
    actual = all_ins.get(address)
    if actual is None or norm(actual).lower() != norm(expected).lower():
        raise ValueError(f"anchor drift at 0x{address:08x}: expected {expected!r}, got {actual!r}")


def direct_calls(ins: dict[int, str]) -> list[dict]:
    rows = []
    for address, text in sorted(ins.items()):
        match = CALL_RE.match(text)
        if match:
            rows.append({"site": f"0x{address:08x}", "target": f"0x{int(match.group(1),16):08x}", "text": text})
    return rows


def analyze(executable: Path, objdump: str = "objdump") -> dict:
    digest = sha256(executable)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")

    decoded = {name: disassemble(executable, start, size, objdump) for name, (start, size) in FUNCTIONS.items()}
    all_ins = {}
    for rows in decoded.values():
        all_ins.update(rows)
    for address, expected in ANCHORS.items():
        require_anchor(all_ins, address, expected)
    for fn, sites in WRITE_SITES.items():
        for address in sites:
            if address not in decoded[fn]:
                raise ValueError(f"missing write site 0x{address:08x} in {fn}")

    write_offsets = {fn: sorted(set(sites.values())) for fn, sites in WRITE_SITES.items()}
    if any(TARGET_LOCAL in offsets for offsets in write_offsets.values()):
        raise ValueError("selected local +0x538 unexpectedly appears in bounded write offsets")

    calls_755a60 = direct_calls(decoded["FUN_00755a60"])
    calls_760b50 = direct_calls(decoded["FUN_00760b50"])
    calls_752fc0 = direct_calls(decoded["FUN_00752fc0"])
    if calls_752fc0:
        raise ValueError("FUN_00752fc0 is no longer a leaf")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest, "machine_transfer_adjudicates": True},
        "selected_slot3": {"hdvehicle_offset": "0x2380", "local_target": "+0x538", "absolute_target": "HDVehicle+0x28b8", "width": "f64/qword"},
        "paths": {
            "thermal_loop": {
                "root_function": "FUN_00770e80",
                "receiver_derivation": "EDI=HDVehicle+0x740+slot*0xa80; ECX=EDI-0x340 => HDVehicle+0x400+slot*0xa80",
                "slot3_receiver": "HDVehicle+0x2380",
                "callee": "FUN_00755a60",
                "callee_write_offsets": [f"+0x{x:x}" for x in write_offsets["FUN_00755a60"]],
                "exact_root_forwarded_to": "FUN_00752fc0",
                "leaf_write_offsets": [f"+0x{x:x}" for x in write_offsets["FUN_00752fc0"]],
                "leaf_has_direct_calls": False,
                "target_overlap": False,
            },
            "tire_thermal": {
                "root_function": "FUN_00770e80",
                "slot3_receiver_materializer": "0x00771177 lea ecx,[esi+0x2380]",
                "callee": "FUN_00760b50",
                "callee_write_offsets": [f"+0x{x:x}" for x in write_offsets["FUN_00760b50"]],
                "exact_root_forwarded_to_direct_callee": False,
                "child_receiver_call": "FUN_007ba860 receives [wheel+0x420]",
                "target_overlap": False,
            },
        },
        "call_inventory": {"FUN_00755a60": calls_755a60, "FUN_00760b50": calls_760b50, "FUN_00752fc0": calls_752fc0},
        "adjudication": {
            "slot3_fun00770e80_exact_wheel_direct_carrier_subset_complete": True,
            "fun00755a60_selected_target_writer_found": False,
            "fun00752fc0_selected_target_writer_found": False,
            "fun00760b50_selected_target_writer_found": False,
            "deeper_direct_aliases_ruled_out": False,
            "indirect_callback_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only exact selected-wheel carriers materialized inside FUN_00770e80 and their bounded direct descendants.",
            "Other lifecycle functions, stored aliases, out-of-line chunks, indirect calls and callback carriers remain open.",
            "No numeric offset is promoted to object identity without the exact receiver transfer shown here.",
        ],
        "next_step": "Trace stored/escaped selected-wheel aliases and indirect/callback carriers outside these two FUN_00770e80 direct paths.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--objdump", default="objdump")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, objdump=args.objdump)
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
