from bmw_m3_paint_contract import get_bmw_paint_contract, validate_material_binding


def _binding():
    contract=get_bmw_paint_contract()['contract']
    return {
        'shader':'bodywork.fx',
        'specializations':contract['specializations'][:],
        'textures':[
            {'material_parameter':'diffuseTexture','sampler':'diffuseMap','d3d9_sampler_register':1,'texture':'COMMON_PAINT.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'Linear','address_u':'Wrap','address_v':'Wrap','srgb':True},
            {'material_parameter':'specularTexture','sampler':'specularMap','d3d9_sampler_register':2,'texture':'COMMON_PAINT_SPECULAR.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'Linear','address_u':'Wrap','address_v':'Wrap','srgb':True},
            {'material_parameter':'scratchControlTexture','sampler':'scratchControlMap','d3d9_sampler_register':4,'texture':'COMMON_BLANK.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'None','address_u':'Clamp','address_v':'Clamp','srgb':False},
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

def test_bmw_paint_contract_accepts_compile_material_shape():
    raw=_binding()
    raw['shader']={'ref':'render/shaders/bodywork.fx','resolved':[{'path':'render/shaders/bodywork.fx'}]}
    raw['specializations']=None
    raw['specialization']=None
    raw['shader_selection']={
        'selected_fxo': {'specialization_matched':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH']},
    }
    raw['textures']=[
        {'material_parameter':'diffuseTexture','sampler':'diffuseMap','d3d9_sampler_register':1,'ref':'vehicles/textures/COMMON_PAINT.dds'},
        {'material_parameter':'specularTexture','sampler':'specularMap','d3d9_sampler_register':2,'ref':'vehicles/textures/COMMON_PAINT_SPECULAR.dds'},
        {'material_parameter':'scratchControlTexture','sampler':'scratchControlMap','d3d9_sampler_register':4,'ref':'vehicles/textures/COMMON_BLANK.dds'},
    ]
    report=validate_material_binding(raw)
    assert report['ready'] is True


def test_bmw_paint_contract_blocks_sampler_state_drift():
    binding=_binding()
    binding['textures'][0]['address_u']='Clamp'
    report=validate_material_binding(binding)
    assert report['ready'] is False
    assert 'sampler:diffuseMap:address_u:mismatch' in report['blocking_reasons']


def test_bmw_paint_contract_blocks_missing_sampler_state():
    binding=_binding()
    del binding['textures'][0]['mip_filter']
    report=validate_material_binding(binding)
    assert report['ready'] is False
    assert 'sampler:diffuseMap:mip_filter:missing' in report['blocking_reasons']
