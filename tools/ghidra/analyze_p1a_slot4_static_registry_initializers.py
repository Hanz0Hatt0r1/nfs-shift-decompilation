#!/usr/bin/env python3
"""Prove static registry initializer results cannot carry animation vptr 0x00af7544."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13ASlot4StaticRegistryInitializers/1'
UPSTREAM='SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
RANGES={
 'static_registration':(0x005ff8bc,0x005ff8da,'text','61d2d99bfffc233302cce7d7d317767b8f343ca6a98009a394e36fc30ed5e0a6'),
 'registry_init_dispatch':(0x00614570,0x00614592,'text','2b66cccc0be38ff01f6cc177225c7290b6dc6482ed6791bde18c488f50da4c83'),
 'initializer_A':(0x00614700,0x0061473f,'text','0eeee508b35ab663d2bec281b9a40b125e8557399de811cae49cc0b439cf1a1b'),
 'initializer_B':(0x00614130,0x00614184,'text','e323ed3b749bb2e1b17ff4c2770881e21f61d70985f6e3713c311975d253ed6c'),
 'table_A':(0x00ae7d84,0x00ae7d90,'rdata','32453105aab240201b63b89a444738792569640e416bbbba0239d3fda890ae94'),
 'table_B':(0x00ae7d6c,0x00ae7d78,'rdata','1c201216165fdc35adeccde7bf722e4214ed25b465a806ad8bcb43317f8efae5'),
}
SECTION={'text':(0x00401000,0x00000400),'rdata':(0x00aa6000,0x006a4a00)}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')

def dis(exe,start,end):
    p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{start:x}',f'--stop-address=0x{end:x}',str(exe)],capture_output=True,text=True,check=True)
    out={}
    for line in p.stdout.splitlines():
        m=I.match(line)
        if m:out[int(m.group(1),16)]=(m.group(2).lower(),re.sub(r'\s+',' ',m.group(3).strip()).replace(', ',','))
    return out

def req(M,addr,op,operand):
    if M.get(addr)!=(op,operand):raise AssertionError((hex(addr),M.get(addr),(op,operand)))
    return f'0x{addr:08x} {op} {operand}'

def analyze(exe,upstream):
    b=exe.read_bytes()
    if hashlib.sha256(b).hexdigest()!=SHA:raise ValueError('wrong retail executable')
    up=json.loads(upstream.read_text(encoding='utf-8'))
    if up['format']!=UPSTREAM:raise ValueError('wrong upstream contract')
    if up['registry_path']['direct_registration_calls']!=['0x005ff8c6','0x005ff8d5','0x005ffc7a']:raise AssertionError('registration surface drift')
    if up['registry_path']['callback_result_field']!='record+0x8':raise AssertionError('registry result drift')
    if up['adjudication']['p13a_fun0067b660_immediate_slot4_caller_cleanup_subset_complete'] is not True:raise AssertionError('upstream incomplete')
    ranges={};maps={};raw={}
    for name,(start,end,section,expected_hash) in RANGES.items():
        va,off=SECTION[section];d=b[off+start-va:off+end-va]
        if len(d)!=end-start or hashlib.sha256(d).hexdigest()!=expected_hash:raise AssertionError(('range drift',name))
        ranges[name]={'start':f'0x{start:08x}','end_exclusive':f'0x{end:08x}','size':end-start,'sha256':hashlib.sha256(d).hexdigest()}
        raw[name]=d
        if section=='text':maps[name]=dis(exe,start,end)
    A={}
    M=maps['static_registration']
    for name,addr,op,o in [
        ('static_A_table_push',0x5ff8bc,'push','0xae7d84'),
        ('static_A_registry_call',0x5ff8c6,'call','0x6144f0'),
        ('static_B_table_push',0x5ff8cb,'push','0xae7d6c'),
        ('static_B_registry_call',0x5ff8d5,'call','0x6144f0')]:A[name]=req(M,addr,op,o)
    M=maps['registry_init_dispatch']
    for name,addr,op,o in [
        ('init_load_table',0x61457a,'mov','eax,DWORD PTR [edi+0x4]'),
        ('init_load_function',0x614581,'mov','edx,DWORD PTR [eax]'),
        ('init_invoke',0x614584,'call','edx'),
        ('init_save_result',0x61458b,'mov','DWORD PTR [edi+0x8],eax')]:A[name]=req(M,addr,op,o)
    M=maps['initializer_A']
    for name,addr,op,o in [
        ('initializer_A_allocator',0x614722,'call','0x5845d0'),
        ('initializer_A_vptr_store',0x61472b,'mov','DWORD PTR [eax],0xae7d84'),
        ('initializer_A_return',0x61473e,'ret','')]:A[name]=req(M,addr,op,o)
    M=maps['initializer_B']
    for name,addr,op,o in [
        ('initializer_B_allocator',0x614157,'call','0x5845d0'),
        ('initializer_B_null_branch',0x614161,'jne','0x614167'),
        ('initializer_B_null_return',0x614166,'ret',''),
        ('initializer_B_vptr_store',0x614170,'mov','DWORD PTR [eax],0xae7d6c'),
        ('initializer_B_return',0x614183,'ret','')]:A[name]=req(M,addr,op,o)
    rows=[]
    for name,table,initializer in [('A',0x00ae7d84,0x00614700),('B',0x00ae7d6c,0x00614130)]:
        d=raw['table_'+name]
        target=struct.unpack_from('<I',d)[0]
        if target!=initializer:raise AssertionError(('initializer table drift',name,target))
        rows.append({'registration_call':'0x005ff8c6' if name=='A' else '0x005ff8d5',
                     'registered_table':f'0x{table:08x}', 'initializer':f'0x{initializer:08x}',
                     'returned_object_vptr_on_success':f'0x{table:08x}',
                     'returned_object_can_be_null':name=='B',
                     'returned_object_vptr_is_animation_vptr':False})
    return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
            'authority':{'platform':'PC retail 1.02','retail_executable_sha256':SHA,'upstream_contract':UPSTREAM,'machine_ranges':ranges},
            'static_initializer_rows':rows,'static_registration_count':2,
            'animation_vtable':'0x00af7544',
            'registry_initializer_result_path':{'callback_table_entry_offset':'+0x0','result_storage_offset':'record+0x8',
                                                'result_used_by_slot4_dispatch':'0x006145c4',
                                                'static_result_types_exclude_animation_vtable':True,
                                                'dynamic_registration_forwarder':'0x005ffc7a',
                                                'dynamic_result_types_closed':False},
            'machine_anchors':A,
            'adjudication':{'p13a_slot4_static_registry_initializer_result_subset_complete':True,
                            'p13a_slot4_two_static_registration_results_are_animation_object':False,
                            'fun0067b660_callback_argument_provenance_complete':False,
                            'fun0067b660_callback_argument_is_selected_wheel_ruled_out':False,
                            'callbacks_and_indirect_entry_ruled_out':False,
                            'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
                            'stored_or_escaped_aliases_ruled_out':False,
                            'p13a_slot0_complete':False,'p13a_slot1_complete':False,
                            'p1_3_control_producer_complete':False,'external_provider_count':7},
            'limits':['The two statically registered initializer callbacks return their own class objects with vptrs 0x00ae7d84 and 0x00ae7d6c (or null for B), never the animation vptr 0x00af7544.',
                      'The dynamically forwarded registry entry at 0x005ffc7a is not bounded by this static subset.',
                      'Other vtable slot4 invocation forms and the actual FUN_0067b660 explicit argument remain unresolved.'],
            'next_step':'Classify dynamic 0x005ffc7a registration producers and alternate FUN_0067b660 virtual dispatch shapes.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--upstream',required=True,type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();s=json.dumps(analyze(a.executable,a.upstream),sort_keys=True,indent=2)+'\n'
    if a.output:a.output.write_text(s,encoding='utf-8')
    else:print(s,end='')
if __name__=='__main__':main()