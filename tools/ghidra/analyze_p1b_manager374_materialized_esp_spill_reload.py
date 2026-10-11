#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374MaterializedESPSpillReloadProbe/1"
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
POINTER_GPRS = GPRS - {"esp"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {
    "call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2",
    "syscall", "sysret", "sysenter", "sysexit", "hlt",
}
STACK_BARRIERS = {
    "push", "pushf", "pushfd", "pusha", "pushad",
    "pop", "popf", "popfd", "popa", "popad", "enter", "leave",
}
DEST0_WRITES = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xadd", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar", "shld", "shrd",
    "fst", "fstp", "fist", "fistp", "fisttp", "pop",
}
SUBREG_PARENT = {
    "al": "eax", "ah": "eax", "ax": "eax", "eax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx", "ebx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx", "ecx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx", "edx": "edx",
    "si": "esi", "esi": "esi", "di": "edi", "edi": "edi",
    "bp": "ebp", "ebp": "ebp", "sp": "esp", "esp": "esp",
}

INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(
    r"^(?:(BYTE|WORD|DWORD|QWORD|XMMWORD|TBYTE) PTR )?(?:(?:cs|ds|es|fs|gs|ss):)?\[([^\]]+)\]$",
    re.I,
)
LEA_PLUS374 = re.compile(r"^\[(eax|ebx|ecx|edx|esi|edi|ebp|esp)\+0x0*374\]$", re.I)
ESP_CELL = re.compile(r"^esp(?:(\+|-)0x([0-9a-f]+))?$", re.I)
LEA_ESP = re.compile(r"^esp(?:(\+|-)0x([0-9a-f]+))?$", re.I)
ZERO_MEM = re.compile(r"^(eax|ebx|ecx|edx|esi|edi|ebp)(?:\+0x0+)?$", re.I)


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
        parts = operands.split(" ", 1)
        mnemonic = parts[0].lower()
        operands = parts[1] if len(parts) == 2 else ""
    return mnemonic, operands, prefixes


def mem(op: str):
    match = MEM.fullmatch(op.strip())
    if not match:
        return None
    width = match.group(1).upper() if match.group(1) else None
    expr = match.group(2).replace(" ", "").lower()
    return width, expr


def full_gpr(op: str):
    reg = op.strip().lower()
    return reg if reg in GPRS else None


def explicit_register_parent(op: str):
    return SUBREG_PARENT.get(op.strip().lower())


def signed_hex_expr(expr: str, pattern: re.Pattern):
    match = pattern.fullmatch(expr)
    if not match:
        return None
    sign, digits = match.groups()
    if digits is None:
        return 0
    value = int(digits, 16)
    return -value if sign == "-" else value


def lea_plus374_base(op: str):
    parsed = mem(op)
    if parsed is None:
        return None
    _, expr = parsed
    match = LEA_PLUS374.fullmatch(f"[{expr}]")
    return match.group(1).lower() if match else None


def esp_cell_offset(op: str, require_dword: bool = False):
    parsed = mem(op)
    if parsed is None:
        return None
    width, expr = parsed
    if require_dword and width != "DWORD":
        return None
    return signed_hex_expr(expr, ESP_CELL)


def zero_displacement_pointer_reg(op: str):
    parsed = mem(op)
    if parsed is None:
        return None
    _, expr = parsed
    match = ZERO_MEM.fullmatch(expr)
    return match.group(1).lower() if match else None


def parse_immediate(op: str):
    text = op.strip().lower()
    try:
        if text.startswith("-0x"):
            return -int(text[3:], 16)
        if text.startswith("0x"):
            return int(text[2:], 16)
        if re.fullmatch(r"-?[0-9]+", text):
            return int(text, 10)
    except ValueError:
        pass
    return None


def lea_esp_adjustment(op: str):
    parsed = mem(op)
    if parsed is None:
        return None
    _, expr = parsed
    return signed_hex_expr(expr, LEA_ESP)


def is_control(mnemonic: str) -> bool:
    return mnemonic in CONTROL or mnemonic.startswith("j") or mnemonic.startswith("loop")


def is_memory_write_operand(mnemonic: str, operand_index: int) -> bool:
    if mnemonic == "xchg":
        return operand_index in {0, 1}
    if mnemonic.startswith("set"):
        return operand_index == 0
    return mnemonic in DEST0_WRITES and operand_index == 0


