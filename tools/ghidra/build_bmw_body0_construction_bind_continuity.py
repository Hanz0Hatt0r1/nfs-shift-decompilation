#!/usr/bin/env python3
"""Prove the static SDF BODY pose -> persistent BODY construction continuity.

This pass closes the construction-side semantic gap left by Phase 424.  The
retail loader/body-builder chain is now source- and machine-audited strongly
enough to name the formerly opaque BODY descriptor groups:

* descriptor +0x00/+0x08/+0x10 = SDF BODY ``pos``;
* descriptor +0x18/+0x20/+0x28 = SDF BODY ``rot``;
* descriptor +0x108/+0x110/+0x118 = SDF BODY ``ori``;
* FUN_007b3670 copies ``pos`` to persistent BODY origin +0x00/+0x08/+0x10;
* FUN_007bbb10 forwards ``ori`` to FUN_007b00a0, which writes the persistent
  BODY basis +0xd4..+0xf4.

The pass deliberately does not equate the SDF model construction frame with the
renderer/VHF vehicle-root frame.  Consequently it cannot by itself produce
SHIFT.BMWBody0BindFrameProof/1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[1]
_PHYSICS_DIR = _REPO_ROOT / "src" / "physics"
if str(_PHYSICS_DIR) not in sys.path:
    sys.path.insert(0, str(_PHYSICS_DIR))

import rigid_body_sdf_runtime as _sdf

FORMAT = "SHIFT.BMWBody0ConstructionBindContinuity/1"
INTAKE_FORMAT = "SHIFT.BMWM3PhysicsIntakeEvidence/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
BODY_INDEX = 0
BODY_NAME = "body"

TARGETS = {
    "0x007b6900": {
        "name": "FUN_007b6900",
        "mnemonic_sha256": "154593816d7647c6cd8a0ee37b96e92c38cd78b318bd16cdbfcefb7bca3aba81",
        "role": "SDF BODY loader",
    },
    "0x007b3670": {
        "name": "FUN_007b3670",
        "mnemonic_sha256": "bcf42f221ca37b7ee8f907b0783fc8da894ecc3528e86506f6d58e448a0953d3",
        "role": "persistent BODY builder",
    },
    "0x007bbb10": {
        "name": "FUN_007bbb10",
        "mnemonic_sha256": "345f993d42c3338af314e48791796449516286b95ccdc40a7d188590fc091238",
        "role": "BODY orientation descriptor copy",
    },
    "0x007b00a0": {
        "name": "FUN_007b00a0",
        "mnemonic_sha256": "1571bec085d38a85854dba34ab5e2f92d890ddbb4ea9e51c8d55e110d8e41d54",
        "role": "BODY orientation -> 3x3 basis builder",
    },
}

REQUIRED_DIRECT_EDGES = (
    ("0x007b6900", "0x007b6e8f", "0x007b3670"),
    ("0x007b3670", "0x007b37c8", "0x007bbb10"),
    ("0x007bbb10", "0x007bbb3a", "0x007b00a0"),
    ("0x007b00a0", "0x007b00b5", "0x00900c40"),
    ("0x007b00a0", "0x007b00c6", "0x00900b10"),
    ("0x007b00a0", "0x007b00dd", "0x00900c40"),
    ("0x007b00a0", "0x007b00ee", "0x00900b10"),
    ("0x007b00a0", "0x007b0105", "0x00900c40"),
    ("0x007b00a0", "0x007b0116", "0x00900b10"),
)

DESCRIPTOR_LAYOUT = {
    "pos": [0x00, 0x08, 0x10],
    "rot": [0x18, 0x20, 0x28],
    "vel": [0x78, 0x80, 0x88],
    "name": [0x100],
    "ori": [0x108, 0x110, 0x118],
    "mass": [0x120],
    "inertia": [0x128, 0x12C, 0x130],
}
RUNTIME_LAYOUT = {
    "origin": [0x00, 0x08, 0x10],
    "orientation_cache": [0x108, 0x110, 0x118],
    "basis": [0xD4, 0xD8, 0xDC, 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4],
}
EXPECTED_BMW_BODIES = [
    "body",
    "fl_spindle",
    "fr_spindle",
    "fl_wheel",
    "fr_wheel",
    "rl_spindle",
    "rr_spindle",
    "rl_wheel",
    "rr_wheel",
    "fuel_tank",
    "driver_head",
]


def _load_json(path: Path, expected_format: str | None = None) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    if expected_format is not None and value.get("format") != expected_format:
        raise ValueError(f"{path}: expected {expected_format}")
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
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _address(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field}: invalid address {value!r}")
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError as exc:
        raise ValueError(f"{field}: invalid address {value!r}") from exc


def _hex_list(values: Sequence[int]) -> list[str]:
    return [f"+0x{value:x}" for value in values]


def _validate_retail_export(root: Path) -> dict[str, Any]:
    binary = _load_json(root / "binary.json")
    if binary.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected Ghidra program: {binary.get('program_name')!r}")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable MD5")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(root / "functions.jsonl"):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address not in TARGETS:
            continue
        if address in found:
            raise ValueError(f"duplicate function row {address}")
        found[address] = row

    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))
    for address, expected in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("mnemonic_sha256") != expected["mnemonic_sha256"]:
            raise ValueError(f"{address}: mnemonic fingerprint drift")

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(root / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        raw_from = row.get("from_function")
        raw_instruction = row.get("instruction")
        raw_to = row.get("to")
        if not all(isinstance(value, str) for value in (raw_from, raw_instruction, raw_to)):
            continue
        edges.add(
            (
                _address(raw_from, field="callgraph.from_function"),
                _address(raw_instruction, field="callgraph.instruction"),
                _address(raw_to, field="callgraph.to"),
            )
        )
    missing_edges = [edge for edge in REQUIRED_DIRECT_EDGES if edge not in edges]
    if missing_edges:
        text = ", ".join(f"{a}:{i}->{b}" for a, i, b in missing_edges)
        raise ValueError("missing required direct call edge(s): " + text)

    return {
        "program_name": PROGRAM,
        "executable_md5": PE_MD5,
        "functions": [
            {
                "address": address,
                "name": TARGETS[address]["name"],
                "role": TARGETS[address]["role"],
                "mnemonic_sha256": TARGETS[address]["mnemonic_sha256"],
            }
            for address in TARGETS
        ],
        "required_direct_edges": [
            {"from": source, "instruction": instruction, "to": target}
            for source, instruction, target in REQUIRED_DIRECT_EDGES
        ],
    }


def _validate_intake(path: Path) -> dict[str, Any]:
    report = _load_json(path, INTAKE_FORMAT)
    archive = report.get("archive") or {}
    sdf_entry = report.get("sdf_entry") or {}
    structure = report.get("structure") or {}
    bodies = report.get("bodies")
    if archive.get("filename") != "BMW_M3_E36.bff":
        raise ValueError("BMW archive identity drift")
    if archive.get("sha256") != "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70":
        raise ValueError("BMW archive SHA-256 drift")
    if sdf_entry.get("path") != "vehicles/physics/suspension/aarm_multilink.sdf":
        raise ValueError("BMW SDF path drift")
    if structure.get("body_count") != len(EXPECTED_BMW_BODIES):
        raise ValueError("BMW BODY count drift")
    if bodies != EXPECTED_BMW_BODIES:
        raise ValueError("BMW BODY order/name drift")
    digest = sdf_entry.get("decoded_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("BMW SDF decoded SHA-256 missing")
    return report


def _values(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(entry.get("name")): entry.get("value")
        for entry in record.get("entries") or []
    }


def _finite3(value: Any, label: str) -> list[float]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise ValueError(f"{label}: expected exactly three scalars")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{label}: non-numeric scalar")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label}: non-finite scalar")
        result.append(number)
    return result


def _zero3(value: Sequence[float]) -> bool:
    # This is an exact resource-value gate, not an epsilon comparison.  The
    # identity basis shortcut is legal only for literal numeric zero inputs.
    return all(number == 0.0 for number in value)


def _identity_pose_row(pos: Sequence[float]) -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        float(pos[0]), float(pos[1]), float(pos[2]), 1.0,
    ]


def _inspect_optional_sdf(path: Path, intake: Mapping[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected_digest = str((intake.get("sdf_entry") or {}).get("decoded_sha256") or "")
    if digest != expected_digest:
        raise ValueError("decoded BMW SDF SHA-256 mismatch")

    parsed = _sdf.parse_sdf(raw, strict=True)
    if parsed.get("ready") is not True:
        raise ValueError("decoded BMW SDF did not parse cleanly")
    bodies = _sdf.records_by_type(parsed, "BODY")
    if len(bodies) != len(EXPECTED_BMW_BODIES):
        raise ValueError("decoded BMW SDF BODY count drift")
    names = [str(_values(record).get("name") or "") for record in bodies]
    if names != EXPECTED_BMW_BODIES:
        raise ValueError("decoded BMW SDF BODY order/name drift")

    body0_values = _values(bodies[BODY_INDEX])
    pos = _finite3(body0_values.get("pos"), "BODY0 pos")
    ori = _finite3(body0_values.get("ori"), "BODY0 ori")
    result: dict[str, Any] = {
        "available": True,
        "path": str(path),
        "sha256": digest,
        "body_index": BODY_INDEX,
        "body_name": BODY_NAME,
        "pos": pos,
        "ori": ori,
        "ori_is_exact_zero": _zero3(ori),
        "basis_ready": False,
        "basis": None,
        "body0_local_to_sdf_model_row_matrix_ready": False,
        "body0_local_to_sdf_model_row_matrix": None,
    }
    if _zero3(ori):
        result["basis_ready"] = True
        result["basis"] = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        result["body0_local_to_sdf_model_row_matrix_ready"] = True
        result["body0_local_to_sdf_model_row_matrix"] = _identity_pose_row(pos)
    return result


def build_bmw_body0_construction_bind_continuity(
    ghidra_export: Path,
    intake_path: Path,
    sdf_path: Path | None = None,
) -> dict[str, Any]:
    retail = _validate_retail_export(ghidra_export)
    intake = _validate_intake(intake_path)

    source_static_proof = {
        "evidence_state": "proven-static",
        "source_basis": "audited SHIFT.exe.c decompilation plus raw IA-32, anchored to exact retail function fingerprints and callsites",
        "descriptor_layout": {key: _hex_list(value) for key, value in DESCRIPTOR_LAYOUT.items()},
        "runtime_layout": {key: _hex_list(value) for key, value in RUNTIME_LAYOUT.items()},
        "continuity": [
            {
                "source_field": "BODY.pos",
                "descriptor_offsets": _hex_list(DESCRIPTOR_LAYOUT["pos"]),
                "runtime_field": "persistent_BODY.origin",
                "runtime_offsets": _hex_list(RUNTIME_LAYOUT["origin"]),
                "producer": "FUN_007b6900",
                "consumer": "FUN_007b3670",
                "machine_witness": "FUN_007b3670 qword copies at 0x007b3797..0x007b37b1",
            },
            {
                "source_field": "BODY.ori",
                "descriptor_offsets": _hex_list(DESCRIPTOR_LAYOUT["ori"]),
                "runtime_field": "persistent_BODY.basis",
                "runtime_offsets": _hex_list(RUNTIME_LAYOUT["basis"]),
                "producer": "FUN_007b6900",
                "copy_helper": "FUN_007bbb10",
                "basis_builder": "FUN_007b00a0",
                "machine_witness": "0x007bbb21 pushes BODY.ori pointer while ECX=BODY+0xd4 before 0x007bbb3a -> FUN_007b00a0",
            },
        ],
        "phase424_group_resolution": {
            "group_a": "BODY.ori",
            "group_b": "BODY.rot",
        },
        "basis_builder": {
            "function": "FUN_007b00a0",
            "input": "three f64 BODY.ori scalars at +0x00/+0x08/+0x10 of the supplied vector",
            "output": "nine f32 basis scalars at BODY +0xd4..+0xf4",
            "trig_helpers": {
                "0x00900c40": "x87 fsin",
                "0x00900b10": "x87 fcos",
            },
            "zero_orientation_identity_exact": True,
        },
    }

    resource: dict[str, Any] = {
        "available": False,
        "expected_path": (intake.get("sdf_entry") or {}).get("path"),
        "expected_sha256": (intake.get("sdf_entry") or {}).get("decoded_sha256"),
        "body_index": BODY_INDEX,
        "body_name": BODY_NAME,
        "pos": None,
        "ori": None,
        "basis_ready": False,
        "basis": None,
        "body0_local_to_sdf_model_row_matrix_ready": False,
        "body0_local_to_sdf_model_row_matrix": None,
    }
    if sdf_path is not None:
        resource = _inspect_optional_sdf(sdf_path, intake)

    blockers: list[dict[str, Any]] = []
    if not resource["available"]:
        blockers.append(
            {
                "id": "exact-BMW-BODY0-pos-ori-values-unavailable",
                "status": "blocked",
                "required_evidence": (
                    "supply/recover the exact decoded aarm_multilink.sdf matching the already recorded Phase 404 SHA-256; "
                    "no new runtime capture is required"
                ),
            }
        )
    elif not resource["basis_ready"]:
        blockers.append(
            {
                "id": "nonzero-BODY0-ori-retail-basis-evaluation-not-materialized",
                "status": "blocked",
                "required_evidence": (
                    "materialize the exact FUN_007b00a0 basis result for the observed nonzero BODY0 ori; "
                    "do not substitute an unvalidated host transcendental implementation"
                ),
            }
        )

    blockers.append(
        {
            "id": "SDF-model-to-VHF-vehicle-root-frame-relation-unproven",
            "status": "unknown",
            "required_evidence": (
                "prove the static frame relation between the SDF model construction frame and the VHF vehicle-root/assembly frame; "
                "do not assume equality from naming or zero BODY0 pose alone"
            ),
        }
    )

    local_pose_ready = bool(resource["body0_local_to_sdf_model_row_matrix_ready"])
    return {
        "format": FORMAT,
        "version": 1,
        "status": "static-continuity-proven",
        "ready": True,
        "retail_identity": retail,
        "bmw_intake": {
            "archive": intake.get("archive"),
            "sdf_entry": intake.get("sdf_entry"),
            "body_count": (intake.get("structure") or {}).get("body_count"),
            "body_index": BODY_INDEX,
            "body_name": BODY_NAME,
        },
        "source_static_proof": source_static_proof,
        "resource_BODY0": resource,
        "handoff": {
            "BODY_descriptor_pos_ori_semantics_ready": True,
            "construction_origin_continuity_ready": True,
            "construction_basis_continuity_ready": True,
            "BODY0_resource_pos_ori_values_ready": bool(resource["available"]),
            "BODY0_local_to_SDF_model_bind_pose_ready": local_pose_ready,
            "SDF_model_to_VHF_vehicle_root_frame_relation_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "identity_matrix_assumed": False,
            "SDF_model_frame_assumed_equal_VHF_vehicle_root": False,
            "construction_bind_continuity_proven": True,
            "final_BODY0_to_VHF_bind_relation_proven": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the BMW BODY0 SDF-pos/ori -> persistent origin/basis static continuity proof"
    )
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("bmw_intake", type=Path)
    parser.add_argument("--sdf", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = build_bmw_body0_construction_bind_continuity(
        args.ghidra_export,
        args.bmw_intake,
        args.sdf,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
