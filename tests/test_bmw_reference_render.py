from pathlib import Path

import bmw_reference_render


def _slice(command_ready=True):
    return {
        'format': 'SHIFT.BMWMaterialSlice/1',
        'status': 'match',
        'ready': True,
        'blocking_reasons': [],
        'primitive_index': 1,
        'material_ref': 'vehicles/bmw/BMW_M3_E36_PAINT.mtx',
        'render_command': {
            'format': 'SHIFT.RenderCommand/1',
            'ready': command_ready,
            'blocking_reasons': [] if command_ready else ['render:not-ready'],
        },
    }


def test_bmw_reference_render_wraps_geometry_renderer(monkeypatch, tmp_path):
    captured = {}
    def fake_render(command, mesh, output, **kwargs):
        captured.update({'command': command, 'mesh': mesh, 'output': output, 'kwargs': kwargs})
        Path(output).write_bytes(b'P6\\n1 1\\n255\\n\\x01\\x02\\x03')
        return {'format': 'SHIFT.StaticDrawReference/1', 'sha': 'inner'}

    monkeypatch.setattr('reference_renderer.render_render_command', fake_render)
    output = tmp_path / 'bmw.ppm'
    result = bmw_reference_render.render_material_slice(
        _slice(), {'vertices': [(0, 0, 0)], 'indices': []}, output, width=1, height=1
    )
    assert result['format'] == 'SHIFT.BMWReferenceRender/1'
    assert result['status'] == 'rendered'
    assert result['sha256'] == 'b0d3d5d640c1f1f8cf4b50c00c3d1a5a7a72d6f27e9dca6dbf7c8d8c9c9c0c6b'
    assert captured['command']['format'] == 'SHIFT.RenderCommand/1'
    assert captured['kwargs']['width'] == 1
    assert output.exists()


def test_bmw_reference_render_rejects_blocked_slice(tmp_path):
    blocked = _slice(command_ready=False)
    blocked['ready'] = False
    blocked['blocking_reasons'] = ['render:not-ready']
    try:
        bmw_reference_render.render_material_slice(blocked, {}, tmp_path / 'bad.ppm')
    except ValueError as exc:
        assert 'render:not-ready' in str(exc)
    else:
        raise AssertionError('expected ValueError')