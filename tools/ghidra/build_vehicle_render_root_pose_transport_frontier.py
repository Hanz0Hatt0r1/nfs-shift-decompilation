#!/usr/bin/env python3
"""Freeze the finite SMS vehicle root-pose transport frontier.

This stage complements the outer-Vehicle/car-body visual frontier with an
independent SMS/GraphicsEngine-side path.  It proves only exact retail function
identity and direct-call topology.  Receiver-relative offsets observed in the
current decompiler output are emitted as non-gating hypotheses for the next
instruction-level proof; they are deliberately not promoted to frame identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleRenderRootPoseTransportFrontier/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"

TARGETS: dict[str, dict[str, Any]] = {
    "0x0070db00": {
        "name": "FUN_0070db00", "size": 61, "calling_convention": "__thiscall",
        "mnemonic_sha256": "a94a57a6bd66e069657d30c0bac22fffbd1b541949a53633a07c31ea8e986455",
        "role": "vehicle-slot double-buffer snapshot reader",
    },
    "0x00481e20": {
        "name": "FUN_00481e20", "size": 5913, "calling_convention": "__thiscall",
        "mnemonic_sha256": "37a722e4d69ffa88ae44b3b22d251fda6064674d8654da3506a3a298a3bb8c7d",
        "role": "extended vehicle-state snapshot copy",
    },
    "0x0047fa40": {
        "name": "FUN_0047fa40", "size": 325, "calling_convention": "__thiscall",
        "mnemonic_sha256": "667f0fad50ce7f1035d3d6b9cb5adcb78387577d1c855bce660170dbbb1c0a69",
        "role": "base snapshot direct-copy helper",
    },
    "0x004848bc": {
        "name": "FUN_004848bc", "size": 1005, "calling_convention": "__fastcall",
        "mnemonic_sha256": "c42d1f68ccf1c7aa9cbb78c1eeb130d296b1c1503044f564a6f30f31c59ce149",
        "role": "SMS participant render tick",
    },
    "0x00483540": {
        "name": "FUN_00483540", "size": 1274, "calling_convention": "__fastcall",
        "mnemonic_sha256": "42c29f6f4d6cec8e4e250cd1c8e6d7ac691a36fc3eb249e2a16670b02f3cd483",
        "role": "derived vehicle render-state builder",
    },
    "0x00438da0": {
        "name": "FUN_00438da0", "size": 207, "calling_convention": "__fastcall",
        "mnemonic_sha256": "afaa139e050a75dffccf4960c8d928bf9203aa8db2ae2e2f804b40fdc420864b",
        "role": "quaternion-to-matrix helper candidate",
    },
    "0x0042fc90": {
        "name": "FUN_0042fc90", "size": 111, "calling_convention": "__thiscall",
        "mnemonic_sha256": "21fbeebafacbc9c2b9f2d6b9987915413a27b5a8263e75f4b177861701b7f7ce",
        "role": "matrix-copy/expand helper candidate",
    },
    "0x004ae150": {
        "name": "FUN_004ae150", "size": 1846, "calling_convention": "__fastcall",
        "mnemonic_sha256": "9564786227db5a858d3b07ebde3633ce46e69470aa90b49bed632024c21e7fe7",
        "role": "vehicle RenderHierarchy node-local update lane",
    },
    "0x0047c9f0": {
        "name": "FUN_0047c9f0", "size": 73, "calling_convention": "__fastcall",
        "mnemonic_sha256": "28bbc6d91309a329c923d5ebe5c08cf39b449db065fc6da2048d8a9f64f1e08c",
        "role": "participant-list world-pose dispatch",
    },
    "0x00480700": {
        "name": "FUN_00480700", "size": 92, "calling_convention": "__fastcall",
        "mnemonic_sha256": "f516ada7168e7af185891058c2e3405389a715a4933cc64acb624502f06f9f6d",
        "role": "vehicle world-affine consumer candidate",
    },
    "0x004a8c20": {
        "name": "FUN_004a8c20", "size": 198, "calling_convention": "__fastcall",
        "mnemonic_sha256": "1bdaa8f843f668bc4bec2d58d23a62c20efd23c737b78795f687a1cf67e72ece",
        "role": "vehicle-render-model world-point consumer",
    },
}

REQUIRED_EDGES = (
    ("0x0070db00", "0x0070db29", "0x00481e20"),
    ("0x00481e20", "0x00481e2b", "0x0047fa40"),
    ("0x004848bc", "0x004848f5", "0x00481e20"),
    ("0x004848bc", "0x00484916", "0x00483540"),
    ("0x004848bc", "0x00484933", "0x0042fc90"),
    ("0x004848bc", "0x00484b31", "0x004ae150"),
    ("0x00483540", "0x00483996", "0x00438da0"),
    ("0x0047c9f0", "0x0047ca24", "0x00480700"),
    ("0x00480700", "0x00480726", "0x0042fc90"),
    ("0x00480700", "0x0048074f", "0x004a8c20"),
)

TARGETED_INSTRUCTION_WORKLIST = (
    "FUN_0070db00",
    "FUN_00481e20",
    "FUN_0047fa40",
    "FUN_004848bc",
    "FUN_00483540",
    "FUN_00438da0",
    "FUN_0042fc90",
    "FUN_004ae150",
    "FUN_00480700",
    "FUN_004a8c20",
)

NON_GATING_DECOMPILER_OBSERVATIONS = {
    "participant_source_snapshot_byte_offset": "0x110",
    "participant_render_snapshot_byte_offset": "0xa00",
    "render_root_quaternion_byte_offset": "0xa00",
    "render_root_position_byte_offsets": ["0xa10", "0xa14", "0xa18"],
    "derived_rotation_matrix_byte_offset": "0x1028",
    "vehicle_render_model_byte_offset": "0x1340",
    "vehicle_slot_snapshot_base_byte_offset": "0xd70",
    "vehicle_slot_snapshot_stride_bytes": "0x8f0",
    "vehicle_slot_active_selector_byte_offset": "0x1f50",
}


def _load_json(path: Path) -> dict[str, Any]:
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


def build_vehicle_render_root_pose_transport_frontier(ghidra_export: Path) -> dict[str, Any]:
    binary = _load_json(ghidra_export / "binary.json")
    if binary.get("program_name") != PROGRAM or binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable identity")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(ghidra_export / "functions.jsonl"):
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
    for address, expected in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        for key in ("name", "size", "calling_convention", "mnemonic_sha256"):
            if row.get(key) != expected[key]:
                raise ValueError(f"{address}: {key} drift")
        functions.append({"address": address, **expected})

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(ghidra_export / "callgraph.jsonl"):
        if row.get("indirect") is True:
            continue
        raw_source, raw_insn, raw_target = row.get("from_function"), row.get("instruction"), row.get("to")
        if not all(isinstance(v, str) for v in (raw_source, raw_insn, raw_target)):
            continue
        edges.add((
            _addr(raw_source, "callgraph.from_function"),
            _addr(raw_insn, "callgraph.instruction"),
            _addr(raw_target, "callgraph.to"),
        ))

    required = set(REQUIRED_EDGES)
    missing_edges = sorted(required - edges)
    if missing_edges:
        raise ValueError(f"vehicle render root-pose required call edge drift: {missing_edges}")

    return {
        "format": FORMAT,
        "status": "frontier-ready",
        "ready": True,
        "retail": {
            "program_name": PROGRAM,
            "executable_md5": PE_MD5,
            "functions": functions,
            "required_direct_edges": [
                {"from": source, "instruction": instruction, "to": target}
                for source, instruction, target in REQUIRED_EDGES
            ],
        },
        "proven": {
            "vehicle_slot_snapshot_reader_reaches_extended_snapshot_copy": True,
            "extended_snapshot_copy_reaches_base_direct_copy_helper": True,
            "participant_render_tick_reaches_snapshot_copy": True,
            "participant_render_tick_reaches_derived_state_builder": True,
            "derived_state_builder_reaches_quaternion_matrix_helper": True,
            "participant_render_tick_reaches_vehicle_hierarchy_node_update_lane": True,
            "participant_list_reaches_vehicle_world_affine_consumer": True,
            "vehicle_world_affine_consumer_reaches_vehicle_render_model_world_point_consumer": True,
            "root_pose_transport_callgraph_neighborhood_bounded": True,
        },
        "non_gating_decompiler_observations": {
            **NON_GATING_DECOMPILER_OBSERVATIONS,
            "admissibility": "instruction-proof-pending",
            "used_to_open_readiness_gates": False,
        },
        "targeted_instruction_worklist": {
            "format": "SHIFT.GhidraFunctionInstructions/2",
            "functions": list(TARGETED_INSTRUCTION_WORKLIST),
            "purpose": (
                "prove receiver-relative snapshot source/destination offsets, quaternion/position "
                "world-affine construction, and the exact owner receiving that affine before any "
                "outer-Vehicle/VHF frame identity claim"
            ),
        },
        "next_proof": {
            "question": (
                "Does the SMS participant root-pose snapshot carry the same outer Vehicle frame, "
                "and which source-backed GraphicsEngine/RenderHierarchy owner receives its world affine?"
            ),
            "required_checks": [
                "prove FUN_0070db00 active snapshot address expression and 0x8f0 double-buffer stride",
                "prove FUN_00481e20/FUN_0047fa40 direct root-pose field copy without basis conversion",
                "prove FUN_00483540 quaternion source and derived rotation-matrix destination offsets",
                "prove FUN_004848bc/FUN_00480700 position offsets and full world-affine construction",
                "separate FUN_004ae150 node-local palette updates from the external hierarchy/root owner",
                "join the resulting owner to a source-backed RenderHierarchy/VHF runtime object",
            ],
        },
        "handoff": {
            "sms_vehicle_root_pose_transport_callgraph_frontier_ready": True,
            "sms_vehicle_root_pose_offsets_instruction_proof_ready": False,
            "sms_vehicle_world_affine_instruction_proof_ready": False,
            "sms_vehicle_world_affine_RenderHierarchy_owner_join_ready": False,
            "outer_vehicle_root_to_SMS_snapshot_semantic_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "scope": {
            "decompiler_offsets_promoted_to_proof": False,
            "callgraph_adjacency_used_as_frame_identity": False,
            "node_local_VHF_palette_updates_equated_to_vehicle_world_root": False,
            "secondary_world_point_consumer_equated_to_VHF_root_setter": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_vehicle_render_root_pose_transport_frontier(args.ghidra_export)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
