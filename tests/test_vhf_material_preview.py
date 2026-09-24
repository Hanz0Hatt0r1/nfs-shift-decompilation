from types import SimpleNamespace

from vhf_material_preview import _render


def _mesh():
    return SimpleNamespace(
        vertices=[
            (-0.8, -0.7, 0.0),
            (0.8, -0.7, 0.0),
            (0.0, 0.8, 0.0),
        ],
        normals=[
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
        ],
        uv_layers={
            "130": [
                (0.0, 0.0),
                (1.0, 0.0),
                (0.5, 1.0),
            ]
        },
        indices=[0, 1, 2],
        primitives=[
            SimpleNamespace(
                material="vehicles/bmw_m3_e36/bmw_m3_e36_paint.mtx",
                first_index=0,
                index_count=3,
            )
        ],
        vertex_count=3,
        triangle_count=1,
    )


def test_material_preview_paints_only_matching_material():
    mesh = _mesh()
    scene = {
        "parts": [
            {
                "name": "BODY",
                "world_matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "mesh": mesh,
            }
        ]
    }
    image = {
        "format": "SHIFT.ReferenceTexture/1",
        "source_format": "RGBA32",
        "width": 1,
        "height": 1,
        "pixels": bytes((220, 40, 20, 255)),
    }

    ppm, painted_triangles = _render(
        scene,
        paint_material="vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
        texture_image=image,
        width=64,
        height=64,
        yaw_deg=0,
        pitch_deg=0,
    )

    assert painted_triangles == 1
    assert ppm.startswith(b"P6\n64 64\n255\n")
    assert bytes((12, 12, 12)) in ppm
    payload = ppm.split(b"255\\n", 1)[1]\n    colored = [payload[i:i + 3] for i in range(0, len(payload), 3) if payload[i:i + 3] != bytes((12, 12, 12))]\n    assert colored\n    assert any(pixel[0] > pixel[1] * 2 and pixel[0] > pixel[2] for pixel in colored)\n