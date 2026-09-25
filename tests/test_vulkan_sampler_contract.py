import json

from vulkan_sampler_contract import build_sampler_contract_report, write_sampler_contract_report, write_sampler_metadata


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "textures": [{
                "sampler": "diffuseMap",
                "material_parameter": "diffuseTexture",
                "d3d9_sampler_register": 1,
                "sampler_state": {
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "mip_filter": "LINEAR",
                    "address_u": "REPEAT",
                    "address_v": "REPEAT",
                    "max_anisotropy": 4,
                    "lod_bias": 0,
                    "srgb": True,
                },
            }],
            "external_samplers": [{
                "sampler": "environmentMap",
                "d3d9_sampler_register": 3,
                "sampler_type": "samplerCube",
                "sampler_state": {
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "mip_filter": "LINEAR",
                    "address_u": "CLAMP",
                    "address_v": "CLAMP",
                    "address_w": "CLAMP",
                },
            }, {
                "sampler": "sShadowMap_f1_0",
                "d3d9_sampler_register": 0,
                "sampler_type": "sampler2D",
            }],
        }],
    }


def test_sampler_contract_preserves_full_d3d9_state():
    result = build_sampler_contract_report(_command())
    assert result["ready"] is True
    texture = result["textures"][0]["contract"]
    assert texture["min_filter_gl"] == "LINEAR_MIPMAP_LINEAR"
    assert texture["address_u"] == "REPEAT"
    assert texture["max_anisotropy"] == 4
    assert texture["lod_bias"] == 0
    assert texture["color_space"] == "sRGB"
    cube = result["external_samplers"][0]["contract"]
    assert cube["address_w"] == "CLAMP_TO_EDGE"
    assert cube["min_filter_gl"] == "LINEAR_MIPMAP_LINEAR"


def test_sampler_contract_keeps_uncaptured_external_shadow_explicit():
    result = build_sampler_contract_report(_command())
    shadow = result["external_samplers"][1]
    assert shadow["register"] == 0
    assert shadow["contract"]["status"] == "not-supplied"
    assert shadow["contract"]["ready"] is True


def test_sampler_metadata_binds_sidecar_to_exact_packet(tmp_path):
    packet = tmp_path / "textures.svtp"
    packet.write_bytes(b"packet")
    report = build_sampler_contract_report(_command())
    sampler_report = write_sampler_contract_report(report, tmp_path / "samplers.json")
    metadata = write_sampler_metadata(sampler_report, packet, tmp_path / "samplers.meta.json")
    assert metadata["packet"]["sha256"]
    loaded = json.loads((tmp_path / "samplers.meta.json").read_text(encoding="utf-8"))
    assert loaded["packet"]["path"] == "textures.svtp"
    assert loaded["sampler_contract"]["format"] == "SHIFT.VulkanSamplerContract/1"
