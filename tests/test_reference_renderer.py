from reference_renderer import orthographic_mvp, rasterize_mesh, render_mesh_json


def _triangle():
    return {
        "vertices": [(-0.7, -0.6, 0.0), (0.7, -0.6, 0.0), (0.0, 0.7, 0.0)],
        "indices": [0, 1, 2],
        "colors": [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)],
    }


def test_reference_renderer_fills_triangle():
    mesh = _triangle()
    image = rasterize_mesh(
        mesh["vertices"],
        mesh["indices"],
        colors=mesh["colors"],
        width=64,
        height=64,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    assert image.startswith(b"P6\n64 64\n255\n")
    body = image.split(b"\n", 3)[3]
    clear = bytes((12, 12, 12))
    assert sum(1 for i in range(0, len(body), 3) if body[i:i+3] != clear) > 100


def test_reference_renderer_is_deterministic():
    mesh = _triangle()
    mvp = orthographic_mvp(mesh["vertices"])
    a = rasterize_mesh(mesh["vertices"], mesh["indices"], colors=mesh["colors"], width=32, height=32, mvp=mvp)
    b = rasterize_mesh(mesh["vertices"], mesh["indices"], colors=iter(mesh["colors"]), width=32, height=32, mvp=mvp)
    assert a == b


def test_reference_renderer_rejects_bad_index_buffer():
    mesh = _triangle()
    try:
        rasterize_mesh(mesh["vertices"], [0, 1], width=8, height=8)
    except ValueError as exc:
        assert "divisible by three" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_render_mesh_json_writes_expected_contract(tmp_path):
    out = tmp_path / "triangle.ppm"
    result = render_mesh_json(_triangle(), out, width=16, height=16)
    assert out.exists()
    assert result["format"] == "SHIFT.ReferenceRender/1"
    assert result["vertex_count"] == 3
    assert result["triangle_count"] == 1
