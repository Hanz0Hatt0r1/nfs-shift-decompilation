#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun00757d2cRuntimeIndexedWheelRootPersistence/1'
UPSTREAM_FORMAT='SHIFT.GlobalVehicleComponentCallsiteStatic/1'
SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
START=0x00757d2c; END=0x00757e51; BODY_SHA='587dcc93159ef142ef57d18e657aa3078e5d2748db0febb4ecba32a286bc20fa'
TEXT_VA=0x00401000; TEXT_RAW=0x400
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def disasm(exe):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{START:x}',f'--stop-address=0x{END:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=INST_RE.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def require(imap,a,mn,ops=''):
 got=imap.get(a); exp=(mn,norm(ops))
 if got!=exp: raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {mn} {exp[1]}'.rstrip()
def analyze(exe:Path,upstream:Path):
 b=exe.read_bytes(); sha=hashlib.sha256(b).hexdigest()
 if sha!=SHA256:raise ValueError(sha)
 off=TEXT_RAW+(START-TEXT_VA); body=b[off:off+(END-START)]
 if len(body)!=293 or hashlib.sha256(body).hexdigest()!=BODY_SHA:raise AssertionError('body drift')
 u=json.loads(upstream.read_text())
 if u['format']!=UPSTREAM_FORMAT:raise ValueError(u['format'])
 cs=u['runtime_component_callsite']
 expected={'callee_core':'0x00757d2c','vehicle_pointer_register_at_core_entry':'ECX','component_offset_register_at_core_entry':'EAX','vehicle_base_address':'0x00c13700','component_base_offset':'0x400','component_stride':'0xa80','component_count':4,'component_offset_rule':'slot * 0xa80'}
 for k,v in expected.items():
  if cs.get(k)!=v:raise AssertionError((k,cs.get(k),v))
 rows=disasm(exe); imap={a:(m,o) for a,m,o in rows}
 anchors={
 'root_materialization':require(imap,0x757d2e,'lea','eax,[eax+ecx*1+0x400]'),
 'root_child_424_read':require(imap,0x757d36,'mov','edi,DWORD PTR [eax+0x424]'),
 'root_scalar_504_write':require(imap,0x757d43,'mov','BYTE PTR [eax+0x504],bl'),
 'root_scalar_540_write':require(imap,0x757d4b,'mov','BYTE PTR [eax+0x540],bl'),
 'root_kill_fast':require(imap,0x757d51,'mov','eax,DWORD PTR [ecx+0x339c]'),
 'root_child_420_read':require(imap,0x757d93,'mov','edx,DWORD PTR [eax+0x420]'),
 'root_kill_slow':require(imap,0x757d99,'mov','eax,DWORD PTR [ecx+0x339c]'),
 'child_stack_store':require(imap,0x757da4,'mov','DWORD PTR [ebp+0x8],edx')}
 live=[r for r in rows if 0x757d2e<=r[0]<0x757d51 or 0x757d93<=r[0]<0x757d99]
 bad=[]; root_mem=[]
 for a,m,o in live:
  if m=='push' and o=='eax': bad.append((a,m,o))
  if m=='mov' and ',' in o:
   dst,src=o.split(',',1)
   if src=='eax' and '[' in dst: bad.append((a,m,o))
   if src=='eax' and dst in {'ebx','ecx','edx','esi','edi'}: bad.append((a,m,o))
  if m=='lea' and o.endswith(',eax'): bad.append((a,m,o))
  if '[eax' in o: root_mem.append({'address':f'0x{a:08x}','mnemonic':m,'operands':o})
 if bad:raise AssertionError(bad)
 transfers=[(a,m,o) for a,m,o in live if m in {'call','jmp'}]
 if transfers:raise AssertionError(transfers)
 slots=[]
 for i,offv in enumerate([0x400,0xe80,0x1900,0x2380]):
  slots.append({'slot':i,'wheel_root':f'HDVehicle+0x{offv:x}','selected_target':f'HDVehicle+0x{offv+0x538:x}..+0x{offv+0x53f:x}'})
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
 'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_body_start':'0x00757d2c','machine_body_end_exclusive':'0x00757e51','machine_body_size':len(body),'machine_body_sha256':BODY_SHA,'upstream_runtime_identity_contract':UPSTREAM_FORMAT},
 'runtime_identity':{'caller':cs['caller'],'call_address':cs['call_address'],'return_address':cs['return_address'],'vehicle_base_address':cs['vehicle_base_address'],'core_entry_abi':'ECX=vehicle, EAX=slot*0xa80','wheel_root_formula':'vehicle + 0x400 + slot*0xa80','component_count':4,'slots':slots},
 'exact_root_lifetime':{'materialization':'0x00757d2e','register':'EAX','fast_path_kill':'0x00757d51','slow_path_last_root_use':'0x00757d93','slow_path_kill':'0x00757d99','root_value_nonstack_store_count':0,'root_value_push_count':0,'root_value_register_copy_count':0,'root_value_call_or_jump_while_live_count':0,'root_memory_accesses':root_mem,'child_pointer_note':'[wheel+0x420] is loaded to EDX on the slow path and written only to stack slot [EBP+0x8] here; it is not the exact wheel-root value.'},
 'machine_anchors':anchors,
 'adjudication':{'p13a_fun00757d2c_runtime_indexed_wheel_root_subset_complete':True,'runtime_indexed_exact_wheel_root_materialization_found':True,'runtime_indexed_exact_wheel_root_persistent_escape_found':False,'runtime_indexed_exact_wheel_root_selected_slot0_or_slot1_store_found':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This closes only the source-backed runtime indexed wheel-root materializer in FUN_00757d2c.','A positive exact wheel-root reconstruction exists, so the global reconstructed-wheel-pointer gate remains fail-closed; this contract proves only that this reconstructed root does not itself escape or persist.','The slow path loads child=[wheel+0x420]; child aliases are a separate pointer class and are not promoted to wheel-root identity.','Other indexed/loop/fixed wheel-root materializers, copied pointers, callbacks and incoming indirect entry remain open.'],
 'next_step':'Inventory the remaining exact four-wheel/indexed materializers (especially FUN_00757318, FUN_007582f0, FUN_007653f9 and FUN_0076ed60) and classify root-value stores/copies before changing the runtime-generated selected-wheel pointer gate.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
if __name__=='__main__':main()
