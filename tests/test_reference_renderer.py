from pathlib import Path
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
    assert result["sha256"] == "3981a2538abd99b38c0488e4bd0f6bf4a469c18c1d11712568a616a3ce9ce3cb"


def test_reference_renderer_honors_static_draw_submesh_index_range(tmp_path):
    from reference_renderer import render_static_draw
    mesh = {
        "vertices": [
            (-0.9, -0.8, 0.0), (0.0, 0.8, 0.0), (0.9, -0.8, 0.0),
            (-0.9, -0.2, 0.0), (0.0, 0.2, 0.0), (0.9, -0.2, 0.0),
        ],
        "indices": [0, 1, 2, 3, 4, 5],
        "colors": [
            (255, 0, 0, 255), (255, 0, 0, 255), (255, 0, 0, 255),
            (0, 255, 0, 255), (0, 255, 0, 255), (0, 255, 0, 255),
        ],
    }
    draw = _static_draw()
    draw["submeshes"] = [{"first_index": 0, "index_count": 3, "material": {}}]
    out = tmp_path / "range.ppm"
    render_static_draw(
        draw,
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
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert (0, 255, 0) not in pixels


def _render_command_ready():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "mesh": {
            "ref": "cars/body.meb",
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
            },
            "attributes": [{
                "location": 0,
                "property_id": "200",
                "offset": 0,
                "stride": 12,
                "storage": "f32x3",
            }],
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
            "shader": {
                "vertex": "#version 310 es\\nvoid main(){}",
                "pixel": "#version 310 es\\nvoid main(){}",
            },
            "uniforms": {
                "format": "SHIFT.MaterialUniformBinding/1",
                "bindings": [],
            },
            "textures": [],
            "constant_commands": [],
        }],
        "resource_plan": {
            "format": "SHIFT.RenderResources/1",
            "texture_count": 0,
            "sampler_count": 0,
        },
    }


def test_reference_renderer_executes_render_command(tmp_path):
    from reference_renderer import render_render_command
    out = tmp_path / "command.ppm"
    result = render_render_command(
        _render_command_ready(),
        _triangle(),
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
    assert result["command_contract"]["validation"]["valid"] is True
    assert result["command_contract"]["ready"] is True
    assert out.exists()


def test_reference_renderer_rejects_render_command_mesh_count_mismatch(tmp_path):
    from reference_renderer import render_render_command
    command = _render_command_ready()
    command["mesh"]["vertex_count"] = 4
    try:
        render_render_command(command, _triangle(), tmp_path / "bad.ppm", width=16, height=16)
    except ValueError as exc:
        assert "mesh vertex count mismatch" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_rasterizes_uv_texture(tmp_path):
    from reference_renderer import render_textured_static_draw
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((255, 32, 16, 255)),
    }
    mesh = {
        **_triangle(),
        "uv_layers": {
            "130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)],
        },
    }
    out = tmp_path / "textured.ppm"
    result = render_textured_static_draw(
        _static_draw(),
        mesh,
        image,
        out,
        sampler={
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        },
        width=32,
        height=32,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (255, 32, 16) in [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]


def test_reference_renderer_textured_path_requires_uv0(tmp_path):
    from reference_renderer import render_textured_static_draw
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_static_draw(_static_draw(), _triangle(), image, tmp_path / "bad.ppm")
    except ValueError as exc:
        assert "no UV0" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_executes_textured_render_command(tmp_path):
    from reference_renderer import render_textured_render_command
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((200, 100, 50, 255)),
    }
    mesh = {
        **_triangle(),
        "uv_layers": {
            "130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)],
        },
    }
    out = tmp_path / "command-textured.ppm"
    result = render_textured_render_command(
        _render_command_ready(),
        mesh,
        image,
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
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert result["command_contract"]["validation"]["valid"] is True
    assert out.exists()


def test_reference_renderer_textured_cli(tmp_path):
    import json
    import struct
    import subprocess
    import sys

    command_path = tmp_path / "command.json"
    mesh_path = tmp_path / "mesh.json"
    texture_path = tmp_path / "texture.dds"
    out = tmp_path / "cli.ppm"

    command_path.write_text(json.dumps(_render_command_ready()), encoding="utf-8")
    mesh_path.write_text(
        json.dumps({
            **_triangle(),
            "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
        }),
        encoding="utf-8",
    )

    values = (
        124, 0, 1, 1, 0, 0, 1,
        *([0] * 11),
        32, 0x40, 0, 32,
        0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000,
        0, 0, 0, 0, 0,
    )
    texture = b"DDS " + struct.pack("<31I", *values) + struct.pack("<I", 0xFF2010FF)
    texture_path.write_bytes(texture)

    proc = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "reference_renderer.py"),
            str(command_path),
            "--render-command",
            "--textured",
            "--mesh",
            str(mesh_path),
            "--texture",
            str(texture_path),
            "--output",
            str(out),
            "--width",
            "32",
            "--height",
            "32",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert result["texture_format"] == "RGBA32"
    assert len(result["output"]) > 0
    assert out.exists()


