"""Verify the source-level BMW M3 vehicle selector against the golden asset namespace."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.SourceVehicleIdentityEvidence/1"
EXPECTED_SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXPECTED_RESOURCE_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"
EXPECTED_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"

def validate_source_vehicle_identity(source: str | bytes, *, source_sha256: str | None = None) -> dict[str, Any]:
    text = source.decode('utf-8', 'replace') if isinstance(source, bytes) else source
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    reasons=[]
    if source_sha256 is not None and digest != source_sha256:
        reasons.append('source:sha256-mismatch')
    match=re.search(r'float10 __fastcall FUN_004c32d0\\(int param_1\\)(?P<body>.*?)(?=\\n\\n//\\n)',text,re.S)
    if not match:
        match=re.search(r'float10 __fastcall FUN_004c32d0\\(int param_1\\)(?P<body>.*?return \\(float10\\)0;.*?\\n\\}',text,re.S)
    body=match.group('body') if match else ''
    exact=bool(re.search(r'case 2:\\s*pcVar3 = "bmw_m3_e36";',body,re.S))
    if not exact: reasons.append('source:bmw-case2-missing')
    return {
        'format':FORMAT,
        'status':'match' if not reasons else 'mismatch',
        'ready':not reasons,
        'blocking_reasons':list(dict.fromkeys(reasons)),
        'source_sha256':digest,
        'expected_source_sha256':source_sha256,
        'function':'FUN_004c32d0',
        'selector_case':2,
        'selector_value':'bmw_m3_e36' if exact else None,
        'golden_resource':EXPECTED_RESOURCE,
        'golden_resource_sha256':EXPECTED_RESOURCE_SHA256,
    }

def validate_source_vehicle_file(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    raw=p.read_bytes()
    expected=EXPECTED_SOURCE_SHA256 if p.name == 'SHIFT.exe.c' else None
    return validate_source_vehicle_identity(raw, source_sha256=expected)