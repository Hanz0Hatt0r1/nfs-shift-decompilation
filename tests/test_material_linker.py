import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from material_linker import link_material, parse_fx_samplers
from shader_ir import parse_shader_blobs

def synthetic_fxo():
    names=[b'diffuseMap\0',b'environmentMap\0',b'specularMap\0']
    header_size=28; info_size=20*len(names); type_size=20
    offsets=[]; pos=header_size+info_size+type_size
    for n in names: offsets.append(pos); pos+=len(n)
    payload=bytearray(b'CTAB')
    payload+=struct.pack('<7I',header_size,0,0xFFFF0300,len(names),header_size,0,0)
    for i,no in enumerate(offsets):
        payload+=struct.pack('<IHHHHII',no,3,(0,2,1)[i],1,0,header_size+info_size,0)
    payload+=struct.pack('<HHHHHHII',4,12,1,1,1,0,0,0)
    payload+=b''.join(names); payload+=b'\x00'*((-len(payload))%4)
    return struct.pack('<I',0xFFFF0300)+struct.pack('<I',((len(payload)//4)<<16)|0xFFFE)+payload+struct.pack('<I',0xFFFF)

def test_ctab_reflection_exposes_sampler_registers():
    blobs=parse_shader_blobs(synthetic_fxo())
    assert len(blobs)==1
    assert {s['name']:s['register'] for s in blobs[0].ctab_samplers}=={'diffuseMap':0,'environmentMap':2,'specularMap':1}

def test_material_linker_maps_bmt_texture_names_to_sampler_registers():
    source='''texture diffuseTexture; texture specularTexture; texture environmentTexture;
    sampler2D diffuseMap : SAMPLER < string SamplerTexture="diffuseTexture"; string MinFilter="Linear"; string MagFilter="Linear"; string MipFilter="Linear"; string AddressU="Wrap"; string AddressV="Wrap"; > = sampler_state { Texture=<diffuseTexture>; };
    sampler2D specularMap : SAMPLER < string SamplerTexture="specularTexture"; string MinFilter="Linear"; string MagFilter="Linear"; string MipFilter="Linear"; string AddressU="Wrap"; string AddressV="Wrap"; > = sampler_state { Texture=<specularTexture>; };
    samplerCUBE environmentMap : SAMPLER < string SamplerTexture="environmentTexture"; string MinFilter="Linear"; string MagFilter="Linear"; string MipFilter="Linear"; string AddressU="Clamp"; string AddressV="Clamp"; string AddressW="Clamp"; > = sampler_state { Texture=<environmentTexture>; };'''
    material={'name':'TEST','shader':'render\\shaders\\glass.fx','technique':'Glass','shaderparams':[
        {'name':'diffuseTexture','type':'EPT_TEXTURE','value':'Vehicles\\Textures\\A.dds'},
        {'name':'specularTexture','type':'EPT_TEXTURE','value':'Vehicles\\Textures\\B.dds'}]}
    r=link_material(material,source,fxo_candidates=[('glass.fxo',synthetic_fxo())],
                    texture_paths=['vehicles/textures/a.dds','vehicles/textures/b.dds'])
    by={b['sampler']:b for b in r['bindings']}
    assert by['diffuseMap']['texture_resolved'].endswith('a.dds')
    assert by['specularMap']['d3d9_sampler_register']==1
    assert r['selected_fxo'] is not None and r['selected_fxo']['exact']

def test_fx_sampler_state_parser():
    s=parse_fx_samplers('samplerCUBE env : SAMPLER < string SamplerTexture="environmentTexture"; string AddressU="Clamp"; string AddressV="Clamp"; string AddressW="Clamp"; > = sampler_state {};')
    assert s[0]['sampler']=='env' and s[0]['sampler_type']=='samplerCUBE'
    assert s[0]['texture_parameter']=='environmentTexture' and s[0]['address_w']=='Clamp'


def test_material_linker_does_not_hide_unhashed_shader_ties():
    source='''texture diffuseTexture; sampler2D diffuseMap : SAMPLER < string SamplerTexture="diffuseTexture"; > = sampler_state { Texture=<diffuseTexture>; };'''
    material={'name':'TEST','shader':'body.fx','technique':'Default','shaderparams':[
        {'name':'diffuseTexture','type':'EPT_TEXTURE','value':'a.dds'}]}
    # Two identical-scoring pixel programs in separate FXO files produce no
    # pair hash in this synthetic fixture; their stable file/offset identity
    # must still make the material selection explicitly ambiguous.
    blobs=synthetic_fxo()
    r=link_material(material,source,fxo_candidates=[('a.fxo',blobs),('b.fxo',blobs)],
                    texture_paths=['a.dds'])
    assert r['selection_status']=='ambiguous'
    assert len(r['ambiguous_candidates'])==2


def test_material_selection_tie_uses_all_evidence_fields():
    from material_linker import _selection_evidence_key
    base = {
        "exact": True,
        "score": 3,
        "vertex_pair_valid": True,
        "vertex_pair_score": 0.9,
        "uniform_coverage": 0.5,
        "specialization_score": 1.0,
        "specialization_contradicted": [],
        "specialization_unexpected": [],
        "uniform_matches": ["a"],
    }
    better = dict(base)
    worse = dict(base)
    worse["specialization_contradicted"] = ["METALLIC"]
    assert _selection_evidence_key(better) != _selection_evidence_key(worse)


def synthetic_linkable_fxo_pair():
    """Build one minimal CTAB-backed VS/PS pair with semantic register mismatch."""
    import struct

    def ctab(name: bytes, stage_version: int, register: int) -> bytes:
        header = 28
        info = 20
        typ = 20
        name_off = header + info + typ
        payload = bytearray(b"CTAB")
        payload += struct.pack("<7I", header, 0, stage_version, 1, header, 0, 0)
        payload += struct.pack("<IHHHHII", name_off, 3, register, 1, 0, header + info, 0)
        payload += struct.pack("<HHHHHHII", 4, 12, 1, 1, 1, 0, 0, 0)
        payload += name
        payload += b"\x00" * ((-len(payload)) % 4)
        return struct.pack("<I", stage_version) + struct.pack(
            "<I", ((len(payload) // 4) << 16) | 0xFFFE
        ) + payload

    vs_version = 0xFFFE0300
    ps_version = 0xFFFF0300
    dcl = (2 << 24) | 31
    vs = bytearray(ctab(b"diffuseMap\x00", vs_version, 0))
    vs += struct.pack(
        "<III", dcl, 0, 0x80000000 | 0 | (15 << 16) | (1 << 28)
    )
    vs += struct.pack(
        "<III", dcl, 5 | (5 << 16), 0x80000000 | 1 | (15 << 16) | (6 << 28)
    )
    vs += struct.pack("<I", 0xFFFF)

    ps = bytearray(ctab(b"diffuseMap\x00", ps_version, 0))
    ps += struct.pack(
        "<III", dcl, 5 | (5 << 16), 0x80000000 | 0 | (15 << 16) | (1 << 28)
    )
    ps += struct.pack("<I", 0xFFFF)
    return bytes(vs + ps)


def test_material_binding_includes_linked_shader_pair():
    source = '''texture diffuseTexture;
    sampler2D diffuseMap : SAMPLER < string SamplerTexture="diffuseTexture"; > =
        sampler_state { Texture=<diffuseTexture>; };
    float4 sampleDiffuse(float2 uv) { return tex2D(diffuseMap, uv); }'''
    material = {
        "name": "TEST",
        "shader": "body.fx",
        "shaderparams": [
            {"name": "diffuseTexture", "type": "EPT_TEXTURE", "value": "a.dds"},
        ],
    }
    data = synthetic_linkable_fxo_pair()
    r = link_material(
        material,
        source,
        fxo_candidates=[("body.fxo", data)],
        texture_paths=["a.dds"],
        vertex_properties=["200"],
    )
    assert r["selection_status"] == "unique"
    linked = r["linked_shader_pair"]
    assert linked is not None, r.get("linked_shader_error")
    assert linked["varying_locations"] == [{"usage": "TEXCOORD", "index": 5, "location": 0}]
    assert linked["vertex_input_locations"] == {0: 0}
    assert "layout(location=0) out vec4 out_1;" in linked["vertex_glsl"]
    assert "layout(location=0) in vec4 in_0;" in linked["pixel_glsl"]
    identity = r["permutation_identity"]
    assert identity is not None
    assert identity["format"] == "SHIFT.ShaderPermutationIdentity/1"
    assert len(identity["identity_sha256"]) == 64
