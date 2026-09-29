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


def _setup(monkeypatch, tmp_path, shader_entries=None, split_mesh=False):
    primary=tmp_path/'BMW_M3_E36.bff'
    primary.write_bytes(b'primary')
    entries=[
        FakeEntry('vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt',0),
    ]
    primary_payloads={e.path:b'x' for e in entries}
    shader_entries = shader_entries or ['render/shaders/bodywork.fx']
    for i,path in enumerate(shader_entries):
        entry=FakeEntry(path,i+2)
        entries.append(entry)
        primary_payloads[path]=b'x'
    entries.append(FakeEntry('render/textures/COMMON_PAINT.dds',20))
    primary_payloads['render/textures/COMMON_PAINT.dds']=b'x'

    archives={str(primary):FakeArchive(primary,entries,primary_payloads)}
    meb_archive=primary
    if split_mesh:
        supplemental=tmp_path/'BMW_M3_E36_Cockpit.bff'
        supplemental.write_bytes(b'supplemental')
        meb_entry=FakeEntry('vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb',1)
        archives[str(supplemental)]=FakeArchive(
            supplemental,
            [meb_entry],
            {meb_entry.path:b'x'},
        )
    else:
        meb_entry=FakeEntry('vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb',1)
        archives[str(primary)].entries.append(meb_entry)
        archives[str(primary)].payloads[meb_entry.path]=b'x'

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
    return primary, (tmp_path/'BMW_M3_E36_Cockpit.bff' if split_mesh else None)


def test_real_bmw_material_extractor_supports_split_material_and_mesh_archives(monkeypatch,tmp_path):
    primary,supplemental=_setup(monkeypatch,tmp_path,split_mesh=True)
    report=extractor.build_real_bmw_material_binding(primary,supplemental_bffs=[supplemental])
    assert report['ready'] is True
    assert report['provenance']['material_entry']['archive']=='BMW_M3_E36.bff'
    assert report['provenance']['mesh_entry']['archive']=='BMW_M3_E36_Cockpit.bff'


def test_real_bmw_material_extractor_builds_ready_binding(monkeypatch,tmp_path):
    primary,_=_setup(monkeypatch,tmp_path)
    report=extractor.build_real_bmw_material_binding(primary)
    assert report['format']=='SHIFT.RealBMWMaterialBindingEvidence/1'
    assert report['ready'] is True
    assert report['material_binding']['selection_status']=='unique'
    assert report['generic_material_gate']['ready'] is True
    assert report['paint_contract']['ready'] is True
    assert report['paint_shader_gate']['ready'] is True
    assert report['provenance']['material_entry']['index']==0
    assert report['provenance']['mesh_entry']['index']==1
    assert report['boundary']['runtime_instance_attribution']=='not-proven'


def test_real_bmw_material_extractor_accepts_identical_duplicate_shader_source(monkeypatch,tmp_path):
    primary,_=_setup(monkeypatch,tmp_path)
    original_bff = extractor.BFF
    primary_archive = original_bff(str(primary))
    supplemental=tmp_path/'RENDER.bff'
    supplemental.write_bytes(b'render')
    duplicate=FakeEntry('render/shaders/bodywork.fx',99)
    supplemental_archive=FakeArchive(
        supplemental,
        [duplicate],
        {duplicate.path:b'x'},
    )
    def fake_bff(path):
        path = str(Path(path))
        if path == str(supplemental):
            return supplemental_archive
        return primary_archive
    monkeypatch.setattr(extractor,'BFF',fake_bff)
    report=extractor.build_real_bmw_material_binding(
        primary,supplemental_bffs=[supplemental]
    )
    assert report['ready'] is True
    assert report['provenance']['shader_source']['archive']=='BMW_M3_E36.bff'


def test_real_bmw_material_extractor_blocks_conflicting_duplicate_shader_source(monkeypatch,tmp_path):
    primary,_=_setup(monkeypatch,tmp_path)
    original_bff = extractor.BFF
    primary_archive = original_bff(str(primary))
    supplemental=tmp_path/'RENDER.bff'
    supplemental.write_bytes(b'render')
    duplicate=FakeEntry('render/shaders/bodywork.fx',99)
    supplemental_archive=FakeArchive(
        supplemental,
        [duplicate],
        {duplicate.path:b'different'},
    )
    def fake_bff(path):
        path = str(Path(path))
        if path == str(supplemental):
            return supplemental_archive
        return primary_archive
    monkeypatch.setattr(extractor,'BFF',fake_bff)
    with pytest.raises(ValueError,match='conflicting duplicate entry'):
        extractor.build_real_bmw_material_binding(
            primary,supplemental_bffs=[supplemental]
        )


def test_fxo_candidates_are_family_filtered_and_duplicate_resources_collapsed(tmp_path):
    a=FakeArchive(
        tmp_path/'A.bff',
        [
            FakeEntry('render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo',1),
            FakeEntry('render/shaders/cache/render_shaders_glass_11112222.fxo',2),
        ],
        {
            'render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo':b'body-a',
            'render/shaders/cache/render_shaders_glass_11112222.fxo':b'glass',
        },
    )
    b=FakeArchive(
        tmp_path/'B.bff',
        [
            FakeEntry('render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo',3),
            FakeEntry('render/shaders/cache/render_shaders_bodywork_ccccdddd.fxo',4),
        ],
        {
            'render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo':b'body-a',
            'render/shaders/cache/render_shaders_bodywork_ccccdddd.fxo':b'body-b',
        },
    )
    candidates,duplicates=extractor._fxo_candidates_for_shader(
        extractor._entry_rows([a,b]),
        'render/shaders/bodywork.fx',
    )
    assert duplicates == 1
    assert [name for name,_ in candidates] == [
        'render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo',
        'render/shaders/cache/render_shaders_bodywork_ccccdddd.fxo',
    ]


