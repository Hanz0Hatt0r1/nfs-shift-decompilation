"""Single readiness gate for a captured BMW render state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bmw_runtime_parity import validate_files as validate_runtime_parity_files
from bmw_runtime_draw_correlation import correlate_runtime_draw
from bmw_runtime_shader_join import _runtime_draw_states
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

    # The shader/parity join and the material draw-range join must identify the
    # same runtime draw. Matching only by frame would reintroduce the exact
    # cross-draw ambiguity that Phase 184 removed downstream.
    parity_draws = {
        (row.get('frame'), row.get('draw_index'))
        for row in (parity.get('shader_join', {}).get('candidate_frames') or [])
    }
    draw_matches = {
        (row.get('frame'), row.get('draw_index'))
        for row in (draw_correlation.get('matches') or [])
    }
    if parity_draws and draw_matches and not parity_draws.intersection(draw_matches):
        reasons.append('runtime-draw:shader-and-material-range-mismatch')

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

    same_instance_gate = runtime.get('same_instance_gate') or {}
    if same_instance_gate.get('ready') is not True:
        reasons.extend(
            'runtime-same-instance:' + str(reason)
            for reason in (same_instance_gate.get('blocking_reasons') or ['not-proven'])
        )
    matched_candidates = parity.get('shader_join', {}).get('candidate_frames') or []
    runtime_states = list(_runtime_draw_states(runtime))
    matched_state_count = 0
    for candidate in matched_candidates:
        frame_id = candidate.get('frame')
        draw_index = candidate.get('draw_index')
        state = None
        if draw_index is not None:
            state = next(
                (
                    snapshot
                    for frame, snapshot, source in runtime_states
                    if frame.get('frame') == frame_id
                    and source == 'draw-snapshot'
                    and snapshot.get('draw_index') == draw_index
                ),
                None,
            )
        else:
            state = next((frame for frame in runtime.get('frames') or [] if frame.get('frame') == frame_id), None)
        if state is None:
            reasons.append(f"runtime-frame:{frame_id}:matched-state-missing")
            continue
        matched_state_count += 1
        missing = []
        binding = state.get('vertex_declaration') or {}
        if not binding.get('create_known'):
            missing.append('declaration')
        for key in ('vertex_shader', 'pixel_shader'):
            if not (state.get(key) or {}).get('create_known'):
                missing.append(key)
        if not state.get('stream_sources'):
            missing.append('stream')
        if not state.get('index_binding'):
            missing.append('indices')
        if not state.get('draw') and not state.get('draws'):
            missing.append('draw')
        if missing:
            reasons.append(f"runtime-frame:{frame_id}:{draw_index if draw_index is not None else 'aggregate'}:state-incomplete")
    if parity.get('matched_frame_count') and not matched_state_count:
        reasons.append('runtime-frame:matched-state-missing')
    if isinstance(command, dict):
        constant_parity = validate_render_command_constant_parity(command)
        reasons.extend(constant_parity.get('blocking_reasons') or [])
        has_constant_bindings = any(
            bool((submesh.get('uniforms') or {}).get('bindings'))
            for submesh in command.get('submeshes', []) or []
            if isinstance(submesh, dict)
        )
        if has_constant_bindings and constant_parity.get('ready') is not True:
            reasons.append('render-command:constant-parity-not-ready')
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
        'runtime_same_instance_gate': same_instance_gate,
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
            'same_instance_gate': 'required',
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