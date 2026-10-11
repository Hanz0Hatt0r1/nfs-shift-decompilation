import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_remaining_allocation_provenance.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_remaining_allocation_provenance.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_allocprov',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_counts():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['classified_site_count']==4;assert r['allocation_provenance_group_count']==3
def test_sites_exact():assert data()['inventory']['classified_sites']==['0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
def test_allocator_8868d0_groups():
 g=data()['inventory']['allocation_provenance_groups'];assert g[0]['base_register']=='esi';assert '0x008868d0' in g[0]['base_provenance'];assert g[1]['base_register']=='ebx';assert '0x008868d0' in g[1]['base_provenance']
def test_allocator_8868c0_payload_group():
 g=data()['inventory']['allocation_provenance_groups'][2];assert g['sites']==['0x0080b696'];assert g['base_register']=='edx';assert 'alloc_return+4' in g['base_provenance'];assert '0x008868c0' in g['base_provenance']
def test_mod1_frontier_preserved():assert data()['inventory']['remaining_modulus1_sites']==['0x00503328','0x0050334b']
def test_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_remaining_allocation_provenance_subset_complete'] is True;assert a['writable_callback_pair_remaining_mod4_mod8_sites_all_allocation_backed'] is True;assert a['writable_callback_pair_allocator_range_disjoint_from_image_proven'] is False;assert a['writable_callback_pair_target_compatible_frontier_empty'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