def test_fxo_candidate_duplicate_path_conflict_fails_closed(tmp_path):
    path='render/shaders/cache/render_shaders_bodywork_aaaabbbb.fxo'
    a=FakeArchive(tmp_path/'A.bff',[FakeEntry(path,1)],{path:b'a'})
    b=FakeArchive(tmp_path/'B.bff',[FakeEntry(path,2)],{path:b'b'})
    with pytest.raises(ValueError,match='conflicting duplicate entry'):
        extractor._fxo_candidates_for_shader(
            extractor._entry_rows([a,b]),
            'render/shaders/bodywork.fx',
        )


def test_real_bmw_material_extractor_requires_actual_files(monkeypatch,tmp_path):
    missing=tmp_path/'missing.bff'
    with pytest.raises(FileNotFoundError):
        extractor.build_real_bmw_material_binding(missing)


def test_real_bmw_material_extractor_accepts_external_shader_source(monkeypatch,tmp_path):
    primary,_=_setup(monkeypatch,tmp_path,shader_entries=['render/shaders/bodywork.fx','vehicles/shaders/bodywork.fx'])
    external=tmp_path/'bodywork.fx'
    external.write_text('float4 main() : COLOR { return 1; }',encoding='utf-8')
    report=extractor.build_real_bmw_material_binding(primary,shader_source_file=external)
    assert report['ready'] is True
    assert report['provenance']['shader_source']['kind']=='external-file'
    assert report['provenance']['shader_source']['path']==str(external)
    assert 'shader_source_entry' not in report['provenance']


def test_real_bmw_material_extractor_rejects_wrong_external_shader_name(monkeypatch,tmp_path):
    primary,_=_setup(monkeypatch,tmp_path)
    external=tmp_path/'glass.fx'
    external.write_text('void main() {}',encoding='utf-8')
    with pytest.raises(ValueError,match='does not match material reference'):
        extractor.build_real_bmw_material_binding(primary,shader_source_file=external)



def _generic_binding():
    value = _binding()
    value = dict(value)
    value['material'] = 'GENERIC_WINDOWS'
    value['shader'] = 'glass.fx'
    value['specialization'] = {'requested': []}
    value['bindings'] = []
    value['selected_fxo'] = {
        'file': 'glass.fxo',
        'program_offset': 96,
        'exact': True,
        'vertex_pair_selection_status': 'unique',
        'pixel_sha256': '1' * 64,
        'vertex_sha256': '2' * 64,
        'pair_sha256': '3' * 64,
    }
    value['permutation_identity'] = {
        'format': 'SHIFT.ShaderPermutationIdentity/1',
        'identity_sha256': '4' * 64,
    }
    return value


def test_generic_material_gate_requires_unique_exact_linked_permutation():
    ready = extractor.validate_generic_material_binding(_generic_binding())
    assert ready['ready'] is True

    broken = _generic_binding()
    broken['permutation_identity'] = None
    result = extractor.validate_generic_material_binding(broken)
    assert result['ready'] is False
    assert (
        'generic-material:permutation-identity-missing'
        in result['blocking_reasons']
    )


def test_real_bmw_material_extractor_supports_nonpaint_bmt(monkeypatch, tmp_path):
    primary, _ = _setup(monkeypatch, tmp_path)
    archive = extractor.BFF(primary)

    generic_bmt = 'vehicles/bmw_m3_e36/generic_windows.bmt'
    generic_shader = 'render/shaders/glass.fx'
    archive.entries.extend([
        FakeEntry(generic_bmt, 30),
        FakeEntry(generic_shader, 31),
    ])
    archive.payloads[generic_bmt] = b'generic-bmt'
    archive.payloads[generic_shader] = b'generic-fx'

    monkeypatch.setattr(
        extractor,
        'parse_bmt_material',
        lambda data: {
            'material': {
                'name': 'GENERIC_WINDOWS',
                'shader': generic_shader,
                'specializations': [],
                'shaderparams': [],
            }
        },
    )
    monkeypatch.setattr(
        extractor,
        'link_material',
        lambda *args, **kwargs: _generic_binding(),
    )
    monkeypatch.setattr(
        extractor,
        'validate_material_binding',
        lambda binding: (_ for _ in ()).throw(
            AssertionError('paint contract must not run for nonpaint material')
        ),
    )
    monkeypatch.setattr(
        extractor,
        'validate_bmw_paint_shader_gate',
        lambda binding: (_ for _ in ()).throw(
            AssertionError('paint shader gate must not run for nonpaint material')
        ),
    )

    report = extractor.build_real_bmw_material_binding(
        primary,
        material_bmt=generic_bmt,
    )

    assert report['ready'] is True
    assert report['material_bmt'] == generic_bmt
    assert report['generic_material_gate']['ready'] is True
    assert report['paint_contract'] is None
    assert report['paint_shader_gate'] is None
    assert report['provenance']['material_entry']['path'] == generic_bmt
