#!/usr/bin/env python3
"""Build a fail-closed render-manager receiver-transfer frontier using machine-read seeds.

Version 1 required a particular raw Ghidra p-code LOAD shape before seeding an
exact DAT_00bc185c READ. Retail evidence showed that requirement rejected all
95 exact READ xrefs even though the exported machine instructions are direct
IA-32 loads such as ``MOV ECX,dword ptr [0x00bc185c]``.

This version keeps the positive constructor/class identity prerequisite and the
same bounded local-CFG receiver trace, but defines the seed from three physical
facts that the existing evidence already records independently:

1. the current root-pose rank marks the instruction as an exact READ xref of
   DAT_00bc185c;
2. the exported machine instruction is exactly ``MOV tracked_reg,[global]``;
3. the finite all-path register engine yields one changed post-instruction
   memory origin naming that same global.

Structured p-code is still consumed by the v1 safe-transfer engine as a
fail-closed safety net for register writes. A particular raw LOAD/COPY lowering
is diagnostic only and is not required to prove the obvious IA-32 memory load.
Nothing here proves +0xca4 access, render-owner identity, VHF frame identity, or
BODY0 bind-frame closure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_player_vehicle_renderables_runtime_alias as _alias
import build_player_vehicle_render_manager_receiver_transfer_frontier as _v1

FORMAT = "SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2"
LEGACY_FORMAT = _v1.FORMAT
PROGRAM = _v1.PROGRAM
PE_MD5 = _v1.PE_MD5
CANDIDATE_GLOBAL = _v1.CANDIDATE_GLOBAL
DEFAULT_MAX_DIRECT_TARGETS = _v1.DEFAULT_MAX_DIRECT_TARGETS
_TRACKED = tuple(_v1._TRACKED)

_DIRECT_ABSOLUTE_MEMORY_RE = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword)\s+ptr\s+)?"
    r"\[\s*(?:(?:0x)?([0-9a-f]+)|dat_([0-9a-f]+))\s*\]\s*$",
    re.IGNORECASE,
)


def _direct_absolute_memory_address(operand: Any) -> int | None:
    if not isinstance(operand, str):
        return None
    match = _DIRECT_ABSOLUTE_MEMORY_RE.fullmatch(operand)
    if match is None:
        return None
    token = match.group(1) or match.group(2)
    if token is None:
        return None
    try:
        return int(token, 16)
    except ValueError:
        return None


def _seed_from_read(
    read: Mapping[str, Any],
    row: Mapping[str, Any],
    incoming_states: Mapping[str, Any],
    global_address: str,
) -> tuple[str, str, dict[str, frozenset[str]], dict[str, Any]] | None:
    function = _alias._addr(read.get("function"), field="read.function")
    address = _alias._addr(read.get("instruction"), field="read.instruction")
    instruction = _v1._instruction_map(row).get(address)
    if instruction is None:
        raise ValueError(f"{function}:{address}: exact rank READ instruction missing")

    before = incoming_states.get(address)
    if not isinstance(before, dict):
        raise ValueError(f"{function}:{address}: exact rank READ instruction unreachable")

    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if mnemonic != "MOV" or not isinstance(operands, list) or len(operands) < 2:
        return None
    if any(not isinstance(value, str) for value in operands):
        return None

    destination = _alias._register_engine._register(operands[0])
    if destination not in _TRACKED:
        return None
    source_address = _direct_absolute_memory_address(operands[1])
    if source_address is None or source_address != int(global_address, 16):
        return None

    after = _v1._safe_transfer(instruction, before)
    origins = _alias._register_engine._sorted_origins(after[destination])
    before_origins = _alias._register_engine._sorted_origins(before[destination])
    if len(origins) != 1 or origins == before_origins:
        return None
    if not _alias._origin_mentions_global(origins[0], global_address):
        return None

    # Preserve raw p-code information as diagnostics only. The machine-read
    # proof above remains sufficient even when Ghidra lowers the instruction to
    # a different raw p-code shape.
    pcode_outputs = _v1._pcode_load_register_outputs(instruction.get("pcode"), address)
    pcode_shape_matches_destination = destination in pcode_outputs

    marker = f"candidate-global-manager:{function}@{address}"
    seeded = dict(after)
    seeded[destination] = frozenset((marker,))
    return address, marker, seeded, {
        "function": function,
        "instruction": address,
        "instruction_text": instruction.get("text"),
        "destination_register": destination,
        "source_operand": operands[1],
        "global_origins_after_read": origins,
        "marker": marker,
        "exact_rank_global_read_xref": True,
        "exact_machine_MOV_absolute_global_load": True,
        "all_path_single_global_origin_after_read": True,
        "raw_pcode_load_shape_matches_destination": pcode_shape_matches_destination,
        "raw_pcode_load_shape_required_for_seed": False,
        "structured_pcode_write_safety_net": True,
    }


def build_frontier(
    constructor_identity_path: Path,
    rank_path: Path,
    instruction_export: Path,
    *,
    max_direct_targets: int = DEFAULT_MAX_DIRECT_TARGETS,
) -> dict[str, Any]:
    # Reuse the audited v1 validation, CFG trace, sink extraction and worklist
    # construction. Only the seed admission rule changes, and it is restored
    # immediately so importing both modules in one test process is deterministic.
    original_seed = _v1._seed_from_read
    _v1._seed_from_read = _seed_from_read
    try:
        report = _v1.build_frontier(
            constructor_identity_path,
            rank_path,
            instruction_export,
            max_direct_targets=max_direct_targets,
        )
    finally:
        _v1._seed_from_read = original_seed

    report["format"] = FORMAT
    report["version"] = 2
    skipped = report.get("analysis", {}).get("skipped_reads", [])
    for item in skipped:
        if isinstance(item, dict):
            item["reason"] = "read-does-not-yield-one-exact-machine-backed-tracked-register"

    scope = report.setdefault("scope", {})
    scope.update(
        {
            "seed_requires_exact_rank_READ_xref": True,
            "seed_requires_exact_machine_MOV_absolute_global_load": True,
            "seed_requires_all_path_single_global_origin": True,
            "seed_requires_raw_pcode_LOAD_shape": False,
            "raw_pcode_still_used_for_fail_closed_register_write_detection": True,
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("constructor_identity", type=Path)
    parser.add_argument("exhaustive_root_pose_rank", type=Path)
    parser.add_argument("exhaustive_instruction_export", type=Path)
    parser.add_argument("--max-direct-targets", type=int, default=DEFAULT_MAX_DIRECT_TARGETS)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_frontier(
            args.constructor_identity,
            args.exhaustive_root_pose_rank,
            args.exhaustive_instruction_export,
            max_direct_targets=args.max_direct_targets,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
