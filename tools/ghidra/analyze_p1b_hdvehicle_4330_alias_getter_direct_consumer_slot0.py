#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
WRITE_M={'mov','movzx','movsx','add','sub','xor','or','and','adc','sbb','inc','dec','neg','not','shl','sal','shr','sar','rol','ror','xchg','fstp','fistp','cmpxchg','xadd'}
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,check=True,errors='replace');out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),re.sub(r'\s+',' ',m.group(3).strip()).replace(', ',',')))
 return out
def analyze(exe):
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==SHA;rows=dis(exe);d={a:(m,o) for a,m,o in rows}
 calls={0x8df037:('call','0x553640'),0x8df2cf:('call','0x552f50'),0x8dfc06:('call','0x552f50')}
 for a,v in calls.items():assert d[a]==v,(hex(a),d.get(a),v)
 field_leas={
  0x8df142:'0xc',0x8df160:'0x10',0x8df17e:'0x1c',0x8df1ff:'0x18',0x8df21d:'0x14',0x8df23b:'0x38',
  0x8df3bb:'0xc',0x8df3d5:'0x10',0x8df400:'0x38',
  0x8dfcb3:'0xc',0x8dfccd:'0x10',0x8dfcf8:'0x38'}
 for a,off in field_leas.items():
  m,o=d[a];assert m=='lea' and o.endswith('+'+off+']'),(hex(a),m,o,off)
 ranges=[(0x8defc0,0x8df483),(0x8dfbd0,0x8dfd71)];nonstack=[]
 for a,m,o in rows:
  if any(lo<=a<hi for lo,hi in ranges):
   p=o.split(',') if o else []
   if p and '[' in p[0] and m in WRITE_M and '[ebp' not in p[0] and '[esp' not in p[0]:nonstack.append((a,m,o))
 assert nonstack==[],nonstack
 return {'format':'SHIFT.P1B.HDVehicle4330AliasGetterDirectConsumerSlot0Writer/1','version':1,'ready':True,'owner':'Process 1B / P1.3B','authority':{'platform':'PC retail 1.02','retail_executable_sha256':SHA,'upstream_contract':'SHIFT.P1B.HDVehicle4330SourceSlotExactAddressSurface/1'},'surface':{'direct_alias_getter_callsite_count':3,'caller_functions':[{'function_range':'0x008defc0-0x008df483','getter_calls':['0x008df037 -> 0x00553640','0x008df2cf -> 0x00552f50'],'nonstack_direct_memory_write_count':0},{'function_range':'0x008dfbd0-0x008dfd71','getter_calls':['0x008dfc06 -> 0x00552f50'],'nonstack_direct_memory_write_count':0}],'nonzero_field_pointer_argument_offsets':{'0x00b83dc0_stride_0x40':['0x0c','0x10','0x38'],'0x00b83ec0_stride_0x3c':['0x0c','0x10','0x14','0x18','0x1c','0x38']},'slot0_direct_memory_write_count':0,'slot0_pointer_argument_count':0,'slot0_write_or_pointer_escape_count':0},'adjudication':{'direct_alias_getter_consumer_slot0_writer_subset_complete':True,'direct_alias_getter_consumer_slot0_write_or_pointer_escape_found':False,'computed_or_runtime_alias_surface_complete':False,'runtime_or_alias_writer_provenance_complete':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This classifies only the three direct callsites of the two exact alias getters.','The direct consumers do expose addresses of nonzero object fields to helper calls, so this is specifically a slot0/table-pointer writer closure rather than an all-fields read-only claim.','Computed aliases, runtime-created getter pointers, indirect getter entry and unrelated writers remain open.'],'next_step':'Continue computed/copied/runtime alias provenance for the two source slots, using slot0 specifically as the writer target of interest.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
