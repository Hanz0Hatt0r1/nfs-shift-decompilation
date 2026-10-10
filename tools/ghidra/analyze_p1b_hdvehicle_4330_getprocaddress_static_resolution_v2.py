#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path

FORMAT='SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2'
EXPECTED_PROVIDER_COUNT=7
BASE_PATH=Path(__file__).with_name('analyze_p1b_hdvehicle_4330_getprocaddress_static_resolution.py')

def load_base(path: Path=BASE_PATH):
    spec=importlib.util.spec_from_file_location('p1b_gpa_v1',path)
    m=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m); return m

def direct_target(row: dict):
    if not row.get('operands'): return None
    token=row['operands'].split()[0]
    try:return int(token,0)
    except ValueError:return None

def scan_register_lifetime(instructions:list[dict], start_index:int, register:str, destination_register):
    addr_to_index={row['address']:i for i,row in enumerate(instructions)}
    work=[start_index+1]; seen=set(); calls={}; unresolved=[]
    while work:
        i=work.pop()
        if i<0 or i>=len(instructions) or i in seen: continue
        seen.add(i); row=instructions[i]; mn=row['mnemonic']; op=row['operands']
        if mn.startswith('ret') or mn in {'int3','hlt'}: continue
        if mn=='call' and op==register: calls[row['address']]=i
        if destination_register(row)==register: continue
        if mn=='jmp':
            target=direct_target(row)
            if target is None or target not in addr_to_index: unresolved.append(row['address'])
            else: work.append(addr_to_index[target])
            continue
        if mn.startswith('j'):
            target=direct_target(row)
            if target is not None and target in addr_to_index: work.append(addr_to_index[target])
            elif target is None: unresolved.append(row['address'])
            if i+1<len(instructions): work.append(i+1)
            continue
        if i+1<len(instructions): work.append(i+1)
    return [calls[a] for a in sorted(calls)], sorted(set(unresolved))

def analyze(exe:Path, base_path:Path=BASE_PATH):
    b=load_base(base_path)
    data=exe.read_bytes(); import hashlib
    digest=hashlib.sha256(data).hexdigest()
    if digest!=b.EXPECTED_SHA256 or len(data)!=b.EXPECTED_SIZE: raise ValueError('retail authority mismatch')
    pe=b.PE32(data); instructions=b.parse_objdump(exe)
    refs=[(i,r) for i,r in enumerate(instructions) if f"0x{b.GETPROCADDRESS_IAT:x}" in r['operands']]
    direct_refs=[(i,r) for i,r in refs if r['mnemonic']=='call']
    load_refs=[(i,r) for i,r in refs if r['mnemonic']=='mov']
    families=[]; name_rows=[]; all_loaded_calls=[]
    for i,row in load_refs:
        reg=row['operands'].split(',',1)[0].strip()
        call_indexes,unresolved=scan_register_lifetime(instructions,i,reg,b.destination_register)
        if unresolved: raise ValueError(f'unresolved control flow from load 0x{row["address"]:08x}: {unresolved}')
        calls=[]
        for ci in call_indexes:
            call=instructions[ci]; name=b.immediate_proc_name_before_call(instructions,ci,pe)
            if name is None: raise ValueError(f'unresolved name at 0x{call["address"]:08x}')
            entry={'callsite':f'0x{call["address"]:08x}','name':name}
            calls.append(entry); name_rows.append({'source':'register_loaded_iat',**entry}); all_loaded_calls.append(call['address'])
        families.append({'loadsite':f'0x{row["address"]:08x}','register':reg,'callsite_count':len(calls),'first_callsite':calls[0]['callsite'] if calls else None,'last_callsite':calls[-1]['callsite'] if calls else None})
    generic_seen=False
    for i,row in direct_refs:
        if row['address']==b.GENERIC_WRAPPER_GPA_CALL: generic_seen=True; continue
        name=b.immediate_proc_name_before_call(instructions,i,pe)
        if row['address']==0x00634046 and name is None: name=pe.cstring(0x00AEBE58)
        if name is None: raise ValueError(f'unresolved direct name at 0x{row["address"]:08x}')
        name_rows.append({'source':'direct_iat_call','callsite':f'0x{row["address"]:08x}','name':name})
    wrapper_callers=[(i,r) for i,r in enumerate(instructions) if r['mnemonic']=='call' and r['operands']==f'0x{b.GENERIC_WRAPPER:x}']
    wrapper_names=[]
    for i,row in wrapper_callers:
        name=b.immediate_proc_name_before_call(instructions,i,pe) or b.resolve_formatted_wrapper_name(instructions,i,pe)
        if name is None: raise ValueError(f'unresolved wrapper name at 0x{row["address"]:08x}')
        wrapper_names.append(name); name_rows.append({'source':'generic_wrapper_direct_caller','callsite':f'0x{row["address"]:08x}','name':name})
    unique=sorted({r['name'] for r in name_rows}); patch=sorted(set(unique)&b.PATCH_API_NAMES)
    return {
      'format':FORMAT,'version':2,'ready':True,'owner':'Process 1B / P1.3B',
      'authority':{'platform':'PC retail 1.02','retail_executable_sha256':digest,'retail_file_size':len(data),'retail_bytes_are_machine_authority':True},
      'getprocaddress_surface':{
        'iat_va':f'0x{b.GETPROCADDRESS_IAT:08x}','classified_instruction_reference_count':len(refs),
        'direct_iat_call_reference_count':len(direct_refs),'iat_load_reference_count':len(load_refs),
        'register_loaded_callsite_count':len(set(all_loaded_calls)),'physical_getprocaddress_callsite_count':len(direct_refs)+len(set(all_loaded_calls)),
        'register_loaded_family_count':len(families),'register_loaded_families':families,
        'generic_wrapper':f'0x{b.GENERIC_WRAPPER:08x}','generic_wrapper_direct_caller_count':len(wrapper_callers),
        'generic_wrapper_direct_caller_names':wrapper_names,'known_name_instance_count':len(name_rows),
        'known_unique_name_count':len(unique),'known_patch_api_name_hits':patch,
        'v1_register_loaded_callsite_count':86,'v1_physical_getprocaddress_callsite_count':98,
        'v2_newly_recovered_callsites':['0x0099a116','0x00a623b8','0x00a623c2']
      },
      'adjudication':{
        'cfg_aware_register_loaded_getprocaddress_surface_complete':True,'v1_linear_scan_count_superseded':True,
        'known_getprocaddress_patch_api_resolution_found':bool(patch),'dynamic_getprocaddress_resolution_ruled_out':False,
        'runtime_generated_or_copied_function_pointers_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,
        'runtime_computed_carrier_pointers_ruled_out':False,'runtime_copied_or_encoded_carrier_pointers_ruled_out':False,
        'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,
        'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':EXPECTED_PROVIDER_COUNT
      },
      'limits':['CFG-aware traversal closes only static lifetimes rooted at the seven imported GetProcAddress IAT loads. Runtime-generated resolver aliases, external resolver pointers and unrelated pointer tables remain open.'],
      'next_step':'Classify the 89 CFG-aware register-loaded GetProcAddress result lineages and compose resolver-populated function-pointer storage coverage.'
    }

def main():
    p=argparse.ArgumentParser(); p.add_argument('exe',type=Path); p.add_argument('--base-analyzer',type=Path,default=BASE_PATH); p.add_argument('--output',type=Path); a=p.parse_args()
    d=analyze(a.exe,a.base_analyzer); t=json.dumps(d,indent=2,sort_keys=True)+'\n'; a.output.write_text(t) if a.output else print(t,end='')
if __name__=='__main__': main()
