from bmw_runtime_texture_resource_parity import (
    build_report,
    latest_create_before,
    parse_resource_create_log,
    validate_report,
)


def _witness():
    def draw(call, ptr1, ptr2, ptr4):
        return {
            "draw": {"call": call},
            "match": {
                "material": "BMW_M3_E36_PAINT",
                "sampler_bindings": [
                    {"kind": "material", "parameter": "diffuseTexture", "register": 1, "texture_ptr": ptr1},
                    {"kind": "material", "parameter": "specularTexture", "register": 2, "texture_ptr": ptr2},
                    {"kind": "material", "parameter": "scratchControlTexture", "register": 4, "texture_ptr": ptr4},
                ],
            },
        }
    return {
        "draws": [
            draw(100, "0x100", "0x200", "0x300"),
            draw(200, "0x100", "0x200", "0x300"),
            draw(300, "0x100", "0x200", "0x300"),
            draw(400, "0x100", "0x200", "0x300"),
        ]
    }


def test_parse_resource_create_log_reads_2d_and_cube_objects():
    rows = parse_resource_create_log(
        "10 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 8, Height = 8, Levels = 4, Usage = 0x0, Format = D3DFMT_DXT5, Pool = D3DPOOL_MANAGED, ppTexture = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "20 IDirect3DDevice9::CreateCubeTexture(this = 0x1, EdgeLength = 256, Levels = 9, Usage = D3DUSAGE_RENDERTARGET, Format = D3DFMT_A16B16G16R16F, Pool = D3DPOOL_DEFAULT, ppCubeTexture = &0x200, pSharedHandle = NULL) = D3D_OK\n"
    )
    assert rows[0]["resource_type"] == "texture2d"
    assert rows[0]["width"] == 8
    assert rows[0]["format"] == "D3DFMT_DXT5"
    assert rows[1]["resource_type"] == "cube_texture"
    assert rows[1]["width"] == 256
    assert rows[1]["format"] == "D3DFMT_A16B16G16R16F"


def test_latest_create_before_draw_ignores_future_reuse():
    rows = parse_resource_create_log(
        "10 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 64, Height = 32, Levels = 7, Usage = 0x0, Format = D3DFMT_DXT5, Pool = D3DPOOL_MANAGED, ppTexture = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "20 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 1024, Height = 1024, Levels = 11, Usage = 0x0, Format = D3DFMT_DXT1, Pool = D3DPOOL_MANAGED, ppTexture = &0x100, pSharedHandle = NULL) = D3D_OK\n"
    )
    selected = latest_create_before(rows, "0x100", 30)
    assert selected["call"] == 20
    assert selected["width"] == 1024
    assert latest_create_before(rows, "0x100", 15)["call"] == 10


def test_build_report_classifies_direct_vs_generated(monkeypatch):
    expected = {
        "diffuseTexture": {
            "parameter": "diffuseTexture", "register": 1, "path": "vehicles/textures/common_paint.dds",
            "archive": "BMW_M3_E36.bff", "entry_index": 857, "source_sha256": "a"*64, "source_size": 184,
            "width": 8, "height": 8, "mipmaps": 4, "fourcc": "DXT1",
        },
        "specularTexture": {
            "parameter": "specularTexture", "register": 2, "path": "vehicles/textures/common_paint_specular.dds",
            "archive": "BMW_M3_E36.bff", "entry_index": 856, "source_sha256": "b"*64, "source_size": 240,
            "width": 8, "height": 8, "mipmaps": 4, "fourcc": "DXT5",
        },
        "scratchControlTexture": {
            "parameter": "scratchControlTexture", "register": 4, "path": "vehicles/textures/common_blank.dds",
            "archive": "BMW_M3_E36.bff", "entry_index": 848, "source_sha256": "c"*64, "source_size": 152,
            "width": 4, "height": 4, "mipmaps": 3, "fourcc": "DXT1",
        },
    }
    monkeypatch.setattr(
        "bmw_runtime_texture_resource_parity._static_dds",
        lambda _archive, path: expected[next(k for k, v in expected.items() if v["path"] == path)],
    )
    log = (
        "100 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 1024, Height = 1024, Levels = 11, Usage = 0x0, Format = D3DFMT_DXT1, Pool = D3DPOOL_MANAGED, ppTexture = &0x100, pSharedHandle = NULL) = D3D_OK\n"
        "110 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 8, Height = 8, Levels = 4, Usage = 0x0, Format = D3DFMT_DXT5, Pool = D3DPOOL_MANAGED, ppTexture = &0x200, pSharedHandle = NULL) = D3D_OK\n"
        "120 IDirect3DDevice9::CreateTexture(this = 0x1, Width = 4, Height = 4, Levels = 3, Usage = 0x0, Format = D3DFMT_DXT1, Pool = D3DPOOL_MANAGED, ppTexture = &0x300, pSharedHandle = NULL) = D3D_OK\n"
    )
    report = build_report(_witness(), log, "BMW_M3_E36.bff")
    assert report["draw_binding_count"] == 12
    assert report["summary"]["direct_dds_compatible_count"] == 8
    assert report["summary"]["generated_or_transformed_candidate_count"] == 4
    assert report["rows"][0]["classification"] == "generated-or-transformed-candidate"
    assert report["rows"][1]["classification"] == "direct-dds-compatible"
    assert report["rows"][2]["classification"] == "direct-dds-compatible"


def test_validate_report_requires_all_three_material_parameters():
    report = {
        "format": "SHIFT.BMWM3RuntimeTextureResourceParity/1",
        "material": "BMW_M3_E36_PAINT",
        "draw_binding_count": 12,
        "rows": [
            {"parameter": "diffuseTexture"},
            {"parameter": "specularTexture"},
        ],
    }
    reasons = validate_report(report)
    assert "material-parameters:incomplete" in reasons
