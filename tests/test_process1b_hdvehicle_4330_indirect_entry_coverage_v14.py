import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools'/'ghidra'/'build_p1b_hdvehicle_4330_indirect_entry_coverage_v14.py'
SURFACE=ROOT/'evidence'/'p1b_hdvehicle_4330_base_indexed_direct_cfg_carry.json'
EVIDENCE=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v14.json'
def data(path): return json.loads(path.read_text(encoding='utf-8'))
def module():
 spec=importlib.util.spec_from_file_location('p1b_4330_indirect_v14',BUILDER); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_direct_cfg_surface_is_fixed_point_and_fail_closed():
 d=data(SURFACE); i=d['inventory']; a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedDirectCFGCarry/1'
 assert (i['base_indexed_data_load_count'],i['unique_effective_address_count'])==(63,51)
 assert i['direct_cfg_carried_load_count']==44
 assert i['direct_branch_state_event_count']==207
 assert i['direct_branch_site_count']==199
 assert i['tainted_register_indirect_transfer_count']==0
 assert i['fixed_point_maxout_count']==0
 assert i['direct_call_boundary_count']==56
 assert i['indirect_jump_boundary_count']==11
 assert len(i['indirect_jump_boundaries'])==11
 assert a['base_indexed_direct_cfg_gpr_carry_subset_complete'] is True
 assert a['base_indexed_inter_block_carry_globally_ruled_out'] is False
 assert a['indirect_entry_into_carriers_ruled_out'] is False
def test_indirect_jump_boundaries_do_not_jump_through_live_taint_register():
 for row in data(SURFACE)['inventory']['indirect_jump_boundaries']:
  assert row['jump_register'] not in row['live_taint_registers']
def test_v14_advances_only_one_bounded_class():
 d=data(EVIDENCE); s=d['surface']; a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14'
 assert (s['previous_bounded_coverage_class_count'],s['composed_coverage_class_count'])==(17,18)
 assert s['base_indexed_direct_cfg_carried_load_count']==44
 assert s['base_indexed_direct_cfg_tainted_indirect_transfer_count']==0
 assert s['base_indexed_direct_cfg_direct_call_boundary_count']==56
 assert s['base_indexed_direct_cfg_indirect_jump_boundary_count']==11
 assert s['bounded_exact_carrier_hit_count']==0
 assert a['base_indexed_direct_call_boundaries_remain_open'] is True
 assert a['base_indexed_indirect_jump_successors_remain_open'] is True
 assert a['base_indexed_inter_block_carry_globally_ruled_out'] is False
 assert a['indirect_entry_into_carriers_ruled_out'] is False
 assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
 assert a['last_literal_0x004b86cf_rejected'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7
def test_builder_reproduces_committed_v14(): assert module().build()==data(EVIDENCE)
