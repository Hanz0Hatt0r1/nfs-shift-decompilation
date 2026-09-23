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


def test_bab_bind_pose_quaternion_is_converted_to_local_matrix():
    from bab_format import bab_local_matrices
    bab = {"bones": [{
        "index": 0,
        "name": "root",
        "rotation_quaternion_xyzw": [0, 0, 0, 1],
        "translation": [1, 2, 3],
    }]}
    assert bab_local_matrices(bab) == [[
        1.0, 0.0, 0.0, 1.0,
        0.0, 1.0, 0.0, 2.0,
        0.0, 0.0, 1.0, 3.0,
    ]]


def test_bab_bas_bind_skeleton_keeps_animation_payload_opaque():
    from bab_format import build_bab_bas_skeleton
    bab = {
        "header": {"name": "idle"},
        "bones": [{
            "index": 0, "name": "root",
            "rotation_quaternion_xyzw": [0, 0, 0, 1],
            "translation": [0, 0, 0],
        }],
        "animation_payload_offset": 128,
        "animation_payload_size": 64,
        "animation_payload_sha256": "abc",
    }
    bas = {
        "name": "car",
        "nodes": [{"index": 0, "name": "root", "parent": None, "mirror": None}],
    }
    r = build_bab_bas_skeleton(bab, bas)
    assert r["coverage"] == 1.0
    assert r["links"][0]["parent"] is None
    assert r["animation_payload"]["decoded"] is False
    assert r["animation_payload"]["sha256"] == "abc"
