#!/usr/bin/env python3
"""Close exact-root persistence in residual indexed materializers FUN_00765850/FUN_00765aa0."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AResidualIndexedWheelRootLifetimes/1'
RETAIL_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
RANGES={
 'selected_caller_fun00765850_a':(0x0074d983,0x0074d98d,'ce125396503a0b863689591d27e1b6a8f1590b112d322d44e6d9e6c6fceca14b'),
 'selected_caller_fun00765850_b':(0x00713b06,0x00713b10,'92179493933149cf264ec44a8887e143bf0f3469b10fd6ecb7fff1335dc97830'),
 'selected_caller_fun00765aa0':(0x00713ac2,0x00713acc,'9e165eeb62186e0e1f02c5ce4397ada83c1825d42c88153daef26d68354625b9'),
 'fun00765850':(0x00765850,0x00765a93,'279d20bf853889e31a7e7d594fdde5d79d323435894629aa25925697c2069d19'),
 'fun00765aa0':(0x00765aa0,0x00765c37,'c094c028f42dedd868fb39179db7906e386b5a84217b6ff008e2767960761ae4'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
REGS={'eax','ebx','ecx','edx','esi','edi'}

def pe_sections(b):
 pe=struct.unpack_from('<I',b,0x3c)[0];co=pe+4;n=struct.unpack_from('<H',b,co+2)[0];os=struct.unpack_from('<H',b,co+16)[0];op=co+20;ib=struct.unpack_from('<I',b,op+28)[0];sh=op+os;out=[]
 for i in range(n):
  o=sh+i*40;vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);out.append((ib+va,max(vs,rs),rp))
 return out

def raw(b,secs,s,e):
 for va,span,rp in secs:
  if va<=s and e<=va+span:return b[rp+s-va:rp+e-va]
 raise ValueError(hex(s))

def norm(x):return re.sub(r'\s+',' ',x.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out

def M(rows):return {a:(m,o) for a,m,o in rows}
def req(mp,a,m,o):
 exp=(m,norm(o));got=mp.get(a)
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'

def exact_root_events(rows,materialize,spill,kill,reload):
 live=False; aliases=set(); out={'stack_spills':[],'nonstack_stores':[],'register_copies':[],'pushes':[],'exact_receiver_calls':[]}
 for a,m,o in rows:
  if a==materialize:
   live=True;aliases={'edi'};continue
  if a==kill:
   live=False;aliases.clear();continue
  if a==reload:
   live=True;aliases={'edi'};continue
  if not live:continue
  if m=='push' and o in aliases:out['pushes'].append(f'0x{a:08x}')
  if m=='mov' and ',' in o:
   dst,src=o.split(',',1)
   if src in aliases:
    if dst.startswith(('DWORD PTR [ebp','DWORD PTR [esp')):out['stack_spills'].append({'site':f'0x{a:08x}','dst':dst})
    elif dst.startswith(('BYTE PTR [','WORD PTR [','DWORD PTR [','QWORD PTR [')):out['nonstack_stores'].append({'site':f'0x{a:08x}','dst':dst})
    elif dst in REGS:
     aliases.add(dst);out['register_copies'].append({'site':f'0x{a:08x}','dst':dst,'src':src})
   elif dst in aliases and src not in aliases:
    aliases.discard(dst)
  elif m in {'lea','xor','add','sub','and','or','imul','movzx','movsx','pop'}:
   dst=o.split(',',1)[0]
   if dst in aliases:aliases.discard(dst)
  if m=='call' and 'ecx' in aliases:out['exact_receiver_calls'].append({'site':f'0x{a:08x}','target':o})
 if out['stack_spills'] != [{'site':f'0x{spill:08x}','dst':'DWORD PTR [ebp-0x24]' if spill==0x76589a else 'DWORD PTR [ebp-0x1c]'}]:
  raise AssertionError(('stack spill surface',out['stack_spills']))
 return out

def analyze(exe:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=RETAIL_SHA:raise ValueError(sha)
 secs=pe_sections(b);auth={}
 for n,(s,e,h) in RANGES.items():
  d=raw(b,secs,s,e);g=hashlib.sha256(d).hexdigest()
  if g!=h:raise AssertionError(('range drift',n,g,h))
  auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 C1=M(dis(exe,0x74d983,0x74d98d));C2=M(dis(exe,0x713b06,0x713b10));C3=M(dis(exe,0x713ac2,0x713acc))
 A=dis(exe,0x765850,0x765a93);B=dis(exe,0x765aa0,0x765c37);AM=M(A);BM=M(B)
 anchors={
  'selected_65850_literal_a':req(C1,0x74d983,'mov','ecx,0xc13700'),'selected_65850_call_a':req(C1,0x74d988,'call','0x765850'),
  'selected_65850_literal_b':req(C2,0x713b06,'mov','ecx,0xc13700'),'selected_65850_call_b':req(C2,0x713b0b,'call','0x765850'),
  'selected_65aa0_literal':req(C3,0x713ac2,'mov','ecx,0xc13700'),'selected_65aa0_call':req(C3,0x713ac7,'call','0x765aa0'),
  '65850_index_stride':req(AM,0x765878,'imul','eax,eax,0xa80'),'65850_root':req(AM,0x76588b,'lea','edi,[eax+ecx*1+0x400]'),
  '65850_root_spill':req(AM,0x76589a,'mov','DWORD PTR [ebp-0x24],edi'),'65850_child_kill':req(AM,0x7659b8,'mov','edi,DWORD PTR [edi+0x424]'),
  '65850_root_reload':req(AM,0x765a57,'mov','edi,DWORD PTR [ebp-0x24]'),'65850_final_scalar_store':req(AM,0x765a82,'fstp','QWORD PTR [edi+0x520]'),
  '65aa0_index_stride':req(BM,0x765abe,'imul','eax,eax,0xa80'),'65aa0_vehicle_capture':req(BM,0x765ac5,'mov','esi,ecx'),
  '65aa0_root':req(BM,0x765ac8,'lea','edi,[eax+esi*1+0x400]'),'65aa0_root_spill':req(BM,0x765ad2,'mov','DWORD PTR [ebp-0x1c],edi'),
  '65aa0_child_kill':req(BM,0x765b5c,'mov','edi,DWORD PTR [edi+0x424]'),'65aa0_root_reload':req(BM,0x765bf8,'mov','edi,DWORD PTR [ebp-0x1c]'),
  '65aa0_final_byte_store':req(BM,0x765c1f,'mov','BYTE PTR [edi+0x505],0x0'),'65aa0_final_scalar_store':req(BM,0x765c26,'fstp','QWORD PTR [edi+0x520]'),
 }
 ae=exact_root_events(A,0x76588b,0x76589a,0x7659b8,0x765a57);be=exact_root_events(B,0x765ac8,0x765ad2,0x765b5c,0x765bf8)
 for name,ev in [('FUN_00765850',ae),('FUN_00765aa0',be)]:
  if ev['nonstack_stores'] or ev['register_copies'] or ev['pushes'] or ev['exact_receiver_calls']:raise AssertionError((name,ev))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_bytes_adjudicate':True,'ranges':auth},
  'selected_hdvehicle_entry':{
   'FUN_00765850':[{'literal':'0x00c13700','call':'0x0074d988'},{'literal':'0x00c13700','call':'0x00713b0b'}],
   'FUN_00765aa0':[{'literal':'0x00c13700','call':'0x00713ac7'}],
  },
  'indexed_materializers':[
   {'function':'FUN_00765850','formula':'HDVehicle+0x400+index*0xa80','root_register':'EDI','root_stack_spill':'[EBP-0x24]','child_identity_kill':'0x007659b8 EDI=[root+0x424]','root_reload':'0x00765a57','exact_root_events':ae,'persistent_exact_root_escape_found':False},
   {'function':'FUN_00765aa0','formula':'HDVehicle+0x400+index*0xa80','root_register':'EDI','root_stack_spill':'[EBP-0x1c]','child_identity_kill':'0x00765b5c EDI=[root+0x424]','root_reload':'0x00765bf8','exact_root_events':be,'persistent_exact_root_escape_found':False},
  ],
  'machine_anchors':anchors,
  'adjudication':{
   'p13a_residual_indexed_wheel_root_lifetime_subset_complete':True,
   'fun00765850_exact_root_persistent_escape_found':False,'fun00765aa0_exact_root_persistent_escape_found':False,
   'residual_indexed_exact_root_nonstack_store_found':False,'residual_indexed_exact_root_push_found':False,
   'residual_indexed_exact_root_direct_callee_forward_found':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This closes exact-root lifetime only in FUN_00765850 and FUN_00765aa0 after machine-proven selected-HDVehicle direct entry; child/interior pointers are separate values.',
   'Each exact root is spilled only to a stack local, later EDI is replaced by a child/derived pointer, and the exact root is reloaded only for final scalar wheel-field writes.',
   'No exact root is stored to non-stack memory, pushed, copied to a new GPR alias, or forwarded as an ECX receiver while exact-root identity is live.',
   'The positive FUN_0076df50 runtime queue store and all broader runtime/callback/stored-alias gates remain independent and fail-closed.'
  ],
  'next_step':'Compose these residual indexed lifetimes with the known-materializer handoff and the positive FUN_0076df50 queue-store contract, then continue exact consumer tracing from wheel virtual target 0x0075cfb0.'
 }

def main():
 p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
