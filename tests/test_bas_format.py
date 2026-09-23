from bas_format import parse_bas

def test_bas_transform_and_hierarchy():
    data=b'''<?xml version="1.0"?><SKELETON name="CAR"><EXPORTER><Tool name="test"/></EXPORTER><NODE name="ROOT"><TRANSFORM data="3F800000 00000000 00000000 00000000 00000000 3F800000 00000000 00000000 00000000 00000000 3F800000 00000000 3F800000 40000000 40400000 3F800000"/><NODE name="CHILD" mirror="CHILD"><TRANSFORM data="3F800000 00000000 00000000 00000000 00000000 3F800000 00000000 00000000 00000000 00000000 3F800000 00000000 00000000 00000000 00000000 3F800000"/></NODE></NODE></SKELETON>'''
    r=parse_bas(data)
    assert r["node_count"]==2 and r["nodes"][1]["parent"]==0
    assert r["nodes"][0]["translation"]==[1.0,2.0,3.0]
