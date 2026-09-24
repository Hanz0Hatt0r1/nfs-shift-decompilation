from bmw_runtime_draw_correlation import correlate_runtime_draw


def _material(first=150, count=6294):
    return {
        'format':'SHIFT.BMWMaterialSlice/1',
        'primitive_index':1,
        'render_command':{'submeshes':[
            {'index': 1, 'first_index':first,'index_count':count},
        ]},
    }


def _runtime(draws):
    return {'format':'SHIFT.D3D9RuntimeBindingEvidence/1','frames':[{'frame':7,'draws':draws}]}


def test_runtime_draw_correlation_accepts_exact_triangle_draw():
    report=correlate_runtime_draw(_material(),_runtime([{'start_index':150,'primitive_count':2098,'base_vertex_index':0}]))
    assert report['ready'] is True
    assert report['matches'][0]['frame']==7


def test_runtime_draw_correlation_blocks_wrong_range():
    report=correlate_runtime_draw(_material(),_runtime([{'start_index':0,'primitive_count':2098}]))
    assert report['ready'] is False
    assert 'runtime:draw-range-not-found' in report['blocking_reasons']


def test_runtime_draw_correlation_blocks_multiple_matches():
    draw={'start_index':150,'primitive_count':2098}
    report=correlate_runtime_draw(_material(),_runtime([draw,draw]))
    assert report['ready'] is False
    assert 'runtime:multiple-draws-match-primitive' in report['blocking_reasons']


def test_runtime_draw_correlation_requires_triangle_list_count():
    report=correlate_runtime_draw(_material(count=5),_runtime([{'start_index':150,'primitive_count':1}]))
    assert report['ready'] is False
    assert 'material:index-range-not-triangle-list' in report['blocking_reasons']

def test_runtime_draw_correlation_uses_explicit_submesh_index_when_slice_contains_one_selected_primitive():
    material = _material()
    material['render_command']['submeshes'][0]['index'] = 1
    report = correlate_runtime_draw(
        material,
        _runtime([{'start_index': 150, 'primitive_count': 2098, 'base_vertex_index': 0}]),
    )
    assert report['ready'] is True
    assert report['primitive_index'] == 1
    assert report['matches'][0]['frame'] == 7
