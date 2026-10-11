#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FORMAT = "SHIFT.P1B.Manager374WholeImagePlus374WriterProbe/1"
GPRS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}

# Intentionally explicit. Any first-memory-operand +0x374 form outside this set is
# reported separately instead of being guessed as a write.
WRITE_MNEMONICS = {
    "mov", "movd", "movq", "movss", "movsd", "movaps", "movups", "movapd", "movupd",
    "movdqa", "movdqu", "movnti", "movntq", "movntdq", "movntps", "movntpd",
    "add", "sub", "adc", "sbb", "and", "or", "xor", "inc", "dec", "not", "neg",
    "xchg", "cmpxchg", "cmpxchg8b", "bts", "btr", "btc",
    "rol", "ror", "rcl", "rcr", "shl", "shr", "sal", "sar",
    "fst", "fstp", "fist", "fistp", "fisttp",
}

INSN = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$")
MEM = re.compile(r"^(?:(?:BYTE|WORD|DWORD|QWORD|XMMWORD|TBYTE) PTR )?\[([^\]]+)\]$", re.I)
GPR_RE = re.compile(r"\b(eax|ebx|ecx|edx|esi|edi|ebp|esp)\b", re.I)
PLUS_374 = re.compile(r"(?:^|\+)0x0*374(?:$|\+)", re.I)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).replace(", ", ",")


def split_ops(text: str) -> list[str]:
    return text.split(",") if text else []


def plus374_memory(op: str):
    match = MEM.fullmatch(op.strip())
    if not match:
        return None
    expr = match.group(1).replace(" ", "").lower()
    if not PLUS_374.search(expr):
        return None
    regs = sorted(set(GPR_RE.findall(expr)))
    if not regs:
        return None
    return {"expression": expr, "registers": regs}


def scan_rows(rows):
    write_candidates = []
    other_first_memory_forms = []
    mnemonic_counts: dict[str, int] = {}
    other_mnemonic_counts: dict[str, int] = {}

    for address, mnemonic, operands in rows:
        ops = split_ops(operands)
        if not ops:
            continue
        info = plus374_memory(ops[0])
        if info is None:
            continue
        row = {
            "site": f"0x{address:08x}",
            "mnemonic": mnemonic,
            "destination": ops[0],
            "expression": info["expression"],
            "registers": info["registers"],
            "operands": operands,
        }
        if mnemonic in WRITE_MNEMONICS:
            write_candidates.append(row)
            mnemonic_counts[mnemonic] = mnemonic_counts.get(mnemonic, 0) + 1
        else:
            other_first_memory_forms.append(row)
            other_mnemonic_counts[mnemonic] = other_mnemonic_counts.get(mnemonic, 0) + 1

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "surface": {
            "exact_plus_374_write_candidate_count": len(write_candidates),
            "exact_plus_374_write_candidates": write_candidates,
            "write_mnemonic_counts": dict(sorted(mnemonic_counts.items())),
            "exact_plus_374_other_first_memory_operand_count": len(other_first_memory_forms),
            "exact_plus_374_other_first_memory_operands": other_first_memory_forms,
            "other_first_memory_mnemonic_counts": dict(sorted(other_mnemonic_counts.items())),
        },
        "adjudication": {
            "whole_image_exact_plus_374_write_mnemonic_candidate_inventory_complete": True,
            "whole_image_exact_plus_374_other_first_memory_operand_inventory_complete": True,
            "all_plus_374_candidate_receivers_classified": False,
            "unknown_or_unrelated_manager_root_alias_surface_complete": False,
            "global_helper_non_vtable_indirect_setter_surface_complete": False,
            "global_manager_root_origin_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This is a syntactic whole-image inventory of first memory operands with an exact +0x374 displacement and at least one 32-bit GPR base/index.",
            "Only an explicit write/RMW mnemonic allowlist is promoted to write candidates; every other first-memory-operand mnemonic is surfaced separately and remains fail-closed.",
            "A +0x374 displacement does not imply Participants Manager identity. Every positive candidate receiver must be machine-proven before it can affect manager+0x374 identity adjudication.",
            "Computed effective addresses that materialize +0x374 in a register before a zero-displacement store are outside this probe.",
        ],
        "next_step": "Run on authoritative PC retail 1.02 SHIFT.exe, classify every +0x374 write candidate receiver, then pursue only surviving manager-root-capable sites before the final manager+0x374 -> HDVehicle+0x4330 adjudication.",
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
