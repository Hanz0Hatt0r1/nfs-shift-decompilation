"""Correlate an exact BMW material slice with a captured runtime shader state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWRuntimeShaderJoin/1"

def _identity_from_material(material_slice: Mapping[str, Any]) -> Mapping[str, Any] | None:
    material = material_slice.get('material') or {}
    selection = material_slice.get('shader_selection') or {}
    return selection.get('permutation_identity') or material.get('permutation_identity')

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
    frame_rows = runtime_report.get('frames') or []
    matches = []
    for frame in frame_rows:
        identity = frame.get('shader_permutation_identity') or {}
        same_id = bool(expected_id and identity.get('identity_sha256') == expected_id)
        binding = frame.get('vertex_declaration') or {}
        frame_sha = binding.get('resource_sha256')
        frame_path = binding.get('resource_path')
        same_resource = False
        if expected_resource_sha and frame_sha:
            same_resource = str(frame_sha) == str(expected_resource_sha)
        elif expected_resource and frame_path:
            same_resource = str(frame_path).replace('\\', '/').strip('/').lower() == expected_resource.replace('\\', '/').strip('/').lower()
        if same_id and same_resource:
            matches.append(frame)
    if expected_id and not matches:
        reasons.append('runtime:shader-or-resource-instance-not-found')
    candidate_rows = []
    for frame in matches:
        identity = frame.get('shader_permutation_identity') or {}
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
            # External renderer-global samplers are legitimate only when the material slice records them.
            sampler_mismatches.append({'reason': 'unexpected-runtime-samplers', 'registers': unexpected})
        candidate_rows.append({
            'frame': frame.get('frame'),
            'vertex_shader': frame.get('vertex_shader'),
            'pixel_shader': frame.get('pixel_shader'),
            'identity_sha256': identity.get('identity_sha256'),
            'sampler_mismatches': sampler_mismatches,
        })
        if sampler_mismatches:
            reasons.append(f"runtime:sampler-contract:{frame.get('frame')}")
    ready = bool(expected_id and matches and not reasons)
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if matches else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'material_identity': expected,
        'candidate_frames': candidate_rows,
        'matched_frame_count': len(matches),
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