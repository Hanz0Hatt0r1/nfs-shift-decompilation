#!/usr/bin/env python3
"""Bound stack spill/reload persistence of helper-returned receiver+0x374 targets."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

FORMAT = "SHIFT.P1B.Manager374HelperReturnedTargetStackPersistenceProbe/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
MAX_POST_INSTRUCTIONS = 64
WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar",
    "fst", "fstp", "fist", "fistp", "fisttp",
}
NON_WRITING_FIRST_REG = {"cmp", "test", "push", "bt", "nop"}
STACK_EXPR = re.compile(r"^(esp|ebp)(?:([+-])0x([0-9a-f]+))?$", re.I)


def load_base():
    path = Path(__file__).with_name("analyze_p1b_manager374_helper_returned_materialized_targets.py")
    spec = importlib.util.spec_from_file_location("_p1b_helper_returned_base", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load sibling probe: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def stack_key(op: str, esp_delta: int) -> tuple[str, int] | None:
    expr = BASE.memory_expr(op)
    if expr is None:
        return None
    match = STACK_EXPR.fullmatch(expr)
    if not match:
        return None
    base = match.group(1).lower()
    off = 0
    if match.group(3):
        off = int(match.group(3), 16)
        if match.group(2) == "-":
            off = -off
    return (base, off - esp_delta if base == "esp" else off)


def render_key(key: tuple[str, int]) -> str:
    base, off = key
    sign = "+" if off >= 0 else "-"
    return f"{base}{sign}0x{abs(off):x}"


def copy_prov(prov: dict) -> dict:
    return dict(prov)


def scan_post_stack(rows: list[tuple[int, str, str]], call_index: int, helper: dict) -> dict:
    regs: dict[str, dict] = {
        "eax": {
            "helper_target": helper["helper_target"],
            "helper_argument_channel": helper["return_argument_channel"],
            "helper_return_site": helper["return_site"],
            "copy_depth": 0,
            "reloaded_from_stack": False,
            "reload_key": None,
        }
    }
    stack_aliases: dict[tuple[str, int], dict] = {}
    esp_delta = 0
    spills: list[dict] = []
    reloads: list[dict] = []
    reload_writes: list[dict] = []
    direct_no_reload_writes: list[dict] = []
    non_stack_escapes: list[dict] = []
    stack_overwrites = 0
    termination = "instruction-limit"

    for post_index, (address, raw_mnemonic, raw_operands) in enumerate(rows[call_index + 1:call_index + 1 + MAX_POST_INSTRUCTIONS]):
        mnemonic, operands, prefixes = BASE.normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        ops = BASE.split_ops(operands)

        if mnemonic == "call" or BASE.is_branch_or_trap(mnemonic) or mnemonic in {"ret", "retn"}:
            termination = "control-boundary"
            break

        if mnemonic == "push" and len(ops) == 1:
            esp_delta += 4
            key = ("esp", -esp_delta)
            src = ops[0].lower()
            if src in regs:
                prov = copy_prov(regs[src])
                stack_aliases[key] = prov
                spills.append({
                    "site": f"0x{address:08x}",
                    "kind": "push",
                    "source_register": src,
                    "logical_stack_key": render_key(key),
                })
            else:
                stack_aliases.pop(key, None)
            continue

        if mnemonic == "pop" and len(ops) == 1:
            key = ("esp", -esp_delta)
            dst = BASE.parent_reg(ops[0])
            if dst:
                if key in stack_aliases:
                    prov = copy_prov(stack_aliases[key])
                    prov["reloaded_from_stack"] = True
                    prov["reload_key"] = render_key(key)
                    prov["copy_depth"] = 0
                    regs[dst] = prov
                    reloads.append({
                        "site": f"0x{address:08x}",
                        "kind": "pop",
                        "destination_register": dst,
                        "logical_stack_key": render_key(key),
                    })
                else:
                    regs.pop(dst, None)
            stack_aliases.pop(key, None)
            esp_delta -= 4
            continue

        if mnemonic in {"sub", "add"} and len(ops) == 2 and ops[0].lower() == "esp":
            amount = BASE.parse_imm(ops[1])
            if amount is None:
                termination = "unsupported-stack-adjustment"
                break
            esp_delta += amount if mnemonic == "sub" else -amount
            continue

        if mnemonic == "lea" and len(ops) == 2 and ops[0].lower() == "esp":
            expr = BASE.memory_expr(ops[1])
            match = STACK_EXPR.fullmatch(expr or "")
            if not match or match.group(1).lower() != "esp":
                termination = "unsupported-stack-adjustment"
                break
            off = 0
            if match.group(3):
                off = int(match.group(3), 16)
                if match.group(2) == "-":
                    off = -off
            esp_delta -= off
            continue

        if mnemonic in {"leave", "enter"} or (ops and ops[0].lower() == "esp"):
            termination = "unsupported-stack-adjustment"
            break

        if ops:
            ptr = BASE.zero_memory_reg(ops[0])
            if ptr in regs:
                prov = regs[ptr]
                row = {
                    "site": f"0x{address:08x}",
                    "mnemonic": mnemonic,
                    "operands": operands,
                    "address_register": ptr,
                    "helper_target": prov["helper_target"],
                    "helper_argument_channel": prov["helper_argument_channel"],
                    "helper_return_site": prov["helper_return_site"],
                    "copy_depth": prov["copy_depth"],
                    "reload_key": prov["reload_key"],
                    "caller_post_index": post_index,
                }
                if mnemonic in WRITE_MNEMONICS:
                    if prov["reloaded_from_stack"]:
                        reload_writes.append(row)
                    else:
                        direct_no_reload_writes.append(row)

        if mnemonic == "mov" and len(ops) == 2:
            dst, src = ops
            dst_lower = dst.lower()
            src_lower = src.lower()
            dst_reg = dst_lower if dst_lower in BASE.TRACKED_GPRS else None
            src_reg = src_lower if src_lower in BASE.TRACKED_GPRS else None
            dst_key = stack_key(dst, esp_delta)
            src_key = stack_key(src, esp_delta)

            if dst_reg:
                if src_reg in regs:
                    prov = copy_prov(regs[src_reg])
                    prov["copy_depth"] += 1
                    regs[dst_reg] = prov
                    continue
                if src_key is not None and src_key in stack_aliases:
                    prov = copy_prov(stack_aliases[src_key])
                    prov["reloaded_from_stack"] = True
                    prov["reload_key"] = render_key(src_key)
                    prov["copy_depth"] = 0
                    regs[dst_reg] = prov
                    reloads.append({
                        "site": f"0x{address:08x}",
                        "kind": "mov",
                        "destination_register": dst_reg,
                        "logical_stack_key": render_key(src_key),
                    })
                    continue
                regs.pop(dst_reg, None)
                continue

            if dst_key is not None:
                if src_reg in regs:
                    stack_aliases[dst_key] = copy_prov(regs[src_reg])
                    spills.append({
                        "site": f"0x{address:08x}",
                        "kind": "mov",
                        "source_register": src_reg,
                        "logical_stack_key": render_key(dst_key),
                    })
                else:
                    if dst_key in stack_aliases:
                        stack_overwrites += 1
                    stack_aliases.pop(dst_key, None)
                continue

            if BASE.memory_expr(dst) is not None and src_reg in regs:
                prov = regs[src_reg]
                non_stack_escapes.append({
                    "site": f"0x{address:08x}",
                    "source_register": src_reg,
                    "destination": dst,
                    "helper_target": prov["helper_target"],
                    "helper_argument_channel": prov["helper_argument_channel"],
                })

            parent = BASE.parent_reg(dst)
            if parent:
                regs.pop(parent, None)
            continue

        if ops:
            dst_key = stack_key(ops[0], esp_delta)
            if dst_key is not None and mnemonic in WRITE_MNEMONICS:
                if dst_key in stack_aliases:
                    stack_overwrites += 1
                stack_aliases.pop(dst_key, None)

        for reg in BASE.implicit_clobbers(mnemonic, ops, prefixes):
            regs.pop(reg, None)
        if ops:
            parent = BASE.parent_reg(ops[0])
            if parent in regs and mnemonic not in NON_WRITING_FIRST_REG:
                regs.pop(parent, None)

    return {
        "spill_count": len(spills),
        "spills": spills,
        "reload_count": len(reloads),
        "reloads": reloads,
        "reload_derived_write_count": len(reload_writes),
        "reload_derived_writes": reload_writes,
        "direct_no_reload_write_count": len(direct_no_reload_writes),
        "direct_no_reload_writes": direct_no_reload_writes,
        "non_stack_persistence_escape_count": len(non_stack_escapes),
        "non_stack_persistence_escapes": non_stack_escapes,
        "stack_overwrite_invalidation_count": stack_overwrites,
        "termination": termination,
    }


def scan_rows(rows: list[tuple[int, str, str]]) -> dict:
    index_by_address = {address: index for index, (address, _mnemonic, _operands) in enumerate(rows)}
    helper_cache: dict[int, dict] = {}
    qualifying_call_count = 0
    post_scans: list[dict] = []
    reload_write_candidates: list[dict] = []
    non_stack_escapes: list[dict] = []

    for call_index, (address, raw_mnemonic, raw_operands) in enumerate(rows):
        mnemonic, operands, _prefixes = BASE.normalize_prefixed_instruction(raw_mnemonic, raw_operands)
        if mnemonic != "call":
            continue
        target = BASE.parse_direct_target(operands)
        if target is None or target not in index_by_address:
            continue
        if target not in helper_cache:
            helper = BASE.analyze_helper(rows, index_by_address[target])
            helper["helper_target"] = f"0x{target:08x}"
            helper_cache[target] = helper
        helper = helper_cache[target]
        if not helper.get("qualified"):
            continue
        qualifying_call_count += 1
        post = scan_post_stack(rows, call_index, helper)
        row = {
            "callsite": f"0x{address:08x}",
            "target": f"0x{target:08x}",
            "return_argument_channel": helper["return_argument_channel"],
            "helper_return_site": helper["return_site"],
            "post_stack_scan": post,
        }
        post_scans.append(row)
        for candidate in post["reload_derived_writes"]:
            reload_write_candidates.append(dict(candidate, callsite=row["callsite"], target=row["target"]))
        for escape in post["non_stack_persistence_escapes"]:
            non_stack_escapes.append(dict(escape, callsite=row["callsite"], target=row["target"]))

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "qualified_helper_callsite_count": qualifying_call_count,
            "post_return_stack_scan_count": len(post_scans),
            "post_return_stack_scans": post_scans,
            "stack_reload_derived_write_candidate_count": len(reload_write_candidates),
            "stack_reload_derived_write_candidates": reload_write_candidates,
            "non_stack_persistence_escape_count": len(non_stack_escapes),
            "non_stack_persistence_escapes": non_stack_escapes,
        },
        "adjudication": {
            "helper_returned_target_stack_persistence_subset_scanned": True,
            "helper_returned_target_stack_reload_write_candidates_classified": False,
            "helper_returned_target_non_stack_persistence_complete": False,
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
            "Seeds only qualified direct-local helper returns proven by SHIFT.P1B.Manager374HelperReturnedMaterializedTargetProbe/1 semantics.",
            "Tracks caller-side exact GPR copies plus EBP-relative and ESP-normalized stack spill/reload for at most 64 instructions after the helper call.",
            "A new write candidate must pass through an actual stack reload; direct EAX/GPR writes remain owned by the immediate post-return probe.",
            "EBP-relative persistence is syntactic fixed-base persistence and requires later candidate classification; the probe does not infer that every EBP use is a canonical stack frame.",
            "Non-stack memory persistence is inventoried as an escape but not followed. Calls/control boundaries, dynamic stack adjustment, persisted-return helper chaining, runtime patching and external mutation remain outside scope."
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe; classify stack-reload write candidates and non-stack persistence escapes, then extend only a positive surviving persisted-return carrier class.",
    }


def analyze(executable: Path) -> dict:
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected executable SHA: {digest}")
    rows = BASE.disassemble(executable)
    result = scan_rows(rows)
    result["authority"] = {
        "platform": "PC retail 1.02",
        "retail_executable_sha256": digest,
        "upstream_helper_semantics": BASE.FORMAT,
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
