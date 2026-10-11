#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SLOTS={0xb83dc0:[0x552f59,0x553229,0x553a62,0xa79b0d],0xb83ec0:[0x553649,0x553b62]}
GETTERS={0x552f50:[0x8df2cf,0x8dfc06],0x553640:[0x8df037]}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def pe_sections(data):
 pe=struct.unpack_from('<I',data,0x3c)[0];n=struct.unpack_from('<H',data,pe+6)[0];opt=pe+24;osz=struct.unpack_from('<H',data,pe+20)[0];image=struct.unpack_from('<I',data,opt+28)[0];out=[]
 for j in range(n):
  x=opt+osz+j*40;name=data[x:x+8].split(b'\0',1)[0].decode('ascii','replace');vs,va,rs,rp=struct.unpack_from('<IIII',data,x+8);out.append((name,va,rs,rp))
 return image,out
def offset_to_va(data,fo):
 image,secs=pe_sections(data)
 for _,va,rs,rp in secs:
  if rp<=fo<rp+rs:return image+va+fo-rp
 raise KeyError(fo)
def raw_occurrences(data,value):
 pat=struct.pack('<I',value);return [offset_to_va(data,i) for i in range(len(data)) if data.startswith(pat,i)]
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,check=True,errors='replace');out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out[int(m.group(1),16)]=(m.group(2).lower(),re.sub(r'\s+',' ',m.group(3).strip()).replace(', ',','))
 return out
def analyze(exe):
 data=exe.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA;d=dis(exe)
 expected={0xb83dc0:[0x552f5b,0x55322a,0x553a63,0xa79b0f],0xb83ec0:[0x55364b,0x553b63]}
 for slot,vas in expected.items():assert raw_occurrences(data,slot)==vas
 required={0x552f59:('mov','DWORD PTR [eax],0xb83dc0'),0x553229:('mov','esi,0xb83dc0'),0x553a62:('mov','esi,0xb83dc0'),0xa79b0d:('mov','DWORD PTR ds:0xb83dc0,esi'),0x553649:('mov','DWORD PTR [eax],0xb83ec0'),0x553b62:('mov','esi,0xb83ec0')}
 for a,v in required.items():assert d[a]==v,(hex(a),d.get(a),v)
 for getter,calls in GETTERS.items():
  got=sorted(a for a,(m,o) in d.items() if m=='call' and o==hex(getter));assert got==calls
  assert len(raw_occurrences(data,getter))==0
 return {'format':'SHIFT.P1B.HDVehicle4330SourceSlotExactAddressSurface/1','version':1,'ready':True,'owner':'Process 1B / P1.3B','authority':{'platform':'PC retail 1.02','retail_executable_sha256':SHA,'upstream_contract':'SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15'},'surface':{'source_slots':[{'address':'0x00b83dc0','raw_dword_occurrence_count':4,'exact_instruction_sites':['0x00552f59','0x00553229','0x00553a62','0x00a79b0d'],'roles':['alias_getter_output_value','four_object_call_loop_base','four_object_direct_method_loop_base','direct_initializer_write_destination']},{'address':'0x00b83ec0','raw_dword_occurrence_count':2,'exact_instruction_sites':['0x00553649','0x00553b62'],'roles':['alias_getter_output_value','forty_one_object_direct_method_loop_base']}],'total_exact_source_slot_address_dword_occurrence_count':6,'alias_getters':[{'address':'0x00552f50','returned_base':'0x00b83dc0','returned_count':4,'direct_call_site_count':2,'direct_call_sites':['0x008df2cf','0x008dfc06'],'raw_function_address_dword_occurrence_count':0},{'address':'0x00553640','returned_base':'0x00b83ec0','returned_count':41,'direct_call_site_count':1,'direct_call_sites':['0x008df037'],'raw_function_address_dword_occurrence_count':0}],'total_static_alias_getter_direct_call_site_count':3,'total_static_alias_getter_function_address_dword_occurrence_count':0},'adjudication':{'exact_source_slot_address_literal_surface_complete':True,'exact_source_slot_alias_getter_static_entry_surface_complete':True,'source_slot_alias_getter_function_address_taken_found':False,'computed_or_runtime_alias_surface_complete':False,'runtime_or_alias_writer_provenance_complete':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only exact whole-image little-endian dword occurrences of the two source-slot addresses and the static entry surface of the two exact alias getters.','Computed addresses, copied aliases, runtime-created pointers and consumers reached through runtime-computed getter pointers remain outside this subset.','The getter caller paths are not yet promoted read-only by this contract.'],'next_step':'Classify the three direct alias-getter caller paths for read/write/escape behavior, then continue computed alias and runtime writer provenance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
