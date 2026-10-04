#!/usr/bin/env python3
"""Freeze the retail BODY0-local -> outer Vehicle-root symbolic bind relation.

This pass proves a symbolic affine relation only. It anchors the relevant
retail functions/calls to the exact SHIFT.exe Ghidra export, then records the
source-audited semantics visible in SHIFT.exe.c:

* Vehicle transform forwarding reaches HDVehicle with the same position/Euler;
* HDVehicle targets BODY0 at P_vehicle - R_vehicle * offset33b;
* the reverse wheel/export path maps BODY0-local points to vehicle-root points
  by subtracting the same offset33b;
* therefore BODY0-local -> outer Vehicle-root has identity rotation and
  translation -offset33b at bind/assembly time.

The numeric BMW offset is deliberately not invented, and outer Vehicle-root is
not equated with the VHF hierarchy root. Consequently this contract is not a
SHIFT.BMWBody0BindFrameProof/1 producer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BMWBody0VehicleRootBindRelation/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

TARGETS = {
    "0x00747b90": ("FUN_00747b90", 36, "__fastcall", "fda8fcb2b4d9c692033d047f34517b0b63f7f13bbcc9d63f59b57d3f6719b2cd", "three-double vector subtraction"),
    "0x0075bbd0": ("FUN_0075bbd0", 255, "__thiscall", "1535aa3e485c32d31b215ed14c49dc988cdf2b42ed0537d4b3794adeab08e8c3", "BODY0-local -> vehicle-root reverse projection"),
    "0x007615c0": ("FUN_007615c0", 792, "__thiscall", "0b2268dceb26dfaff8814b4091e50d48371b74083ac6d41e3d50da99cc036a22", "SDF chassis BODY selection"),
    "0x007633b0": ("FUN_007633b0", 319, "__thiscall", "34643530b03a2868818cec0b31ed9f0f03ca146df2c1e915e846b88033aaebfe", "HDVehicle chassis transform setter"),
    "0x0076b280": ("FUN_0076b280", 7796, "__thiscall", "9563b40c06bcc7442aabd3308eefa62e1b9f7d0bb9afe752ddf0dc068e0cd7f6", "offset33b producer"),
    "0x0076df50": ("FUN_0076df50", 1548, "__thiscall", "73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda", "HDVehicle initialization bridge"),
    "0x007927c0": ("FUN_007927c0", 340, "__thiscall", "32b16c7d280c26335f9244b4cc7f8269995e4d2608724f8b0e5c4c0c41a75561", "outer Vehicle transform setter"),
    "0x007b5ac0": ("FUN_007b5ac0", 993, "__thiscall", "a12aa30b38d26372e09c263d7eec1f4147e46b8e7c4245e7a8af808990d12df2", "connected pmodel BODY pose setter"),
}

REQUIRED_DIRECT_EDGES = (
    ("0x007927c0", "0x007928e3", "0x007633b0"),
    ("0x007633b0", "0x0076344f", "0x00747b90"),
    ("0x007633b0", "0x00763479", "0x007b5ac0"),
    ("0x0076df50", "0x0076e238", "0x007615c0"),
    ("0x0076df50", "0x0076e270", "0x0076b280"),
)

OFFSET_FIELDS = ["HDVehicle+0x33b0", "HDVehicle+0x33b8", "HDVehicle+0x33c0"]
BODY_POINTER_FIELD = "HDVehicle+0x33a0"
GLOBAL_HDVEHICLE = "0x00c13700"
GLOBAL_BODY_POINTER = "0x00c16aa0"
GLOBAL_OFFSET_X = "0x00c16ab0"


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
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(value)
    return rows


def _addr(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected address string")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def validate_export(root: Path) -> dict[str, Any]:
    binary = _read_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError("unexpected Ghidra program")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable MD5")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _addr(raw, "functions.address")
        if address in TARGETS:
            if address in found:
                raise ValueError(f"duplicate function row {address}")
            found[address] = row

    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))

    functions: list[dict[str, Any]] = []
    for address, (name, size, calling_convention, fingerprint, role) in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("name") != name:
            raise ValueError(f"{address}: function name drift")
        if row.get("size") != size:
            raise ValueError(f"{address}: function size drift")
        if row.get("calling_convention") != calling_convention:
            raise ValueError(f"{address}: calling convention drift")
        if row.get("mnemonic_sha256") != fingerprint:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
        functions.append({
            "address": address,
            "name": name,
            "size": size,
            "calling_convention": calling_convention,
            "mnemonic_sha256": fingerprint,
            "role": role,
        })

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        a, i, b = row.get("from_function"), row.get("instruction"), row.get("to")
        if not all(isinstance(x, str) for x in (a, i, b)):
            continue
        edges.add((_addr(a, "callgraph.from_function"), _addr(i, "callgraph.instruction"), _addr(b, "callgraph.to")))
    missing_edges = [edge for edge in REQUIRED_DIRECT_EDGES if edge not in edges]
    if missing_edges:
        raise ValueError("missing required direct call edge(s): " + ", ".join(f"{a}:{i}->{b}" for a, i, b in missing_edges))

    return {
        "program_name": PROGRAM,
        "executable_md5": PE_MD5,
        "functions": functions,
        "required_direct_edges": [
            {"from": a, "instruction": i, "to": b} for a, i, b in REQUIRED_DIRECT_EDGES
        ],
    }


def build_bmw_body0_vehicle_root_bind_relation(ghidra_export: Path) -> dict[str, Any]:
    retail = validate_export(ghidra_export)
    return {
        "format": FORMAT,
        "status": "symbolic-ready",
        "ready": True,
        "retail": retail,
        "source_audit": {
            "evidence_state": "source-backed-decompiler",
            "scope": "audited SHIFT.exe.c semantics anchored to exact retail function fingerprints/callsites; not an instruction-level semantic proof",
            "facts": [
                "FUN_007927c0 forwards the same outer Vehicle position/Euler to FUN_007633b0",
                "FUN_007633b0 computes target_BODY0_origin = vehicle_position - R(vehicle_orientation) * offset33b",
                "FUN_007633b0 passes the same vehicle orientation to FUN_007b5ac0 for BODY0/pmodel pose",
                "FUN_0075bbd0 converts a world point to BODY0-local and subtracts offset33b to produce vehicle-root-local output",
                "FUN_0076b280 is the initialization producer for offset33b after SDF load",
            ],
        },
        "identity_aliases": {
            "global_HDVehicle": GLOBAL_HDVEHICLE,
            "chassis_BODY_pointer_field": BODY_POINTER_FIELD,
            "chassis_BODY_pointer_absolute": GLOBAL_BODY_POINTER,
            "offset33b_x_field": OFFSET_FIELDS[0],
            "offset33b_x_absolute": GLOBAL_OFFSET_X,
            "absolute_alias_equations": [
                "0x00c13700 + 0x33a0 = 0x00c16aa0",
                "0x00c13700 + 0x33b0 = 0x00c16ab0",
            ],
        },
        "symbolic_bind_relation": {
            "from_frame": "BODY0-local",
            "to_frame": "outer-Vehicle-root",
            "rotation": "identity",
            "translation": ["-HDVehicle[0x33b0]", "-HDVehicle[0x33b8]", "-HDVehicle[0x33c0]"],
            "row_vector_matrix": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                "-HDVehicle[0x33b0]", "-HDVehicle[0x33b8]", "-HDVehicle[0x33c0]", 1,
            ],
            "spawn_equation": "O_BODY0_world = P_vehicle_world - R_vehicle * offset33b",
            "reverse_equation": "q_vehicle_root = q_BODY0_local - offset33b",
        },
        "gates": {
            "retail_vehicle_transform_to_HDVehicle_spawn_bridge_ready": True,
            "BODY0_to_outer_vehicle_root_rotation_identity_ready": True,
            "BODY0_to_outer_vehicle_root_translation_symbolic_ready": True,
            "BODY0_to_outer_vehicle_root_symbolic_matrix_ready": True,
            "BMW_numeric_offset33b_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "remaining_blockers": [
            {
                "id": "bmw-offset33b-numeric-value",
                "required": "exact BMW HDVehicle+0x33b0/+0x33b8/+0x33c0 after FUN_0076b280, or a source-equivalent reproduction from exact BMW init inputs",
            },
            {
                "id": "outer-vehicle-root-to-vhf-root-join",
                "required": "retail static/source-backed consumer join proving outer Vehicle root is the VHF hierarchy vehicle-root frame (or proving the exact affine delta)",
            },
        ],
        "scope": {
            "numeric_offset_assumed": False,
            "identity_translation_assumed": False,
            "outer_vehicle_root_equated_to_VHF_root": False,
            "new_runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ghidra-export", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_bmw_body0_vehicle_root_bind_relation(args.ghidra_export)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
