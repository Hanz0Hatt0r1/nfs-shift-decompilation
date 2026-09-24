"""Validate exact MEB property descriptor triples against the decoded vertex layout."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.BMWMEBDescriptorParity/1"
TYPE_BY_PROPERTY = {
    '200': 1, '220': 2, '240': 2, '250': 2,
    '130': 1, '131': 1, '132': 1, '133': 1, '134': 1,
    '230': 2, '231': 2, '232': 2, '233': 2, '234': 2,
    '310': 3, '460': 4, '461': 4, '580': 5,
}

def validate_meb_descriptor_parity(material_slice: Mapping[str, Any]) -> dict[str, Any]:
    mesh = material_slice.get('mesh') or {}
    attrs = list((mesh.get('vertex_layout') or {}).get('attributes') or [])
    descriptors = {str(row.get('id')): row for row in mesh.get('property_descriptors') or [] if row.get('id') is not None}
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []
    for attr in attrs:
        pid = str(attr.get('property_id'))
        descriptor = descriptors.get(pid)
        row = {'property_id': pid, 'name': attr.get('name'), 'status': 'not-found' if descriptor is None else 'match'}
        if descriptor is None:
            reasons.append(f'meb-descriptor:missing:{pid}')
            checks.append(row)
            continue
        words = descriptor.get('words')
        if not isinstance(words, list) or len(words) < 3:
            reasons.append(f'meb-descriptor:triple-invalid:{pid}')
            row['status'] = 'mismatch'
            checks.append(row)
            continue
        type_ordinal, usage_ordinal, channel = map(int, words[:3])
        expected_type = TYPE_BY_PROPERTY.get(pid)
        layout_index = int(attr.get('usage_index', 0) or 0)
        row.update({
            'descriptor_offset': descriptor.get('offset'),
            'descriptor_raw_hex': descriptor.get('raw_hex'),
            'type_ordinal': type_ordinal,
            'usage_ordinal': usage_ordinal,
            'channel': channel,
            'expected_type_ordinal': expected_type,
            'layout_usage_index': layout_index,
        })
        if expected_type is not None and type_ordinal != expected_type:
            reasons.append(f'meb-descriptor:type-mismatch:{pid}')
            row['status'] = 'mismatch'
        if channel != layout_index:
            reasons.append(f'meb-descriptor:channel-mismatch:{pid}')
            row['status'] = 'mismatch'
        checks.append(row)
    if not attrs:
        reasons.append('meb-descriptor:layout-empty')
    ready = bool(checks and not reasons)
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if checks else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(reasons)),
        'checks': checks,
    }