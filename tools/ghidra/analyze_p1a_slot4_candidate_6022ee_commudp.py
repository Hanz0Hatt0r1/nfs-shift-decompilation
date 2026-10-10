#!/usr/bin/env python3
"""Resolve the direct/static 0x006022ee slot+4 candidate to the CommUDP table family."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13ASlot4Candidate6022eeCommUdpResolution/1'
UPSTREAM='SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA,TEXT_RAW=0x00401000,0x00000400
RDATA_VA,RDATA_RAW=0x00aa6000,0x006a4a00
ANIMATION_VTABLE=0x00af7544
NETWORK_VTABLE=0x00adccb8
COMMUDP_DTOR=0x00600f60
COMMUDP_SLOT20=0x00601030
SECONDARY=0x006022d0
SECONDARY_RVA=SECONDARY-0x00400000
RANGES={
 'secondary_dispatch':(0x006022d0,0x006022fe,'text','6eb7ca96c6e6201003cf2c6ef463680592c019b19f7dcf74528a1a6a251309a6'),
 'commudp_ctor':(0x00601960,0x00601af4,'text','9cd3ce30ded02921458ba16076a1ba456f7b990d5fa4c0c7c3a95ecf304b08b2'),
 'producer_dual':(0x005bfc86,0x005bfed0,'text','295d75634b413466058a7b4aab9acce1d3c85d30c99a6afee86202665ca28403'),
 'producer_single':(0x005bfed0,0x005bfff5,'text','8ca2875007885bf30573ce475da56dd80ac24ef68f23e11385c4c594855e7f71'),
 'wrapper_state_primary':(0x005c32d0,0x005c3537,'text','5139bb3441b61e93f49b5a60d7f8d7ef34424a5dd43330703784e6dd69338cac'),
 'wrapper_state_secondary':(0x005c3550,0x005c36b5,'text','0d1d8c591a8902b261e13fb986a1a1e23caad89586aa4dfe30c72897ec859353'),
 'link_ctor':(0x006021a0,0x006022ce,'text','1de773036fffeba070b8d9f3c28fcc451aa12947fd7791d26c339660959c06c7'),
 'net_update_slot':(0x005c4a90,0x005c4af5,'text','78cf24afa0d65e5df02962c0a5b565d2940c45b32bdd9a508be4e3a6af3fdd66'),
 'network_ctor_prefix':(0x005bf8f0,0x005bf930,'text','7e04c987bbe540e37412a2cb73535fca2b482fba5a27b27c517357ab7c92b0b2'),
 'network_vtable':(0x00adccb8,0x00adcce4,'rdata','570cf26fa0f0c917d157fb88016f90cce3e531fd83b0c6c690cf70f6fe051034'),
 'wrapper_destructor':(0x005bcc00,0x005bcc70,'text','32624536f9c1e55b9791fb0a5069367beb5f29d1093815b5a57cba48a678ecea'),
 'network_destructor':(0x005c3190,0x005c32d0,'text','0fcb098d51864e30ef6f1f579cc3f8a9ed992520bd9666e43e960c2226f21af5'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')

def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out

def slice_va(blob:bytes,s:int,e:int,sec:str)->bytes:
 va,raw=(TEXT_VA,TEXT_RAW) if sec=='text' else (RDATA_VA,RDATA_RAW)
 off=raw+s-va
 return blob[off:off+e-s]
def dword(blob:bytes,va:int)->int:
 if RDATA_VA<=va<RDATA_VA+0xdabb7:off=RDATA_RAW+va-RDATA_VA
 elif TEXT_VA<=va<TEXT_VA+0x6a4489:off=TEXT_RAW+va-TEXT_VA
 else:raise ValueError(hex(va))
 return struct.unpack_from('<I',blob,off)[0]
def occ(blob:bytes,v:int):
 pat=struct.pack('<I',v);out=[];i=0
 while True:
  i=blob.find(pat,i)
  if i<0:return out
  out.append(i);i+=1
def req(M,a,m,o=''):
 got=M.get(a);exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {got[0]} {got[1]}'.rstrip()
def calls(rows,target:int):
 want=f'0x{target:x}'
 return [a for a,m,o in rows if m=='call' and o==want]

def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 inv=up.get('slot4_abi_inventory',{}).get('near_register_slot4_immediate_cleanup',[])
 cand=next((x for x in inv if x.get('call')=='0x006022ee'),None)
 if not cand or cand.get('slot4_load')!='0x006022ea':raise AssertionError('upstream 0x006022ee candidate drift')
 rows=dis(exe);M={a:(m,o) for a,m,o in rows}
 auth={}
 for n,(s,e,sec,h) in RANGES.items():
  raw=slice_va(blob,s,e,sec);got=hashlib.sha256(raw).hexdigest()
  if len(raw)!=e-s or got!=h:raise AssertionError(('range drift',n,len(raw),got))
  auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':got}
 if dword(blob,NETWORK_VTABLE+0x20)!=0x005c4a90:raise AssertionError('network vtable +0x20 drift')
 ventries=[dword(blob,NETWORK_VTABLE+i) for i in range(0,0x2c,4)]
 surfaces={
  'FUN_00601960':[f'0x{x:08x}' for x in calls(rows,0x00601960)],
  'FUN_006021a0':[f'0x{x:08x}' for x in calls(rows,0x006021a0)],
  'FUN_006022d0':[f'0x{x:08x}' for x in calls(rows,0x006022d0)],
  'FUN_005bcc00':[f'0x{x:08x}' for x in calls(rows,0x005bcc00)],
 }
 expected={
  'FUN_00601960':['0x005b998a','0x005b99b4','0x005bfdad','0x005bfdf2','0x005bff3f'],
  'FUN_006021a0':['0x005c34bd','0x005c367b'],
  'FUN_006022d0':['0x005bcc0d','0x005c319e','0x005c31dd'],
  'FUN_005bcc00':['0x005c4a6a','0x005c4a72'],
 }
 if surfaces!=expected:raise AssertionError(('direct surface drift',surfaces))
 va_occ=occ(blob,SECONDARY);rva_occ=occ(blob,SECONDARY_RVA)
 if va_occ or rva_occ:raise AssertionError(('secondary raw pointer literal drift',va_occ,rva_occ))
 A={
  'network_vptr_store':req(M,0x005bf8fb,'mov','DWORD PTR [esi],0xadccb8'),
  'network_slot20_record_primary':req(M,0x005c4a9a,'lea','edi,[esi+0x1c]'),
  'network_slot20_primary_call':req(M,0x005c4a9e,'call','0x5c32d0'),
  'network_slot20_record_secondary':req(M,0x005c4aaf,'lea','eax,[esi+0x54]'),
  'network_slot20_secondary_call':req(M,0x005c4ab5,'call','0x5c3550'),
  'producer_20_call':req(M,0x005bfdad,'call','0x601960'),
  'producer_20_store':req(M,0x005bfdb5,'mov','DWORD PTR [esi+0x20],eax'),
  'producer_24_call':req(M,0x005bfdf2,'call','0x601960'),
  'producer_24_store':req(M,0x005bfe10,'mov','DWORD PTR [esi+0x24],eax'),
  'producer_58_call':req(M,0x005bff3f,'call','0x601960'),
  'producer_58_store':req(M,0x005bff5d,'mov','DWORD PTR [esi+0x58],eax'),
  'commudp_slot4_store':req(M,0x006019f0,'mov','DWORD PTR [esi+0x4],0x600f60'),
  'commudp_slot20_store':req(M,0x00601a21,'mov','DWORD PTR [esi+0x20],0x601030'),
  'commudp_return':req(M,0x00601aec,'mov','eax,esi'),
  'primary_load_record_4':req(M,0x005c34a4,'mov','edx,DWORD PTR [edi+0x4]'),
  'primary_load_record_8':req(M,0x005c34a7,'mov','ebp,DWORD PTR [edi+0x8]'),
  'primary_link_arg':req(M,0x005c34b6,'push','ebp'),
  'primary_link_call':req(M,0x005c34bd,'call','0x6021a0'),
  'primary_alt_record_8':req(M,0x005c3514,'mov','ecx,DWORD PTR [edi+0x8]'),
  'primary_alt_record_4':req(M,0x005c3517,'mov','ebp,DWORD PTR [edi+0x4]'),
  'secondary_load_record_4':req(M,0x005c366c,'mov','eax,DWORD PTR [edi+0x4]'),
  'secondary_link_arg':req(M,0x005c3673,'push','eax'),
  'secondary_link_call':req(M,0x005c367b,'call','0x6021a0'),
  'link_capture_first_arg':req(M,0x006021f6,'mov','ebp,DWORD PTR [esp+0x28]'),
  'link_store_table_ptr':req(M,0x00602211,'mov','DWORD PTR [esi],ebp'),
  'candidate_load_table_ptr':req(M,0x006022e8,'mov','eax,DWORD PTR [esi]'),
  'candidate_slot4_load':req(M,0x006022ea,'mov','ecx,DWORD PTR [eax+0x4]'),
  'candidate_arg':req(M,0x006022ed,'push','eax'),
  'candidate_call':req(M,0x006022ee,'call','ecx'),
  'candidate_slot20_load':req(M,0x006022da,'mov','eax,DWORD PTR [eax+0x20]'),
  'candidate_slot20_call':req(M,0x006022dd,'call','eax'),
  'wrapper_dtor_candidate_call':req(M,0x005bcc0d,'call','0x6022d0'),
  'network_dtor_primary_load':req(M,0x005c3194,'mov','eax,DWORD PTR [esi+0x1c]'),
  'network_dtor_primary_call':req(M,0x005c319e,'call','0x6022d0'),
  'network_dtor_secondary_load':req(M,0x005c31d5,'mov','eax,DWORD PTR [esi+0x54]'),
  'network_dtor_secondary_call':req(M,0x005c31dd,'call','0x6022d0'),
  'wrapper_dtor_from_secondary_record':req(M,0x005c4a61,'lea','ecx,[esi+0x54]'),
  'wrapper_dtor_secondary_record_call':req(M,0x005c4a6a,'call','0x5bcc00'),
  'wrapper_dtor_from_primary_record':req(M,0x005c4a6f,'lea','ecx,[esi+0x1c]'),
  'wrapper_dtor_primary_record_call':req(M,0x005c4a72,'call','0x5bcc00'),
 }
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,'machine_ranges':auth},
  'upstream_candidate':cand,
  'network_object':{'vtable':'0x00adccb8','slot_0x20':'0x005c4a90','animation_vtable':'0x00af7544',
    'vtable_is_animation_vtable':False,'vtable_entries':[f'0x{x:08x}' for x in ventries]},
  'commudp_table':{'constructor':'FUN_00601960','returned_object_slot_0x4':'0x00600f60','returned_object_slot_0x20':'0x00601030',
    'candidate_0x006022ee_exact_slot4_target_on_bounded_paths':'FUN_00600f60','candidate_0x006022dd_exact_slot20_target_on_bounded_paths':'FUN_00601030'},
  'producer_paths':{
    'network_fields_from_FUN_00601960':['this+0x20','this+0x24','this+0x58'],
    'primary_wrapper_record':'this+0x1c (record+4/+8 map to this+0x20/+0x24)',
    'secondary_wrapper_record':'this+0x54 (record+4 maps to this+0x58)',
    'FUN_006021a0_stores_first_pointer_argument_at_wrapper_0':True,
    'FUN_006022d0_reloads_wrapper_0_before_slot4':True,
  },
  'direct_call_surfaces':surfaces,
  'secondary_static_pointer_literals':{'absolute_va':'0x006022d0','absolute_va_occurrence_count':len(va_occ),
    'rva':'0x002022d0','rva_occurrence_count':len(rva_occ)},
  'machine_anchors':A,
  'adjudication':{
    'p13a_slot4_candidate_006022ee_direct_static_commudp_subset_complete':True,
    'slot4_candidate_006022ee_direct_static_target_resolved':True,
    'slot4_candidate_006022ee_direct_static_targets_fun0067b660':False,
    'slot4_candidate_006022ee_direct_static_exact_target_fun00600f60':True,
    'slot20_candidate_006022dd_direct_static_exact_target_fun00601030':True,
    'exact_static_fun006022d0_absolute_pointer_found':False,
    'exact_static_fun006022d0_rva_pointer_found':False,
    'fun0067b660_callback_argument_provenance_complete':False,
    'callbacks_and_indirect_entry_ruled_out':False,
    'encoded_or_reconstructed_callback_entry_ruled_out':False,
    'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
    'stored_or_escaped_aliases_ruled_out':False,
    'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
    'This resolves the 0x006022ee candidate only for the complete direct/static entry surface proven here: three direct FUN_006022d0 calls, two direct wrapper-destructor calls, two direct FUN_006021a0 constructors, and no exact raw FUN_006022d0 VA/RVA pointer literal.',
    'The bounded wrapper producers source their table pointers from FUN_00601960 returns stored in network fields +0x20/+0x24/+0x58; FUN_00601960 fixes table slot +0x4 to FUN_00600f60 and +0x20 to FUN_00601030.',
    'Reconstructed/encoded/runtime-generated entry to FUN_006022d0 remains an independent open class; therefore global callback/incoming-indirect closure is not promoted.',
    'The separate 0x006145c4 registry candidate remains open for dynamic initializer registrations after the two static initializer result types were rejected.'
  ],
  'next_step':'Continue the remaining 0x006145c4 dynamic registry candidate and reconstructed/indirect entry classes; do not reopen 0x006022ee direct/static CommUDP provenance.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s,encoding='utf-8')
 else:print(s,end='')
if __name__=='__main__':main()
