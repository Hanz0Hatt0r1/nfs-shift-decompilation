#!/usr/bin/env python3
"""Prove the canonical BMW BODY0 construction pose without inventing a VHF-frame join.

This is the next fail-closed layer for the playable Linux vehicle-transform path.
It combines the exact retail BMW_M3_E36 BFF resources with already recovered
machine-code facts for the SDF loader and persistent BODY constructor.

The result proves BODY index 0 is constructed at zero origin with identity basis
inside the physics construction frame.  It deliberately does *not* equate that
frame to the Phase 645 VHF vehicle root; that final root-frame relation remains
an independent prerequisite for SHIFT.BMWBody0BindFrameProof/1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shift_importer import BFF

FORMAT = "SHIFT.BMWBody0ConstructionBindPose/1"
BIND_PROOF_FORMAT = "SHIFT.BMWBody0BindFrameProof/1"

EXECUTABLE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
ARCHIVE_NAME = "BMW_M3_E36.bff"
ARCHIVE_SHA256 = "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
SDF_PATH = "vehicles/physics/suspension/aarm_multilink.sdf"
SDF_SHA256 = "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
VHF_PATH = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
VHF_SHA256 = "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
BODY_OBJECT_NAME = "BMW_M3_E36_KIT00_BODY_LODA"
BODY_MEB_PATH = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
BODY_INDEX = 0
BODY_NAME = "body"

IDENTITY_ROW = [
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
]

# Exact Ghidra function extents plus independent retail PE byte hashes.  The
# companion verifier checks these against SHIFT.exe without executing it.
FUNCTION_BYTES: dict[str, dict[str, Any]] = {
    "FUN_007b6900": {
        "start": 0x007B6900,
        "end": 0x007B724B,
        "sha256": "f002a432094a9424f70d1cc4df66520bd52a4cfb43cb85912dc64b69db6bb039",
        "role": "SDF BODY/constraint loader and descriptor producer",
    },
    "FUN_007b3670": {
        "start": 0x007B3670,
        "end": 0x007B381E,
        "sha256": "ebf20c065ba0fd4e1597d2cbfa176ab7ffd8d68533779f141fad8bdcd723c55b",
        "role": "0x170-byte persistent BODY construction writer",
    },
    "FUN_007bbb10": {
        "start": 0x007BBB10,
        "end": 0x007BBB5E,
        "sha256": "592ef45c846952ec94d40661a29b60416b39fb6f34825a11f4928c4e65981b84",
        "role": "BODY orientation-vector to persistent basis setter",
    },
    "FUN_007b00a0": {
        "start": 0x007B00A0,
        "end": 0x007B01B4,
        "sha256": "9344a52395e678bbf86704d0075a5c70599dbe46075f973ef69deb2ed2ceb226",
        "role": "three-angle to 3x3 basis construction",
    },
}

DIRECT_CALLS = [
    {"caller": "FUN_007b6900", "callsite": 0x007B6E8F, "callee": "FUN_007b3670"},
    {"caller": "FUN_007b3670", "callsite": 0x007B37C8, "callee": "FUN_007bbb10"},
    {"caller": "FUN_007bbb10", "callsite": 0x007BBB3A, "callee": "FUN_007b00a0"},
]

# Exact byte spans that encode the value-transfer facts used by this contract.
# These are verified by verify_bmw_body0_construction_bind_binary.py.
MACHINE_SIGNATURES: dict[str, dict[str, Any]] = {
    "builder_origin_copy": {
        "start": 0x007B3797,
        "end": 0x007B37B5,
        "hex": "dd068b078b531469c070010000dd1c10dd4608dd5c1008dd4610dd5c1010",
    },
    "builder_orientation_forward": {
        "start": 0x007B37BF,
        "end": 0x007B37CD,
        "hex": "8d86080100005003cae843830000",
    },
    "builder_count_increment": {
        "start": 0x007B3810,
        "end": 0x007B3813,
        "hex": "830701",
    },
    "orientation_store_and_basis_call": {
        "start": 0x007BBB13,
        "end": 0x007BBB3F,
        "hex": (
            "8b4508dd00568bf1dd9e0801000050dd40088d8ed4000000"
            "dd9e10010000dd4010dd9e18010000e86145ffff"
        ),
    },
    "x87_fcos": {"start": 0x00900B7D, "end": 0x00900B7F, "hex": "d9ff"},
    "x87_fsin": {"start": 0x00900CAD, "end": 0x00900CAF, "hex": "d9fe"},
}

_VECTOR_RE = re.compile(r"\b(?P<key>pos|ori)\s*=\s*\((?P<values>[^)]*)\)", re.IGNORECASE)
_NAME_RE = re.compile(r"\bname\s*=\s*(?P<name>[^\s]+)", re.IGNORECASE)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zero(value: float) -> bool:
    return math.isfinite(value) and abs(value) <= 1.0e-12


def _triplet(text: str, key: str) -> list[float]:
    for match in _VECTOR_RE.finditer(text):
        if match.group("key").lower() != key:
            continue
        parts = [part.strip() for part in match.group("values").split(",")]
        if len(parts) != 3:
            raise ValueError(f"{key}: expected exactly three values")
        values = [float(part) for part in parts]
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{key}: non-finite value")
        return values
    raise ValueError(f"BODY record is missing {key}")


def _body_records(sdf: bytes) -> list[dict[str, Any]]:
    text = sdf.decode("utf-8")
    # Strip line comments before section splitting so words in comments cannot
    # manufacture a BODY record or field.
    clean = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
    markers = list(re.finditer(r"(?m)^\s*\[([^\]]+)\]\s*$", clean))
    records: list[dict[str, Any]] = []
    for index, marker in enumerate(markers):
        if marker.group(1).strip().upper() != "BODY":
            continue
        end = markers[index + 1].start() if index + 1 < len(markers) else len(clean)
        body_text = clean[marker.end() : end]
        name_match = _NAME_RE.search(body_text)
        if name_match is None:
            raise ValueError("BODY record has no name")
        records.append(
            {
                "name": name_match.group("name"),
                "pos": _triplet(body_text, "pos"),
                "ori": _triplet(body_text, "ori"),
            }
        )
    return records


def _normalized_resource_path(value: str) -> str:
    return value.replace("\\", "/").strip().lower()


def _numbers(value: str, count: int, label: str) -> list[float]:
    parts = value.split()
    if len(parts) != count:
        raise ValueError(f"{label}: expected {count} scalars")
    result = [float(part) for part in parts]
    if not all(math.isfinite(number) for number in result):
        raise ValueError(f"{label}: non-finite scalar")
    return result


def _canonical_vhf_identity(vhf: bytes) -> dict[str, Any]:
    root = ET.fromstring(vhf.decode("utf-8"))
    matrices: dict[str, ET.Element] = {}
    for matrix in root.iter("MATRIX"):
        matrix_id = matrix.get("id")
        if matrix_id is not None:
            if matrix_id in matrices:
                raise ValueError(f"duplicate VHF MATRIX id {matrix_id}")
            matrices[matrix_id] = matrix

    candidates: list[ET.Element] = []
    for node in root.iter("NODE"):
        if node.get("type") != "OBJECT" or node.get("Name") != BODY_OBJECT_NAME:
            continue
        resource = node.find("RESOURCE")
        if resource is None:
            continue
        filename = resource.get("Filename") or ""
        if _normalized_resource_path(filename) == BODY_MEB_PATH:
            candidates.append(node)
    if len(candidates) != 1:
        raise ValueError(
            f"expected one canonical VHF body object, found {len(candidates)}"
        )

    node = candidates[0]
    matrix_id = node.get("MatrixNumber")
    if matrix_id is None or matrix_id not in matrices:
        raise ValueError("canonical VHF body object has no resolved MATRIX")
    matrix = matrices[matrix_id]
    offset = _numbers(matrix.get("Offset") or "", 3, "VHF body Offset")
    orientation = _numbers(
        matrix.get("Orientation") or "", 4, "VHF body Orientation"
    )
    parent = matrix.get("parent")
    if parent != "0":
        raise ValueError("canonical VHF body MATRIX is not directly rooted at MATRIX 0")

    root_matrix = matrices.get("0")
    if root_matrix is None:
        raise ValueError("VHF MATRIX 0 missing")
    root_offset = _numbers(root_matrix.get("Offset") or "", 3, "VHF root Offset")
    root_orientation = _numbers(
        root_matrix.get("Orientation") or "", 4, "VHF root Orientation"
    )
    if not all(_zero(value) for value in root_offset):
        raise ValueError("VHF root Offset is not zero")
    if root_orientation != [0.0, 0.0, 0.0, 1.0]:
        raise ValueError("VHF root Orientation is not identity quaternion")
    if not all(_zero(value) for value in offset):
        raise ValueError("canonical VHF body Offset is not zero")
    if orientation != [0.0, 0.0, 0.0, 1.0]:
        raise ValueError("canonical VHF body Orientation is not identity quaternion")

    return {
        "object_name": BODY_OBJECT_NAME,
        "resource_path": BODY_MEB_PATH,
        "matrix_number": int(matrix_id),
        "matrix_parent": int(parent),
        "offset": offset,
        "orientation_quaternion": orientation,
        "object_to_vhf_root_identity": True,
    }


def _entry_by_path(archive: BFF, path: str):
    matches = [
        entry
        for entry in archive.entries
        if _normalized_resource_path(entry.path) == path
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {path} entry, found {len(matches)}")
    return matches[0]


def build_bmw_body0_construction_bind_pose(bff_path: Path) -> dict[str, Any]:
    bff_path = Path(bff_path)
    archive_bytes = bff_path.read_bytes()
    archive_sha = _sha256(archive_bytes)
    if archive_sha != ARCHIVE_SHA256:
        raise ValueError(
            f"unexpected BMW_M3_E36.bff SHA-256: expected {ARCHIVE_SHA256}, got {archive_sha}"
        )

    with BFF(bff_path) as archive:
        sdf_entry = _entry_by_path(archive, SDF_PATH)
        vhf_entry = _entry_by_path(archive, VHF_PATH)
        sdf = archive.extract_entry(sdf_entry)
        vhf = archive.extract_entry(vhf_entry)

    if _sha256(sdf) != SDF_SHA256:
        raise ValueError("canonical E36 SDF SHA-256 drift")
    if _sha256(vhf) != VHF_SHA256:
        raise ValueError("canonical E36 VHF SHA-256 drift")

    bodies = _body_records(sdf)
    if len(bodies) != 11:
        raise ValueError(f"canonical E36 SDF BODY count drift: {len(bodies)}")
    body0 = bodies[0]
    if body0["name"] != BODY_NAME:
        raise ValueError(f"BODY index 0 name drift: {body0['name']!r}")
    if not all(_zero(value) for value in body0["pos"]):
        raise ValueError("BODY0 SDF position is not zero")
    if not all(_zero(value) for value in body0["ori"]):
        raise ValueError("BODY0 SDF orientation is not zero")

    vhf_identity = _canonical_vhf_identity(vhf)

    return {
        "format": FORMAT,
        "status": "ready",
        "ready": True,
        "source": {
            "archive": ARCHIVE_NAME,
            "archive_sha256": archive_sha,
            "sdf_path": SDF_PATH,
            "sdf_sha256": _sha256(sdf),
            "vhf_path": VHF_PATH,
            "vhf_sha256": _sha256(vhf),
            "original_game_executed": False,
            "new_runtime_capture_used": False,
        },
        "body0_resource_descriptor": {
            "body_index": BODY_INDEX,
            "body_name": BODY_NAME,
            "body_count": len(bodies),
            "pos": body0["pos"],
            "ori": body0["ori"],
            "first_BODY_record_is_chassis_BODY0": True,
        },
        "machine_construction_chain": {
            "functions": FUNCTION_BYTES,
            "direct_calls": [
                {
                    **row,
                    "callsite": f"0x{int(row['callsite']):08x}",
                }
                for row in DIRECT_CALLS
            ],
            "loader_pos_descriptor_offsets": ["+0x00", "+0x08", "+0x10"],
            "loader_ori_descriptor_offsets": ["+0x108", "+0x110", "+0x118"],
            "persistent_BODY_origin_offsets": ["+0x00", "+0x08", "+0x10"],
            "persistent_BODY_basis_offsets": "+0xd4..+0xf4",
            "BODY_stride": "0x170",
            "body_count_increment_occurs_after_origin_and_basis_writes": True,
            "zero_orientation_uses_x87_fsin_fcos": True,
            "zero_orientation_produces_identity_basis": True,
            "construction_path_uses_FUN_007b7840": False,
        },
        "construction_pose": {
            "frame": "physics-SDF-construction-root",
            "origin": [0.0, 0.0, 0.0],
            "basis": [
                1.0, 0.0, 0.0,
                0.0, 1.0, 0.0,
                0.0, 0.0, 1.0,
            ],
            "row_matrix": list(IDENTITY_ROW),
            "BODY0_initial_pose_identity_proven": True,
            "evidence_state": "proven-static-resource-plus-machine",
        },
        "phase645_resource_side": vhf_identity,
        "handoff": {
            "BODY0_construction_pose_ready": True,
            "BODY0_initial_pose_identity_proven": True,
            "phase645_canonical_body_object_to_vhf_root_identity_proven": True,
            "physics_construction_root_equals_vhf_vehicle_root_proven": False,
            "BODY0_bind_frame_proof_ready": False,
            "required_contract": BIND_PROOF_FORMAT,
            "critical_next_join": (
                "prove physics-SDF construction root == Phase645 VHF vehicle root; "
                "do not infer the join from matching identity matrices alone"
            ),
        },
        "blockers": [
            {
                "id": "physics-construction-root-to-vhf-root-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "source/static vehicle-root continuity joining the FUN_007615c0/FUN_007b6900 "
                    "physics owner construction frame to the Phase645 VHF hierarchy root"
                ),
            }
        ],
        "scope": {
            "identity_matrix_assumed": False,
            "matching_zero_offsets_used_as_root_frame_identity": False,
            "SDF_BODY0_values_traced_into_persistent_BODY": True,
            "zero_ori_to_identity_basis_machine_path_proven": True,
            "FUN_007b7840_promoted_to_bind_initializer": False,
            "BODY0_local_equals_VHF_root_proven": False,
            "BODY0_bind_matrix_proven": False,
            "renderer_transform_reimplemented": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bff", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_bmw_body0_construction_bind_pose(args.bff)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
