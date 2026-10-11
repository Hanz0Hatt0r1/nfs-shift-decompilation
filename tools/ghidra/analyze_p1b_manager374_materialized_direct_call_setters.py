#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374MaterializedDirectCallSetterProbe/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
MAX_CALLEE_INSTRUCTIONS = 96
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
SUBREG_PARENT = {
    "al": "eax", "ah": "eax", "ax": "eax", "eax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx", "ebx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx", "ecx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx", "edx": "edx",
    "si": "esi", "esi": "esi", "di": "edi", "edi": "edi",
    "bp": "ebp", "ebp": "ebp", "sp": "esp", "esp": "esp",
}
WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar",
    "fst", "fstp", "fist", "fistp", "fisttp",
}
NON_WRITING_FIRST_REG = {"cmp", "test", "push", "bt", "nop"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {"ret", "retn", "iret", "iretd", "int", "int3", "ud2", "hlt"}
INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
LEA_PLUS374 = re.compile(r"^\[(eax|ebx|ecx|edx|esi|edi|ebp|esp)\+0x0*374\]$", re.I)
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD|XMMWORD|TBYTE) PTR )?(?:(?:cs|ds|es|fs|gs|ss):)?\[([^\]]+)\]$", re.I)
ZERO_MEM = re.compile(r"^(eax|ebx|ecx|edx|esi|edi|ebp|esp)(?:\+0x0+)?$", re.I)
STACK_MEM = re.compile(r"^(esp|ebp)(?:([+-])0x([0-9a-f]+))?$", re.I)
DIRECT_TARGET = re.compile(r"^(?:0x)?([0-9a-fA-F]+)(?:\s+<[^>]*>)?$")
IMM = re.compile(r"^(?:0x)?([0-9a-fA-F]+)$", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).replace(", ", ",")


def split_ops(text: str) -> list[str]:
    return text.split(",") if text else []


def normalize_prefixed_instruction(mnemonic: str, operands: str) -> tuple[str, str, list[str]]:
    prefixes: list[str] = []
    mnemonic = mnemonic.lower()
    operands = norm(operands)
    while mnemonic in PREFIXES and operands:
        prefixes.append(mnemonic)
        pieces = operands.split(" ", 1)
        mnemonic = pieces[0].lower()
        operands = pieces[1] if len(pieces) == 2 else ""
    return mnemonic, operands, prefixes


def parent_reg(op: str) -> str | None:
    return SUBREG_PARENT.get(op.strip().lower())


def parse_imm(op: str) -> int | None:
    text = op.strip().lower()
    sign = 1
    if text.startswith("-"):
        sign = -1
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]
    match = IMM.fullmatch(text)
    return sign * int(match.group(1), 16) if match else None


def parse_direct_target(op: str) -> int | None:
    match = DIRECT_TARGET.fullmatch(op.strip())
    return int(match.group(1), 16) if match else None


def lea_plus374_base(op: str) -> str | None:
    match = LEA_PLUS374.fullmatch(op.replace(" ", ""))
    return match.group(1).lower() if match else None


def memory_expr(op: str) -> str | None:
    match = MEM.fullmatch(op.strip())
    return match.group(1).replace(" ", "").lower() if match else None


def zero_memory_reg(op: str) -> str | None:
    expr = memory_expr(op)
    if expr is None:
        return None
    match = ZERO_MEM.fullmatch(expr)
    return match.group(1).lower() if match else None


def stack_logical_key(op: str, esp_delta: int, ebp_delta: int | None) -> int | None:
    expr = memory_expr(op)
    if expr is None:
        return None
    match = STACK_MEM.fullmatch(expr)
    if not match:
        return None
    base = match.group(1).lower()
    off = 0
    if match.group(3):
        off = int(match.group(3), 16)
        if match.group(2) == "-":
            off = -off
    if base == "esp":
        return off - esp_delta
    if ebp_delta is None:
        return None
    return off - ebp_delta


def is_control(mnemonic: str) -> bool:
    return mnemonic in CONTROL or mnemonic.startswith("j") or mnemonic.startswith("loop")


def copy_prov(prov: dict) -> dict:
    return dict(prov)


