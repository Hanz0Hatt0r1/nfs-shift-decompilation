from __future__ import annotations
import hashlib
import math
import struct
from typing import Any

ALIGN4=lambda x:(x+3)&~3

def _u32(data:bytes,off:int)->int:
    if off+4>len(data): raise ValueError("BAB u32 out of range")
    return struct.unpack_from("<I",data,off)[0]

def _f32s(data:bytes,off:int,count:int)->list[float]:
    if off+4*count>len(data): raise ValueError("BAB float record out of range")
    return list(struct.unpack_from("<"+"f"*count,data,off))

def parse_bab(data:bytes,*,max_bones:int|None=None, preserve_tail:bool=True)->dict[str,Any]:
    """Parse the verified BMW SHIFT BAB animation-bank header and bone table.

    The first 0x30 bytes and the fixed bone record grammar are established from
    real SHIFT BAB samples. The post-table animation payload is intentionally
    opaque and is retained by offset/hash until its keyframe grammar is proven.
    """
    if len(data)<0x30 or data[:4]!=b"BAB\x00":
        raise ValueError("not a SHIFT BAB resource")
    version=_u32(data,4)
    name_len=_u32(data,8)
    name_start=0x0c
    name_end=name_start+name_len
    if name_end>len(data): raise ValueError("BAB name exceeds resource")
    name=data[name_start:name_end].decode("utf-8","replace")
    cursor=max(0x30,ALIGN4(name_end))
    header={
        "magic":"BAB\\0","version":version,"name_length":name_len,"name":name,
        "field_18":_u32(data,0x18),"field_1c":_u32(data,0x1c),
        "bone_record_count":_u32(data,0x20),"field_24_f32":struct.unpack_from("<f",data,0x24)[0],
        "field_28":_u32(data,0x28),"field_2c":_u32(data,0x2c),
    }
    declared=header["bone_record_count"]
    count=min(declared,max_bones) if max_bones is not None else declared
    bones=[]
    for i in range(count):
        record_start=cursor
        if cursor+4>len(data): raise ValueError(f"BAB truncated name length at bone {i}")
        n=_u32(data,cursor); cursor+=4
        if n==0 or n>4096 or cursor+n>len(data): raise ValueError(f"BAB invalid bone name length {n} at {i}")
        bone_name=data[cursor:cursor+n].decode("utf-8","replace"); cursor+=n
        cursor=ALIGN4(cursor)
        q=_f32s(data,cursor,7); cursor+=28
        flag=_u32(data,cursor); cursor+=4
        tail=_f32s(data,cursor,4); cursor+=16
        quat=q[:4]; translation=q[4:7]
        qnorm=math.sqrt(sum(x*x for x in quat))
        bones.append({
            "index":i,"name":bone_name,"record_offset":record_start,
            "rotation_quaternion_xyzw":quat,"translation":translation,
            "flag":flag,"tail_floats":tail,"quaternion_norm":qnorm,
            "unit_quaternion":abs(qnorm-1.0)<0.01,
            "record_size":cursor-record_start,
        })
    tail_offset=cursor
    trailing=data[tail_offset:]
    strings=[]
    pos=0
    while pos<len(trailing):
        j=trailing.find(b"\x00",pos)
        if j<0: j=len(trailing)
        raw=trailing[pos:j]
        if 5<=len(raw)<=128 and all(32<=x<127 for x in raw):
            strings.append({"offset":tail_offset+pos,"text":raw.decode("ascii","replace")})
        pos=j+1
        if len(strings)>=256: break
    return {
        "format":"SHIFT.BAB","version":1,"header":header,
        "skeleton_offset":max(0x30,ALIGN4(name_end)),"skeleton_end":tail_offset,
        "bones_declared":declared,"bones_parsed":len(bones),"bones":bones,
        "animation_payload_offset":tail_offset,
        "animation_payload_size":len(trailing),
        "animation_payload_sha256":hashlib.sha256(trailing).hexdigest(),
        "animation_string_hints":strings,
        "animation_payload_preserved":preserve_tail,
    }

def link_bab_bas(bab:dict[str,Any],bas:dict[str,Any])->dict[str,Any]:
    bas_nodes={str(n.get("name","")):n for n in bas.get("nodes",[]) if n.get("name")}
    links=[]; missing=[]; extras=[]
    bab_names={b["name"] for b in bab.get("bones",[])}
    for b in bab.get("bones",[]):
        n=bas_nodes.get(b["name"])
        rec={"bone_index":b["index"],"name":b["name"],"bas_index":n.get("index") if n else None,"bas_parent":None,"mirror":n.get("mirror") if n else None,"matched":n is not None}
        if n:
            rec["bas_parent"]=next((x.get("name") for x in bas.get("nodes",[]) if x.get("index")==n.get("parent")),None)
        else: missing.append(rec)
        links.append(rec)
    extras=[{"name":n["name"],"index":n["index"]} for n in bas.get("nodes",[]) if n.get("name") not in bab_names]
    return {"format":"SHIFT.BABBasLink/1","matched":len(links)-len(missing),"missing":missing,"extra_bas_nodes":extras,"links":links,"coverage":(len(links)-len(missing))/len(links) if links else 1.0}
