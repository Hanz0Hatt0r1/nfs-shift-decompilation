#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374MaterializedEbpSpillReloadProbe/1"
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {
    "call", "jmp", "ret", "retn", "iret", "iretd", "int", "int3", "ud2",
    "syscall", "sysret", "sysenter", "sysexit", "hlt",
}
WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "xadd", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
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
EBP_CELL = re.compile(r"^ebp(?:(\+|-)0x([0-9a-f]+))?$", re.I)


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


def memory_expr(op: str):
    match = MEM.fullmatch(op.strip())
    return match.group(1).replace(" ", "").lower() if match else None


def lea_plus374_base(op: str):
    expr = memory_expr(op)
    if expr is None:
        return None
    match = LEA_PLUS374.fullmatch(f"[{expr}]")
    return match.group(1).lower() if match else None


def zero_displacement_memory_register(op: str):
    expr = memory_expr(op)
    if expr is None:
        return None
    match = ZERO_MEM.fullmatch(expr)
    return match.group(1).lower() if match else None


def ebp_cell_offset(op: str):
    expr = memory_expr(op)
    if expr is None:
        return None
    match = EBP_CELL.fullmatch(expr)
    if not match:
        return None
    if not match.group(1):
        return 0
    value = int(match.group(2), 16)
    return value if match.group(1) == "+" else -value


def explicit_register_parent(op: str):
    return SUBREG_PARENT.get(op.strip().lower())


def full_gpr(op: str):
    reg = op.strip().lower()
    return reg if reg in GPRS else None


def is_control(mnemonic: str) -> bool:
    return mnemonic in CONTROL or mnemonic.startswith("j") or mnemonic.startswith("loop")


def is_write_mnemonic(mnemonic: str) -> bool:
    return (
        mnemonic in WRITE_MNEMONICS
        or mnemonic.startswith("set")
        or mnemonic.startswith("stos")
        or mnemonic.startswith("movs")
    )


