from pathlib import Path
import json

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
        Path(output).write_bytes(b'P6\n1 1\n255\n\x01\x02\x03')
        return {'format': 'SHIFT.StaticDrawReference/1', 'sha': 'inner'}

    monkeypatch.setattr('reference_renderer.render_render_command', fake_render)
    output = tmp_path / 'bmw.ppm'
    result = bmw_reference_render.render_material_slice(
        _slice(), {'vertices': [(0, 0, 0)], 'indices': []}, output, width=1, height=1
    )
    assert result['format'] == 'SHIFT.BMWReferenceRender/1'
    assert result['status'] == 'rendered'
    assert result['sha256'] == 'f7f61f7db8e5185115f264ded4e62a8064628b0ba5b1b94d491c3d2cf4673042'
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

def test_render_files_accepts_slice_as_mesh_input(monkeypatch, tmp_path):
    import bmw_reference_render as module

    seen={}
    def fake_render(material_slice, mesh, output, **kwargs):
        seen['mesh']=mesh
        return {'ok':True}

    monkeypatch.setattr(module, 'render_material_slice', fake_render)
    slice_data=_slice()
    slice_data['mesh']={'format':'SHIFT.MEB','vertex_count':4}
    slice_path=tmp_path/'slice.json'
    mesh_path=tmp_path/'same.json'
    slice_path.write_text(json.dumps(slice_data), encoding='utf-8')
    mesh_path.write_text(json.dumps(slice_data), encoding='utf-8')
    result=module.render_files(slice_path, mesh_path, tmp_path/'out.png')
    assert result['ok'] is True
    assert seen['mesh']=={'format':'SHIFT.MEB','vertex_count':4}
