import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools/ghidra/analyze_p1b_hdvehicle_4330_getprocaddress_static_resolution_v2.py'
EV=ROOT/'evidence/p1b_hdvehicle_4330_getprocaddress_static_resolution_v2.json'

def load():
    spec=importlib.util.spec_from_file_location('gpa2',AN); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m

def test_corrected_counts_and_families():
    d=json.loads(EV.read_text()); s=d['getprocaddress_surface']
    assert d['format']=='SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2'
    assert s['register_loaded_callsite_count']==89
    assert s['physical_getprocaddress_callsite_count']==101
    assert s['known_name_instance_count']==112
    assert s['known_unique_name_count']==108
    assert [x['callsite_count'] for x in s['register_loaded_families']]==[2,4,5,2,6,67,3]
    assert s['v2_newly_recovered_callsites']==['0x0099a116','0x00a623b8','0x00a623c2']
    assert s['known_patch_api_name_hits']==[]

def test_cfg_scan_follows_success_branch_past_error_pop():
    m=load()
    rows=[
      {'address':0x1000,'mnemonic':'mov','operands':'ebx,dword ptr ds:0x2000'},
      {'address':0x1006,'mnemonic':'cmp','operands':'eax,0x0'},
      {'address':0x1009,'mnemonic':'jne','operands':'0x1012'},
      {'address':0x100b,'mnemonic':'pop','operands':'ebx'},
      {'address':0x100c,'mnemonic':'ret','operands':''},
      {'address':0x1012,'mnemonic':'call','operands':'ebx'},
      {'address':0x1014,'mnemonic':'mov','operands':'ebx,eax'},
    ]
    idx,unresolved=m.scan_register_lifetime(rows,0,'ebx',lambda r: r['operands'].split(',',1)[0] if r['mnemonic'] in {'mov','pop'} else None)
    assert idx==[5]
    assert unresolved==[]

def test_global_gates_remain_closed():
    a=json.loads(EV.read_text())['adjudication']
    assert a['cfg_aware_register_loaded_getprocaddress_surface_complete'] is True
    assert a['v1_linear_scan_count_superseded'] is True
    assert a['runtime_generated_or_copied_function_pointers_ruled_out'] is False
    assert a['runtime_patching_or_generated_code_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
