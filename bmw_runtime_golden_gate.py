"""Single readiness gate for a captured BMW render state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bmw_runtime_parity import validate_files as validate_runtime_parity_files

FORMAT = "SHIFT.BMWRuntimeGoldenGate/1"

def validate_runtime_golden_gate(material_path: str | Path, runtime_path: str | Path, *, usage_map_path: str | Path | None = None) -> dict[str, Any]:
    material = json.loads(Path(material_path).read_text(encoding='utf-8'))
    runtime = json.loads(Path(runtime_path).read_text(encoding='utf-8'))
    parity = validate_runtime_parity_files(material_path, runtime_path, usage_map_path=usage_map_path, require_constant_values=True)
    command = material.get('render_command')
    reasons = list(parity.get('blocking_reasons') or [])
    command_status = 'not-supplied'
    if isinstance(command, dict):
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
        'render_command': {'status': command_status},
        'golden_requirements': {
            'shader_identity': 'required',
            'resource_identity': 'required',
            'sampler_parity': 'required',
            'constant_register_parity': 'required',
            'constant_value_parity': 'required',
            'declaration_parity': 'required',
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