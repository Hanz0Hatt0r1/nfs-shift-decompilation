import pytest

from sgb_meshinst_runtime import (
    FORMAT,
    build_meshinst_runtime_contract,
)


def test_imb_uses_binary_loader_and_source_backed_runtime_layout():
    report = build_meshinst_runtime_contract(
        "tracks/test/crowd_banner.imb",
        descriptor_instance_count=3,
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["factory"]["type"] == 7
    assert report["factory"]["name"] == "MeshInst"
    assert report["factory"]["allocation_bytes"] == 0xB0
    assert report["factory"]["base_class"] == "MeshType"
    assert report["resource_loader"]["mode"] == "binary"
    assert report["resource_loader"]["function"] == "FUN_00859800"
    assert "LoadBinaryMeshFromResource" in report["resource_loader"]["retail_name"]

    layout = report["runtime_layout"]
    assert layout["instance_count"]["runtime_offset"] == 0x80
    assert layout["instance_count"]["source_descriptor_offset"] == 0x30
    assert layout["instance_count"]["value"] == 3
    assert layout["instance_storage"]["runtime_pointer_offset"] == 0x84
    assert layout["instance_storage"]["element_stride"] == 0x40
    assert layout["instance_storage"]["alignment"] == 0x10
    assert layout["instance_storage"]["payload_bytes"] == 0xC0
    assert layout["instance_storage"]["allocation_request_bytes"] == 0xD0
    assert 0x8C in layout["zero_initialized_dwords"]

    registration = report["renderer_registration"]
    assert registration["register"]["category"] == 10
    assert registration["unregister"]["category"] == 10


def test_imx_uses_xml_loader_and_preserves_mesh_xml_fields():
    report = build_meshinst_runtime_contract("tracks/test/banner.IMX")
    assert report["resource_loader"]["mode"] == "xml"
    assert report["resource_loader"]["function"] == "FUN_008587e0"
    assert "LoadXMLMeshFromResource" in report["resource_loader"]["retail_name"]
    assert report["resource_loader"]["neutral_geometry_format"] == (
        "SHIFT.IMXNeutralGeometry/1"
    )
    assert report["resource_loader"]["neutral_geometry_adapter"] == (
        "imx_neutral_geometry.build_imx_neutral_geometry"
    )
    assert report["resource_loader"]["xml_grammar"] == "source-backed"
    assert report["runtime_layout"]["instance_count"]["value"] is None
    assert report["runtime_layout"]["instance_storage"]["payload_bytes"] is None
    fields = report["mesh_type_base_loader"]["xml_fields_proven"]
    assert fields["vertices"] == "Vertices"
    assert fields["bounding_sphere"] == "BOUNDSPHERE"
    assert fields["axis_aligned_box"] == "AABBOX"
    assert fields["bones"] == "BONES"
    assert report["boundary"]["neutral_geometry_adapter"] == (
        "SHIFT.IMBNeutralGeometry/1 + SHIFT.IMXNeutralGeometry/1"
    )


def test_zero_instance_count_does_not_claim_storage_allocation():
    report = build_meshinst_runtime_contract(
        "tracks/test/empty.imb",
        descriptor_instance_count=0,
    )
    storage = report["runtime_layout"]["instance_storage"]
    assert storage["payload_bytes"] == 0
    assert storage["allocation_request_bytes"] is None
    assert (
        report["renderer_registration"]["register"]["condition"]
        == "runtime +0x80 != 0"
    )


def test_non_meshinst_resource_is_rejected():
    with pytest.raises(ValueError, match="requires a .imb or .imx"):
        build_meshinst_runtime_contract("tracks/test/object.meb")


def test_negative_instance_count_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        build_meshinst_runtime_contract(
            "tracks/test/object.imb",
            descriptor_instance_count=-1,
        )
