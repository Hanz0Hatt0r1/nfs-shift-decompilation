"""Render an already-selected BMW material slice through the desktop oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.BMWReferenceRender/1"

def render_material_slice(
    material_slice: dict[str, Any],
    mesh: dict[str, Any],
    output: str | Path,
    *,
    width: int = 512,
    height: int = 512,
    shader_reference: bool = False,
    texture_image: dict[str, Any] | None = None,
    shader_constants: dict[str, dict[int, Iterable[float]]] | None = None,
) -> dict[str, Any]:
    if material_slice.get('format') != 'SHIFT.BMWMaterialSlice/1':
        raise ValueError('input is not SHIFT.BMWMaterialSlice/1')
    if not material_slice.get('ready'):
        raise ValueError('BMW material slice is not ready: ' + ', '.join(material_slice.get('blocking_reasons') or []))
    command = material_slice.get('render_command')
    if not isinstance(command, dict):
        raise ValueError('BMW material slice has no RenderCommand/1')
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if shader_reference:
        if texture_image is None:
            raise ValueError('shader_reference requires an explicit texture image')
        from reference_renderer import render_textured_render_command
        result = render_textured_render_command(
            command, mesh, texture_image, out, width=width, height=height,
            shader_reference=True, shader_constants=shader_constants,
        )
    else:
        from reference_renderer import render_render_command
        result = render_render_command(command, mesh, out, width=width, height=height)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        'format': FORMAT,
        'status': 'rendered',
        'output': str(out),
        'width': width, 'height': height,
        'sha256': digest,
        'primitive_index': material_slice.get('primitive_index'),
        'material_ref': material_slice.get('material_ref'),
        'shader_reference': shader_reference,
        'reference_result': result,
    }

def render_files(slice_path: str | Path, mesh_path: str | Path, output: str | Path, *, width: int = 512, height: int = 512, shader_reference: bool = False, texture_path: str | Path | None = None) -> dict[str, Any]:
    material_slice = json.loads(Path(slice_path).read_text(encoding='utf-8'))
    mesh = json.loads(Path(mesh_path).read_text(encoding='utf-8'))
    texture = json.loads(Path(texture_path).read_text(encoding='utf-8')) if texture_path else None
    return render_material_slice(material_slice, mesh, output, width=width, height=height, shader_reference=shader_reference, texture_image=texture)

def main() -> int:
    ap = argparse.ArgumentParser(description='Render one ready BMW material slice through the desktop reference renderer')
    ap.add_argument('slice')
    ap.add_argument('mesh')
    ap.add_argument('output')
    ap.add_argument('--width', type=int, default=512)
    ap.add_argument('--height', type=int, default=512)
    ap.add_argument('--shader-reference', action='store_true')
    ap.add_argument('--texture-json')
    args = ap.parse_args()
    result = render_files(args.slice, args.mesh, args.output, width=args.width, height=args.height, shader_reference=args.shader_reference, texture_path=args.texture_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())