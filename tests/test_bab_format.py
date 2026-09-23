import struct
from bas_format import parse_bas
from bab_format import parse_bab, link_bab_bas

def make_bab():
    b=bytearray(b"BAB\x00")
    b+=struct.pack("<7I",13,10,0,0,1,0,0)
    # overwrite: header fields actually span 0x18 onward; extend to 0x30
    b[0x18:0x30]=struct.pack("<6I",1,3,2,0x3f700000,2,0)
    b+=b"\x00"*((0x30-len(b)))
    for name,q,t in [
      ("Hips",(0,0,0,1),(1,2,3)),
      ("Spine",(0,0,0,1),(0,1,0)),
    ]:
      nb=name.encode(); b+=struct.pack("<I",len(nb))+nb+b"\x00"*((-((len(nb)+4)%4))%4)
      b+=struct.pack("<7f",*q,*t)+struct.pack("<I",3)+struct.pack("<4f",1,1,1,0)
    return bytes(b)

def test_bab_header_and_bones():
    r=parse_bab(make_bab())
    assert r["bones_parsed"]==2
    assert r["bones"][0]["name"]=="Hips"
    assert r["bones"][0]["rotation_quaternion_xyzw"]==[0,0,0,1]
    assert r["bones"][0]["translation"]==[1,2,3]
    assert r["bones"][0]["unit_quaternion"]

def test_bab_bas_name_link():
    bab=parse_bab(make_bab())
    bas=parse_bas(b'''<SKELETON name="x"><NODE name="Hips"/><NODE name="Spine"/></SKELETON>''')
    r=link_bab_bas(bab,bas)
    assert r["coverage"]==1.0