def implicit_clobbers(mnemonic: str, ops: list[str], prefixes: list[str]) -> set[str]:
    clobbered: set[str] = set()
    if mnemonic in {"mul", "div", "idiv"} or (mnemonic == "imul" and len(ops) == 1):
        clobbered.update({"eax", "edx"})
    if mnemonic in {"cdq", "cwd"}:
        clobbered.add("edx")
    if mnemonic in {"cbw", "cwde", "lahf", "xlat", "xlatb", "aaa", "aad", "aam", "aas", "daa", "das"}:
        clobbered.add("eax")
    if mnemonic == "cpuid":
        clobbered.update({"eax", "ebx", "ecx", "edx"})
    if mnemonic in {"rdtsc", "rdpmc"}:
        clobbered.update({"eax", "edx"})
    if mnemonic == "rdtscp":
        clobbered.update({"eax", "ecx", "edx"})
    if mnemonic == "cmpxchg":
        clobbered.add("eax")
    if mnemonic == "cmpxchg8b":
        clobbered.update({"eax", "edx"})
    if mnemonic in {"xchg", "xadd"}:
        for op in ops[:2]:
            parent = explicit_register_parent(op)
            if parent:
                clobbered.add(parent)
    if mnemonic.startswith(("movs", "cmps", "stos", "lods", "scas")):
        clobbered.update({"eax", "ecx", "esi", "edi"})
    if prefixes and any(prefix.startswith("rep") for prefix in prefixes):
        clobbered.add("ecx")
    return clobbered


