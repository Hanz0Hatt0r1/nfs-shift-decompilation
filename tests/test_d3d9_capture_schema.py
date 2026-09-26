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

def test_capture_schema_rejects_invalid_create_texture():
    row = {
        "event": "create_texture",
        "frame": 1,
        "texture_ptr": "0x1",
        "width": 0,
        "height": 32,
        "levels": 0,
        "usage": 0,
        "format": 21,
        "pool": 1,
    }
    reasons = validate_capture_event(row)
    assert "create-texture:width-invalid" in reasons
    assert "create-texture:levels-invalid" in reasons


def test_capture_schema_rejects_invalid_create_cube_texture():
    row = {
        "event": "create_cube_texture",
        "frame": 1,
        "texture_ptr": "0x2",
        "edge_length": 0,
        "levels": 0,
        "usage": 0,
        "format": 21,
        "pool": 1,
    }
    reasons = validate_capture_event(row)
    assert "create-cube-texture:edge-length-invalid" in reasons
    assert "create-cube-texture:levels-invalid" in reasons


def test_capture_schema_accepts_texture_payload():
    row = {
        "event": "texture_payload",
        "frame": 3,
        "texture_ptr": "0x100",
        "resource_type_name": "texture2d",
        "level": 0,
        "width": 8,
        "height": 8,
        "pitch": 16,
        "format": 827611204,
        "pool": 1,
        "byte_size": 32,
        "snapshot_status": "captured",
        "payload_path": "textures/0x100_l0.bin",
    }
    assert validate_capture_event(row) == []


def test_capture_schema_rejects_invalid_texture_payload():
    row = {
        "event": "texture_payload",
        "frame": 3,
        "texture_ptr": "0x100",
        "level": -1,
        "width": 0,
        "height": 0,
        "pitch": 0,
        "format": 0,
        "pool": 0,
        "byte_size": 0,
        "snapshot_status": "bad",
    }
    reasons = validate_capture_event(row)
    assert "texture-payload:level-invalid" in reasons
    assert "texture-payload:width-invalid" in reasons
    assert "texture-payload:height-invalid" in reasons
    assert "texture-payload:pitch-invalid" in reasons
    assert "texture-payload:byte-size-invalid" in reasons
    assert "texture-payload:status-invalid" in reasons


def test_capture_schema_accepts_cube_texture_payload():
    row = {
        "event": "texture_payload",
        "frame": 3,
        "texture_ptr": "0x200",
        "resource_type_name": "cube_texture",
        "face": 2,
        "face_name": "py",
        "level": 0,
        "width": 256,
        "height": 256,
        "pitch": 1024,
        "format": 113,
        "pool": 0,
        "byte_size": 65536,
        "snapshot_status": "captured",
        "payload_path": "cube/0x200_py_l0.bin",
    }
    assert validate_capture_event(row) == []


def test_capture_schema_rejects_invalid_cube_texture_face():
    row = {
        "event": "texture_payload",
        "frame": 3,
        "texture_ptr": "0x200",
        "resource_type_name": "cube_texture",
        "face": 6,
        "face_name": "bad",
        "level": 0,
        "width": 256,
        "height": 256,
        "pitch": 1024,
        "format": 113,
        "pool": 0,
        "byte_size": 65536,
        "snapshot_status": "captured",
    }
    reasons = validate_capture_event(row)
    assert "texture-payload:face-invalid" in reasons
