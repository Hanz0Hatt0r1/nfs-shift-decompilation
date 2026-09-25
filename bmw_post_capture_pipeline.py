"""Run the complete BMW post-capture evidence/render pipeline.

The command intentionally preserves every boundary:
BFF -> material binding -> runtime trace -> exact shader selection ->
runtime render contract -> offline shader render.

A blocked stage still writes its report and returns a non-zero status; no
runtime resource identity is fabricated to make a render appear ready.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bff_meb_render import find_meb_entry
from bmw_material_from_bff import build_real_bmw_material_binding
from bmw_runtime_render_contract import build_runtime_render_contract
from bmw_runtime_shader_select import select_runtime_shader
from bmw_runtime_shader_render import render_runtime_shader
from d3d9_runtime_trace import build_runtime_binding_evidence, load_events
from meb_format import mesh_to_jsonable, read_meb
from shift_importer import BFF


FORMAT = "SHIFT.BMWPostCapturePipeline/1"
TARGET_MEB = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_target_mesh(primary_bff: str | Path) -> tuple[dict[str, Any], bytes]:
    with BFF(primary_bff) as archive:
        entry = find_meb_entry(archive, TARGET_MEB)
        data = archive.extract_entry(entry, type2="lzx")
    mesh = read_meb(data)
    return mesh_to_jsonable(mesh), data


def run_pipeline(
    primary_bff: str | Path,
    render_bff: str | Path,
    runtime_capture: str | Path,
    output_dir: str | Path,
    *,
    usage_map: dict[int, int] | None = None,
    snapshot_root: str | Path | None = None,
    allow_resource_mismatch: bool = False,
    render_width: int = 1200,
    render_height: int = 800,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    material = build_real_bmw_material_binding(
        primary_bff,
        supplemental_bffs=[render_bff],
    )
    _write(out / "material_binding.json", material)

    mesh, meb_bytes = _load_target_mesh(primary_bff)
    _write(out / "mesh.json", mesh)

    events = load_events(runtime_capture)
    runtime = build_runtime_binding_evidence(
        events,
        meb_resource={
            "resource": TARGET_MEB,
            "resource_sha256": __import__("hashlib").sha256(meb_bytes).hexdigest(),
            "property_descriptors": mesh.get("property_descriptors", []),
        },
        usage_ordinal_map=usage_map,
    )
    _write(out / "runtime_binding.json", runtime)

    selection = select_runtime_shader(
        material,
        runtime,
        require_same_resource=not allow_resource_mismatch,
    )
    _write(out / "runtime_shader_selection.json", selection)

    result: dict[str, Any] = {
        "format": FORMAT,
        "status": "blocked",
        "ready": False,
        "stages": {
            "material_binding": material.get("status"),
            "runtime_trace": runtime.get("status"),
            "runtime_same_instance_gate": (runtime.get("same_instance_gate") or {}).get("status", "not-proven"),
            "shader_selection": selection.get("status"),
            "runtime_render_contract": "not-run",
            "shader_render": "not-run",
        },
        "output_dir": str(out),
    }

    if not selection.get("ready"):
        result["blocking_reasons"] = list(selection.get("blocking_reasons") or [])
        _write(out / "pipeline_result.json", result)
        return result

    same_instance = runtime.get("same_instance_gate") or {}
    if same_instance.get("ready") is not True:
        result["blocking_reasons"] = [
            "runtime-same-instance:" + str(reason)
            for reason in (same_instance.get("blocking_reasons") or ["not-proven"])
        ]
        _write(out / "pipeline_result.json", result)
        return result

    contract = build_runtime_render_contract(
        material,
        runtime,
        primary_bff=primary_bff,
        render_bff=render_bff,
    )
    _write(out / "runtime_render_contract.json", contract)
    result["stages"]["runtime_render_contract"] = contract.get("status")

    if contract.get("reference_render_ready") is not True:
        result["blocking_reasons"] = list(contract.get("blocking_reasons") or [])
        _write(out / "pipeline_result.json", result)
        return result

    snapshot_dir = snapshot_root if snapshot_root is not None else out
    rendered = render_runtime_shader(
        out / "runtime_render_contract.json",
        out / "material_binding.json",
        out / "mesh.json",
        primary_bff,
        out / "bmw_m3_e36_shader_executed.ppm",
        snapshot_root=snapshot_dir,
        width=render_width,
        height=render_height,
    )
    _write(out / "shader_render_result.json", rendered)
    result.update({
        "status": rendered.get("status"),
        "ready": True,
        "stages": {
            **result["stages"],
            "shader_render": rendered.get("status"),
        },
        "render": rendered,
    })
    _write(out / "pipeline_result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete BMW post-capture evidence/render pipeline"
    )
    parser.add_argument("primary_bff")
    parser.add_argument("render_bff")
    parser.add_argument("runtime_capture")
    parser.add_argument("output_dir")
    parser.add_argument("--usage-map")
    parser.add_argument("--snapshot-root")
    parser.add_argument("--allow-resource-mismatch", action="store_true")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args(argv)

    usage_map = None
    if args.usage_map:
        raw = json.loads(Path(args.usage_map).read_text(encoding="utf-8"))
        usage_map = {int(key): int(value) for key, value in raw.items()}

    result = run_pipeline(
        args.primary_bff,
        args.render_bff,
        args.runtime_capture,
        args.output_dir,
        usage_map=usage_map,
        snapshot_root=args.snapshot_root,
        allow_resource_mismatch=args.allow_resource_mismatch,
        render_width=args.width,
        render_height=args.height,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
