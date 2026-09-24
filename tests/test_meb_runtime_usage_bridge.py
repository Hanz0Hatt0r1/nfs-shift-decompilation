from meb_runtime_usage_bridge import build_usage_ordinal_bridge


def _material():
    return {
        'format':'SHIFT.BMWMaterialSlice/1',
        'golden_identity':{'resource':'vehicles/bmw/body.meb','resource_sha256':'sha'},
        'mesh':{'property_descriptors':[
            {'id':'200','words':[2,0,0]},
            {'id':'460','words':[4,6,0]},
        ]},
    }


def _runtime(records, resource_sha='sha'):
    return {
        'format':'SHIFT.D3D9RuntimeBindingEvidence/1',
        'declarations':[{'pointer':'0x1','decoded':{'records':records}}],
        'frames':[{'frame':1,'vertex_declaration':{'declaration_ptr':'0x1','resource_sha256':resource_sha}}],
    }


def test_usage_bridge_accepts_unique_same_resource_matches():
    runtime=_runtime([
        {'type':2,'usage':0,'usage_index':0},
        {'type':4,'usage':6,'usage_index':0},
    ])
    report=build_usage_ordinal_bridge(_material(),runtime)
    assert report['ready'] is True
    assert report['usage_map']=={'0':0,'6':6}


def test_usage_bridge_blocks_conflicting_runtime_usage_for_one_ordinal():
    runtime=_runtime([
        {'type':4,'usage':6,'usage_index':0},
        {'type':4,'usage':10,'usage_index':0},
    ])
    material={'format':'SHIFT.BMWMaterialSlice/1','golden_identity':{'resource':'vehicles/bmw/body.meb','resource_sha256':'sha'},'mesh':{'property_descriptors':[{'id':'460','words':[4,6,0]}]}}
    report=build_usage_ordinal_bridge(material,runtime)
    assert report['ready'] is False
    assert report['status']=='ambiguous'
    assert report['conflicts'][0]['usage_ordinal']==6


def test_usage_bridge_ignores_unrelated_resource():
    report=build_usage_ordinal_bridge(_material(),_runtime([{'type':4,'usage':6,'usage_index':0}],resource_sha='other'))
    assert report['ready'] is False
    assert report['status']=='not-proven'
    assert report['usage_map']=={}