from source_vehicle_identity import validate_source_vehicle_identity


def _source(case='bmw'):
    value='bmw_m3_e36' if case=='bmw' else 'nissan_240sx'
    return f'''float10 __fastcall FUN_004c32d0(int param_1)\n{{\n  switch(uVar1) {{\n  case 1:\n    pcVar3 = "nissan_240sx";\n    break;\n  case 2:\n    pcVar3 = "{value}";\n    break;\n  }}\n  return (float10)0;\n}}\n'''

def test_source_vehicle_identity_accepts_bmw_case2():
    report=validate_source_vehicle_identity(_source())
    assert report['ready'] is True
    assert report['selector_case']==2
    assert report['selector_value']=='bmw_m3_e36'
    assert report['selector_line'] is not None


def test_source_vehicle_identity_blocks_case2_drift():
    report=validate_source_vehicle_identity(_source('other'))
    assert report['ready'] is False
    assert 'source:bmw-case2-missing' in report['blocking_reasons']