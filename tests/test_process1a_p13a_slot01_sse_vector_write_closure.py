import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'ghidra' / 'analyze_p1a_slot01_sse_vector_write_surface.py'
EVIDENCE = ROOT / 'evidence' / 'p1a_p13a_slot01_sse_vector_write_closure.json'
EXPECTED_SITES = [
    '0x00901268','0x009012cf','0x009012f6','0x00909f59','0x00909f86',
    '0x0090a4c9','0x0090a4ee','0x0090a514','0x00912159','0x00912605',
    '0x00912623','0x00912821','0x0091286b','0x00912912',
]

def load_tool():
    spec=importlib.util.spec_from_file_location('p1a_sse',TOOL); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def load_evidence(): return json.loads(EVIDENCE.read_text(encoding='utf-8'))

def test_direct_vector_store_classification():
    m=load_tool()
    assert m.direct_vector_store('movlpd','QWORD PTR [esp+0x4],xmm0') == (True, True)
    assert m.direct_vector_store('movups','XMMWORD PTR [edi+0x20],xmm3') == (True, False)
    assert m.direct_vector_store('movsd','xmm0,QWORD PTR [esi]') == (False, False)

def test_vector_to_gpr_escape_tracking_is_clobber_aware():
    m=load_tool()
    good=[(0x1000,'movd','eax,xmm0'),(0x1004,'mov','DWORD PTR [edi+0x8],eax')]
    assert len(m.escaped_vector_gpr_stores(good)) == 1
    clobbered=[(0x2000,'movd','eax,xmm0'),(0x2004,'xor','eax,eax'),(0x2006,'mov','DWORD PTR [edi],eax')]
    assert m.escaped_vector_gpr_stores(clobbered) == []
    stack=[(0x3000,'movd','eax,xmm0'),(0x3004,'mov','DWORD PTR [esp+0x4],eax')]
    assert m.escaped_vector_gpr_stores(stack) == []

def test_retail_surface_is_exact_and_stack_only():
    d=load_evidence(); s=d['scan']
    assert d['format']=='SHIFT.P1A.P13ASlot01SSEVectorWriteClosure/1'
    assert s['reachable_unique_node_count']==377
    assert s['reachable_sized_function_count']==371
    assert s['direct_vector_memory_store_count']==14
    assert s['direct_stack_vector_memory_store_count']==14
    assert s['direct_nonstack_vector_memory_store_count']==0
    assert s['direct_vector_store_function_count']==4
    assert s['implicit_mask_vector_store_count']==0
    assert s['vector_to_gpr_nonstack_escape_count']==0
    assert [r['site'] for r in d['direct_vector_stores']]==EXPECTED_SITES
    assert all(r['destination_class']=='stack' for r in d['direct_vector_stores'])
    assert d['implicit_mask_vector_stores']==[]
    assert d['vector_to_gpr_nonstack_escapes']==[]

def test_sse_closes_but_deeper_and_indirect_gates_stay_closed():
    a=load_evidence()['adjudication']
    assert a['shallow_sse_vector_write_depth4_surface_complete'] is True
    assert a['shallow_sse_vector_selected_hdvehicle_writer_found'] is False
    assert a['sse_vector_copy_init_complete'] is True
    assert a['deeper_direct_aliases_ruled_out'] is False
    assert a['indirect_callback_aliases_ruled_out'] is False
    assert a['p13a_slot0_complete'] is False and a['p13a_slot1_complete'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
