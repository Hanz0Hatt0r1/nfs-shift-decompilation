#!/usr/bin/env python3
"""Execute the P1D exact wheel-root persistence frontier on retail PE machine code.

The six register windows are semantic seeds from merged PC-retail machine contracts.
This tool uses GNU objdump only to reproduce the finite instruction surface and
classify root-register uses. It never extends a root lifetime or promotes numeric
proximity to selected-wheel identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3ExactRootPersistenceMachineClosure/1"
PE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

WINDOWS = {
    "FUN_00758b50": ("ecx", 0x00758CCF, 0x00758D70, 52, 161, "82218e6367840c8d9c7e3723fcad5c70e25c8d198fd1772c65dbc83900ac9377"),
    "FUN_00755950": ("edx", 0x00755956, 0x00755992, 16, 60, "79b509c1706c0aa91c335548404f53e9dac1c10b89cf71e7894edda47d2567ba"),
    "FUN_00755a60": ("esi", 0x00755A73, 0x00755F71, 387, 1278, "3c7f7ecc4348f555cf643c02ab652440568351bade905e9ffbf8056f71ec1f8a"),
    "FUN_00752fc0": ("ecx", 0x00752FC0, 0x00752FE5, 7, 37, "830ecb8fa09bf20a07a8e269f4d44351dc167232bba00f5d9a7d931675d111cc"),
    "FUN_00760b50": ("esi", 0x00760B6A, 0x00760D63, 135, 505, "f648d08e067bd2a9e4a22187829d08e40b58d6cbce8e9c967d00e403090d2ec8"),
    "FUN_00755f80": ("esi", 0x00755F9A, 0x00756004, 35, 106, "c2843b9d46ffebf900114d96fcc96e1b21d7c11355dc3aad8209bbde5ca80179"),
}

EXPECTED_CANDIDATES = {
    "0x00755964": ("FUN_00755950", "derived-address-root", "derived-interior-alias", "EDX+0x80 forwarded to FUN_007555b0; exact wheel root is not forwarded"),
    "0x00755b8f": ("FUN_00755a60", "register-copy-root", "child-pointer-load", "EAX=[wheel+0x420], not an exact-root copy"),
    "0x00755c04": ("FUN_00755a60", "derived-address-root", "derived-interior-alias", "wheel+0x7c8 reaches FUN_00753620 and writes only local +0x0 => wheel+0x7c8"),
    "0x00755db3": ("FUN_00755a60", "register-copy-root", "known-exact-root-forward", "ECX=ESI immediately before already-closed FUN_00752fc0 leaf"),
    "0x00760d02": ("FUN_00760b50", "register-copy-root", "child-pointer-load", "ECX=[wheel+0x420] reaches FUN_007ba860; distinct child receiver"),
    "0x00755f9c": ("FUN_00755f80", "register-copy-root", "child-pointer-load", "EAX=[wheel+0x420], not exact wheel root"),
    "0x00755fb8": ("FUN_00755f80", "register-copy-root", "child-pointer-load", "ECX=[wheel+0x420], not exact wheel root"),
    "0x00755fd6": ("FUN_00755f80", "register-copy-root", "child-pointer-load", "EAX=[wheel+0x420], not exact wheel root"),
}

INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def disassemble(exe: Path, start: int, end: int) -> list[dict]:
    cmd = [
        "objdump", "-d", "-Mintel",
        f"--start-address=0x{start:x}", f"--stop-address=0x{end:x}",
        str(exe),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    rows = []
    for line in proc.stdout.splitlines():
        match = INSN_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        raw = bytes.fromhex(match.group(2))
        mnemonic = match.group(3).lower()
        operands = match.group(4).strip().lower()
        rows.append({"address": address, "bytes": raw, "mnemonic": mnemonic, "operands": operands})
    return rows


def mentions(reg: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9_]){re.escape(reg)}(?![a-z0-9_])", text) is not None


def split_operands(text: str) -> tuple[str, str]:
    if "," not in text:
        return text.strip(), ""
    left, right = text.split(",", 1)
    return left.strip(), right.strip()


def classify(row: dict, reg: str) -> list[str]:
    mnemonic = row["mnemonic"]
    operands = row["operands"]
    dst, src = split_operands(operands)
    root_dst = mentions(reg, dst)
    root_src = mentions(reg, src)
    kinds = []
    if mnemonic.startswith("call"):
        kinds.append("call-boundary")
    if mnemonic == "push" and root_dst:
        kinds.append("push-root")
    if (mnemonic.startswith("mov") or mnemonic == "xchg") and "[" in dst and root_src:
        kinds.append("memory-store-root")
    if mnemonic.startswith("mov") and "[" not in dst and root_src:
        kinds.append("register-copy-root")
    if mnemonic == "lea" and "[" in src and root_src:
        kinds.append("derived-address-root")
    if "[" in dst and root_dst and "memory-store-root" not in kinds:
        kinds.append("root-based-memory-destination")
    if "[" in src and root_src:
        kinds.append("root-based-memory-source")
    if mentions(reg, operands) and not kinds:
        kinds.append("other-root-use")
    return kinds


def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != PE_SHA256:
        raise ValueError(f"unexpected retail executable SHA-256: {digest}")

    windows = []
    ranked = []
    store_count = 0
    push_count = 0
    for function, (reg, start, end, expected_count, expected_bytes, expected_sha) in WINDOWS.items():
        rows = disassemble(exe, start, end)
        blob = b"".join(row["bytes"] for row in rows)
        actual_sha = hashlib.sha256(blob).hexdigest()
        if len(rows) != expected_count or len(blob) != expected_bytes or actual_sha != expected_sha:
            raise ValueError(
                f"{function}: machine window drift count={len(rows)} bytes={len(blob)} sha={actual_sha}"
            )
        local_store = local_push = 0
        for row in rows:
            kinds = classify(row, reg)
            local_store += int("memory-store-root" in kinds)
            local_push += int("push-root" in kinds)
            for kind in ("memory-store-root", "push-root", "register-copy-root", "derived-address-root"):
                if kind in kinds:
                    ranked.append({
                        "instruction_address": f"0x{row['address']:08x}",
                        "function": function,
                        "root_register": reg,
                        "raw_candidate_class": kind,
                        "mnemonic": row["mnemonic"],
                        "operands": row["operands"],
                    })
                    break
        store_count += local_store
        push_count += local_push
        windows.append({
            "function": function,
            "root_register": reg,
            "start": f"0x{start:08x}",
            "end_exclusive": f"0x{end:08x}",
            "instruction_count": len(rows),
            "machine_byte_count": len(blob),
            "machine_bytes_sha256": actual_sha,
            "memory_store_root_count": local_store,
            "push_root_count": local_push,
        })

    by_site = {row["instruction_address"]: row for row in ranked}
    if set(by_site) != set(EXPECTED_CANDIDATES):
        raise ValueError(f"persistence candidate set drift: {sorted(by_site)}")
    adjudicated = []
    for site, (function, raw_class, semantic_class, note) in EXPECTED_CANDIDATES.items():
        row = by_site[site]
        if row["function"] != function or row["raw_candidate_class"] != raw_class:
            raise ValueError(f"candidate identity drift at {site}: {row}")
        adjudicated.append({**row, "machine_adjudication": semantic_class, "note": note})

    if store_count != 0 or push_count != 0:
        raise ValueError(f"unexpected exact-root persistence primitive: stores={store_count} pushes={push_count}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "gnu_objdump_machine_bytes_adjudicate_finite_window_surface": True,
            "semantic_root_windows_seeded_from_merged_machine_contracts": True,
        },
        "scope": {
            "carrier_window_count": 6,
            "windows": windows,
            "memory_store_root_count": store_count,
            "push_root_count": push_count,
            "ranked_persistence_candidate_count": len(adjudicated),
        },
        "ranked_candidates": adjudicated,
        "composition": {
            "FUN_00755950": "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1",
            "FUN_00755a60": "SHIFT.P1D.Slot3Fun00755a60RegisterAliasClosure/1",
            "FUN_00760b50": "SHIFT.P1D.Slot3Fun00760b50RegisterAliasClosure/1",
            "FUN_00755f80": "SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1 plus SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1",
            "FUN_00758b50": "SHIFT.P1D.P13DSlot3PrimaryAliasEscape/1",
            "FUN_00752fc0": "SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1",
        },
        "adjudication": {
            "bounded_six_window_machine_persistence_inventory_complete": True,
            "bounded_six_window_memory_store_root_count": 0,
            "bounded_six_window_push_root_count": 0,
            "bounded_six_window_persistence_candidates_adjudicated": True,
            "bounded_six_window_selected_slot3_writer_found": False,
            "machine_register_alias_storage_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the six exact-root register windows defined by merged #1793 tooling and upstream machine contracts.",
            "The raw exporter-style register-copy class intentionally over-approximates MOV reg,[root+offset]; those rows are machine-adjudicated as child-pointer loads, not exact-root copies.",
            "Aliases created in other carriers/callees, aggregate stores, callbacks, runtime-generated pointer paths and the 16-carrier source-storage replay remain open.",
        ],
        "next_step": "Trace callee-created selected-wheel aliases outside these six windows and complete the separate 16-carrier source-storage replay before composing any global stored/escaped-alias gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.exe)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
