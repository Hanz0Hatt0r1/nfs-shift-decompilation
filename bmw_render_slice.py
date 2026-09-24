"""Select one exact BMW M3 resource from a generic SHIFT.RenderBinding/1 report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.BMWRenderSlice/1"

def _norm(value: Any) -> str:
    return str(value or '').replace('\\', '/').strip('/').lower()

def _packet_identity(packet: Mapping[str, Any]) -> tuple[str, str | None]:
    mesh = packet.get('mesh') or {}
    resolved = mesh.get('resolved') or {}
    path = _norm(resolved.get('path') or mesh.get('ref'))
    sha = mesh.get('resource_sha256') or resolved.get('resource_sha256')
    return path, str(sha) if sha else None

def select_bmw_packets(render_binding: Mapping[str, Any], golden: Mapping[str, Any]) -> dict[str, Any]:
    if render_binding.get('format') != 'SHIFT.RenderBinding/1':
        raise ValueError('input is not SHIFT.RenderBinding/1')
    golden_meta = golden.get('golden') or {}
    expected_path = _norm(golden_meta.get('resource'))
    expected_sha = golden_meta.get('resource_sha256')
    packets = render_binding.get('packets') or []
    selected = []
    identity_matches = []
    for index, packet in enumerate(packets):
        path, sha = _packet_identity(packet)
        path_match = bool(expected_path and path == expected_path)
        sha_match = bool(expected_sha and sha == expected_sha)
        row = {'packet_index': index, 'path': path, 'resource_sha256': sha, 'path_match': path_match, 'sha_match': sha_match}
        if path_match or sha_match:
            identity_matches.append(row)
        if path_match and sha_match:
            selected.append((index, packet))
    blockers = []
    if not expected_path or not expected_sha:
        blockers.append('golden:identity-incomplete')
    if not identity_matches:
        blockers.append('golden:resource-not-found')
    if len(selected) == 0 and identity_matches:
        blockers.append('golden:identity-conflict')
    if len(selected) > 1:
        blockers.append('golden:multiple-packets-for-resource')
    chosen = selected[0][1] if len(selected) == 1 else None
    static_draw = None
    render_command = None
    if chosen is not None:
        idx = selected[0][0]
        draws = render_binding.get('static_draws') or []
        commands = render_binding.get('render_commands') or []
        static_draw = draws[idx] if idx < len(draws) else None
        render_command = commands[idx] if idx < len(commands) else None
        if static_draw is None:
            blockers.append('render:static-draw-missing')
        if render_command is None:
            blockers.append('render:command-missing')
    ready = not blockers and chosen is not None
    return {
        'format': FORMAT,
        'status': 'match' if ready else ('partial' if identity_matches else 'not-found'),
        'ready': ready,
        'blocking_reasons': list(dict.fromkeys(blockers)),
        'golden_identity': {'resource': golden_meta.get('resource'), 'resource_sha256': expected_sha},
        'identity_matches': identity_matches,
        'packet_index': selected[0][0] if len(selected) == 1 else None,
        'packet': chosen,
        'static_draw': static_draw,
        'render_command': render_command,
    }

def validate_files(golden_path: str | Path, render_binding_path: str | Path) -> dict[str, Any]:
    golden = json.loads(Path(golden_path).read_text(encoding='utf-8'))
    binding = json.loads(Path(render_binding_path).read_text(encoding='utf-8'))
    return select_bmw_packets(binding, golden)

def main() -> int:
    ap = argparse.ArgumentParser(description='Extract one exact BMW M3 render slice from SHIFT.RenderBinding/1')
    ap.add_argument('golden')
    ap.add_argument('render_binding')
    ap.add_argument('output')
    args = ap.parse_args()
    report = validate_files(args.golden, args.render_binding)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'format': report['format'], 'status': report['status'], 'ready': report['ready'], 'packet_index': report['packet_index']}, ensure_ascii=False, indent=2))
    return 0 if report['ready'] else 2

if __name__ == '__main__':
    raise SystemExit(main())