def test_textured_render_command_uses_embedded_sampler_state(tmp_path):
    from reference_renderer import render_textured_render_command
    command = _render_command_ready()
    command["submeshes"][0]["textures"] = [{
        "resource": "material",
        "resource_binding_id": "tb_body",
        "texture_id": "tex_body",
        "sampler_id": "smp_body",
        "sampler_state": {
            "format": "SHIFT.SamplerState/1",
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        },
    }]
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((123, 45, 67, 255)),
    }
    out = tmp_path / "embedded-sampler.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        sampler=None,
        width=16,
        height=16,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert (123, 45, 67) in pixels


def _textured_tex_shader_program():
    def operand(kind, reg_type, index, **extra):
        return {
            "token": 0x80000000,
            "kind": kind,
            "reg_type": reg_type,
            "index": index,
            "swizzle": extra.get("swizzle"),
            "source_modifier": extra.get("source_modifier"),
            "write_mask": extra.get("write_mask"),
        }

    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "pixel",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [{"usage": "TEXCOORD", "index": 0, "register": "v0"}],
        "outputs": [{"usage": "COLOR", "index": 0, "register": "oC0"}],
        "samplers": [0],
        "constants": [],
        "temps": [],
        "unsupported_opcodes": [],
        "instructions": [{
            "offset": 0,
            "opcode": 66,
            "name": "TEX",
            "token": 0,
            "length": 4,
            "controls": 0,
            "predicated": False,
            "operands": [
                operand("dest", 8, 0, write_mask="xyzw"),
                operand("source", 1, 0, swizzle="xyzw"),
                operand("source", 10, 0, swizzle="xyzw"),
            ],
            "predicate": None,
        }],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {"0": "sampler2D"},
    }


def test_reference_renderer_executes_pixel_shader_reference(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()

    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((10, 120, 220, 255)),
    }
    out = tmp_path / "shader-reference.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        width=24,
        height=24,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (10, 120, 220) in pixels


def test_reference_renderer_rejects_shader_reference_without_pixel_program(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "missing.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "no embedded pixel_program" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_executes_material_constant_tint(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    program = _textured_tex_shader_program()
    program["temps"] = [0]
    program["constants"] = [0]
    tex_dest = program["instructions"][0]["operands"][0]
    tex_dest["reg_type"] = 0
    tex_dest["index"] = 0
    program["instructions"].append({
        "offset": 16,
        "opcode": 5,
        "name": "MUL",
        "token": 0,
        "length": 4,
        "controls": 0,
        "predicated": False,
        "operands": [
            {
                "token": 0x80000000,
                "kind": "dest",
                "reg_type": 8,
                "index": 0,
                "write_mask": "xyzw",
            },
            {
                "token": 0x80000000,
                "kind": "source",
                "reg_type": 0,
                "index": 0,
                "swizzle": "xyzw",
                "source_modifier": 0,
            },
            {
                "token": 0x80000000,
                "kind": "source",
                "reg_type": 2,
                "index": 0,
                "swizzle": "xyzw",
                "source_modifier": 0,
            },
        ],
        "predicate": None,
    })
    command["submeshes"][0]["shader"]["pixel_program"] = program
    command["submeshes"][0]["uniforms"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "tint",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 0,
            "register_count": 1,
            "ctab_type": "float4",
            "value": [0.5, 0.25, 1.0, 1.0],
        }],
        "optimized_out_or_unreflected": [],
    }
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((200, 100, 50, 255)),
    }
    out = tmp_path / "material-tint.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        width=24,
        height=24,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (100, 25, 50) in pixels


