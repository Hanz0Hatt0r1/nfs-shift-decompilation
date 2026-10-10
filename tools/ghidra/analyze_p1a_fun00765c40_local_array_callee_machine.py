#!/usr/bin/env python3
"""Verify FUN_00765c40 HDVehicle-local array callee lifetimes for P1.3A.

This is a bounded PC-retail machine proof for the four pointer families already
classified by the merged post-derived inventory as HDVehicle-local, non-wheel
arrays: +0x3430, +0x35c8, +0x35f8 and +0x36e0.  It proves their actual direct
callee/data-use lifetimes do not persist/reconstruct a selected wheel pointer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AFun00765c40LocalArrayCalleeMachineClosure/1"
POST_FORMAT = "SHIFT.P1D.Slot3Fun00765c40PostDerivedInventory/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

BODY_SPECS = {
    "FUN_007afd20": (0x007AFD20, 49, "2e93cc7574546ce67474eac98cfb1b41aad12ff83b23738ae69754b2f7d021cf"),
    "FUN_007baa70": (0x007BAA70, 121, "eed5416afe216f33c24d437e8ed50a7773c2fee316a4f1c841ef0e6bbd5e817e"),
    "FUN_00747b90": (0x00747B90, 36, "e2c7ab1cffe9f74b40aa5706acf142958fcb2fc37c5427550f9266960410155d"),
    "FUN_007aefb0": (0x007AEFB0, 83, "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"),
}

EXPECTED_BYTES = {
    0x00766081: "8dbec8350000",       # EDI = HDVehicle+0x35c8
    0x00766089: "8d86f8350000",       # EAX = HDVehicle+0x35f8
    0x00766091: "8d8e30340000",       # ECX = HDVehicle+0x3430
    0x00766099: "897df48945ec894df0", # store three cursors to stack locals
    0x007660BE: "e85d9c0400",         # -> FUN_007afd20
    0x00766188: "8b55ecdd12",         # EDX = +0x35f8 cursor; FST qword [EDX]
    0x00766353: "8bcf",               # ECX = EDI (+0x35c8 cursor)
    0x00766365: "e806470500",         # -> FUN_007baa70
    0x007663A8: "8345ec088345f01883c704836df801897df4", # 12-loop cursor increments
    0x007663CD: "8d8ee0360000",       # ECX = HDVehicle+0x36e0
    0x007663EA: "0550fdffff",         # current +0x36e0 cursor - 0x2b0 => +0x3430 family
    0x007663F6: "e8b58b0400",         # -> FUN_007aefb0
    0x00766460: "8b55f4",             # EDX = +0x36e0 cursor
    0x0076646A: "e82117feff",         # -> FUN_00747b90
    0x007664ED: "8bcf",               # ECX = chassis BODY, not local-array cursor
    0x007664F2: "e879450500",         # -> FUN_007baa70 on chassis BODY
    0x007664F7: "8345f418836df801",   # four-loop +0x18 stride / count--
    0x007AFD2C: "e87ff2ffff",         # FUN_007afd20 -> FUN_007aefb0
}

EXPECTED_CALL_TARGETS = {
    0x007660BE: 0x007AFD20,
    0x00766365: 0x007BAA70,
    0x007663F6: 0x007AEFB0,
    0x0076646A: 0x00747B90,
    0x007664F2: 0x007BAA70,
    0x007AFD2C: 0x007AEFB0,
}


def parse_pe32(data: bytes):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    table = opt + opt_size
    sections = []
    for i in range(count):
        off = table + i * 40
        sections.append({
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
        })
    return image_base, sections


def read_va(data: bytes, va: int, size: int) -> bytes:
    base, sections = parse_pe32(data)
    rva = va - base
    for section in sections:
        if section["rva"] <= rva and rva + size <= section["rva"] + section["raw_size"]:
            off = section["raw_offset"] + (rva - section["rva"])
            return data[off:off + size]
    raise ValueError(f"VA 0x{va:08x} is not file-backed")


def rel32_target(data: bytes, site: int) -> int:
    raw = read_va(data, site, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"0x{site:08x}: expected CALL rel32")
    rel = struct.unpack_from("<i", raw, 1)[0]
    return site + 5 + rel


def verify_post_inventory(post: dict) -> None:
    if post.get("format") != POST_FORMAT or post.get("ready") is not True:
        raise ValueError("unexpected/unready post-derived inventory")
    if post.get("authority", {}).get("retail_executable_sha256") != RETAIL_SHA256:
        raise ValueError("post-derived inventory retail hash drift")
    fam = post.get("families", {})
    a12 = fam.get("hdvehicle_local_arrays_12", {})
    if a12.get("bases") != ["HDVehicle+0x3430", "HDVehicle+0x35c8", "HDVehicle+0x35f8"]:
        raise ValueError("12-loop local-array bases drift")
    if a12.get("iteration_count") != 12 or a12.get("strides") != ["+0x18", "+0x4", "+0x8"]:
        raise ValueError("12-loop geometry drift")
    if a12.get("selected_slot3_pointer_identity") is not False or a12.get("callee_lifetime_fully_closed") is not False:
        raise ValueError("12-loop upstream identity/lifetime premise drift")
    a4 = fam.get("hdvehicle_local_array_4", {})
    if a4.get("base") != "HDVehicle+0x36e0" or a4.get("iteration_count") != 4 or a4.get("stride") != "+0x18":
        raise ValueError("4-loop local-array geometry drift")
    if a4.get("selected_slot3_pointer_identity") is not False or a4.get("callee_lifetime_fully_closed") is not False:
        raise ValueError("4-loop upstream identity/lifetime premise drift")


def analyze(executable: Path, post_path: Path) -> dict:
    data = executable.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {actual_sha}")
    post = json.loads(post_path.read_text(encoding="utf-8"))
    verify_post_inventory(post)

    windows = []
    for va, expected_hex in sorted(EXPECTED_BYTES.items()):
        expected = bytes.fromhex(expected_hex)
        actual = read_va(data, va, len(expected))
        if actual != expected:
            raise ValueError(f"0x{va:08x}: bytes mismatch: expected {expected_hex}, got {actual.hex()}")
        windows.append({"site": f"0x{va:08x}", "bytes": expected_hex})

    calls = []
    for site, expected_target in sorted(EXPECTED_CALL_TARGETS.items()):
        target = rel32_target(data, site)
        if target != expected_target:
            raise ValueError(f"0x{site:08x}: target drift: expected 0x{expected_target:08x}, got 0x{target:08x}")
        calls.append({"site": f"0x{site:08x}", "target": f"0x{target:08x}"})

    bodies = {}
    for name, (va, size, expected_hash) in BODY_SPECS.items():
        body = read_va(data, va, size)
        actual_hash = hashlib.sha256(body).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"{name}: body hash drift: {actual_hash}")
        bodies[name] = {"start": f"0x{va:08x}", "size": size, "machine_bytes_sha256": actual_hash}

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contract": POST_FORMAT,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": actual_sha,
            "machine_bytes_adjudicate": True,
        },
        "verified_byte_windows": windows,
        "verified_calls": calls,
        "callee_bodies": bodies,
        "array_3430": {
            "identity": "HDVehicle+0x3430 + iteration*0x18, 12 iterations",
            "caller_stack_slot": "[EBP-0x10]",
            "callee_path": ["FUN_007afd20", "FUN_007aefb0"],
            "FUN_007afd20_argument_role": "param_2 data-vector pointer; forwarded once to FUN_007aefb0 and otherwise only read as scalar/vector data",
            "FUN_007aefb0_argument_role": "param_1 data-vector pointer; reads qwords +0x0/+0x8/+0x10 only; writes output param_2; zero calls",
            "pointer_store_or_back_reference_found": False,
            "wheel_root_reconstruction_found": False,
        },
        "array_35c8": {
            "identity": "HDVehicle+0x35c8 + iteration*0x4, 12 iterations",
            "caller_stack_slot": "[EBP-0x0c]",
            "callee": "FUN_007baa70",
            "receiver_relative_writes": ["+0x48", "+0x50", "+0x58", "+0x60", "+0x68", "+0x70"],
            "absolute_write_span_over_iterations": "HDVehicle+0x3610..+0x3664",
            "direct_call_count": 0,
            "pointer_store_or_back_reference_found": False,
            "wheel_root_reconstruction_found": False,
        },
        "array_35f8": {
            "identity": "HDVehicle+0x35f8 + iteration*0x8, 12 iterations",
            "caller_stack_slot": "[EBP-0x14]",
            "machine_use": "0x0076618b FST QWORD PTR [EDX] after EDX=[EBP-0x14]",
            "callee_receives_cursor": False,
            "pointer_store_or_back_reference_found": False,
            "wheel_root_reconstruction_found": False,
        },
        "array_36e0": {
            "identity": "HDVehicle+0x36e0 + iteration*0x18, 4 iterations",
            "caller_stack_slot": "[EBP-0x0c]",
            "derived_data_source": "cursor-0x2b0 => HDVehicle+0x3430 + iteration*0x18",
            "derived_data_callee": "FUN_007aefb0",
            "cursor_data_callee": "FUN_00747b90",
            "FUN_00747b90_argument_role": "EDX/param_2 data-vector pointer; reads qwords +0x0/+0x8/+0x10; writes stack/output ECX only; zero calls",
            "later_FUN_007baa70_receiver": "chassis BODY [HDVehicle+0x33a0], not +0x36e0 cursor",
            "pointer_store_or_back_reference_found": False,
            "wheel_root_reconstruction_found": False,
        },
        "adjudication": {
            "p13a_fun00765c40_local_array_callee_lifetimes_complete": True,
            "p13a_fun00765c40_local_array_pointer_escape_found": False,
            "p13a_fun00765c40_local_array_wheel_root_reconstruction_found": False,
            "p13a_fun00765c40_local_array_selected_slot_writer_found": False,
            "other_derived_aliases_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "callbacks_and_indirect_entry_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the callee/data-use lifetimes of HDVehicle+0x3430/+0x35c8/+0x35f8/+0x36e0 already classified upstream as non-wheel local arrays.",
            "The proof does not infer pointer identity from numeric offsets: selected slot0/slot1 wheel identity remains separate machine-proven state.",
            "Runtime-generated/copied selected-wheel pointers, callbacks, indirect entry, aggregate copies and other derived aliases remain open.",
            "No global stored-or-escaped-alias, slot-completion or aggregate P1.3 gate is promoted."
        ],
        "next_step": (
            "Compose this closure with the FUN_00765c40 derived-alias handoff; consume the merged 16-carrier/direct-callee "
            "bulk-opcode absence; then trace the two unresolved FUN_00770e80 indirect callsites and runtime-generated/copied selected-wheel pointers."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--post", type=Path, default=Path("evidence/p1d_slot3_fun00765c40_post_derived_inventory.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable, args.post)
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
