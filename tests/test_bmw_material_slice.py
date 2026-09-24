from bmw_material_slice import select_material_slice


def _slice(status='unique', linked=True, resolved=True, command_ready=True):
    material = {
        'ref': 'vehicles/bmw/paint.mtx',
        'resolved': [{'path': 'vehicles/bmw/paint.bmt'}] if resolved else [],
        'shader_selection': {
            'status': status,
            'shader_pair': {'selection_status': 'unique'},
            'linked_shader_pair': {'format': 'SHIFT.LinkedShaderPair/1'} if linked else None,
            'permutation_identity': {'format': 'SHIFT.ShaderPermutationIdentity/1', 'identity_sha256': 'id'} if linked else None,
            'bindings': [],
        },
        'textures': [{
            'binding_source': 'fxo-ctab',
            'd3d9_sampler_register': 1,
        }],
    }
    return {
        'format': 'SHIFT.BMWRenderSlice/1',
        'ready': True,
        'packet': {
            'submeshes': [
                {'first_index': 0, 'index_count': 30, 'material': material, 'material_ref': 'vehicles/bmw/paint.mtx'},
            ],
        },
        'render_command': {'ready': command_ready, 'blocking_reasons': [] if command_ready else ['command:not-ready']},
    }


def test_bmw_material_slice_accepts_unique_material_draw():
    report = select_material_slice(_slice())
    assert report['ready'] is True
    assert report['primitive_index'] == 0
    assert report['material_ref'] == 'vehicles/bmw/paint.mtx'


def test_bmw_material_slice_blocks_ambiguous_shader():
    report = select_material_slice(_slice(status='ambiguous'))
    assert report['ready'] is False
    assert 'shader-selection:ambiguous' in report['blocking_reasons']


def test_bmw_material_slice_blocks_missing_linked_shader():
    report = select_material_slice(_slice(linked=False))
    assert report['ready'] is False
    assert 'shader-glsl:missing' in report['blocking_reasons']


def test_bmw_material_slice_propagates_render_command_blocker():
    report = select_material_slice(_slice(command_ready=False))
    assert report['ready'] is False
    assert 'command:not-ready' in report['blocking_reasons']

def test_bmw_material_slice_blocks_missing_permutation_identity():
    report = select_material_slice(_slice())
    report_source = _slice()
    del report_source['packet']['submeshes'][0]['material']['shader_selection']['permutation_identity']
    report = select_material_slice(report_source)
    assert report['ready'] is False
    assert 'shader-permutation-identity:missing' in report['blocking_reasons']