def _two_texture_add_shader_program():
    def operand(kind, reg_type, index, *, swizzle="xyzw", write_mask=None):
        return {
            "token": 0x80000000,
            "kind": kind,
            "reg_type": reg_type,
            "index": index,
            "swizzle": swizzle,
            "source_modifier": 0,
            "write_mask": write_mask,
        }

    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "pixel",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [{"usage": "TEXCOORD", "index": 0, "register": "v0"}],
        "outputs": [{"usage": "COLOR", "index": 0, "register": "oC0"}],
        "samplers": [0, 1],
        "constants": [],
        "temps": [0, 1],
        "unsupported_opcodes": [],
        "instructions": [
            {
                "offset": 0,
                "opcode": 66,
                "name": "TEX",
                "token": 0,
                "length": 4,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 0, 0, write_mask="xyzw"),
                    operand("source", 1, 0),
                    operand("source", 10, 0),
                ],
                "predicate": None,
            },
            {
                "offset": 16,
                "opcode": 66,
                "name": "TEX",
                "token": 0,
                "length": 4,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 0, 1, write_mask="xyzw"),
                    operand("source", 1, 0),
                    operand("source", 10, 1),
                ],
                "predicate": None,
            },
            {
                "offset": 32,
                "opcode": 2,
                "name": "ADD",
                "token": 0,
                "length": 4,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 8, 0, write_mask="xyzw"),
                    operand("source", 0, 0),
                    operand("source", 0, 1),
                ],
                "predicate": None,
            },
        ],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {"0": "sampler2D", "1": "sampler2D"},
    }


def test_reference_renderer_executes_multiple_shader_texture_samplers(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _two_texture_add_shader_program()
    command["submeshes"][0]["textures"] = [
        {
            "resource": "material",
            "resource_binding_id": "tb_diffuse",
            "texture_id": "tex_diffuse",
            "sampler_id": "smp_diffuse",
            "d3d9_sampler_register": 0,
            "sampler_state": {
                "format": "SHIFT.SamplerState/1",
                "min_filter": "POINT",
                "mag_filter": "POINT",
                "address_u": "CLAMP_TO_EDGE",
                "address_v": "CLAMP_TO_EDGE",
                "ready": True,
            },
        },
        {
            "resource": "material",
            "resource_binding_id": "tb_specular",
            "texture_id": "tex_specular",
            "sampler_id": "smp_specular",
            "d3d9_sampler_register": 1,
            "sampler_state": {
                "format": "SHIFT.SamplerState/1",
                "min_filter": "POINT",
                "mag_filter": "POINT",
                "address_u": "CLAMP_TO_EDGE",
                "address_v": "CLAMP_TO_EDGE",
                "ready": True,
            },
        },
    ]
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image0 = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((100, 40, 20, 255)),
    }
    image1 = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((30, 10, 5, 255)),
    }
    out = tmp_path / "multi-texture.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image0,
        out,
        shader_reference=True,
        texture_images={0: image0, 1: image1},
        width=24,
        height=24,
        mvp=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (130, 50, 25) in pixels


def test_reference_renderer_rejects_missing_second_texture(tmp_path):
    from reference_renderer import render_textured_render_command
    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _two_texture_add_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "missing-second.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "missing texture images for samplers: s1" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def _uv1_texture_shader_program():
    program = _textured_tex_shader_program()
    program["inputs"] = [
        {"usage": "TEXCOORD", "index": 1, "register": "v1"},
    ]
    program["instructions"][0]["operands"][1]["reg_type"] = 1
    program["instructions"][0]["operands"][1]["index"] = 1
    return program


def test_reference_renderer_maps_texcoord1_to_m132_layer(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _uv1_texture_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {
            "130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)],
            "131": [(1.0, 0.0), (1.0, 0.0), (1.0, 0.0)],
        },
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 2,
        "height": 1,
        "pixels": bytes((255, 0, 0, 255, 0, 255, 0, 255)),
    }
    out = tmp_path / "uv1.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        sampler={
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        },
        width=24,
        height=24,
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (0, 255, 0) in pixels


