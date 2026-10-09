#!/usr/bin/env python3
"""Verify semantic closure of the shallow P1.3A unrolled-MOV copy frontier."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

FORMAT='SHIFT.P1A.P13ASlot01UnrolledMovCopyMachineClosure/1'
RETAIL_SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
FRONTIER_FORMAT='SHIFT.P1A.P13ASlot01UnrolledMovCopyFrontier/1'
EXPECTED_CANDIDATES=[
 'FUN_0076e560','FUN_007b0710','FUN_00403d00','FUN_004e9380','FUN_00633290',
 'FUN_006333f0','FUN_0075a8d0','FUN_007b0580','FUN_0064fef0','FUN_007b0450','_LocaleUpdate'
]
EXPECTED_BYTES={
0x00771069:'8bce',0x00771098:'e8c3d4ffff',0x0076e57a:'8bf1',0x0076e75e:'e82d17faff',0x0076e763:'8bb888020000',0x0076e772:'8bcf',0x0076e774:'e817c4f9ff',0x0076e77d:'8b55fc',0x0076e7a6:'894208',0x0076e7b7:'89420c',0x0076e82d:'894a08',0x0076e83c:'894a0c',
0x00765e38:'8d8d20ffffff',0x007b0c8a:'8bcf',0x007b0c8e:'e8cde8f9ff',0x007b0c93:'8bf0',0x007b0cca:'894648',0x007b0ccd:'894e4c',
0x0076d77d:'8d55f0',0x0076d787:'e804cbf9ff',0x0076d7b5:'8b4df0',0x0076d7b9:'e84265c9ff',0x00403d03:'8bc1',0x00403d5f:'895004',0x00403d65:'894808',
0x007b0cf4:'b9e0b9c100',0x007b0cf9:'e88286d3ff',0x004e9387:'8bd9',0x004e93cb:'8b93e0000000',0x004e9454:'890e',0x004e9459:'895604',0x004e945c:'894608',0x004e945f:'894e0c',
0x0070abec:'c745fc00000000',0x0070abf9:'e89286f2ff',0x006332ac:'8d7310',0x006332d6:'e8454d0000',0x006332ee:'8938',0x006332f4:'894804',0x006332f7:'895008',
0x00767cbc:'8dbec8400000',0x00767cc2:'57',0x00767cce:'8bce',0x00767cd3:'e8f82bffff',0x0075ad4f:'8b4510',0x0075ad5c:'8908',0x0075ad61:'894804',0x0075ad67:'895008',0x0075ad6a:'89480c',
0x007b0919:'8d55a8',0x007b091e:'b9e0b9c100',0x007b092a:'e851fcffff',0x007b0590:'8bf2',0x007b05cc:'895608',0x007b05d2:'89560c',0x007b05df:'894e18',0x007b05e6:'89561c',
0x0063341e:'8d5508',0x00633421:'e8caca0100',0x0064fef5:'8bf9',0x0064fefd:'8bf2',0x0064feff:'e8ecf7fdff',0x0064ff0c:'8908',0x0064ff1e:'894808',0x0064ff21:'89500c',
0x007b0ce4:'6a00',0x007b0ce6:'6a00',0x007b0ce8:'6a00',0x004e9479:'8b5518',0x004e947c:'85d2',0x004e9483:'e8c86f2c00',
0x00765fe7:'e891eb1900',0x00904beb:'e8328f0000',0x0090db78:'e87234ffff',0x00901009:'890e',0x0090100e:'894e04'
}
EXPECTED_CALL_TARGETS={
0x00771098:0x0076e560,0x0076e75e:0x0070fe90,0x0076e774:0x0070ab90,
0x007b0c8e:0x0074f560,0x0076d787:0x0070a290,0x0076d7b9:0x00403d00,
0x007b0cf9:0x004e9380,0x0070abf9:0x00633290,0x006332d6:0x00638020,
0x00767cd3:0x0075a8d0,0x007b092a:0x007b0580,0x00633421:0x0064fef0,
0x004e9483:0x007b0450,0x00765fe7:0x00904b7d,0x00904beb:0x0090db22,0x0090db78:0x00900fef,
}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def pe_layout(data:bytes):
 pe=struct.unpack_from('<I',data,0x3c)[0]
 if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0':raise ValueError('invalid PE')
 coff=pe+4;n=struct.unpack_from('<H',data,coff+2)[0];optsz=struct.unpack_from('<H',data,coff+16)[0];opt=coff+20
 base=struct.unpack_from('<I',data,opt+28)[0]; table=opt+optsz; secs=[]
 for i in range(n):
  o=table+i*40;vs,va,rs,rp=struct.unpack_from('<IIII',data,o+8);secs.append((va,max(vs,rs),rp))
 return base,secs

def va_bytes(data:bytes,va:int,size:int)->bytes:
 base,secs=pe_layout(data);rva=va-base
 for sv,span,rp in secs:
  if sv<=rva<sv+span:return data[rp+rva-sv:rp+rva-sv+size]
 raise ValueError(f'unmapped VA {va:#x}')

def verify(exe:Path,frontier:Path)->dict:
 eh=sha256(exe)
 if eh!=RETAIL_SHA256:raise ValueError(f'unexpected retail SHA256 {eh}')
 fr=json.loads(frontier.read_text())
 if fr.get('format')!=FRONTIER_FORMAT:raise ValueError('unexpected frontier format')
 names=[c['function'] for c in fr['candidates']]
 if names!=EXPECTED_CANDIDATES:raise ValueError(f'unexpected candidate set {names!r}')
 data=exe.read_bytes(); wins=[]; calls=[]
 for va,hx in EXPECTED_BYTES.items():
  exp=bytes.fromhex(hx);got=va_bytes(data,va,len(exp))
  if got!=exp:raise ValueError(f'byte mismatch {va:#x}: {got.hex()} != {hx}')
  wins.append({'address':f'0x{va:08x}','bytes':hx})
 for va,target in EXPECTED_CALL_TARGETS.items():
  raw=va_bytes(data,va,5)
  if raw[0] not in (0xe8,0xe9):raise ValueError(f'not rel32 transfer {va:#x}')
  got=va+5+int.from_bytes(raw[1:],'little',signed=True)
  if got!=target:raise ValueError(f'call target mismatch {va:#x}: {got:#x} != {target:#x}')
  calls.append({'site':f'0x{va:08x}','target':f'0x{target:08x}'})
 return {'format':FORMAT,'retail_executable_sha256':eh,'candidate_functions':names,'verified_byte_windows':wins,'verified_rel32_transfers':calls}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('frontier',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
 try:p=verify(a.executable,a.frontier)
 except ValueError as e:ap.error(str(e))
 text=json.dumps(p,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text)
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
