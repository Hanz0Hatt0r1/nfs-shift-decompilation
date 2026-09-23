from renderer_resources import build_resource_index


def _row(path="textures/body.dds", sha="a" * 64, fourcc="DXT1"):
    return {
        "path": path,
        "sha256": sha,
        "analysis": {
            "format": "DDS",
            "width": 64,
            "height": 64,
            "mipmaps": 6,
            "fourcc": fourcc,
            "rgb_bits": 0,
            "byte_size": 4096,
        },
    }


def _binding(param, minf="LINEAR"):
    return {
        "material_parameter": param,
        "ref": "textures/body.dds",
        "d3d9_sampler_register": 1,
        "binding_source": "fxo-ctab",
        "min_filter": minf,
        "mag_filter": "LINEAR",
        "mip_filter": "LINEAR",
        "address_u": "WRAP",
        "address_v": "WRAP",
        "srgb": True,
        "linear": False,
    }


def test_resource_index_deduplicates_same_texture_blob():
    r = build_resource_index(
        [_row()],
        [_binding("Diffuse"), _binding("Specular", minf="POINT")],
        extensions=["EXT_texture_compression_s3tc"],
    )
    assert r["stats"]["textures"] == 1
    assert r["stats"]["samplers"] == 2
    assert r["stats"]["bindings"] == 2
    assert r["textures"][0]["id"].startswith("tex_a")
    assert all(x["gpu_ready"] for x in r["bindings"])


def test_resource_index_separates_sampler_state_from_texture_identity():
    r = build_resource_index(
        [_row()],
        [_binding("A", minf="LINEAR"), _binding("B", minf="POINT")],
        extensions=["EXT_texture_compression_s3tc"],
    )
    assert r["bindings"][0]["texture_id"] == r["bindings"][1]["texture_id"]
    assert r["bindings"][0]["sampler_id"] != r["bindings"][1]["sampler_id"]


def test_resource_index_requires_runtime_compression_extension():
    r = build_resource_index(
        [_row()],
        [_binding("Diffuse")],
        extensions=[],
    )
    assert r["stats"]["gpu_ready_textures"] == 0
    assert "runtime-extension-missing:EXT_texture_compression_s3tc" in r["textures"][0]["blocking_reasons"]
    assert r["bindings"][0]["gpu_ready"] is False


def test_resource_index_reports_missing_binding_resource():
    r = build_resource_index(
        [_row()],
        [_binding("Diffuse") | {"ref": "textures/missing.dds"}],
        extensions=["EXT_texture_compression_s3tc"],
    )
    assert r["stats"]["unresolved"] == 1
    assert r["unresolved"][0]["kind"] == "texture-resource-missing"