def callee_scan(rows: list[tuple[int, str, str]], start_index: int, entry_aliases: dict[str, dict], stack_args: dict[int, dict]) -> dict:
    aliases = {reg: copy_prov(prov) for reg, prov in entry_aliases.items()}
    esp_delta = 0
    ebp_delta: int | None = None
    writes: list[dict] = []
    reads: list[dict] = []
    reloads: list[dict] = []
    termination = "instruction-limit"
    unsupported_stack_adjustment = False

    for local_index, (address, raw_mnemonic, raw_operands) in enumerate(rows[start_index:start_index + MAX_CALLEE_INSTRUCTIONS]):
        mnemonic, operands, _prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        if mnemonic == "call":
            termination = "nested-call"
            break
        if is_control(mnemonic):
            termination = "control-boundary"
            break

        if mnemonic == "push" and len(ops) == 1:
            esp_delta += 4
            continue
        if mnemonic == "pop" and len(ops) == 1:
            dst = parent_reg(ops[0])
            if dst:
                aliases.pop(dst, None)
            esp_delta -= 4
            continue
        if mnemonic in {"sub", "add"} and len(ops) == 2 and ops[0].lower() == "esp":
            amount = parse_imm(ops[1])
            if amount is None:
                unsupported_stack_adjustment = True
                termination = "unsupported-stack-adjustment"
                break
            esp_delta += amount if mnemonic == "sub" else -amount
            continue
        if mnemonic == "lea" and len(ops) == 2 and ops[0].lower() == "esp":
            expr = memory_expr(ops[1])
            match = STACK_MEM.fullmatch(expr or "")
            if not match or match.group(1).lower() != "esp":
                unsupported_stack_adjustment = True
                termination = "unsupported-stack-adjustment"
                break
            off = 0
            if match.group(3):
                off = int(match.group(3), 16)
                if match.group(2) == "-":
                    off = -off
            esp_delta -= off
            continue
        if mnemonic == "mov" and len(ops) == 2 and ops[0].lower() == "ebp" and ops[1].lower() == "esp":
            ebp_delta = esp_delta
            aliases.pop("ebp", None)
            continue
        if mnemonic in {"leave", "enter"} or (ops and ops[0].lower() == "esp" and mnemonic not in NON_WRITING_FIRST_REG):
            unsupported_stack_adjustment = True
            termination = "unsupported-stack-adjustment"
            break

        if ops:
            ptr = zero_memory_reg(ops[0])
            if ptr in aliases:
                prov = aliases[ptr]
                item = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "address_register": ptr,
                    "materializer_site": prov["materializer_site"],
                    "receiver_register": prov["receiver_register"],
                    "argument_channel": prov["argument_channel"],
                    "callee_instruction_index": local_index,
                }
                if mnemonic in WRITE_MNEMONICS:
                    writes.append(item)
                else:
                    reads.append(item)

        if mnemonic == "mov" and len(ops) == 2:
            dst, src = ops
            dst_reg = dst.lower() if dst.lower() in GPRS else None
            src_reg = src.lower() if src.lower() in GPRS else None
            if dst_reg:
                if src_reg in aliases:
                    aliases[dst_reg] = copy_prov(aliases[src_reg])
                    continue
                key = stack_logical_key(src, esp_delta, ebp_delta)
                if key in stack_args:
                    aliases[dst_reg] = copy_prov(stack_args[key])
                    reloads.append({
                        "site": f"0x{address:08x}",
                        "destination_register": dst_reg,
                        "logical_stack_offset": key,
                        "argument_channel": stack_args[key]["argument_channel"],
                    })
                    continue
                aliases.pop(dst_reg, None)
                continue
            parent = parent_reg(dst)
            if parent:
                aliases.pop(parent, None)
            continue

        if ops:
            parent = parent_reg(ops[0])
            if parent and parent in aliases and mnemonic not in NON_WRITING_FIRST_REG:
                aliases.pop(parent, None)

    return {
        "write_count": len(writes),
        "writes": writes,
        "read_count": len(reads),
        "reads": reads,
        "stack_argument_reload_count": len(reloads),
        "stack_argument_reloads": reloads,
        "termination": termination,
        "unsupported_stack_adjustment": unsupported_stack_adjustment,
    }


