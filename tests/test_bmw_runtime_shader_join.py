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

def test_runtime_shader_join_does_not_cross_correlate_draws_within_one_frame():
    runtime = _runtime()
    runtime['frames'][0]['shader_permutation_identity'] = {
        'identity_sha256': 'shader-id',
        'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}}},
    }
    runtime['frames'][0]['draw_snapshots'] = [
        {
            'frame': 17,
            'draw_index': 0,
            'draw': {'start_index': 0, 'primitive_count': 10, 'base_vertex_index': 0},
            'vertex_declaration': {
                'resource_sha256': 'abc',
                'resource_path': 'vehicles/bmw/body.meb',
            },
            'shader_permutation_identity': {
                'identity_sha256': 'other-shader',
                'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}},
                },
            },
            'texture_bindings': [{'stage': 1, 'texture_ptr': '0x31'}],
        },
        {
            'frame': 17,
            'draw_index': 1,
            'draw': {'start_index': 150, 'primitive_count': 20, 'base_vertex_index': 0},
            'vertex_declaration': {
                'resource_sha256': 'other-resource',
                'resource_path': 'vehicles/other/body.meb',
            },
            'shader_permutation_identity': {
                'identity_sha256': 'shader-id',
                'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}},
                },
            },
            'texture_bindings': [{'stage': 1, 'texture_ptr': '0x32'}],
        },
    ]
    report = join_runtime_shader(_material(), runtime)
    assert report['ready'] is False
    assert report['matched_frame_count'] == 0
    assert report['matched_draw_count'] == 0
    assert 'runtime:shader-or-resource-instance-not-found' in report['blocking_reasons']


def test_runtime_shader_join_selects_exact_draw_snapshot():
    runtime = _runtime()
    runtime['frames'][0]['draw_snapshots'] = [{
        'frame': 17,
        'draw_index': 3,
        'draw': {'start_index': 150, 'primitive_count': 20, 'base_vertex_index': 0},
        'vertex_declaration': {
            'resource_sha256': 'abc',
            'resource_path': 'vehicles/bmw/body.meb',
        },
        'shader_permutation_identity': {
            'identity_sha256': 'shader-id',
            'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}}},
        },
        'texture_bindings': [{'stage': 1, 'texture_ptr': '0x31'}],
    }]
    report = join_runtime_shader(_material(), runtime)
    assert report['ready'] is True
    assert report['matched_frame_count'] == 1
    assert report['matched_draw_count'] == 1
    assert report['candidate_frames'][0]['draw_index'] == 3
    assert report['candidate_frames'][0]['source'] == 'draw-snapshot'


def test_runtime_shader_join_keeps_legacy_frames_when_other_frames_have_snapshots():
    runtime = {
        'format': 'SHIFT.D3D9RuntimeBindingEvidence/1',
        'frames': [
            {
                'frame': 16,
                'vertex_declaration': {
                    'resource_sha256': 'abc',
                    'resource_path': 'vehicles/bmw/body.meb',
                },
                'shader_permutation_identity': {
                    'identity_sha256': 'shader-id',
                    'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}}},
                },
                'texture_bindings': [],
            },
            {
                'frame': 17,
                'vertex_declaration': {},
                'shader_permutation_identity': {
                    'identity_sha256': 'shader-id',
                    'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}}},
                },
                'draw_snapshots': [{
                    'frame': 17,
                    'draw_index': 0,
                    'vertex_declaration': {
                        'resource_sha256': 'wrong',
                        'resource_path': 'vehicles/other/body.meb',
                    },
                    'shader_permutation_identity': {
                        'identity_sha256': 'shader-id',
                        'payload': {'pixel': {'sampler_types': {'1': 'sampler2D'}}},
                    },
                    'texture_bindings': [],
                }],
            },
        ],
    }
    report = join_runtime_shader(_material(), runtime)
    assert report['ready'] is True
    assert report['matched_frame_count'] == 1
    assert report['candidate_frames'][0]['frame'] == 16
    assert report['candidate_frames'][0]['source'] == 'frame-aggregate'


def test_runtime_shader_join_uses_exact_material_draw_range():
    material = _material()
    material["primitive_index"] = 1
    material["render_command"] = {
        "submeshes": [
            {"index": 0, "first_index": 0, "index_count": 30},
            {"index": 1, "first_index": 150, "index_count": 6294},
        ]
    }
    runtime = _runtime()
    base = {
        "vertex_declaration": {
            "resource_sha256": "abc",
            "resource_path": "vehicles/bmw/body.meb",
        },
        "texture_bindings": [{"stage": 1, "texture_ptr": "0x31"}],
    }
    runtime["frames"][0]["draw_snapshots"] = [
        {
            **base,
            "frame": 17,
            "draw_index": 0,
            "draw": {"start_index": 0, "primitive_count": 10, "base_vertex_index": 0},
            "shader_permutation_identity": {
                "identity_sha256": "shader-id",
                "payload": {"pixel": {"sampler_types": {"1": "sampler2D"}}},
            },
        },
        {
            **base,
            "frame": 17,
            "draw_index": 1,
            "draw": {"start_index": 150, "primitive_count": 2098, "base_vertex_index": 0},
            "shader_permutation_identity": {
                "identity_sha256": "shader-id",
                "payload": {"pixel": {"sampler_types": {"1": "sampler2D"}}},
            },
        },
    ]
    report = join_runtime_shader(material, runtime)
    assert report["ready"] is True
    assert report["matched_draw_count"] == 1
    assert report["candidate_frames"][0]["draw_index"] == 1


def test_runtime_shader_join_blocks_invalid_material_draw_range():
    material = _material()
    material["primitive_index"] = 1
    material["render_command"] = {
        "submeshes": [{"index": 1, "first_index": 151, "index_count": 6294}]
    }
    report = join_runtime_shader(_material(), {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [],
    })
    assert report["ready"] is False
