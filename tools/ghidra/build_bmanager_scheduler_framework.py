#!/usr/bin/env python3
"""Prove the retail BManager scheduler framework without promoting cadence.

This analyzer records two positive static facts:
1. the BManager subsystem exposes explicit Auto/Manual update, desired/average
   frequency and delta diagnostics in retail SHIFT.exe;
2. the source-backed cPhysicsManager constructor reaches a BManager-tick-labeled
   routine through the recovered base-constructor/static-init chain.

Neither fact proves the runtime dispatcher that invokes cPhysicsManager vtable
slot +0x18, nor the elapsed/accumulator input reaching FUN_00713050. Those
claims remain deliberately closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BManagerSchedulerFramework/1"
BINARY_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
MANAGER_FORMAT = "SHIFT.PhysicsManagerRuntime/1"

PHYSICS_MANAGER_CTOR = 0x0070FAE0
BMANAGER_BASE_CTOR = 0x00647A10
BMANAGER_STATIC_INIT = 0x0065BF80
BMANAGER_TICK = 0x0065BD70
BMANAGER_STATUS = 0x0065B430
ATEXIT = 0x00900FB3

EXPECTED_FUNCTIONS: dict[int, tuple[str, str]] = {
    PHYSICS_MANAGER_CTOR: (
        "FUN_0070fae0",
        "24c183bd4ed6f53a7f44ecf6c7b3403a812310fecff8049ae6b0faa92dc30bfc",
    ),
    BMANAGER_BASE_CTOR: (
        "FUN_00647a10",
        "02623d464525cc356f76666acacbefbe1d55c404516f4cf2aff80b077cdfa4dd",
    ),
    BMANAGER_STATIC_INIT: (
        "FUN_0065bf80",
        "07f419bf72d7295ba073b55e824e3cf31d940956d68d523947b53fd964774450",
    ),
    BMANAGER_TICK: (
        "FUN_0065bd70",
        "53ac6e78ad78956e0e66a64a66246c1d18319e379ecba592438ed01f43de45a8",
    ),
    BMANAGER_STATUS: (
        "FUN_0065b430",
        "1333c50e294bacce0ef4616997162176235900395005594aa5cef7fec926d59a",
    ),
}

EXPECTED_ASSOCIATION_EDGES = (
    (PHYSICS_MANAGER_CTOR, BMANAGER_BASE_CTOR, 0x0070FB03),
    (BMANAGER_BASE_CTOR, BMANAGER_STATIC_INIT, 0x00647B07),
    (BMANAGER_STATIC_INIT, BMANAGER_TICK, 0x0065BF98),
    (BMANAGER_STATIC_INIT, ATEXIT, 0x0065BFA2),
)

EXPECTED_TICK_OUTGOING = (
    (0x0065BD85, 0x0067CBC0),
    (0x0065BDA5, 0x0067CBC0),
    (0x0065BDC6, 0x0040CB40),
    (0x0065BDD3, 0x0067CBC0),
    (0x0065BE12, 0x0067CBC0),
    (0x0065BE48, 0x00669B00),
    (0x0065BE53, 0x0064F500),
    (0x0065BE71, 0x008F3DF0),
    (0x0065BE76, 0x00657D90),
    (0x0065BE81, 0x00657D70),
    (0x0065BE86, 0x00657D90),
    (0x0065BE91, 0x00657D70),
    (0x0065BE96, 0x00657D90),
    (0x0065BEA1, 0x00657D70),
    (0x0065BEB2, 0x004F5E10),
    (0x0065BEC3, 0x004F5E10),
    (0x0065BED4, 0x0046F7E0),
    (0x0065BEE7, 0x0064F570),
)

EXPECTED_STRINGS = (
    (0x00AEFC50, ", Delta( %d ms )", 0x0065B516, BMANAGER_STATUS),
    (0x00AEFC64, ", Manual Sync, Avg. Freq = %2.2f Hz", 0x0065B4DB, BMANAGER_STATUS),
    (0x00AEFC88, ", Desired Freq = %2.2f Hz, Avg. Freq = %2.2f Hz", 0x0065B4C2, BMANAGER_STATUS),
    (0x00AEFCB8, "Manual Update", 0x0065B496, BMANAGER_STATUS),
    (0x00AEFCC8, "Auto Update", 0x0065B48F, BMANAGER_STATUS),
    (0x00AEFCFC, "BManager Tick", 0x0065BEDC, BMANAGER_TICK),
    (0x00AEFD0C, "_BManagerSys Critical", 0x0065BE64, BMANAGER_TICK),
)


def _norm(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    try:
        return int(token, 16)
    except ValueError:
        return None


def _hex(value: int) -> str:
    return f"0x{value:08x}"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected JSON object")
        rows.append(value)
    return rows


def _validate_binary(binary: dict[str, Any]) -> dict[str, Any]:
    if binary.get("format") != BINARY_FORMAT:
        raise ValueError(f"retail binary export must be {BINARY_FORMAT}")
    if binary.get("program_name") != "SHIFT.exe":
        raise ValueError("retail binary export program_name drift")
    md5 = str(binary.get("executable_md5") or "").lower()
    if md5 != PE_MD5:
        raise ValueError(f"retail PE MD5 drift: expected {PE_MD5}, got {md5 or '<missing>'}")
    return {"format": BINARY_FORMAT, "program_name": "SHIFT.exe", "executable_md5": md5, "verified": True}


def _validate_runtime_contract(source: str) -> dict[str, Any]:
    required = (
        f'MANAGER_FORMAT = "{MANAGER_FORMAT}"',
        'MANAGER_VTABLE = "PTR_FUN_00b04524"',
        "Source/Manager/cPhysicsManager.hpp",
        '"functions": ["FUN_0070fae0", "FUN_0070f580"]',
        '"named_object": "Physics Manager"',
    )
    missing = [token for token in required if token not in source]
    if missing:
        raise ValueError("Physics Manager runtime contract drift: " + ", ".join(missing))
    return {"format": MANAGER_FORMAT, "constructor": "FUN_0070fae0", "verified": True}


def _function_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        address = _norm(row.get("address"))
        if address is not None:
            result[address] = row
    return result


def _validate_functions(functions: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for address, (name, digest) in EXPECTED_FUNCTIONS.items():
        row = functions.get(address)
        if row is None:
            raise ValueError(f"required BManager frontier function missing: {_hex(address)}")
        if row.get("name") != name:
            raise ValueError(f"BManager frontier function name drift at {_hex(address)}")
        if row.get("mnemonic_sha256") != digest:
            raise ValueError(f"BManager frontier function hash drift at {_hex(address)}")
        result.append({"address": _hex(address), "name": name, "mnemonic_sha256": digest, "verified": True})
    return result


def _edge_rows(callgraph: list[dict[str, Any]], source: int, target: int) -> list[dict[str, Any]]:
    return [
        row for row in callgraph
        if _norm(row.get("from_function")) == source
        and _norm(row.get("to")) == target
        and row.get("indirect") is False
    ]


def _validate_association_edges(callgraph: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source, target, instruction in EXPECTED_ASSOCIATION_EDGES:
        rows = _edge_rows(callgraph, source, target)
        calls = sorted(v for v in (_norm(row.get("instruction")) for row in rows) if v is not None)
        if calls != [instruction]:
            raise ValueError(
                f"BManager association edge {_hex(source)} -> {_hex(target)} drift: "
                f"expected {_hex(instruction)}, got {[ _hex(v) for v in calls ]}"
            )
        result.append({"from": _hex(source), "to": _hex(target), "instruction": _hex(instruction), "verified": True})
    return result


def _validate_tick_shape(callgraph: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in callgraph if _norm(row.get("from_function")) == BMANAGER_TICK]
    indirect = [row for row in rows if row.get("indirect") is True]
    if indirect:
        raise ValueError("BManager Tick acquired indirect outgoing calls; dispatch frontier requires re-audit")
    observed = sorted(
        (_norm(row.get("instruction")), _norm(row.get("to")))
        for row in rows
        if row.get("indirect") is False
    )
    if any(instruction is None or target is None for instruction, target in observed):
        raise ValueError("BManager Tick direct outgoing call has unresolved address")
    expected = sorted(EXPECTED_TICK_OUTGOING)
    if observed != expected:
        raise ValueError(
            "BManager Tick direct outgoing shape drift: expected "
            f"{[(_hex(i), _hex(t)) for i, t in expected]}, got "
            f"{[(_hex(i), _hex(t)) for i, t in observed]}"
        )
    return {
        "function": _hex(BMANAGER_TICK),
        "outgoing_call_count": len(observed),
        "indirect_outgoing_call_count": 0,
        "all_observed_outgoing_calls_direct": True,
        "verified": True,
    }


def _validate_strings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for address, value, xref, function in EXPECTED_STRINGS:
        matches = [row for row in rows if _norm(row.get("address")) == address]
        if len(matches) != 1:
            raise ValueError(f"BManager string {_hex(address)} expected once; found {len(matches)}")
        row = matches[0]
        if row.get("value") != value:
            raise ValueError(f"BManager string value drift at {_hex(address)}")
        xrefs = {_norm(item) for item in row.get("xrefs", [])}
        functions = {_norm(item) for item in row.get("functions", [])}
        if xref not in xrefs or function not in functions:
            raise ValueError(f"BManager string xref/function drift at {_hex(address)}")
        result.append({"address": _hex(address), "value": value, "xref": _hex(xref), "function": _hex(function), "verified": True})
    return result


def build_framework(
    binary_path: Path,
    functions_path: Path,
    callgraph_path: Path,
    strings_xrefs_path: Path,
    physics_runtime_path: Path,
) -> dict[str, Any]:
    binary = _validate_binary(_read_json(binary_path))
    functions = _function_index(_read_jsonl(functions_path))
    callgraph = _read_jsonl(callgraph_path)
    strings = _read_jsonl(strings_xrefs_path)
    runtime = _validate_runtime_contract(physics_runtime_path.read_text(encoding="utf-8"))

    fingerprints = _validate_functions(functions)
    association_edges = _validate_association_edges(callgraph)
    tick_shape = _validate_tick_shape(callgraph)
    string_evidence = _validate_strings(strings)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked-runtime-dispatch-proof",
        "ready": False,
        "binary_identity": binary,
        "physics_manager_contract": runtime,
        "function_fingerprints": fingerprints,
        "cadence_policy_evidence": {
            "status_function": _hex(BMANAGER_STATUS),
            "auto_manual_update_strings_observed": True,
            "desired_average_frequency_strings_observed": True,
            "delta_ms_string_observed": True,
            "strings": string_evidence,
            "retail_cadence_value_proven": False,
        },
        "bmanager_tick_anchor": tick_shape,
        "physics_manager_bmanager_association": {
            "verified": True,
            "path": [
                _hex(PHYSICS_MANAGER_CTOR),
                _hex(BMANAGER_BASE_CTOR),
                _hex(BMANAGER_STATIC_INIT),
                _hex(BMANAGER_TICK),
            ],
            "edges": association_edges,
            "constructor_reaches_bmanager_tick_labeled_routine": True,
            "inheritance_claimed": False,
            "per_frame_dispatch_claimed": False,
        },
        "runtime_dispatch": {
            "bmanager_tick_to_physics_manager_vtable_plus_0x18_proven": False,
            "physics_manager_receiver_alias_proven": False,
            "physics_manager_entry_invocation_cadence_proven": False,
        },
        "cadence": {
            "retail_cadence_admitted": False,
            "host_1_60_is_retail_evidence": False,
            "rendered_frame_equivalence_proven": False,
            "elapsed_or_accumulator_producer_proven": False,
        },
        "blocking_reasons": [
            "bmanager-runtime-dispatch-to-physics-manager-vtable-plus-0x18-not-proven",
            "physics-manager-scheduler-entry-elapsed-or-accumulator-input-not-proven",
        ],
        "next_static_targets": {
            "functions": [
                "0x0065b750",
                "0x00662600",
                "0x00648200",
                "0x006485b0",
                "0x0065b430",
                "0x00647460",
            ],
            "question": (
                "prove the BManager controller iteration/registration edge that dispatches "
                "cPhysicsManager vtable +0x18, then trace the timer/rate value feeding that dispatch"
            ),
        },
        "limits": {
            "bmanager_tick_string_promoted_to_virtual_dispatch": False,
            "constructor_association_promoted_to_inheritance": False,
            "diagnostic_frequency_strings_promoted_to_runtime_cadence": False,
            "host_pacing_promoted": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("functions", type=Path)
    parser.add_argument("callgraph", type=Path)
    parser.add_argument("strings_xrefs", type=Path)
    parser.add_argument("physics_runtime", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_framework(
        args.binary,
        args.functions,
        args.callgraph,
        args.strings_xrefs,
        args.physics_runtime,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
