#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374MaterializedPlus374WriterProbe/1"
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {"call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2"}
WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar",
    "fst", "fstp", "fist", "fistp", "fisttp",
}
SUBREG_PARENT = {
    "al": "eax", "ah": "eax", "ax": "eax", "eax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx", "ebx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx", "ecx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx", "edx": "edx",
    "si": "esi", "esi": "esi", "di": "edi", "edi": "edi",
    "bp": "ebp", "ebp": "ebp", "sp": "esp", "esp": "esp",
}
STACK_MUTATORS = {
    "push", "pushf", "pushfd", "pusha", "pushad",
    "pop", "popf", "popfd", "popa", "popad", "enter", "leave",
}

INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(
    r"^(?:(?:BYTE|WORD|DWORD|QWORD|XMMWORD|TBYTE) PTR )?(?:(?:cs|ds|es|fs|gs|ss):)?\[([^\]]+)\]$",
    re.I,
)
LEA_PLUS374 = re.compile(r"^\[(eax|ebx|ecx|edx|esi|edi|ebp|esp)\+0x0*374\]$", re.I)
ZERO_MEM = re.compile(r"^(eax|ebx|ecx|edx|esi|edi|ebp|esp)(?:\+0x0+)?$", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).replace(", ", ",")


def split_ops(text: str) -> list[str]:
    return text.split(",") if text else []


def normalize_prefixed_instruction(mnemonic: str, operands: str) -> tuple[str, str, list[str]]:
    prefixes: list[str] = []
    mnemonic = mnemonic.lower()
    operands = norm(operands)
    while mnemonic in PREFIXES:
        prefixes.append(mnemonic)
        if not operands:
            return mnemonic, operands, prefixes
        pieces = operands.split(" ", 1)
        mnemonic = pieces[0].lower()
        operands = pieces[1] if len(pieces) == 2 else ""
    return mnemonic, operands, prefixes


def lea_plus374_base(op: str):
    match = LEA_PLUS374.fullmatch(op.replace(" ", ""))
    return match.group(1).lower() if match else None


def zero_displacement_memory_register(op: str):
    match = MEM.fullmatch(op.strip())
    if not match:
        return None
    expr = match.group(1).replace(" ", "").lower()
    zero = ZERO_MEM.fullmatch(expr)
    return zero.group(1).lower() if zero else None


def explicit_register_parent(op: str):
    return SUBREG_PARENT.get(op.strip().lower())


def is_control(mnemonic: str) -> bool:
    return mnemonic in CONTROL or mnemonic.startswith("j") or mnemonic.startswith("loop")


def implicit_clobbers(mnemonic: str, ops: list[str], prefixes: list[str]) -> set[str]:
    clobbered: set[str] = set()
    if mnemonic in STACK_MUTATORS:
        clobbered.add("esp")
        if mnemonic == "leave":
            clobbered.add("ebp")
    if mnemonic in {"mul", "div", "idiv"} or (mnemonic == "imul" and len(ops) == 1):
        clobbered.update({"eax", "edx"})
    if mnemonic in {"cdq", "cwd"}:
        clobbered.add("edx")
    if mnemonic in {"cbw", "cwde"}:
        clobbered.add("eax")
    if mnemonic == "cpuid":
        clobbered.update({"eax", "ebx", "ecx", "edx"})
    if mnemonic == "rdtsc":
        clobbered.update({"eax", "edx"})
    if mnemonic == "rdtscp":
        clobbered.update({"eax", "ecx", "edx"})
    if mnemonic == "cmpxchg":
        clobbered.add("eax")
    if mnemonic == "cmpxchg8b":
        clobbered.update({"eax", "edx"})
    if mnemonic == "xchg":
        for op in ops[:2]:
            parent = explicit_register_parent(op)
            if parent:
                clobbered.add(parent)
    if mnemonic.startswith(("movs", "cmps", "stos", "lods", "scas")):
        # Conservative superset. String instructions can update ESI/EDI, and REP
        # forms update ECX; LODS/STOS/SCAS also involve the accumulator.
        clobbered.update({"eax", "ecx", "esi", "edi"})
    if prefixes and any(prefix.startswith("rep") for prefix in prefixes):
        clobbered.add("ecx")
    return clobbered


