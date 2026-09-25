"""Correlate an exact BMW material slice with a captured runtime shader state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from runtime_resource_identity import match_resource_identity
from d3d9_draw_snapshot_schema import validate_draw_snapshot

FORMAT = "SHIFT.BMWRuntimeShaderJoin/1"

def _identity_from_material(material_slice: Mapping[str, Any]) -> Mapping[str, Any] | None:
    material = material_slice.get('material') or {}
    selection = material_slice.get('shader_selection') or {}
    return selection.get('permutation_identity') or material.get('permutation_identity')

def _expected_draw_range(material_slice: Mapping[str, Any]) -> tuple[int, int] | None:
    command = material_slice.get("render_command") or {}
    submeshes = command.get("submeshes") or []
    if not submeshes:
        return None
    primitive_index = material_slice.get("primitive_index")
    if primitive_index is None and len(submeshes) == 1:
        primitive_index = 0
    if primitive_index is None:
        return None
    try:
        primitive_index = int(primitive_index)
    except (TypeError, ValueError):
        return None
    rows = [
        row for row in submeshes
        if isinstance(row, Mapping) and int(row.get("index", -1)) == primitive_index
    ]
    if len(rows) != 1 and primitive_index < len(submeshes) and not rows:
        rows = [submeshes[primitive_index]]
    if len(rows) != 1:
        return None
    try:
        return int(rows[0].get("first_index")), int(rows[0].get("index_count"))
    except (TypeError, ValueError):
        return None


def _expected_sampler_registers(material_slice: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in material_slice.get('textures') or []:
        register = row.get('d3d9_sampler_register')
        if register is None:
            continue
        out[int(register)] = {
            'sampler': row.get('sampler'),
            'sampler_type': row.get('sampler_type'),
            'material_parameter': row.get('material_parameter'),
        }
    selection = material_slice.get('shader_selection') or {}
    for row in selection.get('external_samplers') or []:
        register = row.get('d3d9_sampler_register')
        if register is None:
            continue
        out[int(register)] = {
            'sampler': row.get('sampler'),
            'sampler_type': row.get('sampler_type'),
            'source': 'external',
        }
    return out

def _draw_matches_range(draw: Mapping[str, Any], expected: tuple[int, int]) -> bool:
    try:
        start_index = int(draw.get("start_index"))
        primitive_count = int(draw.get("primitive_count"))
    except (TypeError, ValueError):
        return False
    expected_first, expected_count = expected
    if expected_count % 3 != 0:
        return False
    return start_index == expected_first and primitive_count == expected_count // 3


def _runtime_draw_states(
    runtime_report: Mapping[str, Any],
    *,
    reject_invalid_snapshots: bool = False,
):
    """Yield the exact runtime state used by each draw.

    Current captures contain draw_snapshots. Legacy fixtures without them are
    accepted for compatibility, but an available snapshot set always wins so
    frame-level post-draw state can never be substituted for draw-local state.
    """
    frames = [
        frame for frame in (runtime_report.get("frames") or [])
        if isinstance(frame, Mapping)
    ]
    for frame in frames:
        snapshots = frame.get("draw_snapshots") or []
        if snapshots:
            for snapshot in snapshots:
                if not isinstance(snapshot, Mapping):
                    continue
                if reject_invalid_snapshots and snapshot.get("format") is not None:
                    if validate_draw_snapshot(snapshot):
                        continue
                yield frame, snapshot, "draw-snapshot"
        else:
            yield frame, frame, "frame-aggregate"


def join_runtime_shader(material_slice: Mapping[str, Any], runtime_report: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if runtime_report.get('format') != 'SHIFT.D3D9RuntimeBindingEvidence/1':
        raise ValueError('input is not SHIFT.D3D9RuntimeBindingEvidence/1')
    expected = _identity_from_material(material_slice)
    if not expected:
        reasons.append('material:permutation-identity-missing')
    expected_id = expected.get('identity_sha256') if expected else None
    golden_identity = material_slice.get('golden_identity') or {}
    expected_resource = str(golden_identity.get('resource') or '')
    expected_resource_sha = golden_identity.get('resource_sha256')
    expected_samplers = _expected_sampler_registers(material_slice)
    expected_draw_range = _expected_draw_range(material_slice)
    matches = []
    for frame, state, state_source in _runtime_draw_states(runtime_report, reject_invalid_snapshots=True):
        states = [(state, None)]
        if state_source == 'frame-aggregate' and expected_draw_range is not None:
            states = [
                (state, draw_index)
                for draw_index, draw in enumerate(state.get("draws") or [])
                if isinstance(draw, Mapping)
                and _draw_matches_range(draw, expected_draw_range)
            ]
        elif state_source == 'draw-snapshot' and expected_draw_range is not None:
            draw = state.get("draw") or {}
            if not _draw_matches_range(draw, expected_draw_range):
                states = []
        for current_state, legacy_draw_index in states:
            identity = current_state.get('shader_permutation_identity') or {}
            if not identity and state_source == 'frame-aggregate':
                identity = frame.get('shader_permutation_identity') or {}
            same_id = bool(expected_id and identity.get('identity_sha256') == expected_id)
            binding = current_state.get('vertex_declaration') or {}
            same_resource, _resource_status = match_resource_identity(
                binding,
                expected_sha256=expected_resource_sha,
                expected_path=expected_resource,
            )
            same_resource = same_resource is True
            if same_id and same_resource:
                if legacy_draw_index is not None:
                    current_state = {**current_state, "draw_index": legacy_draw_index, "draw": (current_state.get("draws") or [])[legacy_draw_index]}
                matches.append((frame, current_state, state_source))

    if expected_id and not matches:
        reasons.append('runtime:shader-or-resource-instance-not-found')
    candidate_rows = []
    for frame, state, state_source in matches:
        identity = state.get('shader_permutation_identity') or frame.get('shader_permutation_identity') or {}
        pixel = identity.get('payload', {}).get('pixel', {})
        runtime_samplers = {int(k): str(v) for k, v in (pixel.get('sampler_types') or {}).items()}
        sampler_mismatches = []
        for register, expected_row in expected_samplers.items():
            runtime_type = runtime_samplers.get(register)
            expected_type = expected_row.get('sampler_type')
            if runtime_type is None:
                sampler_mismatches.append({'register': register, 'reason': 'missing-runtime-sampler', 'expected_type': expected_type})
            elif expected_type and runtime_type != expected_type:
                sampler_mismatches.append({'register': register, 'reason': 'sampler-type-mismatch', 'expected_type': expected_type, 'runtime_type': runtime_type})
        runtime_set = set(runtime_samplers)
        expected_set = set(expected_samplers)
        unexpected = sorted(runtime_set - expected_set)
        if unexpected:
            sampler_mismatches.append({'reason': 'unexpected-runtime-samplers', 'registers': unexpected})
        state_draw_index = state.get('draw_index')
        candidate_rows.append({
            'frame': frame.get('frame'),
            'draw_index': state_draw_index,
            'expected_draw_range': (
                {
                    'first_index': expected_draw_range[0],
                    'index_count': expected_draw_range[1],
                }
                if expected_draw_range is not None
                else None
            ),
            'draw': state.get('draw'),
            'source': state_source,
            'vertex_shader': state.get('vertex_shader'),
            'pixel_shader': state.get('pixel_shader'),
            'identity_sha256': identity.get('identity_sha256'),
            'sampler_mismatches': sampler_mismatches,
        })
        if sampler_mismatches:
            suffix = (
                f"{frame.get('frame')}:{state_draw_index}"
                if state_source == 'draw-snapshot'
                else str(frame.get('frame'))
            )
            reasons.append(f"runtime:sampler-contract:{suffix}")
    matched_frames = {row.get('frame') for row in candidate_rows}
    ready = bool(expected_id and matches and not reasons)
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if matches else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'material_identity': expected,
        'candidate_frames': candidate_rows,
        'matched_frame_count': len(matched_frames),
        'matched_draw_count': len(candidate_rows),
        'expected_draw_range': (
            {
                'first_index': expected_draw_range[0],
                'index_count': expected_draw_range[1],
            }
            if expected_draw_range is not None
            else None
        ),
        'state_source': 'draw-snapshot' if any(row.get('source') == 'draw-snapshot' for row in candidate_rows) else ('frame-aggregate' if candidate_rows else 'none'),
    }

def validate_files(material_slice_path: str | Path, runtime_report_path: str | Path) -> dict[str, Any]:
    material = json.loads(Path(material_slice_path).read_text(encoding='utf-8'))
    runtime = json.loads(Path(runtime_report_path).read_text(encoding='utf-8'))
    return join_runtime_shader(material, runtime)

def main() -> int:
    ap = argparse.ArgumentParser(description='Join BMW material shader identity with captured D3D9 runtime shader state')
    ap.add_argument('material_slice')
    ap.add_argument('runtime_report')
    ap.add_argument('output')
    args = ap.parse_args()
    report = validate_files(args.material_slice, args.runtime_report)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'format': report['format'], 'status': report['status'], 'ready': report['ready'], 'matched_frame_count': report['matched_frame_count'], 'blocking_reasons': report['blocking_reasons']}, ensure_ascii=False, indent=2))
    return 0 if report['ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())