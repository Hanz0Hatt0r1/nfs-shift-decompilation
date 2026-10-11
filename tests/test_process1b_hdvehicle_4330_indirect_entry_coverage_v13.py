import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools'/'ghidra'/'build_p1b_hdvehicle_4330_indirect_entry_coverage_v13.py'
CALLEE=ROOT/'evidence'/'p1b_hdvehicle_4330_base_indexed_direct_callee_provenance.json'
EVIDENCE=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v13.json'
def data(path): return json.loads(path.read_text(encoding='utf-8'))
def module():
 spec=importlib.util.spec_from_file_location('p1b_4330_indirect_v13',BUILDER); assert spec and spec.loader
 mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def test_all_five_direct_call_escapes_are_classified_as_data():
 d=data(CALLEE); s=d['surface']
 assert d['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedDirectCalleeProvenance/1'
 assert (s['escape_count'],s['classified_escape_count'],s['unclassified_escape_count'])==(5,5,0)
 assert s['nul_terminated_string_escape_count']==5
 assert s['indirect_call_or_jump_through_escape_value_count']==0
 assert s['format_string_literal_address']=='0x00ac03c4' and s['format_string_literal_ascii']=='%s='
def test_exact_first_hop_callees_are_stable():
 got=[(x['call_site'],x['callee'],x['classification']) for x in data(CALLEE)['escapes']]
 assert got==[
  ('0x004b1c1b','0x006329e0','nul_terminated_byte_string'),
  ('0x00d74308','0x006329e0','nul_terminated_byte_string'),
  ('0x004cd46b','0x00632c70','nul_terminated_byte_string'),
  ('0x005f51ed','0x00403c90','printf_percent_s_string_argument'),
  ('0x008d1960','0x008b4c70','nul_terminated_byte_string_to_refcounted_string')]
def test_v13_advances_only_bounded_coverage():
 d=data(EVIDENCE); s=d['surface']; a=d['adjudication']
 assert d['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/13'
 assert (s['previous_bounded_coverage_class_count'],s['composed_coverage_class_count'])==(16,17)
 assert s['base_indexed_direct_call_argument_escape_classified_count']==5
 assert s['base_indexed_direct_callee_indirect_transfer_count']==0 and s['bounded_exact_carrier_hit_count']==0
 assert a['base_indexed_direct_call_escape_data_provenance_complete'] is True
 assert a['base_indexed_inter_block_carry_remains_open'] is True
 assert a['base_indexed_runtime_or_alias_provenance_remains_open'] is True
 assert a['indirect_entry_into_carriers_ruled_out'] is False
 assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
 assert a['last_literal_0x004b86cf_rejected'] is False
 assert a['p1_3_control_producer_complete'] is False and a['external_provider_count']==7
def test_builder_reproduces_committed_v13(): assert module().build()==data(EVIDENCE)
