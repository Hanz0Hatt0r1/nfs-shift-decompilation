from bmw_runtime_parity import validate_runtime_parity


def _material():
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'ready': True,
        'golden_identity': {'resource': 'vehicles/bmw/body.meb', 'resource_sha256': 'sha'},
        'material': {
            'permutation_identity': {
                'format': 'SHIFT.ShaderPermutationIdentity/1',
                'identity_sha256': 'shader-id',
            },
        },
        'uniform_binding': {
            'format': 'SHIFT.MaterialUniformBinding/1',
            'bindings': [{
                'name': 'primerBasis', 'register_set': 2, 'register_index': 5,
                'register_count': 1, 'stage': 'pixel', 'ctab_type': 'float4',
            }],
        },
        'mesh': {
            'vertex_layout': {'attributes': [{
                'property_id': '460', 'usage': 'COLOR', 'usage_index': 0,
            }]},
        },
        'textures': [],
    }


def _runtime(const_registers=None, declaration_type=4):
    return {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'declarations': [{
            'pointer': '0x100',
            'decoded': {
                'records': [{
                    'index': 0, 'stream': 0, 'offset': 0,
                    'type': declaration_type, 'usage': 10, 'usage_index': 0,
                }],
            },
        }],
        'frames': [{
            'frame': 9,
            'vertex_declaration': {'declaration_ptr': '0x100', 'resource_sha256': 'sha', 'resource_path': 'vehicles/bmw/body.meb'},
            'shader_permutation_identity': {
                'format': 'SHIFT.ShaderPermutationIdentity/1',
                'identity_sha256': 'shader-id',
                'payload': {
                    'vertex': {'constants': []},
                    'pixel': {'constants': const_registers if const_registers is not None else [5], 'sampler_types': {}},
                },
            },
        }],
    }


def test_bmw_runtime_parity_accepts_constant_and_color_declaration_match():
    report = validate_runtime_parity(_material(), _runtime(), usage_map={6: 10})
    assert report['ready'] is True
    assert report['constant_parity']['status'] == 'match'
    assert report['declaration_parity']['status'] == 'match'


def test_bmw_runtime_parity_blocks_missing_constant_register():
    report = validate_runtime_parity(_material(), _runtime(const_registers=[]), usage_map={6: 10})
    assert report['ready'] is False
    assert any(x.startswith('constant:pixel:primerBasis:missing') for x in report['blocking_reasons'])


def test_bmw_runtime_parity_blocks_wrong_color_declaration_type():
    report = validate_runtime_parity(_material(), _runtime(declaration_type=8), usage_map={6: 10})
    assert report['ready'] is False
    assert 'declaration:460:not-found' in report['blocking_reasons']


def test_bmw_runtime_parity_requires_explicit_usage_map():
    report = validate_runtime_parity(_material(), _runtime(), usage_map=None)
    assert report['ready'] is False
    assert 'declaration:usage-map-missing' in report['blocking_reasons']