def test_reference_renderer_rejects_missing_semantic_uv_layer(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _uv1_texture_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "missing-uv1.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "requires TEXCOORD1 but mesh has no matching UV layer" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_uses_render_command_constant_payload(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    program = _textured_tex_shader_program()
    program["temps"] = [0]
    program["constants"] = [0]
    program["instructions"][0]["operands"][0]["reg_type"] = 0
    program["instructions"][0]["operands"][0]["index"] = 0
    program["instructions"].append({
        "offset": 16,
        "opcode": 5,
        "name": "MUL",
        "token": 0,
        "length": 4,
        "controls": 0,
        "predicated": False,
        "operands": [
            {"token": 0x80000000, "kind": "dest", "reg_type": 8, "index": 0, "write_mask": "xyzw"},
            {"token": 0x80000000, "kind": "source", "reg_type": 0, "index": 0, "swizzle": "xyzw", "source_modifier": 0},
            {"token": 0x80000000, "kind": "source", "reg_type": 2, "index": 0, "swizzle": "xyzw", "source_modifier": 0},
        ],
        "predicate": None,
    })
    command["submeshes"][0]["shader"]["pixel_program"] = program
    command["submeshes"][0]["constant_payload"] = {
        "format": "SHIFT.MaterialConstantPayload/1",
        "ready": True,
        "blocking_reasons": [],
        "register_count": 1,
        "registers": [{
            "register_index": 0,
            "values": [0.5, 0.25, 1.0, 1.0],
            "byte_offset": 0,
            "byte_size": 16,
        }],
    }
    mesh = {**_triangle(), "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]}}
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((200, 100, 50, 255)),
    }
    out = tmp_path / "payload-tint.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        width=24,
        height=24,
        mvp=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (100, 25, 50) in pixels


def _normal_dot_shader_program():
    def operand(kind, reg_type, index, *, swizzle="xyzw", write_mask=None):
        return {
            "token": 0x80000000,
            "kind": kind,
            "reg_type": reg_type,
            "index": index,
            "swizzle": swizzle,
            "source_modifier": 0,
            "write_mask": write_mask,
        }

    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "pixel",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [{"usage": "NORMAL", "index": 0, "register": "v1"}],
        "outputs": [{"usage": "COLOR", "index": 0, "register": "oC0"}],
        "samplers": [],
        "constants": [0],
        "temps": [],
        "unsupported_opcodes": [],
        "instructions": [{
            "offset": 0,
            "opcode": 8,
            "name": "DP3",
            "token": 0,
            "length": 4,
            "controls": 0,
            "predicated": False,
            "operands": [
                operand("dest", 8, 0, write_mask="xyzw"),
                operand("source", 1, 1),
                operand("source", 2, 0),
            ],
            "predicate": None,
        }],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {},
    }


def test_reference_renderer_executes_normal_varying(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _normal_dot_shader_program()
    command["submeshes"][0]["uniforms"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "lightDirection",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 0,
            "register_count": 1,
            "ctab_type": "float4",
            "value": [0.0, 0.0, 1.0, 0.0],
        }],
        "optimized_out_or_unreflected": [],
    }
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
        "normals": [(0.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)],
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((5, 6, 7, 255)),
    }
    out = tmp_path / "normal-dot.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        width=24,
        height=24,
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert (255, 255, 255) in pixels


def test_reference_renderer_rejects_missing_normal_varying(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _normal_dot_shader_program()
    command["submeshes"][0]["uniforms"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "lightDirection",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 0,
            "register_count": 1,
            "ctab_type": "float4",
            "value": [0.0, 0.0, 1.0, 0.0],
        }],
        "optimized_out_or_unreflected": [],
    }
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "missing-normal.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "requires NORMAL0 but mesh has no matching attribute" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def _vertex_passthrough_program():
    def operand(kind, reg_type, index, *, swizzle="xyzw", write_mask="xyzw"):
        return {
            "token": 0x80000000,
            "kind": kind,
            "reg_type": reg_type,
            "index": index,
            "swizzle": swizzle,
            "source_modifier": 0,
            "write_mask": write_mask if kind == "dest" else None,
        }

    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "vertex",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [
            {"usage": "POSITION", "index": 0, "register": "v0"},
            {"usage": "TEXCOORD", "index": 0, "register": "v1"},
        ],
        "outputs": [
            {"usage": "POSITION", "index": 0, "register": "oR0"},
            {"usage": "TEXCOORD", "index": 0, "register": "oT1"},
        ],
        "samplers": [],
        "constants": [],
        "temps": [],
        "unsupported_opcodes": [],
        "instructions": [
            {
                "offset": 0,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 4, 0),
                    operand("source", 1, 0),
                ],
                "predicate": None,
            },
            {
                "offset": 12,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 6, 1),
                    operand("source", 1, 1),
                ],
                "predicate": None,
            },
        ],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {},
    }


