from skeleton_ir import parse_skeleton, skinning_contract

def test_parse_meb_skeleton_records():
    import struct
    bb=struct.pack("<12f",1,0,0,0,1,0,0,0,1,1,2,3)
    s={"num_bones":1,"num_chars":5,"char_blob_hex":b"wheel\0".hex(),"bone_blob_hex":bb.hex()}
    r=parse_skeleton(s)
    assert r["bone_names"]==["wheel"]
    assert r["bones"][0]["translation"]==[1.0,2.0,3.0]
    assert r["bones"][0]["orthonormal_candidate"] is True

def test_skinning_contract_requires_weight_index_pair():
    assert skinning_contract(["200","310"])["valid"] is False
    assert skinning_contract(["200","310","580"])["skinned"] is True
    assert skinning_contract(["200"])["skinned"] is False