def scan_rows(rows):
    regs: dict[str, dict] = {}
    cells: dict[int, dict] = {}
    sp_position = 0
    stack_generation = 0
    seeds = []
    normalization_events = []
    spills = []
    reloads = []
    write_candidates = []
    other_dereferences = []
    terminations = {
        "control_boundary": 0,
        "stack_barrier": 0,
        "unsupported_esp_write": 0,
        "esp_memory_reference_barrier": 0,
        "esp_dword_overlap_invalidation": 0,
        "tracked_register_clobber": 0,
        "implicit_tracked_register_clobber": 0,
    }

    def reset_stack(reason: str):
        nonlocal sp_position, stack_generation
        if cells:
            terminations[reason] += len(cells)
        elif reason in {"stack_barrier", "unsupported_esp_write"}:
            terminations[reason] += 1
        cells.clear()
        sp_position = 0
        stack_generation += 1

    def invalidate_overlapping_dword_cells(key: int):
        victims = [old for old in cells if old < key + 4 and key < old + 4]
        for old in victims:
            cells.pop(old, None)
        terminations["esp_dword_overlap_invalidation"] += len(victims)

    for address, raw_mnemonic, raw_operands in rows:
        mnemonic, operands, prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        for operand_index, op in enumerate(ops):
            pointer_reg = zero_displacement_pointer_reg(op)
            if pointer_reg in regs and regs[pointer_reg]["reload_depth"] > 0:
                provenance = regs[pointer_reg]
                row = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "prefixes": prefixes,
                    "operand_index": operand_index,
                    "memory_operand": op,
                    "address_register": pointer_reg,
                    "receiver_register": provenance["receiver_register"],
                    "materializer_site": provenance["materializer_site"],
                    "reload_depth": provenance["reload_depth"],
                    "copy_depth": provenance["copy_depth"],
                    "operands": operands,
                }
                if is_memory_write_operand(mnemonic, operand_index):
                    write_candidates.append(row)
                else:
                    other_dereferences.append(row)

        if is_control(mnemonic):
            if regs or cells:
                terminations["control_boundary"] += 1
            regs.clear()
            cells.clear()
            sp_position = 0
            stack_generation += 1
            continue

        if mnemonic in {"add", "sub"} and len(ops) == 2 and ops[0] == "esp":
            amount = parse_immediate(ops[1])
            if amount is None:
                reset_stack("unsupported_esp_write")
            else:
                sp_position += amount if mnemonic == "add" else -amount
                normalization_events.append({
                    "site": f"0x{address:08x}",
                    "kind": mnemonic,
                    "amount": amount,
                    "sp_position": sp_position,
                    "stack_generation": stack_generation,
                })
            continue

        if mnemonic == "lea" and len(ops) == 2 and ops[0] == "esp":
            adjustment = lea_esp_adjustment(ops[1])
            if adjustment is None:
                reset_stack("unsupported_esp_write")
            else:
                sp_position += adjustment
                normalization_events.append({
                    "site": f"0x{address:08x}",
                    "kind": "lea",
                    "amount": adjustment,
                    "sp_position": sp_position,
                    "stack_generation": stack_generation,
                })
            continue

        if mnemonic in STACK_BARRIERS:
            if ops:
                parent = explicit_register_parent(ops[0])
                if parent in regs:
                    regs.pop(parent, None)
                    terminations["tracked_register_clobber"] += 1
            reset_stack("stack_barrier")
            continue

        if mnemonic == "lea" and len(ops) == 2 and full_gpr(ops[0]) in POINTER_GPRS:
            base = lea_plus374_base(ops[1])
            if base is not None:
                dst = full_gpr(ops[0])
                regs[dst] = {
                    "receiver_register": base,
                    "materializer_site": f"0x{address:08x}",
                    "reload_depth": 0,
                    "copy_depth": 0,
                }
                seeds.append({
                    "site": f"0x{address:08x}",
                    "address_register": dst,
                    "receiver_register": base,
                    "operands": operands,
                })
                continue

        if mnemonic == "mov" and len(ops) == 2:
            dst, src = ops
            dst_parent = explicit_register_parent(dst)
            dst_full = full_gpr(dst)
            src_full = full_gpr(src)
            dst_off = esp_cell_offset(dst, require_dword=True)
            src_off = esp_cell_offset(src, require_dword=True)

            if dst_off is not None:
                key = sp_position + dst_off
                invalidate_overlapping_dword_cells(key)
                if src_full in regs:
                    provenance = dict(regs[src_full])
                    cells[key] = provenance
                    spills.append({
                        "site": f"0x{address:08x}",
                        "logical_offset": key,
                        "esp_offset": dst_off,
                        "sp_position": sp_position,
                        "stack_generation": stack_generation,
                        "source_register": src_full,
                        "receiver_register": provenance["receiver_register"],
                        "materializer_site": provenance["materializer_site"],
                    })
                continue

            if dst_full in POINTER_GPRS and src_off is not None:
                key = sp_position + src_off
                provenance = dict(cells[key]) if key in cells else None
                if provenance is not None:
                    provenance["reload_depth"] += 1
                    provenance["copy_depth"] = 0
                    regs[dst_full] = provenance
                    reloads.append({
                        "site": f"0x{address:08x}",
                        "logical_offset": key,
                        "esp_offset": src_off,
                        "sp_position": sp_position,
                        "stack_generation": stack_generation,
                        "destination_register": dst_full,
                        "receiver_register": provenance["receiver_register"],
                        "materializer_site": provenance["materializer_site"],
                        "reload_depth": provenance["reload_depth"],
                    })
                elif dst_full in regs:
                    regs.pop(dst_full, None)
                    terminations["tracked_register_clobber"] += 1
                continue

            if dst_full in POINTER_GPRS and src_full in regs:
                provenance = dict(regs[src_full])
                provenance["copy_depth"] += 1
                regs[dst_full] = provenance
                continue

            if any(esp_cell_offset(op, require_dword=False) is not None for op in ops):
                if cells:
                    terminations["esp_memory_reference_barrier"] += len(cells)
                    cells.clear()

            if dst_parent == "esp":
                reset_stack("unsupported_esp_write")
            elif dst_parent in regs:
                regs.pop(dst_parent, None)
                terminations["tracked_register_clobber"] += 1
            continue

        if any(esp_cell_offset(op, require_dword=False) is not None for op in ops):
            if cells:
                terminations["esp_memory_reference_barrier"] += len(cells)
                cells.clear()

        if ops:
            parent = explicit_register_parent(ops[0])
            if parent == "esp":
                reset_stack("unsupported_esp_write")
            elif parent in regs:
                regs.pop(parent, None)
                terminations["tracked_register_clobber"] += 1

        for reg in implicit_clobbers(mnemonic, ops, prefixes):
            if reg in regs:
                regs.pop(reg, None)
                terminations["implicit_tracked_register_clobber"] += 1

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "materialized_plus_374_seed_count": len(seeds),
            "materialized_plus_374_seeds": seeds,
            "esp_normalization_event_count": len(normalization_events),
            "esp_normalization_events": normalization_events,
            "esp_relative_spill_count": len(spills),
            "esp_relative_spills": spills,
            "esp_relative_reload_count": len(reloads),
            "esp_relative_reloads": reloads,
            "reload_derived_zero_displacement_write_candidate_count": len(write_candidates),
            "reload_derived_zero_displacement_write_candidates": write_candidates,
            "reload_derived_other_dereference_count": len(other_dereferences),
            "reload_derived_other_dereferences": other_dereferences,
            "termination_counts": terminations,
        },
        "adjudication": {
            "materialized_plus_374_esp_spill_reload_normalized_subset_complete": True,
            "esp_reload_write_candidate_receivers_classified": False,
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
            "Covers exact full-GPR receiver+0x374 materialization, exact DWORD ESP-relative MOV spill/reload, and immediate add/sub or lea esp,[esp+/-imm] normalization inside one straight-line region.",
            "Tracked DWORD cells use normalized four-byte ranges; overlapping DWORD stores invalidate prior cells before new provenance can be installed.",
            "Push/pop/enter/leave, arbitrary ESP writes, CFG stack-state carry, non-ESP memory aliases, helper returns, indexed LEA and arithmetic pointer reconstruction remain outside this subset.",
            "Any ESP-relative memory reference outside the exact DWORD MOV grammar invalidates tracked ESP cells conservatively.",
            "Recovered receiver registers are syntactic provenance only and do not imply Participants Manager identity.",
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe and classify only positive normalized ESP reload-derived +0x374 write receivers; extend another carrier class only if retail evidence survives this subset.",
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
