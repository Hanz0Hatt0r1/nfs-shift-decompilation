from bmw_runtime_parity import validate_runtime_parity
from d3d9_shader_constant_bind_evidence import analyze_d3d9_shader_constant_bind


def _material(value=None):
    value = [1.0, 2.0, 3.0, 4.0] if value is None else value
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'ready': True,
        'golden_identity': {'resource': 'vehicles/bmw/body.meb', 'resource_sha256': 'sha'},
        'material': {'permutation_identity': {'format': 'SHIFT.ShaderPermutationIdentity/1', 'identity_sha256': 'shader-id'}},
        'uniform_binding': {'bindings': [{'name': 'primerBasis', 'register_set': 2, 'register_index': 5, 'register_count': 1, 'stage': 'pixel', 'ctab_type': 'float4', 'value': value}]},
        'mesh': {'vertex_layout': {'attributes': [{'property_id': '460', 'usage': 'COLOR', 'usage_index': 0}]}},
        'textures': [],
    }


def _runtime(values=None):
    values = [1.0, 2.0, 3.0, 4.0] if values is None else values
    return {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'declarations': [{'pointer': '0x100', 'decoded': {'records': [{'type': 4, 'usage': 10, 'usage_index': 0}]}}],
        'frames': [{
            'frame': 3,
            'vertex_declaration': {'declaration_ptr': '0x100', 'resource_sha256': 'sha'},
            'constant_writes': [{'stage': 'pixel', 'start_register': 5, 'vector4f_count': 1, 'values': values}],
            'shader_permutation_identity': {'identity_sha256': 'shader-id', 'payload': {'vertex': {'constants': []}, 'pixel': {'constants': [5], 'sampler_types': {}}}},
        }],
    }


def test_runtime_parity_matches_exact_constant_values():
    report = validate_runtime_parity(_material(), _runtime(), usage_map={6: 10}, require_constant_values=True)
    assert report['ready'] is True
    assert report['constant_parity']['value_status'] == 'match'


def test_runtime_parity_blocks_constant_value_mismatch():
    report = validate_runtime_parity(_material(), _runtime([1.0, 2.0, 9.0, 4.0]), usage_map={6: 10}, require_constant_values=True)
    assert report['ready'] is False
    assert 'constant-values:pixel:primerBasis:mismatch' in report['blocking_reasons']


def test_runtime_parity_blocks_missing_constant_capture_when_required():
    runtime = _runtime()
    runtime['frames'][0]['constant_writes'] = []
    report = validate_runtime_parity(_material(), runtime, usage_map={6: 10}, require_constant_values=True)
    assert report['ready'] is False
    assert 'constant-values:pixel:primerBasis:not-captured' in report['blocking_reasons']


def test_shader_constant_bind_source_shape_is_observed():
    source = '''
void FUN_0084eb80(int param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)
{
  (**(code **)(**(int **)(param_1 + 8) + 0x178))(*(int **)(param_1 + 8),param_2,param_3,param_4);
}
void FUN_0084eea0(int param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)
{
  (**(code **)(**(int **)(param_1 + 8) + 0x1b4))(*(int **)(param_1 + 8),param_2,param_3,param_4);
}
'''
    report = analyze_d3d9_shader_constant_bind(source)
    assert report['status'] == 'observed'
    assert report['bindings']['vertex_float']['vtable_byte_offset'] == '0x178'
    assert report['bindings']['pixel_float']['vtable_byte_offset'] == '0x1b4'