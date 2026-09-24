from pathlib import Path
from types import SimpleNamespace

import pytest

import bmw_material_from_bff as extractor


class FakeEntry:
    def __init__(self, path, index):
        self.path = path
        self.index = index
        self.compressed_size = 10
        self.uncompressed_size = 10


class FakeArchive:
    def __init__(self, path, entries, payloads):
        self.path = Path(path)
        self.entries = entries
        self.payloads = payloads

    def extract_entry(self, entry):
        return self.payloads[entry.path]

    def close(self):
        pass


def _binding():
    return {
        'format':'SHIFT.MaterialBinding/1',
        'material':'BMW_M3_E36_PAINT',
        'shader':'bodywork.fx',
        'specialization':{'requested':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH']},
        'bindings': [
            {'texture_parameter':'diffuseTexture','sampler':'diffuseMap','d3d9_sampler_register':1,'texture':'COMMON_PAINT.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'Linear','address_u':'Wrap','address_v':'Wrap','srgb':True,'binding':'material-texture'},
            {'texture_parameter':'specularTexture','sampler':'specularMap','d3d9_sampler_register':2,'texture':'COMMON_PAINT_SPECULAR.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'Linear','address_u':'Wrap','address_v':'Wrap','srgb':True,'binding':'material-texture'},
            {'texture_parameter':'scratchControlTexture','sampler':'scratchControlMap','d3d9_sampler_register':4,'texture':'COMMON_BLANK.dds','min_filter':'Linear','mag_filter':'Linear','mip_filter':'None','address_u':'Clamp','address_v':'Clamp','srgb':False,'binding':'material-texture'},
            {'sampler':'environmentMap','d3d9_sampler_register':3,'binding':'external-or-specialised'},
            {'sampler':'sShadowMap_f1_0','d3d9_sampler_register':0,'binding':'external-or-specialised'},
        ],
        'unresolved_textures':[],
        'selection_status':'unique',
        'selected_fxo':{'file':'bodywork.fxo','program_offset':64,'exact':True,'vertex_pair_selection_status':'unique','pixel_sha256':'a'*64,'vertex_sha256':'b'*64,'pair_sha256':'c'*64,'specialization_matched':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH']},
        'shader_pair':{'selection_status':'unique'},
        'linked_shader_pair':{'format':'SHIFT.LinkedShaderPair/1'},
        'permutation_identity':{'format':'SHIFT.ShaderPermutationIdentity/1','identity_sha256':'d'*64},
    }


def _setup(monkeypatch, tmp_path, shader_entries=None):
    primary=tmp_path/'BMW_M3_E36.bff'
    primary.write_bytes(b'primary')
    entries=[
        FakeEntry('vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt',0),
        FakeEntry('vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb',1),
    ]
    for i,path in enumerate(shader_entries or ['render/shaders/bodywork.fx']):
        entries.append(FakeEntry(path,i+2))
    entries.append(FakeEntry('render/textures/COMMON_PAINT.dds',20))
    payloads={e.path:b'x' for e in entries}
    archives={str(primary):FakeArchive(primary,entries,payloads)}

    def fake_bff(path):
        return archives[str(Path(path))]

    monkeypatch.setattr(extractor,'BFF',fake_bff)
    monkeypatch.setattr(
        extractor,
        'parse_bmt_material',
        lambda data:{
            'material':{
                'name':'BMW_M3_E36_PAINT',
                'shader':'render/shaders/bodywork.fx',
                'specializations':['USE_FRESNEL','ALLOW_VINYLS','DIRT_SCRATCH'],
                'shaderparams':[{'name':'diffuseTexture','type':'EPT_TEXTURE','value':'COMMON_PAINT.dds'}],
            }
        },
    )
    monkeypatch.setattr(extractor,'read_meb',lambda data:SimpleNamespace(vertex_properties=['200','460']))
    monkeypatch.setattr(extractor,'link_material',lambda *args,**kwargs:_binding())
    return primary


def test_real_bmw_material_extractor_builds_ready_binding(monkeypatch,tmp_path):
    primary=_setup(monkeypatch,tmp_path)
    report=extractor.build_real_bmw_material_binding(primary)
    assert report['format']=='SHIFT.RealBMWMaterialBindingEvidence/1'
    assert report['ready'] is True
    assert report['material_binding']['selection_status']=='unique'
    assert report['paint_contract']['ready'] is True
    assert report['paint_shader_gate']['ready'] is True
    assert report['provenance']['material_entry']['index']==0
    assert report['provenance']['mesh_entry']['index']==1
    assert report['boundary']['runtime_instance_attribution']=='not-proven'


def test_real_bmw_material_extractor_blocks_ambiguous_bodywork_shader(monkeypatch,tmp_path):
    primary=_setup(
        monkeypatch,
        tmp_path,
        shader_entries=['render/shaders/bodywork.fx','vehicles/shaders/bodywork.fx'],
    )
    with pytest.raises(ValueError,match='expected one'):
        extractor.build_real_bmw_material_binding(primary)


def test_real_bmw_material_extractor_requires_actual_files(monkeypatch,tmp_path):
    missing=tmp_path/'missing.bff'
    with pytest.raises(FileNotFoundError):
        extractor.build_real_bmw_material_binding(missing)
