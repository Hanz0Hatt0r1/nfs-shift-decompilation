from pathlib import Path
import json

from bmw_runtime_parity import validate_files as validate_runtime_parity_files


def test_runtime_parity_accepts_nested_usage_bridge_report(tmp_path):
    material={
        'format':'SHIFT.BMWMaterialSlice/1',
        'ready':True,
        'golden_identity':{'resource':'vehicles/bmw/body.meb','resource_sha256':'sha'},
        'material':{'permutation_identity':{'identity_sha256':'id'}},
        'uniform_binding':{'bindings':[]},
        'mesh':{'vertex_layout':{'attributes':[]}},
        'textures':[],
    }
    runtime={'format':'SHIFT.D3D9RuntimeBindingEvidence/1','frames':[]}
    m=tmp_path/'m.json'; r=tmp_path/'r.json'; u=tmp_path/'u.json'
    m.write_text(json.dumps(material)); r.write_text(json.dumps(runtime))
    u.write_text(json.dumps({'format':'SHIFT.MEBRuntimeUsageOrdinalBridge/1','status':'observed','usage_map':{'6':10}}))
    report=validate_runtime_parity_files(m,r,usage_map_path=u)
    assert report['format']=='SHIFT.BMWRuntimeParity/1'
    assert report['status']=='not-found'