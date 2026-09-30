import json
from pathlib import Path

import pytest

from imx_neutral_geometry import (
    FORMAT,
    build_imx_neutral_geometry,
    build_imx_neutral_geometry_file,
)


def _xml(*, stream_type="F32Vec3", stream_usage="Position"):
    return f"""<?xml version="1.0"?>
<MESH Vertices="3" Streams="4" Buffers="1" EnvMapType="EDEMT_INSIDE">
  <BOUNDSPHERE Centre="0 0 0" Radius="2"/>
  <AABBOX Min="-1 -1 -1" Max="1 1 1"/>
  <STREAM Type="{stream_type}" Usage="{stream_usage}" Channel="0">
    <ITEM {"Pos" if stream_usage == "Position" else stream_usage}="0 0 0"/>
    <ITEM {"Pos" if stream_usage == "Position" else stream_usage}="1 0 0"/>
    <ITEM {"Pos" if stream_usage == "Position" else stream_usage}="0 1 0"/>
  </STREAM>
  <STREAM Type="F32Vec3" Usage="Normal" Channel="0">
    <ITEM Normal="0 0 1"/>
    <ITEM Normal="0 0 1"/>
    <ITEM Normal="0 0 1"/>
  </STREAM>
  <STREAM Type="F32Vec2" Usage="TexCoord" Channel="0">
    <ITEM UV="0 0"/>
    <ITEM UV="1 0"/>
    <ITEM UV="0 1"/>
  </STREAM>
  <STREAM Type="RGBA32" Usage="Colour" Channel="0">
    <ITEM Colour="0xff112233"/>
    <ITEM Colour="0xff445566"/>
    <ITEM Colour="0xff778899"/>
  </STREAM>
  <INDEXBUFFER Material="tracks/test/object.bmt" Entries="1">
    <TRIANGLE Indices="0 1 2"/>
  </INDEXBUFFER>
</MESH>
""".encode("utf-8")


