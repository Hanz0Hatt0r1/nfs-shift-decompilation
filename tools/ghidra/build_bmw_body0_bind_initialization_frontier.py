#!/usr/bin/env python3
"""Build an exact static worklist for the BMW BODY0 bind-initialization proof.

This layer does not infer that any pose writer is the bind initializer.  It uses
only direct Ghidra callgraph edges and exact retail anchors to answer a narrower
question: which functions/callsites can connect the SDF BODY construction lane
to the verified broad BODY pose-writer candidate FUN_007b7840?

The output is a finite targeted instruction worklist for the next value-provenance
stage.  Callgraph reachability remains discovery evidence, never semantic proof.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BMWBody0BindInitializationFrontier/1"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
PROGRAM = "SHIFT.exe"

SDF_LOADER = "0x007b6900"
BODY_BUILDER = "0x007b3670"
POSE_WRITER_CANDIDATE = "0x007b7840"
ANCHORS = {
    "sdf_loader": SDF_LOADER,
    "body_builder": BODY_BUILDER,
    "pose_writer_candidate": POSE_WRITER_CANDIDATE,
}


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _address(value: Any, *, field: str) -> str:
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


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def _instruction_key(row: dict[str, Any]) -> tuple[int, str]:
    value = row.get("instruction")
    if isinstance(value, str):
        try:
            return int(value, 0), value
        except ValueError:
            pass
    return (1 << 63), str(value or "")


def _load_binary(root: Path) -> dict[str, Any]:
    path = root / "binary.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    if value.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected program: {value.get('program_name')!r}")
    if value.get("executable_md5") != PE_MD5:
        raise ValueError(
            f"unexpected executable MD5: expected {PE_MD5}, got {value.get('executable_md5')!r}"
        )
    return value


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address in result:
            raise ValueError(f"{path}: duplicate function {address}")
        result[address] = row
    missing = [address for address in ANCHORS.values() if address not in result]
    if missing:
        raise ValueError("required function(s) absent from export: " + ", ".join(missing))
    return result


def _load_callgraph(root: Path):
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    malformed: list[dict[str, Any]] = []
    for line_no, row in enumerate(_read_jsonl(path), 1):
        if row.get("indirect") is not False:
            continue
        source_raw = row.get("from_function")
        target_raw = row.get("to")
        instruction_raw = row.get("instruction")
        if not all(isinstance(value, str) and value for value in (source_raw, target_raw, instruction_raw)):
            malformed.append({"line": line_no, "reason": "direct edge missing source/target/instruction"})
            continue
        try:
            source = _address(source_raw, field="callgraph.from_function")
            target = _address(target_raw, field="callgraph.to")
            instruction = _address(instruction_raw, field="callgraph.instruction")
        except ValueError as exc:
            malformed.append({"line": line_no, "reason": str(exc)})
            continue
        normalized = dict(row)
        normalized["from_function"] = source
        normalized["to"] = target
        normalized["instruction"] = instruction
        outgoing[source].append(normalized)
        incoming[target].append(normalized)

    for rows in outgoing.values():
        rows.sort(key=_instruction_key)
    for rows in incoming.values():
        rows.sort(key=lambda row: (row["from_function"], *_instruction_key(row)))
    return outgoing, incoming, malformed


def _shortest_directed_path(
    start: str,
    goal: str,
    outgoing: dict[str, list[dict[str, Any]]],
    *,
    max_depth: int,
) -> list[dict[str, Any]] | None:
    if start == goal:
        return []
    queue = deque([(start, [])])
    best_depth: dict[str, int] = {start: 0}
    while queue:
        current, path = queue.popleft()
        depth = len(path)
        if depth >= max_depth:
            continue
        for edge in outgoing.get(current, []):
            target = str(edge["to"])
            next_path = path + [edge]
            if target == goal:
                return next_path
            next_depth = len(next_path)
            previous = best_depth.get(target)
            if previous is not None and previous <= next_depth:
                continue
            best_depth[target] = next_depth
            queue.append((target, next_path))
    return None


def _path_record(path: list[dict[str, Any]] | None) -> dict[str, Any]:
    if path is None:
        return {"reachable": False, "depth": None, "edges": [], "function_path": []}
    if not path:
        return {"reachable": True, "depth": 0, "edges": [], "function_path": []}
    functions = [str(path[0]["from_function"])] + [str(edge["to"]) for edge in path]
    return {
        "reachable": True,
        "depth": len(path),
        "edges": [_edge(edge) for edge in path],
        "function_path": functions,
    }


def _function_record(address: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": address,
        "name": row.get("name"),
        "calling_convention": row.get("calling_convention"),
        "signature": row.get("signature"),
        "size": row.get("size"),
        "external": row.get("external"),
        "thunk": row.get("thunk"),
    }


def build_bmw_body0_bind_initialization_frontier(
    root: Path,
    *,
    max_depth: int = 8,
) -> dict[str, Any]:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    binary = _load_binary(root)
    functions = _load_functions(root)
    outgoing, incoming, malformed = _load_callgraph(root)

    direct_callers = incoming.get(POSE_WRITER_CANDIDATE, [])
    builder_to_writer = _shortest_directed_path(
        BODY_BUILDER,
        POSE_WRITER_CANDIDATE,
        outgoing,
        max_depth=max_depth,
    )
    loader_to_builder = _shortest_directed_path(
        SDF_LOADER,
        BODY_BUILDER,
        outgoing,
        max_depth=max_depth,
    )
    loader_to_writer = _shortest_directed_path(
        SDF_LOADER,
        POSE_WRITER_CANDIDATE,
        outgoing,
        max_depth=max_depth,
    )

    caller_rows: list[dict[str, Any]] = []
    target_functions = {SDF_LOADER, BODY_BUILDER, POSE_WRITER_CANDIDATE}
    target_callsites: set[str] = set()
    for edge in direct_callers:
        caller = str(edge["from_function"])
        target_functions.add(caller)
        target_callsites.add(str(edge["instruction"]))
        path_from_builder = _shortest_directed_path(
            BODY_BUILDER, caller, outgoing, max_depth=max_depth
        )
        path_from_loader = _shortest_directed_path(
            SDF_LOADER, caller, outgoing, max_depth=max_depth
        )
        caller_rows.append(
            {
                "caller": caller,
                "caller_name": edge.get("from_name"),
                "callsite": str(edge["instruction"]),
                "edge": _edge(edge),
                "from_BODY_builder": _path_record(path_from_builder),
                "from_SDF_loader": _path_record(path_from_loader),
                "candidate_class": (
                    "builder-reachable-pose-writer-caller"
                    if path_from_builder is not None
                    else "loader-reachable-pose-writer-caller"
                    if path_from_loader is not None
                    else "unjoined-direct-pose-writer-caller"
                ),
                "bind_initializer_semantics_proven": False,
                "BODY0_pointer_proven": False,
                "origin_basis_value_provenance_proven": False,
            }
        )

    caller_rows.sort(
        key=lambda row: (
            0 if row["candidate_class"] == "builder-reachable-pose-writer-caller" else 1
            if row["candidate_class"] == "loader-reachable-pose-writer-caller" else 2,
            row["from_BODY_builder"]["depth"]
            if isinstance(row["from_BODY_builder"]["depth"], int)
            else 1 << 30,
            int(row["caller"], 0),
            int(row["callsite"], 0),
        )
    )

    for path in (builder_to_writer, loader_to_builder, loader_to_writer):
        if path:
            for edge in path:
                target_functions.add(str(edge["from_function"]))
                target_functions.add(str(edge["to"]))
                target_callsites.add(str(edge["instruction"]))

    target_rows = []
    for address in sorted(target_functions, key=lambda value: int(value, 0)):
        row = functions.get(address)
        if row is None:
            # A direct-call endpoint can be external or absent from functions.jsonl.
            # Keep it visible but do not silently advertise it as exportable.
            target_rows.append(
                {
                    "address": address,
                    "name": None,
                    "exportable": False,
                    "reason": "function metadata absent",
                }
            )
            continue
        exportable = row.get("external") is not True and row.get("thunk") is not True
        target_rows.append(
            {
                "address": address,
                "name": row.get("name"),
                "exportable": exportable,
                "reason": "targeted instruction/p-code proof" if exportable else "external-or-thunk",
            }
        )

    instruction_targets = [row["address"] for row in target_rows if row["exportable"]]
    blockers: list[dict[str, Any]] = [
        {
            "id": "BODY0-bind-origin-basis-value-provenance-unproven",
            "evidence_state": "unknown",
            "required_evidence": (
                "prove exact BODY index 0 pointer/value continuity from SDF construction or another "
                "source-backed initialization lane into persistent BODY origin+basis"
            ),
        },
        {
            "id": "pose-writer-candidate-bind-role-unproven",
            "evidence_state": "candidate",
            "target": POSE_WRITER_CANDIDATE,
            "required_evidence": (
                "for every relevant direct caller, prove or reject bind-initialization role from "
                "instruction-level pointer/value provenance and ordering"
            ),
        },
    ]
    if not direct_callers:
        blockers.append(
            {
                "id": "pose-writer-direct-caller-set-empty",
                "evidence_state": "blocked",
                "required_evidence": "resolve references/indirect dispatch or prove the saved export is incomplete",
            }
        )

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": {
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "pointer_size": binary.get("pointer_size"),
        },
        "anchors": {
            name: _function_record(address, functions[address])
            for name, address in ANCHORS.items()
        },
        "directed_reachability": {
            "SDF_loader_to_BODY_builder": _path_record(loader_to_builder),
            "BODY_builder_to_pose_writer_candidate": _path_record(builder_to_writer),
            "SDF_loader_to_pose_writer_candidate": _path_record(loader_to_writer),
            "max_depth": max_depth,
            "semantic_meaning": "discovery-only",
        },
        "pose_writer_candidate": {
            "function": POSE_WRITER_CANDIDATE,
            "direct_caller_count": len(direct_callers),
            "direct_callers": caller_rows,
            "verified_capability": "can write BODY origin+basis/motion/cross-vector under flags",
            "bind_initializer_semantics_proven": False,
        },
        "targeted_proof_worklist": {
            "function_count": len(instruction_targets),
            "function_targets": instruction_targets,
            "function_records": target_rows,
            "callsite_count": len(target_callsites),
            "callsites": sorted(target_callsites, key=lambda value: int(value, 0)),
            "next_stage": (
                "export SHIFT.GhidraFunctionInstructions/2 for exportable targets; trace BODY0 pointer, "
                "origin/basis values and call ordering; emit SHIFT.BMWBody0BindFrameProof/1 only "
                "after exact static continuity is proven"
            ),
        },
        "blockers": blockers,
        "malformed_direct_callgraph_rows": malformed,
        "scope": {
            "direct_call_edges_only": True,
            "callgraph_reachability_is_semantic_proof": False,
            "SDF_pos_ori_promoted_to_runtime_pose": False,
            "pose_writer_candidate_promoted_to_initializer": False,
            "BODY0_pointer_identity_proven": False,
            "BODY0_bind_matrix_proven": False,
            "matching_offsets_used_as_identity": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--callsites-out", type=Path)
    args = parser.parse_args()

    report = build_bmw_body0_bind_initialization_frontier(
        args.ghidra_export,
        max_depth=args.max_depth,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        values = report["targeted_proof_worklist"]["function_targets"]
        args.targets_out.write_text("".join(f"{value}\n" for value in values), encoding="utf-8")
    if args.callsites_out:
        args.callsites_out.parent.mkdir(parents=True, exist_ok=True)
        values = report["targeted_proof_worklist"]["callsites"]
        args.callsites_out.write_text("".join(f"{value}\n" for value in values), encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"pose-writer direct callers: {report['pose_writer_candidate']['direct_caller_count']}")
    print(f"instruction targets: {report['targeted_proof_worklist']['function_count']}")
    print(f"callsites: {report['targeted_proof_worklist']['callsite_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
