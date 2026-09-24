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


def producer_events():
    return [
        {'event':'create_vertex_declaration','frame':0,'event_index':0,'thread_id':10,
         'device_ptr':'0x10','declaration_ptr':'0x20','bytes_hex':'0000000000000000'},
        {'event':'set_vertex_declaration','frame':0,'event_index':1,'thread_id':10,
         'device_ptr':'0x10','declaration_ptr':'0x20'},
        {'event':'set_stream_source','frame':0,'event_index':2,'thread_id':10,
         'device_ptr':'0x10','vertex_buffer_ptr':'0x30','stream':0,
         'offset_in_bytes':0,'stride':32},
        {'event':'set_indices','frame':0,'event_index':3,'thread_id':10,
         'device_ptr':'0x10','index_buffer_ptr':'0x40'},
        {'event':'create_vertex_shader','frame':0,'event_index':4,'thread_id':10,
         'device_ptr':'0x10','shader_ptr':'0x50','bytes_hex':'0000ffff'},
        {'event':'set_vertex_shader','frame':0,'event_index':5,'thread_id':10,
         'device_ptr':'0x10','shader_ptr':'0x50'},
        {'event':'set_vertex_shader_constant_f','frame':0,'event_index':6,'thread_id':10,
         'device_ptr':'0x10','start_register':0,'vector4f_count':1,
         'values':[1.0,0.0,0.0,1.0]},
        {'event':'create_pixel_shader','frame':0,'event_index':7,'thread_id':10,
         'device_ptr':'0x10','shader_ptr':'0x60','bytes_hex':'0000ffff'},
        {'event':'set_pixel_shader','frame':0,'event_index':8,'thread_id':10,
         'device_ptr':'0x10','shader_ptr':'0x60'},
        {'event':'set_pixel_shader_constant_f','frame':0,'event_index':9,'thread_id':10,
         'device_ptr':'0x10','start_register':0,'vector4f_count':1,
         'values':[1.0,1.0,1.0,1.0]},
        {'event':'draw_indexed_primitive','frame':0,'event_index':10,'thread_id':10,
         'device_ptr':'0x10','primitive_type':4,'base_vertex_index':0,
         'min_vertex_index':0,'num_vertices':3,'start_index':0,'primitive_count':1},
    ]


def test_producer_event_family_is_schema_valid():
    events=producer_events()
    assert all(not validate_capture_event(event) for event in events)
    report=validate_capture_events(events)
    assert report['ready'] is True
    assert report['event_count']==len(events)


def test_sequence_validation_rejects_event_index_gaps():
    events=producer_events()
    events[4]['event_index']=6
    report=validate_capture_events(events)
    assert report['ready'] is False
    assert any(item['reason']=='event-index:sequence-gap' for item in report['blocking_reasons'])


def test_sequence_validation_rejects_negative_frame():
    events=producer_events()
    events[-1]['frame']=-1
    report=validate_capture_events(events)
    assert report['ready'] is False
    assert any(item['reason']=='frame:negative' for item in report['blocking_reasons'])


def test_non_finite_constant_is_blocked():
    events=producer_events()
    events[6]['values']=[1.0,float('nan'),0.0,1.0]
    reasons=validate_capture_event(events[6])
    assert 'constant:values-nonfinite' in reasons
    assert 'constant:values-invalid' in reasons
