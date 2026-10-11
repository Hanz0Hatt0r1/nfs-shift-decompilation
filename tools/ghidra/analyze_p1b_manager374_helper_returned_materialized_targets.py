#!/usr/bin/env python3
"""Bound helpers that return an exact entry argument plus 0x374, then callers that write through it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
TARGET_DELTA = 0x374
MAX_HELPER_INSTRUCTIONS = 96
MAX_CALLER_POST_INSTRUCTIONS = 32
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
TRACKED_GPRS = GPRS - {"esp"}
PREFIXES = {"lock", "rep", "repe", "repz", "repne", "repnz"}
CONTROL = {"ret", "retn", "iret", "iretd", "int", "int3", "ud2", "hlt"}
NON_WRITING_FIRST_REG = {"cmp", "test", "push", "bt", "nop"}
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
INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
DIRECT_TARGET = re.compile(r"^(?:0x)?([0-9a-fA-F]+)(?:\s+<[^>]*>)?$")
IMM = re.compile(r"^(?:0x)?([0-9a-fA-F]+)$", re.I)
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD|XMMWORD|TBYTE) PTR )?(?:(?:cs|ds|es|fs|gs|ss):)?\[([^\]]+)\]$", re.I)
STACK_MEM = re.compile(r"^(esp|ebp)(?:([+-])0x([0-9a-f]+))?$", re.I)
SIMPLE_LEA = re.compile(r"^\[(eax|ebx|ecx|edx|esi|edi|ebp)(?:([+-])0x([0-9a-f]+))?\]$", re.I)
ZERO_MEM = re.compile(r"^(eax|ebx|ecx|edx|esi|edi|ebp|esp)(?:\+0x0+)?$", re.I)


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


def memory_expr(op: str) -> str | None:
    match = MEM.fullmatch(op.strip())
    return match.group(1).replace(" ", "").lower() if match else None


def zero_memory_reg(op: str) -> str | None:
    expr = memory_expr(op)
    if expr is None:
        return None
    match = ZERO_MEM.fullmatch(expr)
    return match.group(1).lower() if match else None


def simple_lea(op: str) -> tuple[str, int] | None:
    match = SIMPLE_LEA.fullmatch(op.replace(" ", ""))
    if not match:
        return None
    delta = 0
    if match.group(3):
        delta = int(match.group(3), 16)
        if match.group(2) == "-":
            delta = -delta
    return match.group(1).lower(), delta


def stack_logical_offset(op: str, esp_delta: int, ebp_delta: int | None) -> int | None:
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


def is_branch_or_trap(mnemonic: str) -> bool:
    return mnemonic in {"iret", "iretd", "int", "int3", "ud2", "hlt"} or mnemonic.startswith("j") or mnemonic.startswith("loop")


def copy_prov(prov: dict) -> dict:
    return {"argument_channel": prov["argument_channel"], "delta": prov["delta"]}


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
    if mnemonic in {"cmpxchg", "cmpxchg8b"}:
        clobbered.add("eax")
        if mnemonic == "cmpxchg8b":
            clobbered.add("edx")
    if mnemonic in {"xchg", "xadd"}:
        for op in ops[:2]:
            parent = parent_reg(op)
            if parent:
                clobbered.add(parent)
    if mnemonic in {"popa", "popad"}:
        clobbered.update(TRACKED_GPRS)
    if mnemonic.startswith(("movs", "cmps", "stos", "lods", "scas")):
        clobbered.update({"eax", "ecx", "esi", "edi"})
    if any(prefix.startswith("rep") for prefix in prefixes):
        clobbered.add("ecx")
    return clobbered


def analyze_helper(rows: list[tuple[int, str, str]], start_index: int) -> dict:
    regs: dict[str, dict] = {
        "ecx": {"argument_channel": "ecx", "delta": 0},
        "edx": {"argument_channel": "edx", "delta": 0},
    }
    esp_delta = 0
    ebp_delta: int | None = None
    stack_argument_loads: list[dict] = []
    transitions: list[dict] = []

    for local_index, (address, raw_mnemonic, raw_operands) in enumerate(rows[start_index:start_index + MAX_HELPER_INSTRUCTIONS]):
        mnemonic, operands, prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        if mnemonic == "call":
            return {"qualified": False, "termination": "nested-call", "instruction_count": local_index + 1}
        if is_branch_or_trap(mnemonic):
            return {"qualified": False, "termination": "control-boundary", "instruction_count": local_index + 1}
        if mnemonic in {"ret", "retn"}:
            eax = regs.get("eax")
            qualified = bool(eax and eax["delta"] == TARGET_DELTA)
            return {
                "qualified": qualified,
                "termination": "return",
                "instruction_count": local_index + 1,
                "return_site": f"0x{address:08x}",
                "return_argument_channel": eax["argument_channel"] if qualified else None,
                "return_delta": eax["delta"] if eax else None,
                "stack_argument_loads": stack_argument_loads,
                "transitions": transitions,
            }

        if mnemonic == "push" and len(ops) == 1:
            esp_delta += 4
            continue
        if mnemonic == "pop" and len(ops) == 1:
            dst = parent_reg(ops[0])
            if dst:
                regs.pop(dst, None)
            esp_delta -= 4
            continue
        if mnemonic in {"sub", "add"} and len(ops) == 2 and ops[0].lower() == "esp":
            amount = parse_imm(ops[1])
            if amount is None:
                return {"qualified": False, "termination": "unsupported-stack-adjustment", "instruction_count": local_index + 1}
            esp_delta += amount if mnemonic == "sub" else -amount
            continue
        if mnemonic == "lea" and len(ops) == 2 and ops[0].lower() == "esp":
            expr = memory_expr(ops[1])
            match = STACK_MEM.fullmatch(expr or "")
            if not match or match.group(1).lower() != "esp":
                return {"qualified": False, "termination": "unsupported-stack-adjustment", "instruction_count": local_index + 1}
            off = 0
            if match.group(3):
                off = int(match.group(3), 16)
                if match.group(2) == "-":
                    off = -off
            esp_delta -= off
            continue
        if mnemonic == "mov" and len(ops) == 2 and ops[0].lower() == "ebp" and ops[1].lower() == "esp":
            ebp_delta = esp_delta
            regs.pop("ebp", None)
            continue
        if mnemonic == "mov" and len(ops) == 2 and ops[0].lower() == "esp" and ops[1].lower() == "ebp":
            if ebp_delta is None:
                return {"qualified": False, "termination": "unsupported-stack-adjustment", "instruction_count": local_index + 1}
            esp_delta = ebp_delta
            continue
        if mnemonic == "leave":
            if ebp_delta is None:
                return {"qualified": False, "termination": "unsupported-stack-adjustment", "instruction_count": local_index + 1}
            esp_delta = ebp_delta - 4
            ebp_delta = None
            regs.pop("ebp", None)
            continue
        if mnemonic == "enter" or (ops and ops[0].lower() == "esp"):
            return {"qualified": False, "termination": "unsupported-stack-adjustment", "instruction_count": local_index + 1}

        if mnemonic == "mov" and len(ops) == 2:
            dst, src = ops
            dst_reg = dst.lower() if dst.lower() in TRACKED_GPRS else None
            src_reg = src.lower() if src.lower() in TRACKED_GPRS else None
            if dst_reg:
                if src_reg in regs:
                    regs[dst_reg] = copy_prov(regs[src_reg])
                    transitions.append({"site": f"0x{address:08x}", "kind": "gpr-copy", "destination": dst_reg, **regs[dst_reg]})
                    continue
                stack_off = stack_logical_offset(src, esp_delta, ebp_delta)
                if stack_off is not None and stack_off > 0 and stack_off % 4 == 0:
                    prov = {"argument_channel": f"stack+0x{stack_off:x}", "delta": 0}
                    regs[dst_reg] = prov
                    stack_argument_loads.append({"site": f"0x{address:08x}", "destination": dst_reg, "logical_stack_offset": stack_off})
                    continue
                regs.pop(dst_reg, None)
                continue
            parent = parent_reg(dst)
            if parent:
                regs.pop(parent, None)
            continue

        if mnemonic == "lea" and len(ops) == 2 and ops[0].lower() in TRACKED_GPRS:
            dst = ops[0].lower()
            parsed = simple_lea(ops[1])
            if parsed and parsed[0] in regs:
                base, delta = parsed
                prov = copy_prov(regs[base])
                prov["delta"] += delta
                regs[dst] = prov
                transitions.append({"site": f"0x{address:08x}", "kind": "lea-base-disp", "destination": dst, **prov})
            else:
                regs.pop(dst, None)
            continue

        if mnemonic in {"add", "sub"} and len(ops) == 2 and ops[0].lower() in TRACKED_GPRS:
            dst = ops[0].lower()
            amount = parse_imm(ops[1])
            if dst in regs and amount is not None:
                regs[dst]["delta"] += amount if mnemonic == "add" else -amount
                transitions.append({"site": f"0x{address:08x}", "kind": "immediate-arithmetic", "destination": dst, **regs[dst]})
            else:
                regs.pop(dst, None)
            continue

        for reg in implicit_clobbers(mnemonic, ops, prefixes):
            regs.pop(reg, None)
        if ops:
            parent = parent_reg(ops[0])
            if parent in regs and mnemonic not in NON_WRITING_FIRST_REG:
                regs.pop(parent, None)

    return {"qualified": False, "termination": "instruction-limit", "instruction_count": MAX_HELPER_INSTRUCTIONS}


def scan_caller_post_return(rows: list[tuple[int, str, str]], call_index: int, helper: dict) -> dict:
    tracked: dict[str, dict] = {
        "eax": {
            "helper_target": helper["helper_target"],
            "argument_channel": helper["return_argument_channel"],
            "return_site": helper["return_site"],
            "copy_depth": 0,
        }
    }
    writes: list[dict] = []
    reads: list[dict] = []
    copies: list[dict] = []
    termination = "instruction-limit"

    for post_index, (address, raw_mnemonic, raw_operands) in enumerate(rows[call_index + 1:call_index + 1 + MAX_CALLER_POST_INSTRUCTIONS]):
        mnemonic, operands, prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = split_ops(operands)

        if mnemonic == "call" or is_branch_or_trap(mnemonic) or mnemonic in {"ret", "retn"}:
            termination = "control-boundary"
            break

        if ops:
            ptr = zero_memory_reg(ops[0])
            if ptr in tracked:
                prov = tracked[ptr]
                item = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "address_register": ptr,
                    "copy_depth": prov["copy_depth"],
                    "helper_target": prov["helper_target"],
                    "helper_argument_channel": prov["argument_channel"],
                    "helper_return_site": prov["return_site"],
                    "caller_post_index": post_index,
                }
                if mnemonic in WRITE_MNEMONICS:
                    writes.append(item)
                else:
                    reads.append(item)

        if mnemonic == "mov" and len(ops) == 2 and ops[0].lower() in TRACKED_GPRS:
            dst, src = ops[0].lower(), ops[1].lower()
            if src in tracked:
                prov = dict(tracked[src])
                prov["copy_depth"] += 1
                tracked[dst] = prov
                copies.append({"site": f"0x{address:08x}", "source": src, "destination": dst, "copy_depth": prov["copy_depth"]})
            else:
                tracked.pop(dst, None)
            continue

        for reg in implicit_clobbers(mnemonic, ops, prefixes):
            tracked.pop(reg, None)
        if ops:
            parent = parent_reg(ops[0])
            if parent in tracked and mnemonic not in NON_WRITING_FIRST_REG:
                tracked.pop(parent, None)

    return {
        "write_count": len(writes),
        "writes": writes,
        "read_count": len(reads),
        "reads": reads,
        "copy_count": len(copies),
        "copies": copies,
        "termination": termination,
    }


def scan_rows(rows: list[tuple[int, str, str]]) -> dict:
    index_by_address = {address: index for index, (address, _mnemonic, _operands) in enumerate(rows)}
    helper_cache: dict[int, dict] = {}
    helper_candidates: dict[int, dict] = {}
    candidate_calls: list[dict] = []
    write_candidates: list[dict] = []
    unresolved_direct_target_count = 0
    indirect_call_count = 0

    for call_index, (address, raw_mnemonic, raw_operands) in enumerate(rows):
        mnemonic, operands, _prefixes = normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        if mnemonic != "call":
            continue
        target = parse_direct_target(operands)
        if target is None:
            indirect_call_count += 1
            continue
        start_index = index_by_address.get(target)
        if start_index is None:
            unresolved_direct_target_count += 1
            continue
        if target not in helper_cache:
            helper_scan = analyze_helper(rows, start_index)
            helper_scan["helper_target"] = f"0x{target:08x}"
            helper_cache[target] = helper_scan
            if helper_scan.get("qualified"):
                helper_candidates[target] = helper_scan
        helper = helper_cache[target]
        if not helper.get("qualified"):
            continue
        post = scan_caller_post_return(rows, call_index, helper)
        call_row = {
            "callsite": f"0x{address:08x}",
            "target": f"0x{target:08x}",
            "return_argument_channel": helper["return_argument_channel"],
            "helper_return_site": helper["return_site"],
            "caller_post_scan": post,
        }
        candidate_calls.append(call_row)
        for write in post["writes"]:
            write_candidates.append(dict(write, callsite=call_row["callsite"], target=call_row["target"]))

    helpers = []
    for target in sorted(helper_candidates):
        helper = helper_candidates[target]
        helpers.append({
            "target": f"0x{target:08x}",
            "return_argument_channel": helper["return_argument_channel"],
            "return_site": helper["return_site"],
            "instruction_count": helper["instruction_count"],
            "stack_argument_loads": helper.get("stack_argument_loads", []),
            "transitions": helper.get("transitions", []),
        })

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "direct_local_helper_target_count": len(helper_cache),
            "qualified_helper_return_target_count": len(helpers),
            "qualified_helper_return_targets": helpers,
            "qualified_helper_callsite_count": len(candidate_calls),
            "qualified_helper_callsites": candidate_calls,
            "post_return_write_through_candidate_count": len(write_candidates),
            "post_return_write_through_candidates": write_candidates,
            "unresolved_direct_target_count": unresolved_direct_target_count,
            "indirect_call_count": indirect_call_count,
        },
        "adjudication": {
            "direct_helper_returned_plus_374_target_subset_scanned": True,
            "helper_returned_plus_374_write_candidates_classified": False,
            "helper_returned_materialized_address_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "external_or_unknown_origin_outer_alias_surface_complete": False,
            "independent_unnamed_opaque_or_external_runtime_root_synthesis_complete": False,
            "unrecognized_runtime_transform_root_origin_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Qualifies only direct local helpers whose first bounded straight-line return leaves EAX equal to entry ECX, entry EDX, or a positive stack argument plus exactly 0x374.",
            "Helper analysis stops on nested calls, branches/traps, unsupported stack mutations, or the 96-instruction bound; no path merge is inferred.",
            "Caller analysis follows only EAX and exact GPR MOV copies for 32 instructions and stops at the next call/control boundary; stack persistence and memory persistence of the returned target are outside scope.",
            "Only explicit zero-displacement write/RMW through the recovered returned-target alias counts as a candidate; read-only dereferences remain separate.",
            "Indirect calls, external helpers, helper-returned targets synthesized from unrelated opaque inputs, runtime patching/generated code, and external process mutation remain open.",
            "A helper argument channel is syntactic ABI provenance only and does not establish Participants Manager receiver identity."
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe and classify every post-return write candidate by callsite receiver provenance; then extend only surviving indirect/external helper-return or persisted-return carrier classes before final identity adjudication.",
    }


def disassemble(executable: Path) -> list[tuple[int, str, str]]:
    proc = subprocess.run(
        ["objdump", "-d", "-Mintel", str(executable)],
        capture_output=True,
        text=True,
        check=True,
        errors="replace",
    )
    rows: list[tuple[int, str, str]] = []
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
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
