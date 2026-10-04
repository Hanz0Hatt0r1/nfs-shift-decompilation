#!/usr/bin/env python3
"""Prove the resolved direct-call role of FUN_007b7840 for BMW BODY0 bind work.

This proof deliberately answers one narrow question: do any *resolved direct*
non-recursive calls to the broad BODY pose writer belong to the SDF/body
construction lane, or are they all descendants of the already source/machine-
backed FUN_00770e80 half-step relation-refresh path?

It does not infer semantics from callgraph adjacency alone.  The outer-update
anchor is accepted only through SHIFT.BodyFrameIntegrationStatic/1, while exact
retail function fingerprints and direct callsites are revalidated from the saved
Ghidra export.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

_ROOT = Path(__file__).resolve().parents[2]
_PHYSICS = _ROOT / "src" / "physics"
if str(_PHYSICS) not in sys.path:
    sys.path.insert(0, str(_PHYSICS))

import body_frame_integration_static as _body_static

FORMAT = "SHIFT.BMWBody0BindPoseWriterDirectRole/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

OUTER_UPDATE = "0x00770e80"
RELATION_REFRESH = "0x007b8810"
SYSTEM_LOCATION_RECOVERY = "0x007b8630"
POSE_WRITER_WRAPPER = "0x007b8260"
POSE_WRITER = "0x007b7840"
SDF_LOADER = "0x007b6900"
BODY_BUILDER = "0x007b3670"

CONSTRUCTION_HELPERS = ("0x007bba90", "0x007bbb10", "0x007bbb60")

FINGERPRINTS = {
    OUTER_UPDATE: "509d932c8a3c397f69fe91acecadef2bc148a05237a947c226d9ff039860514e",
    RELATION_REFRESH: "7203aad37b4b6394f3c344b8e55dff95b2776d355f05a6d1bdbdab387c21350c",
    SYSTEM_LOCATION_RECOVERY: "64bccd697f0cd15af9e5b46c752700d4958a3ba1709259db1a9df98d21ba816f",
    POSE_WRITER_WRAPPER: "876fc10148a37e84e2768a7c138d3c996d46c3db6fb7e3faa958667c0b17948d",
    POSE_WRITER: "4e9ca2cb352a7fb97d26271ee3a41b62527eb5824ae161a7cdd75d423eb215b0",
    SDF_LOADER: "154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81",
    BODY_BUILDER: "bcf42f221ca37b7ee8f907b0783fc8da894ecc3528e86506f6d58e448a0953d3",
    "0x007bba90": "ade565ab3fa59f77ca0ec62392629eaec5642920ea64d5b7e1760d849fb0e587",
    "0x007bbb10": "345f993d42c3338af314e48791796449516286b95ccdc40a7d188590fc091238",
    "0x007bbb60": "113211b1c93c307c1bac779494a1a6420ceb8d691dfe6d8c0987af615f3752c4",
}

EXPECTED_INCOMING = {
    POSE_WRITER: {
        (POSE_WRITER, "0x007b7d75"),
        (POSE_WRITER_WRAPPER, "0x007b82f4"),
    },
    POSE_WRITER_WRAPPER: {(SYSTEM_LOCATION_RECOVERY, "0x007b8729")},
    SYSTEM_LOCATION_RECOVERY: {(RELATION_REFRESH, "0x007b8816")},
    RELATION_REFRESH: {
        (OUTER_UPDATE, "0x00770fb7"),
        (OUTER_UPDATE, "0x00770fe7"),
    },
}

EXPECTED_CONSTRUCTION_EDGES = {
    (SDF_LOADER, BODY_BUILDER, "0x007b6e8f"),
    (BODY_BUILDER, "0x007bba90", "0x007b3792"),
    (BODY_BUILDER, "0x007bbb10", "0x007b37c8"),
    (BODY_BUILDER, "0x007bbb60", "0x007b380b"),
}


def _addr(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field}: missing address")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield value


def _load_binary(root: Path) -> dict[str, Any]:
    path = root / "binary.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    if value.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected program: {value.get('program_name')!r}")
    if value.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")
    return value


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _addr(raw, field="functions.address")
        if address in rows:
            raise ValueError(f"{path}: duplicate function {address}")
        rows[address] = row

    for address, expected_hash in FINGERPRINTS.items():
        row = rows.get(address)
        if row is None:
            raise ValueError(f"missing required function {address}")
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("mnemonic_sha256") != expected_hash:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
    return rows


def _load_direct_callgraph(root: Path) -> tuple[dict[str, list[dict[str, Any]]], set[tuple[str, str, str]]]:
    path = root / "callgraph.jsonl"
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exact_edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        source = row.get("from_function")
        target = row.get("to")
        instruction = row.get("instruction")
        if not all(isinstance(value, str) and value for value in (source, target, instruction)):
            continue
        source_n = _addr(source, field="callgraph.from_function")
        target_n = _addr(target, field="callgraph.to")
        instruction_n = _addr(instruction, field="callgraph.instruction")
        normalized = dict(row)
        normalized.update(
            from_function=source_n,
            to=target_n,
            instruction=instruction_n,
        )
        incoming[target_n].append(normalized)
        exact_edges.add((source_n, target_n, instruction_n))
    return incoming, exact_edges


def _incoming_pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(str(row["from_function"]), str(row["instruction"])) for row in rows}


def _validate_outer_schedule_contract() -> dict[str, Any]:
    contract = _body_static.build_contract()
    _body_static.validate_contract(contract)
    source = contract.get("source")
    if not isinstance(source, dict) or source.get("executable_md5") != PE_MD5:
        raise ValueError("BODY frame integration contract retail identity drift")
    closed = contract.get("closed_boundaries")
    if not isinstance(closed, dict) or closed.get("two_half_step_order_inside_FUN_00770e80") is not True:
        raise ValueError("BODY frame integration outer-update ordering is not proven")
    schedule = contract.get("outer_schedule", {}).get("FUN_00770e80")
    if not isinstance(schedule, dict):
        raise ValueError("BODY frame integration outer schedule missing")
    if schedule.get("relation_refresh_1") != "0x00770fb7 -> FUN_007b8810":
        raise ValueError("first relation-refresh source witness drift")
    if schedule.get("relation_refresh_2") != "0x00770fe7 -> FUN_007b8810":
        raise ValueError("second relation-refresh source witness drift")
    return contract


def prove_bmw_body0_bind_pose_writer_direct_role(root: Path) -> dict[str, Any]:
    binary = _load_binary(root)
    functions = _load_functions(root)
    incoming, exact_edges = _load_direct_callgraph(root)
    source_contract = _validate_outer_schedule_contract()

    for target, expected in EXPECTED_INCOMING.items():
        actual = _incoming_pairs(incoming.get(target, []))
        if actual != expected:
            raise ValueError(
                f"{target}: exact direct incoming set drift: expected {sorted(expected)}, got {sorted(actual)}"
            )

    missing_construction = sorted(EXPECTED_CONSTRUCTION_EDGES - exact_edges)
    if missing_construction:
        raise ValueError(f"construction anchor edge(s) missing: {missing_construction}")

    external_pose_calls = sorted(
        [row for row in incoming[POSE_WRITER] if row["from_function"] != POSE_WRITER],
        key=lambda row: int(row["instruction"], 0),
    )
    if len(external_pose_calls) != 1:
        raise ValueError("expected exactly one resolved direct non-recursive pose-writer call")

    chain = [
        {
            "from": OUTER_UPDATE,
            "callsite": "0x00770fb7 or 0x00770fe7",
            "to": RELATION_REFRESH,
            "semantic_basis": "SHIFT.BodyFrameIntegrationStatic/1 source/machine-backed relation refresh after each half-step",
        },
        {"from": RELATION_REFRESH, "callsite": "0x007b8816", "to": SYSTEM_LOCATION_RECOVERY},
        {"from": SYSTEM_LOCATION_RECOVERY, "callsite": "0x007b8729", "to": POSE_WRITER_WRAPPER},
        {"from": POSE_WRITER_WRAPPER, "callsite": "0x007b82f4", "to": POSE_WRITER},
    ]

    construction_targets = [BODY_BUILDER, *CONSTRUCTION_HELPERS]
    return {
        "format": FORMAT,
        "source": {
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "ghidra_export": str(root),
            "semantic_anchor_format": source_contract.get("format"),
            "semantic_anchor_decompile_sha256": source_contract.get("source", {}).get("decompile_sha256"),
        },
        "pose_writer": {
            "address": POSE_WRITER,
            "mnemonic_sha256": functions[POSE_WRITER].get("mnemonic_sha256"),
            "resolved_direct_call_count": len(incoming[POSE_WRITER]),
            "resolved_direct_recursive_calls": [
                {"caller": POSE_WRITER, "callsite": "0x007b7d75"}
            ],
            "resolved_direct_nonrecursive_calls": [
                {
                    "caller": external_pose_calls[0]["from_function"],
                    "callsite": external_pose_calls[0]["instruction"],
                }
            ],
        },
        "outer_update_direct_chain": chain,
        "construction_lane": {
            "loader_to_builder": {
                "caller": SDF_LOADER,
                "callsite": "0x007b6e8f",
                "target": BODY_BUILDER,
            },
            "builder_direct_helpers": [
                {"target": "0x007bba90", "callsite": "0x007b3792"},
                {"target": "0x007bbb10", "callsite": "0x007b37c8"},
                {"target": "0x007bbb60", "callsite": "0x007b380b"},
            ],
            "next_target_functions": construction_targets,
        },
        "proof": {
            "all_resolved_direct_nonrecursive_pose_writer_calls_are_outer_update_descendants": True,
            "resolved_direct_construction_call_to_pose_writer_exists": False,
            "FUN_007b7840_direct_construction_bind_initializer_role": "rejected",
            "FUN_007b7840_any_possible_bind_role": "unknown",
            "indirect_or_address_taken_invocations_absence_proven": False,
        },
        "handoff": {
            "continue_FUN_007b7840_resolved_direct_bind_value_provenance": False,
            "follow_BODY_construction_writer_now": True,
            "next_static_targets": construction_targets,
            "required_next_proof": (
                "trace FUN_007b3670 and its exact direct initialization helpers to the persistent 0x170 BODY target; "
                "prove BODY0 pointer identity plus origin/basis source values on the construction lane"
            ),
            "BODY0_pointer_at_bind_callsite_ready": False,
            "BODY0_bind_origin_basis_values_ready": False,
            "BODY0_bind_frame_proof_ready": False,
        },
        "remaining_unknowns": [
            "whether FUN_007b7840 has an unresolved indirect/address-taken bind invocation",
            "which FUN_007b3670/helper writes establish the BODY0 bind origin/basis",
            "exact BODY0 bind matrix",
        ],
        "scope": {
            "callgraph_adjacency_used_as_semantic_proof": False,
            "outer_update_semantics_source_machine_backed": True,
            "resolved_direct_callsets_required_exact": True,
            "pose_writer_any_bind_role_disproven": False,
            "BODY0_bind_matrix_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "native_runtime_changed": False,
            "renderer_changed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = prove_bmw_body0_bind_pose_writer_direct_role(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