def scan_rows(rows):
    # tracked[reg] identifies the original receiver register used by
    # lea reg,[receiver+0x374]. This is an address-provenance label only; it
    # does not assign semantic Participants Manager identity to the receiver.
    tracked: dict[str, dict] = {}
    seeds = []
    copies = []
    write_candidates = []
    other_dereferences = []
    terminations = {
        "control_boundary": 0,
        "tracked_register_clobber": 0,
        "implicit_tracked_register_clobber": 0,
    }

    for address, raw_mnemonic, raw_operands in rows:
        mnemonic, operands, prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        # Observe exact zero-displacement dereferences before processing a
        # destination-register clobber from this same instruction.
        if ops:
            pointer_reg = zero_displacement_memory_register(ops[0])
            if pointer_reg in tracked:
                provenance = tracked[pointer_reg]
                row = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "prefixes": prefixes,
                    "destination": ops[0],
                    "address_register": pointer_reg,
                    "receiver_register": provenance["receiver_register"],
                    "materializer_site": provenance["materializer_site"],
                    "copy_depth": provenance["copy_depth"],
                    "operands": operands,
                }
                if mnemonic in WRITE_MNEMONICS:
                    write_candidates.append(row)
                else:
                    other_dereferences.append(row)

        if is_control(mnemonic):
            if tracked:
                terminations["control_boundary"] += 1
            tracked.clear()
            continue

        # Exact seed: only one GPR base and exactly +0x374. Indexed forms are
        # deliberately excluded because they are not receiver+0x374 identity.
        if mnemonic == "lea" and len(ops) == 2 and ops[0] in GPRS:
            base = lea_plus374_base(ops[1])
            if base is not None:
                tracked[ops[0]] = {
                    "receiver_register": base,
                    "materializer_site": f"0x{address:08x}",
                    "copy_depth": 0,
                }
                seeds.append({
                    "site": f"0x{address:08x}",
                    "address_register": ops[0],
                    "receiver_register": base,
                    "operands": operands,
                })
                continue

        # Preserve only explicit GPR MOV copies of the exact materialized
        # address. Other transformations are killed rather than approximated.
        if mnemonic == "mov" and len(ops) == 2 and ops[0] in GPRS:
            dst, src = ops
            if src in tracked:
                src_info = tracked[src]
                tracked[dst] = {
                    "receiver_register": src_info["receiver_register"],
                    "materializer_site": src_info["materializer_site"],
                    "copy_depth": src_info["copy_depth"] + 1,
                }
                copies.append({
                    "site": f"0x{address:08x}",
                    "source_register": src,
                    "destination_register": dst,
                    "materializer_site": src_info["materializer_site"],
                    "copy_depth": src_info["copy_depth"] + 1,
                })
            elif dst in tracked:
                tracked.pop(dst, None)
                terminations["tracked_register_clobber"] += 1
            # MOV has no additional implicit GPR clobber relevant here.
            continue

        # Explicit full or partial register destinations destroy exact address
        # provenance. Partial writes such as mov al,1 must invalidate EAX.
        if ops:
            parent = explicit_register_parent(ops[0])
            if parent in tracked:
                tracked.pop(parent, None)
                terminations["tracked_register_clobber"] += 1

        # Model high-risk implicit clobbers conservatively so a later [reg]
        # store cannot inherit stale exact-address provenance.
        for reg in implicit_clobbers(mnemonic, ops, prefixes):
            if reg in tracked:
                tracked.pop(reg, None)
                terminations["implicit_tracked_register_clobber"] += 1

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "materialized_plus_374_seed_count": len(seeds),
            "materialized_plus_374_seeds": seeds,
            "materialized_plus_374_copy_count": len(copies),
            "materialized_plus_374_copies": copies,
            "zero_displacement_write_candidate_count": len(write_candidates),
            "zero_displacement_write_candidates": write_candidates,
            "zero_displacement_other_dereference_count": len(other_dereferences),
            "zero_displacement_other_dereferences": other_dereferences,
            "termination_counts": terminations,
        },
        "adjudication": {
            "whole_image_lea_materialized_plus_374_same_region_subset_complete": True,
            "materialized_plus_374_candidate_receivers_classified": False,
            "computed_plus_374_address_writer_surface_complete": False,
            "unknown_or_unrelated_manager_root_alias_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Covers exact lea addr,[receiver+0x374], GPR MOV copies of addr, and exact zero-displacement first-memory-operand dereferences before a control boundary or tracked-register clobber.",
            "Partial-register destinations and selected implicit x86 GPR clobbers invalidate exact-address provenance conservatively.",
            "Indexed LEA, arithmetic reconstruction, stack spill/reload, cross-control-flow carry, helper returns, and memory-stored materialized addresses remain outside this subset.",
            "A recovered receiver register is syntactic provenance only and does not imply Participants Manager identity.",
            "Only an explicit write/RMW mnemonic allowlist is classified as a write candidate; other dereferences remain separately fail-closed.",
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe and classify only positive materialized +0x374 write receivers; then extend solely the surviving carrier class before final manager+0x374 identity adjudication.",
    }


def disassemble(executable: Path):
    proc = subprocess.run(
        ["objdump", "-d", "-Mintel", str(executable)],
        capture_output=True,
        text=True,
        check=True,
        errors="replace",
    )
    rows = []
    for line in proc.stdout.splitlines():
        match = INSN.match(line)
        if match:
            rows.append((int(match.group(1), 16), match.group(2).lower(), norm(match.group(3))))
    return rows


def analyze(executable: Path):
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")
    result = scan_rows(disassemble(executable))
    result["authority"] = {
        "platform": "PC retail 1.02",
        "retail_executable_sha256": digest,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(analyze(args.executable), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