def scan_rows(rows: list[tuple[int, str, str]]) -> dict:
    index_by_address = {address: index for index, (address, _m, _o) in enumerate(rows)}
    tracked: dict[str, dict] = {}
    pushes: list[dict | None] = []
    materializers: list[dict] = []
    direct_boundaries: list[dict] = []
    indirect_boundaries: list[dict] = []
    write_candidates: list[dict] = []
    unresolved_direct_targets = 0

    for address, raw_mnemonic, raw_operands in rows:
        mnemonic, operands, _prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        if mnemonic == "lea" and len(ops) == 2 and ops[0].lower() in GPRS:
            base = lea_plus374_base(ops[1])
            if base is not None:
                dst = ops[0].lower()
                tracked[dst] = {
                    "materializer_site": f"0x{address:08x}",
                    "receiver_register": base,
                }
                pushes.clear()
                materializers.append({
                    "site": f"0x{address:08x}",
                    "address_register": dst,
                    "receiver_register": base,
                    "operands": operands,
                })
                continue

        if mnemonic == "mov" and len(ops) == 2 and ops[0].lower() in GPRS:
            dst, src = ops[0].lower(), ops[1].lower()
            if src in tracked:
                tracked[dst] = copy_prov(tracked[src])
            else:
                tracked.pop(dst, None)
            continue

        if mnemonic == "push" and len(ops) == 1 and tracked:
            src = ops[0].lower()
            pushes.append(copy_prov(tracked[src]) if src in tracked else None)
            continue

        if mnemonic == "call":
            entry_aliases: dict[str, dict] = {}
            for reg in ("ecx", "edx"):
                if reg in tracked:
                    prov = copy_prov(tracked[reg])
                    prov["argument_channel"] = reg
                    entry_aliases[reg] = prov

            stack_args: dict[int, dict] = {}
            for arg_index, prov in enumerate(reversed(pushes), 1):
                if prov is None:
                    continue
                item = copy_prov(prov)
                item["argument_channel"] = f"stack+0x{arg_index * 4:x}"
                stack_args[arg_index * 4] = item

            if entry_aliases or stack_args:
                target = parse_direct_target(operands)
                boundary = {
                    "callsite": f"0x{address:08x}",
                    "target": f"0x{target:08x}" if target is not None else None,
                    "register_argument_channels": sorted(entry_aliases),
                    "stack_argument_channels": [f"stack+0x{x:x}" for x in sorted(stack_args)],
                }
                if target is None:
                    indirect_boundaries.append(boundary)
                elif target not in index_by_address:
                    unresolved_direct_targets += 1
                    boundary["callee_scan"] = None
                    direct_boundaries.append(boundary)
                else:
                    result = callee_scan(rows, index_by_address[target], entry_aliases, stack_args)
                    boundary["callee_scan"] = result
                    direct_boundaries.append(boundary)
                    for write in result["writes"]:
                        write_candidates.append(dict(write, callsite=boundary["callsite"], target=boundary["target"]))
            tracked.clear()
            pushes.clear()
            continue

        if is_control(mnemonic):
            tracked.clear()
            pushes.clear()
            continue

        if mnemonic in {"add", "sub", "lea", "pop", "leave", "enter"} and ops and ops[0].lower() == "esp":
            pushes.clear()

        if ops:
            parent = parent_reg(ops[0])
            if parent and parent in tracked and mnemonic not in NON_WRITING_FIRST_REG:
                tracked.pop(parent, None)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "materialized_plus_374_seed_count": len(materializers),
            "materialized_plus_374_seeds": materializers,
            "direct_call_argument_boundary_count": len(direct_boundaries),
            "direct_call_argument_boundaries": direct_boundaries,
            "indirect_call_argument_boundary_count": len(indirect_boundaries),
            "indirect_call_argument_boundaries": indirect_boundaries,
            "unresolved_direct_target_count": unresolved_direct_targets,
            "direct_callee_write_through_candidate_count": len(write_candidates),
            "direct_callee_write_through_candidates": write_candidates,
        },
        "adjudication": {
            "materialized_plus_374_direct_call_argument_subset_scanned": True,
            "materialized_plus_374_direct_callee_write_through_candidates_classified": False,
            "materialized_helper_mediated_setter_surface_complete": False,
            "helper_returned_materialized_address_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Covers exact lea addr,[receiver+0x374], GPR MOV copies, ECX/EDX or PUSH argument forwarding at the first CALL, and one bounded direct callee span.",
            "Direct callee stack arguments are normalized across push/pop, immediate add/sub ESP, LEA ESP,[ESP+/-imm], and MOV EBP,ESP; unsupported stack mutations fail closed.",
            "Nested calls, branches, indirect callees, helper-returned target addresses, non-stack memory aliases, cross-CFG carry, runtime patching and external process mutation remain outside this subset.",
            "Only an explicit write/RMW mnemonic allowlist counts as a write through the recovered exact target-address alias.",
            "Recovered receiver registers and target-address aliases are syntactic provenance only; they do not establish Participants Manager identity.",
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe; classify any direct-callee write-through candidate by receiver identity, then extend only surviving indirect/helper-returned materialized-address classes.",
    }


def disassemble(executable: Path) -> list[tuple[int, str, str]]:
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


def analyze(executable: Path) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")
    result = scan_rows(disassemble(executable))
    result["authority"] = {
        "platform": "PC retail 1.02",
        "retail_executable_sha256": digest,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.executable)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
