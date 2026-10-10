#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

FORMAT='SHIFT.P1A.P13ARuntimeModuleBaseStorageFrontier/1'
RETAIL_SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED_BYTES={
0x00904817:'6800004000e83f491600',
0x00A69197:'e8e4d7e1ff8bf085f674648b068b8080000000578b7d088bd78bceffd08b068b80a00000008bd78bceffd08b068b',
0x00886A66:'e8f55fb8ff50a33496c200',
0x00886980:'a13496c200c3',
0x0040CA60:'e90beeffff',
0x0040B883:'b960f9bb00e883e7ffff6810b0a900e81c574f0083c404b860f9bb00',
0x0040A010:'e97b999200',
0x00D339AA:'8d8e00060000c706d8b2aa00e8b50480ffeb',
0x00886B70:'52e83adcdaff8bc8e863dcdaffc3',
0x00886C60:'568bf2e848dbdaff89700c5ec3',
0x006347B0:'e90df0e5ff840504a6bf00751d090504a6bf00b9f8a4bf00e8e3f9ffff6840dda900e8dcc72c0083c404b8f8a4bf00c3',
0x006347E0:'558bec8b450883ec088941048b4dfc518b0d58a9bf00506a06e8922601008be55dc204',
0x00886C00:'e8abdbdaff8b4004c3',
0x00886C70:'e83bdbdaff8b400cc3',
}
EXPECTED_REL32={
0x0090481C:0x00A69160,0x00A69197:0x00886980,0x00886A66:0x0040CA60,
0x0040B888:0x0040A010,0x00886B71:0x006347B0,0x00886B78:0x006347E0,
0x00886C63:0x006347B0,0x00886C00:0x006347B0,0x00886C70:0x006347B0,
}
EXPECTED_REL32_JMP={0x0040CA60:0x0040B870,0x0040A010:0x00D33990,0x006347B0:0x004937C2,0x004937C7:0x006347B5}
VTABLE=0x00AAB2D8
VTABLE_SLOTS={0x80:0x00886B70,0x84:0x00886C00,0xA0:0x00886C60,0xA4:0x00886C70}

def parse(data):
 pe=struct.unpack_from('<I',data,0x3c)[0]; opt=pe+24
 if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',data,opt)[0]!=0x10b: raise ValueError('expected PE32')
 base=struct.unpack_from('<I',data,opt+28)[0]; n=struct.unpack_from('<H',data,pe+6)[0]; os=struct.unpack_from('<H',data,pe+20)[0]; tab=opt+os; secs=[]
 for i in range(n):
  o=tab+i*40; secs.append((struct.unpack_from('<I',data,o+12)[0],struct.unpack_from('<I',data,o+16)[0],struct.unpack_from('<I',data,o+20)[0]))
 return base,secs

def read(data,va,n):
 base,secs=parse(data); r=va-base
 for a,s,o in secs:
  if a<=r and r+n<=a+s:return data[o+r-a:o+r-a+n]
 raise ValueError(f'VA not file backed: 0x{va:08x}')

def rel32(data,site,opcode=0xe8):
 raw=read(data,site,5)
 if raw[0]!=opcode: raise ValueError(f'bad opcode at 0x{site:08x}')
 return site+5+struct.unpack_from('<i',raw,1)[0]

def analyze(path):
 data=path.read_bytes(); actual=hashlib.sha256(data).hexdigest()
 if actual!=RETAIL_SHA256: raise ValueError(actual)
 for va,h in EXPECTED_BYTES.items():
  b=bytes.fromhex(h)
  if read(data,va,len(b))!=b: raise ValueError(f'bytes mismatch 0x{va:08x}')
 for s,t in EXPECTED_REL32.items():
  if rel32(data,s)!=t: raise ValueError(f'call mismatch 0x{s:08x}')
 for s,t in EXPECTED_REL32_JMP.items():
  if rel32(data,s,0xe9)!=t: raise ValueError(f'jmp mismatch 0x{s:08x}')
 slots={f'+0x{k:x}':f'0x{struct.unpack("<I",read(data,VTABLE+k,4))[0]:08x}' for k in VTABLE_SLOTS}
 for k,t in VTABLE_SLOTS.items():
  if struct.unpack('<I',read(data,VTABLE+k,4))[0]!=t: raise ValueError(f'vtable mismatch +0x{k:x}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':actual,'machine_transfer_adjudicates':True},
  'startup_seed':{'site':'0x00904817','value':'0x00400000','call':'0x0090481c -> FUN_00a69160','argument_role':'first stack argument / module instance base'},
  'runtime_receiver':{
   'global':'0x00c29634','getter':'FUN_00886980','setup':'0x00886a66 calls thunk_FUN_0040b870 and stores returned 0x00bbf960 into 0x00c29634',
   'fixed_object':'0x00bbf960','constructor':'thunk_FUN_00d33990','vptr_store':'0x00d339b0 -> 0x00aab2d8','vtable':'0x00aab2d8','resolved_slots':slots},
  'module_base_sinks':[
   {'dispatch_slot':'+0x80','target':'FUN_00886b70','flow':'EDX -> stack arg -> FUN_006347e0','storage_singleton':'0x00bfa4f8','destination':'0x00bfa4fc / singleton+0x4','getter_slot':'+0x84','getter':'FUN_00886c00'},
   {'dispatch_slot':'+0xa0','target':'FUN_00886c60','flow':'EDX -> ESI -> [FUN_006347b0()+0xc]','storage_singleton':'0x00bfa4f8','destination':'0x00bfa504 / singleton+0xc','getter_slot':'+0xa4','getter':'FUN_00886c70'},
  ],
  'storage_singleton_proof':{'factory':'FUN_006347b0','all_paths_return':'0x00bfa4f8','setter_for_plus_4':'FUN_006347e0 writes its first stack argument to [ECX+0x4]','direct_plus_c_store':'FUN_00886c60 writes EDX-derived ESI to [FUN_006347b0()+0xc]'},
  'adjudication':{
   'p13a_startup_module_base_storage_subset_complete':True,'runtime_module_base_persistence_found':True,'runtime_module_base_storage_field_count':2,
   'runtime_module_base_fields_are_carrier_pointers':False,'runtime_module_base_getter_consumer_paths_complete':False,'manual_imagebase_plus_rva_pointer_construction_ruled_out':False,
   'encoded_or_reconstructed_carrier_pointers_ruled_out':False,'runtime_generated_or_copied_carrier_pointers_ruled_out':False,'runtime_callback_registration_ruled_out':False,
   'incoming_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This closes only startup propagation of the exact module base into two proven runtime storage fields.','The persisted value is the module base itself, not one of the 16 carrier entrypoints.','Downstream consumers of getters +0x84/+0xa4, arithmetic using the stored base, callback registration and incoming indirect dispatch remain open.','No slot or aggregate P1.3 gate is promoted.'],
  'next_step':'Trace consumers of FUN_00886c00/FUN_00886c70 (vtable +0x84/+0xa4) and classify any RVA arithmetic or callback registration before changing reconstruction/dispatch gates.'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();p=analyze(a.executable);s=json.dumps(p,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