def test_reference_renderer_executes_vertex_shader_and_links_varyings_by_semantic(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["vertex_program"] = _vertex_passthrough_program()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()

    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((10, 120, 220, 255)),
    }
    out = tmp_path / "vertex-reference.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        width=24,
        height=24,
    )
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    assert result["vertex_shader_executed"] is True
    assert result["world_matrix_applied"] is False
    assert (10, 120, 220) in pixels


def test_reference_renderer_rejects_unmatched_vertex_pixel_semantic(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    vertex = _vertex_passthrough_program()
    vertex["outputs"] = [
        {"usage": "POSITION", "index": 0, "register": "oR0"},
        {"usage": "TEXCOORD", "index": 1, "register": "oT1"},
    ]
    command["submeshes"][0]["shader"]["vertex_program"] = vertex
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()

    mesh = {**_triangle(), "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]}}
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "bad-varying.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "pixel shader semantic has no matching vertex output: TEXCOORD0" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_feeds_known_normal_into_vertex_shader(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    vertex = _vertex_passthrough_program()
    vertex["inputs"].append({"usage": "NORMAL", "index": 0, "register": "v2"})
    command["submeshes"][0]["shader"]["vertex_program"] = vertex
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()

    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]},
        "normals": [(0.0, 0.0, 1.0)] * 3,
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((40, 50, 60, 255)),
    }
    out = tmp_path / "vertex-normal-reference.ppm"
    result = render_textured_render_command(
        command, mesh, image, out, shader_reference=True, width=24, height=24
    )
    assert result["vertex_shader_executed"] is True
    body = out.read_bytes().split(b"\n", 3)[3]
    assert (40, 50, 60) in [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]


def test_reference_renderer_accepts_uvw0_property_230(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {"230": [(1.0, 0.0, 0.5)] * 3},
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 2,
        "height": 1,
        "pixels": bytes((200, 20, 30, 255, 20, 200, 30, 255)),
    }
    out = tmp_path / "uvw0-230.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        sampler={
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        },
        width=24,
        height=24,
    )
    assert result["format"] == "SHIFT.TexturedStaticDrawReference/1"
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert (20, 200, 30) in pixels


def test_reference_renderer_rejects_mixed_130_230_uv_families(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {
            "130": [(0.0, 0.0)] * 3,
            "230": [(1.0, 0.0, 0.0)] * 3,
        },
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "mixed-uv-family.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "TEXCOORD0 has conflicting MEB UV families: 130 and 230" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def _vertex_skin_input_program():
    def operand(kind, reg_type, index, *, write_mask="xyzw"):
        return {
            "token": 0x80000000,
            "kind": kind,
            "reg_type": reg_type,
            "index": index,
            "swizzle": "xyzw",
            "source_modifier": 0,
            "write_mask": write_mask if kind == "dest" else None,
        }

    return {
        "schema": "SHIFT.ShaderProgram/1",
        "stage": "vertex",
        "shader_model": [3, 0],
        "offset": 0,
        "end": 0,
        "inputs": [
            {"usage": "POSITION", "index": 0, "register": "v0"},
            {"usage": "BLENDWEIGHT", "index": 0, "register": "v2"},
            {"usage": "BLENDINDICES", "index": 0, "register": "v3"},
        ],
        "outputs": [
            {"usage": "POSITION", "index": 0, "register": "oR0"},
            {"usage": "TEXCOORD", "index": 0, "register": "oT0"},
        ],
        "samplers": [],
        "constants": [],
        "temps": [],
        "unsupported_opcodes": [],
        "instructions": [
            {
                "offset": 0,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 4, 0),
                    operand("source", 1, 0),
                ],
                "predicate": None,
            },
            {
                "offset": 12,
                "opcode": 1,
                "name": "MOV",
                "token": 0,
                "length": 3,
                "controls": 0,
                "predicated": False,
                "operands": [
                    operand("dest", 6, 0),
                    operand("source", 1, 2),
                ],
                "predicate": None,
            },
        ],
        "const_ints": [],
        "const_bools": [],
        "sampler_types": {},
    }


