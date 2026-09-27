"""Extract and parse a complete vehicle physics bundle from a SHIFT BFF archive."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from shift_importer import BFF
from vehicle_physics_asset_graph_runtime import build_profile
from turbo_runtime import parse_turbo_bbf, parse_turbo_tbf

FORMAT = "SHIFT.VehiclePhysicsBundleExtractor/1"

DEFAULT_TARGETS = {
    "cdf": "vehicles/physics/chassis/bmw_m3_e36.cdf",
    "edf": "vehicles/physics/engines/bmw_m3_e36.edf",
    "gdf": "vehicles/physics/gearbox/common.gdf",
    "sdf": "vehicles/physics/suspension/aarm_multilink.sdf",
    "tbf": "vehicles/physics/turbo/gen_lowrpm_33.tbf",
    "bbf": "vehicles/physics/turbo/nitrous.bbf",
}


def _find_entry(archive: BFF, wanted: str):
    wanted = wanted.replace("\\", "/").lower()
    hits = [entry for entry in archive.entries if entry.path.replace("\\", "/").lower() == wanted]
    if not hits:
        basename = Path(wanted).name
        hits = [
            entry for entry in archive.entries
            if Path(entry.path.replace("\\", "/")).name.lower() == basename
        ]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one BFF entry for {wanted!r}, found {len(hits)}")
    return hits[0]


def extract_bundle(
    bff_path: str | Path,
    output_dir: str | Path,
    *,
    targets: Mapping[str, str] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    bff_path = Path(bff_path)
    output_dir = Path(output_dir)
    targets = dict(targets or DEFAULT_TARGETS)
    output_dir.mkdir(parents=True, exist_ok=True)
    resource_dir = output_dir / "resources"
    resource_dir.mkdir(parents=True, exist_ok=True)

    extracted: dict[str, Path] = {}
    entries: dict[str, Any] = {}

    with BFF(bff_path) as archive:
        for kind in ("cdf", "edf", "gdf", "sdf", "tbf", "bbf"):
            wanted = targets[kind]
            entry = _find_entry(archive, wanted)
            payload = archive.extract_entry(entry, type2="lzx")
            destination = resource_dir / Path(entry.path).name
            destination.write_bytes(payload)
            extracted[kind] = destination
            entries[kind] = {
                "requested_path": wanted,
                "archive_path": entry.path,
                "index": int(entry.index),
                "type": int(entry.type),
                "compressed_size": int(entry.compressed_size),
                "uncompressed_size": int(entry.uncompressed_size),
                "decoded_size": len(payload),
            }

    profile = build_profile(
        cdf=extracted["cdf"],
        edf=extracted["edf"],
        gdf=extracted["gdf"],
        sdf=extracted["sdf"],
        strict=strict,
    )
    turbo_tbf = parse_turbo_tbf(extracted["tbf"].read_bytes(), strict=strict)
    turbo_bbf = parse_turbo_bbf(extracted["bbf"].read_bytes(), max_value=None)
    profile = dict(profile)
    profile["turbo"] = {"tbf": turbo_tbf, "bbf": turbo_bbf}
    if turbo_tbf.get("ready") is not True:
        profile["blockers"] = list(profile.get("blockers", [])) + ["turbo-tbf:parse-not-ready"]
    if turbo_bbf.get("ready") is not True:
        profile["blockers"] = list(profile.get("blockers", [])) + ["turbo-bbf:parse-not-ready"]
    profile["ready"] = bool(profile.get("ready")) and turbo_tbf.get("ready") is True and turbo_bbf.get("ready") is True
    profile["status"] = "ready" if profile["ready"] else "ready-with-warnings"
    result = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if profile["ready"] else "ready-with-warnings",
        "ready": profile["ready"],
        "source": {
            "bff": str(bff_path),
            "bytes": bff_path.stat().st_size,
        },
        "entries": entries,
        "extracted_paths": {key: str(value) for key, value in extracted.items()},
        "physics_profile": str(output_dir / "vehicle_physics_asset_graph.json"),
        "profile": profile,
    }
    (output_dir / "vehicle_physics_asset_graph.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract and parse BMW/SHIFT vehicle physics resources from a BFF")
    parser.add_argument("bff", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    result = extract_bundle(args.bff, args.output, strict=args.strict)
    (args.output / "bundle_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": result["format"],
        "status": result["status"],
        "ready": result["ready"],
        "entries": result["entries"],
        "extracted_paths": result["extracted_paths"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
