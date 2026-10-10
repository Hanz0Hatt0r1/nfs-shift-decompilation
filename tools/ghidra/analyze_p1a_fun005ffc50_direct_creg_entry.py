#!/usr/bin/env python3
"""Bound the direct/static entry surface that can reach FUN_005ffc50's `creg` branch."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50DirectCregEntryClosure/1'
UPSTREAM='SHIFT.P1A.P13ASlot4StaticRegistryInitializers/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005FFC50
CREG=0x63726567
TARGET_RVA=TARGET-0x00400000
TEXT_VA=0x00401000
TEXT_RAW=0x00000400
RANGE=(0x005FFC50,0x005FFD88,'c06a36d72bae94295247b8cd1864984ec58feaf4efdfeccf38968af5d699c234')
EXPECTED_CALLS=[
  (0x005b81db,0x005b81d5,0x6d696372,'FUN_005b81a0'),
  (0x005b8204,0x005b81fe,0x6d696372,'FUN_005b81a0'),
  (0x005b8239,0x005b8233,0x706f7274,'FUN_005b8210'),
  (0x005be27f,0x005be279,0x74696d65,'FUN_005be1b0'),
  (0x005be2ee,0x005be2e8,0x6d696372,'FUN_005be1b0'),
  (0x005be30d,0x005be307,0x636c6964,'FUN_005be1b0'),
  (0x005be32c,0x005be326,0x73657276,'FUN_005be1b0'),
  (0x005be369,0x005be363,0x63646563,'FUN_005be1b0'),
  (0x005be38b,0x005be385,0x63646563,'FUN_005be1b0'),
  (0x005be3af,0x005be3a9,0x63726566,'FUN_005be1b0'),
  (0x005be3c3,0x005be3bd,0x63646563,'FUN_005be1b0'),
  (0x005be42b,0x005be425,0x69646576,'FUN_005be1b0'),
  (0x005be464,0x005be45e,0x6f646576,'FUN_005be1b0'),
]
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')

def norm(s:str)->str:
    return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')

def rows(exe:Path):
    p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
    out=[]
    for line in p.stdout.splitlines():
        m=I.match(line)
        if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
    return out

def section_bytes(blob:bytes,start:int,end:int)->bytes:
    off=TEXT_RAW+(start-TEXT_VA)
    return blob[off:off+(end-start)]

def occurrences(blob:bytes,value:int):
    pat=struct.pack('<I',value); out=[]; i=0
    while True:
        i=blob.find(pat,i)
        if i<0:return out
        out.append(i);i+=1

def command_for_call(rs,index:int):
    pushes=[]
    for a,m,o in reversed(rs[max(0,index-16):index]):
        if m=='push':
            pushes.append((a,o))
            if len(pushes)==2: break
    if len(pushes)!=2: raise AssertionError(('cannot recover command',rs[index],pushes))
    site,operand=pushes[1]
    if not operand.startswith('0x'): raise AssertionError(('command push is not immediate',rs[index],pushes))
    return site,int(operand,16)

def req(imap,address,mnemonic,operands):
    got=imap.get(address); exp=(mnemonic,norm(operands))
    if got!=exp: raise AssertionError((hex(address),got,exp))
    return f'0x{address:08x} {got[0]} {got[1]}'

def analyze(exe:Path,upstream:Path):
    blob=exe.read_bytes(); sha=hashlib.sha256(blob).hexdigest()
    if sha!=SHA: raise ValueError(f'unexpected retail SHA256: {sha}')
    up=json.loads(upstream.read_text(encoding='utf-8'))
    if up.get('format')!=UPSTREAM: raise ValueError(f"unexpected upstream format: {up.get('format')}")
    if up.get('registry_initializer_result_path',{}).get('dynamic_registration_forwarder')!='0x005ffc7a':
        raise AssertionError('upstream dynamic registration anchor drift')
    start,end,expected_hash=RANGE
    raw=section_bytes(blob,start,end)
    got_hash=hashlib.sha256(raw).hexdigest()
    if len(raw)!=(end-start) or got_hash!=expected_hash: raise AssertionError(('FUN_005ffc50 range drift',len(raw),got_hash))
    rs=rows(exe); imap={a:(m,o) for a,m,o in rs}
    direct=[]
    for i,(a,m,o) in enumerate(rs):
        if m=='call' and o=='0x5ffc50':
            cmd_site,cmd=command_for_call(rs,i)
            direct.append((a,cmd_site,cmd))
    expected=[x[:3] for x in EXPECTED_CALLS]
    if direct!=expected: raise AssertionError(('direct-call surface drift',direct))
    caller_by_site={site:caller for site,_,_,caller in EXPECTED_CALLS}
    rows_out=[]
    for site,cmd_site,cmd in direct:
        rows_out.append({'call_site':f'0x{site:08x}','caller':caller_by_site[site],
                         'command_push_site':f'0x{cmd_site:08x}','command':f'0x{cmd:08x}',
                         'is_creg':cmd==CREG})
    counts=collections.Counter(f'0x{x[2]:08x}' for x in direct)
    va_occ=occurrences(blob,TARGET); rva_occ=occurrences(blob,TARGET_RVA)
    anchors={
      'command_load':req(imap,0x005ffc50,'mov','eax,DWORD PTR [esp+0x8]'),
      'creg_compare':req(imap,0x005ffc69,'cmp','eax,0x63726567'),
      'creg_arg2_load':req(imap,0x005ffc70,'mov','edx,DWORD PTR [esp+0x10]'),
      'creg_arg1_load':req(imap,0x005ffc74,'mov','eax,DWORD PTR [esp+0xc]'),
      'creg_arg2_push':req(imap,0x005ffc78,'push','edx'),
      'creg_arg1_push':req(imap,0x005ffc79,'push','eax'),
      'creg_registry_call':req(imap,0x005ffc7a,'call','0x6144f0'),
      'creg_cleanup':req(imap,0x005ffc7f,'add','esp,0x8'),
    }
    direct_creg=sum(1 for x in direct if x[2]==CREG)
    if direct_creg: raise AssertionError('direct creg entry unexpectedly exists')
    if va_occ or rva_occ: raise AssertionError(('exact static pointer literal unexpectedly exists',va_occ,rva_occ))
    return {
      'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
      'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,
        'fun005ffc50_range':{'start':f'0x{start:08x}','end_exclusive':f'0x{end:08x}','size':end-start,'sha256':got_hash}},
      'creg_branch':{'dispatcher':'FUN_005ffc50','dispatcher_address':'0x005ffc50','command_value':'0x63726567',
        'registry_forward_call':'0x005ffc7a','registry_target':'thunk_FUN_0043ca56 / 0x006144f0',
        'forwarded_stack_arguments':['[entry ESP+0xc]','[entry ESP+0x10]']},
      'direct_entry_surface':{'direct_call_count':len(direct),'distinct_direct_caller_count':len(set(caller_by_site.values())),
        'direct_callers':sorted(set(caller_by_site.values())),'direct_creg_call_count':direct_creg,
        'command_counts':dict(sorted(counts.items())),'rows':rows_out},
      'static_pointer_literal_surface':{'exact_absolute_va':'0x005ffc50','exact_absolute_va_occurrence_count':len(va_occ),
        'exact_rva':'0x001ffc50','exact_rva_occurrence_count':len(rva_occ)},
      'machine_anchors':anchors,
      'adjudication':{
        'p13a_fun005ffc50_direct_creg_entry_subset_complete':True,
        'direct_fun005ffc50_creg_registration_found':False,
        'exact_static_fun005ffc50_absolute_pointer_found':False,
        'exact_static_fun005ffc50_rva_pointer_found':False,
        'fun005ffc50_creg_requires_indirect_or_reconstructed_entry':True,
        'fun0067b660_callback_argument_provenance_complete':False,
        'fun0067b660_callback_argument_is_selected_wheel_ruled_out':False,
        'callbacks_and_indirect_entry_ruled_out':False,
        'encoded_or_reconstructed_callback_entry_ruled_out':False,
        'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
        'stored_or_escaped_aliases_ruled_out':False,
        'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,
        'external_provider_count':7,
      },
      'limits':[
        'This closes only direct machine calls to FUN_005ffc50 plus exact raw absolute-VA/RVA pointer literals for that dispatcher.',
        'The creg branch remains present and forwards two runtime-supplied stack arguments to the registry; its indirect/reconstructed incoming entry surface is not proven empty.',
        'Encoded/split pointers, runtime registration, incoming indirect entry, and alternate FUN_0067b660 slot4 dispatch forms remain open.',
        'No slot0, slot1, aggregate P1.3, stored-alias, or global callback gate is promoted.'
      ],
      'next_step':'Trace incoming indirect/reconstructed entry to FUN_005ffc50 or recover another concrete FUN_0067b660 slot+0x4 dispatcher with explicit argument provenance.'
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
    a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(s,encoding='utf-8')
    else:print(s,end='')
if __name__=='__main__':main()
