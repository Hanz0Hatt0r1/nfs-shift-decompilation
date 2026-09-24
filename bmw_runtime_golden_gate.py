"""Single readiness gate for a captured BMW render state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bmw_runtime_parity import validate_files as validate_runtime_parity_files
from bmw_runtime_draw_correlation import correlate_runtime_draw
from bmw_vertex_input_parity import validate_bmw_vertex_input_parity
from render_command_constant_parity import validate_render_command_constant_parity

FORMAT = "SHIFT.BMWRuntimeGoldenGate/1"

def validate_runtime_golden_gate(material_path: str | Path, runtime_path: str | Path, *, usage_map_path: str | Path | None = None) -> dict[str, Any]:
    material = json.loads(Path(material_path).read_text(encoding='utf-8'))
    runtime = json.loads(Path(runtime_path).read_text(encoding='utf-8'))
    parity = validate_runtime_parity_files(material_path, runtime_path, usage_map_path=usage_map_path, require_constant_values=True)
    draw_correlation = correlate_runtime_draw(material, runtime)
    reasons = list(parity.get('blocking_reasons') or [])
    reasons.extend(draw_correlation.get('blocking_reasons') or [])

    # Vertex-input parity is evaluated below only when an explicit Usage map is supplied by the caller.
    if usage_map_path:
        usage_raw = json.loads(Path(usage_map_path).read_text(encoding='utf-8'))
        if isinstance(usage_raw, dict) and isinstance(usage_raw.get('usage_map'), dict):
            usage_raw = usage_raw.get('usage_map')
        usage_map = {int(k): int(v) for k, v in usage_raw.items()} if isinstance(usage_raw, dict) else None
        vertex_input_parity = validate_bmw_vertex_input_parity(material, runtime, usage_map=usage_map)
    else:
        vertex_input_parity = {
            'format': 'SHIFT.BMWVertexInputParity/1',
            'status': 'not-supplied',
            'ready': False,
            'blocking_reasons': ['vertex-input:usage-map-missing'],
        }
    reasons.extend(vertex_input_parity.get('blocking_reasons') or [])

    command = material.get('render_command')
    command_status = 'not-supplied'
    constant_parity = None
    integrity = runtime.get('integrity') or {}
    if integrity.get('status') != 'observed':
        reasons.append('runtime-trace:integrity-not-proven')
    matched_frame_ids = {
        row.get('frame')
        for row in (parity.get('shader_join', {}).get('candidate_frames') or [])
    }
    runtime_frames = [
        frame for frame in runtime.get('frames') or []
        if frame.get('frame') in matched_frame_ids
    ]
    for frame in runtime_frames:
        missing = []
        binding = frame.get('vertex_declaration') or {}
        if not binding.get('create_known'):
            missing.append('declaration')
        for key in ('vertex_shader', 'pixel_shader'):
            if not (frame.get(key) or {}).get('create_known'):
                missing.append(key)
        if not frame.get('stream_sources'):
            missing.append('stream')
        if not frame.get('index_binding'):
            missing.append('indices')
        if not frame.get('draws'):
            missing.append('draw')
        if missing:
            reasons.append(f"runtime-frame:{frame.get('frame')}:state-incomplete")
    if parity.get('matched_frame_count') and not runtime_frames:
        reasons.append('runtime-frame:matched-frame-missing')
    if isinstance(command, dict):
        constant_parity = validate_render_command_constant_parity(command)
        reasons.extend(constant_parity.get('blocking_reasons') or [])
        command_status = 'ready' if command.get('ready') is True else 'blocked'
        if command.get('ready') is not True:
            reasons.extend(command.get('blocking_reasons') or ['render-command:not-ready'])
    else:
        reasons.append('render-command:missing')
        command_status = 'missing'
    ready = bool(parity.get('ready') and command_status == 'ready' and not reasons)
    return {
        'format': FORMAT,
        'status': 'ready' if ready else 'blocked',
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'runtime_parity': parity,
        'runtime_draw_correlation': draw_correlation,
        'vertex_input_parity': vertex_input_parity,
        'render_command_constant_parity': constant_parity,
        'render_command': {'status': command_status},
        'golden_requirements': {
            'shader_identity': 'required',
            'resource_identity': 'required',
            'sampler_parity': 'required',
            'constant_register_parity': 'required',
            'constant_value_parity': 'required',
            'meb_descriptor_parity': 'required',
            'declaration_parity': 'required',
            'vertex_input_parity': 'required',
            'draw_correlation': 'required',
            'render_command_constant_parity': 'required',
        },
    }

def main() -> int:
    ap = argparse.ArgumentParser(description='Gate a BMW golden render on full runtime parity')
    ap.add_argument('material_slice')
    ap.add_argument('runtime_report')
    ap.add_argument('output')
    ap.add_argument('--usage-map')
    args = ap.parse_args()
    report = validate_runtime_golden_gate(args.material_slice, args.runtime_report, usage_map_path=args.usage_map)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'format': report['format'], 'status': report['status'], 'ready': report['ready'], 'blocking_reasons': report['blocking_reasons']}, ensure_ascii=False, indent=2))
    return 0 if report['ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())