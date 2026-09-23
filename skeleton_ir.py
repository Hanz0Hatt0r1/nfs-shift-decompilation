from __future__ import annotations
import math
import struct
from typing import Any

def parse_skeleton(skeleton: dict[str, Any]) -> dict[str, Any]:
    num_bones=int(skeleton.get("num_bones",0))
    char_blob=bytes.fromhex(skeleton.get("char_blob_hex",""))
    bone_blob=bytes.fromhex(skeleton.get("bone_blob_hex",""))
    if len(bone_blob)!=num_bones*48:
        raise ValueError(f"bone blob size {len(bone_blob)} != {num_bones*48}")
    names=[x.decode("utf-8","replace") for x in char_blob.split(b"\x00") if x]
    bones=[]
    for i in range(num_bones):
        vals=list(struct.unpack_from("<12f",bone_blob,i*48))
        rot=vals[:9]
        translation=vals[9:12]
        det=(rot[0]*(rot[4]*rot[8]-rot[5]*rot[7])
             -rot[1]*(rot[3]*rot[8]-rot[5]*rot[6])
             +rot[2]*(rot[3]*rot[7]-rot[4]*rot[6]))
        mat4=[
            vals[0],vals[1],vals[2],vals[3],
            vals[4],vals[5],vals[6],vals[7],
            vals[8],vals[9],vals[10],vals[11],
            0.0,0.0,0.0,1.0,
        ]
        bones.append({
            "index":i,
            "name":names[i] if i<len(names) else f"bone_{i}",
            "matrix_3x4":vals,
            "matrix_4x4_candidate":mat4,
            "translation":translation,
            "rotation_determinant":det,
            "orthonormal_candidate":abs(abs(det)-1.0)<0.02,
        })
    return {
        "format":"SHIFT.Skeleton/1",
        "num_bones":num_bones,
        "num_chars":int(skeleton.get("num_chars",len(char_blob))),
        "bone_names":names,
        "bones":bones,
        "raw_char_blob_hex":char_blob.hex(),
        "raw_bone_blob_hex":bone_blob.hex(),
    }

def skinning_contract(vertex_properties: list[str] | tuple[str,...], skeleton: dict[str,Any] | None=None) -> dict[str,Any]:
    props={str(x.get("id")) if isinstance(x,dict) else str(x) for x in vertex_properties}
    weights="310" in props
    indices="580" in props
    contract={"has_weights":weights,"has_indices":indices,"skinned":weights and indices,"valid":weights==indices}
    if skeleton is not None:
        contract["bone_count"]=int(skeleton.get("num_bones",0))
    if weights and not indices: contract["error"]="weights_without_indices"
    if indices and not weights: contract["error"]="indices_without_weights"
    return contract