def test_reference_renderer_executes_vs_with_blend_weight_and_index_inputs(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["vertex_program"] = _vertex_skin_input_program()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0)] * 3},
        "bone_weights": [(1.0, 0.0, 0.0, 1.0)] * 3,
        "bone_indices": [(7, 8, 9, 10)] * 3,
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 2,
        "height": 1,
        "pixels": bytes((25, 35, 45, 255, 225, 235, 245, 255)),
    }
    out = tmp_path / "skin-inputs.ppm"
    result = render_textured_render_command(
        command,
        mesh,
        image,
        out,
        shader_reference=True,
        sampler={
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "address_u": "CLAMP_TO_EDGE",
            "address_v": "CLAMP_TO_EDGE",
        },
        width=24,
        height=24,
    )
    assert result["vertex_shader_executed"] is True
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert (225, 235, 245) in pixels


def test_reference_renderer_rejects_missing_blend_index_input(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["shader"]["vertex_program"] = _vertex_skin_input_program()
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    mesh = {
        **_triangle(),
        "uv_layers": {"130": [(0.0, 0.0)] * 3},
        "bone_weights": [(1.0, 0.0, 0.0, 1.0)] * 3,
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((25, 35, 45, 255)),
    }
    try:
        render_textured_render_command(
            command,
            mesh,
            image,
            tmp_path / "missing-blend-index.ppm",
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "requires BLENDINDICES0 but mesh has no matching attribute" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_executes_external_sampler2d_without_material_fallback(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["textures"] = []
    command["submeshes"][0]["external_samplers"] = [{
        "sampler": "sShadowMap_f1_0",
        "sampler_type": "sampler2D",
        "d3d9_sampler_register": 0,
        "binding": "external-or-specialised",
    }]
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    external = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((80, 90, 100, 255)),
    }
    out = tmp_path / "external-shadow.ppm"
    result = render_textured_render_command(
        command,
        {**_triangle(), "uv_layers": {"130": [(0.0, 0.0)] * 3}},
        external,
        out,
        shader_reference=True,
        external_texture_images={0: external},
        width=24,
        height=24,
    )
    assert result["external_sampler_requirements"] == [{
        "sampler": "sShadowMap_f1_0",
        "d3d9_sampler_register": 0,
        "sampler_type": "sampler2D",
    }]
    body = out.read_bytes().split(b"\n", 3)[3]
    pixels = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
    assert (80, 90, 100) in pixels


def test_reference_renderer_does_not_use_legacy_image_for_external_sampler(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["textures"] = []
    command["submeshes"][0]["external_samplers"] = [{
        "sampler": "sShadowMap_f1_0",
        "sampler_type": "sampler2D",
        "d3d9_sampler_register": 0,
        "binding": "external-or-specialised",
    }]
    command["submeshes"][0]["shader"]["pixel_program"] = _textured_tex_shader_program()
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((10, 20, 30, 255)),
    }
    out = tmp_path / "missing-external.ppm"
    try:
        render_textured_render_command(
            command,
            {**_triangle(), "uv_layers": {"130": [(0.0, 0.0)] * 3}},
            image,
            out,
            shader_reference=True,
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "missing texture images for samplers: s0" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reference_renderer_rejects_external_cube_sampler(tmp_path):
    from reference_renderer import render_textured_render_command

    command = _render_command_ready()
    command["submeshes"][0]["textures"] = []
    command["submeshes"][0]["external_samplers"] = [{
        "sampler": "environmentMap",
        "sampler_type": "samplerCube",
        "d3d9_sampler_register": 3,
        "binding": "external-or-specialised",
    }]
    program = _textured_tex_shader_program()
    program["samplers"] = [3]
    program["sampler_types"] = {"3": "samplerCube"}
    program["instructions"][0]["operands"][2]["index"] = 3
    command["submeshes"][0]["shader"]["pixel_program"] = program
    cube_image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((1, 2, 3, 255)),
    }
    try:
        render_textured_render_command(
            command,
            {**_triangle(), "uv_layers": {"130": [(0.0, 0.0)] * 3}},
            cube_image,
            tmp_path / "cube.ppm",
            shader_reference=True,
            external_texture_images={3: cube_image},
            width=8,
            height=8,
        )
    except ValueError as exc:
        assert "external sampler s3 (samplerCube) requires a dedicated reference resource implementation" in str(exc)
    else:
        raise AssertionError("expected ValueError")