def implicit_clobbers(mnemonic: str, ops: list[str], prefixes: list[str]) -> set[str]:
    clobbered: set[str] = set()
    if mnemonic in STACK_MUTATORS:
        clobbered.add("esp")
        if mnemonic in {"enter", "leave", "popa", "popad"}:
            clobbered.add("ebp")
        if mnemonic in {"popa", "popad"}:
            clobbered.update({"eax", "ebx", "ecx", "edx", "esi", "edi"})
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
    if mnemonic in {"cmpxchg", "xadd"}:
        clobbered.add("eax" if mnemonic == "cmpxchg" else "")
        clobbered.discard("")
    if mnemonic == "cmpxchg8b":
        clobbered.update({"eax", "edx"})
    if mnemonic == "xchg":
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
    ebp_cells: dict[int, dict] = {}
    seeds = []
    spills = []
    reloads = []
    reload_write_candidates = []
    reload_other_dereferences = []
    terminations = {
        "control_boundary": 0,
        "tracked_register_clobber": 0,
        "implicit_tracked_register_clobber": 0,
        "ebp_frame_invalidation": 0,
        "ebp_memory_reference_invalidation": 0,
        "tracked_ebp_cell_overwrite": 0,
    }

    def clear_frame_cells():
        if ebp_cells:
            terminations["ebp_frame_invalidation"] += len(ebp_cells)
            ebp_cells.clear()

    def invalidate_cells_for_reference(dst_cell=None):
        if not ebp_cells:
            return
        if dst_cell is not None and dst_cell in ebp_cells:
            terminations["tracked_ebp_cell_overwrite"] += 1
        terminations["ebp_memory_reference_invalidation"] += len(ebp_cells)
        ebp_cells.clear()

    for address, raw_mnemonic, raw_operands in rows:
        mnemonic, operands, prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        if ops:
            pointer_reg = zero_displacement_memory_register(ops[0])
            if pointer_reg in regs and regs[pointer_reg]["reload_depth"] > 0:
                provenance = regs[pointer_reg]
                row = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "prefixes": prefixes,
                    "destination": ops[0],
                    "address_register": pointer_reg,
                    "receiver_register": provenance["receiver_register"],
                    "materializer_site": provenance["materializer_site"],
                    "reload_depth": provenance["reload_depth"],
                    "copy_depth": provenance["copy_depth"],
                    "operands": operands,
                }
                if is_write_mnemonic(mnemonic):
                    reload_write_candidates.append(row)
                else:
                    reload_other_dereferences.append(row)

        if is_control(mnemonic):
            if regs or ebp_cells:
                terminations["control_boundary"] += 1
            regs.clear()
            ebp_cells.clear()
            continue

        if mnemonic == "lea" and len(ops) == 2 and full_gpr(ops[0]):
            base = lea_plus374_base(ops[1])
            if base is not None:
                dst = full_gpr(ops[0])
                if dst == "ebp":
                    clear_frame_cells()
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
            dst_cell = ebp_cell_offset(dst)
            src_cell = ebp_cell_offset(src)

            if dst_cell is not None:
                invalidate_cells_for_reference(dst_cell)
                if src_full in regs:
                    provenance = dict(regs[src_full])
                    ebp_cells[dst_cell] = provenance
                    spills.append({
                        "site": f"0x{address:08x}",
                        "offset": dst_cell,
                        "source_register": src_full,
                        "receiver_register": provenance["receiver_register"],
                        "materializer_site": provenance["materializer_site"],
                        "reload_depth": provenance["reload_depth"],
                    })
                continue

            if dst_full and src_cell is not None:
                provenance = dict(ebp_cells[src_cell]) if src_cell in ebp_cells else None
                if dst_full == "ebp":
                    clear_frame_cells()
                if provenance is not None:
                    provenance["reload_depth"] += 1
                    provenance["copy_depth"] = 0
                    regs[dst_full] = provenance
                    reloads.append({
                        "site": f"0x{address:08x}",
                        "offset": src_cell,
                        "destination_register": dst_full,
                        "receiver_register": provenance["receiver_register"],
                        "materializer_site": provenance["materializer_site"],
                        "reload_depth": provenance["reload_depth"],
                    })
                elif dst_full in regs:
                    regs.pop(dst_full, None)
                    terminations["tracked_register_clobber"] += 1
                continue

            if dst_full and src_full in regs:
                if dst_full == "ebp":
                    clear_frame_cells()
                provenance = dict(regs[src_full])
                provenance["copy_depth"] += 1
                regs[dst_full] = provenance
                continue

            if dst_parent in regs:
                if dst_parent == "ebp":
                    clear_frame_cells()
                regs.pop(dst_parent, None)
                terminations["tracked_register_clobber"] += 1
            elif dst_parent == "ebp":
                clear_frame_cells()
            continue

        # Outside exact MOV spill/reload, any EBP-relative memory-like operand
        # is a conservative barrier. This intentionally treats read-only forms
        # and LEA-style syntax as invalidating too, avoiding incomplete opcode
        # and operand-width alias modeling.
        if any(ebp_cell_offset(op) is not None for op in ops):
            invalidate_cells_for_reference()

        if ops:
            parent = explicit_register_parent(ops[0])
            if parent == "ebp":
                clear_frame_cells()
            if parent in regs:
                regs.pop(parent, None)
                terminations["tracked_register_clobber"] += 1

        for reg in implicit_clobbers(mnemonic, ops, prefixes):
            if reg == "ebp":
                clear_frame_cells()
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
            "ebp_relative_spill_count": len(spills),
            "ebp_relative_spills": spills,
            "ebp_relative_reload_count": len(reloads),
            "ebp_relative_reloads": reloads,
            "reload_derived_zero_displacement_write_candidate_count": len(reload_write_candidates),
            "reload_derived_zero_displacement_write_candidates": reload_write_candidates,
            "reload_derived_other_dereference_count": len(reload_other_dereferences),
            "reload_derived_other_dereferences": reload_other_dereferences,
            "termination_counts": terminations,
        },
        "adjudication": {
            "materialized_plus_374_ebp_spill_reload_subset_complete": True,
            "ebp_reload_write_candidate_receivers_classified": False,
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
            "This successor adds only exact MOV spill/reload through unchanged EBP-relative memory cells after exact lea addr,[receiver+0x374] materialization.",
            "Pointer spill/reload/copy propagation requires complete 32-bit GPR operands; partial-register MOV is clobber-only.",
            "Direct/copy-only materialized dereferences are predecessor coverage and are not counted as new reload-derived candidates.",
            "Any non-MOV EBP-relative memory-like reference invalidates all tracked EBP cells conservatively; exact MOV spill replaces older tracked cells before installing new provenance.",
            "ESP-relative cells, implicit push/pop transport, cross-control-flow state, memory-stored non-EBP aliases, helper returns, indexed LEA and arithmetic reconstruction remain outside this subset.",
            "Any EBP write invalidates tracked cell identity; control boundaries clear all tracked state.",
            "Recovered receiver registers remain syntactic provenance only and do not imply Participants Manager identity.",
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe and classify only positive reload-derived +0x374 write receivers; extend another carrier class only if retail evidence survives this subset.",
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
