import json

import pytest

from imx_neutral_geometry import (
    FORMAT,
    build_imx_neutral_geometry,
    build_imx_neutral_geometry_file,
)


def _fixture(*, streams=4, entries=1, type_name="F32Vec3"):
    return f"""<?xml version="1.0"?>
<MESH Vertices="3" Streams="{streams}" Buffers="1" EnvMapType="EDEMT_OUTSIDE">
  <BOUNDSPHERE Centre="0 0 0" Radius="2"/>
  <AABBOX Min="-1 -1 -1" Max="1 1 1"/>
  <BONES NumBones="1">
    <NODE Name="root" Transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
  </BONES>
  <STREAM Type="{type_name}" Usage="Position" Channel="0">
    <ITEM Pos="0 0 0"/>
    <ITEM Pos="1 0 0"/>
    <ITEM Pos="0 1 0"/>
  </STREAM>
  <STREAM Type="F32Vec2" Usage="TexCoord" Channel="0">
    <ITEM UV="0 0"/>
    <ITEM UV="1 0"/>
    <ITEM UV="0 1"/>
  </STREAM>
  <STREAM Type="RGBA32" Usage="Colour" Channel="0">
    <ITEM Colour="0xff0000ff"/>
    <ITEM Colour="0xff00ff00"/>
    <ITEM Colour="0xffff0000"/>
  </STREAM>
  <STREAM Type="U8Vec4" Usage="BlendIndices" Channel="0">
    <ITEM Indices="0 1 2 3"/>
    <ITEM Indices="4 5 6 7"/>
    <ITEM Indices="8 9 10 11"/>
  </STREAM>
  <INDEXBUFFER Type="TRIANGLE" Material="tracks/test/object.bmt"
               Entries="{entries}" NumBones="1" BoneIndices="0">
    <TRIANGLE Indices="0 1 2"/>
  </INDEXBUFFER>
</MESH>
"""


def test_imx_adapter_materializes_source_backed_neutral_geometry():
    report = build_imx_neutral_geometry(_fixture())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["decoded_properties"] == ["200", "130", "460", "580"]
    assert report["deferred_stream_count"] == 0

    mesh = report["mesh"]
    assert mesh["format"] == "SHIFT.NeutralMesh/1"
    assert mesh["source_format"] == "SHIFT.IMXXMLMesh/1"
    assert mesh["vertex_count"] == 3
    assert mesh["triangle_count"] == 1
    assert mesh["vertex_properties"] == ["200", "130", "460", "580"]
    assert mesh["vertices"] == [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    assert mesh["uv_layers"]["130"] == [
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    assert mesh["colors"] == [
        [255, 0, 0, 255],
        [0, 255, 0, 255],
        [0, 0, 255, 255],
    ]
    assert mesh["bone_indices"] == [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9, 10, 11],
    ]
    assert mesh["indices"] == [0, 1, 2]
    assert mesh["vertex_layout"]["runtime_interleaved_stride"] == 28

    primitive = mesh["primitives"][0]
    assert primitive["material"] == "tracks/test/object.bmt"
    assert primitive["primitive_type"] == 4
    assert primitive["first_index"] == 0
    assert primitive["index_count"] == 3
    assert primitive["triangle_count"] == 1
    assert primitive["vertex_range_u16"] == [0, 2]
    assert primitive["bone_palette_u16"] == [0]

    assert mesh["bones"]["count"] == 1
    assert mesh["bones"]["records"][0]["name"] == "root"
    assert mesh["bones"]["records"][0]["matrix"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    assert mesh["environment_map_type"] == {
        "source": "EDEMT_OUTSIDE",
        "runtime_value": 1,
    }


def test_imx_adapter_preserves_unmapped_source_stream():
    xml = _fixture().replace(
        '<STREAM Type="U8Vec4" Usage="BlendIndices" Channel="0">',
        '<STREAM Type="F32" Usage="Depth" Channel="0">',
    ).replace(
        '<ITEM Indices="0 1 2 3"/>',
        '<ITEM Depth="0.25"/>',
    ).replace(
        '<ITEM Indices="4 5 6 7"/>',
        '<ITEM Depth="0.50"/>',
    ).replace(
        '<ITEM Indices="8 9 10 11"/>',
        '<ITEM Depth="0.75"/>',
    )
    report = build_imx_neutral_geometry(xml)

    assert report["ready"] is True
    assert report["deferred_stream_count"] == 1
    row = report["deferred_streams"][0]
    assert row["property_id"] == "070"
    assert row["type_name"] == "F32"
    assert row["usage_name"] == "Depth"
    assert row["values"] == [[0.25], [0.5], [0.75]]
    assert report["boundary"]["unknown_stream_policy"] == (
        "preserve-decoded-values-and-defer"
    )


def test_imx_adapter_rejects_xml_type_without_recovered_item_conversion():
    with pytest.raises(ValueError, match="no recovered FUN_008587e0 XML ITEM"):
        build_imx_neutral_geometry(_fixture(type_name="F16Vec2"))


def test_imx_adapter_rejects_stream_count_mismatch():
    with pytest.raises(ValueError, match="Streams=5"):
        build_imx_neutral_geometry(_fixture(streams=5))


def test_imx_adapter_rejects_triangle_entry_count_mismatch():
    with pytest.raises(ValueError, match="Entries=2"):
        build_imx_neutral_geometry(_fixture(entries=2))


def test_imx_file_adapter_writes_stable_json(tmp_path):
    source = tmp_path / "mesh.imx"
    output = tmp_path / "mesh-neutral.json"
    source.write_text(_fixture(), encoding="utf-8")

    report = build_imx_neutral_geometry_file(source, output)

    assert report["ready"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["format"] == FORMAT
    assert written["mesh"]["indices"] == [0, 1, 2]
    assert written["primitives"][0]["material"] == "tracks/test/object.bmt"
