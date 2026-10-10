#!/usr/bin/env python3
"""Bound x87 FSTENV/FNSTENV EIP-extraction paths for exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse, hashlib, json, re, sqlite3, struct, subprocess
from pathlib import Path

FORMAT="SHIFT.P1B.HDVehicle4330X87EipCaptureSurface/1"
RETAIL_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
EXPECTED_SITES=[0x004177E4,0x0050D063,0x00913763,0x00913A1B]
EXPECTED_FUNCS={
 "0x004175b9":("FUN_004175b9",554,"2f1e0bbee826c3bed7a4de238b353507f45e94327ab9db7ed91bc3d7dd6034ee"),
 "0x00417810":("thunk_FUN_0045c8d0",5,"68de32f85d6daf246c1b8163a07400b82021cdc7a881415976e223547625a126"),
 "0x0050d030":("thunk_FUN_004eb550",5,"68de32f85d6daf246c1b8163a07400b82021cdc7a881415976e223547625a126"),
 "0x0050d070":("thunk_FUN_0040cc70",5,"68de32f85d6daf246c1b8163a07400b82021cdc7a881415976e223547625a126"),
 "0x00913576":("FUN_00913576",518,"90627c4a22a36ead94ab385ea2bd3a2fe0bed4f50d017b0db352b9f08039e0b2"),
 "0x0091382e":("FUN_0091382e",518,"03b0f268c779a771fe2a96eec4d567a290d537f5ba05f1eaa91971d870af3da8"),
}
SECTION_RE=re.compile(r"^Disassembly of section ([^:]+):$")
INST_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(.*)$")
WINDOWS={
 0x004175D0:"ff248de4774100",
 0x004177E4:"d9774100e3754100e375410030764100d7754100547641008b7641004b77410068774100a8774100cc774100",
 0x0050D030:"e91be5fdff90ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccd9b3cccccccccccccccccccccce9fbfbefff",
 0x00913760:"83ec1cd9342481642404ffbc000009442404d9242483c41c595b58c3",
 0x00913A18:"83ec1cd9342481642404ffbc000009442404d9242483c41c595b58c3",
}
JUMP_TABLE=[0x004177D9,0x004175E3,0x004175E3,0x00417630,0x004175D7,0x00417654,0x0041768B,0x0041774B,0x00417768,0x004177A8,0x004177CC]


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()


def pe_map(data:bytes):
 pe=struct.unpack_from('<I',data,0x3c)[0];coff=pe+4;n=struct.unpack_from('<H',data,coff+2)[0];osz=struct.unpack_from('<H',data,coff+16)[0];opt=coff+20;base=struct.unpack_from('<I',data,opt+28)[0];table=opt+osz;secs=[]
 for i in range(n):
  o=table+i*40;name=data[o:o+8].split(b'\0',1)[0].decode(errors='replace');vs,va,rs,rp=struct.unpack_from('<IIII',data,o+8);secs.append((name,base+va,max(vs,rs),rp,rs))
 return secs


def bytes_at(data:bytes,secs,va:int,n:int)->bytes:
 for _,start,span,raw,raw_size in secs:
  if start<=va<start+span:return data[raw+(va-start):raw+(va-start)+n]
 raise ValueError(f'unmapped VA 0x{va:08x}')


def parse_objdump(text:str):
 section=None;inst=[]
 for line in text.splitlines():
  sm=SECTION_RE.match(line.strip())
  if sm:section=sm.group(1);continue
  im=INST_RE.match(line)
  if im and section:
   inst.append({"section":section,"address":int(im.group(1),16),"bytes":bytes.fromhex(im.group(2)),"asm":im.group(3).strip()})
 return inst


def x87_sites(inst):
 return [row for row in inst if row['asm'].lower().startswith(('fnstenv ','fstenv '))]


def direct_refs(inst,target:int):
 needle=f"0x{target:x}"
 return [{"address":f"0x{r['address']:08x}","asm":r['asm']} for r in inst if needle in r['asm'].lower()]


def analyze(exe:Path,database:Path)->dict:
 eh,dh=sha256(exe),sha256(database)
 if eh!=RETAIL_SHA256:raise ValueError(f'unexpected retail hash: {eh}')
 if dh!=SQLITE_SHA256:raise ValueError(f'unexpected sqlite hash: {dh}')
 data=exe.read_bytes();secs=pe_map(data)
 for va,hx in WINDOWS.items():
  expected=bytes.fromhex(hx)
  if bytes_at(data,secs,va,len(expected))!=expected:raise ValueError(f'machine window drift at 0x{va:08x}')
 proc=subprocess.run(['objdump','-d','-M','intel',str(exe)],check=True,capture_output=True,text=True,errors='replace')
 inst=parse_objdump(proc.stdout);sites=x87_sites(inst)
 got=[r['address'] for r in sites]
 if got!=EXPECTED_SITES:raise ValueError(f'x87 env-site drift: {[hex(x) for x in got]!r}')

 db=sqlite3.connect(database)
 try:
  row=db.execute("select value from metadata where key='format'").fetchone();fmt=None if row is None else row[0]
  if fmt not in SUPPORTED:raise ValueError(f'unsupported sqlite format: {fmt!r}')
  funcs=[]
  for addr,name,raw_text in db.execute('select address,name,raw_json from functions'):
   raw=json.loads(raw_text);size=int(raw.get('size') or 0)
   try:start=int(addr,16)
   except ValueError:continue
   if size:funcs.append((start,start+size,name))
  def owner(site):
   rows=[name for start,end,name in funcs if start<=site<end]
   if len(rows)>1:raise ValueError(f'multiple owners for 0x{site:08x}: {rows!r}')
   return rows[0] if rows else None
  owners={f'0x{site:08x}':owner(site) for site in EXPECTED_SITES}
  if owners!={"0x004177e4":None,"0x0050d063":None,"0x00913763":"FUN_00913576","0x00913a1b":"FUN_0091382e"}:
   raise ValueError(f'owner drift: {owners!r}')
  for addr,(name,size,digest) in EXPECTED_FUNCS.items():
   row=db.execute('select name,raw_json from functions where lower(address)=?',(addr,)).fetchone()
   if row is None:raise ValueError(f'missing function {addr}')
   raw=json.loads(row[1])
   if row[0]!=name or int(raw.get('size') or -1)!=size or raw.get('mnemonic_sha256')!=digest:raise ValueError(f'function identity drift: {addr}')
 finally:db.close()

 table=[struct.unpack('<I',bytes_at(data,secs,0x004177E4+i*4,4))[0] for i in range(11)]
 if table!=JUMP_TABLE:raise ValueError(f'jump-table drift: {table!r}')
 refs_4177=direct_refs(inst,0x004177E4)
 if refs_4177!=[{"address":"0x004175d0","asm":"jmp    DWORD PTR [ecx*4+0x4177e4]"}]:raise ValueError(f'jump-table ref drift: {refs_4177!r}')
 if direct_refs(inst,0x0050D063):raise ValueError('padding decode unexpectedly targeted by direct control flow')

 return {
  "format":FORMAT,"version":1,"ready":True,"owner":"Process 1B / P1.3B",
  "authority":{"platform":"PC retail 1.02","retail_executable_sha256":eh,"ghidra_sqlite_sha256":dh,"retail_machine_bytes_adjudicate":True,"objdump_role":"decoded x87-site inventory","sqlite_role":"function ownership/fingerprints"},
  "upstream_contracts":["SHIFT.P1B.HDVehicle4330CanonicalEipCaptureSurface/1","SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1"],
  "decoded_x87_env_sites":{"count":4,"addresses":[f'0x{x:08x}' for x in EXPECTED_SITES]},
  "classifications":[
   {"address":"0x004177e4","classification":"inline switch-table data, not instruction","owner":None,"proof":"0x004175d0 jumps through [ECX*4+0x004177e4]; 11 dwords are branch targets inside FUN_004175b9"},
   {"address":"0x0050d063","classification":"INT3 padding false decode, not function-owned instruction","owner":None,"proof":"between thunk_FUN_004eb550 end and thunk_FUN_0040cc70 start; no direct control-flow target"},
   {"address":"0x00913763","classification":"real FNSTENV save/modify/reload; no saved-EIP extraction","owner":"FUN_00913576","proof":"only saved-env RMW is [ESP+4], followed by FLDENV [ESP] and stack release"},
   {"address":"0x00913a1b","classification":"real FNSTENV save/modify/reload; no saved-EIP extraction","owner":"FUN_0091382e","proof":"only saved-env RMW is [ESP+4], followed by FLDENV [ESP] and stack release"},
  ],
  "adjudication":{"decoded_x87_env_site_surface_complete":True,"decoded_x87_env_site_count":4,"real_x87_env_save_instruction_count":2,"x87_saved_eip_extraction_found":False,"x87_fstenv_eip_capture_surface_complete":True,"noncanonical_eip_capture_surface_complete":False,"runtime_computed_carrier_pointers_ruled_out":False,"runtime_copied_or_encoded_carrier_pointers_ruled_out":False,"indirect_entry_into_carriers_ruled_out":False,"global_runtime_derived_4330_alias_surface_complete":False,"manager_374_join_to_hdvehicle_4330_complete":False,"last_literal_0x004b86cf_rejected":False,"p1_3_control_producer_complete":False,"external_provider_count":7},
  "limits":["This closes decoded FSTENV/FNSTENV instruction-pointer extraction only.","Two objdump-looking sites are proven inline data/padding rather than instructions; two real sites never extract an environment instruction pointer.","Other noncanonical EIP/address synthesis, runtime copies, transformed constants and encoded pointers remain open."],
  "next_step":"Continue non-x87 computed pointer synthesis and runtime callback-pointer copies; do not promote indirect-entry or manager identity gates yet."
 }


def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe',type=Path);p.add_argument('database',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.exe,a.database)
 except (ValueError,subprocess.CalledProcessError) as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(t,encoding='utf-8')
 else:print(t,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
