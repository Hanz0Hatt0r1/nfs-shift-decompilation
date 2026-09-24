from d3d9_capture_schema import validate_capture_event, validate_capture_events


def test_capture_schema_accepts_constant_write():
    row={'event':'set_pixel_shader_constant_f','frame':1,'start_register':5,'vector4f_count':1,'values':[1.0,2.0,3.0,4.0]}
    assert validate_capture_event(row)==[]


def test_capture_schema_rejects_constant_length_mismatch():
    row={'event':'set_pixel_shader_constant_f','frame':1,'start_register':5,'vector4f_count':1,'values':[1.0,2.0,3.0]}
    reasons=validate_capture_event(row)
    assert 'constant:values-length-mismatch' in reasons


def test_capture_schema_rejects_invalid_stream_stride():
    row={'event':'set_stream_source','frame':1,'stream':0,'vertex_buffer_ptr':'0x1','offset_in_bytes':0,'stride':0}
    reasons=validate_capture_event(row)
    assert 'stream-stride:invalid' in reasons


def test_capture_schema_reports_multiple_invalid_events():
    report=validate_capture_events([
        {'event':'set_indices','frame':1},
        {'event':'draw_indexed_primitive','frame':1,'primitive_count':'one'},
    ])
    assert report['format']=='SHIFT.D3D9RuntimeCaptureSchema/1'
    assert report['ready'] is False
    assert report['event_count']==2
    assert len(report['blocking_reasons'])>=1