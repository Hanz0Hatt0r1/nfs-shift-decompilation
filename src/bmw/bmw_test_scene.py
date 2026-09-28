"""Render a reproducible BMW M3 E36 KIT00 VHF test scene."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from vhf_scene_preview import _render_scene_ppm, build_vhf_scene

FORMAT = "SHIFT.BMWM3TestScene/1"

VIEW_PRESETS = (
    {"name": "front_left", "yaw_deg": -28.0, "pitch_deg": -15.0},
    {"name": "rear_right", "yaw_deg": 152.0, "pitch_deg": -12.0},
    {"name": "side", "yaw_deg": -90.0, "pitch_deg": -10.0},
    {"name": "front", "yaw_deg": 0.0, "pitch_deg": -8.0},
)


def _archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_test_scene(
    archive: str | Path,
    *,
    kit: str = "00",
    lod: str = "A",
) -> dict[str, Any]:
    archive_path = Path(archive)
    scene = build_vhf_scene(
        archive_path,
        "vehicles/bmw_m3_e36/bmw_m3_e36.vhf",
        kit=kit,
        lod=lod,
        include_generic=True,
        include_lightglows=False,
    )
    body_parts = [
        part
        for part in scene["parts"]
        if part["resource"].lower()
        == "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
    ]
    return {
        "format": FORMAT,
        "status": "ready",
        "ready": True,
        "source": {
            "archive": archive_path.name,
            "archive_sha256": _archive_sha256(archive_path),
            "vhf_resource": scene["vhf_resource"],
            "kit": kit,
            "lod": lod,
        },
        "renderer": {
            "format": "SHIFT.VHFSceneReferenceRender/1",
            "mode": "geometry-preview",
            "material_execution": False,
            "runtime_capture_required": False,
        },
        "vehicle": {
            "part_count": len(scene["parts"]),
            "body_part_count": len(body_parts),
            "parts": [
                {
                    "name": part["name"],
                    "resource": part["resource"],
                    "resource_sha256": part["resource_sha256"],
                    "vertex_count": part["mesh"].vertex_count,
                    "triangle_count": part["mesh"].triangle_count,
                }
                for part in scene["parts"]
            ],
        },
        "cameras": list(VIEW_PRESETS),
    }


def render_test_scene(
    archive: str | Path,
    output_dir: str | Path,
    *,
    kit: str = "00",
    lod: str = "A",
    width: int = 1600,
    height: int = 900,
) -> dict[str, Any]:
    scene = build_vhf_scene(
        archive,
        "vehicles/bmw_m3_e36/bmw_m3_e36.vhf",
        kit=kit,
        lod=lod,
        include_generic=True,
        include_lightglows=False,
    )
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_test_scene(archive, kit=kit, lod=lod)
    outputs = []
    for view in VIEW_PRESETS:
        image = _render_scene_ppm(
            scene,
            width=width,
            height=height,
            yaw_deg=view["yaw_deg"],
            pitch_deg=view["pitch_deg"],
        )
        path = out_dir / f'{view["name"]}.ppm'
        path.write_bytes(image)
        outputs.append(
            {
                "name": view["name"],
                "path": str(path),
                "sha256": hashlib.sha256(image).hexdigest(),
            }
        )
    manifest["render"] = {
        "width": width,
        "height": height,
        "outputs": outputs,
    }
    (out_dir / "scene.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render BMW M3 E36 KIT00 test scene")
    parser.add_argument("archive", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--kit", default="00")
    parser.add_argument("--lod", default="A")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args(argv)
    report = render_test_scene(
        args.archive,
        args.output_dir,
        kit=args.kit,
        lod=args.lod,
        width=args.width,
        height=args.height,
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "part_count": report["vehicle"]["part_count"],
                "outputs": report.get("render", {}).get("outputs", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
