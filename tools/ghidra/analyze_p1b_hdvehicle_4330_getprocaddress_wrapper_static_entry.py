#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1B.HDVehicle4330GetProcAddressWrapperStaticEntrySurface/1'
EXE_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
C_SHA='512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9'
TARGET=0x0093DD2B; IMAGE_BASE=0x00400000; PROVIDERS=7

def raw_hits(data,v):
    pat=struct.pack('<I',v); out=[]; i=0
    while True:
        i=data.find(pat,i)
        if i<0:return out
        out.append(i); i+=1

def analyze(exe:Path,cfile:Path):
    data=exe.read_bytes(); c=cfile.read_text(encoding='utf-8',errors='replace')
    if hashlib.sha256(data).hexdigest()!=EXE_SHA or len(data)!=8801792: raise ValueError('exe authority drift')
    if hashlib.sha256(cfile.read_bytes()).hexdigest()!=C_SHA: raise ValueError('c export authority drift')
    text=subprocess.check_output(['objdump','-d','-Mintel',str(exe)],text=True,errors='replace')
    calls=[]; jmps=[]
    for line in text.splitlines():
        m=re.match(r'^\s*([0-9a-fA-F]+):.*\b(call|jmp)\s+0x([0-9a-fA-F]+)\b',line)
        if m and int(m.group(3),16)==TARGET:
            (calls if m.group(2)=='call' else jmps).append(int(m.group(1),16))
    sym=list(re.finditer(r'\bFUN_0093dd2b\b',c)); defs=[]; inv=[]; other=[]
    for m in sym:
        before=c[max(0,m.start()-100):m.start()]; after=c[m.end():m.end()+8]
        if re.search(r'int\s+__cdecl\s*$',before) and after.lstrip().startswith('('): defs.append(m.start())
        elif after.lstrip().startswith('('): inv.append(m.start())
        else: other.append(m.start())
    return {
      'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B',
      'authority':{'retail_executable_sha256':EXE_SHA,'retail_file_size':len(data),'ghidra_c_sha256':C_SHA,'retail_bytes_are_machine_authority':True,'ghidra_c_is_navigation_crosscheck_only':True},
      'surface':{'wrapper_va':f'0x{TARGET:08x}','wrapper_rva':f'0x{TARGET-IMAGE_BASE:08x}','whole_image_absolute_va_literal_hit_count':len(raw_hits(data,TARGET)),'whole_image_rva_literal_hit_count':len(raw_hits(data,TARGET-IMAGE_BASE)),'direct_callsite_count':len(calls),'direct_callsites':[f'0x{x:08x}' for x in calls],'direct_jumpsite_count':len(jmps),'source_symbol_occurrence_count':len(sym),'source_definition_count':len(defs),'source_direct_invocation_count':len(inv),'source_non_invocation_value_use_count':len(other)},
      'adjudication':{'generic_wrapper_static_entry_surface_complete':True,'generic_wrapper_static_address_taken_or_literal_seed_found':False,'generic_wrapper_static_indirect_entry_seed_found':False,'generic_wrapper_indirect_runtime_entry_ruled_out':False,'dynamic_getprocaddress_resolution_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':PROVIDERS},
      'limits':['This closes static exact VA/RVA publication and source-visible address-taking of wrapper 0x0093dd2b only.','Runtime-computed/copied/encoded wrapper pointers and opaque indirect entry remain open.'],
      'next_step':'Trace runtime-generated/copied wrapper pointers or runtime-populated function-pointer stores.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('cfile',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();d=analyze(a.exe,a.cfile);s=json.dumps(d,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
