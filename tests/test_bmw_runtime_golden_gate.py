import json

from bmw_runtime_golden_gate import validate_runtime_golden_gate


def _material(ready_command=True):
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'ready': True,
        'primitive_index': 1,
        'golden_identity': {'resource': 'vehicles/bmw/body.meb', 'resource_sha256': 'sha'},
        'material': {'permutation_identity': {'identity_sha256': 'shader-id'}},
        'uniform_binding': {'bindings': [{'name': 'primerBasis', 'register_set': 2, 'register_index': 5, 'register_count': 1, 'stage': 'pixel', 'value': [1.0,2.0,3.0,4.0]}]},
        'mesh': {
            'vertex_layout': {'attributes': [{'property_id': '460', 'usage': 'COLOR', 'usage_index': 0}]},
            'property_descriptors': [{'id': '460', 'offset': 0, 'words': [4, 6, 0], 'raw_hex': '040000000600000000000000'}],
        },
        'textures': [],
        'render_command': {
            'format': 'SHIFT.RenderCommand/1',
            'ready': ready_command,
            'blocking_reasons': [] if ready_command else ['render-command:not-ready'],
            'mesh': {'vertex_layout': {'format': 'SHIFT.VertexLayout/1'}, 'vertex_count': 3550, 'attributes': []},
            'submeshes': [{
                'index': 1,
                'first_index': 150,
                'index_count': 6294,
                'uniforms': {'bindings': [{'name': 'primerBasis', 'stage': 'pixel', 'register_index': 5, 'register_count': 1, 'ctab_type': 'float4'}]},
                'constant_payload': {'format': 'SHIFT.MaterialConstantPayload/1', 'ready': True, 'registers': [{'register_index': 5, 'values': [1.0,2.0,3.0,4.0], 'byte_offset': 80, 'byte_size': 16}]},
                'constant_commands': [{'name': 'primerBasis', 'stage': 'pixel', 'register_index': 5, 'register_count': 1, 'ctab_type': 'float4', 'byte_offset': 80}],
            }],
            'resource_plan': {'format': 'SHIFT.RenderResources/1', 'texture_count': 0, 'sampler_count': 0, 'external_sampler_count': 0},
        },
    }


def _runtime(constant_values=True):
    return {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'declarations': [{'pointer': '0x1', 'decoded': {'records': [{'type':4,'usage':10,'usage_index':0}]}}],
        'integrity': {'format':'SHIFT.D3D9RuntimeTraceIntegrity/1','status':'observed','blocking_reasons':[]},
        'frames': [{
            'frame': 1,
            'vertex_declaration': {'declaration_ptr':'0x1','resource_sha256':'sha','create_known':True},
            'vertex_shader': {'shader_ptr':'0x2','create_known':True},
            'pixel_shader': {'shader_ptr':'0x3','create_known':True},
            'stream_sources': [{'stream':0}],
            'index_binding': {'index_buffer_ptr':'0x4'},
            'draws': [{'start_index':150, 'primitive_count':2098, 'base_vertex_index':0}],
            'constant_writes': [{'stage':'pixel','start_register':5,'vector4f_count':1,'values':[1.0,2.0,3.0,4.0]}] if constant_values else [],
            'shader_permutation_identity': {'identity_sha256':'shader-id','payload':{'vertex':{'inputs':[{'register':'v0','usage':'COLOR','index':0}], 'constants':[]},'pixel':{'constants':[5],'sampler_types':{}}}},
        }],
        'same_instance_gate': {
            'status': 'proven',
            'ready': True,
            'candidate_frames': [{
                'frame': 1,
                'declaration_ptr': '0x1',
                'same_meb_resource': True,
                'declaration_create_known': True,
                'declaration_decode_status': 'match',
                'bound_declaration_valid': True,
                'descriptor_matches': [{
                    'property_id': '460',
                    'type_ordinal': 4,
                    'usage_ordinal': 6,
                    'runtime_usage': 10,
                    'channel': 0,
                    'record_indices': [0],
                }],
            }],
            'blocking_reasons': [],
        },
    }


def test_runtime_golden_gate_ready_on_full_parity(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; m.write_text(json.dumps(_material())); r.write_text(json.dumps(_runtime()))
    report=validate_runtime_golden_gate(m,r,usage_map_path=None)
    # declaration Usage mapping is mandatory, so gate should remain blocked
    assert report['ready'] is False
    assert 'declaration:usage-map-missing' in report['blocking_reasons']


def test_runtime_golden_gate_ready_with_usage_map_and_command(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(_material())); r.write_text(json.dumps(_runtime())); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is True, report
    assert report['status'] == 'ready'


def test_runtime_golden_gate_blocks_render_command(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(_material(False))); r.write_text(json.dumps(_runtime())); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is False
    assert 'render-command:not-ready' in report['blocking_reasons']

def test_runtime_golden_gate_propagates_vertex_input_mismatch(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    material=_material()
    runtime=_runtime()
    runtime['frames'][0]['shader_permutation_identity']['payload']['vertex']['inputs']=[{'register':'v0','usage':'NORMAL','index':0}]
    m.write_text(json.dumps(material)); r.write_text(json.dumps(runtime)); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is False
    assert 'vertex-input:layout-semantic-missing:NORMAL0' in report['blocking_reasons']
    assert report['vertex_input_parity']['status'] == 'partial'


def test_runtime_golden_gate_blocks_render_command_constant_parity(tmp_path):
    material=_material()
    material['render_command']['submeshes'][0] = {
        'first_index':150,
        'index_count':6294,
        'uniforms':{'bindings':[{'name':'Tint','stage':'pixel','register_index':5,'register_count':1,'ctab_type':'float4'}]},
        'constant_payload':{'ready':True,'registers':[{'register_index':5,'values':[1.0,2.0,3.0,4.0],'byte_offset':80,'byte_size':16}]},
        'constant_commands':[{'name':'Tint','stage':'pixel','register_index':5,'register_count':1,'ctab_type':'float4','byte_offset':96}],
    }
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(material)); r.write_text(json.dumps(_runtime())); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is False
    assert 'render-command:constant-parity-not-ready' in report['blocking_reasons']



def test_runtime_golden_gate_requires_same_instance_gate(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(_material())); runtime=_runtime(); runtime.pop('same_instance_gate')
    r.write_text(json.dumps(runtime)); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is False
    assert 'runtime-same-instance:not-proven' in report['blocking_reasons']
