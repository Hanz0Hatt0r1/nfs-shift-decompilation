"""Strict shader/permutation gate for the evidence-backed BMW M3 paint material."""
from __future__ import annotations

from typing import Any, Mapping

from bmw_m3_paint_contract import PAINT_CONTRACT, normalize_material_binding

FORMAT = "SHIFT.BMWM3PaintShaderGate/1"

def validate_bmw_paint_shader_gate(binding: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_material_binding(binding)
    selection = binding.get('shader_selection') or {}
    selected_fxo = selection.get('selected_fxo') or {}
    pair = selection.get('shader_pair') or {}
    linked = selection.get('linked_shader_pair') or binding.get('linked_shader_pair')
    identity = selection.get('permutation_identity') or binding.get('permutation_identity')
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []

    if selection.get('status') != 'unique':
        reasons.append('shader-selection:not-unique')
    if not selected_fxo:
        reasons.append('shader-selection:selected-fxo-missing')
    else:
        if selected_fxo.get('exact') is not True:
            reasons.append('shader-selection:selected-fxo-not-exact')
        if selected_fxo.get('vertex_pair_selection_status') not in (None, 'unique'):
            reasons.append('shader-selection:vertex-pair-not-unique')
    if not pair:
        reasons.append('shader-pair:missing')
    elif pair.get('selection_status') != 'unique':
        reasons.append('shader-pair:not-unique')
    if not linked:
        reasons.append('shader-pair:linked-source-missing')
    if not identity or identity.get('format') != 'SHIFT.ShaderPermutationIdentity/1':
        reasons.append('shader-identity:missing-or-invalid')
    elif not isinstance(identity.get('identity_sha256'), str) or len(identity['identity_sha256']) != 64:
        reasons.append('shader-identity:sha256-invalid')

    shader = str(normalized.get('shader') or '').replace('\\','/').rsplit('/', 1)[-1].lower()
    if shader != PAINT_CONTRACT['shader'].lower():
        reasons.append('shader:path-mismatch')

    for expected in PAINT_CONTRACT['samplers']:
        matches = [
            row for row in normalized.get('textures') or []
            if row.get('sampler') == expected['fx_sampler']
            or row.get('material_parameter') == expected['parameter']
        ]
        row = {'sampler': expected['fx_sampler'], 'expected_register': expected['register']}
        if len(matches) != 1:
            reasons.append(f"sampler:{expected['fx_sampler']}:expected-one")
            row['status'] = 'not-found' if not matches else 'ambiguous'
        else:
            observed = matches[0].get('d3d9_sampler_register', matches[0].get('slot'))
            row.update({'register': observed, 'status': 'match' if observed == expected['register'] else 'mismatch'})
            if observed != expected['register']:
                reasons.append(f"sampler:{expected['fx_sampler']}:register-mismatch")
        checks.append(row)

    external = normalized.get('external_samplers') or []
    for expected in PAINT_CONTRACT['external_samplers']:
        matches = [row for row in external if row.get('sampler') == expected['name'] or row.get('name') == expected['name']]
        if len(matches) != 1:
            reasons.append(f"external:{expected['name']}:expected-one")
        else:
            observed = matches[0].get('d3d9_sampler_register', matches[0].get('slot'))
            if observed != expected['register']:
                reasons.append(f"external:{expected['name']}:register-mismatch")

    unresolved = [row for row in binding.get('unresolved_textures') or [] if row is not None]
    if unresolved:
        reasons.append('material:unresolved-textures')

    return {
        'format': FORMAT,
        'status': 'ready' if not reasons else 'blocked',
        'ready': not reasons,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'shader_selection_status': selection.get('status'),
        'selected_fxo': {k: selected_fxo.get(k) for k in ('file','program_offset','exact','vertex_pair_selection_status','pixel_sha256','vertex_sha256','pair_sha256')},
        'permutation_identity': identity,
        'checks': checks,
    }