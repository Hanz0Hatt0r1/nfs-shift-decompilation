import hashlib
import json
import struct
from pathlib import Path

from vulkan_dds_bridge import FORMAT_BRIDGE, bridge_bmw_dds_resources


def _dds_header(width=4, height=4, *, fourcc=b"", caps2=0):
    pf_flags = 0x4 if fourcc else 0x40
    pf_fourcc = struct.unpack("<I", fourcc.ljust(4, b"\0"))[0]
    values = (
        124, 0, height, width, 0, 0, 1,
        *([0] * 11),
        32, pf_flags, pf_fourcc, 0,
        0, 0, 0, 0,
        caps2, 0, 0, 0, 0,
    )
    header = struct.pack("<31I", *values)
    assert len(header) == 124
    return b"DDS " + header


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "textures": [{
                "sampler": "diffuseMap",
                "d3d9_sampler_register": 1,
                "resource_binding_id": 10,
                "texture_id": 20,
                "sampler_id": 30,
                "sampler_state": {
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "address_u": "REPEAT",
                    "address_v": "REPEAT",
                },
            }],
            "external_samplers": [{
                "sampler": "environmentMap",
                "sampler_type": "samplerCube",
                "d3d9_sampler_register": 3,
                "sampler_state": {
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "address_u": "CLAMP_TO_EDGE",
                    "address_v": "CLAMP_TO_EDGE",
                    "address_w": "CLAMP_TO_EDGE",
                },
            }],
        }],
    }


def _dxt1():
    return struct.pack("<HHI", 0xF800, 0x07E0, 0)


def _write_dds(path: Path):
    path.write_bytes(_dds_header(fourcc=b"DXT1") + _dxt1())


def _write_cube(path: Path):
    flags = 0x400 | 0x800 | 0x1000 | 0x2000 | 0x4000 | 0x8000
    payload = b"".join(_dxt1() for _ in range(6))
    path.write_bytes(_dds_header(fourcc=b"DXT1", caps2=0x200 | flags) + payload)


def test_dds_bridge_emits_vulkan_packets_and_provenance(tmp_path):
    dds = tmp_path / "diffuse.dds"
    cube = tmp_path / "environment.dds"
    _write_dds(dds)
    _write_cube(cube)

    output = tmp_path / "out"
    result = bridge_bmw_dds_resources(
        _command(),
        {"1": str(dds)},
        output,
        environment_cube_dds=cube,
    )

    assert result["format"] == FORMAT_BRIDGE
    assert result["ready"] is True, result
    assert result["packets"]["textures"]["path"] == "textures.svtp"
    assert result["packets"]["environment_cube"]["path"] == "environment_cube.svcp"
    assert result["provenance"]["path"] == "dds_sources.json"

    sources = result["decoded_sources"]
    assert [row["register"] for row in sources] == [1, 3]
    assert sources[0]["source_sha256"] == hashlib.sha256(dds.read_bytes()).hexdigest()
    assert sources[1]["source_sha256"] == hashlib.sha256(cube.read_bytes()).hexdigest()

    manifest = json.loads((output / "dds_bridge_manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == FORMAT_BRIDGE
    assert (output / "textures.svtp").is_file()
    assert (output / "environment_cube.svcp").is_file()


def test_dds_bridge_rejects_cubemap_on_2d_register(tmp_path):
    cube = tmp_path / "bad.dds"
    _write_cube(cube)

    result = bridge_bmw_dds_resources(
        _command(),
        {"1": str(cube)},
        tmp_path / "out",
        environment_cube_dds=None,
    )
    assert result["ready"] is False
    assert "dds-bridge:cubemap-supplied-to-2d-register:s1" in result["blocking_reasons"]


def test_dds_bridge_requires_all_material_2d_registers(tmp_path):
    dds = tmp_path / "diffuse.dds"
    _write_dds(dds)
    command = _command()
    command["submeshes"][0]["textures"].append({
        "sampler": "normalMap",
        "d3d9_sampler_register": 2,
        "sampler_state": {
            "min_filter": "NEAREST",
            "mag_filter": "NEAREST",
            "address_u": "REPEAT",
            "address_v": "REPEAT",
        },
    })

    result = bridge_bmw_dds_resources(
        command,
        {"1": str(dds)},
        tmp_path / "out",
    )
    assert result["ready"] is False
    assert "dds-bridge:missing-2d-ds:s2" in result["blocking_reasons"]


def test_dds_bridge_reports_decode_failures_instead_of_raising(tmp_path):
    bad = tmp_path / "bad.dds"
    bad.write_bytes(b"not-dds")
    result = bridge_bmw_dds_resources(
        _command(),
        {"1": str(bad)},
        tmp_path / "out",
        environment_cube_dds=None,
    )
    assert result["ready"] is False
    assert any(reason.startswith("dds-bridge:decode-failed:s1:") for reason in result["blocking_reasons"])


def test_dds_bridge_does_not_double_report_incompatible_2d_resource_as_missing(tmp_path):
    cube = tmp_path / "bad-kind.dds"
    _write_cube(cube)
    result = bridge_bmw_dds_resources(
        _command(),
        {"1": str(cube)},
        tmp_path / "out",
        environment_cube_dds=None,
    )
    assert result["ready"] is False
    assert "dds-bridge:cubemap-supplied-to-2d-register:s1" in result["blocking_reasons"]
    assert "dds-bridge:missing-2d-ds:s1" not in result["blocking_reasons"]
