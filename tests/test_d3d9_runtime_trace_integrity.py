from d3d9_runtime_trace_integrity import validate_runtime_trace_integrity


def _complete_events():
    return [
        {'event':'create_vertex_declaration','frame':1,'declaration_ptr':'0x1','bytes_hex':'00'},
        {'event':'create_vertex_shader','frame':1,'shader_ptr':'0x2','bytes_hex':'aa'},
        {'event':'create_pixel_shader','frame':1,'shader_ptr':'0x3','bytes_hex':'bb'},
        {'event':'set_vertex_declaration','frame':1,'declaration_ptr':'0x1'},
        {'event':'set_vertex_shader','frame':1,'shader_ptr':'0x2'},
        {'event':'set_pixel_shader','frame':1,'shader_ptr':'0x3'},
        {'event':'set_stream_source','frame':1,'stream':0},
        {'event':'set_indices','frame':1,'index_buffer_ptr':'0x4'},
        {'event':'draw_indexed_primitive','frame':1,'primitive_count':1},
    ]


def test_runtime_trace_integrity_accepts_complete_draw():
    report=validate_runtime_trace_integrity(_complete_events())
    assert report['status']=='observed'
    assert report['blocking_reasons']==[]
    assert report['frames'][0]['draws']==1


def test_runtime_trace_integrity_rejects_bind_before_create():
    events=_complete_events()
    events[3]['declaration_ptr']='0x9'
    report=validate_runtime_trace_integrity(events)
    assert report['status']=='partial'
    assert any(x['reason']=='declaration-bind-before-create' for x in report['blocking_reasons'])


def test_runtime_trace_integrity_rejects_incomplete_draw_state():
    events=[x for x in _complete_events() if x['event']!='set_indices']
    report=validate_runtime_trace_integrity(events)
    assert report['status']=='partial'
    assert any(x['reason']=='draw-state-incomplete' for x in report['blocking_reasons'])


def test_runtime_trace_integrity_rejects_shader_pointer_reuse_with_new_bytes():
    events=_complete_events()+[{'event':'create_vertex_shader','frame':1,'shader_ptr':'0x2','bytes_hex':'cc'}]
    report=validate_runtime_trace_integrity(events)
    assert any(x['reason']=='shader-pointer-reused-with-different-bytes' for x in report['blocking_reasons'])

def test_runtime_trace_integrity_accepts_contiguous_event_indices():
    events = [
        dict(event, event_index=index)
        for index, event in enumerate(_complete_events(), start=10)
    ]
    report = validate_runtime_trace_integrity(events)
    assert report["event_index"]["status"] == "valid"
    assert report["event_index"]["first"] == 10
    assert report["event_index"]["last"] == 18


def test_runtime_trace_integrity_rejects_missing_event_index_in_sequence():
    events = [
        dict(event, event_index=index)
        for index, event in enumerate(_complete_events())
    ]
    events[-1]["event_index"] = 10
    report = validate_runtime_trace_integrity(events)
    assert report["status"] == "partial"
    assert report["event_index"]["status"] == "invalid"
    assert any(
        x["reason"] == "event-index-not-contiguous"
        for x in report["blocking_reasons"]
    )


def test_runtime_trace_integrity_keeps_legacy_no_event_index_fixtures_valid():
    report = validate_runtime_trace_integrity(_complete_events())
    assert report["event_index"]["status"] == "valid"
    assert report["event_index"]["observed_count"] == 0


def test_runtime_trace_integrity_rejects_partial_event_index_metadata():
    events = [
        dict(_complete_events()[0], event_index=0),
        *_complete_events()[1:],
    ]
    report = validate_runtime_trace_integrity(events)
    assert report["event_index"]["status"] == "invalid"
    assert any(
        x["reason"] == "event-index-partial"
        for x in report["blocking_reasons"]
    )
