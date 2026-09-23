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


def _static_draw():
    return {
        "format": "SHIFT.StaticDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "world_matrix": [
            [1, 0, 0, 0.1],
            [0, 1, 0, 0.0],
            [0, 0, 1, 0.0],
            [0, 0, 0, 1],
        ],
    }


def test_reference_renderer_accepts_static_draw_contract(tmp_path):
    from reference_renderer import render_static_draw
    out = tmp_path / "draw.ppm"
    result = render_static_draw(_static_draw(), _triangle(), out, width=32, height=32)
    assert result["format"] == "SHIFT.StaticDrawReference/1"
    assert result["world_matrix_applied"] is True
    assert out.exists()


def test_reference_renderer_rejects_unready_static_draw(tmp_path):
    from reference_renderer import render_static_draw
    draw = _static_draw()
    draw["ready"] = False
    draw["blocking_reasons"] = ["shader-selection:ambiguous"]
    try:
        render_static_draw(draw, _triangle(), tmp_path / "bad.ppm")
    except ValueError as exc:
        assert "shader-selection:ambiguous" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def _draw_packet_ready():
    return {
        "schema": "SHIFT.DrawPacket/1",
        "scene": {"archive": "CAR.bff", "path": "cars/body.vhf"},
        "node": {"name": "BODY", "type": "OBJECT"},
        "mesh": {
            "ref": "cars/body.meb",
            "resolved": {"path": "cars/body.meb"},
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200",
                    "location": 0,
                    "offset": 0,
                    "element_size": 12,
                    "abi_status": "inferred",
                }],
            },
        },
        "world_matrix": [
            [1, 0, 0, 0.0],
            [0, 1, 0, 0.0],
            [0, 0, 1, 0.0],
            [0, 0, 0, 1.0],
        ],
        "submeshes": [{
            "first_index": 0,
            "index_count": 3,
            "material": {
                "name": "BODY",
                "status": "unique",
                "shader_pair": {
                    "selection_status": "unique",
                    "interface": {"valid": True},
                    "vertex_format": {"valid": True},
                },
                "linked_shader_pair": {
                    "format": "SHIFT.LinkedShaderPair/1",
                },
            },
        }],
    }


def test_reference_renderer_consumes_draw_packet_boundary(tmp_path):
    from reference_renderer import render_draw_packet
    packet = _draw_packet_ready()
    out = tmp_path / "packet.ppm"
    mesh = _triangle()
    result = render_draw_packet(
        packet,
        mesh,
        out,
        width=32,
        height=32,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    assert result["format"] == "SHIFT.StaticDrawReference/1"
    assert result["draw_contract"]["ready"] is True
    assert result["draw_contract"]["blocking_reasons"] == []
    assert out.exists()


def test_reference_renderer_rejects_unready_draw_packet(tmp_path):
    from reference_renderer import render_draw_packet
    packet = _draw_packet_ready()
    packet["submeshes"][0]["material"]["linked_shader_pair"] = None
    try:
        render_draw_packet(packet, _triangle(), tmp_path / "blocked.ppm", width=16, height=16)
    except ValueError as exc:
        assert "shader-glsl:missing" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_draw_packet_golden_render_has_stable_sha256(tmp_path):
    import json
    from reference_renderer import render_draw_packet_json

    packet_path = tmp_path / "packet.json"
    mesh_path = tmp_path / "mesh.json"
    out = tmp_path / "golden.ppm"
    packet_path.write_text(json.dumps(_draw_packet_ready()), encoding="utf-8")
    mesh_path.write_text(json.dumps(_triangle()), encoding="utf-8")

    result = render_draw_packet_json(
        packet_path,
        mesh_path,
        out,
        width=32,
        height=32,
    )
    assert result["sha256"] == "34b8ca110ed9fba3a6a254438525d5b5f6056e1ecb8cfc5e07d404cbf0c77921"
