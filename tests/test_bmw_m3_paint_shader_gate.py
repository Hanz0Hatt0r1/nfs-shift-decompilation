from bmw_m3_paint_shader_gate import validate_bmw_paint_shader_gate


def _binding():
    return {
        'shader':'bodywork.fx',
        'specializations':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH'],
        'textures': [
            {'sampler':'diffuseMap','material_parameter':'diffuseTexture','d3d9_sampler_register':1},
            {'sampler':'specularMap','material_parameter':'specularTexture','d3d9_sampler_register':2},
            {'sampler':'scratchControlMap','material_parameter':'scratchControlTexture','d3d9_sampler_register':4},
        ],
        'external_samplers': [
            {'sampler':'environmentMap','d3d9_sampler_register':3},
            {'sampler':'sShadowMap_f1_0','d3d9_sampler_register':0},
        ],
        'unresolved_textures': [],
        'shader_selection': {
            'status':'unique',
            'selected_fxo': {
                'file':'bodywork.fxo','program_offset':64,'exact':True,
                'vertex_pair_selection_status':'unique',
                'pixel_sha256':'a'*64,'vertex_sha256':'b'*64,'pair_sha256':'c'*64,
            },
            'shader_pair': {'selection_status':'unique'},
            'linked_shader_pair': {'format':'SHIFT.LinkedShaderPair/1'},
            'permutation_identity': {'format':'SHIFT.ShaderPermutationIdentity/1','identity_sha256':'d'*64},
        },
    }


def test_bmw_paint_shader_gate_accepts_unique_exact_pair():
    report=validate_bmw_paint_shader_gate(_binding())
    assert report['ready'] is True
    assert report['blocking_reasons']==[]


def test_bmw_paint_shader_gate_blocks_ambiguous_selection():
    binding=_binding(); binding['shader_selection']['status']='ambiguous'
    report=validate_bmw_paint_shader_gate(binding)
    assert report['ready'] is False
    assert 'shader-selection:not-unique' in report['blocking_reasons']


def test_bmw_paint_shader_gate_blocks_missing_permutation_identity():
    binding=_binding(); binding['shader_selection']['permutation_identity']=None
    report=validate_bmw_paint_shader_gate(binding)
    assert report['ready'] is False
    assert 'shader-identity:missing-or-invalid' in report['blocking_reasons']


def test_bmw_paint_shader_gate_blocks_sampler_register_drift():
    binding=_binding(); binding['textures'][0]['d3d9_sampler_register']=9
    report=validate_bmw_paint_shader_gate(binding)
    assert report['ready'] is False
    assert 'sampler:diffuseMap:register-mismatch' in report['blocking_reasons']

def test_bmw_paint_shader_gate_accepts_material_binding_bindings_shape():
    binding=_binding()
    rows=[]
    for row in binding['textures']:
        rows.append(dict(row))
    rows.extend([
        {'binding':'external-or-specialised','sampler':'environmentMap','d3d9_sampler_register':3},
        {'binding':'external-or-specialised','sampler':'sShadowMap_f1_0','d3d9_sampler_register':0},
    ])
    binding.pop('textures')
    binding['bindings']=rows
    binding.pop('external_samplers')
    report=validate_bmw_paint_shader_gate(binding)
    assert report['ready'] is True
