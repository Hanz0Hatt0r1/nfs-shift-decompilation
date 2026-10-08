#!/usr/bin/env python3
"""Extend the audited render-manager CFG trace with persistent memory-store sinks.

The existing SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2 follows
an exact DAT_00bc185c value through the local CFG and records call, dereference,
push, and return sinks.  This consumer reuses that exact seed/CFG machinery and
adds one deliberately narrow sink: ``MOV [memory], exact_manager_alias``.

It does not infer what the destination object means and it does not follow the
stored value into another function.  A non-empty store list is therefore a
worklist for exact destination/caller provenance, not a semantic alias proof.
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

import build_player_vehicle_render_manager_receiver_transfer_frontier_v2 as _v2

_v1 = _v2._v1
_alias = _v1._alias
_accesses = _v1._accesses

FORMAT = "SHIFT.PlayerVehicleRenderManagerMemoryEscapeSurface/1"
UPSTREAM_FORMAT = _v2.FORMAT

_ABSOLUTE_MEMORY_RE = re.compile(
    r"^\s*(?:(?:byte|word|dword|qword)\s+ptr\s+)?"
    r"\[\s*(?:(?:0x)?([0-9a-f]+)|dat_([0-9a-f]+))\s*\]\s*$",
    re.IGNORECASE,
)


def _destination_kind(operand: str) -> tuple[str, str | None, int | None]:
    parsed = _accesses._parse_memory_operand(operand)
    if parsed is not None:
        base, displacement = parsed
        if base in {"ESP", "EBP"}:
            return "stack-memory", base, displacement
        return "register-relative-memory", base, displacement
    match = _ABSOLUTE_MEMORY_RE.fullmatch(operand)
    if match is not None:
        token = match.group(1) or match.group(2)
        assert token is not None
        return "absolute-memory", None, int(token, 16)
    return "unparsed-memory", None, None


def _memory_store_sinks(
    function: str,
    marker: str,
    instruction: Mapping[str, Any],
    state: Mapping[str, frozenset[str]],
) -> list[dict[str, Any]]:
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if mnemonic != "MOV" or not isinstance(operands, list) or len(operands) != 2:
        return []
    if any(not isinstance(value, str) for value in operands):
        return []

    destination, source = operands
    if "[" not in destination or "]" not in destination:
        return []
    source_register = _alias._register_engine._register(source)
    if source_register not in state or not _v1._single_marker(state[source_register], marker):
        return []

    address = _alias._addr(instruction.get("address"), field="memory-store.instruction")
    destination_kind, base_register, displacement = _destination_kind(destination)
    return [
        {
            "kind": "manager-pointer-memory-store",
            "function": function,
            "instruction": address,
            "instruction_text": instruction.get("text"),
            "source_register": source_register,
            "destination_operand": destination,
            "destination_kind": destination_kind,
            "destination_base_register": base_register,
            "destination_displacement": displacement,
            "persistent_alias_identity_proven": False,
            "destination_owner_identity_proven": False,
        }
    ]


def build_surface(
    constructor_identity_path: Path,
    rank_path: Path,
    instruction_export: Path,
    *,
    max_direct_targets: int = _v2.DEFAULT_MAX_DIRECT_TARGETS,
) -> dict[str, Any]:
    original_other_sinks = _v1._other_sinks

    def patched_other_sinks(function, marker, instruction, state):
        return original_other_sinks(function, marker, instruction, state) + _memory_store_sinks(
            function, marker, instruction, state
        )

    _v1._other_sinks = patched_other_sinks
    try:
        upstream = _v2.build_frontier(
            constructor_identity_path,
            rank_path,
            instruction_export,
            max_direct_targets=max_direct_targets,
        )
    finally:
        _v1._other_sinks = original_other_sinks

    if upstream.get("format") != UPSTREAM_FORMAT:
        raise ValueError("unexpected upstream receiver-transfer format")
    if upstream.get("ready") is not True:
        raise ValueError("upstream receiver-transfer frontier is not ready")

    analysis = upstream.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("upstream analysis missing")
    stores = [
        dict(item)
        for item in analysis.get("all_sinks") or []
        if isinstance(item, Mapping) and item.get("kind") == "manager-pointer-memory-store"
    ]
    stores.sort(
        key=lambda item: (
            int(str(item.get("function") or "0x0"), 16),
            int(str(item.get("instruction") or "0x0"), 16),
            str(item.get("destination_operand") or ""),
        )
    )

    counts: dict[str, int] = {}
    for item in stores:
        kind = str(item.get("destination_kind") or "unknown")
        counts[kind] = counts.get(kind, 0) + 1

    provenance = upstream.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("upstream provenance missing")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "upstream": {
            "format": UPSTREAM_FORMAT,
            "seedable_pointer_load_count": provenance.get("seedable_pointer_load_count"),
            "reference_read_count": provenance.get("reference_read_count"),
            "selected_function_count": provenance.get("selected_function_count"),
        },
        "scope": {
            "exact_global": _v2.CANDIDATE_GLOBAL,
            "all_path_local_cfg_tracking": True,
            "memory_store_shape": "MOV [memory], exact_manager_alias",
            "follows_stored_alias_after_store": False,
            "destination_semantics_inferred": False,
        },
        "analysis": {
            "memory_store_count": len(stores),
            "destination_kind_counts": counts,
            "memory_stores": stores,
        },
        "handoff": {
            "exact_manager_memory_store_surface_inventory_ready": True,
            "exact_manager_memory_store_surface_closed_negative": len(stores) == 0,
            "cross_function_persistent_alias_identity_ready": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "A listed store is only a persistent-alias candidate until destination ownership and later loads are proven.",
            "The pass does not follow stored aliases across function boundaries.",
            "Derived interface/subobject pointers are not promoted back to the exact outer root.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("constructor_identity", type=Path)
    parser.add_argument("exhaustive_root_pose_rank", type=Path)
    parser.add_argument("exhaustive_instruction_export", type=Path)
    parser.add_argument("--max-direct-targets", type=int, default=_v2.DEFAULT_MAX_DIRECT_TARGETS)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_surface(
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
