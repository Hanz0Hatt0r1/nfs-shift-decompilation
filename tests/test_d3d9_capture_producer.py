from d3d9_capture_schema import validate_capture_event, validate_capture_events


def _events():
    return [
        {"event":"create_vertex_declaration","frame":0,"event_index":0,"thread_id":7,"device_ptr":"0x10","declaration_ptr":"0x20","bytes_hex":"0000000000000000"},
        {"event":"set_vertex_declaration","frame":0,"event_index":1,"thread_id":7,"device_ptr":"0x10","declaration_ptr":"0x20"},
        {"event":"set_stream_source","frame":0,"event_index":2,"thread_id":7,"device_ptr":"0x10","vertex_buffer_ptr":"0x30","stream":0,"offset_in_bytes":0,"stride":32},
        {"event":"set_indices","frame":0,"event_index":3,"thread_id":7,"device_ptr":"0x10","index_buffer_ptr":"0x40"},
        {"event":"set_texture","frame":0,"event_index":4,"thread_id":7,"device_ptr":"0x10","stage":3,"texture_ptr":"0x41","resource_descriptor_status":"observed","resource_type":3,"resource_type_name":"cube_texture","width":128,"height":128,"format":21,"pool":1,"level_count":8},
        {"event":"create_vertex_shader","frame":0,"event_index":5,"thread_id":7,"device_ptr":"0x10","shader_ptr":"0x50","bytes_hex":"0000ffff"},
        {"event":"set_vertex_shader","frame":0,"event_index":6,"thread_id":7,"device_ptr":"0x10","shader_ptr":"0x50"},
        {"event":"set_vertex_shader_constant_f","frame":0,"event_index":7,"thread_id":7,"device_ptr":"0x10","start_register":0,"vector4f_count":1,"values":[1.0,0.0,0.0,1.0]},
        {"event":"create_pixel_shader","frame":0,"event_index":8,"thread_id":7,"device_ptr":"0x10","shader_ptr":"0x60","bytes_hex":"0000ffff"},
        {"event":"set_pixel_shader","frame":0,"event_index":9,"thread_id":7,"device_ptr":"0x10","shader_ptr":"0x60"},
        {"event":"set_pixel_shader_constant_f","frame":0,"event_index":10,"thread_id":7,"device_ptr":"0x10","start_register":0,"vector4f_count":1,"values":[1.0,1.0,1.0,1.0]},
        {"event":"draw_indexed_primitive","frame":0,"event_index":11,"thread_id":7,"device_ptr":"0x10","primitive_type":4,"base_vertex_index":0,"min_vertex_index":0,"num_vertices":3,"start_index":0,"primitive_count":1},
    ]


def test_capture_producer_event_family_matches_schema():
    events=_events()
    assert all(not validate_capture_event(row) for row in events)
    report=validate_capture_events(events)
    assert report["ready"] is True
    assert report["event_count"] == len(events)


def test_capture_producer_accepts_optional_object_metadata():
    row=_events()[0]
    assert validate_capture_event(row)==[]


def test_capture_producer_rejects_bad_constant_shape():
    row=_events()[7]
    row["values"]=[1.0,2.0,3.0]
    assert "constant:values-length-mismatch" in validate_capture_event(row)


def test_capture_producer_rejects_invalid_stream_stride():
    row=_events()[2]
    row["stride"]=0
    assert "stream-stride:invalid" in validate_capture_event(row)
