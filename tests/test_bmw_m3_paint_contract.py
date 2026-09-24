from bmw_m3_paint_contract import get_bmw_paint_contract, validate_material_binding


def _binding():
    contract=get_bmw_paint_contract()['contract']
    return {
        'shader':'bodywork.fx',
        'specializations':contract['specializations'][:],
        'textures':[
            {'material_parameter':'diffuseTexture','sampler':'diffuseMap','d3d9_sampler_register':1,'texture':'COMMON_PAINT.dds'},
            {'material_parameter':'specularTexture','sampler':'specularMap','d3d9_sampler_register':2,'texture':'COMMON_PAINT_SPECULAR.dds'},
            {'material_parameter':'scratchControlTexture','sampler':'scratchControlMap','d3d9_sampler_register':4,'texture':'COMMON_BLANK.dds'},
        ],
        'external_samplers':[
            {'sampler':'environmentMap','d3d9_sampler_register':3},
            {'sampler':'sShadowMap_f1_0','d3d9_sampler_register':0},
        ],
    }


def test_bmw_paint_contract_accepts_documented_binding():
    report=validate_material_binding(_binding())
    assert report['ready'] is True
    assert report['blocking_reasons']==[]


def test_bmw_paint_contract_blocks_shader_path_mismatch():
    binding=_binding(); binding['shader']='other.fx'
    report=validate_material_binding(binding)
    assert report['ready'] is False
    assert 'shader:path-mismatch' in report['blocking_reasons']


def test_bmw_paint_contract_blocks_missing_specialization():
    binding=_binding(); binding['specializations']=binding['specializations'][:-1]
    report=validate_material_binding(binding)
    assert report['ready'] is False
    assert any(x.startswith('specializations:missing:') for x in report['blocking_reasons'])


def test_bmw_paint_contract_blocks_sampler_register_drift():
    binding=_binding(); binding['textures'][0]['d3d9_sampler_register']=7
    report=validate_material_binding(binding)
    assert report['ready'] is False
    assert 'sampler:diffuseMap:register-mismatch' in report['blocking_reasons']