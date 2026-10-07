from __future__ import annotations
import argparse, hashlib, json, re, struct
from pathlib import Path

SOURCE_SHA256="512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
EXE_MD5="705af8b420e5eb1e3834ac43d5533c6b"
EXE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
IMAGE_BASE=0x00400000
MESSAGES=(3,4,5,6,7)
SPANS={
 "broadcast_registry_thunk":(0x00408D7D,0x00408D88,"bbe9ee5675be56b1dea93bdd2ddcddf63989cba42ffa70011645c5d844e7a33d"),
 "broadcast_loop":(0x0065BD1C,0x0065BD6A,"58e695a7697a15e027927ce8c9c1daf68bf66fb5b55bf3c26a00a830cc724fc2"),
 "state_broadcasts_3_to_7":(0x00633810,0x006338FE,"3f2def63c74065c13a4d8b0ef8b23ab0fa2c1dc81edd84274878ab6cdd492403"),
 "controller_queue_event_default":(0x006551B0,0x00655208,"11f68ed9f58867072b989ab8025dd926e1f519b9ad56b5fc92c291a07d9cfee6"),
 "thread_queue_bind":(0x00649DC6,0x00649DF0,"46baed784b1fbdfa4939aef38f68001e090ce013f8a4d032d85dee8929c0781a"),
 "queue_init_flags":(0x00649BB8,0x00649BE7,"9b66d228cfb0b8bf6d19550ce14a2f1bfe3d7863d34a0394c6a27a61fde78cdd"),
 "controller_send":(0x00655220,0x00655273,"0673402b61df4b5079c12f85f45075025caf3a543be2157f7ef951df7dd51714"),
 "queue_enqueue":(0x00650350,0x00650392,"aac399569c05a994e2a0a4093e81397101ebe12a29dea3a1939ce8b17a25cfe4"),
 "setevent_wrapper":(0x0064F530,0x0064F53E,"3b4e286558bd0a53cc2f1f6e517fd763c858e0d4d0106ff4d17fe187092537a1"),
}

def digest(p:Path,a="sha256"):
 h=hashlib.new(a); h.update(p.read_bytes()); return h.hexdigest()

def fn(text:str,name:str)->str:
 m=re.search(r"(?m)^[^\n]*\b"+re.escape(name)+r"\([^\n]*\)\s*\n\s*\{",text)
 if not m: raise ValueError(f"missing {name}")
 i=text.find("{",m.start()); d=0
 for j in range(i,len(text)):
  d += text[j]=="{"; d -= text[j]=="}"
  if d==0: return text[m.start():j+1]
 raise ValueError(f"unterminated {name}")

def sections(data:bytes):
 pe=struct.unpack_from("<I",data,0x3c)[0]; n=struct.unpack_from("<H",data,pe+6)[0]; os=struct.unpack_from("<H",data,pe+20)[0]
 out=[]; table=pe+24+os
 for i in range(n):
  off=table+i*40; vs,va,rs,ro=struct.unpack_from("<IIII",data,off+8); out.append((va,max(vs,rs),ro))
 return out

def vabytes(data:bytes,start:int,end:int)->bytes:
 rva=start-IMAGE_BASE
 for va,size,ro in sections(data):
  if va<=rva and rva+(end-start)<=va+size:
   off=ro+rva-va; return data[off:off+end-start]
 raise ValueError(hex(start))

def need(body:str,*tokens:str):
 missing=[t for t in tokens if t not in body]
 if missing: raise ValueError(f"source drift: {missing!r}")

