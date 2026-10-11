#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
CARRIERS={0x769520,0x76b130,0x76df50,0x768a4d,0x756050,0x772200,0x772570,0x7c3b00,0x76b280,0x7618f0,0x769640,0x7567a0,0x756bb0,0x771db0,0x771e10}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def va_reader(data):
 pe=struct.unpack_from('<I',data,0x3c)[0]; assert data[pe:pe+4]==b'PE\0\0'
 n=struct.unpack_from('<H',data,pe+6)[0]; opt=pe+24; osz=struct.unpack_from('<H',data,pe+20)[0]; assert struct.unpack_from('<H',data,opt)[0]==0x10b
 image=struct.unpack_from('<I',data,opt+28)[0]; secs=[]; off=opt+osz
 for j in range(n):
  x=off+j*40; vs,va,rs,rp=struct.unpack_from('<IIII',data,x+8); secs.append((va,max(vs,rs),rp))
 def u32(addr):
  rva=addr-image
  for va,span,rp in secs:
   if va<=rva<va+span:return struct.unpack_from('<I',data,rp+rva-va)[0]
  raise KeyError(hex(addr))
 return u32
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,check=True,errors='replace'); out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out[int(m.group(1),16)]=(m.group(2).lower(),re.sub(r'\s+',' ',m.group(3).strip()).replace(', ',','))
 return out
def require(d,a,m,o): assert d[a]==(m,o),(hex(a),d.get(a),(m,o))
def analyze(exe):
 data=exe.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 u32=va_reader(data); d=dis(exe)
 require(d,0x553240,'mov','eax,DWORD PTR [esi]'); require(d,0x553242,'mov','edx,DWORD PTR [eax+0x4]'); require(d,0x553247,'call','edx')
 require(d,0x55399a,'mov','eax,DWORD PTR [edi-0x10]'); require(d,0x5539a0,'mov','edx,DWORD PTR [eax+0x4]'); require(d,0x5539ac,'call','edx')
 require(d,0xa79af0,'mov','esi,0xacdd70'); require(d,0xa79b0d,'mov','DWORD PTR ds:0xb83dc0,esi')
 require(d,0xa9d6d7,'mov','esi,0xb83ef4'); require(d,0xa9d6e0,'sub','esi,0x40'); require(d,0xa9d6e6,'mov','DWORD PTR [esi-0x34],0xacdd68')
 require(d,0xa9d737,'mov','esi,0xb84890'); require(d,0xa9d740,'sub','esi,0x3c'); require(d,0xa9d746,'mov','DWORD PTR [esi-0x34],0xacdd68')
 dc0_reset=[0xb83ef4-0x40*(i+1)-0x34 for i in range(4)]; ec0_reset=[0xb84890-0x3c*(i+1)-0x34 for i in range(41)]
 assert dc0_reset[-1]==0xb83dc0 and ec0_reset[-1]==0xb83ec0
 assert (u32(0xb83dc0),u32(0xb83ec0))==(0xacdd68,0xacdd68)
 table={0xacdd68:u32(0xacdd6c),0xacdd70:u32(0xacdd74)}; assert table=={0xacdd68:0x553a90,0xacdd70:0x553260}
 dc0_targets={table[x] for x in {0xacdd68,0xacdd70}}; ec0_targets={table[0xacdd68]}; all_targets=dc0_targets|ec0_targets; assert not(all_targets&CARRIERS)
 return {'format':'SHIFT.P1B.HDVehicle4330BaseIndexedMemoryDerivedCallTargetProvenance/1','version':1,'ready':True,'owner':'Process 1B / P1.3B','authority':{'platform':'PC retail 1.02','retail_executable_sha256':SHA},'surface':{'target_derived_call_count':2,'bounded_static_initializer_writer_subset_complete':True,'bounded_target_table_pointer_values':['0x00acdd68','0x00acdd70'],'bounded_callable_target_values':[f'0x{x:08x}' for x in sorted(all_targets)],'canonical_p1b_carrier_count':15,'bounded_callable_target_exact_carrier_hit_count':0,'calls':[{'call_site':'0x00553247','source_slot':'0x00b83dc0','table_pointer_values':['0x00acdd68','0x00acdd70'],'callable_target_values':['0x00553260','0x00553a90']},{'call_site':'0x005539ac','source_slot':'0x00b83ec0','table_pointer_values':['0x00acdd68'],'callable_target_values':['0x00553a90']}],'image_initial_values':{'0x00b83dc0':'0x00acdd68','0x00b83ec0':'0x00acdd68'},'table_plus_4_targets':{'0x00acdd68':'0x00553a90','0x00acdd70':'0x00553260'},'bounded_writer_evidence':{'0x00b83dc0':['image=0x00acdd68','0x00a79af0 -> 0x00a79b0d writes 0x00acdd70','0x00a9d6d0 four-object reset loop includes slot and writes 0x00acdd68'],'0x00b83ec0':['image=0x00acdd68','0x00a9d730 41-object reset loop includes slot and writes 0x00acdd68']}},'adjudication':{'bounded_static_initializer_target_provenance_complete':True,'bounded_static_initializer_target_can_hit_exact_p1b_carrier':False,'runtime_or_alias_writer_provenance_complete':False,'memory_derived_indirect_call_target_identity_complete':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only image-initial and exact visible initializer/reset writers for the two selected source slots.','Computed aliases, arbitrary runtime mutation, heap/object replacement and other writers remain open; exact runtime target identity is therefore not complete.'],'next_step':'Bound computed/alias/runtime writers for 0x00b83dc0 and 0x00b83ec0, then compose this negative exact-carrier target subset into aggregate coverage.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
