#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AModuleBaseImmediateDispatchClosure/1'
RETAIL_SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SINGLETON_GETTER=0x00886980
FIELD_GETTERS={0x00886C00:'+0x84 / module-base field +0x4',0x00886C70:'+0xa4 / module-base field +0xc'}
MAX_INSTRUCTIONS=16
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
RR=re.compile(r'^(eax|ebx|ecx|edx|esi|edi),(eax|ebx|ecx|edx|esi|edi)$')
MEM=re.compile(r'^(eax|ebx|ecx|edx|esi|edi),DWORD PTR \[(eax|ebx|ecx|edx|esi|edi)(?:\+0x([0-9a-fA-F]+))?\]$')
IND_MEM=re.compile(r'^DWORD PTR \[(eax|ebx|ecx|edx|esi|edi)\+0x([0-9a-fA-F]+)\]$')
DIRECT=re.compile(r'^0x([0-9a-fA-F]+)$')
WRITE_MNEMONICS={'mov','lea','xor','add','sub','and','or','shl','shr','sar','sal','movzx','movsx','pop','inc','dec','imul'}
REGS={'eax','ebx','ecx','edx','esi','edi'}

def written_reg(mn,ops):
 if mn not in WRITE_MNEMONICS:return None
 first=ops.split(',',1)[0].strip()
 return first if first in REGS else None

def scan_lines(lines):
 direct_getter_calls=[]; direct_field_getter_transfers=[]; hits=[]; active=[]
 for line in lines:
  m=INST_RE.match(line)
  if not m:continue
  addr=int(m.group(1),16); mn=m.group(2).lower(); ops=m.group(3).strip()
  dm=DIRECT.match(ops) if mn in ('call','jmp') else None
  if dm:
   target=int(dm.group(1),16)
   if target in FIELD_GETTERS: direct_field_getter_transfers.append({'site':f'0x{addr:08x}','kind':mn,'target':f'0x{target:08x}','getter':FIELD_GETTERS[target]})
  nxt=[]
  for st in active:
   st['steps']+=1; aliases=st['aliases']; vptrs=st['vptrs']; methods=st['methods']
   rr=RR.match(ops) if mn=='mov' else None
   mem=MEM.match(ops) if mn=='mov' else None
   if rr:
    dst,src=rr.groups()
    if src in aliases: aliases.add(dst)
    else: aliases.discard(dst)
    if src in vptrs: vptrs.add(dst)
    else: vptrs.discard(dst)
    if src in methods: methods[dst]=methods[src]
    else: methods.pop(dst,None)
   elif mem:
    dst,base,imm=mem.groups(); off=int(imm,16) if imm else 0
    base_is_alias=base in aliases; base_is_vptr=base in vptrs
    aliases.discard(dst); vptrs.discard(dst); methods.pop(dst,None)
    if base_is_alias and off==0:vptrs.add(dst)
    elif base_is_vptr:methods[dst]=off
   else:
    dst=written_reg(mn,ops)
    if dst:
     aliases.discard(dst);vptrs.discard(dst);methods.pop(dst,None)
   if mn=='call':
    im=IND_MEM.match(ops)
    if im and im.group(1) in vptrs:
     hits.append({'singleton_getter_call':f"0x{st['origin']:08x}",'dispatch_site':f'0x{addr:08x}','slot':f'+0x{int(im.group(2),16):x}','form':'call-memory'})
    elif ops in methods:
     hits.append({'singleton_getter_call':f"0x{st['origin']:08x}",'dispatch_site':f'0x{addr:08x}','slot':f'+0x{methods[ops]:x}','form':'call-register'})
    continue
   if st['steps']<MAX_INSTRUCTIONS:nxt.append(st)
  active=nxt
  if mn=='call' and dm and int(dm.group(1),16)==SINGLETON_GETTER:
   direct_getter_calls.append(f'0x{addr:08x}'); active.append({'origin':addr,'steps':0,'aliases':{'eax'},'vptrs':set(),'methods':{}})
 return direct_getter_calls,direct_field_getter_transfers,hits

def disassemble(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout
 out=scan_lines(p.stdout); err=p.stderr.read() if p.stderr else '';rc=p.wait()
 if rc:raise RuntimeError(err)
 return out

def analyze(exe):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=RETAIL_SHA256:raise ValueError(sha)
 calls,direct_getters,hits=disassemble(exe); counts=collections.Counter(r['slot'] for r in hits)
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_disassembly_adjudicates':True},
 'scope':{'singleton_getter':'FUN_00886980','singleton_getter_address':'0x00886980','max_instructions_after_getter':MAX_INSTRUCTIONS,'window_stops_at_first_other_call':True,'tracked_shape':'return alias -> vptr load -> slot load -> indirect call'},
 'inventory':{'direct_singleton_getter_call_count':len(calls),'direct_field_getter_transfer_count':len(direct_getters),'immediate_virtual_dispatch_count':len(hits),'slot_counts':dict(sorted(counts.items())),'module_base_getter_slot_0x84_count':counts['+0x84'],'module_base_getter_slot_0xa4_count':counts['+0xa4']},
 'direct_field_getter_transfers':direct_getters,'immediate_virtual_dispatches':hits,
 'adjudication':{'p13a_module_base_immediate_dispatch_subset_complete':True,'direct_module_base_field_getter_transfer_found':bool(direct_getters),'immediate_module_base_getter_dispatch_found':bool(counts['+0x84'] or counts['+0xa4']),'module_base_getter_consumer_paths_complete':False,'delayed_or_stored_receiver_alias_dispatch_ruled_out':False,'runtime_callback_registration_ruled_out':False,'incoming_indirect_entry_ruled_out':False,'encoded_or_reconstructed_carrier_pointers_ruled_out':False,'runtime_generated_or_copied_carrier_pointers_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This closes only direct transfers to the two field-getter bodies and immediate virtual dispatches within 16 instructions of a direct FUN_00886980 call, stopping at the first intervening call.','Stored/delayed receiver aliases, callbacks, indirect entry and dispatch recovered only at runtime remain open.','Numeric +0x84/+0xa4 references on unrelated objects are deliberately excluded; slot identity requires the tracked FUN_00886980 receiver.','No slot or aggregate P1.3 gate is promoted.'],
 'next_step':'Trace delayed/stored aliases of the exact 0x00bbf960 receiver and runtime registration/indirect consumers; continue selected-wheel data-pointer persistence independently.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
