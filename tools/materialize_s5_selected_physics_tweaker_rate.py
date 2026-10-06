#!/usr/bin/env python3
"""Materialize the selected-session PhysicsTweaker tick rate fail-closed.

The tool accepts either the exact retail PHYSICSBOOTFLOW.bff or already-decoded
entry bytes.  It never substitutes the cPhysicsManager constructor default.
Admission requires the decoded payload SHA-256 already pinned by
SHIFT.BMWOffset33bSelectorGeometryInputs/1 and a unique positive integral
`<prop name="tick rate" data="..."/>` value.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shift_importer import BFF  # noqa: E402

FORMAT = "SHIFT.SelectedSessionPhysicsTweakerRate/1"
GEOMETRY_FORMAT = "SHIFT.BMWOffset33bSelectorGeometryInputs/1"
CADENCE_FORMAT = "SHIFT.RetailOuterUpdateCadence/1"
EXPECTED_RESOURCE_PATH = "vehicles/physics/physicstweaker.xml"
PROPERTY_NAME = "tick rate"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _resource_identity(geometry_path: Path) -> dict[str, Any]:
    geometry = _read_json(geometry_path)
    if geometry.get("format") != GEOMETRY_FORMAT or geometry.get("ready") is not True:
        raise ValueError(f"positive {GEOMETRY_FORMAT} contract required")
    sources = geometry.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("geometry contract sources missing")
    tweaker = sources.get("physics_tweaker")
    if not isinstance(tweaker, dict):
        raise ValueError("physics_tweaker source identity missing")
    archive = tweaker.get("archive")
    entry = tweaker.get("entry")
    if not isinstance(archive, dict) or not isinstance(entry, dict):
        raise ValueError("physics_tweaker archive/entry identity missing")
    required_archive = {
        "filename": "PHYSICSBOOTFLOW.bff",
        "sha256": "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a",
    }
    required_entry = {
        "index": 49,
        "path": EXPECTED_RESOURCE_PATH,
        "compression_type": 2,
        "compressed_size": 2452,
        "uncompressed_size": 21762,
        "decoded_sha256": "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f",
    }
    for key, expected in required_archive.items():
        if archive.get(key) != expected:
            raise ValueError(f"physics_tweaker archive {key} drift")
    for key, expected in required_entry.items():
        if entry.get(key) != expected:
            raise ValueError(f"physics_tweaker entry {key} drift")
    return {"archive": dict(archive), "entry": dict(entry)}


def _validate_cadence(cadence_path: Path) -> dict[str, Any]:
    cadence = _read_json(cadence_path)
    if cadence.get("format") != CADENCE_FORMAT or cadence.get("ready") is not True:
        raise ValueError(f"positive {CADENCE_FORMAT} contract required")
    adjudication = cadence.get("adjudication")
    rate_field = cadence.get("physics_rate_field")
    runtime = cadence.get("runtime_handoff")
    if not isinstance(adjudication, dict) or not isinstance(rate_field, dict) or not isinstance(runtime, dict):
        raise ValueError("cadence contract required sections missing")
    required_true = (
        "outer_scheduler_cadence_admitted",
        "physics_rate_field_domain_and_reciprocal_proven",
        "inner_fixed_step_1_over_rate_proven",
        "final_inner_rate_requires_loaded_PhysicsTweaker_value",
    )
    for field in required_true:
        if adjudication.get(field) is not True:
            raise ValueError(f"cadence prerequisite not positive: {field}")
    if rate_field.get("runtime_rate_global") != "DAT_00c130d2":
        raise ValueError("cadence runtime rate global drift")
    if rate_field.get("tick_rate_tweaker_offset") != "0x492":
        raise ValueError("cadence PhysicsTweaker tick-rate offset drift")
    if rate_field.get("final_numeric_rate_not_frozen") is not True:
        raise ValueError("cadence contract no longer requires loaded numeric rate")
    if runtime.get("retail_outer_cadence_admitted") is not True:
        raise ValueError("retail outer cadence is not admitted")
    simulation = runtime.get("simulation_quantum")
    if not isinstance(simulation, dict) or simulation.get(
        "session_rate_requires_loaded_PhysicsTweaker_value"
    ) is not True:
        raise ValueError("runtime handoff does not require loaded PhysicsTweaker rate")
    return cadence


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_tick_rate(decoded: bytes, expected_sha256: str) -> int:
    actual = _sha256(decoded)
    if actual != expected_sha256:
        raise ValueError(
            "decoded PhysicsTweaker SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual}"
        )
    try:
        root = ET.fromstring(decoded)
    except ET.ParseError as exc:
        raise ValueError(f"PhysicsTweaker XML parse failed: {exc}") from exc

    matches = [
        element
        for element in root.iter()
        if element.tag == "prop" and element.get("name") == PROPERTY_NAME
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one PhysicsTweaker {PROPERTY_NAME!r} property; "
            f"found {len(matches)}"
        )
    token = matches[0].get("data")
    if token is None or not token.strip():
        raise ValueError("PhysicsTweaker tick rate data attribute missing")
    try:
        value = Decimal(token.strip())
    except InvalidOperation as exc:
        raise ValueError(f"PhysicsTweaker tick rate is not numeric: {token!r}") from exc
    if not value.is_finite() or value <= 0 or value != value.to_integral_value():
        raise ValueError("PhysicsTweaker tick rate must be a positive integral value")
    rate = int(value)
    if not 1 <= rate <= 0xFFFF:
        raise ValueError("PhysicsTweaker tick rate does not fit the recovered uint16 load")
    return rate


def _decoded_from_archive(archive_path: Path, identity: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    archive_expected = identity["archive"]
    entry_expected = identity["entry"]
    archive_bytes = archive_path.read_bytes()
    archive_sha = _sha256(archive_bytes)
    if archive_sha != archive_expected["sha256"]:
        raise ValueError(
            "PHYSICSBOOTFLOW archive SHA-256 mismatch: "
            f"expected {archive_expected['sha256']}, got {archive_sha}"
        )
    if archive_path.name.lower() != str(archive_expected["filename"]).lower():
        raise ValueError("PHYSICSBOOTFLOW archive filename mismatch")

    with BFF(archive_path) as archive:
        index = int(entry_expected["index"])
        if index >= len(archive.entries):
            raise ValueError("PhysicsTweaker entry index outside archive")
        entry = archive.entries[index]
        actual_metadata = {
            "index": entry.index,
            "path": entry.path.lower(),
            "compression_type": entry.type,
            "compressed_size": entry.compressed_size,
            "uncompressed_size": entry.uncompressed_size,
        }
        expected_metadata = {
            "index": index,
            "path": str(entry_expected["path"]).lower(),
            "compression_type": int(entry_expected["compression_type"]),
            "compressed_size": int(entry_expected["compressed_size"]),
            "uncompressed_size": int(entry_expected["uncompressed_size"]),
        }
        if actual_metadata != expected_metadata:
            raise ValueError(
                "PhysicsTweaker entry metadata mismatch: "
                f"expected {expected_metadata}, got {actual_metadata}"
            )
        decoded = archive.extract_entry(entry)
    return decoded, {
        "mode": "exact-retail-bff",
        "archive_sha256_verified_this_run": True,
        "decoded_sha256_verified_this_run": True,
    }


def materialize(
    geometry_path: Path,
    cadence_path: Path,
    *,
    archive_path: Path | None = None,
    decoded_entry_path: Path | None = None,
) -> dict[str, Any]:
    if (archive_path is None) == (decoded_entry_path is None):
        raise ValueError("provide exactly one of archive_path or decoded_entry_path")
    identity = _resource_identity(geometry_path)
    cadence = _validate_cadence(cadence_path)
    expected_decoded_sha = str(identity["entry"]["decoded_sha256"])

    if archive_path is not None:
        decoded, verification = _decoded_from_archive(archive_path, identity)
    else:
        assert decoded_entry_path is not None
        decoded = decoded_entry_path.read_bytes()
        verification = {
            "mode": "exact-decoded-entry",
            "archive_sha256_verified_this_run": False,
            "decoded_sha256_verified_this_run": True,
        }

    rate_hz = _parse_tick_rate(decoded, expected_decoded_sha)
    with localcontext() as ctx:
        ctx.prec = 50
        reciprocal = Decimal(1) / Decimal(rate_hz)
    reciprocal_text = format(reciprocal, "f")
    reciprocal_float = float(reciprocal)
    if not math.isfinite(reciprocal_float) or reciprocal_float <= 0.0:
        raise ValueError("derived PhysicsTweaker reciprocal is invalid")

    return {
        "format": FORMAT,
        "version": 1,
        "status": "selected-session-physics-tweaker-rate-ready",
        "ready": True,
        "resource_identity": identity,
        "verification": verification,
        "selected_session_rate": {
            "property": PROPERTY_NAME,
            "rate_hz": rate_hz,
            "inner_substep_seconds_decimal": reciprocal_text,
            "inner_substep_seconds": reciprocal_float,
            "runtime_rate_global": "DAT_00c130d2",
            "cPhysicsManager_rate_offset": "0x388",
        },
        "cadence_join": {
            "format": CADENCE_FORMAT,
            "outer_scheduler_cadence_admitted": True,
            "inner_fixed_step_1_over_rate_proven": True,
            "normal_outer_increment_seconds": cadence["fixed_step_accumulator"][
                "normal_outer_increment_seconds"
            ],
        },
        "handoff": {
            "loaded_inner_physics_rate_admitted": True,
            "retail_inner_substep_execution_admitted": False,
            "consumer": "RetailOuterSchedulerContract::admit_loaded_inner_rate(rate_hz)",
            "next_step": "consume the exact rate in the native retail scheduler and execute accumulator-driven persistent BODY inner substeps",
        },
        "limits": {
            "constructor_default_180_used_as_selected_session_value": False,
            "community_or_modded_value_used": False,
            "host_1_60_used_as_inner_rate": False,
            "worker_poll_10ms_used_as_inner_rate": False,
            "rendered_frame_equivalence_claimed": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometry-contract",
        type=Path,
        default=ROOT / "evidence/bmw_offset33b_selector_geometry_inputs.json",
    )
    parser.add_argument(
        "--cadence-contract",
        type=Path,
        default=ROOT / "evidence/s5_retail_outer_update_cadence.json",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path)
    source.add_argument("--decoded-entry", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = materialize(
        args.geometry_contract,
        args.cadence_contract,
        archive_path=args.archive,
        decoded_entry_path=args.decoded_entry,
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
