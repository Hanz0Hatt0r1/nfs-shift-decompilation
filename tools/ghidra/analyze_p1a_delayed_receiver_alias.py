#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13ADelayedReceiverAliasClosure/1'
RETAIL_SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SINGLETON_GETTER=0x00886980
WRAPPER=0x005f4f50
TAIL_WRAPPER_CALLER=0x005f8950
NVAPI_SLOT=0x00bbbd34
NVAPI_ID_SLOT=0x00bbbd38
NVAPI_ENUM_PHYSICAL_GPUS_ID=0xe5ac921f
DATA_VA=0x00b81000
DATA_RAW=0x0077f600
MAX_LOCAL_INSTRUCTIONS=24
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
DIRECT_RE=re.compile(r'^0x([0-9a-fA-F]+)$')
REG32={'eax','ebx','ecx','edx','esi','edi'}
SUB_TO_32={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi'}
WRITE_MNEMONICS={'mov','lea','xor','add','sub','and','or','shl','shr','sar','sal','movzx','movsx','pop','inc','dec','imul'}

def norm_ops(s:str)->str:
    return re.sub(r'\s+',' ',s.strip()).replace(' ,',',').replace(', ', ',')

def disassemble(exe:Path):
    p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
    rows=[]
    for line in p.stdout.splitlines():
        m=INST_RE.match(line)
        if m: rows.append((int(m.group(1),16),m.group(2).lower(),norm_ops(m.group(3)),line.strip()))
    return rows

def written_base_reg(mn:str,ops:str):
    if mn not in WRITE_MNEMONICS:return None
    first=ops.split(',',1)[0].strip()
    if first in REG32:return first
    return SUB_TO_32.get(first)

def local_events(rows):
    getter_sites=[]; events=[]
    for i,(a,mn,ops,_) in enumerate(rows):
        dm=DIRECT_RE.match(ops) if mn=='call' else None
        if not(dm and int(dm.group(1),16)==SINGLETON_GETTER):continue
        getter_sites.append(a)
        aliases={'eax'}; pending_push_alias=False
        for j in range(i+1,min(i+1+MAX_LOCAL_INSTRUCTIONS,len(rows))):
            aa,mm,oo,_=rows[j]
            if mm=='ret':
                if 'eax' in aliases: events.append({'getter_call':a,'site':aa,'kind':'raw_return','detail':'eax'})
                break
            if mm=='call':
                if pending_push_alias: events.append({'getter_call':a,'site':aa,'kind':'call_argument_escape','detail':'pushed exact receiver alias'})
                break
            if mm=='push':
                if oo.strip() in aliases: pending_push_alias=True
                continue
            if mm=='pop': pending_push_alias=False
            if mm=='mov' and ',' in oo:
                dst,src=[x.strip() for x in oo.split(',',1)]
                if dst in REG32:
                    if src in aliases: aliases.add(dst)
                    else: aliases.discard(dst)
                    continue
                if src in aliases and dst.startswith('DWORD PTR ['):
                    kind='stack_spill' if ('[ebp' in dst or '[esp' in dst) else 'non_stack_store'
                    events.append({'getter_call':a,'site':aa,'kind':kind,'detail':dst})
                    continue
            wr=written_base_reg(mm,oo)
            if wr: aliases.discard(wr)
            if mm=='jmp': break
    return getter_sites,events

def direct_transfers(rows,target):
    out=[]
    for a,mn,ops,_ in rows:
        if mn not in ('call','jmp'):continue
        dm=DIRECT_RE.match(ops)
        if dm and int(dm.group(1),16)==target:
            out.append({'site':f'0x{a:08x}','kind':mn,'target':f'0x{target:08x}'})
    return out

def instruction_map(rows): return {a:(mn,ops) for a,mn,ops,_ in rows}

def require(imap,addr,mn,ops=None):
    got=imap.get(addr)
    if not got: raise AssertionError(f'missing instruction 0x{addr:08x}')
    if got[0]!=mn: raise AssertionError((hex(addr),got,(mn,ops)))
    if ops is not None and got[1]!=norm_ops(ops): raise AssertionError((hex(addr),got,(mn,norm_ops(ops))))
    return f'0x{addr:08x} {got[0]} {got[1]}'.strip()

def dword_at_va(blob:bytes,va:int)->int:
    off=DATA_RAW+(va-DATA_VA)
    if off<0 or off+4>len(blob): raise ValueError(hex(va))
    return struct.unpack_from('<I',blob,off)[0]

def analyze(exe:Path):
    blob=exe.read_bytes(); sha=hashlib.sha256(blob).hexdigest()
    if sha!=RETAIL_SHA256: raise ValueError(f'unexpected retail SHA256: {sha}')
    rows=disassemble(exe); imap=instruction_map(rows)
    getter_sites,events=local_events(rows)
    by_kind={k:[] for k in ['stack_spill','raw_return','non_stack_store','call_argument_escape']}
    for e in events: by_kind[e['kind']].append(e)
    wrapper_transfers=direct_transfers(rows,WRAPPER)
    tail_calls=direct_transfers(rows,TAIL_WRAPPER_CALLER)
    initial_slot=dword_at_va(blob,NVAPI_SLOT); interface_id=dword_at_va(blob,NVAPI_ID_SLOT)
    anchors={
      'spill_origin':require(imap,0x00832a96,'call','0x886980'),
      'spill_store':require(imap,0x00832aa2,'mov','DWORD PTR [ebp-0x10],eax'),
      'spill_reload':require(imap,0x00832fbc,'mov','edi,DWORD PTR [ebp-0x10]'),
      'dispatch_slot_0x50_load':require(imap,0x00832fc4,'mov','eax,DWORD PTR [eax+0x50]'),
      'dispatch_slot_0x50_call':require(imap,0x00832fce,'call','eax'),
      'dispatch_slot_0x58_load':require(imap,0x00832fd2,'mov','eax,DWORD PTR [edx+0x58]'),
      'dispatch_slot_0x58_call':require(imap,0x00832fd7,'call','eax'),
      'count_address':require(imap,0x00833139,'lea','edx,[ebp-0x10]'),
      'push_count_address':require(imap,0x0083313c,'push','edx'),
      'gpu_array_address':require(imap,0x0083313d,'lea','eax,[ebp-0x224]'),
      'push_gpu_array_address':require(imap,0x00833143,'push','eax'),
      'nvapi_enum_call':require(imap,0x00833144,'call','0xa61b06'),
      'nvapi_status_test':require(imap,0x0083314c,'test','eax,eax'),
      'failure_branch':require(imap,0x0083314e,'jne','0x833167'),
      'success_count_reload':require(imap,0x00833150,'mov','eax,DWORD PTR [ebp-0x10]'),
      'success_count_store':require(imap,0x00833156,'mov','DWORD PTR [esi+0x1f48],eax'),
      'dynamic_resolver_table_base':require(imap,0x00a61aae,'mov','esi,0xbbbd0c'),
      'dynamic_resolver_id_load':require(imap,0x00a61ab3,'mov','eax,DWORD PTR [esi+0x4]'),
      'dynamic_resolver_query_call':require(imap,0x00a61abb,'call','ebp'),
      'dynamic_resolver_slot_store':require(imap,0x00a61ac2,'mov','DWORD PTR [esi],eax'),
      'dynamic_resolver_stride':require(imap,0x00a61ac4,'add','esi,0x8'),
      'raw_return_origin':require(imap,0x005f5182,'call','0x886980'),
      'raw_return_site':require(imap,0x005f51a1,'ret'),
      'caller_5f79d7':require(imap,0x005f79d7,'call','0x5f4f50'),
      'caller_5f79d7_next':require(imap,0x005f79dc,'lea','edi,[esi+0x1fa4]'),
      'caller_5f7b85':require(imap,0x005f7b85,'call','0x5f4f50'),
      'caller_5f7b85_overwrite':require(imap,0x005f7b8c,'mov','eax,DWORD PTR [edx+0x2c]'),
      'tail_to_wrapper':require(imap,0x005f8aff,'jmp','0x5f4f50'),
      'tail_wrapper_caller':require(imap,0x005a89e4,'call','0x5f8950'),
      'tail_wrapper_caller_overwrite':require(imap,0x005a89e9,'call','0x586dd0'),
    }
    if len(getter_sites)!=203: raise AssertionError(len(getter_sites))
    if [(e['getter_call'],e['site']) for e in by_kind['stack_spill']] != [(0x00832a96,0x00832aa2)]: raise AssertionError(by_kind['stack_spill'])
    if [(e['getter_call'],e['site']) for e in by_kind['raw_return']] != [(0x005f5182,0x005f51a1)]: raise AssertionError(by_kind['raw_return'])
    if by_kind['non_stack_store'] or by_kind['call_argument_escape']: raise AssertionError(events)
    if wrapper_transfers != [
        {'site':'0x005f79d7','kind':'call','target':'0x005f4f50'},
        {'site':'0x005f7b85','kind':'call','target':'0x005f4f50'},
        {'site':'0x005f8aff','kind':'jmp','target':'0x005f4f50'}]: raise AssertionError(wrapper_transfers)
    if tail_calls != [{'site':'0x005a89e4','kind':'call','target':'0x005f8950'}]: raise AssertionError(tail_calls)
    if initial_slot != 0x00a61a48 or interface_id != NVAPI_ENUM_PHYSICAL_GPUS_ID: raise AssertionError((hex(initial_slot),hex(interface_id)))
    return {
      'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
      'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_disassembly_adjudicates':True,
        'external_abi_reference':{'provider':'NVIDIA NVAPI','interface_id':'0xe5ac921f','symbol':'NvAPI_EnumPhysicalGPUs','success_status':'NVAPI_OK == 0','second_parameter':'NvU32 *pGpuCount (output)'}},
      'scope':{'singleton_getter':'FUN_00886980','singleton_getter_address':'0x00886980','direct_singleton_getter_call_count':len(getter_sites),
        'local_event_window_max_instructions':MAX_LOCAL_INSTRUCTIONS,'local_event_window_stops_at_first_intervening_call_or_unconditional_jump':True,
        'upstream_entry_surface_contract':'SHIFT.HDVehicle64e8Manager374P13A005f4ffaReceiverRejection/1'},
      'local_exact_receiver_events':{
        'stack_spill_count':len(by_kind['stack_spill']),'raw_return_count':len(by_kind['raw_return']),
        'non_stack_store_count':len(by_kind['non_stack_store']),'call_argument_escape_count':len(by_kind['call_argument_escape']),
        'stack_spills':[{**e,'getter_call':f"0x{e['getter_call']:08x}",'site':f"0x{e['site']:08x}"} for e in by_kind['stack_spill']],
        'raw_returns':[{**e,'getter_call':f"0x{e['getter_call']:08x}",'site':f"0x{e['site']:08x}"} for e in by_kind['raw_return']]
      },
      'stack_spill_closure':{
        'spill':'0x00832aa2 [ebp-0x10] = exact FUN_00886980 receiver',
        'pre_overwrite_receiver_dispatch_slots':['+0x50','+0x58'],
        'module_base_getter_slots_seen_before_overwrite':[],
        'dynamic_nvapi_slot':'0x00bbbd34','dynamic_nvapi_slot_initial_value':f'0x{initial_slot:08x}',
        'dynamic_nvapi_interface_id':f'0x{interface_id:08x}','dynamic_nvapi_symbol':'NvAPI_EnumPhysicalGPUs',
        'call_arguments':{'arg1':'&[ebp-0x224] physical-GPU handle array','arg2':'&[ebp-0x10] output GPU count'},
        'success_path':'0x0083314c test eax,eax; 0x0083314e jne failure; fallthrough is NVAPI_OK (0)',
        'post_call_adjudication':'On the only path that reaches 0x00833150/0x00833156, [ebp-0x10] is the NvAPI_EnumPhysicalGPUs output GPU count, not the prior singleton receiver.',
        'post_call_store_is_receiver_escape':False,
      },
      'raw_return_closure':{
        'origin':'0x005f5182 call FUN_00886980','return':'0x005f51a1 ret with exact receiver still in EAX',
        'wrapper_direct_transfer_surface':wrapper_transfers,'tail_wrapper_direct_call_surface':tail_calls,
        'caller_consumption':[
          {'site':'0x005f79d7','result':'ignored','proof':'next instruction is LEA to EDI; following call overwrites caller-saved EAX before use'},
          {'site':'0x005f7b85','result':'ignored','proof':'EAX overwritten at 0x005f7b8c before any use'},
          {'site':'0x005a89e4 via 0x005f8950 -> 0x005f4f50 tail','result':'ignored','proof':'immediate 0x005a89e9 call 0x00586dd0 overwrites caller-saved EAX before use'},
        ],
        'escaped_receiver_return_consumed':False,
      },
      'machine_anchors':anchors,
      'adjudication':{
        'p13a_direct_getter_delayed_spill_return_subset_complete':True,
        'direct_getter_delayed_stack_spill_reaches_module_base_getter_slot':False,
        'direct_getter_raw_receiver_return_consumed':False,
        'direct_getter_local_non_stack_store_found':False,
        'direct_getter_local_call_argument_escape_found':False,
        'direct_singleton_getter_delayed_or_stored_alias_dispatch_ruled_out':True,
        'delayed_or_stored_receiver_alias_dispatch_ruled_out':False,
        'module_base_getter_consumer_paths_complete':False,
        'runtime_callback_registration_ruled_out':False,'incoming_indirect_entry_ruled_out':False,
        'encoded_or_reconstructed_carrier_pointers_ruled_out':False,'runtime_generated_or_copied_carrier_pointers_ruled_out':False,
        'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
        'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
      },
      'limits':[
        'The local event inventory starts only from the 203 direct FUN_00886980 calls and records exact receiver stores/returns before the first intervening call or unconditional jump; it is not a generic whole-program points-to proof.',
        'The sole stack spill is then followed explicitly through its delayed reload, virtual dispatches and NVAPI overwrite. The sole raw return is closed using the already-bounded FUN_005f4f50 static entry surface from the upstream receiver-rejection contract plus the one direct FUN_005f8950 caller.',
        'NVAPI symbol identity and output-parameter semantics are ABI facts keyed by interface ID 0xe5ac921f; tests do not require network access.',
        'This promotes only the direct singleton-getter delayed/stored receiver consumer frontier. Callback registration, incoming indirect entry, encoded/reconstructed pointers and selected-wheel pointer persistence remain fail-closed.',
      ],
      'next_step':'Move P1.3A to runtime callback/incoming-indirect and selected-wheel pointer-persistence frontiers; keep slot0, slot1 and aggregate P1.3 gates false until those independent blockers close.'
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(s,encoding='utf-8')
    else:print(s,end='')
if __name__=='__main__':main()
