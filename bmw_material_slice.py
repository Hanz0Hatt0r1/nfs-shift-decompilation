"""Extract one deterministic BMW M3 material/submesh from a BMWRenderSlice/1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWMaterialSlice/1"

def _norm(value: Any) -> str:
    return str(value or '').replace('\\', '/').strip('/').lower()

def select_material_slice(slice_report: Mapping[str, Any], *, primitive_index: int = 0) -> dict[str, Any]:
    if slice_report.get('format') != 'SHIFT.BMWRenderSlice/1':
        raise ValueError('input is not SHIFT.BMWRenderSlice/1')
    if not slice_report.get('ready'):
        return {
            'format': FORMAT, 'status': 'blocked', 'ready': False,
            'blocking_reasons': ['render-slice:not-ready'],
            'primitive_index': primitive_index, 'material': None, 'render_command': None,
        }
    packet = slice_report.get('packet') or {}
    packet_mesh = packet.get('mesh') or {}
    submeshes = packet.get('submeshes') or []
    if primitive_index < 0 or primitive_index >= len(submeshes):
        raise IndexError(f'primitive index out of range: 0..{len(submeshes)-1}')
    submesh = submeshes[primitive_index] or {}
    material = submesh.get('material') or {}
    selection = material.get('shader_selection') or {}
    reasons = []
    status = selection.get('status') or selection.get('selection_status', 'none')
    if status != 'unique':
        reasons.append(f'shader-selection:{status}')
    pair = selection.get('shader_pair') or material.get('shader_pair') or {}
    if not pair:
        reasons.append('shader-pair:missing')
    elif pair.get('selection_status', 'none') != 'unique':
        reasons.append(f"shader-pair-selection:{pair.get('selection_status', 'none')}")
    linked = selection.get('linked_shader_pair') or material.get('linked_shader_pair')
    if not linked:
        reasons.append('shader-glsl:missing')
    if status == 'unique' and not selection.get('permutation_identity') and not material.get('permutation_identity'):
        reasons.append('shader-permutation-identity:missing')
    if selection.get('linked_shader_error') or material.get('linked_shader_error'):
        reasons.append('shader-glsl:error')
    if not material.get('resolved'):
        reasons.append('material:unresolved')
    textures = material.get('textures') or material.get('bindings') or []
    for texture in textures:
        binding = texture.get('binding_source') or texture.get('binding')
        if binding == 'material-texture' and texture.get('d3d9_sampler_register') is None:
            reasons.append('texture:sampler-register-missing')
    render_command = slice_report.get('render_command')
    if isinstance(render_command, Mapping) and render_command.get('ready') is False:
        reasons.extend(render_command.get('blocking_reasons') or ['render-command:not-ready'])
    golden_identity = slice_report.get('golden_identity') or {}
    return {
        'format': FORMAT,
        'status': 'match' if not reasons else 'blocked',
        'ready': not reasons,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'primitive_index': primitive_index,
        'golden_identity': golden_identity,
        'mesh': packet_mesh,
        'material_ref': submesh.get('material_ref') or material.get('ref'),
        'material': material,
        'shader_selection': selection,
        'textures': textures,
        'uniform_binding': selection.get('uniform_binding') or material.get('uniform_binding'),
        'render_command': render_command,
    }

def validate_files(slice_path: str | Path, *, primitive_index: int = 0) -> dict[str, Any]:
    report = json.loads(Path(slice_path).read_text(encoding='utf-8'))
    return select_material_slice(report, primitive_index=primitive_index)

def main() -> int:
    ap = argparse.ArgumentParser(description='Extract one BMW M3 material draw from SHIFT.BMWRenderSlice/1')
    ap.add_argument('slice')
    ap.add_argument('output')
    ap.add_argument('--primitive-index', type=int, default=0)
    args = ap.parse_args()
    report = validate_files(args.slice, primitive_index=args.primitive_index)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'format': report['format'], 'status': report['status'], 'ready': report['ready'], 'primitive_index': report['primitive_index']}, ensure_ascii=False, indent=2))
    return 0 if report['ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())