def test_imx_adapter_materializes_proven_neutral_geometry():
    report = build_imx_neutral_geometry(_xml())

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["decoded_properties"] == ["200", "220", "130", "460"]
    assert report["deferred_stream_count"] == 0

    mesh = report["mesh"]
    assert mesh["format"] == "SHIFT.NeutralMesh/1"
    assert mesh["source_format"] == "SHIFT.IMXXMLMesh/1"
    assert mesh["vertex_count"] == 3
    assert mesh["triangle_count"] == 1
    assert mesh["vertices"] == [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]
    assert mesh["normals"] == [[0.0, 0.0, 1.0]] * 3
    assert mesh["uv_layers"]["130"] == [
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    # RGBA32 is preserved in little-endian runtime memory order.
    assert mesh["colors"][0] == [0x33, 0x22, 0x11, 0xFF]
    assert mesh["indices"] == [0, 1, 2]
    assert mesh["environment_map_type"] == {
        "source": "EDEMT_INSIDE",
        "runtime_value": 2,
    }

    primitive = mesh["primitives"][0]
    assert primitive["material"] == "tracks/test/object.bmt"
    assert primitive["primitive_type"] == 4
    assert primitive["triangle_count"] == 1
    assert primitive["first_index"] == 0
    assert primitive["index_count"] == 3
    assert primitive["vertex_range_u16"] == [0, 2]
    assert primitive["vertex_range_source"] == (
        "derived-from-XML-triangle-indices"
    )


def test_xml_runtime_usage_codes_do_not_replace_neutral_property_ids():
    report = build_imx_neutral_geometry(_xml())
    attrs = {
        row.get("property_id"): row
        for row in report["mesh"]["vertex_layout"]["attributes"]
    }

    assert attrs["200"]["runtime_usage_ordinal"] == 0
    assert attrs["220"]["runtime_usage_ordinal"] == 3
    assert attrs["130"]["runtime_usage_ordinal"] == 5
    assert attrs["460"]["runtime_usage_ordinal"] == 10

    assert attrs["220"]["source_usage"] == "Normal"
    assert attrs["130"]["source_usage"] == "TexCoord"
    assert report["boundary"]["runtime_usage_values_are_d3ddeclusage"] is True


def test_bones_expand_source_12_float_affine_matrix():
    xml = b"""<MESH Vertices="1" Streams="1" Buffers="1">
      <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
      <AABBOX Min="0 0 0" Max="0 0 0"/>
      <BONES NumBones="1">
        <NODE Name="root" Transform="1 0 0 0 1 0 0 0 1 4 5 6"/>
      </BONES>
      <STREAM Type="F32Vec3" Usage="Position" Channel="0">
        <ITEM Pos="0 0 0"/>
      </STREAM>
      <INDEXBUFFER Material="tracks/test/skinned.bmt" Entries="1"
                   NumBones="1" BoneIndices="0">
        <TRIANGLE Indices="0 0 0"/>
      </INDEXBUFFER>
    </MESH>"""
    report = build_imx_neutral_geometry(xml)

    assert report["ready"] is True
    bones = report["mesh"]["bones"]
    assert bones["count"] == 1
    assert bones["names"] == ["root"]
    assert bones["matrices"][0]["runtime_matrix_4x4"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        4.0, 5.0, 6.0, 1.0,
    ]
    assert report["mesh"]["primitives"][0]["bone_palette_u16"] == [0]


def test_unproven_xml_value_type_is_preserved_raw_and_blocks():
    xml = b"""<MESH Vertices="1" Streams="2" Buffers="1">
      <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
      <AABBOX Min="0 0 0" Max="0 0 0"/>
      <STREAM Type="F32Vec3" Usage="Position" Channel="0">
        <ITEM Pos="0 0 0"/>
      </STREAM>
      <STREAM Type="F16Vec2" Usage="TexCoord" Channel="0">
        <ITEM UV="0 0"/>
      </STREAM>
      <INDEXBUFFER Material="tracks/test/object.bmt" Entries="1">
        <TRIANGLE Indices="0 0 0"/>
      </INDEXBUFFER>
    </MESH>"""
    report = build_imx_neutral_geometry(xml)

    assert report["ready"] is False
    assert (
        "stream-1:xml-value-decoder-unproven:F16Vec2"
        in report["blocking_reasons"]
    )
    assert report["deferred_stream_count"] == 1
    deferred = report["deferred_streams"][0]
    assert deferred["source_type"] == "F16Vec2"
    assert deferred["runtime_type_ordinal"] == 15
    assert deferred["raw_values"] == ["0 0"]


def test_source_decoded_but_neutral_unmapped_semantic_blocks():
    xml = b"""<MESH Vertices="1" Streams="2" Buffers="1">
      <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
      <AABBOX Min="0 0 0" Max="0 0 0"/>
      <STREAM Type="F32Vec3" Usage="Position" Channel="0">
        <ITEM Pos="0 0 0"/>
      </STREAM>
      <STREAM Type="F32" Usage="Depth" Channel="0">
        <ITEM Depth="1"/>
      </STREAM>
      <INDEXBUFFER Material="tracks/test/object.bmt" Entries="1">
        <TRIANGLE Indices="0 0 0"/>
      </INDEXBUFFER>
    </MESH>"""
    report = build_imx_neutral_geometry(xml)

    assert report["ready"] is False
    assert (
        "stream-1:neutral-semantic-unmapped:F32/Depth/0"
        in report["blocking_reasons"]
    )
    assert report["deferred_streams"][0]["runtime_usage_ordinal"] == 12


@pytest.mark.parametrize(
    "xml, message",
    [
        (
            b"""<MESH Vertices="1" Streams="2" Buffers="0">
              <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
              <AABBOX Min="0 0 0" Max="0 0 0"/>
              <STREAM Type="F32Vec3" Usage="Position"><ITEM Pos="0 0 0"/></STREAM>
            </MESH>""",
            "Streams attribute",
        ),
        (
            b"""<MESH Vertices="2" Streams="1" Buffers="0">
              <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
              <AABBOX Min="0 0 0" Max="0 0 0"/>
              <STREAM Type="F32Vec3" Usage="Position"><ITEM Pos="0 0 0"/></STREAM>
            </MESH>""",
            "ITEM count",
        ),
        (
            b"""<MESH Vertices="1" Streams="1" Buffers="1">
              <BOUNDSPHERE Centre="0 0 0" Radius="1"/>
              <AABBOX Min="0 0 0" Max="0 0 0"/>
              <STREAM Type="F32Vec3" Usage="Position"><ITEM Pos="0 0 0"/></STREAM>
              <INDEXBUFFER Material="m.bmt" Entries="1">
                <TRIANGLE Indices="0 1 0"/>
              </INDEXBUFFER>
            </MESH>""",
            "exceeds vertex count",
        ),
    ],
)
def test_malformed_imx_fails_closed(xml, message):
    with pytest.raises(ValueError, match=message):
        build_imx_neutral_geometry(xml)


def test_file_adapter_writes_stable_json(tmp_path):
    source = tmp_path / "mesh.imx"
    output = tmp_path / "mesh-neutral.json"
    source.write_bytes(_xml())

    report = build_imx_neutral_geometry_file(source, output)

    assert report["ready"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["format"] == FORMAT
    assert written["mesh"]["indices"] == [0, 1, 2]
    assert written["primitives"][0]["material"] == "tracks/test/object.bmt"


def test_frozen_source_evidence_keeps_retail_enum_tables():
    evidence = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "evidence"
            / "imx_xml_mesh_loader_source.json"
        ).read_text(encoding="utf-8")
    )

    assert evidence["function"] == "FUN_008587e0"
    assert evidence["root"] == "MESH"
    assert len(evidence["type_table"]) == 17
    assert len(evidence["usage_table"]) == 9
    usages = {
        row["name"]: row["runtime_usage"]
        for row in evidence["usage_table"]
    }
    assert usages == {
        "Position": 0,
        "BlendWeights": 1,
        "Normal": 3,
        "TexCoord": 5,
        "Tangent": 6,
        "Binormal": 7,
        "Colour": 10,
        "Depth": 12,
        "BlendIndices": 2,
    }
