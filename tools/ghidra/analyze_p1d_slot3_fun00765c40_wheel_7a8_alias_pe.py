#!/usr/bin/env python3
"""Close the FUN_00765c40 four-wheel wheel+0x7a8 register-only alias loop."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00765c40Wheel7a8AliasClosure/1"
HANDOFF_FORMAT = "SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

INIT = (0x00765FBE, 0x00765FCD, 4, 15, "bee86cb6900505f103c284f893576dbdda0fd9b0a5ae6ef3f509e3e70044ddce")
LOOP = (0x00765FF1, 0x00766081, 55, 144, "66ef07bd668d00b964a16c782d83c40dedca8fd156b057a8de617487aecb1de4")
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")
ECX_RE = re.compile(r"\becx\b", re.I)
CALL_RE = re.compile(r"^call\b", re.I)

EXPECTED_ECX_USES = {
    0x00765FBE: ("lea", "ecx,[esi+0xba8]"),
    0x00766062: ("add", "ecx,0xa80"),
    0x0076606B: ("fstp", "QWORD PTR [ecx-0xa88]"),
    0x00766073: ("fst", "QWORD PTR [ecx-0xa80]"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text: str) -> str:
    return " ".join(text.split()).lower()


def load_handoff(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != HANDOFF_FORMAT or not payload.get("ready"):
        raise ValueError("unexpected or unready FUN_00765c40 handoff contract")
    if payload.get("authority", {}).get("retail_executable_sha256") != PE_SHA256:
        raise ValueError("FUN_00765c40 handoff retail identity drift")
    carrier = payload.get("carrier", {})
    if carrier.get("function") != "FUN_00765c40" or carrier.get("receiver_domain") != "HDVehicle":
        raise ValueError("FUN_00765c40 HDVehicle identity drift")
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
        if match:
            rows.append(
                {
                    "address": int(match.group(1), 16),
                    "bytes": bytes.fromhex(match.group(2)),
                    "mnemonic": match.group(3).lower(),
                    "operands": match.group(4).strip(),
                }
            )
    return rows


def verify_window(rows: list[dict], expected: tuple, label: str) -> None:
    start, stop, expected_count, expected_bytes, expected_sha = expected
    blob = b"".join(row["bytes"] for row in rows)
    actual_sha = hashlib.sha256(blob).hexdigest()
    if len(rows) != expected_count or len(blob) != expected_bytes or actual_sha != expected_sha:
        raise ValueError(f"{label} machine-window drift: count={len(rows)} bytes={len(blob)} sha={actual_sha}")


def analyze(executable: Path, handoff_path: Path, objdump: str = "objdump") -> dict:
    load_handoff(handoff_path)
    digest = sha256(executable)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail PE SHA-256: {digest}")

    init_rows = disassemble(executable, INIT[0], INIT[1], objdump)
    loop_rows = disassemble(executable, LOOP[0], LOOP[1], objdump)
    verify_window(init_rows, INIT, "wheel+0x7a8 init")
    verify_window(loop_rows, LOOP, "wheel+0x7a8 loop")
    all_rows = init_rows + loop_rows
    by_address = {row["address"]: row for row in all_rows}

    ecx_uses = {row["address"]: row for row in all_rows if ECX_RE.search(row["operands"])}
    if set(ecx_uses) != set(EXPECTED_ECX_USES):
        raise ValueError(f"wheel+0x7a8 ECX-use surface drift: {[hex(x) for x in ecx_uses]}")
    for address, (mnemonic, operands) in EXPECTED_ECX_USES.items():
        row = by_address[address]
        if row["mnemonic"] != mnemonic or norm(row["operands"]) != norm(operands):
            raise ValueError(f"wheel+0x7a8 anchor drift at 0x{address:08x}: {row}")
    if any(CALL_RE.match(row["mnemonic"]) for row in loop_rows):
        raise ValueError("wheel+0x7a8 loop unexpectedly calls out")

    wheel_bases = [0x400 + index * 0xA80 for index in range(4)]
    aliases = [0xBA8 + index * 0xA80 for index in range(4)]
    if aliases != [0xBA8, 0x1628, 0x20A8, 0x2B28]:
        raise ValueError("wheel+0x7a8 alias arithmetic drift")
    if any(alias - wheel != 0x7A8 for alias, wheel in zip(aliases, wheel_bases)):
        raise ValueError("wheel+0x7a8 normalization drift")
    if wheel_bases[3] != 0x2380 or aliases[3] != 0x2B28:
        raise ValueError("selected slot3 wheel+0x7a8 identity drift")

    selected_writes = [aliases[3] - 8, aliases[3]]
    if selected_writes != [0x2B20, 0x2B28]:
        raise ValueError("selected wheel+0x7a8 write normalization drift")
    target_start, target_end = 0x28B8, 0x28BF
    if any(start <= target_end and start + 7 >= target_start for start in selected_writes):
        raise ValueError("wheel+0x7a8 selected writes unexpectedly overlap target")

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
            "init": {
                "start": "0x00765fbe",
                "end_exclusive": "0x00765fcd",
                "instruction_count": 4,
                "machine_byte_count": 15,
                "machine_bytes_sha256": INIT[4],
            },
            "loop": {
                "start": "0x00765ff1",
                "end_exclusive": "0x00766081",
                "instruction_count": 55,
                "machine_byte_count": 144,
                "machine_bytes_sha256": LOOP[4],
            },
        },
        "wheel_alias": {
            "init_site": "0x00765fbe",
            "init_instruction": "lea ecx,[esi+0xba8]",
            "per_wheel_offset": "+0x7a8",
            "stride_site": "0x00766062",
            "stride_instruction": "add ecx,0xa80",
            "vehicle_relative_aliases": ["+0x0ba8", "+0x1628", "+0x20a8", "+0x2b28"],
            "selected_slot3_alias": "HDVehicle+0x2b28 = wheel+0x7a8",
            "pointer_store_found": False,
            "pointer_push_found": False,
            "direct_call_count": 0,
        },
        "writes": {
            "machine_forms": ["[ecx-0xa88] qword", "[ecx-0xa80] qword"],
            "per_wheel_offsets": ["+0x7a0 qword", "+0x7a8 qword"],
            "selected_slot3_vehicle_relative_offsets": ["+0x2b20 qword", "+0x2b28 qword"],
            "selected_target_overlap": False,
        },
        "adjudication": {
            "fun00765c40_wheel_7a8_register_alias_subset_complete": True,
            "fun00765c40_selected_slot3_wheel_7a8_alias_reached": True,
            "fun00765c40_selected_slot3_wheel_7a8_pointer_escape_found": False,
            "fun00765c40_wheel_7a8_selected_target_writer_found": False,
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
            "This closes only the register-only wheel+0x7a8 four-iteration loop at 0x00765fbe/0x00765ff1..0x0076607f.",
            "Vehicle-local and physics-structure pointers later in FUN_00765c40 are not reclassified as wheel aliases without separate evidence.",
            "Runtime/generated pointers, callbacks, indirect entry and callee-created aliases remain open.",
        ],
        "next_step": "Classify the remaining post-0x00766081 FUN_00765c40 derived pointer families (+0x3430/+0x35c8/+0x35f8/+0x36e0/+0x6730) by exact storage/callee lifetime, without treating numeric proximity as wheel identity.",
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
