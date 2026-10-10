#!/usr/bin/env python3
"""Bound straight-line constant-only synthesis of exact P1B HDVehicle+0x4330 carrier VAs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ConstantEncodedSynthesis/1"
EXPECTED_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SIZE = 8_801_792
CARRIERS = [
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
]
REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
INS_RE = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s*([a-z][a-z0-9]*)\s*(.*)$")
LEA_RE = re.compile(r"\[([a-z]{3})(?:([+-])0x([0-9a-f]+))?\]")
NONWRITING = {"cmp", "test", "push", "bt", "bts", "btc", "btr"}


def parse_imm(text: str) -> int | None:
    text = text.strip().lower()
    sign = 1
    if text.startswith("-"):
        sign = -1
        text = text[1:]
    if not text.startswith("0x"):
        return None
    try:
        return (sign * int(text, 16)) & 0xFFFFFFFF
    except ValueError:
        return None


def rol(value: int, count: int) -> int:
    count &= 31
    return value if not count else ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def ror(value: int, count: int) -> int:
    count &= 31
    return value if not count else ((value >> count) | (value << (32 - count))) & 0xFFFFFFFF


def is_control(mnemonic: str) -> bool:
    return (
        mnemonic.startswith("j") or mnemonic.startswith("call") or mnemonic.startswith("ret")
        or mnemonic.startswith("loop") or mnemonic in {"int", "int3", "iret", "iretd", "sysenter", "sysexit"}
    )


def scan_disassembly(text: str, carriers: set[int] | None = None) -> dict:
    carriers = set(CARRIERS if carriers is None else carriers)
    state: dict[str, int | None] = {reg: None for reg in REGS}
    instruction_count = 0
    control_reset_count = 0
    seeds = Counter()
    transitions = Counter()
    hits: list[dict] = []

    for line in text.splitlines():
        match = INS_RE.match(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        mnemonic = match.group(2).lower()
        operands = match.group(3).strip().lower()
        instruction_count += 1

        if is_control(mnemonic):
            state = {reg: None for reg in REGS}
            control_reset_count += 1
            continue

        parts = [item.strip() for item in operands.split(",")] if operands else []

        if mnemonic == "mov" and len(parts) == 2 and parts[0] in REGS:
            dst, src = parts
            if src in REGS:
                state[dst] = state[src]
            else:
                state[dst] = parse_imm(src)
                if state[dst] is not None:
                    seeds["mov_imm"] += 1

        elif mnemonic == "xor" and len(parts) == 2 and parts[0] in REGS:
            dst, src = parts
            if src == dst:
                state[dst] = 0
                seeds["xor_zero"] += 1
            else:
                imm = parse_imm(src)
                if state[dst] is not None and imm is not None:
                    state[dst] = (state[dst] ^ imm) & 0xFFFFFFFF
                    transitions["xor"] += 1
                else:
                    state[dst] = None

        elif mnemonic in {"add", "sub", "or", "and"} and len(parts) == 2 and parts[0] in REGS:
            dst, src = parts
            imm = parse_imm(src)
            if state[dst] is not None and imm is not None:
                value = state[dst]
                if mnemonic == "add":
                    state[dst] = (value + imm) & 0xFFFFFFFF
                elif mnemonic == "sub":
                    state[dst] = (value - imm) & 0xFFFFFFFF
                elif mnemonic == "or":
                    state[dst] = value | imm
                else:
                    state[dst] = value & imm
                transitions[mnemonic] += 1
            else:
                state[dst] = None

        elif mnemonic in {"inc", "dec", "neg", "not"} and len(parts) == 1 and parts[0] in REGS:
            dst = parts[0]
            if state[dst] is not None:
                value = state[dst]
                if mnemonic == "inc":
                    state[dst] = (value + 1) & 0xFFFFFFFF
                elif mnemonic == "dec":
                    state[dst] = (value - 1) & 0xFFFFFFFF
                elif mnemonic == "neg":
                    state[dst] = (-value) & 0xFFFFFFFF
                else:
                    state[dst] = (~value) & 0xFFFFFFFF
                transitions[mnemonic] += 1
            else:
                state[dst] = None

        elif mnemonic in {"shl", "sal", "shr", "sar", "rol", "ror"} and len(parts) == 2 and parts[0] in REGS:
            dst, src = parts
            imm = parse_imm(src)
            if state[dst] is not None and imm is not None:
                value = state[dst]
                count = imm & 31
                if mnemonic in {"shl", "sal"}:
                    state[dst] = (value << count) & 0xFFFFFFFF
                elif mnemonic == "shr":
                    state[dst] = (value >> count) & 0xFFFFFFFF
                elif mnemonic == "sar":
                    signed = value if value < 0x80000000 else value - 0x100000000
                    state[dst] = (signed >> count) & 0xFFFFFFFF
                elif mnemonic == "rol":
                    state[dst] = rol(value, count)
                else:
                    state[dst] = ror(value, count)
                transitions[mnemonic] += 1
            else:
                state[dst] = None

        elif mnemonic == "lea" and len(parts) == 2 and parts[0] in REGS:
            dst, src = parts
            match_lea = LEA_RE.fullmatch(src.replace(" ", ""))
            if match_lea and match_lea.group(1) in REGS and state[match_lea.group(1)] is not None:
                value = state[match_lea.group(1)]
                if match_lea.group(2):
                    delta = int(match_lea.group(3), 16)
                    value = (value + delta if match_lea.group(2) == "+" else value - delta) & 0xFFFFFFFF
                state[dst] = value
                transitions["lea"] += 1
            else:
                state[dst] = None

        elif parts and parts[0] in REGS and mnemonic not in NONWRITING:
            state[parts[0]] = None

        for reg, value in state.items():
            if value in carriers:
                hits.append({
                    "address": f"0x{address:08x}",
                    "register": reg,
                    "value": f"0x{value:08x}",
                    "mnemonic": mnemonic,
                    "operands": operands,
                })

    return {
        "instruction_count": instruction_count,
        "control_flow_reset_count": control_reset_count,
        "constant_seed_count": sum(seeds.values()),
        "constant_seed_counts": dict(sorted(seeds.items())),
        "recognized_transition_count": sum(transitions.values()),
        "recognized_transition_counts": dict(sorted(transitions.items())),
        "exact_carrier_synthesis_hit_count": len(hits),
        "exact_carrier_synthesis_hits": hits,
    }


def analyze(exe: Path) -> dict:
    payload = exe.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != EXPECTED_SIZE:
        raise ValueError(f"retail size mismatch: {len(payload)}")
    if digest != EXPECTED_SHA256:
        raise ValueError(f"retail sha256 mismatch: {digest}")

    proc = subprocess.run(
        ["objdump", "-d", "-Mintel", str(exe)], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    scan = scan_disassembly(proc.stdout)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": EXPECTED_SHA256,
            "retail_executable_size": EXPECTED_SIZE,
            "machine_disassembly_adjudicates": True,
        },
        "scope": {
            "exact_carrier_count": len(CARRIERS),
            "exact_carriers": [f"0x{x:08x}" for x in CARRIERS],
            "model": "straight-line GPR constant propagation with reset at every control-transfer boundary",
            "tracked_registers": sorted(REGS),
            "tracked_operations": ["mov imm/reg", "xor", "add", "sub", "or", "and", "inc", "dec", "neg", "not", "shl/sal", "shr", "sar", "rol", "ror", "lea reg,[reg+/-imm]"],
            "memory_or_table_loads_in_scope": False,
        },
        "scan": scan,
        "adjudication": {
            "constant_only_encoded_carrier_synthesis_subset_complete": True,
            "constant_only_encoded_exact_carrier_synthesis_found": bool(scan["exact_carrier_synthesis_hit_count"]),
            "computed_or_encoded_code_pointers_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only constant-only straight-line register synthesis within the recognized operation set.",
            "State resets at calls, jumps, conditional branches, returns and other control transfers; path joins are intentionally not modeled.",
            "Memory/table-derived values, delayed module-base consumers, split arithmetic across control-flow boundaries, opaque helper returns, runtime patching and copied pointers remain open.",
            "No identity is inferred from numeric offset equality."
        ],
        "next_step": "Bound memory/table-derived and cross-block encoded carrier reconstruction, then classify any positive exact-carrier stores/copies."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.exe)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
