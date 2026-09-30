from sgb_resource_factory import (
    FORMAT,
    classify_sgb_object_resource,
)


def test_default_object_resource_uses_meshtype_factory():
    report = classify_sgb_object_resource("tracks/test/object.meb")
    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["descriptor_initial_type"] == 0
    assert report["factory_type"] == 0
    assert report["factory_name"] == "MeshType"
    assert report["allocation_bytes"] == 0x80
    assert report["constructor"] == "FUN_0085aac0"
    assert report["extension_promotion"]["enabled"] is False
    assert (
        report["render_instance"]["meshinst_type7_extra_call"]["enabled"]
        is False
    )


def test_imb_and_imx_promote_to_meshinst_type7_case_insensitively():
    for reference in (
        "tracks/test/banner.imb",
        r"TRACKS\TEST\INSTANCE.IMX",
    ):
        report = classify_sgb_object_resource(reference)
        assert report["ready"] is True
        assert report["factory_type"] == 7
        assert report["factory_name"] == "MeshInst"
        assert report["allocation_bytes"] == 0xB0
        assert report["constructor"] == "FUN_0085ae20"
        assert report["extension_promotion"]["enabled"] is True
        loader = report["resource_loader"]
        if report["extension"] == "imb":
            assert loader["mode"] == "binary"
            assert loader["function"] == "FUN_00859800"
        else:
            assert loader["mode"] == "xml"
            assert loader["function"] == "FUN_008587e0"
        extra = report["render_instance"]["meshinst_type7_extra_call"]
        assert extra == {
            "enabled": True,
            "condition": "resource_descriptor+0x04 == 7",
            "vfunc_offset": 0x04,
            "edx_flag": 1,
            "stack_arguments": [0x100, 0],
        }


def test_non_meshinst_extensions_stay_type0_without_meb_equivalence_claim():
    report = classify_sgb_object_resource("tracks/test/foo.meshtype")
    assert report["factory_type"] == 0
    assert report["factory_name"] == "MeshType"
    assert report["resource_loader"] is None
    assert report["boundary"]["meb_equivalence"] == "not-asserted"
    assert report["boundary"]["meshinst_to_meb_equivalence"] == "not-asserted"


def test_missing_reference_blocks_classification():
    report = classify_sgb_object_resource(None)
    assert report["ready"] is False
    assert report["factory_type"] is None
    assert report["blocking_reasons"] == [
        "sgb-resource-factory:resource-reference-missing"
    ]
