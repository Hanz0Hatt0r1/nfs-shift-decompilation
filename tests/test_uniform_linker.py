import struct, sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from uniform_linker import link_material_uniforms

def synthetic_fxo_with_constant():
    # Minimal VS with a CTAB float4 named primerBasis at c5.
    names=[b"primerBasis\0"]; header=28; info=20; typ=20; no=header+info+typ
    payload=bytearray(b"CTAB")+bytearray(struct.pack("<7I",header,0,0xFFFE0300,1,header,0,0))
    payload+=struct.pack("<IHHHHII",no,2,5,1,0,header+info,0)
    payload+=struct.pack("<HHHHHHII",1,3,1,4,1,0,0,0)+names
    payload+=b"\0"*((-len(payload))%4)
    return struct.pack("<I",0xFFFE0300)+struct.pack("<I",((len(payload)//4)<<16)|0xFFFE)+payload+struct.pack("<I",0xFFFF)

def test_material_uniform_binding():
    data=synthetic_fxo_with_constant()
    r=link_material_uniforms({"shaderparams":[{"name":"primerBasis","type":"EPT_VEC4","value":[1,2,3,4]}]},data,[0])
    assert r["bindings"][0]["register_index"]==5
    assert r["bindings"][0]["ctab_type"]=="float4"
