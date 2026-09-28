"""Validate the offline c-register ABI across MaterialUniformBinding, ConstantPayload and RenderCommand."""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.RenderCommandConstantParity/1"

def _binding_rows(uniform_binding: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows=[]
    for row in uniform_binding.get('bindings') or []:
        try:
            start=int(row.get('register_index')); count=int(row.get('register_count'))
        except (TypeError,ValueError):
            continue
        rows.append({'name':row.get('name'),'stage':str(row.get('stage') or 'pixel').lower(),'register_index':start,'register_count':count,'ctab_type':row.get('ctab_type'),'registers':list(range(start,start+count))})
    return rows

def _range_rows(command: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows=[]
    for row in command.get('constant_commands') or []:
        rows.append({'name':row.get('name'),'stage':str(row.get('stage') or 'pixel').lower(),'register_index':row.get('register_index'),'register_count':row.get('register_count'),'ctab_type':row.get('ctab_type'),'byte_offset':row.get('byte_offset')})
    return rows

def validate_render_command_constant_parity(render_command: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(render_command, Mapping):
        return {'format':FORMAT,'status':'invalid','ready':False,'blocking_reasons':['render-command:invalid-input-type'],'checks':[]}
    if render_command.get('format') != 'SHIFT.RenderCommand/1':
        return {'format':FORMAT,'status':'invalid','ready':False,'blocking_reasons':['render-command:invalid-format'],'checks':[]}
    reasons=[]; checks=[]; submeshes=render_command.get('submeshes') or []
    for index,submesh in enumerate(submeshes):
        uniforms=(submesh.get('uniforms') or {}) if isinstance(submesh,Mapping) else {}
        payload=submesh.get('constant_payload') or {} if isinstance(submesh,Mapping) else {}
        expected=_binding_rows(uniforms)
        commands=_range_rows(submesh)
        payload_registers={int(x.get('register_index')):x for x in payload.get('registers') or [] if x.get('register_index') is not None} if isinstance(payload,Mapping) else {}
        command_by_key={(x.get('stage'),x.get('register_index')):x for x in commands}
        if expected and payload.get('ready') is False:
            reasons.append(f'submesh:{index}:constant-payload-not-ready')
        for row in expected:
            key=(row['stage'],row['register_index'])
            command=command_by_key.get(key)
            payload_row=payload_registers.get(row['register_index'])
            missing=[]
            if command is None: missing.append('command')
            if payload_row is None: missing.append('payload')
            if command is not None and int(command.get('register_count') or 0) != row['register_count']: missing.append('command-count')
            if command is not None and int(command.get('byte_offset') or -1) != row['register_index']*16: missing.append('command-offset')
            if missing: reasons.append(f'submesh:{index}:constant:{row["name"] or row["register_index"]}:'+','.join(missing))
            checks.append({'submesh':index,**row,'command_present':command is not None,'payload_present':payload_row is not None,'status':'match' if not missing else 'mismatch'})
        expected_keys={(x['stage'],x['register_index']) for x in expected}
        unexpected=[x for x in commands if (x.get('stage'),x.get('register_index')) not in expected_keys]
        if unexpected: reasons.append(f'submesh:{index}:constant:unexpected-command-range')
    ready=bool(not reasons and all(x['status']=='match' for x in checks))
    return {'format':FORMAT,'status':'match' if ready else 'mismatch','ready':ready,'blocking_reasons':list(dict.fromkeys(reasons)),'checks':checks}