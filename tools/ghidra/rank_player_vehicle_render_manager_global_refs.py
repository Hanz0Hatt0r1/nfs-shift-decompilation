#!/usr/bin/env python3
"""Rank candidate render-manager global xrefs against proven vehicle/render anchors.

This is the finite bridge after SHIFT.GhidraGlobalReferences/1 was introduced for
DAT_00bc185c.  It does not infer manager identity from callgraph proximity.  It
only turns a potentially large exact xref set into a bounded instruction-export
worklist by measuring directed callgraph distance to already-proven Process 1
vehicle/car-body/visual anchors and the mPlayerVehicleRenderables constructor
anchor.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import validate_global_reference_export as _global_refs

FORMAT = "SHIFT.PlayerVehicleRenderManagerGlobalXrefRank/1"
DB_FORMAT = "SHIFT.GhidraEvidenceDatabase/1"
GLOBAL_FORMAT = "SHIFT.GhidraGlobalReferences/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
DEFAULT_GLOBAL = "0x00bc185c"
DEFAULT_LIMIT = 24
DEFAULT_MAX_DEPTH = 8

ANCHORS = {
    "render_manager_constructor": {
        "address": "0x0045ef50",
        "mnemonic_sha256": "6644a22ad5bd2c20d96f40b8f1e7d5193afdd8e9d40a60bf216814e2f43f60aa",
        "domain": "render-manager+mPlayerVehicleRenderables-field",
    },
    "HDVehicle_Init": {
        "address": "0x0076df50",
        "mnemonic_sha256": "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda",
        "domain": "HDVehicle",
    },
    "HDVehicle_control": {
        "address": "0x007633b0",
        "mnemonic_sha256": "34643530b03a2868818cec0b31ed9f0f03ca146df2c1e915e846b88033aaebfe",
        "domain": "HDVehicle-control",
    },
    "car_body_CHASSIS_init": {
        "address": "0x007ac4d0",
        "mnemonic_sha256": "912218c717ebba3ab6185f1ca2758a3a7233a49b7d336939e162bcb3964bc525",
        "domain": "car-body/CHASSIS",
    },
    "vehicle_visual_LOD_setup": {
        "address": "0x007a3d60",
        "mnemonic_sha256": "689d88dc93c57813b682d5b8b7147f99032457307d3b2dab1d21adb1c61e8f45",
        "domain": "vehicle-visual/LOD",
    },
}
VEHICLE_ANCHOR_NAMES = tuple(name for name in ANCHORS if name != "render_manager_constructor")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
            rows.append(value)
    return rows


def _addr(value: Any) -> str:
    return _global_refs.normalize_address(str(value))


def _load_global_export(path: Path, expected_global: str) -> dict[str, Any]:
    expected = _addr(expected_global)
    _global_refs.validate(path, [expected])
    rows = _read_jsonl(path)
    if len(rows) != 1:
        raise ValueError("global-reference export must contain exactly one row")
    row = rows[0]
    if row.get("format") != GLOBAL_FORMAT:
        raise ValueError(f"expected {GLOBAL_FORMAT}")
    if row.get("program") != PROGRAM:
        raise ValueError("global-reference export program identity drift")
    if str(row.get("executable_md5") or "").lower() != PE_MD5:
        raise ValueError("global-reference export executable MD5 drift")
    if _addr(row.get("resolved_address")) != expected:
        raise ValueError("global-reference export resolved-address drift")
    return row


def _load_database(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]], dict[str, set[str]]]:
    binary = _read_json(root / "binary.json")
    if (
        binary.get("format") != DB_FORMAT
        or binary.get("program_name") != PROGRAM
        or str(binary.get("executable_md5") or "").lower() != PE_MD5
    ):
        raise ValueError("retail Ghidra database identity drift")

    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if isinstance(raw, str):
            functions[raw.lower()] = row

    for name, anchor in ANCHORS.items():
        address = anchor["address"]
        row = functions.get(address)
        if row is None:
            raise ValueError(f"missing anchor function {name} {address}")
        if row.get("mnemonic_sha256") != anchor["mnemonic_sha256"]:
            raise ValueError(f"anchor mnemonic drift: {name} {address}")
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"anchor is not a concrete retail function: {name} {address}")

    forward: dict[str, set[str]] = {}
    reverse: dict[str, set[str]] = {}
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True or row.get("to") is None:
            continue
        source_raw = row.get("from_function")
        target_raw = row.get("to")
        if not isinstance(source_raw, str) or not isinstance(target_raw, str):
            continue
        source = source_raw.lower()
        target = target_raw.lower()
        forward.setdefault(source, set()).add(target)
        reverse.setdefault(target, set()).add(source)
    return functions, forward, reverse


def _distance(graph: dict[str, set[str]], start: str, target: str, max_depth: int) -> int | None:
    if start == target:
        return 0
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    seen = {start}
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for nxt in graph.get(node, ()):
            if nxt == target:
                return depth + 1
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append((nxt, depth + 1))
    return None


def _function_reference_sites(global_row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for ref in global_row.get("references") or []:
        if not isinstance(ref, dict) or ref.get("function_address") is None:
            continue
        function = _addr(ref["function_address"])
        grouped.setdefault(function, []).append(
            {
                "from": _addr(ref.get("from")),
                "type": ref.get("type"),
                "operand_index": ref.get("operand_index"),
                "primary": ref.get("primary"),
                "instruction": ref.get("instruction"),
            }
        )
    return grouped


def _anchor_distances(
    function: str,
    forward: dict[str, set[str]],
    reverse: dict[str, set[str]],
    max_depth: int,
) -> dict[str, dict[str, int | None]]:
    result: dict[str, dict[str, int | None]] = {}
    for name, anchor in ANCHORS.items():
        target = anchor["address"]
        result[name] = {
            "forward": _distance(forward, function, target, max_depth),
            "reverse": _distance(reverse, function, target, max_depth),
        }
    return result


def _minimum_vehicle_distance(distances: dict[str, dict[str, int | None]]) -> tuple[int | None, str | None, str | None]:
    candidates: list[tuple[int, str, str]] = []
    for name in VEHICLE_ANCHOR_NAMES:
        for direction in ("forward", "reverse"):
            value = distances[name][direction]
            if value is not None:
                candidates.append((value, name, direction))
    if not candidates:
        return None, None, None
    return min(candidates, key=lambda item: (item[0], item[1], item[2]))


def rank(
    ghidra_export: Path,
    global_export: Path,
    *,
    expected_global: str = DEFAULT_GLOBAL,
    limit: int = DEFAULT_LIMIT,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> dict[str, Any]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if max_depth <= 0:
        raise ValueError("max_depth must be positive")

    global_row = _load_global_export(global_export, expected_global)
    functions, forward, reverse = _load_database(ghidra_export)
    grouped = _function_reference_sites(global_row)
    if not grouped:
        raise ValueError("candidate global has no references inside functions")

    ranked: list[dict[str, Any]] = []
    for function, references in grouped.items():
        metadata = functions.get(function)
        if metadata is None:
            raise ValueError(f"global-ref containing function missing from functions.jsonl: {function}")
        distances = _anchor_distances(function, forward, reverse, max_depth)
        minimum, nearest_anchor, nearest_direction = _minimum_vehicle_distance(distances)
        connected_vehicle_anchors = sorted(
            name
            for name in VEHICLE_ANCHOR_NAMES
            if distances[name]["forward"] is not None or distances[name]["reverse"] is not None
        )
        render_distance_values = [
            value
            for value in distances["render_manager_constructor"].values()
            if value is not None
        ]
        render_distance = min(render_distance_values) if render_distance_values else None
        ranked.append(
            {
                "function": function,
                "function_name": metadata.get("name"),
                "reference_count": len(references),
                "reference_sites": references,
                "anchor_distances": distances,
                "minimum_vehicle_anchor_distance": minimum,
                "nearest_vehicle_anchor": nearest_anchor,
                "nearest_vehicle_anchor_direction": nearest_direction,
                "connected_vehicle_anchor_count": len(connected_vehicle_anchors),
                "connected_vehicle_anchors": connected_vehicle_anchors,
                "minimum_render_manager_constructor_distance": render_distance,
                "callgraph_proximity_is_owner_identity_proof": False,
            }
        )

    ranked.sort(
        key=lambda row: (
            row["minimum_vehicle_anchor_distance"] is None,
            row["minimum_vehicle_anchor_distance"] if row["minimum_vehicle_anchor_distance"] is not None else 10**9,
            -int(row["connected_vehicle_anchor_count"]),
            row["minimum_render_manager_constructor_distance"] is None,
            row["minimum_render_manager_constructor_distance"] if row["minimum_render_manager_constructor_distance"] is not None else 10**9,
            -int(row["reference_count"]),
            int(str(row["function"]), 16),
        )
    )

    selected = ranked[: min(limit, len(ranked))]
    selected_functions = [str(row["function"]) for row in selected]
    connected_selected = [
        row for row in selected if row["minimum_vehicle_anchor_distance"] is not None
    ]

    blockers = [
        {
            "id": "candidate-render-manager-global-instance-identity-unproven",
            "required_evidence": "inspect ranked global-reference functions; proximity to anchors is discovery evidence only",
        },
        {
            "id": "player-vehicle-renderables-field-runtime-access-unproven",
            "required_evidence": "targeted instruction export must prove a concrete access to render-manager +0xca4 in the selected runtime-user set",
        },
        {
            "id": "player-renderable-owner-to-car-body-visual-owner-join-unproven",
            "required_evidence": "join one selected render-manager user to the proven HDVehicle/car-body/visual owner chain by physical pointer/value flow",
        },
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ranked-global-xref-worklist-ready",
        "ready": True,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {
            "address": _addr(global_row.get("resolved_address")),
            "primary_symbol": global_row.get("primary_symbol"),
            "reference_count": global_row.get("reference_count"),
            "function_reference_count": len(grouped),
            "runtime_manager_instance_identity_proven": False,
        },
        "anchors": {
            name: {
                "address": data["address"],
                "domain": data["domain"],
                "identity": "source/static-anchor",
            }
            for name, data in ANCHORS.items()
        },
        "ranking": {
            "max_callgraph_depth": max_depth,
            "ranked_function_count": len(ranked),
            "functions": ranked,
            "selected_instruction_export_limit": limit,
            "selected_instruction_export_functions": selected_functions,
            "selected_with_vehicle_anchor_connection": len(connected_selected),
        },
        "handoff": {
            "candidate_global_exact_xrefs_ranked": True,
            "bounded_instruction_export_worklist_ready": True,
            "player_vehicle_renderables_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "runtime_capture_required": False,
            "indirect_call_edges_used_for_ranking": False,
            "callgraph_proximity_promoted_to_pointer_identity": False,
            "candidate_global_promoted_to_render_manager_instance": False,
            "constructor_plus_0xca4_promoted_to_runtime_access": False,
            "VHF_frame_identity_claimed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("global_reference_export", type=Path)
    parser.add_argument("--global-address", default=DEFAULT_GLOBAL)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = rank(
        args.ghidra_export,
        args.global_reference_export,
        expected_global=args.global_address,
        limit=args.limit,
        max_depth=args.max_depth,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
