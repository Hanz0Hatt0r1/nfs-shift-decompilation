from bmw_vertex_input_parity import validate_bmw_vertex_input_parity


def _material(property_id='200', usage='POSITION', usage_index=0, location=0):
    return {
        'format':'SHIFT.BMWMaterialSlice/1',
        'ready':True,
        'golden_identity':{'resource':'vehicles/bmw/body.meb','resource_sha256':'sha'},
        'material':{'permutation_identity':{'identity_sha256':'shader-id'}},
        'mesh':{
            'vertex_layout':{'attributes':[{'property_id':property_id,'usage':usage,'usage_index':usage_index,'location':location}]},
            'property_descriptors':[{'id':property_id,'words':[2 if property_id=='200' else 4,0 if property_id=='200' else 6,usage_index],'raw_hex':'020000000000000000000000' if property_id=='200' else '040000000600000000000000'}],
        },
    }


def _runtime(usage=0, type_code=1, shader_inputs=None):
    return {
        'format':'SHIFT.D3D9RuntimeBindingEvidence/1',
        'frames':[{'frame':1,
            'vertex_declaration':{'declaration_ptr':'0x1','resource_sha256':'sha'},
            'shader_permutation_identity':{'identity_sha256':'shader-id','payload':{'vertex':{'inputs':shader_inputs or [{'register':'v0','usage':'POSITION','index':0}]},'pixel':{}}},
        }],
        'declarations':[{'pointer':'0x1','decoded':{'records':[{'stream':0,'offset':0,'type':type_code,'usage':usage,'usage_index':0}]}}],
    }


def test_vertex_input_parity_accepts_position_when_usage_map_is_explicit():
    report=validate_bmw_vertex_input_parity(_material(),_runtime(),usage_map={0:0})
    assert report['ready'] is True
    assert report['checks'][0]['declaration_status']=='match'


def test_vertex_input_parity_blocks_wrong_type():
    report=validate_bmw_vertex_input_parity(_material(),_runtime(type_code=4),usage_map={0:0})
    assert report['ready'] is False
    assert 'vertex-input:declaration-mismatch:200' in report['blocking_reasons']


def test_vertex_input_parity_blocks_missing_shader_semantic():
    report=validate_bmw_vertex_input_parity(_material(),_runtime(shader_inputs=[{'register':'v0','usage':'NORMAL','index':0}]),usage_map={0:0})
    assert report['ready'] is False
    assert 'vertex-input:layout-semantic-missing:NORMAL0' in report['blocking_reasons']


def test_vertex_input_parity_keeps_physical_repack_explicit():
    report=validate_bmw_vertex_input_parity(_material(),_runtime(),usage_map={0:0})
    assert report['physical_layout']['status']=='not-comparable-by-design'

def test_vertex_input_parity_blocks_semantic_collision():
    material = _material()
    material['mesh']['vertex_layout']['attributes'] = [
        {'property_id':'130','usage':'TEXCOORD','usage_index':0,'location':0},
        {'property_id':'230','usage':'TEXCOORD','usage_index':0,'location':1},
    ]
    material['mesh']['property_descriptors'] = [
        {'id':'130','words':[1,3,0],'raw_hex':'010000000300000000000000'},
        {'id':'230','words':[2,3,0],'raw_hex':'020000000300000000000000'},
    ]
    runtime = _runtime(usage=5, type_code=1, shader_inputs=[{'register':'v0','usage':'TEXCOORD','index':0}])
    report = validate_bmw_vertex_input_parity(material, runtime, usage_map={3:5})
    assert report['ready'] is False
    assert 'vertex-input:layout-semantic-collision:TEXCOORD0' in report['blocking_reasons']
    assert report['checks'][0]['status'] == 'ambiguous'
