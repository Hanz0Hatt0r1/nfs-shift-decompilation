"""Run the complete BMW M3 runtime-capture evidence pipeline in one command.

Pipeline:
  retail BFFs -> real MaterialBinding -> captured JSONL runtime evidence
  -> exact FXO selection -> runtime RenderContract -> optional texture references.

Every stage keeps its own versioned report so partial/blocked evidence is still
useful. No runtime pointer is converted into a guessed resource identity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from bmw_material_from_bff import build_real_bmw_material_binding
from bmw_runtime_render_contract import build_runtime_render_contract
from bmw_runtime_shader_select import select_runtime_shader
from d3d9_runtime_trace import build_runtime_binding_evidence, load_events
from ppm_svg_snapshot import read_ppm
from runtime_texture_reference import ppm_to_reference_texture

FORMAT = "SHIFT.BMWRuntimeCapturePipeline/1"
DEFAULT_MEB_EVIDENCE = "evidence/bmw_m3_e36_kit00_body_loda.meb.json"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _load_usage_map(path: str | Path | None) -> dict[int, int] | None:
    if path is None:
        return None
    value = _load_json(path)
    raw = value.get("usage_map") if isinstance(value.get("usage_map"), dict) else value
    if not isinstance(raw, dict):
        raise ValueError("usage map must be an object")
    return {int(key): int(item) for key, item in raw.items()}


def _load_meb_evidence(path: str | Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") == "SHIFT.BMWGoldenAssetManifest/1":
        golden = report.get("golden") or {}
        mesh = report.get("mesh") or {}
        return {
            "resource": golden.get("resource"),
            "resource_sha256": golden.get("resource_sha256"),
            "property_descriptors": mesh.get("property_descriptors") or [],
        }
    source = report.get("source") or {}
    mesh = report.get("mesh") or {}
    return {
        "resource": source.get("root_relative_path") or report.get("resource"),
        "resource_sha256": source.get("resource_sha256") or report.get("resource_sha256"),
        "property_descriptors": mesh.get("property_descriptors") or report.get("property_descriptors") or [],
    }


def _texture_snapshot_inventory(runtime_report: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for frame in runtime_report.get("frames") or []:
        if not isinstance(frame, Mapping):
            continue
        for binding in frame.get("texture_bindings") or []:
            if not isinstance(binding, Mapping):
                continue
            paths = binding.get("resource_snapshot_paths") or []
            for path in paths:
                if isinstance(path, str):
                    rows.append({
                        "frame": frame.get("frame"),
                        "stage": binding.get("stage"),
                        "texture_ptr": binding.get("texture_ptr"),
                        "path": path,
                    })
    converted = []
    for row in rows:
        path = Path(row["path"])
        if not path.is_file():
            continue
        try:
            image = ppm_to_reference_texture(path)
        except (OSError, ValueError):
            continue
        converted.append({
            **row,
            "reference_format": image["format"],
            "width": image["width"],
            "height": image["height"],
            "byte_size": image["byte_size"],
            "source_path": image["source_path"],
        })
    return {
        "capture_snapshot_count": len(rows),
        "converted_snapshot_count": len(converted),
        "snapshots": converted,
    }


def build_pipeline(
    primary_bff: str | Path,
    render_bff: str | Path,
    capture_jsonl: str | Path,
    *,
    cockpit_bff: str | Path | None = None,
    meb_evidence: str | Path = DEFAULT_MEB_EVIDENCE,
    usage_map: str | Path | None = None,
    require_same_instance: bool = False,
) -> dict[str, Any]:
    primary = Path(primary_bff)
    render = Path(render_bff)
    supplemental = [cockpit_bff] if cockpit_bff else []

    material = build_real_bmw_material_binding(
        primary,
        supplemental_bffs=[render, *supplemental],
    )

    meb = _load_meb_evidence(meb_evidence)
    usage = _load_usage_map(usage_map)
    runtime = build_runtime_binding_evidence(
        load_events(capture_jsonl),
        meb_resource=meb,
        usage_ordinal_map=usage,
    )

    selection = select_runtime_shader(material, runtime)

    contract = build_runtime_render_contract(
        material,
        runtime,
        primary_bff=primary,
        render_bff=render,
    )

    snapshots = _texture_snapshot_inventory(runtime)
    ready = (
        material.get("ready") is True
        and selection.get("ready") is True
        and contract.get("reference_render_ready") is True
    )
    blockers = []
    for report in (material, runtime, selection, contract):
        blockers.extend(report.get("blocking_reasons") or [])
    if require_same_instance and runtime.get("same_instance_gate", {}).get("ready") is not True:
        blockers.extend(
            "runtime-same-instance:" + str(reason)
            for reason in runtime.get("same_instance_gate", {}).get("blocking_reasons", [])
        )

    return {
        "format": FORMAT,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "inputs": {
            "primary_bff": str(primary),
            "render_bff": str(render),
            "capture_jsonl": str(capture_jsonl),
            "cockpit_bff": str(cockpit_bff) if cockpit_bff else None,
            "meb_evidence": str(meb_evidence),
            "usage_map": str(usage_map) if usage_map else None,
        },
        "material_binding": material,
        "runtime_evidence": runtime,
        "shader_selection": selection,
        "runtime_render_contract": contract,
        "texture_snapshots": snapshots,
        "next_gate": {
            "shader_execution": (
                "ready"
                if contract.get("reference_render_ready") is True
                else "blocked"
            ),
            "runtime_game_capture": (
                "proven"
                if runtime.get("same_instance_gate", {}).get("ready") is True
                else "not-proven"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete BMW M3 runtime capture -> shader selection pipeline"
    )
    parser.add_argument("primary_bff")
    parser.add_argument("render_bff")
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument("--cockpit-bff")
    parser.add_argument("--meb-evidence", default=DEFAULT_MEB_EVIDENCE)
    parser.add_argument("--usage-map")
    parser.add_argument("--require-same-instance", action="store_true")
    args = parser.parse_args(argv)

    report = build_pipeline(
        args.primary_bff,
        args.render_bff,
        args.capture_jsonl,
        cockpit_bff=args.cockpit_bff,
        meb_evidence=args.meb_evidence,
        usage_map=args.usage_map,
        require_same_instance=args.require_same_instance,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "material_ready": report["material_binding"].get("ready"),
        "runtime_status": report["runtime_evidence"].get("status"),
        "shader_selection_status": report["shader_selection"].get("status"),
        "reference_render_ready": report["runtime_render_contract"].get("reference_render_ready"),
        "texture_snapshot_count": report["texture_snapshots"]["converted_snapshot_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
