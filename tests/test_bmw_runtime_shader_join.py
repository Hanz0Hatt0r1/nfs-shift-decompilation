from bmw_runtime_shader_join import join_runtime_shader


def _material():
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'ready': True,
        'golden_identity': {
            'resource': 'vehicles/bmw/body.meb',
            'resource_sha256': 'abc',
        },
        'material': {
            'permutation_identity': {
                'format': 'SHIFT.ShaderPermutationIdentity/1',
                'identity_sha256': 'shader-id',
            },
        },
        'textures': [{
            'sampler_type': 'sampler2D',
            'd3d9_sampler_register': 1,
            'material_parameter': 'Diffuse',
        }],
    }


def _runtime(shader_id='shader-id', resource_sha='abc', sampler_type='sampler2D'):
    return {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'frames': [{
            'frame': 17,
            'vertex_declaration': {
                'resource_sha256': resource_sha,
                'resource_path': 'vehicles/bmw/body.meb',
            },
            'vertex_shader': {'shader_ptr': '0x10', 'create_known': True},
            'pixel_shader': {'shader_ptr': '0x20', 'create_known': True},
            'shader_permutation_identity': {
                'format': 'SHIFT.ShaderPermutationIdentity/1',
                'identity_sha256': shader_id,
                'payload': {'pixel': {'sampler_types': {'1': sampler_type}}},
            },
        }],
    }


def test_runtime_shader_join_requires_shader_and_resource_identity():
    report = join_runtime_shader(_material(), _runtime())
    assert report['ready'] is True
    assert report['matched_frame_count'] == 1


def test_runtime_shader_join_blocks_same_shader_on_wrong_resource():
    report = join_runtime_shader(_material(), _runtime(resource_sha='wrong'))
    assert report['ready'] is False
    assert 'runtime:shader-or-resource-instance-not-found' in report['blocking_reasons']


def test_runtime_shader_join_blocks_sampler_type_mismatch():
    report = join_runtime_shader(_material(), _runtime(sampler_type='samplerCube'))
    assert report['ready'] is False
    assert 'runtime:sampler-contract:17' in report['blocking_reasons']