def build(source:Path,exe:Path):
 if digest(source)!=SOURCE_SHA256: raise ValueError("SHIFT.exe.c hash mismatch")
 if digest(exe,"md5")!=EXE_MD5 or digest(exe)!=EXE_SHA256: raise ValueError("SHIFT.exe hash mismatch")
 text=source.read_text(encoding="utf-8",errors="replace")
 create=fn(text,"thunk_FUN_00d36000"); reg=fn(text,"FUN_0065b750"); bcast=fn(text,"FUN_0065bd1c"); worker=fn(text,"FUN_00662880")
 ctor=fn(text,"FUN_006624a0"); thread=fn(text,"FUN_00649cb0"); entry=fn(text,"FUN_00649b10"); bind=fn(text,"FUN_00655000")
 send=fn(text,"FUN_00655220"); qinit=fn(text,"FUN_0064ff40"); enqueue=fn(text,"FUN_00650350"); setevent=fn(text,"FUN_0064f530")
 need(create,'pcVar6 = "Controller #1";','FUN_006339b0','FUN_00649e20')
 need(reg,'((int)this + 0x4c8)','FUN_0065b6b0','FUN_00649cb0')
 need(bcast,'FUN_00655220(*(int *)(iVar3 + 0xc),uVar1);')
 need(worker,'case 3:','case 4:','case 5:','case 6:','case 7:','FUN_006550a0((int)param_1,&local_24)','FUN_00649780(10,1)')
 need(ctor,'FUN_006551b0(param_1);','&PTR_FUN_00af0568')
 need(thread,'FUN_00649b10','*(undefined4 *)((int)pvVar3 + 0x5c) = uVar2;','FUN_00655000((int)param_2,pvVar3,uVar2);')
 need(entry,'uVar8 = 1;','uVar8 = 3;','FUN_0064ff40(*(int *)(pcVar1 + 0x5c)')
 need(bind,'*(undefined4 *)(param_1 + 8) = param_3;')
 need(send,'iVar1 = *(int *)(param_1 + 8);','FUN_00650350(iVar1,extraout_EDX,0,local_8);')
 need(qinit,'param_4 >> 1','param_4 & 1','"MsgQueue Event"')
 need(enqueue,'& 8','FUN_0064f530((undefined4 *)(param_1 + 0x40));')
 need(setevent,'SetEvent')
 for suffix in ("10","40","70","b0","e0"): need(fn(text,"FUN_006338"+suffix),'FUN_0065bd10();')
 if "FUN_00654ff0" in ctor or "FUN_00654ff0" in reg: raise ValueError("Controller #1 event flag setter appeared before startup")
 if any(x in send+enqueue for x in ("QueueUserAPC","NtQueueApcThread")): raise ValueError("APC primitive appeared in queue send")
 image=exe.read_bytes(); machine={}
 for name,(start,end,expected) in SPANS.items():
  actual=hashlib.sha256(vabytes(image,start,end)).hexdigest()
  if actual!=expected: raise ValueError(f"machine drift: {name}")
  machine[name]={"start":f"0x{start:08x}","end_exclusive":f"0x{end:08x}","sha256":actual}
 return {
  "format":"SHIFT.Process1Controller1BManagerQueueWake/1","ready":True,
  "source":{"authority":"PC retail 1.02","retail_executable_md5":EXE_MD5,"retail_executable_sha256":EXE_SHA256,"retail_source_sha256":SOURCE_SHA256,"xbox_recomp_required":False},
  "controller1":{"manager_registry":"BManager+0x4c8","queue_pointer":"Controller+0x08","thread_state_queue_pointer":"ThreadState+0x5c","worker":"FUN_00662880"},
  "producer":{"owner":"BManager state transitions","broadcast":"FUN_0065bd10/FUN_0065bd1c","messages":list(MESSAGES),"controller1_target_by_registry_identity":True,"shared_api_name_only_inference_used":False},
  "queue_wakeup":{"queue_init_argument":1,"queue_flags_after_init":7,"msgqueue_event_bit":8,"msgqueue_event_enabled":False,"enqueue":"FUN_00650350","setevent_is_bit8_gated":True,"normal_enqueue_calls_setevent":False,"enqueue_contains_apc_primitive":False},
  "adjudication":{"controller1_generic_queue_producer_join_proven":True,"controller1_bmanager_messages":list(MESSAGES),"queue_enqueue_is_apc_source":False,"queue_enqueue_interrupts_sleep_ex_via_msgqueue_event":False,"controller1_alertable_sleep_has_concrete_recovered_apc_wake_source_proven":False,"indirect_or_native_apc_injection_ruled_out":False,"render_or_present_phase_lock_proven":False},
  "machine_spans":machine,
  "next_blocker":{"process":1,"description":"resolve indirect/native APC injection; classify remaining non-broadcast FUN_00655220/FUN_00650350 producers by exact Controller #1 object identity and lifecycle"},
 }

def main():
 p=argparse.ArgumentParser(); p.add_argument("--source",type=Path,required=True); p.add_argument("--exe",type=Path,required=True); p.add_argument("--output",type=Path); a=p.parse_args(); out=json.dumps(build(a.source,a.exe),indent=2)+"\n"
 if a.output: a.output.write_text(out,encoding="utf-8")
 else: print(out,end="")
 return 0
if __name__=="__main__": raise SystemExit(main())
