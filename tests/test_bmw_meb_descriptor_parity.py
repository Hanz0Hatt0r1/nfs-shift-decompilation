from bmw_meb_descriptor_parity import validate_meb_descriptor_parity


def _material(words=(2,0,0)):
    return {
        'format':'SHIFT.BMWMaterialSlice/1',
        'mesh':{
            'vertex_layout':{'attributes':[{'property_id':'200','usage':'POSITION','usage_index':0}]},
            'property_descriptors':[{'id':'200','offset':88,'words':list(words),'raw_hex':'020000000000000000000000'}],
        },
    }


def test_meb_descriptor_parity_accepts_exact_position_triple():
    report=validate_meb_descriptor_parity(_material())
    assert report['ready'] is True
    assert report['checks'][0]['type_ordinal']==2
    assert report['checks'][0]['usage_ordinal']==0
    assert report['checks'][0]['channel']==0


def test_meb_descriptor_parity_blocks_type_mismatch():
    report=validate_meb_descriptor_parity(_material((4,0,0)))
    assert report['ready'] is False
    assert 'meb-descriptor:type-mismatch:200' in report['blocking_reasons']


def test_meb_descriptor_parity_blocks_channel_mismatch():
    report=validate_meb_descriptor_parity(_material((2,0,1)))
    assert report['ready'] is False
    assert 'meb-descriptor:channel-mismatch:200' in report['blocking_reasons']


def test_meb_descriptor_parity_blocks_missing_descriptor():
    material=_material()
    material['mesh']['property_descriptors']=[]
    report=validate_meb_descriptor_parity(material)
    assert report['ready'] is False
    assert 'meb-descriptor:missing:200' in report['blocking_reasons']