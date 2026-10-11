#!/usr/bin/env python3
"""Bound read-only image-seeded reconstruction of the Participants Manager root.

This probe tracks exact 32-bit values loaded from immutable retail image seeds
(.text/.rdata) through a deliberately finite straight-line GPR model. It is a
bounded source-class proof, not a claim about writable memory, helper returns,
external mutation, or arbitrary runtime transforms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from typing import Callable, Iterable

FORMAT = "SHIFT.P1B.Manager374ReadonlyImageSeedReconstruction/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
TARGET = 0x00BC9FC0
WINDOW = 32
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
TRACKED_GPRS = GPRS - {"esp"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {"call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2", "syscall", "sysret", "sysenter", "sysexit", "hlt"}
NON_WRITING_FIRST_REG = {"cmp", "test", "push", "bt", "nop", "prefetchnta", "prefetcht0", "prefetcht1", "prefetcht2"}
SUBREG_PARENT = {
    "al": "eax", "ah": "eax", "ax": "eax", "eax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx", "ebx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx", "ecx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx", "edx": "edx",
    "si": "esi", "esi": "esi", "di": "edi", "edi": "edi",
    "bp": "ebp", "ebp": "ebp", "sp": "esp", "esp": "esp",
}
INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
IMM = re.compile(r"^(?:0x)?([0-9a-fA-F]+)$")
ABS_BRACKET = re.compile(r"^\[\s*(?:0x)?([0-9a-fA-F]+)\s*\]$", re.I)
ABS_SEGMENT = re.compile(r"^(?:(?:cs|ds|es|fs|gs|ss):)?(?:0x)?([0-9a-fA-F]+)$", re.I)
LEA_SIMPLE = re.compile(r"^\[(eax|ebx|ecx|edx|esi|edi|ebp)([+-](?:0x)?[0-9a-fA-F]+)?\]$", re.I)
MASK32 = 0xFFFFFFFF


def u32(value: int) -> int:
    return value & MASK32


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).replace(", ", ",")


def split_ops(text: str) -> list[str]:
    return text.split(",") if text else []


def normalize_prefixed_instruction(mnemonic: str, operands: str) -> tuple[str, str]:
    mnemonic = mnemonic.lower()
    operands = norm(operands)
    while mnemonic in PREFIXES and operands:
        parts = operands.split(" ", 1)
        mnemonic = parts[0].lower()
        operands = parts[1] if len(parts) == 2 else ""
    return mnemonic, operands


def full_gpr(op: str) -> str | None:
    op = op.strip().lower()
    return op if op in TRACKED_GPRS else None


def parent_reg(op: str) -> str | None:
    return SUBREG_PARENT.get(op.strip().lower())


def parse_imm(op: str) -> int | None:
    text = op.strip().lower()
    sign = 1
    if text.startswith("-"):
        sign, text = -1, text[1:]
    elif text.startswith("+"):
        text = text[1:]
    match = IMM.fullmatch(text)
    return u32(sign * int(match.group(1), 16)) if match else None


def abs_memory_address(op: str) -> int | None:
    text = op.strip()
    text = re.sub(r"^(?:BYTE|WORD|DWORD|QWORD|TBYTE|XMMWORD) PTR\s+", "", text, flags=re.I)
    bracket = ABS_BRACKET.fullmatch(text)
    if bracket:
        return int(bracket.group(1), 16)
    segment = ABS_SEGMENT.fullmatch(text)
    if segment:
        return int(segment.group(1), 16)
    return None


def is_control(mnemonic: str) -> bool:
    return mnemonic in CONTROL or mnemonic.startswith("j") or mnemonic.startswith("loop")


def source_key(source: dict) -> tuple:
    return (source["seed_site"], source["seed_address"], source["seed_section"], source["seed_value"])


def merge_sources(*infos: dict) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for info in infos:
        for source in info.get("sources", []):
            merged[source_key(source)] = source
    return [merged[k] for k in sorted(merged)]


def make_info(value: int, row_index: int, sources: list[dict]) -> dict:
    return {"value": u32(value), "origin_index": row_index, "sources": sources}


def copied_info(info: dict) -> dict:
    return {"value": info["value"], "origin_index": info["origin_index"], "sources": list(info["sources"])}


def formation_row(address: int, reg: str, info: dict, mnemonic: str, operands: str, kind: str) -> dict:
    return {
        "site": f"0x{address:08x}",
        "register": reg,
        "value": f"0x{info['value']:08x}",
        "kind": kind,
        "mnemonic": mnemonic,
        "operands": operands,
        "sources": list(info["sources"]),
    }


def parse_lea_single_base(op: str) -> tuple[str, int] | None:
    text = op.replace(" ", "").lower()
    match = LEA_SIMPLE.fullmatch(text)
    if not match:
        return None
    base = match.group(1).lower()
    disp = parse_imm(match.group(2) or "0")
    return (base, disp) if disp is not None else None


def scan_rows(rows: Iterable[tuple[int, str, str]], read_seed: Callable[[int], tuple[int, str] | None]) -> dict:
    regs: dict[str, dict] = {}
    seeds: list[dict] = []
    formations: list[dict] = []
    transitions = 0
    expirations = 0
    control_resets = 0
    unsupported_clobbers = 0

    def install(reg: str, info: dict, address: int, mnemonic: str, operands: str, kind: str) -> None:
        regs[reg] = info
        if info["value"] == TARGET:
            formations.append(formation_row(address, reg, info, mnemonic, operands, kind))

    for row_index, (address, raw_mnemonic, raw_operands) in enumerate(rows):
        mnemonic, operands = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        stale = [reg for reg, info in regs.items() if row_index - info["origin_index"] > WINDOW]
        for reg in stale:
            regs.pop(reg, None)
            expirations += 1

        if is_control(mnemonic):
            if regs:
                control_resets += 1
            regs.clear()
            continue

        if mnemonic == "mov" and len(ops) == 2:
            dst, src = ops
            dst_reg = full_gpr(dst)
            src_reg = full_gpr(src)
            if dst_reg:
                mem = abs_memory_address(src)
                if mem is not None:
                    resolved = read_seed(mem)
                    if resolved is not None:
                        value, section = resolved
                        source = {
                            "seed_site": f"0x{address:08x}",
                            "seed_address": f"0x{mem:08x}",
                            "seed_section": section,
                            "seed_value": f"0x{u32(value):08x}",
                        }
                        info = make_info(value, row_index, [source])
                        seeds.append(dict(source, destination_register=dst_reg))
                        install(dst_reg, info, address, mnemonic, operands, "readonly-image-load")
                        continue
                if src_reg in regs:
                    install(dst_reg, copied_info(regs[src_reg]), address, mnemonic, operands, "gpr-copy")
                    transitions += 1
                    continue
                if dst_reg in regs:
                    regs.pop(dst_reg, None)
                    unsupported_clobbers += 1
                continue
            parent = parent_reg(dst)
            if parent in regs:
                regs.pop(parent, None)
                unsupported_clobbers += 1
            continue

        if mnemonic in {"add", "sub", "xor", "or", "and"} and len(ops) == 2:
            dst = full_gpr(ops[0])
            if dst in regs:
                rhs_imm = parse_imm(ops[1])
                rhs_reg = full_gpr(ops[1])
                lhs = regs[dst]
                if mnemonic == "xor" and rhs_reg == dst:
                    regs.pop(dst, None)
                    continue
                rhs_info = regs.get(rhs_reg) if rhs_reg else None
                if rhs_imm is None and rhs_info is None:
                    regs.pop(dst, None)
                    unsupported_clobbers += 1
                    continue
                rhs = rhs_imm if rhs_imm is not None else rhs_info["value"]
                if mnemonic == "add": value = lhs["value"] + rhs
                elif mnemonic == "sub": value = lhs["value"] - rhs
                elif mnemonic == "xor": value = lhs["value"] ^ rhs
                elif mnemonic == "or": value = lhs["value"] | rhs
                else: value = lhs["value"] & rhs
                sources = merge_sources(lhs, rhs_info) if rhs_info is not None else list(lhs["sources"])
                origin = min([lhs["origin_index"]] + ([rhs_info["origin_index"]] if rhs_info else []))
                info = {"value": u32(value), "origin_index": origin, "sources": sources}
                install(dst, info, address, mnemonic, operands, "binary-arithmetic")
                transitions += 1
                continue

        if mnemonic in {"inc", "dec", "neg", "not"} and len(ops) == 1:
            dst = full_gpr(ops[0])
            if dst in regs:
                old = regs[dst]
                if mnemonic == "inc": value = old["value"] + 1
                elif mnemonic == "dec": value = old["value"] - 1
                elif mnemonic == "neg": value = -old["value"]
                else: value = ~old["value"]
                info = {"value": u32(value), "origin_index": old["origin_index"], "sources": list(old["sources"])}
                install(dst, info, address, mnemonic, operands, "unary-arithmetic")
                transitions += 1
                continue

        if mnemonic in {"shl", "sal", "shr"} and len(ops) == 2:
            dst = full_gpr(ops[0])
            shift = parse_imm(ops[1])
            if dst in regs and shift is not None:
                old = regs[dst]
                amount = shift & 31
                value = old["value"] << amount if mnemonic in {"shl", "sal"} else old["value"] >> amount
                info = {"value": u32(value), "origin_index": old["origin_index"], "sources": list(old["sources"])}
                install(dst, info, address, mnemonic, operands, "shift")
                transitions += 1
                continue

        if mnemonic == "lea" and len(ops) == 2:
            dst = full_gpr(ops[0])
            parsed = parse_lea_single_base(ops[1])
            if dst and parsed and parsed[0] in regs:
                base, disp = parsed
                old = regs[base]
                info = {"value": u32(old["value"] + disp), "origin_index": old["origin_index"], "sources": list(old["sources"])}
                install(dst, info, address, mnemonic, operands, "lea-base-disp")
                transitions += 1
                continue

        if mnemonic == "imul" and len(ops) == 3:
            dst = full_gpr(ops[0])
            src = full_gpr(ops[1])
            factor = parse_imm(ops[2])
            if dst and src in regs and factor is not None:
                old = regs[src]
                info = {"value": u32(old["value"] * factor), "origin_index": old["origin_index"], "sources": list(old["sources"])}
                install(dst, info, address, mnemonic, operands, "imul-immediate")
                transitions += 1
                continue

        if ops:
            parent = parent_reg(ops[0])
            if parent in regs and mnemonic not in NON_WRITING_FIRST_REG:
                regs.pop(parent, None)
                unsupported_clobbers += 1

    unique = {}
    for row in formations:
        key = (row["site"], row["register"], tuple((s["seed_site"], s["seed_address"]) for s in row["sources"]))
        unique[key] = row
    formations = [unique[k] for k in sorted(unique)]
    direct = [row for row in formations if row["kind"] == "readonly-image-load"]
    reconstructed = [row for row in formations if row["kind"] != "readonly-image-load"]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "readonly_image_seed_load_count": len(seeds),
            "readonly_image_seed_loads": seeds,
            "modeled_transition_count": transitions,
            "exact_root_formation_count": len(formations),
            "exact_root_formations": formations,
            "direct_exact_root_seed_count": len(direct),
            "nontrivial_exact_root_reconstruction_count": len(reconstructed),
            "nontrivial_exact_root_reconstructions": reconstructed,
            "window_expiration_count": expirations,
            "control_reset_count": control_resets,
            "unsupported_tracked_clobber_count": unsupported_clobbers,
        },
        "adjudication": {
            "bounded_readonly_image_memory_seed_reconstruction_subset_complete": True,
            "bounded_readonly_image_memory_seed_exact_root_found": bool(formations),
            "memory_load_or_opaque_runtime_reconstruction_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            f"Tracks only exact dword loads from retail .text/.rdata through a straight-line {WINDOW}-instruction GPR window.",
            "Calls, branches, returns and traps clear tracked state; helper-return provenance is outside this subset.",
            "Writable .data/heap/anonymous memory, table indexing, arbitrary memory aliases, runtime patching and unsupported transforms remain open.",
            "A positive exact numeric formation is only a candidate source until its runtime ownership and consumer path are classified.",
        ],
        "next_step": "Run on authoritative retail; classify any exact-root formation. If negative, continue with writable-memory/helper-return and unrecognized-runtime-transform root sources without promoting global manager-root origin closure.",
    }


def iter_objdump_rows(executable: Path):
    proc = subprocess.Popen(["objdump", "-d", "-Mintel", str(executable)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            match = INSN.match(line)
            if match:
                yield int(match.group(1), 16), match.group(2), match.group(3)
    finally:
        proc.stdout.close()
    stderr = proc.stderr.read() if proc.stderr is not None else ""
    if proc.stderr is not None:
        proc.stderr.close()
    rc = proc.wait()
    if rc:
        raise RuntimeError(f"objdump failed ({rc}): {stderr.strip()}")


def pe_readonly_seed_reader(executable: Path):
    blob = executable.read_bytes()
    if blob[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    number_sections = struct.unpack_from("<H", blob, pe + 6)[0]
    size_optional = struct.unpack_from("<H", blob, pe + 20)[0]
    optional = pe + 24
    if struct.unpack_from("<H", blob, optional)[0] != 0x10B:
        raise ValueError("expected PE32 image")
    image_base = struct.unpack_from("<I", blob, optional + 28)[0]
    section_table = optional + size_optional
    sections = []
    for index in range(number_sections):
        off = section_table + index * 40
        name = blob[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", blob, off + 8)
        sections.append({"name": name, "start": image_base + virtual_address, "virtual_size": virtual_size, "raw_size": raw_size, "raw_ptr": raw_ptr})
    allowed = [s for s in sections if s["name"] in {".text", ".rdata"}]

    def read_seed(address: int) -> tuple[int, str] | None:
        for section in allowed:
            offset = address - section["start"]
            if 0 <= offset and offset + 4 <= section["raw_size"]:
                raw = section["raw_ptr"] + offset
                if raw + 4 <= len(blob):
                    return struct.unpack_from("<I", blob, raw)[0], section["name"]
        return None

    return read_seed, sections


def analyze(executable: Path) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")
    reader, sections = pe_readonly_seed_reader(executable)
    result = scan_rows(iter_objdump_rows(executable), reader)
    result["authority"] = {
        "platform": "PC retail 1.02",
        "retail_executable_sha256": RETAIL_SHA256,
        "machine_bytes_adjudicate": True,
        "decoder": "GNU objdump -d -Mintel",
        "seed_sections": [s["name"] for s in sections if s["name"] in {".text", ".rdata"}],
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("executable", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = analyze(args.executable)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
