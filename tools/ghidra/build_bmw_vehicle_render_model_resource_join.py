#!/usr/bin/env python3
"""Join the selected BMW vehicle descriptor to the canonical retail VHF resource.

This is the bounded resource-side continuation of
`SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1`.  It reads retail BFF data,
recovers the concrete `Vehicle Render Model` value from the BMW M3 E36 CRD,
and resolves that value relative to the descriptor's logical resource path.

The pass is deliberately fail-closed: descriptor copies must agree byte-for-
byte and semantically, the owner proof must already be positive, and the
resolved VHF logical path must identify exactly one entry in the primary BMW
archive.  It does not by itself prove the outer Vehicle-root -> VHF-root frame
relation or BODY0 bind-frame semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shift_importer import BFF  # noqa: E402

FORMAT = "SHIFT.BMWVehicleRenderModelResourceJoin/1"
OWNER_FORMAT = "SHIFT.VehicleRenderHierarchyResourceOwnerJoin/1"
VEHICLE_NAME = "BMW_M3_E36"
DESCRIPTOR_PATH = "vehicles/bmw_m3_e36/bmw_m3_e36.crd"
PROPERTY_NAME = "Vehicle Render Model"
EXPECTED_PROPERTY_FIELD = "+0x54"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip("/").lower()


def _validate_owner(owner: dict[str, Any]) -> None:
    if owner.get("format") != OWNER_FORMAT or owner.get("ready") is not True:
        raise ValueError("vehicle RenderHierarchy owner proof is not positive")
    descriptor = owner.get("vehicle_descriptor")
    handoff = owner.get("handoff")
    if not isinstance(descriptor, dict) or not isinstance(handoff, dict):
        raise ValueError("vehicle RenderHierarchy owner proof shape drift")
    if descriptor.get("render_model_property_name") != PROPERTY_NAME:
        raise ValueError("Vehicle Render Model property-name proof drift")
    if descriptor.get("render_model_field") != EXPECTED_PROPERTY_FIELD:
        raise ValueError("Vehicle Render Model +0x54 proof drift")
    if handoff.get("vehicle_render_hierarchy_owner_ready") is not True:
        raise ValueError("vehicle RenderHierarchy owner handoff is not ready")


def _descriptor_value(payload: bytes) -> str:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"BMW descriptor is not valid reflection XML: {exc}") from exc

    matches: list[ET.Element] = []
    for node in root.findall("data"):
        if node.get("class") != "VehicleDetails":
            continue
        props = {prop.get("name"): prop.get("data") for prop in node.findall("prop")}
        if props.get("Name") == VEHICLE_NAME:
            matches.append(node)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one VehicleDetails/{VEHICLE_NAME}, found {len(matches)}")

    props = {prop.get("name"): prop.get("data") for prop in matches[0].findall("prop")}
    value = props.get(PROPERTY_NAME)
    if not value:
        raise ValueError(f"{VEHICLE_NAME}: missing {PROPERTY_NAME!r}")
    return value


def _find_entries(archive: BFF, logical_path: str):
    wanted = _norm(logical_path)
    return [entry for entry in archive.entries if _norm(entry.path) == wanted]


def _resolve_descriptor_resource(descriptor_path: str, value: str) -> str:
    normalized_value = value.replace("\\", "/")
    value_path = PurePosixPath(normalized_value)
    if value_path.is_absolute():
        raise ValueError("Vehicle Render Model unexpectedly uses an absolute path")
    parent = PurePosixPath(descriptor_path.replace("\\", "/")).parent
    if "/" in normalized_value:
        resolved = value_path
    else:
        resolved = parent / value_path
    return str(resolved)


def analyze(owner_proof: Path, primary_vehicle_archive: Path, descriptor_archives: list[Path]) -> dict[str, Any]:
    owner = _load_json(owner_proof)
    _validate_owner(owner)
    if not descriptor_archives:
        raise ValueError("at least one descriptor archive is required")

    descriptor_copies: list[dict[str, Any]] = []
    descriptor_values: set[str] = set()
    descriptor_hashes: set[str] = set()
    for archive_path in descriptor_archives:
        with BFF(archive_path) as archive:
            matches = _find_entries(archive, DESCRIPTOR_PATH)
            if len(matches) != 1:
                raise ValueError(
                    f"{archive_path}: expected exactly one {DESCRIPTOR_PATH}, found {len(matches)}"
                )
            entry = matches[0]
            payload = archive.extract_entry(entry)
            value = _descriptor_value(payload)
            digest = _sha256_bytes(payload)
            descriptor_values.add(value.lower())
            descriptor_hashes.add(digest)
            descriptor_copies.append(
                {
                    "archive": archive_path.name,
                    "archive_sha256": _sha256_file(archive_path),
                    "entry_index": entry.index,
                    "path": entry.path,
                    "compression_type": entry.type,
                    "compressed_size": entry.compressed_size,
                    "uncompressed_size": entry.uncompressed_size,
                    "decoded_sha256": digest,
                    "vehicle_render_model": value,
                }
            )

    if len(descriptor_values) != 1:
        raise ValueError(f"retail descriptor copies disagree on {PROPERTY_NAME}: {sorted(descriptor_values)}")
    if len(descriptor_hashes) != 1:
        raise ValueError("retail BMW descriptor copies are not byte-identical")

    selected_value = descriptor_copies[0]["vehicle_render_model"]
    assert isinstance(selected_value, str)
    resolved_path = _resolve_descriptor_resource(DESCRIPTOR_PATH, selected_value)
    if PurePosixPath(resolved_path).suffix.lower() != ".vhf":
        raise ValueError(f"{PROPERTY_NAME} does not resolve to .vhf: {selected_value!r}")

    with BFF(primary_vehicle_archive) as archive:
        matches = _find_entries(archive, resolved_path)
        if len(matches) != 1:
            raise ValueError(
                f"{primary_vehicle_archive}: resolved VHF path {resolved_path!r} matched {len(matches)} entries"
            )
        vhf_entry = matches[0]
        vhf = archive.extract_entry(vhf_entry)

    try:
        vhf_root = ET.fromstring(vhf)
    except ET.ParseError as exc:
        raise ValueError(f"resolved BMW VHF is not XML/RenderHierarchy data: {exc}") from exc
    if vhf_root.tag != "CAR" or vhf_root.get("Name") != VEHICLE_NAME:
        raise ValueError("resolved VHF root identity does not match BMW_M3_E36")
    hierarchy = vhf_root.find("NODE")
    if hierarchy is None or hierarchy.get("type") != "HIERARCHY":
        raise ValueError("resolved VHF does not expose a HIERARCHY root")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "bmw-vehicle-render-model-resource-proven",
        "ready": True,
        "inputs": {
            "owner_proof": owner_proof.name,
            "owner_proof_format": OWNER_FORMAT,
            "primary_vehicle_archive": primary_vehicle_archive.name,
            "primary_vehicle_archive_sha256": _sha256_file(primary_vehicle_archive),
            "descriptor_archive_count": len(descriptor_archives),
        },
        "selected_vehicle_descriptor": {
            "vehicle_name": VEHICLE_NAME,
            "descriptor_path": DESCRIPTOR_PATH,
            "descriptor_copy_count": len(descriptor_copies),
            "descriptor_decoded_sha256": next(iter(descriptor_hashes)),
            "copies": descriptor_copies,
            "property_name": PROPERTY_NAME,
            "property_field": EXPECTED_PROPERTY_FIELD,
            "property_value": selected_value,
            "selected_BMW_vehicle_render_model_value_ready": True,
        },
        "canonical_bmw_vhf_resource": {
            "resolved_path": vhf_entry.path,
            "archive": primary_vehicle_archive.name,
            "entry_index": vhf_entry.index,
            "compression_type": vhf_entry.type,
            "compressed_size": vhf_entry.compressed_size,
            "uncompressed_size": vhf_entry.uncompressed_size,
            "decoded_sha256": _sha256_bytes(vhf),
            "root_tag": vhf_root.tag,
            "root_name": vhf_root.get("Name"),
            "root_node_type": hierarchy.get("type"),
            "canonical_BMW_VHF_resource_join_ready": True,
        },
        "provenance": {
            "owner_proof_vehicle_render_model_property_ready": True,
            "retail_descriptor_value_recovered": True,
            "retail_descriptor_copies_byte_identical": True,
            "descriptor_relative_resource_resolution_ready": True,
            "resolved_vhf_logical_path_unique_in_primary_archive": True,
            "resolved_vhf_vehicle_identity_matches_descriptor": True,
            "resolved_vhf_render_hierarchy_root_ready": True,
        },
        "handoff": {
            "vehicle_render_hierarchy_owner_ready": True,
            "selected_BMW_vehicle_render_model_value_ready": True,
            "canonical_BMW_VHF_resource_join_ready": True,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
            "next_frontier": (
                "join the proven outer/root-pose transport to this exact BMW VHF HIERARCHY root; "
                "do not infer frame equivalence from resource identity alone"
            ),
        },
        "scope": {
            "runtime_capture_required": False,
            "descriptor_value_invented": False,
            "basename_only_fallback_used": False,
            "archive_order_fallback_used": False,
            "outer_vehicle_to_vhf_frame_relation_claimed": False,
            "body0_bind_frame_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner_proof", type=Path)
    parser.add_argument("primary_vehicle_archive", type=Path)
    parser.add_argument("descriptor_archives", type=Path, nargs="+")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze(args.owner_proof, args.primary_vehicle_archive, args.descriptor_archives)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
