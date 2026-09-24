import json

from bmw_runtime_golden_gate import validate_runtime_golden_gate


def _material(ready_command=True):
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'ready': True,
        'golden_identity': {'resource': 'vehicles/bmw/body.meb', 'resource_sha256': 'sha'},
        'material': {'permutation_identity': {'identity_sha256': 'shader-id'}},
        'uniform_binding': {'bindings': [{'name': 'primerBasis', 'register_set': 2, 'register_index': 5, 'register_count': 1, 'stage': 'pixel', 'value': [1.0,2.0,3.0,4.0]}]},
        'mesh': {'vertex_layout': {'attributes': [{'property_id': '460', 'usage': 'COLOR', 'usage_index': 0}]}},
        'textures': [],
        'render_command': {'ready': ready_command, 'blocking_reasons': [] if ready_command else ['render-command:not-ready']},
    }


def _runtime(constant_values=True):
    return {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'declarations': [{'pointer': '0x1', 'decoded': {'records': [{'type':4,'usage':10,'usage_index':0}]}}],
        'frames': [{
            'frame': 1,
            'vertex_declaration': {'declaration_ptr':'0x1','resource_sha256':'sha'},
            'constant_writes': [{'stage':'pixel','start_register':5,'vector4f_count':1,'values':[1.0,2.0,3.0,4.0]}] if constant_values else [],
            'shader_permutation_identity': {'identity_sha256':'shader-id','payload':{'vertex':{'constants':[]},'pixel':{'constants':[5],'sampler_types':{}}}},
        }],
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
    assert report['ready'] is True
    assert report['status'] == 'ready'


def test_runtime_golden_gate_blocks_render_command(tmp_path):
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(_material(False))); r.write_text(json.dumps(_runtime())); u.write_text(json.dumps({'6':10}))
    report=validate_runtime_golden_gate(m,r,usage_map_path=u)
    assert report['ready'] is False
    assert 'render-command:not-ready' in report['blocking_reasons']